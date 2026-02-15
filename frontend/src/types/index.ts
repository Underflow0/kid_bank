/**
 * TypeScript type definitions for the Family Bank application
 */

export interface User {
  userId: string;
  email: string;
  name: string;
  role: 'parent' | 'child';
  balance: number;
  interestRate: number;
  parentId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Child {
  userId: string;
  name: string;
  email: string;
  balance: number;
  interestRate: number;
  createdAt: string;
  updatedAt: string;
}

export interface Transaction {
  transactionId: string;
  userId: string;
  amount: number;
  type: 'deposit' | 'withdrawal' | 'interest' | 'adjustment';
  description: string;
  balanceAfter: number;
  initiatedBy: string;
  timestamp: string;
}

export interface AuthUser {
  userId: string;
  email: string;
  groups: string[];
}

export interface APIError {
  error: string;
  details?: string;
}

export interface CreateChildRequest {
  email: string;
  name: string;
  initialBalance?: number;
  interestRate?: number;
}

export interface AdjustBalanceRequest {
  childId: string;
  amount: number;
  description?: string;
}

export interface UpdateUserRequest {
  name?: string;
  interestRate?: number;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  nextToken?: string;
}

export interface ChildrenListResponse {
  children: Child[];
  count: number;
}

export interface ChildSummaryResponse {
  child: Child;
  recentTransactions: Transaction[];
}
