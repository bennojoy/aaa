import React, { useEffect, useRef, useCallback, useState } from 'react';
import { View, StyleSheet, FlatList, KeyboardAvoidingView, Platform, Text, TouchableOpacity, TextInput, NativeSyntheticEvent, NativeScrollEvent } from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { RouteProp, useRoute, useFocusEffect, useNavigation } from '@react-navigation/native';
import { RootState } from '../../store/store';
import { getRoomMessages, getConnectionStatus } from '../../store/selectors/chatSelectors';
import { 
  addMessage, 
  updateMessageStatus, 
  markRoomAsRead,
  setConnectionStatus
} from '../../store/slices/chatSlice';
import { connect as connectMQTT } from '../../store/slices/mqttSlice';
import { logger } from '../../utils/logger';
import { mqttService } from '../../services/mqtt';
import { getTraceId } from '../../utils/trace';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { RootStackParamList } from '../../navigation/types';
import { MQTT_CONFIG } from '../../types/mqtt';
import { v4 as uuidv4 } from 'uuid';
import { getMessageHistory } from '../../utils/messageFormat';
import { Message, generateMessageId, generateTraceId } from '../../types/message';
import { MessageWithHistory } from '../../types/chat';
import { WebRTCService } from '../../services/webrtcService';
import { basicAgent } from '../../config/agentConfig';

type ChatScreenRouteProp = RouteProp<RootStackParamList, 'Chat'>;

interface ChatState {
  messages: { [key: string]: Message[] };
  loading: boolean;
  error: string | null;
}

interface MQTTState {
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  currentUserId: string | null;
}

interface AuthState {
  token: string | null;
  user: {
    id: string;
    name: string;
  } | null;
}

