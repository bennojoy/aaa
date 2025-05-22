import { LogLevel } from '../utils/logger';

const isDevelopment = process.env.NODE_ENV === 'development';

export const loggerConfig = {
  level: isDevelopment ? LogLevel.DEBUG : LogLevel.INFO,
  environment: isDevelopment ? 'development' : 'production',
  endpoint: isDevelopment ? undefined : process.env.LOG_ENDPOINT,
}; 