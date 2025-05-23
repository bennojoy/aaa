import { RootState } from '../index';
import { Message } from '../../types/message';

export const getRoomMessages = (roomId: string) => (state: RootState) => {
  const roomMessages = state.chat.messages[roomId];
  if (!roomMessages) return [];

  // Convert messages object to array and sort by timestamp
  return Object.values(roomMessages.items)
    .sort((a, b) => new Date(a.client_timestamp).getTime() - new Date(b.client_timestamp).getTime());
};

export const getRoomUnreadCount = (roomId: string) => (state: RootState) => {
  return state.chat.messages[roomId]?.unread || 0;
};

export const getMessageStatus = (messageId: string) => (state: RootState) => {
  return state.chat.sendingStatus[messageId] || 'sending';
};

export const getConnectionStatus = (state: RootState) => {
  return state.chat.connectionStatus;
}; 