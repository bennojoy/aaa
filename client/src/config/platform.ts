import { Platform } from 'react-native';

interface PlatformConfig {
  apiBaseUrl: string;
  websocketUrl: string;
  timeout: number;
}

const getPlatformConfig = (): PlatformConfig => {
  // Development configuration
  if (__DEV__) {
    return {
      apiBaseUrl: 'http://localhost:8000/api/v1',
      websocketUrl: 'ws://localhost:8000/ws',
      timeout: 30000
    };
  }

  // Production configuration based on platform
  switch (Platform.OS) {
    case 'ios':
      return {
        apiBaseUrl: 'https://api.yourapp.com/api/v1',
        websocketUrl: 'wss://api.yourapp.com/ws',
        timeout: 30000
      };
    case 'android':
      return {
        apiBaseUrl: 'https://api.yourapp.com/api/v1',
        websocketUrl: 'wss://api.yourapp.com/ws',
        timeout: 30000
      };
    case 'web':
      return {
        apiBaseUrl: '/api/v1', // For web, we'll use relative paths
        websocketUrl: 'wss://api.yourapp.com/ws',
        timeout: 30000
      };
    default:
      throw new Error(`Unsupported platform: ${Platform.OS}`);
  }
};

export const platformConfig = getPlatformConfig(); 