import { Middleware, AnyAction } from 'redux';
import { connect, connected, disconnected, error, messageReceived, messageSent, messageFailed } from './slices/mqttSlice';
import { setConnectionStatus, addMessage, updateMessageStatus } from './slices/chatSlice';
import { mqttService } from '../services/mqtt';
import { logger } from '../utils/logger';
import { getTraceId } from '../utils/trace';
import { MQTT_CONFIG } from '../types/mqtt';
import { Message, MessageStatus } from '../types/message';

// Immediate logging
console.log('MQTT middleware module loaded');

interface SendMessageAction extends AnyAction {
  type: 'chat/sendMessage';
  payload: {
    roomId: string;
    content: string;
    roomType: string;
    messageId: string;
  };
}

interface ConnectAction extends AnyAction {
  type: 'mqtt/connect';
  payload: {
    token: string;
    userId: string;
  };
}

const isSendMessageAction = (action: unknown): action is SendMessageAction => {
  return (action as SendMessageAction)?.type === 'chat/sendMessage';
};

const isConnectAction = (action: unknown): action is ConnectAction => {
  return (action as ConnectAction)?.type === 'mqtt/connect';
};

export const mqttMiddleware: Middleware = store => {
  let reconnectTimeout: NodeJS.Timeout;
  let connectionAttempts = 0;
  const MAX_RECONNECT_ATTEMPTS = 5;

  const attemptReconnect = (token: string, userId: string, traceId: string) => {
    connectionAttempts++;
    const delay = Math.min(1000 * Math.pow(2, connectionAttempts), 30000);
    
    logger.info('Attempting MQTT reconnection', { 
      attempt: connectionAttempts, 
      delay,
      traceId 
    }, 'mqtt');
    
    reconnectTimeout = setTimeout(() => {
      store.dispatch({ type: 'mqtt/connect', payload: { token, userId } });
    }, delay);
  };

  return next => action => {
    const result = next(action);
    const traceId = getTraceId();

    // Handle connection
    if (isConnectAction(action)) {
      const { token, userId } = action.payload;

      // Clear any existing reconnect timeout
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }

      // Set up message handler
      const messageHandler = (topic: string, message: any) => {
        console.log('MQTT message received:', { topic, message });
        
        try {
          // Parse message if it's a string
          const parsedMessage = typeof message === 'string' ? JSON.parse(message) : message;
          console.log('Parsed MQTT message:', parsedMessage);

          const messageId = parsedMessage.id;
          const roomId = parsedMessage.room_id;
          const roomType = parsedMessage.room_type;
          const messageTraceId = getTraceId();
          const state = store.getState();
          
          console.log('Message details:', {
            messageId,
            roomId,
            roomType,
            senderId: parsedMessage.sender_id,
            content: parsedMessage.content
          });
          
          logger.info('MQTT middleware received message from topic', {
            topic,
            messageId,
            roomId,
            roomType,
            content: parsedMessage.content,
            senderId: parsedMessage.sender_id,
            timestamp: parsedMessage.client_timestamp,
            traceId: messageTraceId,
            currentState: state.mqtt
          }, 'mqtt');

          // Skip if no room_id in message
          if (!roomId) {
            logger.warn('Received message without room_id, skipping', {
              topic,
              messageId,
              traceId: messageTraceId
            }, 'mqtt');
            return;
          }

          // Check if this is a response to our own message
          const existingMessage = state.chat.messages[roomId]?.items[messageId];
          const isResponseToOwnMessage = existingMessage?.status === 'sending';
          console.log('Checking for existing message:', {
            roomId,
            messageId,
            existingMessage,
            allMessages: state.chat.messages[roomId]?.items,
            isResponseToOwnMessage
          });
          
          if (isResponseToOwnMessage) {
            // Update the status of our sent message
            logger.info('Updating status of sent message', {
              messageId,
              roomId,
              traceId: messageTraceId
            }, 'mqtt');
            store.dispatch(updateMessageStatus({ messageId, status: 'sent' }));
            return;
          }
          
          // For new messages, add them to the store with 'delivered' status
          const messageToAdd = {
            ...parsedMessage,
            status: 'delivered' as MessageStatus,  // All received messages start as 'delivered'
            room_type: roomType === 'assistant' ? 'assistant' as const : 'user' as const,
            assistant_name: roomType === 'assistant' ? 'Assistant' : undefined,
            timestamp: new Date().toISOString()
          };
          
          console.log('Prepared message for store:', messageToAdd);
          
          logger.info('Dispatching message to store', {
            messageId,
            roomId,
            status: messageToAdd.status,
            roomType: messageToAdd.room_type,
            traceId: messageTraceId,
            currentState: state.mqtt
          }, 'mqtt');

          // For received messages, dispatch messageReceived
          store.dispatch(messageReceived({ roomId, message: messageToAdd }));
          
          // Always dispatch addMessage to ensure message is in the store
          console.log('Dispatching addMessage action');
          store.dispatch(addMessage({ roomId, message: messageToAdd }));
          
          logger.info('Message dispatched to store successfully', {
            messageId,
            roomId,
            status: messageToAdd.status,
            roomType: messageToAdd.room_type,
            traceId: messageTraceId,
            currentState: state.mqtt
          }, 'mqtt');
        } catch (error) {
          console.error('Error processing MQTT message:', error);
          logger.error('Error processing MQTT message', {
            error,
            topic,
            message,
            traceId: getTraceId()
          }, 'mqtt');
        }
      };

      // Connect to MQTT
      logger.info('Initiating MQTT connection', { 
        userId, 
        traceId,
        config: MQTT_CONFIG
      }, 'mqtt');
      store.dispatch(setConnectionStatus('connecting'));
      
      console.log('About to call mqttService.connect with:', {
        token: token ? 'present' : 'missing',
        userId,
        config: MQTT_CONFIG
      });

      mqttService.connect({ token, userId })
        .then(() => {
          console.log('MQTT connect promise resolved');
          logger.info('MQTT connection successful, dispatching connected action', { 
            userId, 
            traceId,
            currentState: store.getState().mqtt
          }, 'mqtt');
          store.dispatch(connected());
          store.dispatch(setConnectionStatus('connected'));
          connectionAttempts = 0;
          
          // Subscribe to user's message topic
          const userTopic = `user/${userId}/message`;
          logger.info('Subscribing to user topic', { topic: userTopic, traceId }, 'mqtt');
          return mqttService.subscribe(userTopic);
        })
        .then(() => {
          // Add message handler
          logger.info('Adding message handler', { traceId }, 'mqtt');
          mqttService.addMessageHandler(messageHandler);
          logger.info('MQTT middleware setup complete', { 
            userId, 
            traceId,
            currentState: store.getState().mqtt
          }, 'mqtt');
        })
        .catch((err: Error) => {
          console.error('MQTT connect promise rejected:', err);
          logger.error('MQTT middleware connection error', { 
            error: err, 
            traceId,
            currentState: store.getState().mqtt,
            config: MQTT_CONFIG
          }, 'mqtt');
          store.dispatch(error(err));
          store.dispatch(disconnected());
          store.dispatch(setConnectionStatus('disconnected'));
          
          // Only attempt reconnect if we haven't exceeded max attempts
          if (connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
            attemptReconnect(token, userId, traceId);
          } else {
            logger.error('Max reconnection attempts reached, giving up', {
              userId,
              traceId,
              attempts: connectionAttempts,
              maxAttempts: MAX_RECONNECT_ATTEMPTS
            }, 'mqtt');
          }
        });
    }

    // Handle message sending
    if (isSendMessageAction(action)) {
      const { roomId, content, roomType, messageId } = action.payload;
      const state = store.getState();
      const userId = state.mqtt.currentUserId;
      const connectionStatus = state.mqtt.connectionStatus;

      logger.info('MQTT middleware handling send message', { 
        roomId, 
        roomType, 
        messageId, 
        traceId,
        content,
        senderId: userId,
        connectionStatus,
        currentState: state.mqtt
      }, 'mqtt');

      if (!userId) {
        logger.error('Cannot send message: No user ID in MQTT state', { 
          messageId, 
          traceId,
          currentState: state.mqtt
        }, 'mqtt');
        store.dispatch(messageFailed({ roomId, messageId }));
        return result;
      }

      if (connectionStatus !== 'connected') {
        logger.error('Cannot send message: MQTT not connected', { 
          messageId, 
          traceId,
          connectionStatus,
          currentState: state.mqtt
        }, 'mqtt');
        store.dispatch(messageFailed({ roomId, messageId }));
        return result;
      }

      const messagePayload = {
        id: messageId,
        room_id: roomId,
        room_type: roomType,
        content,
        trace_id: traceId,
        sender_id: userId,
        client_timestamp: new Date().toISOString()
      };

      logger.info('Creating message with sending status', { 
        messageId, 
        traceId,
        payload: messagePayload
      }, 'mqtt');

      // Create message with 'sending' status
      const message = roomType === 'assistant' 
        ? {
            ...messagePayload,
            room_type: 'assistant' as const,
            status: 'sending' as MessageStatus,
            assistant_name: 'Assistant',
            timestamp: new Date().toISOString()
          }
        : {
            ...messagePayload,
            room_type: 'user' as const,
            status: 'sending' as MessageStatus,
            timestamp: new Date().toISOString()
          };
      
      // Add message to store with 'sending' status
      logger.info('Dispatching addMessage with sending status', {
        messageId,
        status: message.status,
        traceId
      }, 'mqtt');
      store.dispatch(addMessage({ roomId, message }));

      // Publish to the correct topic
      logger.info('Publishing message to MQTT', {
        messageId,
        traceId,
        topic: 'messages/to_room'
      }, 'mqtt');

      (async () => {
        try {
          await mqttService.publish(`messages/to_room`, JSON.stringify(messagePayload));
          
          logger.info('Message published successfully, updating status to sent', { 
            messageId, 
            traceId,
            currentState: state.mqtt
          }, 'mqtt');
          
          // First update the message in the store to ensure consistency
          const updatedMessage = {
            ...message,
            status: 'sent' as MessageStatus,
            timestamp: new Date().toISOString()
          };
          
          logger.info('Dispatching addMessage with sent status', {
            messageId,
            status: updatedMessage.status,
            traceId
          }, 'mqtt');
          store.dispatch(addMessage({ roomId, message: updatedMessage }));
          
          // Then update the message status
          logger.info('Dispatching updateMessageStatus', {
            messageId,
            status: 'sent',
            traceId
          }, 'mqtt');
          store.dispatch(updateMessageStatus({ messageId, status: 'sent' }));
          
          // Finally dispatch messageSent action
          logger.info('Dispatching messageSent action', {
            messageId,
            roomId,
            traceId
          }, 'mqtt');
          store.dispatch(messageSent({ roomId, messageId }));
        } catch (err) {
          logger.error('Failed to publish message, updating status to failed', { 
            error: err, 
            messageId, 
            traceId,
            currentState: state.mqtt
          }, 'mqtt');
          
          // Update message status to 'failed'
          store.dispatch(updateMessageStatus({ messageId, status: 'failed' }));
          
          // Also update the message in the store to ensure consistency
          const updatedMessage = {
            ...message,
            status: 'failed' as MessageStatus,
            timestamp: new Date().toISOString()
          };
          store.dispatch(addMessage({ roomId, message: updatedMessage }));
          
          // Dispatch messageFailed action
          store.dispatch(messageFailed({ roomId, messageId }));
        }
      })();
    }

    return result;
  };
}; 