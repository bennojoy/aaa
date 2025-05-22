import axios, { AxiosInstance } from 'axios';
import { getTraceId } from '../utils/trace';
import { logger } from '../utils/logger';
import { storage } from '../utils/storage';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const axiosInstance: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include trace ID and auth token
axiosInstance.interceptors.request.use(
  async (config) => {
    const traceId = getTraceId();
    config.headers['X-Trace-ID'] = traceId;

    // Add auth token if available
    const token = await storage.getToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }

    logger.debug('API Request', {
      url: config.url,
      method: config.method,
      traceId,
      hasAuth: !!token,
    }, 'api');
    return config;
  },
  (error) => {
    logger.error('API Request Error', error, 'api');
    return Promise.reject(error);
  }
);

// Add response interceptor to log responses
axiosInstance.interceptors.response.use(
  (response) => {
    const traceId = response.headers['x-trace-id'];
    logger.debug('API Response', {
      url: response.config.url,
      status: response.status,
      traceId,
    }, 'api');
    return response;
  },
  (error) => {
    const traceId = error.response?.headers?.['x-trace-id'];
    logger.error('API Response Error', {
      url: error.config?.url,
      status: error.response?.status,
      error: error.message,
      traceId,
    }, 'api');
    return Promise.reject(error);
  }
);

// Export the configured axios instance
export const apiClient = axiosInstance; 