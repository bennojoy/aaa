import { Middleware, AnyAction } from 'redux';
import { connect, connected, disconnected, error, messageReceived, messageSent, messageFailed } from '../mqttSlice';
import { setConnectionStatus } from '../chatSlice';
import { mqttService } from '../../services/mqtt';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { MQTT_CONFIG } from '../../config/mqtt';
import { addMessage } from '../chatSlice';

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

function isSendMessageAction(action: unknown): action is SendMessageAction {
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
}

export const mqttMiddleware: Middleware = store => {
  console.log('MQTT middleware initialized');
  
  let unsubscribe: (() => void) | null = null;
  let connectionAttempts = 0;
  let reconnectTimeout: NodeJS.Timeout | null = null;
  const MAX_RECONNECT_ATTEMPTS = 3;
  const RECONNECT_DELAY = 2000; // 2 seconds

  const clearReconnectTimeout = () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  };

  const attemptReconnect = (token: string, userId: string, traceId: string) => {
    clearReconnectTimeout();

    if (connectionAttempts >= MAX_RECONNECT_ATTEMPTS) {
      logger.error('Max reconnection attempts reached', { 
        userId, 
        traceId,
        attempts: connectionAttempts 
      }, 'mqtt');
      store.dispatch(error('Max reconnection attempts reached'));
      store.dispatch(disconnected());
      store.dispatch(setConnectionStatus('disconnected'));
      return;
    }

    connectionAttempts++;
    logger.info('Attempting MQTT reconnection', { 
      userId, 
      traceId,
      attempt: connectionAttempts,
      maxAttempts: MAX_RECONNECT_ATTEMPTS
    }, 'mqtt');

    reconnectTimeout = setTimeout(() => {
      mqttService.connect(token, userId)
        .then(() => {
          logger.info('MQTT reconnection successful', { 
            userId, 
            traceId,
            attempt: connectionAttempts 
          }, 'mqtt');
          store.dispatch(connected());
          store.dispatch(setConnectionStatus('connected'));
          connectionAttempts = 0;
        })
        .catch(err => {
          logger.error('MQTT reconnection failed', { 
            error: err, 
            userId, 
            traceId,
            attempt: connectionAttempts 
          }, 'mqtt');
          attemptReconnect(token, userId, traceId);
        });
    }, RECONNECT_DELAY);
  };

  return next => (action: unknown) => {
    if (typeof action === 'object' && action !== null && 'type' in action) {
      console.log('MQTT middleware received action:', (action as AnyAction).type);
    }
    
    const result = next(action);
    const traceId = getTraceId();

    if (connect.match(action)) {
      console.log('MQTT connect action matched');
      const { token, userId } = action.payload;

      if (!token || !userId) {
        console.error('Invalid MQTT connection parameters:', { hasToken: !!token, hasUserId: !!userId });
        logger.error('Invalid MQTT connection parameters', { 
          hasToken: !!token, 
          hasUserId: !!userId,
          traceId 
        }, 'mqtt');
        store.dispatch(error('Invalid connection parameters'));
        store.dispatch(disconnected());
        store.dispatch(setConnectionStatus('disconnected'));
        return result;
      }

      // Check if we're already connected
      const currentState = store.getState().mqtt;
      if (currentState.connectionStatus === 'connected' && currentState.currentUserId === userId) {
        logger.info('Already connected to MQTT', { 
          userId, 
          traceId,
          currentState 
        }, 'mqtt');
        return result;
      }

      logger.info('MQTT middleware handling connect action', { 
        userId, 
        hasToken: !!token,
        traceId,
        currentState,
        config: MQTT_CONFIG
      }, 'mqtt');

      // Set up message handler
      const messageHandler = (topic: string, message: any) => {
        const messageId = message.id;
        const roomId = message.room_id;
        const roomType = message.room_type;
        const messageTraceId = getTraceId();
        
        logger.info('MQTT middleware received message', {
          messageId,
          roomId,
          roomType,
          content: message.content,
          senderId: message.sender_id,
          timestamp: message.client_timestamp,
          traceId: messageTraceId,
          currentState: store.getState().mqtt
        }, 'mqtt');
        
        // Add message to store with appropriate status
        const messageToAdd = {
          ...message,
          status: message.sender_id === userId ? 'sent' : 'delivered'
        };
        
        // Dispatch to both MQTT and chat slices
        store.dispatch(messageReceived({ roomId, message: messageToAdd }));
        store.dispatch(addMessage({ roomId, message: messageToAdd }));
        
        logger.info('Message dispatched to store', {
          messageId,
          roomId,
          status: messageToAdd.status,
          traceId: messageTraceId,
          currentState: store.getState().mqtt
        }, 'mqtt');
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

      mqttService.connect(token, userId)
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
        .catch(err => {
          console.error('MQTT connect promise rejected:', err);
          logger.error('MQTT middleware connection error', { 
            error: err, 
            traceId,
            currentState: store.getState().mqtt,
            config: MQTT_CONFIG
          }, 'mqtt');
          store.dispatch(error(err.message));
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

      logger.info('Publishing message to MQTT', { 
        messageId, 
        traceId,
        payload: messagePayload,
        currentState: state.mqtt
      }, 'mqtt');

      // First dispatch messageSent to update UI immediately
      store.dispatch(messageSent({ roomId, messageId }));

      // Publish to the correct topic
      mqttService.publish(`messages/to_room`, JSON.stringify(messagePayload))
        .then(() => {
          logger.info('Message published successfully', { 
            messageId, 
            traceId,
            currentState: state.mqtt
          }, 'mqtt');
        })
        .catch(err => {
          logger.error('Failed to publish message', { 
            error: err, 
            messageId, 
            traceId,
            currentState: state.mqtt
          }, 'mqtt');
          store.dispatch(messageFailed({ roomId, messageId }));
        });
    }

    return result;
  };
}; 