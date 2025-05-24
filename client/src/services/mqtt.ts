import mqtt, { MqttClient, IClientOptions } from 'mqtt';
import { logger } from '../utils/logger';
import { getTraceId } from '../utils/trace';
import { AppState, AppStateStatus } from 'react-native';
import { MQTT_CONFIG } from '../config/mqtt';

// Log MQTT library initialization
console.log('MQTT library:', mqtt);
console.log('MQTT library connect function:', mqtt.connect);

// Log MQTT service initialization
console.log('Initializing MQTT service');

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

type ConnectionStatusCallback = (status: ConnectionStatus) => void;
type DisconnectedCallback = () => void;

export interface MQTTService {
  connect: (params: { token: string; userId: string }) => Promise<void>;
  disconnect: () => Promise<void>;
  publish: (topic: string, message: string) => Promise<void>;
  subscribe: (topic: string) => Promise<void>;
  unsubscribe: (topic: string) => Promise<void>;
  isConnected: () => boolean;
  getCurrentUserId: () => string | null;
  setCallbacks: (callbacks: {
    onConnectionStatusChange: (status: ConnectionStatus) => void;
    onDisconnected: () => void;
  }) => void;
}

class MQTTServiceImpl implements MQTTService {
  private client: MqttClient | null = null;
  private messageHandlers: ((topic: string, message: any) => void)[] = [];
  private appStateSubscription: any = null;
  private connectionPromise: Promise<void> | null = null;
  private currentUserId: string | null = null;
  private currentToken: string | null = null;
  private retryCount = 0;
  private maxRetries = 5;
  private baseDelay = 1000; // 1 second
  private maxDelay = 30000; // 30 seconds
  private circuitBreakerOpen = false;
  private circuitBreakerTimeout: NodeJS.Timeout | null = null;
  private lastError: Error | null = null;
  private connectionStatus: ConnectionStatus = 'disconnected';
  private connectionCallbacks: {
    onConnectionStatusChange: (status: ConnectionStatus) => void;
    onDisconnected: () => void;
  } | null = null;

  constructor() {
    console.log('MQTT service constructor called');
    this.appStateSubscription = AppState.addEventListener('change', this.handleAppStateChange);
    
    // Set up connection status callback
    this.setCallbacks({
      onConnectionStatusChange: (status) => {
        const traceId = getTraceId();
        logger.info('MQTT connection status changed', {
          status,
          traceId,
          currentState: {
            hasClient: !!this.client,
            clientState: this.client?.connected ? 'connected' : 'disconnected',
            currentUserId: this.currentUserId
          }
        }, 'mqtt');
      },
      onDisconnected: () => {
        const traceId = getTraceId();
        logger.info('MQTT disconnected', {
          traceId,
          currentState: {
            hasClient: !!this.client,
            clientState: this.client?.connected ? 'connected' : 'disconnected',
            currentUserId: this.currentUserId
          }
        }, 'mqtt');
      }
    });
  }

  public setCallbacks(callbacks: {
    onConnectionStatusChange: (status: ConnectionStatus) => void;
    onDisconnected: () => void;
  }) {
    this.connectionCallbacks = callbacks;
    // Immediately notify of current status
    if (this.connectionStatus) {
      this.connectionCallbacks.onConnectionStatusChange(this.connectionStatus);
    }
  }

  private handleAppStateChange = async (nextAppState: AppStateStatus) => {
    console.log('App state changed:', nextAppState);
    const traceId = getTraceId();
    
    if (nextAppState === 'active' && this.currentUserId && this.currentToken) {
      logger.info('App became active, checking MQTT connection', {
        userId: this.currentUserId,
        hasToken: !!this.currentToken,
        traceId,
        currentState: {
          hasClient: !!this.client,
          clientState: this.client?.connected ? 'connected' : 'disconnected',
          currentUserId: this.currentUserId,
          retryCount: this.retryCount
        }
      }, 'mqtt');
      
      this.connect({ token: this.currentToken, userId: this.currentUserId })
        .catch(error => {
          logger.error('Failed to reconnect MQTT after app became active', {
            error,
            userId: this.currentUserId,
            traceId,
            currentState: {
              hasClient: !!this.client,
              clientState: this.client?.connected ? 'connected' : 'disconnected',
              currentUserId: this.currentUserId,
              retryCount: this.retryCount
            }
          }, 'mqtt');
        });
    }
  };

