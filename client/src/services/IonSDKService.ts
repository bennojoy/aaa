import { Client, LocalStream } from 'ion-sdk-js/dist/ion-sdk.min.js';
import { IonSFUJSONRPCSignal } from 'ion-sdk-js/dist/json-rpc.min.js';
import { logger } from '../utils/logger';

export class IonSDKService {
  private client: Client;
  private mediaStream: LocalStream | null = null;
  private isConnected: boolean = false;
  private currentRoomId: string | null = null;
  private currentUserId: string | null = null;

  constructor(wsUrl: string) {
    const signal = new IonSFUJSONRPCSignal(wsUrl);
    const config = {
      codec: 'vp8',
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
      ]
    };
    this.client = new Client(signal, config);

    // Set up event handlers
    this.setupEventHandlers();
  }

  private setupEventHandlers() {
    // Handle new tracks
    this.client.ontrack = (track: MediaStreamTrack, stream: MediaStream) => {
      logger.info('Received new track', { kind: track.kind, streamId: stream.id }, 'ion');
      // You can emit an event or call a callback here to notify the UI
    };

    // Handle data channels
    this.client.ondatachannel = (ev: RTCDataChannelEvent) => {
      logger.info('Data channel created', { label: ev.channel.label }, 'ion');
    };

    // Handle speaker updates
    this.client.onspeaker = (speakers: string[]) => {
      logger.info('Active speakers updated', { speakers }, 'ion');
    };

    // Handle negotiation errors
    this.client.onerrnegotiate = (
      role: string,
      err: Error,
      offer: RTCSessionDescriptionInit,
      answer: RTCSessionDescriptionInit
    ) => {
      logger.error('Negotiation error', { role, err, offer, answer }, 'ion');
    };

    // Handle active layer updates (for simulcast)
    this.client.onactivelayer = (layer: string) => {
      logger.info('Active layer updated', { layer }, 'ion');
    };
  }

  async joinRoom(roomId: string, userId: string): Promise<void> {
    try {
      logger.info('Joining room', { roomId, userId }, 'ion');

      // Join the room
      await this.client.join(roomId, userId);
      this.isConnected = true;
      this.currentRoomId = roomId;
      this.currentUserId = userId;

      logger.info('Successfully joined room', { roomId, userId }, 'ion');
    } catch (error) {
      logger.error('Failed to join room', { error, roomId, userId }, 'ion');
      throw error;
    }
  }

  async setupMediaStream(constraints: MediaStreamConstraints = {
    audio: true,
    video: false
  }): Promise<void> {
    try {
      // Create local stream with HD resolution
      this.mediaStream = await LocalStream.getUserMedia({
        resolution: 'hd',
        codec: 'vp8',
        audio: constraints.audio as boolean,
        video: constraints.video as boolean,
        simulcast: true // Enable simulcast for better quality control
      });

      logger.info('Media stream setup complete', {
        streamId: this.mediaStream.id,
        tracks: this.mediaStream.getTracks().map(t => t.kind)
      }, 'ion');

      // Publish the stream
      this.client.publish(this.mediaStream);

    } catch (error) {
      logger.error('Failed to setup media stream', { error }, 'ion');
      throw error;
    }
  }

  async leaveRoom(): Promise<void> {
    try {
      if (this.mediaStream) {
        // Stop all tracks
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }

      // Leave the room
      this.client.leave();
      this.isConnected = false;
      this.currentRoomId = null;
      this.currentUserId = null;

      logger.info('Left room and cleaned up resources', {}, 'ion');
    } catch (error) {
      logger.error('Error while leaving room', { error }, 'ion');
      throw error;
    }
  }

  async toggleAudio(enabled: boolean): Promise<void> {
    if (!this.mediaStream) {
      throw new Error('No media stream available');
    }

    const audioTrack = this.mediaStream.getAudioTracks()[0];
    if (audioTrack) {
      audioTrack.enabled = enabled;
      logger.info('Audio track state changed', { enabled }, 'ion');
    }
  }

  async toggleVideo(enabled: boolean): Promise<void> {
    if (!this.mediaStream) {
      throw new Error('No media stream available');
    }

    const videoTrack = this.mediaStream.getVideoTracks()[0];
    if (videoTrack) {
      videoTrack.enabled = enabled;
      logger.info('Video track state changed', { enabled }, 'ion');
    }
  }

  async switchCamera(deviceId: string): Promise<void> {
    if (!this.mediaStream) {
      throw new Error('No media stream available');
    }

    try {
      await this.mediaStream.switchDevice('video', deviceId);
      logger.info('Switched camera', { deviceId }, 'ion');
    } catch (error) {
      logger.error('Failed to switch camera', { error, deviceId }, 'ion');
      throw error;
    }
  }

  async switchMicrophone(deviceId: string): Promise<void> {
    if (!this.mediaStream) {
      throw new Error('No media stream available');
    }

    try {
      await this.mediaStream.switchDevice('audio', deviceId);
      logger.info('Switched microphone', { deviceId }, 'ion');
    } catch (error) {
      logger.error('Failed to switch microphone', { error, deviceId }, 'ion');
      throw error;
    }
  }

  getMediaStream(): LocalStream | null {
    return this.mediaStream;
  }

  isRoomConnected(): boolean {
    return this.isConnected;
  }

  close(): void {
    this.client.close();
    this.isConnected = false;
  }
} 