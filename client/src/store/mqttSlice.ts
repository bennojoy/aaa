import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Message, MessageStatus } from '../types/message';

interface MQTTState {
  connectionStatus: 'connecting' | 'connected' | 'disconnected';
  messages: {
    [roomId: string]: Message[];
  };
  currentUserId: string | null;
  currentToken: string | null;
  error: string | null;
}

const initialState: MQTTState = {
  connectionStatus: 'disconnected',
  messages: {},
  currentUserId: null,
  currentToken: null,
  error: null
};

const mqttSlice = createSlice({
  name: 'mqtt',
  initialState,
  reducers: {
    connect: (state, action: PayloadAction<{ token: string; userId: string }>) => {
      state.connectionStatus = 'connecting';
      state.currentToken = action.payload.token;
      state.currentUserId = action.payload.userId;
      state.error = null;
    },
    connected: (state) => {
      state.connectionStatus = 'connected';
      state.error = null;
    },
    disconnected: (state) => {
      state.connectionStatus = 'disconnected';
      state.currentToken = null;
      state.currentUserId = null;
    },
    error: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.connectionStatus = 'disconnected';
    },
    messageReceived: (state, action: PayloadAction<{ roomId: string; message: Message }>) => {
      const { roomId, message } = action.payload;
      if (!state.messages[roomId]) {
        state.messages[roomId] = [];
      }
      state.messages[roomId].push(message);
    },
    messageSent: (state, action: PayloadAction<{ roomId: string; messageId: string }>) => {
      const { roomId, messageId } = action.payload;
      const message = state.messages[roomId]?.find(m => m.id === messageId);
      if (message) {
        message.status = 'sent';
      }
    },
    messageFailed: (state, action: PayloadAction<{ roomId: string; messageId: string }>) => {
      const { roomId, messageId } = action.payload;
      const message = state.messages[roomId]?.find(m => m.id === messageId);
      if (message) {
        message.status = 'failed';
      }
    },
    clearMessages: (state, action: PayloadAction<string>) => {
      delete state.messages[action.payload];
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
  clearMessages
} = mqttSlice.actions;

export default mqttSlice.reducer; 