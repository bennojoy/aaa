import { takeLatest, call, put, select, SelectEffect } from 'redux-saga/effects';
import {
  loginRequest,
  loginSuccess,
  loginFailure,
  signupRequest,
  signupSuccess,
  signupFailure,
} from '../authSlice';
import { apiClient } from '../../api/client';
import { storage } from '../../utils/storage';
import { logger } from '../../utils/logger';
import { AxiosResponse } from 'axios';
import { LoginCredentials, SignupData, AuthResponse, User } from '../../types/auth';
import { getTraceId } from '../../utils/trace';
import { initializeMqtt } from './chatSaga';

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
    // Handle validation errors from FastAPI
    if (error.response?.data?.detail) {
      if (Array.isArray(error.response.data.detail)) {
        // Handle array of validation errors
        const errorMessages = error.response.data.detail.map((err: any) => err.msg).join(', ');
        logger.error('Login validation failed', { errors: error.response.data.detail }, 'auth');
        yield put(loginFailure(errorMessages));
      } else {
        // Handle single error message
        logger.error('Login failed', { error: error.response.data.detail }, 'auth');
        yield put(loginFailure(error.response.data.detail));
      }
    } else {
      // Handle other types of errors
      const errorMessage = error.message || 'Login failed';
      logger.error('Login failed', { 
        error: error.message,
        status: error.response?.status,
        traceId 
      }, 'auth');
      yield put(loginFailure(errorMessage));
    }
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
    // Handle validation errors from FastAPI
    if (error.response?.data?.detail) {
      if (Array.isArray(error.response.data.detail)) {
        // Handle array of validation errors
        const errorMessages = error.response.data.detail.map((err: any) => err.msg).join(', ');
        logger.error('Signup validation failed', { errors: error.response.data.detail }, 'auth');
        yield put(signupFailure(errorMessages));
      } else {
        // Handle single error message
        logger.error('Signup failed', { error: error.response.data.detail }, 'auth');
        yield put(signupFailure(error.response.data.detail));
      }
    } else {
      // Handle other types of errors
      const errorMessage = error.message || 'Signup failed';
      logger.error('Signup failed', { 
        error: error.message,
        status: error.response?.status,
        traceId 
      }, 'auth');
      yield put(signupFailure(errorMessage));
    }
  }
}

/**
 * Watch for auth-related actions and trigger appropriate sagas
 */
export function* authSaga(): Generator<any, void, any> {
  logger.debug('Starting auth sagas', null, 'auth');
  yield takeLatest(loginRequest.type, handleLogin);
  yield takeLatest(signupRequest.type, handleSignup);
} 