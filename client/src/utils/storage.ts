import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { User } from '../types/auth';

class Storage {
  private async getItem(key: string): Promise<string | null> {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    return SecureStore.getItemAsync(key);
  }

  private async setItem(key: string, value: string): Promise<void> {
    if (Platform.OS === 'web') {
      localStorage.setItem(key, value);
      return;
    }
    await SecureStore.setItemAsync(key, value);
  }

  private async removeItem(key: string): Promise<void> {
    if (Platform.OS === 'web') {
      localStorage.removeItem(key);
      return;
    }
    await SecureStore.deleteItemAsync(key);
  }

  async getToken(): Promise<string | null> {
    return this.getItem('token');
  }

  async setToken(token: string): Promise<void> {
    await this.setItem('token', token);
  }

  async removeToken(): Promise<void> {
    await this.removeItem('token');
  }

  async getUserData(): Promise<User | null> {
    const data = await this.getItem('userData');
    return data ? JSON.parse(data) : null;
  }

  async setUserData(user: User): Promise<void> {
    await this.setItem('userData', JSON.stringify(user));
  }

  async removeUserData(): Promise<void> {
    await this.removeItem('userData');
  }

  async clear(): Promise<void> {
    await this.removeToken();
    await this.removeUserData();
  }
}

export const storage = new Storage(); 