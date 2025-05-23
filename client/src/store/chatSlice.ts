import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ChatState, Message, MessageStatus } from '../types/message';

const initialState: ChatState = {
  messages: {},
  sendingStatus: {},
  connectionStatus: 'disconnected'
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    // Connection status
    setConnectionStatus: (state, action: PayloadAction<ChatState['connectionStatus']>) => {
      state.connectionStatus = action.payload;
    },

    // Message actions
    addMessage: (state, action: PayloadAction<{ roomId: string; message: Message }>) => {
      const { roomId, message } = action.payload;
      
      if (!state.messages[roomId]) {
        state.messages[roomId] = {
          items: {},
          total: 0,
          unread: 0
        };
      }

      state.messages[roomId].items[message.id] = message;
      state.messages[roomId].total += 1;
      
      // Increment unread count if message is not from current user
      if (message.status === 'delivered') {
        state.messages[roomId].unread += 1;
      }
    },

    updateMessageStatus: (state, action: PayloadAction<{ messageId: string; status: MessageStatus }>) => {
      const { messageId, status } = action.payload;
      
      // Find the message in any room and update its status
      Object.values(state.messages).forEach(roomMessages => {
        if (roomMessages.items[messageId]) {
          roomMessages.items[messageId].status = status;
        }
      });

      state.sendingStatus[messageId] = status;
    },

    markRoomAsRead: (state, action: PayloadAction<string>) => {
      const roomId = action.payload;
      if (state.messages[roomId]) {
        state.messages[roomId].unread = 0;
        // Update all message statuses to 'read'
        Object.values(state.messages[roomId].items).forEach(message => {
          if (message.status === 'delivered') {
            message.status = 'read';
          }
        });
      }
    },

    clearRoomMessages: (state, action: PayloadAction<string>) => {
      const roomId = action.payload;
      delete state.messages[roomId];
    }
  }
});

export const {
  setConnectionStatus,
  addMessage,
  updateMessageStatus,
  markRoomAsRead,
  clearRoomMessages
} = chatSlice.actions;

export default chatSlice.reducer; 