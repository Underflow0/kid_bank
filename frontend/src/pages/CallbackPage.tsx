/**
 * Callback Page - Handles OAuth callback from Cognito
 */
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const CallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Refresh user data after OAuth callback
        await refreshUser();
        // Redirect to dashboard
        navigate('/dashboard', { replace: true });
      } catch (error) {
        console.error('Error handling callback:', error);
        navigate('/', { replace: true });
      }
    };

    handleCallback();
  }, [navigate, refreshUser]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
        <p className="text-lg text-gray-600">Completing sign in...</p>
      </div>
    </div>
  );
};

export default CallbackPage;
