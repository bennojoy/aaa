import { Message as BaseMessage } from './message';

export interface OpenAIMessage {
  role: 'user' | 'assistant';
  content: string;
}

export type MessageWithHistory = BaseMessage & {
  history?: OpenAIMessage[] | null;
}

export interface Message {
  id: string;
  content: string;
  room_id: string;
  room_type: 'user' | 'assistant';
  type: string;
  sender_id: string;
  trace_id: string;
  timestamp: string;
  client_timestamp: string;
  created_at: string;
  status: 'sending' | 'sent' | 'failed';
  history?: Array<{
    role: 'user' | 'assistant';
    content: string;
  }> | null;
} 