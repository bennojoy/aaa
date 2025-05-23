import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSelector } from 'react-redux';
import { Message } from '../../types/message';
import { getCurrentUserId } from '../../store/selectors/authSelectors';
import { getMessageStatus } from '../../store/selectors/chatSelectors';
import { RootState } from '../../store';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const currentUserId = useSelector(getCurrentUserId);
  const messageStatus = useSelector((state: RootState) => getMessageStatus(message.id)(state));
  
  const isOwnMessage = message.sender_id === currentUserId;
  const timestamp = new Date(message.client_timestamp).toLocaleTimeString();

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
        <Text style={styles.messageText}>{message.content}</Text>
      </View>

      <View style={styles.footer}>
        <Text style={styles.timestamp}>{timestamp}</Text>
        {isOwnMessage && (
          <Text style={styles.status}>{messageStatus}</Text>
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
  },
  bubble: {
    padding: 12,
    borderRadius: 16,
  },
  ownBubble: {
    backgroundColor: '#007AFF',
  },
  otherBubble: {
    backgroundColor: '#E5E5EA',
  },
  messageText: {
    fontSize: 16,
    color: '#000',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    marginTop: 2,
  },
  timestamp: {
    fontSize: 10,
    color: '#666',
    marginRight: 4,
  },
  status: {
    fontSize: 10,
    color: '#666',
  },
}); 