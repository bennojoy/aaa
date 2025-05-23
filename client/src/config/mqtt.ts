export const MQTT_CONFIG = {
  host: 'localhost',
  port: '8083',
  path: '/mqtt',
  protocol: 'ws',
  keepalive: 60,
  connectTimeout: 30 * 1000,
  rejectUnauthorized: false
} as const; 