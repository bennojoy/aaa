/**
 * Logging utility for the application
 * Supports different log levels and environments (development/production)
 */

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

interface LogConfig {
  level: LogLevel;
  endpoint?: string;
  environment: 'development' | 'production';
}

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: any;
  context?: string;
  trace_id?: string;
}

class Logger {
  private config: LogConfig;
  private static instance: Logger;
  private currentTraceId?: string;

  private constructor() {
    this.config = {
      level: LogLevel.INFO,
      environment: 'development',
    };
  }

  /**
   * Get the singleton instance of the logger
   */
  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  /**
   * Set the current trace ID for correlation
   * @param traceId - The trace ID to set
   */
  public setTraceId(traceId: string): void {
    this.currentTraceId = traceId;
  }

  /**
   * Clear the current trace ID
   */
  public clearTraceId(): void {
    this.currentTraceId = undefined;
  }

  /**
   * Configure the logger with custom settings
   * @param config - Configuration object for the logger
   */
  public configure(config: Partial<LogConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Create a log entry with the specified level
   * @param level - The log level
   * @param message - The log message
   * @param data - Optional data to include in the log
   * @param context - Optional context for the log entry
   * @param traceId - Optional trace ID to override the current one
   */
  private createLogEntry(
    level: LogLevel,
    message: string,
    data?: any,
    context?: string,
    traceId?: string
  ): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      data,
      context,
      trace_id: traceId || this.currentTraceId,
    };
  }

  /**
   * Send log entry to the configured endpoint in production
   * @param entry - The log entry to send
   */
  private async sendToEndpoint(entry: LogEntry): Promise<void> {
    if (this.config.endpoint) {
      try {
        await fetch(this.config.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(entry),
        });
      } catch (error) {
        console.error('Failed to send log to endpoint:', error);
      }
    }
  }

  /**
   * Log a debug message
   * @param message - The message to log
   * @param data - Optional data to include
   * @param context - Optional context
   * @param traceId - Optional trace ID to override the current one
   */
  public debug(message: string, data?: any, context?: string, traceId?: string): void {
    if (this.config.level === LogLevel.DEBUG) {
      const entry = this.createLogEntry(LogLevel.DEBUG, message, data, context, traceId);
      if (this.config.environment === 'development') {
        console.debug(
          `[${entry.timestamp}] ${entry.level}${entry.trace_id ? ` [${entry.trace_id}]` : ''}: ${entry.message}`,
          entry.data || ''
        );
      } else {
        this.sendToEndpoint(entry);
      }
    }
  }

  /**
   * Log an info message
   * @param message - The message to log
   * @param data - Optional data to include
   * @param context - Optional context
   * @param traceId - Optional trace ID to override the current one
   */
  public info(message: string, data?: any, context?: string, traceId?: string): void {
    if ([LogLevel.DEBUG, LogLevel.INFO].includes(this.config.level)) {
      const entry = this.createLogEntry(LogLevel.INFO, message, data, context, traceId);
      if (this.config.environment === 'development') {
        console.info(
          `[${entry.timestamp}] ${entry.level}${entry.trace_id ? ` [${entry.trace_id}]` : ''}: ${entry.message}`,
          entry.data || ''
        );
      } else {
        this.sendToEndpoint(entry);
      }
    }
  }

  /**
   * Log a warning message
   * @param message - The message to log
   * @param data - Optional data to include
   * @param context - Optional context
   * @param traceId - Optional trace ID to override the current one
   */
  public warn(message: string, data?: any, context?: string, traceId?: string): void {
    if ([LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARN].includes(this.config.level)) {
      const entry = this.createLogEntry(LogLevel.WARN, message, data, context, traceId);
      if (this.config.environment === 'development') {
        console.warn(
          `[${entry.timestamp}] ${entry.level}${entry.trace_id ? ` [${entry.trace_id}]` : ''}: ${entry.message}`,
          entry.data || ''
        );
      } else {
        this.sendToEndpoint(entry);
      }
    }
  }

  /**
   * Log an error message
   * @param message - The message to log
   * @param error - The error object or data
   * @param context - Optional context
   * @param traceId - Optional trace ID to override the current one
   */
  public error(message: string, error?: any, context?: string, traceId?: string): void {
    const entry = this.createLogEntry(LogLevel.ERROR, message, error, context, traceId);
    if (this.config.environment === 'development') {
      console.error(
        `[${entry.timestamp}] ${entry.level}${entry.trace_id ? ` [${entry.trace_id}]` : ''}: ${entry.message}`,
        entry.data || ''
      );
    } else {
      this.sendToEndpoint(entry);
    }
  }
}

// Export a singleton instance
export const logger = Logger.getInstance(); 