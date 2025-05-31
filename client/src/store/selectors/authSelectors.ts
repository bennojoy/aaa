import { RootState } from '../store';

export const getCurrentUserId = (state: RootState) => state.auth.user?.id;
export const getCurrentUser = (state: RootState) => state.auth.user;
export const getAuthToken = (state: RootState) => state.auth.token;
export const getAuthError = (state: RootState) => state.auth.error;
export const getAuthLoading = (state: RootState) => state.auth.loading; 