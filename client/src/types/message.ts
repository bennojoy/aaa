import { v4 as uuidv4 } from 'uuid';

export type MessageStatus = 'sending' | 'sent' | 'failed' | 'delivered' | 'read';
export type RoomType = 'user' | 'assistant';

export interface BaseMessage {
  id: string;
  room_id: string;
  room_type: 'user' | 'assistant';
  content: string;
  sender_id: string;
  timestamp: string;
  status: 'sending' | 'sent' | 'delivered' | 'error';
  trace_id: string;
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
export const generateMessageId = () => {
  return crypto.randomUUID();
};

export const generateTraceId = (messageId: string) => `trace_${messageId}`;