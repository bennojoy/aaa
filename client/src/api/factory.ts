import axios from 'axios';
import { storage } from '../utils/storage';

const BASE_URL = 'http://localhost:8000'; // Change this to your API URL

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to add the auth token
apiClient.interceptors.request.use(
  async (config) => {
    const token = await storage.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      await storage.clearToken();
      await storage.clearUserData();
      // You might want to navigate to login screen here
    }
    return Promise.reject(error);
  }
); 