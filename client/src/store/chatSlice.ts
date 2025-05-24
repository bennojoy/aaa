import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ChatState, Message, MessageStatus } from '../types/message';
import { logger } from '../utils/logger';

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

      const existingMessage = state.messages[roomId].items[message.id];
      const isNewMessage = !existingMessage;
      const statusChanged = existingMessage?.status !== message.status;

      // Always update the message in the store
      state.messages[roomId].items[message.id] = message;
      
      // Only increment total for new messages
      if (isNewMessage) {
        state.messages[roomId].total += 1;
      }
      
      // Increment unread count if message is not from current user and status is delivered
      if (message.status === 'delivered' && !existingMessage) {
        state.messages[roomId].unread += 1;
      }

      // Debug log for message persistence
      console.log('Message added/updated in store:', {
        roomId,
        messageId: message.id,
        content: message.content,
        status: message.status,
        isNewMessage,
        statusChanged,
        totalMessages: state.messages[roomId].total,
        currentState: state.messages[roomId]
      });
    },

    updateMessageStatus: (state, action: PayloadAction<{ messageId: string; status: MessageStatus }>) => {
      const { messageId, status } = action.payload;
      
      // Find the message in any room and update its status
      Object.values(state.messages).forEach(roomMessages => {
        if (roomMessages.items[messageId]) {
          const oldStatus = roomMessages.items[messageId].status;
          roomMessages.items[messageId].status = status;
          
          // Debug log for status update
          console.log('Message status updated:', {
            messageId,
            oldStatus,
            newStatus: status,
            roomId: Object.keys(state.messages).find(roomId => 
              state.messages[roomId].items[messageId]
            )
          });
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