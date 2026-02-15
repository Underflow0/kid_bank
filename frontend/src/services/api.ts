/**
 * API service layer - handles all backend API calls
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import type {
  User,
  Child,
  Transaction,
  CreateChildRequest,
  AdjustBalanceRequest,
  UpdateUserRequest,
  TransactionListResponse,
  ChildrenListResponse,
  ChildSummaryResponse,
  APIError
} from '../types';

class APIService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_ENDPOINT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      async (config) => {
        try {
          const session = await fetchAuthSession();
          const token = session.tokens?.idToken?.toString();

          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }

          return config;
        } catch (error) {
          console.error('Error fetching auth token:', error);
          return config;
        }
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        if (error.response) {
          // Server responded with error
          const apiError: APIError = {
            error: error.response.data?.error || 'An error occurred',
            details: error.response.data?.details,
          };
          return Promise.reject(apiError);
        } else if (error.request) {
          // Request made but no response
          return Promise.reject({ error: 'Network error - no response from server' });
        } else {
          // Something else went wrong
          return Promise.reject({ error: error.message || 'Unknown error occurred' });
        }
      }
    );
  }

  // Auth endpoints
  async getUser(): Promise<User> {
    const response = await this.api.get<{ user: User }>('/user');
    return response.data.user;
  }

  async updateUser(data: UpdateUserRequest): Promise<User> {
    const response = await this.api.post<{ user: User }>('/user', data);
    return response.data.user;
  }

  // Family management endpoints
  async getChildren(): Promise<Child[]> {
    const response = await this.api.get<ChildrenListResponse>('/children');
    return response.data.children;
  }

  async getChildSummary(childId: string): Promise<ChildSummaryResponse> {
    const response = await this.api.get<ChildSummaryResponse>(`/children/${childId}`);
    return response.data;
  }

  async createChild(data: CreateChildRequest): Promise<Child> {
    const response = await this.api.post<{ child: Child }>('/children', data);
    return response.data.child;
  }

  // Transaction endpoints
  async getTransactions(userId?: string, limit?: number, nextToken?: string): Promise<TransactionListResponse> {
    const params = new URLSearchParams();
    if (userId) params.append('userId', userId);
    if (limit) params.append('limit', limit.toString());
    if (nextToken) params.append('nextToken', nextToken);

    const response = await this.api.get<TransactionListResponse>(`/transactions?${params.toString()}`);
    return response.data;
  }

  async adjustBalance(data: AdjustBalanceRequest): Promise<Transaction> {
    const response = await this.api.post<{ transaction: Transaction }>('/adjust-balance', data);
    return response.data.transaction;
  }
}

// Export singleton instance
export const apiService = new APIService();
export default apiService;
