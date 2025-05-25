import React, { useEffect, useRef, useCallback, useState } from 'react';
import { View, StyleSheet, FlatList, KeyboardAvoidingView, Platform, Text, TouchableOpacity, TextInput, NativeSyntheticEvent, NativeScrollEvent } from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { RouteProp, useRoute, useFocusEffect, useNavigation } from '@react-navigation/native';
import { RootState } from '../../store';
import { getRoomMessages, getConnectionStatus } from '../../store/selectors/chatSelectors';
import { markRoomAsRead, addMessage, updateMessageStatus } from '../../store/chatSlice';
import { connect } from '../../store/mqttSlice';
import { logger } from '../../utils/logger';
import { mqttService } from '../../services/mqtt';
import { getTraceId } from '../../utils/trace';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { RootStackParamList } from '../../navigation/types';
import { MQTT_CONFIG } from '../../config/mqtt';
import { v4 as uuidv4 } from 'uuid';

type ChatScreenRouteProp = RouteProp<RootStackParamList, 'Chat'>;

export const ChatScreen = () => {
  const route = useRoute<ChatScreenRouteProp>();
  const navigation = useNavigation();
  const { roomId, roomType, roomName } = route.params;
  const dispatch = useDispatch();
  const { currentUserId } = useSelector((state: RootState) => state.mqtt);
  const messages = useSelector(getRoomMessages(roomId));
  const connectionStatus = useSelector(getConnectionStatus);
  const { token, user } = useSelector((state: RootState) => state.auth);
  const [newMessage, setNewMessage] = useState('');
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(true);
  const flatListRef = useRef<FlatList>(null);

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
        
        dispatch(connect({ token, userId: user.id }));
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

  const handleSend = () => {
    if (!newMessage.trim()) return;

    // Check if MQTT is actually connected
    if (!mqttService.isConnected()) {
      logger.warn('MQTT not connected, attempting to reconnect', {
        roomId,
        userId: currentUserId,
        traceId: getTraceId()
      }, 'chat');

      // Attempt to reconnect
      if (token && user?.id) {
        dispatch(connect({ token, userId: user.id }));
      }
      return;
    }

    const messageId = uuidv4();
    const timestamp = new Date().toISOString();
    const message = {
      id: messageId,
      content: newMessage.trim(),
      room_id: roomId,
      room_type: roomType as 'user' | 'assistant',
      type: 'message',
      sender_id: currentUserId || '',
      trace_id: getTraceId(),
      timestamp: timestamp,
      client_timestamp: timestamp,
      created_at: timestamp,
      status: 'sending' as const
    };

    // Add message to Redux immediately
    dispatch(addMessage({ roomId, message }));

    // Publish to MQTT
    mqttService.publish(MQTT_CONFIG.topics.publish.messages, JSON.stringify(message))
      .catch(error => {
        logger.error('Failed to send message', {
          error,
          roomId,
          messageId
        }, 'chat');
        // Update message status to failed
        dispatch(updateMessageStatus({ messageId, status: 'failed' }));
      });

    setNewMessage('');
  };

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
        renderItem={({ item }) => (
          <View style={[
            styles.messageContainer,
            item.sender_id === currentUserId ? styles.sentMessage : styles.receivedMessage
          ]}>
            <Text style={styles.messageText}>{item.content}</Text>
            <Text style={styles.messageTime}>
              {new Date(item.timestamp || item.created_at).toLocaleTimeString()}
            </Text>
          </View>
        )}
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
        <TextInput
          style={styles.input}
          value={newMessage}
          onChangeText={setNewMessage}
          placeholder="Type a message..."
          multiline
        />
        <TouchableOpacity 
          style={[styles.sendButton, !newMessage.trim() && styles.sendButtonDisabled]} 
          onPress={handleSend}
          disabled={!newMessage.trim()}
        >
          <Icon name="send" size={24} color={newMessage.trim() ? "#007AFF" : "#ccc"} />
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
    borderBottomColor: '#eee',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 16,
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
  sentMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#007AFF',
  },
  receivedMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#E5E5EA',
  },
  messageText: {
    fontSize: 16,
    color: '#000',
  },
  messageTime: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  scrollToBottomButton: {
    position: 'absolute',
    right: 20,
    bottom: 80,
    backgroundColor: '#007AFF',
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  input: {
    flex: 1,
    padding: 12,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    marginRight: 8,
    maxHeight: 100,
  },
  sendButton: {
    padding: 12,
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 16,
    color: '#666',
  },
}); 