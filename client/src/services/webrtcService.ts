import { RefObject } from 'react';
import { store } from '../store/store';
import { getAuthToken } from '../store/selectors/authSelectors';
import { logger } from '../utils/logger';
import { apiClient } from '../api/client';
import { Message, generateMessageId, generateTraceId } from '@/types/message';
import { 
  addMessage, 
  updateMessageStatus, 
  markRoomAsRead,
  setConnectionStatus
} from '../store/slices/chatSlice';

import { basicAgent } from '../config/agentConfig';
import { MQTT_CONFIG } from '@/types/mqtt';

interface WebRTCEvent {
  type: string;
  session?: {
    modalities: string[];
    instructions: string;
    voice: string;
    input_audio_transcription: { model: string };
    turn_detection: {
      type: string;
      threshold: number;
      prefix_padding_ms: number;
      silence_duration_ms: number;
      create_response: boolean;
    };
    tools: any[];
  };
  item?: {
    type: string;
    role: string;
    content: Array<{ type: string; text: string }>;
  };
}

export class WebRTCService {
  private peerConnection: RTCPeerConnection | null = null;
  private dataChannel: RTCDataChannel | null = null;
  private isCallActive: boolean = false;
  private traceId: string = '';
  private audioElement: RefObject<HTMLAudioElement | null>;
  private onMessageCallback: ((event: any) => void) | null = null;
  private instructions: string = '';
  private roomId: string;
  private userId: string;

  constructor(audioElement: RefObject<HTMLAudioElement | null>, roomId: string, userId: string) {
    this.audioElement = audioElement;
    this.traceId = crypto.randomUUID();
    this.roomId = roomId;
    this.userId = userId;
    // Create and attach audio element if it doesn't exist
    if (!this.audioElement.current) {
      const audio = document.createElement('audio');
      audio.autoplay = true;
      document.body.appendChild(audio);
      // @ts-ignore - we know this is safe to do
      this.audioElement.current = audio;
    }
  }

  setMessageCallback(callback: (event: any) => void) {
    this.onMessageCallback = callback;
  }

  async startCall(roomId: string): Promise<void> {
    try {
      if (this.isCallActive) {
        logger.warn('Call already active', { traceId: this.traceId });
        return;
      }
      
      this.instructions = basicAgent.instructions;
      this.roomId = roomId;

      // Get auth token from Redux store
      const state = store.getState();
      logger.info('Current Redux state:', { 
        state: {
          auth: {
            token: state.auth.token,
            isAuthenticated: state.auth.isAuthenticated,
            hasUser: !!state.auth.user
          }
        },
        traceId: this.traceId 
      });

      const token = getAuthToken(state);
      if (!token) {
        logger.error('No authentication token available', { 
          state: {
            auth: {
              token: state.auth.token,
              isAuthenticated: state.auth.isAuthenticated,
              hasUser: !!state.auth.user
            }
          },
          traceId: this.traceId 
        });
        throw new Error('No authentication token available');
      }

      logger.info('Got auth token', { 
        tokenLength: token.length,
        tokenPreview: `${token.substring(0, 4)}...${token.substring(token.length - 4)}`,
        traceId: this.traceId 
      });

      // Get ephemeral token from our backend
      const response = await apiClient.post('/api/v1/webrtc/ephemeral-token');
      const { ephemeral_token } = response.data;
      logger.info('Got ephemeral token', { traceId: this.traceId });

      // Initialize WebRTC connection with OpenAI
      this.peerConnection = new RTCPeerConnection();

      // Set up audio track handling for remote audio
      this.peerConnection.ontrack = (e) => {
        logger.info('Received remote audio track', { 
          trackKind: e.track.kind,
          traceId: this.traceId 
        });
        if (this.audioElement.current) {
          this.audioElement.current.srcObject = e.streams[0];
          // Ensure audio playback is enabled
          this.audioElement.current.play().catch(error => {
            logger.error('Failed to play audio', { 
              error, 
              traceId: this.traceId 
            });
          });
        }
      };

      // Set up local audio track
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioTrack = ms.getTracks()[0];
      this.peerConnection.addTrack(audioTrack);
      logger.info('Added local audio track', { 
        trackKind: audioTrack.kind,
        traceId: this.traceId 
      });

      // Create data channel
      this.dataChannel = this.peerConnection.createDataChannel('oai-events');
      this.setupDataChannelHandlers();

      // Create and set local description
      logger.info('Creating WebRTC offer', { traceId: this.traceId });
      const offer = await this.peerConnection.createOffer();
      logger.info('WebRTC offer created', { 
        offer: {
          type: offer.type,
          sdpLength: offer.sdp?.length,
        },
        traceId: this.traceId 
      });

      logger.info('Setting local description', { traceId: this.traceId });
      await this.peerConnection.setLocalDescription(offer);
      logger.info('Local description set successfully', { traceId: this.traceId });

      // Exchange SDP with OpenAI's realtime API
      logger.info('Initiating SDP exchange with OpenAI', { 
        url: 'https://api.openai.com/v1/realtime',
        traceId: this.traceId 
      });

      const baseUrl = 'https://api.openai.com/v1/realtime';
      const model = 'gpt-4o-realtime-preview-2024-12-17';

      const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
        method: 'POST',
        body: offer.sdp,
        headers: {
          'Authorization': `Bearer ${ephemeral_token}`,
          'Content-Type': 'application/sdp',
        },
      });

