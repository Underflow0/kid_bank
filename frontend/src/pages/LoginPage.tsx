/**
 * Login Page - Initial landing page with authentication
 */
import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';

const LoginPage: React.FC = () => {
  const { isAuthenticated, login, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700">
      <div className="card max-w-md w-full mx-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Virtual Family Bank
          </h1>
          <p className="text-gray-600">
            Teach your kids about money management
          </p>
        </div>

        <div className="space-y-4">
          <button
            onClick={login}
            className="w-full btn-primary py-3 text-lg"
          >
            Sign In
          </button>

          <div className="text-center text-sm text-gray-500">
            <p>Sign in with your Cognito account</p>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-2">Features:</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li>✓ Manage virtual bank accounts for children</li>
            <li>✓ Track balances and transactions</li>
            <li>✓ Automated monthly interest payments</li>
            <li>✓ Teach financial responsibility</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
