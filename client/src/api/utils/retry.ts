import { RetryConfig, ApiError } from '../../types/api';

export class Retry {
  constructor(private config: RetryConfig) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    let lastError: Error;
    
    for (let attempt = 0; attempt <= this.config.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;
        if (!this.shouldRetry(error)) {
          throw error;
        }
        if (attempt < this.config.maxRetries) {
          await this.delay(attempt);
        }
      }
    }
    
    throw lastError;
  }

  private shouldRetry(error: any): boolean {
    if (error instanceof ApiError) {
      return error.retryable;
    }
    
    if (error.response) {
      return this.config.retryableStatusCodes.includes(error.response.status);
    }
    
    // Retry on network errors
    return true;
  }

  private delay(attempt: number): Promise<void> {
    // Exponential backoff with jitter
    const delay = Math.min(
      this.config.retryDelay * Math.pow(2, attempt),
      30000 // Max delay of 30 seconds
    );
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    
    return new Promise(resolve => 
      setTimeout(resolve, delay + jitter)
    );
  }
} 