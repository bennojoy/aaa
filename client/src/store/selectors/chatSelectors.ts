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

export const getLastUnreadMessage = (roomId: string) => (state: RootState) => {
  const roomMessages = state.chat.messages[roomId];
  if (!roomMessages) return null;

  const currentUserId = state.mqtt.currentUserId;
  if (!currentUserId) return null;

  // Get all messages and sort by timestamp in descending order
  const messages = Object.values(roomMessages.items)
    .sort((a, b) => new Date(b.client_timestamp).getTime() - new Date(a.client_timestamp).getTime());

  // Find the first unread message that is not from the current user
  return messages.find(msg => 
    msg.status === 'delivered' && msg.sender_id !== currentUserId
  ) || null;
};

export const getMessageStatus = (messageId: string) => (state: RootState) => {
  return state.chat.sendingStatus[messageId] || 'sending';
};

export const getConnectionStatus = (state: RootState) => {
  return state.chat.connectionStatus;
}; 