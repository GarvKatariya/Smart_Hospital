'use client';
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI, RegisterData, UserProfile, UserProfileUpdate, PasswordChange } from './api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  register: (data: RegisterData) => Promise<void>;
  updateProfile: (data: UserProfileUpdate) => Promise<void>;
  changePassword: (data: PasswordChange) => Promise<void>;
  loading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const clearExpiredSession = () => {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setToken(null);
      setUser(null);
    };
    window.addEventListener('hospital:session-expired', clearExpiredSession);
    const restoreSession = async () => {
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        try {
          const response = await authAPI.getMe();
          if (active) {
            setToken(storedToken);
            setUser(response.data);
          }
        } catch {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      if (active) setLoading(false);
    };
    void restoreSession();
    return () => {
      active = false;
      window.removeEventListener('hospital:session-expired', clearExpiredSession);
    };
  }, []);

  const login = async (email: string, pass: string) => {
    const res = await authAPI.login(email, pass);
    const newToken = res.data.access_token || res.data.token;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    const meRes = await authAPI.getMe();
    setUser(meRes.data);
    localStorage.setItem('user', JSON.stringify(meRes.data));
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    router.replace('/login');
  };

  const register = async (data: RegisterData) => {
    await authAPI.register(data);
    await login(data.email, data.password);
  };

  const updateProfile = async (data: UserProfileUpdate) => {
    const response = await authAPI.updateProfile(data);
    setUser(response.data);
    localStorage.setItem('user', JSON.stringify(response.data));
  };

  const changePassword = async (data: PasswordChange) => {
    await authAPI.changePassword(data);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, register, updateProfile, changePassword, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
