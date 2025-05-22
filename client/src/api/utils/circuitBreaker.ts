import { CircuitState, CircuitBreakerConfig, ApiError } from '../../types/api';

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount: number = 0;
  private lastFailureTime: number = 0;
  private halfOpenTimeoutId?: NodeJS.Timeout;

  constructor(private config: CircuitBreakerConfig) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.isOpen()) {
      throw new ApiError(
        503,
        'CIRCUIT_OPEN',
        'Service temporarily unavailable',
        true
      );
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private isOpen(): boolean {
    if (this.state === CircuitState.OPEN) {
      const now = Date.now();
      if (now - this.lastFailureTime >= this.config.resetTimeout) {
        this.state = CircuitState.HALF_OPEN;
        this.setHalfOpenTimeout();
        return false;
      }
      return true;
    }
    return false;
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.state = CircuitState.CLOSED;
    if (this.halfOpenTimeoutId) {
      clearTimeout(this.halfOpenTimeoutId);
    }
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    if (this.failureCount >= this.config.failureThreshold) {
      this.state = CircuitState.OPEN;
    }
  }

  private setHalfOpenTimeout(): void {
    if (this.halfOpenTimeoutId) {
      clearTimeout(this.halfOpenTimeoutId);
    }
    this.halfOpenTimeoutId = setTimeout(() => {
      this.state = CircuitState.OPEN;
    }, this.config.halfOpenTimeout);
  }

  getState(): CircuitState {
    return this.state;
  }

  getFailureCount(): number {
    return this.failureCount;
  }
} 