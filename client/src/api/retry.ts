import { AxiosError } from 'axios';

export interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  retryableStatusCodes: number[];
}

export async function withRetry(error: AxiosError, config: RetryConfig): Promise<any> {
  if (!error.response || !config.retryableStatusCodes.includes(error.response.status)) {
    throw error;
  }

  const retryCount = (error.config as any).__retryCount || 0;
  if (retryCount >= config.maxRetries) {
    throw error;
  }

  // Exponential backoff
  const delay = config.retryDelay * Math.pow(2, retryCount);
  await new Promise(resolve => setTimeout(resolve, delay));

  // Update retry count
  (error.config as any).__retryCount = retryCount + 1;

  // Retry the request
  return error.config;
} 