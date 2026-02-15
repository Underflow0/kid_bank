/**
 * Parent Dashboard - Main dashboard for parent users
 */
import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const ParentDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    navigate('/');
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Virtual Family Bank</h1>
            <p className="text-sm text-gray-600">Parent Dashboard</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">{user.name}</p>
              <p className="text-xs text-gray-500">{user.email}</p>
            </div>
            <button
              onClick={logout}
              className="btn-secondary text-sm"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Welcome, {user.name}!
          </h2>
          <p className="text-gray-600 mb-4">
            Your parent dashboard is under construction. Features coming soon:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>View all children's accounts</li>
            <li>Adjust children's balances</li>
            <li>View transaction history</li>
            <li>Create new child accounts</li>
            <li>Manage interest rates</li>
          </ul>
        </div>
      </main>
    </div>
  );
};

export default ParentDashboard;