export const ChatScreen = () => {
  const route = useRoute<ChatScreenRouteProp>();
  const navigation = useNavigation();
  const { roomId, roomType, roomName } = route.params;
  const dispatch = useDispatch();
  const { currentUserId } = useSelector((state: RootState & { mqtt: MQTTState }) => state.mqtt);
  const messages = useSelector(getRoomMessages(roomId));
  const connectionStatus = useSelector(getConnectionStatus);
  const { token, user } = useSelector((state: RootState & { auth: AuthState }) => state.auth);
  const [newMessage, setNewMessage] = useState('');
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(true);
  const flatListRef = useRef<FlatList>(null);
  const [isCallActive, setIsCallActive] = useState(false);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const webrtcService = useRef<WebRTCService | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isScrolledToBottom) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [messages, isScrolledToBottom]);

  // Handle MQTT reconnection and mark messages as read when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      const traceId = getTraceId();
      logger.info('Chat screen focused', { traceId }, 'chat');

      if (connectionStatus === 'disconnected' && token && user?.id) {
        const retryCount = mqttService.getRetryCount();
        const lastError = mqttService.getLastError();
        const connectionQuality = mqttService.getConnectionQuality();
        const connectionHistory = mqttService.getConnectionHistory();

        logger.info('Attempting MQTT reconnection on screen focus', {
          userId: user.id,
          hasToken: !!token,
          retryCount,
          lastError: lastError?.message,
          connectionQuality,
          recentHistory: connectionHistory.slice(-3) // Last 3 connection events
        }, 'mqtt');
        
        dispatch(connectMQTT({ token, userId: user.id }));
      }

      // Mark messages as read when component mounts or screen comes into focus
      if (currentUserId) {
        dispatch(markRoomAsRead({ roomId, currentUserId }));
        flatListRef.current?.scrollToEnd({ animated: false });
      }

      return () => {
        logger.info('Chat screen unfocused', { traceId }, 'chat');
      };
    }, [dispatch, token, user?.id, currentUserId, roomId, connectionStatus])
  );

  // Handle scroll events to detect if we're at the bottom
  const handleScroll = useCallback((event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { layoutMeasurement, contentOffset, contentSize } = event.nativeEvent;
    const paddingToBottom = 20;
    const isAtBottom = layoutMeasurement.height + contentOffset.y >= contentSize.height - paddingToBottom;
    setIsScrolledToBottom(isAtBottom);
  }, []);

  // Scroll to bottom function
  const scrollToBottom = useCallback(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
    if (currentUserId) {
      dispatch(markRoomAsRead({ roomId, currentUserId }));
    }
  }, [dispatch, roomId, currentUserId]);

  useEffect(() => {
    // Initialize WebRTC service
    webrtcService.current = new WebRTCService(audioElementRef);
    
    // Set up message callback
    webrtcService.current.setMessageCallback((event) => {
      console.log('Received event in ChatScreen:', event);
      
      switch (event.type) {
        case 'conversation.item.create':
          if (event.item?.role === 'assistant') {
            const messageId = generateMessageId();
            const message: Message = {
              id: messageId,
              content: event.item.content[0].text,
              room_id: roomId,
              room_type: 'assistant',
              sender_id: 'assistant',
              timestamp: new Date().toISOString(),
              client_timestamp: new Date().toISOString(),
              status: 'sent',
              trace_id: generateTraceId(messageId),
              assistant_name: 'Assistant'
            };
            dispatch(addMessage({ roomId, message }));
          }
          break;
          
        case 'transcription':
          // Add transcription as a user message
          const messageId = generateMessageId();
          const message: Message = {
            id: messageId,
            content: event.text,
            room_id: roomId,
            room_type: 'user',
            sender_id: user?.id || 'user',
            timestamp: new Date().toISOString(),
            client_timestamp: new Date().toISOString(),
            status: 'sent',
            trace_id: generateTraceId(messageId)
          };
          dispatch(addMessage({ roomId, message }));
          break;
      }
    });

    return () => {
      if (isCallActive) {
        webrtcService.current?.endCall();
      }
    };
  }, [dispatch, roomId, user?.id]);

  const handleCallToggle = async () => {
    if (isCallActive) {
      // End call
      await webrtcService.current?.endCall();
      setIsCallActive(false);
    } else {
      try {
        // Start call using token from Redux store
        await webrtcService.current?.startCall(basicAgent.instructions);
        setIsCallActive(true);
      } catch (error) {
        console.error('Failed to start call:', error);
      }
    }
  };

  const handleSend = () => {
    if (!newMessage.trim() || !user?.id) return;

    const messageId = generateMessageId();
    const message: Message = {
      id: messageId,
      content: newMessage.trim(),
      room_id: roomId,
      room_type: roomType,
      sender_id: user.id,
      timestamp: new Date().toISOString(),
      client_timestamp: new Date().toISOString(),
      status: 'sending',
      trace_id: generateTraceId(messageId)
    };

    if (isCallActive && webrtcService.current) {
      // Send message through WebRTC when call is active
      webrtcService.current.sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'message',
          role: 'user',
          content: [{ type: 'input_text', text: newMessage.trim() }]
        }
      });
      // Trigger response
      webrtcService.current.sendEvent({ type: 'response.create' });
    } else {
      // Send message through MQTT when no call is active
      const mqttMessage = {
        type: 'message',
        room_id: roomId,
        room_type: roomType,
        content: newMessage.trim(),
        sender_id: user.id,
        timestamp: new Date().toISOString(),
        trace_id: message.trace_id
      };
      // Use the configured topic format
      mqttService.publish(`messages/to_room/${roomId}`, JSON.stringify(mqttMessage));
    }

    // Add message to local state
    dispatch(addMessage({ roomId, message }));

    // Clear input
    setNewMessage('');
  };

  const renderMessage = ({ item }: { item: Message }) => (
    <View style={[
      styles.messageContainer,
      item.sender_id === user?.id ? styles.userMessage : styles.aiMessage
    ]}>
      <Text style={styles.messageText}>{item.content}</Text>
      <Text style={styles.timestamp}>
        {new Date(item.timestamp).toLocaleTimeString()}
      </Text>
    </View>
  );

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Icon name="arrow-back" size={24} color="#007AFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{roomName}</Text>
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.messageList}
        onScroll={handleScroll}
        scrollEventThrottle={16}
        onEndReachedThreshold={0.5}
        ListEmptyComponent={
          <Text style={styles.emptyText}>
            No messages yet. Start the conversation!
          </Text>
        }
      />

      {!isScrolledToBottom && (
        <TouchableOpacity 
          style={styles.scrollToBottomButton}
          onPress={scrollToBottom}
        >
          <Icon name="arrow-downward" size={24} color="#fff" />
        </TouchableOpacity>
      )}

      <View style={styles.inputContainer}>
        <TouchableOpacity 
          style={[styles.callButton, isCallActive && styles.callButtonActive]}
          onPress={handleCallToggle}
        >
          <Icon 
            name={isCallActive ? "call-end" : "call"} 
            size={24} 
            color={isCallActive ? "#fff" : "#30D5C8"} 
          />
        </TouchableOpacity>

        <TextInput
          style={styles.input}
          value={newMessage}
          onChangeText={setNewMessage}
          placeholder="Type a message..."
          placeholderTextColor="#86939e"
          multiline
        />

        <TouchableOpacity 
          style={[styles.sendButton, !newMessage.trim() && styles.sendButtonDisabled]}
          onPress={handleSend}
          disabled={!newMessage.trim()}
        >
          <Icon name="send" size={24} color={newMessage.trim() ? "#30D5C8" : "#86939e"} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    marginRight: 16,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  messageList: {
    padding: 16,
  },
  messageContainer: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
    marginBottom: 8,
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#0ABAB5',
    opacity: 0.8,
  },
  aiMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#0ABAB5',
  },
  messageText: {
    fontSize: 16,
    color: '#fff',
  },
  timestamp: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    marginTop: 4,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  input: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginHorizontal: 8,
    maxHeight: 100,
    color: '#000',
  },
  sendButton: {
    padding: 8,
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  callButton: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: '#f5f5f5',
  },
  callButtonActive: {
    backgroundColor: '#ff3b30',
  },
  scrollToBottomButton: {
    position: 'absolute',
    right: 16,
    bottom: 80,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  emptyText: {
    textAlign: 'center',
    color: '#86939e',
    marginTop: 32,
  },
}); 