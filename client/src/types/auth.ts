export interface User {
  id: string;
  phone_number: string;
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

export interface LoginCredentials {
  identifier: string;
  password: string;
}

export interface SignupData {
  phone_number: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  user: User;
} 