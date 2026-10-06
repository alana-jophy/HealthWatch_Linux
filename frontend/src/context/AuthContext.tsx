import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../services/api';

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: 'PUBLIC_HEALTH_OFFICER' | 'ADMIN' | 'HEALTH_WORKER' | 'PATIENT';
  is_active: boolean;
  is_superuser: boolean;
  must_change_password?: boolean;
  patient_pseudo_id?: string | null;
  patient_id?: string | null;
  created_at?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  role: 'PUBLIC_HEALTH_OFFICER' | 'ADMIN' | 'HEALTH_WORKER' | 'PATIENT' | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('healthwatch_jwt_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Restore session from localStorage & verify with /api/auth/me
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('healthwatch_jwt_token');
      const storedUser = localStorage.getItem('healthwatch_user_profile');

      if (storedToken && storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser);
          setUser(parsedUser);
          setToken(storedToken);

          // Background verification
          const res = await axios.get(`${API_BASE_URL}/api/auth/me`, {
            headers: { Authorization: `Bearer ${storedToken}` },
            timeout: 5000,
          });
          if (res.data) {
            setUser(res.data);
            localStorage.setItem('healthwatch_user_profile', JSON.stringify(res.data));
          }
        } catch (err) {
          console.warn('Session verification notice:', err);
          // Only clear if server explicitly rejected with 401/403
          if (axios.isAxiosError(err) && (err.response?.status === 401 || err.response?.status === 403)) {
            localStorage.removeItem('healthwatch_jwt_token');
            localStorage.removeItem('healthwatch_user_profile');
            setUser(null);
            setToken(null);
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await axios.post(`${API_BASE_URL}/api/auth/login`, {
        email: email.trim(),
        password: password,
      });

      const { access_token, user: userData } = res.data;

      localStorage.setItem('healthwatch_jwt_token', access_token);
      localStorage.setItem('healthwatch_user_profile', JSON.stringify(userData));
      
      setToken(access_token);
      setUser(userData);

      return { success: true };
    } catch (err: any) {
      let detail = err.response?.data?.detail 
        || err.response?.data?.message 
        || err.response?.data?.error?.message;
      
      if (!detail) {
        if (err.message && err.message.toLowerCase().includes('network')) {
          detail = `Network Error: Unable to reach backend API (${API_BASE_URL || 'relative'}). Please check server connectivity.`;
        } else if (err.response?.status === 502 || err.response?.status === 503 || err.response?.status === 504) {
          detail = `Gateway Error (${err.response.status}): Backend service is currently unavailable.`;
        } else {
          detail = 'Authentication failed. Please check your credentials (email or username "admin").';
        }
      }
      return { success: false, error: detail };
    }
  };

  const changePassword = async (currentPassword: string, newPassword: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const activeToken = token || localStorage.getItem('healthwatch_jwt_token');
      const res = await axios.post(
        `${API_BASE_URL}/api/auth/change-password`,
        {
          current_password: currentPassword,
          new_password: newPassword,
        },
        {
          headers: { Authorization: `Bearer ${activeToken}` },
        }
      );

      if (res.data?.user) {
        setUser(res.data.user);
        localStorage.setItem('healthwatch_user_profile', JSON.stringify(res.data.user));
      } else if (user) {
        const updated = { ...user, must_change_password: false };
        setUser(updated);
        localStorage.setItem('healthwatch_user_profile', JSON.stringify(updated));
      }

      return { success: true };
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data?.message || 'Failed to update password.';
      return { success: false, error: detail };
    }
  };

  const logout = () => {
    localStorage.removeItem('healthwatch_jwt_token');
    localStorage.removeItem('healthwatch_user_profile');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role || null,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        changePassword,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
