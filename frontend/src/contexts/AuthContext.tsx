import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  login as loginService,
  register as registerService,
  getCurrentUser,
  logout as logoutService,
  getToken,
} from '../services/authService';
import type {
  User,
  LoginCredentials,
  RegisterCredentials,
  AuthState,
  ApiError,
} from '../types/auth';

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Initialize auth state on mount
   */
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = getToken();
      if (storedToken) {
        setToken(storedToken);
        try {
          const userData = await getCurrentUser();
          setUser(userData);
        } catch (err) {
          // Token is invalid, clear it
          logoutService();
          setToken(null);
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  /**
   * Login function
   */
  const login = async (credentials: LoginCredentials): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      const response = await loginService(credentials);
      setToken(response.access_token);
      
      // Fetch user data (now returns full profile)
      const userData = await getCurrentUser();
      setUser(userData);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Login failed. Please try again.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Register function
   */
  const register = async (credentials: RegisterCredentials): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      await registerService(credentials);
      
      // After successful registration, automatically log in
      await login(credentials);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Registration failed. Please try again.');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Logout function
   */
  const logout = (): void => {
    logoutService();
    setUser(null);
    setToken(null);
    setError(null);
  };

  /**
   * Clear error message
   */
  const clearError = (): void => {
    setError(null);
  };

  const setUserState = (newUser: User) => {
    setUser(newUser);
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    loading,
    login,
    register,
    logout,
    error,
    clearError,
    setUser: setUserState,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * Hook to use auth context
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

