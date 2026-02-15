/**
 * Authentication Context - manages auth state across the app
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { getCurrentUser, signOut, fetchAuthSession } from 'aws-amplify/auth';
import type { User, AuthUser } from '../types';
import { apiService } from '../services/api';

interface AuthContextType {
  authUser: AuthUser | null;
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isParent: boolean;
  isChild: boolean;
  login: () => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get Cognito user
      const cognitoUser = await getCurrentUser();
      const session = await fetchAuthSession();

      // Extract groups from ID token
      const idToken = session.tokens?.idToken;
      const groups = (idToken?.payload['cognito:groups'] as string[]) || [];

      const auth: AuthUser = {
        userId: cognitoUser.userId,
        email: cognitoUser.signInDetails?.loginId || '',
        groups,
      };

      setAuthUser(auth);

      // Fetch user profile from API
      const userProfile = await apiService.getUser();
      setUser(userProfile);
    } catch (err: any) {
      console.error('Error fetching user:', err);
      setError(err.error || err.message || 'Failed to fetch user');
      setAuthUser(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const login = () => {
    // Redirect to Cognito Hosted UI
    window.location.href = import.meta.env.VITE_COGNITO_DOMAIN +
      `/oauth2/authorize?client_id=${import.meta.env.VITE_USER_POOL_CLIENT_ID}` +
      `&response_type=code&scope=email+openid+profile` +
      `&redirect_uri=${encodeURIComponent(window.location.origin + '/callback')}`;
  };

  const logout = async () => {
    try {
      await signOut();
      setAuthUser(null);
      setUser(null);
      window.location.href = '/';
    } catch (err: any) {
      console.error('Error signing out:', err);
      setError(err.error || 'Failed to sign out');
    }
  };

  const refreshUser = async () => {
    await fetchUser();
  };

  const value: AuthContextType = {
    authUser,
    user,
    loading,
    error,
    isAuthenticated: !!authUser && !!user,
    isParent: user?.role === 'parent',
    isChild: user?.role === 'child',
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
