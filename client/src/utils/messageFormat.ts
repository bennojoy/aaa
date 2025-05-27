import { MQTT_CONFIG } from '../config/mqtt';
import { Message } from '../types/message';
import { OpenAIMessage } from '../types/chat';

export const getMessageHistory = (
  messages: Message[], 
  currentUserId: string, 
  maxMessages: number,
  roomType: string,
  currentMessage: string
): OpenAIMessage[] | null => {
  // Only collect history for AI rooms or @ai messages
  if (roomType !== 'assistant' && !currentMessage.startsWith('@ai')) {
    return null;
  }

  // Get last X messages
  const recentMessages = messages.slice(-maxMessages);

  // Format messages based on room type
  return recentMessages.map(msg => {
    let role: 'user' | 'assistant';
    
    if (roomType === 'assistant') {
      // In assistant room, only two roles: current user and assistant
      role = msg.sender_id === currentUserId ? 'user' : 'assistant';
    } else {
      // In user room, check against AI sender ID
      role = msg.sender_id === MQTT_CONFIG.ai.senderId ? 'assistant' : 'user';
    }

    return {
      role,
      content: msg.content
    };
  });
}; 