  private testWebSocketConnection(url: string, traceId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = url;

      console.log('Testing WebSocket connection with:', {
        url: wsUrl,
        hasToken: !!this.currentToken,
        tokenLength: this.currentToken?.length,
        tokenPreview: this.currentToken ? `${this.currentToken.substring(0, 4)}...${this.currentToken.substring(this.currentToken.length - 4)}` : undefined,
        protocol: MQTT_CONFIG.protocol,
        host: MQTT_CONFIG.host,
        port: MQTT_CONFIG.port,
        path: MQTT_CONFIG.path
      });

      logger.info('Testing WebSocket connection', { 
        url: wsUrl, 
        traceId,
        protocol: MQTT_CONFIG.protocol,
        host: MQTT_CONFIG.host,
        port: MQTT_CONFIG.port,
        path: MQTT_CONFIG.path,
        hasToken: !!this.currentToken,
        tokenLength: this.currentToken?.length,
        tokenPreview: this.currentToken ? `${this.currentToken.substring(0, 4)}...${this.currentToken.substring(this.currentToken.length - 4)}` : undefined,
        userAgent: navigator.userAgent
      }, 'mqtt');
      
      const ws = new WebSocket(wsUrl);
      const timeout = setTimeout(() => {
        logger.error('WebSocket connection test timed out', { 
          url: wsUrl, 
          traceId,
          timeout: 5000,
          readyState: ws.readyState,
          protocol: ws.protocol,
          extensions: ws.extensions,
          binaryType: ws.binaryType
        }, 'mqtt');
        ws.close();
        reject(new Error('WebSocket connection test timed out'));
      }, 5000);

      ws.onopen = () => {
        clearTimeout(timeout);
        logger.info('WebSocket connection test successful', { 
          url: wsUrl, 
          traceId,
          protocol: ws.protocol,
          readyState: ws.readyState,
          extensions: ws.extensions,
          binaryType: ws.binaryType,
          userAgent: navigator.userAgent
        }, 'mqtt');
        ws.close();
        resolve();
      };

      ws.onerror = (error) => {
        clearTimeout(timeout);
        const errorDetails = {
          error,
          url: wsUrl,
          traceId,
          readyState: ws.readyState,
          protocol: ws.protocol,
          extensions: ws.extensions,
          binaryType: ws.binaryType,
          userAgent: navigator.userAgent,
          errorEvent: error instanceof Event ? {
            type: error.type,
            bubbles: error.bubbles,
            cancelable: error.cancelable,
            composed: error.composed,
            eventPhase: error.eventPhase,
            isTrusted: error.isTrusted,
            timeStamp: error.timeStamp
          } : error
        };
        console.error('WebSocket connection test failed:', errorDetails);
        logger.error('WebSocket connection test failed', errorDetails, 'mqtt');
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = (event) => {
        logger.info('WebSocket connection closed', {
          url: wsUrl,
          traceId,
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          protocol: ws.protocol,
          extensions: ws.extensions,
          binaryType: ws.binaryType,
          userAgent: navigator.userAgent
        }, 'mqtt');
      };
    });
  }

  private calculateBackoffDelay(): number {
    const delay = Math.min(this.baseDelay * Math.pow(2, this.retryCount), this.maxDelay);
    return delay + Math.random() * 1000; // Add jitter
  }

  private openCircuitBreaker() {
    this.circuitBreakerOpen = true;
    logger.info('Circuit breaker opened', {
      retryCount: this.retryCount,
      lastError: this.lastError?.message
    }, 'mqtt');

    // Reset circuit breaker after 30 seconds
    if (this.circuitBreakerTimeout) {
      clearTimeout(this.circuitBreakerTimeout);
    }
    this.circuitBreakerTimeout = setTimeout(() => {
      this.circuitBreakerOpen = false;
      this.retryCount = 0;
      this.lastError = null;
      logger.info('Circuit breaker reset', null, 'mqtt');
    }, 30000);
  }

  async connect(params: { token: string; userId: string }): Promise<void> {
    const { token, userId } = params;
    const traceId = getTraceId();
    const url = `${MQTT_CONFIG.protocol}://${MQTT_CONFIG.host}:${MQTT_CONFIG.port}${MQTT_CONFIG.path}`;

    // If already connected with same user, resolve immediately
    if (this.client?.connected && this.currentUserId === userId) {
      logger.info('Already connected with same user', {
        userId,
        retryCount: this.retryCount
      }, 'mqtt');
      return Promise.resolve();
    }

    // If there's an ongoing connection attempt, return that promise
    if (this.connectionPromise) {
      logger.info('Connection attempt already in progress', {
        userId,
        currentUserId: this.currentUserId,
        retryCount: this.retryCount
      }, 'mqtt');
      return this.connectionPromise;
    }

    this.connectionPromise = new Promise(async (resolve, reject) => {
      try {
        // Disconnect existing client if any
        if (this.client) {
          await this.disconnect();
        }

        // Set current token and user ID
        this.currentToken = token;
        this.currentUserId = userId;

        logger.info('Creating MQTT client', {
          url,
          userId,
          traceId,
          hasToken: !!token
        }, 'mqtt');

        const options: IClientOptions = {
          clientId: userId,
          username: token,
          password: undefined,
          clean: true,
          path: MQTT_CONFIG.path,
          protocol: MQTT_CONFIG.protocol,
          keepalive: MQTT_CONFIG.keepalive,
          connectTimeout: MQTT_CONFIG.connectTimeout,
          reconnectPeriod: 0, // Disable automatic reconnection
          wsOptions: {
            rejectUnauthorized: false // Allow self-signed certificates in development
          }
        };

        // Create MQTT client
        this.client = mqtt.connect(url, options);

        // Set up connection timeout
        const connectionTimeout = setTimeout(() => {
          if (!this.client?.connected) {
            const error = new Error('MQTT connection timeout');
            this.lastError = error;
            this.retryCount++;
            this.client?.end();
            reject(error);
          }
        }, MQTT_CONFIG.connectTimeout);

        // Set up event handlers
        this.client.on('connect', () => {
          clearTimeout(connectionTimeout);
          this.retryCount = 0;
          this.lastError = null;
          this.connectionStatus = 'connected';
          this.connectionCallbacks?.onConnectionStatusChange('connected');

          logger.info('MQTT Connected', {
            userId,
            url,
            traceId
          }, 'mqtt');

          resolve();
        });

        this.client.on('error', (error) => {
          clearTimeout(connectionTimeout);
          this.lastError = error;
          this.retryCount++;
          this.connectionStatus = 'error';
          this.connectionCallbacks?.onConnectionStatusChange('error');

          logger.error('MQTT Error', {
            error,
            url,
            userId,
            traceId
          }, 'mqtt');

          reject(error);
        });

        this.client.on('close', () => {
          clearTimeout(connectionTimeout);
          this.connectionStatus = 'disconnected';
          this.connectionCallbacks?.onConnectionStatusChange('disconnected');
          this.connectionCallbacks?.onDisconnected();

          logger.info('MQTT Connection Closed', {
            url,
            userId,
            traceId
          }, 'mqtt');
        });

        // Set up message handler
        this.client.on('message', (topic, message) => {
          try {
            const messageStr = message.toString();
            const parsedMessage = JSON.parse(messageStr);
            
            logger.info('MQTT message received', {
              topic,
              message: parsedMessage,
              traceId: getTraceId()
            }, 'mqtt');
            
            this.messageHandlers.forEach(handler => {
              try {
                handler(topic, parsedMessage);
              } catch (error) {
                logger.error('Error in message handler', {
                  error,
                  topic,
                  message: parsedMessage,
                  traceId: getTraceId()
                }, 'mqtt');
              }
            });
          } catch (error) {
            logger.error('Error parsing MQTT message', {
              error,
              topic,
              message: message.toString(),
              traceId: getTraceId()
            }, 'mqtt');
          }
        });

      } catch (error) {
        logger.error('MQTT Connection Error', {
          error,
          url,
          userId,
          traceId
        }, 'mqtt');
        
        this.connectionStatus = 'disconnected';
        this.connectionCallbacks?.onConnectionStatusChange('disconnected');
        reject(error);
      } finally {
        this.connectionPromise = null;
      }
    });

    return this.connectionPromise;
  }

  async subscribe(topic: string): Promise<void> {
    if (!this.client) {
      throw new Error('MQTT client not initialized');
    }
    return new Promise((resolve, reject) => {
      this.client?.subscribe(topic, (error) => {
        if (error) {
          reject(error);
        } else {
          resolve();
        }
      });
    });
  }

  async unsubscribe(topic: string): Promise<void> {
    if (!this.client) {
      throw new Error('MQTT client not initialized');
    }
    return new Promise((resolve, reject) => {
      this.client?.unsubscribe(topic, (error) => {
        if (error) {
          reject(error);
        } else {
          resolve();
        }
      });
    });
  }

  publish(topic: string, message: any): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.client) {
        reject(new Error('No MQTT client available'));
        return;
      }

      const traceId = getTraceId();
      logger.info('Publishing message', { 
        topic, 
        message,
        traceId,
        userId: this.currentUserId
      }, 'mqtt');

      this.client.publish(topic, message, (err) => {
        if (err) {
          logger.error('Failed to publish message', { 
            error: err, 
            topic, 
            message,
            traceId,
            userId: this.currentUserId
          }, 'mqtt');
          reject(err);
        } else {
          logger.info('Successfully published message', { 
            topic, 
            message,
            traceId,
            userId: this.currentUserId
          }, 'mqtt');
          resolve();
        }
      });
    });
  }

  addMessageHandler(handler: (topic: string, message: any) => void) {
    logger.info('Adding message handler', { 
      handlerCount: this.messageHandlers.length,
      userId: this.currentUserId
    }, 'mqtt');
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler: (topic: string, message: any) => void) {
    logger.info('Removing message handler', { 
      handlerCount: this.messageHandlers.length,
      userId: this.currentUserId
    }, 'mqtt');
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }

  async disconnect(): Promise<void> {
    if (this.client) {
      return new Promise((resolve) => {
        this.client?.end(false, () => {
          this.client = null;
          this.currentUserId = null;
          this.currentToken = null;
          this.connectionStatus = 'disconnected';
          this.connectionCallbacks?.onConnectionStatusChange('disconnected');
          resolve();
        });
      });
    }
  }

  cleanup() {
    logger.info('Cleaning up MQTT service', { 
      userId: this.currentUserId,
      hasClient: !!this.client,
      clientState: this.client?.connected ? 'connected' : 'disconnected'
    }, 'mqtt');
    this.disconnect();
    if (this.appStateSubscription) {
      this.appStateSubscription.remove();
      this.appStateSubscription = null;
    }
  }

  public isConnected(): boolean {
    return this.client?.connected === true;
  }

  public getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  getCurrentUserId(): string | null {
    return this.currentUserId;
  }
}

export const mqttService = new MQTTServiceImpl(); 