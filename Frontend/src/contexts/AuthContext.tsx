import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI } from '../services/api';
import type { SessionValidation } from '../types';

interface AuthContextType {
  isAuthenticated: boolean;
  user: {
    tierName: string;
    userName: string;
    features: Record<string, boolean>;
  } | null;
  login: (licenseKey: string) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthContextType['user']>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    validateSession();
  }, []);

  const validateSession = async () => {
    try {
      const response = await authAPI.validateSession();
      const data: SessionValidation = response.data;

      if (data.valid) {
        setIsAuthenticated(true);
        setUser({
          tierName: data.tier_name || '',
          userName: 'User',
          features: data.features_enabled || {}
        });
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (error) {
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (licenseKey: string) => {
    try {
      const response = await authAPI.login(licenseKey);
      const data = response.data;

      // Store session token if provided
      if (data.session_token) {
        localStorage.setItem('session_token', data.session_token);
      }

      setIsAuthenticated(true);
      setUser({
        tierName: data.tier_name,
        userName: data.user_name,
        features: data.features_enabled
      });
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('session_token');
      setIsAuthenticated(false);
      setUser(null);
    }
  };

  const value = {
    isAuthenticated,
    user,
    login,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};