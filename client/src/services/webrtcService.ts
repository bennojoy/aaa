import { RefObject } from 'react';
import { store } from '../store/store';

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
  private pc: RTCPeerConnection | null = null;
  private dc: RTCDataChannel | null = null;
  private audioElement: RefObject<HTMLAudioElement | null>;
  private onMessageCallback: ((event: any) => void) | null = null;

  constructor(audioElement: RefObject<HTMLAudioElement | null>) {
    this.audioElement = audioElement;
  }

  setMessageCallback(callback: (event: any) => void) {
    this.onMessageCallback = callback;
  }

  async startCall(agentInstructions: string) {
    try {
      console.log('Starting WebRTC call...');
      
      // Get token from Redux store
      const state = store.getState();
      const token = state.auth.token;
      
      if (!token) {
        throw new Error('No authentication token available');
      }

      // 1. Create peer connection
      this.pc = new RTCPeerConnection();
      console.log('Peer connection created');
      
      // 2. Set up audio track handling
      this.pc.ontrack = (e) => {
        console.log('Received audio track:', e.track.kind);
        if (this.audioElement.current) {
          this.audioElement.current.srcObject = e.streams[0];
        }
      };

      // 3. Get user's microphone and add track
      console.log('Requesting microphone access...');
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('Microphone access granted');
      this.pc.addTrack(ms.getTracks()[0]);

      // 4. Create data channel
      this.dc = this.pc.createDataChannel("oai-events");
      console.log('Data channel created');
      this.setupDataChannelHandlers();

      // 5. Create and set local description (offer)
      console.log('Creating offer...');
      const offer = await this.pc.createOffer();
      await this.pc.setLocalDescription(offer);
      console.log('Local description set');

      // 6. Send offer to OpenAI's realtime API
      console.log('Sending offer to OpenAI...');
      const baseUrl = "https://api.openai.com/v1/realtime";
      const model = "gpt-4o-realtime-preview-2024-12-17";

      const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/sdp",
        },
      });

      // 7. Get and set remote description (answer)
      console.log('Received answer from OpenAI');
      const answerSdp = await sdpResponse.text();
      const answer: RTCSessionDescriptionInit = {
        type: "answer",
        sdp: answerSdp,
      };
      await this.pc.setRemoteDescription(answer);
      console.log('Remote description set');

      // 8. Send initial session update
      console.log('Sending session update...');
      await this.updateSession(agentInstructions);
      console.log('Session update sent');

      return true;
    } catch (error) {
      console.error("Error starting call:", error);
      throw error;
    }
  }

  private setupDataChannelHandlers() {
    if (!this.dc) return;

    this.dc.addEventListener("open", () => {
      console.log("Data channel opened");
    });

    this.dc.addEventListener("close", () => {
      console.log("Data channel closed");
    });

    this.dc.addEventListener("error", (error) => {
      console.error("Data channel error:", error);
    });

    this.dc.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      console.log('Received data channel message:', data);
      
      // Log specific event types
      switch (data.type) {
        case 'conversation.item.create':
          console.log('New conversation item:', data.item);
          break;
        case 'transcription':
          console.log('Transcription:', data.text);
          break;
        case 'function.call':
          console.log('Function call:', data.function);
          break;
        case 'response.create':
          console.log('Response created');
          break;
        case 'response.done':
          console.log('Response completed');
          break;
      }

      if (this.onMessageCallback) {
        this.onMessageCallback(data);
      }
    });
  }

  async updateSession(instructions: string) {
    const sessionUpdateEvent: WebRTCEvent = {
      type: "session.update",
      session: {
        modalities: ["text", "audio"],
        instructions,
        voice: "sage",
        input_audio_transcription: { model: "whisper-1" },
        turn_detection: {
          type: "server_vad",
          threshold: 0.9,
          prefix_padding_ms: 300,
          silence_duration_ms: 500,
          create_response: true
        },
        tools: []
      }
    };

    console.log('Sending session update event:', sessionUpdateEvent);
    this.sendEvent(sessionUpdateEvent);
  }

  sendEvent(event: WebRTCEvent) {
    if (this.dc?.readyState === "open") {
      console.log('Sending event:', event);
      this.dc.send(JSON.stringify(event));
    } else {
      console.error("Cannot send event - data channel not open");
    }
  }

  async endCall() {
    console.log('Ending call...');
    if (this.pc) {
      this.pc.getSenders().forEach((sender) => {
        if (sender.track) {
          sender.track.stop();
        }
      });
      this.pc.close();
      this.pc = null;
    }
    this.dc = null;
    console.log('Call ended');
  }
} 