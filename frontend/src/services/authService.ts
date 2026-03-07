import apiClient from '../config/api';
import type {
  LoginCredentials,
  RegisterCredentials,
  AuthResponse,
  RegisterResponse,
  UserResponse,
  User,
  ApiError,
} from '../types/auth';

const TOKEN_KEY = 'auth_token';

/**
 * Authentication Service
 * 
 * Handles all authentication-related API calls
 */

/**
 * Register a new user
 */
export const register = async (
  credentials: RegisterCredentials
): Promise<RegisterResponse> => {
  try {
    const response = await apiClient.post<RegisterResponse>(
      '/auth/register',
      credentials
    );
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Registration failed. Please try again.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Login user and store token
 */
export const login = async (
  credentials: LoginCredentials
): Promise<AuthResponse> => {
  try {
    const response = await apiClient.post<AuthResponse>(
      '/auth/login',
      credentials
    );
    
    // Store token in localStorage
    if (response.data.access_token) {
      localStorage.setItem(TOKEN_KEY, response.data.access_token);
    }
    
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Login failed. Please check your credentials.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Get current authenticated user
 */
export const getCurrentUser = async (): Promise<User> => {
  try {
    const response = await apiClient.get<User>('/users/me');
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch user information.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Logout user and clear token
 */
export const logout = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

/**
 * Get stored token
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * Check if user is authenticated (has valid token)
 */
export const isAuthenticated = (): boolean => {
  return !!getToken();
};
