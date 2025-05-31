import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AuthResponse, LoginCredentials, SignupData, User } from '../../types/auth';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  loading: false,
  error: null
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearAuthState: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = null;
    },
    // Login actions
    loginRequest: (state, action: PayloadAction<LoginCredentials>) => {
      state.loading = true;
      state.error = null;
    },
    loginSuccess: (state, action: PayloadAction<{ user: User; access_token: string }>) => {
      state.loading = false;
      state.user = action.payload.user;
      state.token = action.payload.access_token;
      state.isAuthenticated = true;
      state.error = null;
    },
    loginFailure: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
      state.isAuthenticated = false;
      state.token = null;
      state.user = null;
    },
    // Signup actions
    signupRequest: (state, action: PayloadAction<SignupData>) => {
      state.loading = true;
      state.error = null;
    },
    signupSuccess: (state, action: PayloadAction<{ user: User; access_token: string | null }>) => {
      state.loading = false;
      state.user = action.payload.user;
      state.token = action.payload.access_token;
      state.isAuthenticated = !!action.payload.access_token;
      state.error = null;
    },
    signupFailure: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
      state.isAuthenticated = false;
      state.token = null;
      state.user = null;
    },
    // Logout action
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = null;
    },
    clearError: (state) => {
      state.error = null;
    }
  }
});

export const {
  clearAuthState,
  loginRequest,
  loginSuccess,
  loginFailure,
  signupRequest,
  signupSuccess,
  signupFailure,
  logout,
  clearError
} = authSlice.actions;

export default authSlice.reducer; 