/**
 * context/AuthContext.jsx
 * =======================
 * React Authentication Context & Provider
 * 
 * WHY THIS FILE EXISTS:
 *     Authentication state (who is logged in, what their role is) is needed by
 *     almost every page. Instead of passing user details down via props, React
 *     Context stores it globally, allowing components to read session states.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import authService from '../services/auth';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(true);

  // Initialize and validate the token on app load
  useEffect(() => {
    const initializeAuth = async () => {
      if (token) {
        try {
          // Verify token is still valid by requesting user details
          const userData = await authService.getMe();
          setUser(userData);
        } catch (error) {
          console.error('Session validation failed:', error);
          // Auto-clean stale data
          logout();
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, [token]);

  /**
   * authenticates credentials and stores the session state.
   */
  const login = async (username, password) => {
    setLoading(true);
    try {
      const data = await authService.login(username, password);
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      
      // Fetch details of the newly logged-in user
      const userData = await authService.getMe();
      setUser(userData);
      return userData;
    } catch (error) {
      logout();
      throw error;
    } finally {
      setLoading(false);
    }
  };

  /**
   * registers a new user account.
   */
  const register = async (username, email, password, role) => {
    setLoading(true);
    try {
      const userData = await authService.register(username, email, password, role);
      return userData;
    } finally {
      setLoading(false);
    }
  };

  /**
   * clears session data and logs out.
   */
  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    isAuthenticated: !!user,
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom Hook to consume AuthContext easily
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
export default AuthContext;
