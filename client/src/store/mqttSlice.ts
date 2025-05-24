import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface MQTTState {
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error';
  currentUserId: string | null;
  currentToken: string | null;
  lastError: string | null;
}

const initialState: MQTTState = {
  connectionStatus: 'disconnected',
  currentUserId: null,
  currentToken: null,
  lastError: null
};

const mqttSlice = createSlice({
  name: 'mqtt',
  initialState,
  reducers: {
    connect: (state, action: PayloadAction<{ token: string; userId: string }>) => {
      state.connectionStatus = 'connecting';
      state.currentToken = action.payload.token;
      state.currentUserId = action.payload.userId;
      state.lastError = null;
    },
    connected: (state) => {
      state.connectionStatus = 'connected';
      state.lastError = null;
    },
    disconnected: (state) => {
      state.connectionStatus = 'disconnected';
      state.currentToken = null;
      state.currentUserId = null;
    },
    error: (state, action: PayloadAction<string>) => {
      state.connectionStatus = 'error';
      state.lastError = action.payload;
    },
    messageReceived: (state, action: PayloadAction<{ roomId: string; message: any }>) => {
      // No state changes needed for message received
    },
    setUserId: (state, action: PayloadAction<string>) => {
      state.currentUserId = action.payload;
    }
  }
});

export const { 
  connect, 
  connected, 
  disconnected, 
  error, 
  messageReceived,
  setUserId 
} = mqttSlice.actions;

export default mqttSlice.reducer; 