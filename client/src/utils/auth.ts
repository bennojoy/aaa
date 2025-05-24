import { apiClient } from '../api/client';
import { storage } from './storage';
import { logger } from './logger';
import { getTraceId } from './trace';

/**
 * Validates the current token
 * @returns {Promise<boolean>} True if token is valid, false otherwise
 */
export const validateToken = async (): Promise<boolean> => {
  const traceId = getTraceId();
  try {
    const token = await storage.getToken();
    if (!token) {
      logger.warn('No token found during validation', { traceId }, 'auth');
      return false;
    }

    await apiClient.get('/api/v1/auth/verify');
    logger.info('Token validated successfully', { traceId }, 'auth');
    return true;
  } catch (error: any) {
    logger.error('Token validation failed', {
      error: error.message,
      status: error.response?.status,
      traceId
    }, 'auth');
    return false;
  }
};

/**
 * Checks if token is expired
 * @param token - The JWT token to check
 * @returns {boolean} True if token is expired, false otherwise
 */
export const isTokenExpired = (token: string): boolean => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));

    const { exp } = JSON.parse(jsonPayload);
    return exp < Date.now() / 1000;
  } catch (error) {
    logger.error('Error checking token expiration', { error }, 'auth');
    return true; // If we can't decode the token, consider it expired
  }
}; 