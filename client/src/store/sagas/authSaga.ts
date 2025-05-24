import { takeLatest, call, put, select, SelectEffect } from 'redux-saga/effects';
import {
  loginRequest,
  loginSuccess,
  loginFailure,
  signupRequest,
  signupSuccess,
  signupFailure,
  logout,
} from '../authSlice';
import { disconnected, connect, setUserId } from '../mqttSlice';
import { apiClient } from '../../api/client';
import { storage } from '../../utils/storage';
import { logger } from '../../utils/logger';
import { AxiosResponse } from 'axios';
import { LoginCredentials, SignupData, AuthResponse, User } from '../../types/auth';
import { getTraceId } from '../../utils/trace';
import { initializeMqtt } from './chatSaga';
import { take } from 'redux-saga/effects';
import { validateToken } from '../../utils/auth';

// Action types
const REHYDRATE = 'persist/REHYDRATE';

// Selector to get auth state
const getAuthState = (state: any) => state.auth;

/**
 * Handle user login request
 * @param action - The login request action containing user credentials
 */
function* handleLogin(action: ReturnType<typeof loginRequest>): Generator<any, void, any> {
  const { identifier, password } = action.payload;
  const traceId = getTraceId();

  logger.info('Login attempt', { identifier, traceId }, 'auth');

  try {
    const response: AxiosResponse<AuthResponse> = yield call(
      apiClient.post,
      '/api/v1/auth/signin',
      {
        identifier,
        password,
      }
    );

    const { access_token, user_id } = response.data;
    
    if (!access_token) {
      throw new Error('No access token received');
    }

    if (!user_id) {
      throw new Error('No user ID received');
    }

    // Create a minimal user object with the ID
    const user: User = {
      id: user_id,
      phone_number: identifier,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    // Store token and user data
    yield call([storage, 'setToken'], access_token);
    yield call([storage, 'setUserData'], user);
    
    logger.info('Login successful', { identifier, userId: user_id }, 'auth');

    // First dispatch login success
    yield put(loginSuccess({ user, access_token }));

    // Wait for auth state to be updated
    const authState = yield select(getAuthState);
    if (!authState.user || !authState.token) {
      throw new Error('Auth state not properly updated');
    }

    // Initialize MQTT connection after login success
    logger.info('Dispatching MQTT initialization', { 
      userId: user_id,
      hasToken: !!access_token,
      traceId
    }, 'auth');
    
    yield put(initializeMqtt({ token: access_token, userId: user_id }));
    logger.info('MQTT initialization dispatched', { 
      userId: user_id,
      traceId
    }, 'auth');

  } catch (error: any) {
    logger.error('Login failed', {
      error: error.message,
      status: error.response?.status,
      traceId
    }, 'auth');

    yield put(loginFailure(error.response?.data?.detail || 'Login failed'));
  }
}

/**
 * Handle user signup request
 * @param action - The signup request action containing user data
 */
function* handleSignup(action: ReturnType<typeof signupRequest>): Generator<any, void, any> {
  const { phone_number, password } = action.payload;
  const traceId = getTraceId();

  logger.info('Signup attempt', { phone_number, traceId }, 'auth');

  try {
    const response: AxiosResponse<AuthResponse> = yield call(
      apiClient.post,
      '/api/v1/auth/signup',
      {
        phone_number,
        password,
      }
    );

    const { access_token, user_id } = response.data;

    if (!access_token) {
      throw new Error('No access token received');
    }

    if (!user_id) {
      throw new Error('No user ID received');
    }

    // Create a minimal user object with the ID
    const user: User = {
      id: user_id,
      phone_number,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    // Store token and user data
    yield call([storage, 'setToken'], access_token);
    yield call([storage, 'setUserData'], user);

    logger.info('Signup successful', { phone_number, userId: user_id }, 'auth');

    // First dispatch signup success
    yield put(signupSuccess({ user, access_token }));

    // Wait for auth state to be updated
    const authState = yield select(getAuthState);
    if (!authState.user || !authState.token) {
      throw new Error('Auth state not properly updated');
    }

    // Initialize MQTT connection after signup success
    yield put(initializeMqtt({ token: access_token, userId: user_id }));

  } catch (error: any) {
    logger.error('Signup failed', {
      error: error.message,
      status: error.response?.status,
      traceId
    }, 'auth');

    yield put(signupFailure(error.response?.data?.detail || 'Signup failed'));
  }
}

/**
 * Handle state rehydration
 * This function is called when the app starts and the persisted state is rehydrated
 */
function* handleRehydration(): Generator<any, void, any> {
  const traceId = getTraceId();
  logger.info('Handling state rehydration', { traceId }, 'auth');

  // Wait for rehydration to complete
  yield take(REHYDRATE);
  
  // Get auth and MQTT state after rehydration
  const authState = yield select(getAuthState);
  const mqttState = yield select((state: any) => state.mqtt);
  
  logger.info('State rehydrated', { 
    hasUser: !!authState.user,
    hasToken: !!authState.token,
    mqttState,
    traceId 
  }, 'auth');

  // If we have both user and token, and MQTT is not connected, connect to MQTT
  if (authState.user && authState.token) {
    logger.info('Auth state valid, checking MQTT connection', { 
      userId: authState.user.id,
      mqttStatus: mqttState.connectionStatus,
      traceId 
    }, 'auth');

    // Get fresh token from storage
    const token = yield call([storage, 'getToken']);
    logger.info('Retrieved token from storage', {
      hasToken: !!token,
      tokenLength: token?.length,
      tokenPreview: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
      traceId
    }, 'auth');

    if (!token) {
      logger.error('No token found in storage', { traceId }, 'auth');
      return;
    }

    // Verify token is still valid
    logger.info('Validating token', { traceId }, 'auth');
    const isValid = yield call(validateToken);
    logger.info('Token validation result', { 
      isValid,
      traceId 
    }, 'auth');

    if (!isValid) {
      logger.error('Token validation failed', { traceId }, 'auth');
      
      // Clear invalid token and user data
      yield call([storage, 'clear']);
      yield put(logout());
      return;
    }

    // Always force a new MQTT connection on rehydration
    logger.info('Resetting MQTT state to disconnected', { traceId }, 'auth');
    yield put(disconnected()); // Reset MQTT state first
    
    // Wait for state to be updated
    yield new Promise(resolve => setTimeout(resolve, 500));
    
    // First set the user ID in the MQTT state
    logger.info('Setting user ID in MQTT state', { 
      userId: authState.user.id,
      traceId 
    }, 'auth');
    yield put(setUserId(authState.user.id));
    
    // Wait for state to be updated
    yield new Promise(resolve => setTimeout(resolve, 500));
    
    // Verify state updates
    const updatedMqttState = yield select((state: any) => state.mqtt);
    logger.info('MQTT state after updates', {
      userId: authState.user.id,
      mqttState: updatedMqttState,
      traceId
    }, 'auth');
    
    // Connect to MQTT with fresh token
    logger.info('Dispatching MQTT connect action', {
      userId: authState.user.id,
      hasToken: !!token,
      tokenLength: token.length,
      tokenPreview: token ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : undefined,
      traceId,
      currentState: updatedMqttState
    }, 'auth');
    
    yield put(connect({ 
      token, 
      userId: authState.user.id 
    }));
    
    // Wait for state to be updated
    yield new Promise(resolve => setTimeout(resolve, 500));
    
    const finalMqttState = yield select((state: any) => state.mqtt);
    logger.info('MQTT connect action dispatched', {
      userId: authState.user.id,
      traceId,
      currentState: finalMqttState
    }, 'auth');
  } else {
    logger.info('No valid auth state found', { 
      traceId,
      hasUser: !!authState.user,
      hasToken: !!authState.token
    }, 'auth');
  }
}

/**
 * Watch for auth-related actions and trigger appropriate sagas
 */
export function* authSaga() {
  yield takeLatest(loginRequest.type, handleLogin);
  yield takeLatest(signupRequest.type, handleSignup);
  yield takeLatest(REHYDRATE, handleRehydration);
} 