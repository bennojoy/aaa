import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { logger } from './logger';
import { getTraceId } from './trace';
import { User } from '../types/auth';

const TOKEN_KEY = 'auth_token';
const USER_DATA_KEY = 'user_data';

// Web storage fallback
const webStorage = {
  getItem: (key: string): string | null => {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.error('Error accessing localStorage:', error);
      return null;
    }
  },
  setItem: (key: string, value: string): void => {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      console.error('Error setting localStorage:', error);
    }
  },
  removeItem: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  }
};

export const storage = {
  async setToken(token: string): Promise<void> {
    const traceId = getTraceId();
    try {
      if (Platform.OS === 'web') {
        webStorage.setItem(TOKEN_KEY, token);
      } else {
        await SecureStore.setItemAsync(TOKEN_KEY, token);
      }
      logger.info('Token stored successfully', { traceId }, 'storage');
    } catch (error) {
      logger.error('Error storing token', { error, traceId }, 'storage');
      throw error;
    }
  },

  async getToken(): Promise<string | null> {
    const traceId = getTraceId();
    try {
      let token: string | null;
      if (Platform.OS === 'web') {
        token = webStorage.getItem(TOKEN_KEY);
      } else {
        token = await SecureStore.getItemAsync(TOKEN_KEY);
      }
      if (!token) {
        logger.warn('No token found', { traceId }, 'storage');
      }
      return token;
    } catch (error) {
      logger.error('Error retrieving token', { error, traceId }, 'storage');
      return null;
    }
  },

  async removeToken(): Promise<void> {
    const traceId = getTraceId();
    try {
      if (Platform.OS === 'web') {
        webStorage.removeItem(TOKEN_KEY);
      } else {
        await SecureStore.deleteItemAsync(TOKEN_KEY);
      }
      logger.info('Token removed successfully', { traceId }, 'storage');
    } catch (error) {
      logger.error('Error removing token', { error, traceId }, 'storage');
      throw error;
    }
  },

  async setUserData(user: User): Promise<void> {
    const traceId = getTraceId();
    try {
      const userData = JSON.stringify(user);
      if (Platform.OS === 'web') {
        webStorage.setItem(USER_DATA_KEY, userData);
      } else {
        await SecureStore.setItemAsync(USER_DATA_KEY, userData);
      }
      logger.info('User data stored successfully', { traceId }, 'storage');
    } catch (error) {
      logger.error('Error storing user data', { error, traceId }, 'storage');
      throw error;
    }
  },

  async getUserData(): Promise<User | null> {
    const traceId = getTraceId();
    try {
      let userData: string | null;
      if (Platform.OS === 'web') {
        userData = webStorage.getItem(USER_DATA_KEY);
      } else {
        userData = await SecureStore.getItemAsync(USER_DATA_KEY);
      }
      if (!userData) {
        logger.warn('No user data found', { traceId }, 'storage');
        return null;
      }
      return JSON.parse(userData);
    } catch (error) {
      logger.error('Error retrieving user data', { error, traceId }, 'storage');
      return null;
    }
  },

  async clear(): Promise<void> {
    const traceId = getTraceId();
    try {
      if (Platform.OS === 'web') {
        webStorage.removeItem(TOKEN_KEY);
        webStorage.removeItem(USER_DATA_KEY);
      } else {
        await Promise.all([
          SecureStore.deleteItemAsync(TOKEN_KEY),
          SecureStore.deleteItemAsync(USER_DATA_KEY)
        ]);
      }
      logger.info('Storage cleared successfully', { traceId }, 'storage');
    } catch (error) {
      logger.error('Error clearing storage', { error, traceId }, 'storage');
      throw error;
    }
  }
}; 