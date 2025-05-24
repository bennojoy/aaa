import React, { useEffect, useRef, useCallback } from 'react';
import { View, StyleSheet, FlatList, KeyboardAvoidingView, Platform } from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { RouteProp, useRoute, useFocusEffect } from '@react-navigation/native';
import { RootState } from '../../store';
import { getRoomMessages, getConnectionStatus } from '../../store/selectors/chatSelectors';
import { sendMessage, markMessagesAsRead } from '../../store/sagas/chatSaga';
import { Message, generateMessageId } from '../../types/message';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { ConnectionStatus } from './ConnectionStatus';
import { logger } from '../../utils/logger';
import { connect } from '../../store/mqttSlice';
import { mqttService } from '../../services/mqtt';
import { getTraceId } from '../../utils/trace';

type ChatScreenRouteProp = RouteProp<{
  Chat: {
    roomId: string;
    roomType: 'user' | 'assistant';
    roomName: string;
  };
}, 'Chat'>;

export const ChatScreen: React.FC = () => {
  const route = useRoute<ChatScreenRouteProp>();
  const { roomId, roomType, roomName } = route.params;
  const dispatch = useDispatch();
  const flatListRef = useRef<FlatList>(null);
  
  const messages = useSelector(getRoomMessages(roomId));
  const connectionStatus = useSelector(getConnectionStatus);
  const { currentUserId } = useSelector((state: RootState) => state.mqtt);
  const { token, user } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    logger.info('Chat screen mounted', { roomId, roomType, roomName }, 'chat');
    // Mark messages as read when entering the room
    dispatch(markMessagesAsRead({ roomId }));
    return () => {
      logger.info('Chat screen unmounted', { roomId, roomType, roomName }, 'chat');
    };
  }, [roomId, roomType, roomName]);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    if (messages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [messages]);

  // Handle MQTT reconnection when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      const traceId = getTraceId();
      logger.info('Chat screen focused', { traceId }, 'chat');

      // Check MQTT connection status
      if (!mqttService.isConnected() && token && user?.id) {
        logger.info('MQTT not connected, attempting to connect', {
          userId: user.id,
          hasToken: !!token,
          traceId
        }, 'chat');

        dispatch(connect({ token, userId: user.id }));
      }

      return () => {
        logger.info('Chat screen unfocused', { traceId }, 'chat');
      };
    }, [dispatch, token, user?.id])
  );

  const handleSendMessage = (content: string) => {
    if (content.trim()) {
      logger.info('Sending message', { roomId, roomType, content }, 'chat');
      dispatch(sendMessage({ roomId, content, roomType, messageId: generateMessageId() }));
    }
  };

  const renderMessage = useCallback(({ item }: { item: Message }) => (
    <MessageBubble message={item} />
  ), []);

  const handleViewableItemsChanged = useCallback(({ viewableItems }: { viewableItems: any[] }) => {
    // Mark messages as read when they become visible
    if (viewableItems.length > 0) {
      dispatch(markMessagesAsRead({ roomId }));
    }
  }, [roomId, dispatch]);

  const viewabilityConfig = {
    itemVisiblePercentThreshold: 50
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <ConnectionStatus status={connectionStatus} />
      
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.messageList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        onViewableItemsChanged={handleViewableItemsChanged}
        viewabilityConfig={viewabilityConfig}
      />

      <MessageInput onSend={handleSendMessage} />
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  messageList: {
    padding: 16,
  },
}); 