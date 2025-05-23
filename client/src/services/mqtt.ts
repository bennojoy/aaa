import mqtt, { MqttClient, IClientOptions } from 'mqtt';
import { logger } from '../utils/logger';
import { getTraceId } from '../utils/trace';
import { AppState, AppStateStatus } from 'react-native';
import { store } from '../store';
import { disconnected } from '../store/mqttSlice';
import { setConnectionStatus } from '../store/chatSlice';
import { MQTT_CONFIG } from '../config/mqtt';

// Log MQTT library initialization
console.log('MQTT library:', mqtt);
console.log('MQTT library connect function:', mqtt.connect);

class MQTTService {
  private client: MqttClient | null = null;
  private messageHandlers: ((topic: string, message: any) => void)[] = [];
  private appStateSubscription: any = null;
  private connectionPromise: Promise<void> | null = null;
  private currentUserId: string | null = null;
  private currentToken: string | null = null;

  constructor() {
    logger.info('MQTT Service initialized', {
      config: MQTT_CONFIG
    }, 'mqtt');
    this.appStateSubscription = AppState.addEventListener('change', this.handleAppStateChange);
  }

  private handleAppStateChange = async (nextAppState: AppStateStatus) => {
    logger.info('App state changed', { 
      nextAppState,
      hasClient: !!this.client,
      clientState: this.client?.connected ? 'connected' : 'disconnected',
      userId: this.currentUserId
    }, 'mqtt');

    // Only disconnect if we're explicitly closing the app
    if (nextAppState === 'inactive' && this.client) {
      logger.info('App becoming inactive, disconnecting MQTT', {
        clientState: this.client.connected ? 'connected' : 'disconnected',
        userId: this.currentUserId
      }, 'mqtt');
      this.disconnect();
    } else if (nextAppState === 'active' && this.currentUserId && this.currentToken && !this.client?.connected) {
      logger.info('App becoming active, reconnecting MQTT if needed', {
        userId: this.currentUserId,
        isConnected: this.client?.connected
      }, 'mqtt');
      this.connect(this.currentToken, this.currentUserId).catch(err => {
        logger.error('Failed to reconnect MQTT on app foreground', {
          error: err,
          userId: this.currentUserId
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

  async connect(token: string, userId: string): Promise<void> {
    // If there's an ongoing connection attempt, return that promise
    if (this.connectionPromise) {
      logger.info('Connection attempt already in progress', {
        userId,
        currentUserId: this.currentUserId,
        hasToken: !!token,
        tokenLength: token?.length,
        tokenPreview: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
        traceId: getTraceId()
      }, 'mqtt');
      return this.connectionPromise;
    }

    // If already connected with same user, resolve immediately
    if (this.client?.connected && this.currentUserId === userId) {
      logger.info('Already connected with same user', {
        userId,
        hasToken: !!token,
        tokenLength: token?.length,
        tokenPreview: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
        traceId: getTraceId()
      }, 'mqtt');
      return Promise.resolve();
    }

    this.connectionPromise = new Promise(async (resolve, reject) => {
      const traceId = getTraceId();
      const url = `${MQTT_CONFIG.protocol}://${MQTT_CONFIG.host}:${MQTT_CONFIG.port}${MQTT_CONFIG.path}`;
      
      // Set current token and user ID before connecting
      this.currentToken = token;
      this.currentUserId = userId;
      
      console.log('MQTT connect called with:', {
        url,
        userId,
        hasToken: !!token,
        tokenLength: token?.length,
        tokenPreview: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
        config: MQTT_CONFIG
      });

      logger.info('MQTT connect called', {
        config: MQTT_CONFIG,
        userId,
        hasExistingClient: !!this.client,
        existingClientState: this.client?.connected ? 'connected' : 'disconnected',
        currentUserId: this.currentUserId,
        traceId,
        url,
        hasToken: !!token,
        tokenLength: token?.length,
        tokenPreview: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined
      }, 'mqtt');
      
      try {
        if (this.client) {
          logger.info('Disconnecting existing client before reconnecting', {
            userId,
            currentUserId: this.currentUserId,
            clientState: this.client.connected ? 'connected' : 'disconnected',
            hasToken: !!token,
            tokenLength: token?.length,
            tokenPreview: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
            traceId
          }, 'mqtt');
          this.disconnect();
        }
        
        const options: IClientOptions = {
          clientId: userId, // Use userId as clientId
          username: token,
          password: undefined,
          clean: true, // Use clean session for better connection management
          path: MQTT_CONFIG.path,
          protocol: MQTT_CONFIG.protocol,
          keepalive: MQTT_CONFIG.keepalive,
          connectTimeout: MQTT_CONFIG.connectTimeout
        };

        console.log('Creating MQTT client with options:', {
          ...options,
          password: '***',
          username: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
          hasToken: !!token,
          tokenLength: token?.length
        });

        logger.info('Creating MQTT client', { 
          url, 
          options: {
            ...options,
            password: '***',
            username: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
            hasToken: !!token,
            tokenLength: token?.length
          },
          traceId
        }, 'mqtt');
        
        // Create MQTT client
        try {
          console.log('Creating MQTT client instance');
          this.client = mqtt.connect(url, options);
          console.log('MQTT client instance created');

          // Set up connection timeout
          const connectionTimeout = setTimeout(() => {
            if (!this.client?.connected) {
              console.error('MQTT connection timeout');
              logger.error('MQTT connection timeout', {
                url,
                userId,
                traceId,
                timeout: MQTT_CONFIG.connectTimeout
              }, 'mqtt');
              this.client?.end();
              reject(new Error('MQTT connection timeout'));
            }
          }, MQTT_CONFIG.connectTimeout);

          this.client.on('connect', () => {
            console.log('MQTT client connected');
            clearTimeout(connectionTimeout);
            logger.info('MQTT Connected', { 
              userId, 
              url,
              clientState: this.client?.connected ? 'connected' : 'disconnected',
              traceId
            }, 'mqtt');
            resolve();
          });

          this.client.on('error', (error) => {
            console.error('MQTT client error:', error);
            clearTimeout(connectionTimeout);
            logger.error('MQTT Error', { 
              error,
              url,
              clientState: this.client?.connected ? 'connected' : 'disconnected',
              userId: this.currentUserId,
              traceId
            }, 'mqtt');
            store.dispatch(disconnected());
            store.dispatch(setConnectionStatus('disconnected'));
            reject(error);
          });

          this.client.on('close', () => {
            clearTimeout(connectionTimeout);
            logger.info('MQTT Connection Closed', { 
              url,
              clientState: this.client?.connected ? 'connected' : 'disconnected',
              userId: this.currentUserId,
              traceId
            }, 'mqtt');
            store.dispatch(disconnected());
            store.dispatch(setConnectionStatus('disconnected'));
          });

          this.client.on('offline', () => {
            clearTimeout(connectionTimeout);
            logger.info('MQTT Client Offline', {
              url,
              clientState: this.client?.connected ? 'connected' : 'disconnected',
              userId: this.currentUserId,
              traceId
            }, 'mqtt');
            store.dispatch(disconnected());
            store.dispatch(setConnectionStatus('disconnected'));
          });

          this.client.on('reconnect', () => {
            logger.info('MQTT Client Reconnecting', {
              url,
              clientState: this.client?.connected ? 'connected' : 'disconnected',
              userId: this.currentUserId,
              traceId
            }, 'mqtt');
            store.dispatch(setConnectionStatus('connecting'));
          });

          this.client.on('end', () => {
            clearTimeout(connectionTimeout);
            logger.info('MQTT Client Ended', {
              url,
              clientState: this.client?.connected ? 'connected' : 'disconnected',
              userId: this.currentUserId,
              traceId
            }, 'mqtt');
            store.dispatch(disconnected());
            store.dispatch(setConnectionStatus('disconnected'));
          });

        } catch (error) {
          logger.error('Failed to create MQTT client', {
            error,
            url,
            userId,
            traceId
          }, 'mqtt');
          throw error;
        }

      } catch (error) {
        logger.error('MQTT Connection Error', { 
          error,
          url,
          userId: this.currentUserId,
          traceId
        }, 'mqtt');
        store.dispatch(disconnected());
        store.dispatch(setConnectionStatus('disconnected'));
        reject(error);
      } finally {
        this.connectionPromise = null;
      }
    });

    return this.connectionPromise;
  }

  subscribe(topic: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.client) {
        reject(new Error('No MQTT client available'));
        return;
      }

      const traceId = getTraceId();
      logger.info('Subscribing to topic', { 
        topic, 
        traceId,
        userId: this.currentUserId
      }, 'mqtt');

      this.client.subscribe(topic, (err) => {
        if (err) {
          logger.error('Failed to subscribe to topic', { 
            error: err, 
            topic, 
            traceId,
            userId: this.currentUserId
          }, 'mqtt');
          reject(err);
        } else {
          logger.info('Successfully subscribed to topic', { 
            topic, 
            traceId,
            userId: this.currentUserId
          }, 'mqtt');
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

  disconnect() {
    if (this.client) {
      logger.info('Disconnecting MQTT client', { 
        userId: this.currentUserId,
        clientState: this.client.connected ? 'connected' : 'disconnected'
      }, 'mqtt');
      this.client.end();
      this.client = null;
      this.currentUserId = null;
      this.currentToken = null;
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
}

export const mqttService = new MQTTService(); 