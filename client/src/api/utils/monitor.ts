import { ApiMetrics } from '../../types/api';

export class ApiMonitor {
  private metrics: ApiMetrics = {
    totalRequests: 0,
    failedRequests: 0,
    circuitBreakerTrips: 0,
    averageResponseTime: 0
  };

  private responseTimes: number[] = [];

  logRequest(success: boolean, responseTime: number): void {
    this.metrics.totalRequests++;
    if (!success) {
      this.metrics.failedRequests++;
    }
    this.updateAverageResponseTime(responseTime);
  }

  logCircuitBreakerTrip(): void {
    this.metrics.circuitBreakerTrips++;
  }

  private updateAverageResponseTime(responseTime: number): void {
    this.responseTimes.push(responseTime);
    if (this.responseTimes.length > 100) {
      this.responseTimes.shift(); // Keep only last 100 measurements
    }
    this.metrics.averageResponseTime = 
      this.responseTimes.reduce((a, b) => a + b, 0) / this.responseTimes.length;
  }

  getMetrics(): ApiMetrics {
    return { ...this.metrics };
  }

  resetMetrics(): void {
    this.metrics = {
      totalRequests: 0,
      failedRequests: 0,
      circuitBreakerTrips: 0,
      averageResponseTime: 0
    };
    this.responseTimes = [];
  }
} 