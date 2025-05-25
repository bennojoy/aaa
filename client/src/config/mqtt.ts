export const MQTT_CONFIG = {
  brokerUrl: 'ws://localhost:8083',
  path: '/mqtt',
  protocol: 'ws',
  keepalive: 60, // 60 seconds keep-alive
  connectTimeout: 30000,
  reconnectPeriod: 1000, // 1 second initial delay
  maxRetries: 10,
  minRetryInterval: 1000, // 1 second
  maxRetryInterval: 30000, // 30 seconds
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
  }
}; 