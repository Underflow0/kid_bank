/**
 * Child Dashboard - Main dashboard for child users
 */
import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const ChildDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    navigate('/');
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-primary-600">My Bank Account</h1>
          </div>
          <button
            onClick={logout}
            className="btn-secondary text-sm"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Balance Card */}
        <div className="card bg-gradient-to-r from-primary-500 to-primary-600 text-white mb-8">
          <h2 className="text-lg font-medium mb-2">Your Balance</h2>
          <p className="text-4xl font-bold">${user.balance.toFixed(2)}</p>
          <p className="text-sm mt-2 opacity-90">
            Interest Rate: {(user.interestRate * 100).toFixed(1)}% per month
          </p>
        </div>

        {/* Welcome Card */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Hi, {user.name}!
          </h2>
          <p className="text-gray-600 mb-4">
            This is your personal bank account dashboard. More features coming soon:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>View your transaction history</li>
            <li>Track your savings goals</li>
            <li>See how much interest you've earned</li>
            <li>Learn about money management</li>
          </ul>
        </div>
      </main>
    </div>
  );
};

export default ChildDashboard;
