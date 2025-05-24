import React, { useEffect } from 'react';
import { connect } from '../../store/mqttSlice';
import { storage } from '../../utils/storage';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { store } from '../../store';
import { useSelector } from 'react-redux';
import { mqttService } from '../../services/mqtt';

// Get MQTT connection status from store
const mqttConnectionStatus = useSelector((state: any) => state.mqtt.connectionStatus);

// Add effect to handle MQTT reconnection
useEffect(() => {
  const handleReconnect = async () => {
    const traceId = getTraceId();
    const state = store.getState();
    const { currentUserId } = state.mqtt;
    const { user } = state.auth;

    // Check both Redux state and actual MQTT connection
    const isActuallyConnected = mqttService.isConnected();
    const actualConnectionStatus = mqttService.getConnectionStatus();

    logger.info('Checking MQTT connection status', {
      reduxStatus: mqttConnectionStatus,
      actualStatus: actualConnectionStatus,
      isActuallyConnected,
      userId: currentUserId,
      traceId
    }, 'chat');

    // Only reconnect if we have a user and either:
    // 1. Redux thinks we're disconnected, or
    // 2. The actual MQTT client is not connected
    if (user && currentUserId && (!isActuallyConnected || mqttConnectionStatus === 'disconnected')) {
      logger.info('Attempting MQTT reconnection from chat window', {
        userId: currentUserId,
        reduxStatus: mqttConnectionStatus,
        actualStatus: actualConnectionStatus,
        traceId
      }, 'chat');

      try {
        const token = await storage.getToken();
        if (token) {
          store.dispatch(connect({ token, userId: currentUserId }));
        }
      } catch (error) {
        logger.error('Failed to reconnect MQTT', {
          error,
          userId: currentUserId,
          traceId
        }, 'chat');
      }
    }
  };

  handleReconnect();
}, [mqttConnectionStatus]); 