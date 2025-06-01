import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { mqttService } from '../../services/mqtt';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';

interface MQTTState {
  currentUserId: string | null;
  currentToken: string | null;
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error';
  retryCount: number;
  lastError: Error | null;
}

const initialState: MQTTState = {
  currentUserId: null,
  currentToken: null,
  connectionStatus: 'disconnected',
  retryCount: 0,
  lastError: null
};

const mqttSlice = createSlice({
  name: 'mqtt',
  initialState,
  reducers: {
    connect: (state, action: PayloadAction<{ token: string; userId: string }>) => {
      const { token, userId } = action.payload;
      const traceId = getTraceId();

      logger.info('Connecting to MQTT', { userId, traceId }, 'mqtt');
      
      state.connectionStatus = 'connecting';
      state.currentUserId = userId;
      state.currentToken = token;
      state.retryCount = 0;
      state.lastError = null;

      try {
        mqttService.connect({ token, userId });
      } catch (error) {
        logger.error('Failed to connect to MQTT', { error, traceId }, 'mqtt');
        state.connectionStatus = 'error';
        state.lastError = error as Error;
      }
    },
    connected: (state) => {
      const traceId = getTraceId();
      logger.info('Connected to MQTT', { traceId }, 'mqtt');
      state.connectionStatus = 'connected';
      state.lastError = null;
    },
    disconnected: (state) => {
      const traceId = getTraceId();
      logger.info('Disconnected from MQTT', { traceId }, 'mqtt');
      state.connectionStatus = 'disconnected';
      state.currentToken = null;
      state.currentUserId = null;
      state.retryCount = 0;
      state.lastError = null;
    },
    error: (state, action: PayloadAction<Error>) => {
      const traceId = getTraceId();
      logger.error('MQTT error', { error: action.payload, traceId }, 'mqtt');
      state.connectionStatus = 'error';
      state.lastError = action.payload;
    },
    messageReceived: (state, action: PayloadAction<{ roomId: string; message: any }>) => {
      // No state changes needed for message received
    },
    messageSent: (state, action: PayloadAction<{ roomId: string; messageId: string }>) => {
      // No state changes needed for message sent
    },
    messageFailed: (state, action: PayloadAction<{ roomId: string; messageId: string }>) => {
      // No state changes needed for message failed
    },
    setUserId: (state, action: PayloadAction<string>) => {
      state.currentUserId = action.payload;
    },
    setRetryCount: (state, action: PayloadAction<number>) => {
      state.retryCount = action.payload;
    }
  }
});

export const { 
  connect, 
  connected, 
  disconnected, 
  error, 
  messageReceived,
  messageSent,
  messageFailed,
  setUserId,
  setRetryCount
} = mqttSlice.actions;

export default mqttSlice.reducer; 