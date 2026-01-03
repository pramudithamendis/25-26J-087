/**
 * TypeScript type definitions for authentication
 */

export interface User {
  email: string;
  role: string;
  first_name?: string;
  last_name?: string;
  city?: string;
  phone_number?: string;
  name?: string; // Keep for backward compatibility
  github_handle?: string;
  github_url?: string;
  linkedin_url?: string;
  cv_file_path?: string;
  linkedin_file_path?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  first_name: string;
  last_name: string;
  email: string;
  city: string;
  phone_number?: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterResponse {
  message: string;
}

export interface UserResponse {
  user: User;
}

export interface ApiError {
  detail: string;
  statusCode?: number;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

