import { v4 as uuidv4 } from 'uuid';

export type MessageStatus = 'sending' | 'sent' | 'failed' | 'delivered' | 'read';
export type RoomType = 'user' | 'assistant';

export interface BaseMessage {
  id: string;
  room_id: string;
  room_type: RoomType;
  content: string;
  trace_id: string;
  sender_id: string;
  client_timestamp: string;
  status: MessageStatus;
}

export interface UserMessage extends BaseMessage {
  room_type: 'user';
}

export interface AssistantMessage extends BaseMessage {
  room_type: 'assistant';
  assistant_name: string;
}

export type Message = UserMessage | AssistantMessage;

export interface RoomMessages {
  items: { [messageId: string]: Message };
  total: number;
  unread: number;
}

export interface ChatState {
  messages: {
    [roomId: string]: RoomMessages;
  };
  sendingStatus: {
    [messageId: string]: MessageStatus;
  };
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
}

// Utility functions
export const generateMessageId = () => uuidv4();
export const generateTraceId = (messageId: string) => `trace_${messageId}`; 