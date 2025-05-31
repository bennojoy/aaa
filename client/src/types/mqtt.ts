import { MqttClient } from 'mqtt';

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error' | 'retry_limit_reached';

export type ConnectionStatusCallback = (status: ConnectionStatus) => void;
export type DisconnectedCallback = () => void;

export interface MqttMessage {
  topic: string;
  payload: any;
  timestamp: number;
}

export interface ConnectionHistory {
  timestamp: number;
  status: ConnectionStatus;
  reason?: string;
  latency?: number;
}

export interface ConnectionCallbacks {
  onConnectionStatusChange?: (status: ConnectionStatus) => void;
  onDisconnected?: () => void;
  onMessage?: (topic: string, message: string) => void;
  onError?: (error: Error) => void;
}

export interface MQTTService {
  connect(params: { token: string; userId: string }): Promise<void>;
  disconnect(): Promise<void>;
  publish(topic: string, message: string): Promise<void>;
  subscribe(topic: string): Promise<void>;
  unsubscribe(topic: string): Promise<void>;
  getConnectionStatus(): ConnectionStatus;
  getConnectionQuality(): 'good' | 'fair' | 'poor';
  getRetryCount(): number;
  getLastError(): Error | null;
  getConnectionHistory(): ConnectionHistory[];
  setConnectionCallbacks(callbacks: ConnectionCallbacks): void;
}

// MQTT Configuration
export const MQTT_CONFIG = {
  brokerUrl: 'ws://localhost:8083',
  path: '/mqtt',
  protocol: 'ws',
  keepalive: 30, // 30 seconds keep-alive
  connectTimeout: 30000,
  reconnectPeriod: 0, // Disable automatic reconnection, we'll handle it manually
  // Retry configuration
  retry: {
    maxRetries: 10,
    minRetryInterval: 1000, // 1 second
    maxRetryInterval: 30000, // 30 seconds
    jitter: 1000, // Maximum jitter in milliseconds
  },
  clean: true,
  // Add connection quality thresholds
  connectionQuality: {
    good: 1000, // ms
    fair: 2000, // ms
    poor: 3000  // ms
  },
  // Add topic configuration
  topics: {
    publish: {
      messages: 'messages/to_room'  // Single topic for all message publishing
    },
    subscribe: {
      user: (userId: string) => `user/${userId}/message`  // Function to generate user-specific topic
    }
  },
  messageHistory: {
    maxMessages: 10
  },
  ai: {
    senderId: '2d90c5f0-f3ca-4fb4-a726-ac90316635d6'
  }
} as const; 