import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSelector } from 'react-redux';
import { Message } from '../../types/message';
import { getCurrentUserId } from '../../store/selectors/authSelectors';
import { RootState } from '../../store/store';
import { logger } from '../../utils/logger';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const currentUserId = useSelector(getCurrentUserId);
  
  logger.info('Rendering MessageBubble', {
    messageId: message.id,
    content: message.content,
    sender: message.sender_id,
    status: message.status
  });
  
  const isOwnMessage = message.sender_id === currentUserId;
  const timestamp = new Date(message.timestamp).toLocaleTimeString();

  return (
    <View style={[
      styles.container,
      isOwnMessage ? styles.ownMessage : styles.otherMessage
    ]}>
      {!isOwnMessage && message.room_type === 'assistant' && (
        <Text style={styles.assistantName}>{message.assistant_name}</Text>
      )}
      
      <View style={[
        styles.bubble,
        isOwnMessage ? styles.ownBubble : styles.otherBubble
      ]}>
        <Text style={[
          styles.messageText,
          isOwnMessage ? styles.ownMessageText : styles.otherMessageText
        ]}>
          {message.content}
        </Text>
      </View>

      <View style={styles.footer}>
        <Text style={styles.timestamp}>{timestamp}</Text>
        {isOwnMessage && message.status !== 'sending' && (
          <Text style={styles.status}>{message.status}</Text>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 4,
    maxWidth: '80%',
  },
  ownMessage: {
    alignSelf: 'flex-end',
  },
  otherMessage: {
    alignSelf: 'flex-start',
  },
  assistantName: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
    marginLeft: 4,
  },
  bubble: {
    padding: 12,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.2,
    shadowRadius: 1.41,
    elevation: 2,
  },
  ownBubble: {
    backgroundColor: '#0ABAB5',
    borderBottomRightRadius: 4,
  },
  otherBubble: {
    backgroundColor: '#E5E5EA',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 20,
  },
  ownMessageText: {
    color: '#fff',
  },
  otherMessageText: {
    color: '#000',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    marginTop: 2,
    paddingHorizontal: 4,
  },
  timestamp: {
    fontSize: 10,
    color: '#666',
    marginRight: 4,
  },
  status: {
    fontSize: 10,
    color: '#666',
  }
}); 