import { takeLatest, call, put } from 'redux-saga/effects';
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

/**
 * Handle user login request
 * @param action - The login request action containing user credentials
 */
function* handleLogin(action: ReturnType<typeof loginRequest>) {
  try {
    const { identifier, password } = action.payload as LoginCredentials;
    const response: AxiosResponse<AuthResponse> = yield call(
      apiClient.post,
      '/api/v1/auth/signin',
      {
        identifier,
        password,
      }
    );

    const { access_token, user } = response.data;
    
    if (!access_token) {
      throw new Error('No access token received');
    }

    yield call([storage, 'setToken'], access_token);
    yield call([storage, 'setUserData'], user);
    yield put(loginSuccess({ user, access_token }));
    
    logger.info('Login successful', { identifier }, 'auth');
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
      logger.error('Login failed', { error }, 'auth');
      yield put(loginFailure(errorMessage));
    }
  }
}

/**
 * Handle user signup request
 * @param action - The signup request action containing user data
 */
function* handleSignup(action: ReturnType<typeof signupRequest>) {
  logger.debug('Starting signup process', { payload: action.payload }, 'auth');
  try {
    const { phone_number, password } = action.payload as SignupData;
    logger.debug('Making signup API call', { phone_number }, 'auth');
    
    const response: AxiosResponse<AuthResponse> = yield call(
      apiClient.post,
      '/api/v1/auth/signup',
      {
        phone_number,
        password,
      }
    );

    logger.debug('Received signup response', { status: response.status, data: response.data }, 'auth');

    // Check if we have a valid response
    if (!response.data) {
      throw new Error('Invalid response from server');
    }

    // Success case - just show success message
    yield put(signupSuccess(response.data));
    logger.info('Signup successful', { phoneNumber: phone_number }, 'auth');
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
      logger.error('Signup failed', { error }, 'auth');
      yield put(signupFailure(errorMessage));
    }
  }
}

/**
 * Watch for auth-related actions and trigger appropriate sagas
 */
export function* authSaga() {
  logger.debug('Starting auth sagas', null, 'auth');
  yield takeLatest(loginRequest.type, handleLogin);
  yield takeLatest(signupRequest.type, handleSignup);
} 