/**
 * Dashboard Page - Main page after login (routes to Parent or Child dashboard)
 */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const DashboardPage: React.FC = () => {
  const { user, isParent, isChild, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  // Redirect based on user role
  if (isParent) {
    return <Navigate to="/parent" replace />;
  }

  if (isChild) {
    return <Navigate to="/child" replace />;
  }

  // Fallback if role is not recognized
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="card">
        <h2 className="text-xl font-bold text-red-600 mb-4">Error</h2>
        <p>Unable to determine user role. Please contact support.</p>
      </div>
    </div>
  );
};

export default DashboardPage;