      if (!sdpResponse.ok) {
        logger.error('SDP exchange failed', { 
          status: sdpResponse.status,
          statusText: sdpResponse.statusText,
          traceId: this.traceId 
        });
        throw new Error('Failed to establish WebRTC connection');
      }

      logger.info('SDP exchange successful', { 
        status: sdpResponse.status,
        traceId: this.traceId 
      });

      const answerSdp = await sdpResponse.text();
      logger.info('Received SDP answer', { 
        sdpLength: answerSdp.length,
        traceId: this.traceId 
      });

      const answer: RTCSessionDescriptionInit = {
        type: 'answer',
        sdp: answerSdp,
      };

      logger.info('Setting remote description', { traceId: this.traceId });
      await this.peerConnection.setRemoteDescription(answer);
      logger.info('Remote description set successfully', { traceId: this.traceId });

      // Wait for data channel to be open
      if (this.dataChannel?.readyState !== 'open') {
        await new Promise<void>((resolve) => {
          if (!this.dataChannel) return;
          const onOpen = () => {
            this.dataChannel?.removeEventListener('open', onOpen);
            resolve();
          };
          this.dataChannel.addEventListener('open', onOpen);
        });
      }

      this.isCallActive = true;
      logger.info('WebRTC call started successfully', { 
        connectionState: this.peerConnection.connectionState,
        iceConnectionState: this.peerConnection.iceConnectionState,
        traceId: this.traceId 
      });

    } catch (error) {
      logger.error('Failed to start call', { 
        error, 
        traceId: this.traceId 
      });
      this.cleanup();
      throw error;
    }
  }

  private setupDataChannelHandlers(): void {
    if (!this.dataChannel) return;

    this.dataChannel.onopen = () => {
      logger.info('Data channel opened', { traceId: this.traceId });
    };

    this.dataChannel.onclose = () => {
      logger.info('Data channel closed', { traceId: this.traceId });
      this.cleanup();
    };

    this.dataChannel.onerror = (error) => {
      logger.error('Data channel error', { 
        error, 
        traceId: this.traceId 
      });
      this.cleanup();
    };

    this.dataChannel.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        logger.info('Received message', { 
          type: message.type,
          message: message,
          traceId: this.traceId 
        });

        // Handle session.created event
        if (message.type === 'session.created') {
          // Send session.update with agent configuration
          const sessionUpdateEvent = {
            type: 'session.update',
            session: {
              modalities: ['text', 'audio'],
              instructions: this.instructions,
              voice: 'sage',
              input_audio_transcription: { model: 'whisper-1' },
              turn_detection: {
                type: 'server_vad',
                threshold: 0.9,
                prefix_padding_ms: 300,
                silence_duration_ms: 500,
                create_response: true
              },
              tools: []
            }
          };
          
          this.dataChannel?.send(JSON.stringify(sessionUpdateEvent));
          logger.info('Sent session.update event', { 
            event: sessionUpdateEvent,
            traceId: this.traceId 
          });
        }

        if (message.type == 'conversation.item.input_audio_transcription.completed') {
          // Add transcription as a user message
          const messageId = generateMessageId();
          const user_message: Message = {
            id: messageId,
            content: message.transcript,
            room_id: this.roomId,
            room_type: 'assistant',
            sender_id: this.userId || 'user',
            timestamp: new Date().toISOString(),
            status: 'sent',
            trace_id: generateTraceId(messageId)
          };
          store.dispatch(addMessage({ roomId: this.roomId, message: user_message }));
        }
        if (message.type == 'response.output_item.done') {
          const messageId = generateMessageId();
          const assistant_message: Message = {
            id: messageId,
            content: message.item.content[0].transcript,
            room_id: this.roomId,
            room_type: 'assistant',
            sender_id: MQTT_CONFIG.ai.senderId,
            timestamp: new Date().toISOString(),
            status: 'sent',
            trace_id: generateTraceId(messageId)
          };
          store.dispatch(addMessage({ roomId: this.roomId, message: assistant_message }));
        }
 
        if (this.onMessageCallback) {
          this.onMessageCallback(message);
        }
      } catch (error) {
        logger.error('Failed to parse message', { 
          error, 
          traceId: this.traceId 
        });
      }
    };
  }

  sendMessage(message: string): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      logger.warn('Cannot send message - data channel not open', { 
        traceId: this.traceId 
      });
      return;
    }

    try {
      this.dataChannel.send(JSON.stringify({
        type: 'message',
        content: message,
      }));
      logger.info('Message sent', { 
        message, 
        traceId: this.traceId 
      });
    } catch (error) {
      logger.error('Failed to send message', { 
        error, 
        traceId: this.traceId 
      });
    }
  }

  endCall(): void {
    logger.info('Ending call', { traceId: this.traceId });
    this.cleanup();
  }

  private cleanup(): void {
    if (this.dataChannel) {
      this.dataChannel.close();
      this.dataChannel = null;
    }

    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    this.isCallActive = false;
    logger.info('Call cleaned up', { traceId: this.traceId });
  }

  sendEvent(event: WebRTCEvent): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      logger.warn('Cannot send event - data channel not open', { 
        traceId: this.traceId 
      });
      return;
    }

    try {
      this.dataChannel.send(JSON.stringify(event));
      logger.info('Event sent', { 
        event, 
        traceId: this.traceId 
      });
    } catch (error) {
      logger.error('Failed to send event', { 
        error, 
        traceId: this.traceId 
      });
    }
  }
}