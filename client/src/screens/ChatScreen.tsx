import React, { useRef, useState, useEffect } from 'react';
import { View, TextInput, TouchableOpacity, StyleSheet, FlatList, Text } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { WebRTCService } from '../services/webrtcService';
import { basicAgent } from '../config/agentConfig';
import { useDispatch, useSelector } from 'react-redux';
import { addMessage } from '../store/slices/chatSlice';
import { RootState } from '../store/store';

const ChatScreen = () => {
  const [newMessage, setNewMessage] = useState('');
  const [isCallActive, setIsCallActive] = useState(false);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const webrtcService = useRef<WebRTCService | null>(null);
  const dispatch = useDispatch();
  const messages = useSelector((state: RootState) => state.chat.messages);

  useEffect(() => {
    // Initialize WebRTC service
    webrtcService.current = new WebRTCService(audioElementRef);
    
    // Set up message callback
    webrtcService.current.setMessageCallback((event) => {
      console.log('Received event in ChatScreen:', event);
      
      switch (event.type) {
        case 'conversation.item.create':
          if (event.item?.role === 'assistant') {
            const message = {
              id: Date.now().toString(),
              content: event.item.content[0].text,
              sender: 'ai' as const,
              timestamp: new Date().toISOString()
            };
            dispatch(addMessage(message));
          }
          break;
          
        case 'transcription':
          // Add transcription as a user message
          const transcriptionMessage = {
            id: Date.now().toString(),
            content: event.text,
            sender: 'user' as const,
            timestamp: new Date().toISOString()
          };
          dispatch(addMessage(transcriptionMessage));
          break;
      }
    });

    return () => {
      if (isCallActive) {
        webrtcService.current?.endCall();
      }
    };
  }, []);

  const handleCallToggle = async () => {
    if (isCallActive) {
      // End call
      await webrtcService.current?.endCall();
      setIsCallActive(false);
    } else {
      try {
        // Get ephemeral key from your server
        const response = await fetch('/api/session');
        const data = await response.json();
        const ephemeralKey = data.client_secret.value;

        // Start call
        await webrtcService.current?.startCall(ephemeralKey, basicAgent.instructions);
        setIsCallActive(true);
      } catch (error) {
        console.error('Failed to start call:', error);
      }
    }
  };

  const handleSend = () => {
    if (!newMessage.trim() || !webrtcService.current) return;

    // Send message through WebRTC
    webrtcService.current.sendEvent({
      type: 'conversation.item.create',
      item: {
        type: 'message',
        role: 'user',
        content: [{ type: 'input_text', text: newMessage.trim() }]
      }
    });

    // Add message to local state
    const message = {
      id: Date.now().toString(),
      content: newMessage.trim(),
      sender: 'user' as const,
      timestamp: new Date().toISOString()
    };
    dispatch(addMessage(message));

    // Clear input
    setNewMessage('');

    // Trigger response
    webrtcService.current.sendEvent({ type: 'response.create' });
  };

  const renderMessage = ({ item }: { item: any }) => (
    <View style={[
      styles.messageContainer,
      item.sender === 'user' ? styles.userMessage : styles.aiMessage
    ]}>
      <Text style={styles.messageText}>{item.content}</Text>
      <Text style={styles.timestamp}>
        {new Date(item.timestamp).toLocaleTimeString()}
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={messages}
        renderItem={renderMessage}
        keyExtractor={item => item.id}
        style={styles.messageList}
        inverted={false}
      />
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          value={newMessage}
          onChangeText={setNewMessage}
          placeholder="Type a message..."
          multiline
        />
        <TouchableOpacity 
          style={[styles.sendButton, !newMessage.trim() && styles.sendButtonDisabled]} 
          onPress={handleSend}
          disabled={!newMessage.trim()}
        >
          <Icon name="send" size={24} color={newMessage.trim() ? "#007AFF" : "#ccc"} />
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.callButton, isCallActive && styles.callButtonActive]} 
          onPress={handleCallToggle}
        >
          <Icon name={isCallActive ? "call-end" : "call"} size={24} color={isCallActive ? "#FF3B30" : "#007AFF"} />
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  messageList: {
    flex: 1,
    padding: 10,
  },
  messageContainer: {
    maxWidth: '80%',
    padding: 10,
    borderRadius: 15,
    marginVertical: 5,
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#007AFF',
  },
  aiMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#E5E5EA',
  },
  messageText: {
    color: '#fff',
    fontSize: 16,
  },
  timestamp: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    marginTop: 5,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 10,
    borderTopWidth: 1,
    borderTopColor: '#eee',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 8,
    marginRight: 10,
    maxHeight: 100,
  },
  sendButton: {
    padding: 8,
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  callButton: {
    padding: 8,
    marginLeft: 10,
  },
  callButtonActive: {
    backgroundColor: '#FFE5E5',
    borderRadius: 20,
  },
});

export default ChatScreen; 