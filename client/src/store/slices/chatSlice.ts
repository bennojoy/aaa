import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ChatState, Message, MessageStatus } from '../../types/message';
import { logger } from '../../utils/logger';

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
      logger.info('Message added/updated in store', {
        roomId,
        messageId: message.id,
        content: message.content,
        status: message.status,
        isNewMessage,
        statusChanged,
        totalMessages: state.messages[roomId].total,
        currentState: state.messages[roomId]
      }, 'chat');
    },

    updateMessageStatus: (state, action: PayloadAction<{ messageId: string; status: MessageStatus }>) => {
      const { messageId, status } = action.payload;
      
      // Find the message in any room and update its status
      Object.values(state.messages).forEach(roomMessages => {
        if (roomMessages.items[messageId]) {
          const oldStatus = roomMessages.items[messageId].status;
          roomMessages.items[messageId].status = status;
          
          // Debug log for status update
          logger.info('Message status updated', {
            messageId,
            oldStatus,
            newStatus: status,
            roomId: Object.keys(state.messages).find(roomId => 
              state.messages[roomId].items[messageId]
            )
          }, 'chat');
        }
      });

      state.sendingStatus[messageId] = status;
    },

    markRoomAsRead: (state, action: PayloadAction<{ roomId: string; currentUserId: string }>) => {
      const { roomId, currentUserId } = action.payload;
      if (state.messages[roomId]) {
        logger.info('Starting markRoomAsRead', {
          roomId,
          currentUserId,
          totalMessages: Object.keys(state.messages[roomId].items).length,
          currentUnreadCount: state.messages[roomId].unread
        }, 'chat');

        // Reset unread count
        state.messages[roomId].unread = 0;
        
        // Update all message statuses to 'read' for messages from other users
        let updatedCount = 0;
        Object.values(state.messages[roomId].items).forEach(message => {
          const oldStatus = message.status;
          if (message.sender_id !== currentUserId && message.status !== 'read') {
            message.status = 'read';
            updatedCount++;
            logger.info('Message status updated', {
              messageId: message.id,
              senderId: message.sender_id,
              oldStatus,
              newStatus: message.status,
              content: message.content.substring(0, 50) // Log first 50 chars of content
            }, 'chat');
          }
        });

        // Debug log for marking room as read
        logger.info('Room marked as read complete', {
          roomId,
          unreadCount: state.messages[roomId].unread,
          totalMessages: Object.keys(state.messages[roomId].items).length,
          messagesUpdated: updatedCount,
          currentState: state.messages[roomId]
        }, 'chat');
      } else {
        logger.info('Room not found in state', { roomId }, 'chat');
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