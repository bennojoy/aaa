import { Middleware } from 'redux';
import { mqttService } from '../../services/mqtt';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { RootState } from '../store';
import { messageReceived } from '../mqttSlice';
import { addMessage } from '../chatSlice';
import { Message } from '../../types/message';

interface SendMessageAction {
  type: 'chat/sendMessage';
  payload: {
    roomId: string;
    content: string;
    roomType: 'user' | 'assistant';
    messageId: string;
  };
}

interface ConnectAction {
  type: 'mqtt/connect';
  payload: {
    token: string;
    userId: string;
  };
}

const isSendMessageAction = (action: unknown): action is SendMessageAction => {
  return (
    typeof action === 'object' &&
    action !== null &&
    'type' in action &&
    action.type === 'chat/sendMessage' &&
    'payload' in action &&
    typeof action.payload === 'object' &&
    action.payload !== null &&
    'roomId' in action.payload &&
    'content' in action.payload &&
    'roomType' in action.payload &&
    'messageId' in action.payload
  );
};

const isConnectAction = (action: unknown): action is ConnectAction => {
  return (
    typeof action === 'object' &&
    action !== null &&
    'type' in action &&
    action.type === 'mqtt/connect' &&
    'payload' in action &&
    typeof action.payload === 'object' &&
    action.payload !== null &&
    'token' in action.payload &&
    'userId' in action.payload
  );
};

export const mqttMiddleware: Middleware = (store) => {
  let unsubscribe: (() => void) | null = null;

  const handleMessage = (topic: string, message: any) => {
    try {
      // Handle both string and object message formats
      const parsedMessage = typeof message === 'string' 
        ? JSON.parse(message)
        : message;

      logger.info('MQTT message received', {
        topic,
        message: parsedMessage,
        traceId: parsedMessage.trace_id,
        currentState: {
          isConnected: mqttService.isConnected(),
          currentUserId: mqttService.getCurrentUserId(),
          hasUnsubscribe: !!unsubscribe
        }
      }, 'mqtt');

      // Extract message details
      const messageId = parsedMessage.id;
      const roomId = parsedMessage.room_id;
      const roomType = parsedMessage.room_type;
      const content = parsedMessage.content;
      const traceId = parsedMessage.trace_id;
      const senderId = parsedMessage.sender_id || 'system';
      const timestamp = parsedMessage.timestamp || new Date().toISOString();
      const status = parsedMessage.status || 'delivered';

      // Prepare message for store
      const storeMessage: Message = {
        id: messageId,
        room_id: roomId,
        room_type: roomType,
        content,
        sender_id: senderId,
        timestamp,
        status,
        trace_id: traceId,
        ...(roomType === 'assistant' ? { assistant_name: parsedMessage.assistant_name || 'Assistant' } : {})
      };

      // Dispatch message to store
      store.dispatch(messageReceived({ roomId, message: storeMessage }));
      store.dispatch(addMessage({ roomId, message: storeMessage }));

    } catch (error) {
      logger.error('Error handling MQTT message', {
        error,
        topic,
        message: typeof message === 'string' ? message : JSON.stringify(message)
      }, 'mqtt');
    }
  };

  return next => (action: unknown) => {
    const result = next(action);
    const traceId = getTraceId();

    // Handle connect action
    if (isConnectAction(action)) {
      const { token, userId } = action.payload;
      const state = store.getState() as RootState;

      // Check if we're already connected with the same user
      if (mqttService.isConnected() && mqttService.getCurrentUserId() === userId) {
        logger.info('Already connected with same user', {
          userId
        }, 'mqtt');
        return result;
      }

      logger.info('Initiating MQTT connection', { 
        userId, 
        traceId,
        hasToken: !!token,
        currentState: {
          isConnected: mqttService.isConnected(),
          currentUserId: mqttService.getCurrentUserId()
        }
      }, 'mqtt');

      // Connect to MQTT
      mqttService.connect({ token, userId })
        .then(async () => {
          // Set up message handler if not already set
          if (!unsubscribe) {
            mqttService.addMessageHandler(handleMessage);
            unsubscribe = () => {
              mqttService.removeMessageHandler(handleMessage);
              unsubscribe = null;
            };
          }

          // Subscribe to user's message topic
          const userTopic = `user/${userId}/message`;
          await mqttService.subscribe(userTopic);

          logger.info('MQTT connection successful', {
            userId,
            traceId,
            topic: userTopic,
            currentState: {
              isConnected: mqttService.isConnected(),
              currentUserId: mqttService.getCurrentUserId()
            }
          }, 'mqtt');
        })
        .catch((err) => {
          logger.error('MQTT connection failed', {
            error: err instanceof Error ? err.message : 'Unknown error',
            userId,
            traceId,
            currentState: {
              isConnected: mqttService.isConnected(),
              currentUserId: mqttService.getCurrentUserId()
            }
          }, 'mqtt');
        });
    }

    // Handle message sending
    if (isSendMessageAction(action)) {
      const { roomId, content, roomType, messageId } = action.payload;
      const state = store.getState() as RootState;
      const currentUserId = mqttService.getCurrentUserId();

      if (!mqttService.isConnected()) {
        logger.error('Cannot send message: MQTT not connected', {
          roomId,
          roomType,
          messageId,
          traceId
        }, 'mqtt');
        return result;
      }

      const message = {
        id: messageId,
        room_id: roomId,
        room_type: roomType,
        content,
        sender_id: currentUserId,
        timestamp: new Date().toISOString(),
        status: 'sending',
        trace_id: traceId
      };

      mqttService.publish('messages/to_room', JSON.stringify(message))
        .then(() => {
          logger.info('Message published successfully', {
            messageId,
            traceId,
            currentState: {
              isConnected: mqttService.isConnected(),
              currentUserId
            }
          }, 'mqtt');
        })
        .catch(error => {
          logger.error('Failed to publish message', {
            error,
            messageId,
            traceId,
            currentState: {
              isConnected: mqttService.isConnected(),
              currentUserId
            }
          }, 'mqtt');
        });
    }

    return result;
  };
}; 