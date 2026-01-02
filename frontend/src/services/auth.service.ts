import axios from 'axios';
import type { LoginRequest, RegisterRequest, AuthResponse } from '../types/auth.types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Register new user
 */
export const register = async (data: RegisterRequest): Promise<{ message: string }> => {
  try {
    const response = await axios.post(`${API_BASE_URL}/auth/register`, data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'Registration failed');
    }
    throw error;
  }
};

/**
 * Login user
 */
export const login = async (data: LoginRequest): Promise<AuthResponse> => {
  try {
    const response = await axios.post<AuthResponse>(`${API_BASE_URL}/auth/login`, data);
    
    // Store token in localStorage
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('user_email', data.email);
    
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
    throw error;
  }
};

/**
 * Logout user
 */
export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_email');
  localStorage.removeItem('last_uploaded_cv_id');
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem('access_token');
};

/**
 * Get current user email
 */
export const getCurrentUserEmail = (): string | null => {
  return localStorage.getItem('user_email');
};
