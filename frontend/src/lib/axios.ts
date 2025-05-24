import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// Base API URL - should be configured from environment variables in production
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Token storage keys
const ACCESS_TOKEN_KEY = 'mca_access_token';
const REFRESH_TOKEN_KEY = 'mca_refresh_token';

// Token expiration times (in milliseconds)
const ACCESS_TOKEN_EXPIRY = 60 * 60 * 1000; // 60 minutes
const REFRESH_TOKEN_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7 days

// API endpoints
export const API_ENDPOINTS = {
  // Authentication endpoints
  auth: {
    login: '/api/v1/auth/login',
    refresh: '/api/v1/auth/refresh',
    logout: '/api/v1/auth/logout',
  },
  // Application endpoints
  applications: {
    base: '/api/v1/applications',
    list: '/api/v1/applications',
    details: (id: string) => `/api/v1/applications/${id}`,
    status: (id: string) => `/api/v1/applications/${id}/status`,
    bulkActions: '/api/v1/applications/bulk',
  },
  // Document endpoints
  documents: {
    base: '/api/v1/documents',
    list: '/api/v1/documents',
    details: (id: string) => `/api/v1/documents/${id}`,
    download: (id: string) => `/api/v1/documents/${id}/download`,
  },
  // Webhook endpoints
  webhooks: {
    base: '/api/v1/webhooks',
    list: '/api/v1/webhooks',
    create: '/api/v1/webhooks',
    test: '/api/v1/webhooks/test',
    logs: '/api/v1/webhooks/logs',
  },
};

// Token management functions
export const getAccessToken = (): string | null => {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
};

export const getRefreshToken = (): string | null => {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
};

export const setTokens = (accessToken: string, refreshToken: string): void => {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
};

export const clearTokens = (): void => {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
};

export const isAuthenticated = (): boolean => {
  return !!getAccessToken();
};

// Error normalization function
export interface NormalizedError {
  status: number;
  message: string;
  errors?: Record<string, string[]>;
  originalError?: any;
}

export const normalizeError = (error: AxiosError): NormalizedError => {
  const status = error.response?.status || 500;
  const message = 
    (error.response?.data as any)?.message || 
    error.message || 
    'An unexpected error occurred';
  
  const errors = (error.response?.data as any)?.errors || {};
  
  return {
    status,
    message,
    errors,
    originalError: error,
  };
};

// Create Axios instance
const createAxiosInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    timeout: 30000, // 30 seconds timeout
  });

  // Flag to prevent multiple refresh token requests
  let isRefreshing = false;
  // Queue of failed requests to retry after token refresh
  let failedRequestsQueue: Array<{
    resolve: (value: unknown) => void;
    reject: (reason?: any) => void;
    config: AxiosRequestConfig;
  }> = [];

  // Process the queue of failed requests
  const processQueue = (error: AxiosError | null, token: string | null = null) => {
    failedRequestsQueue.forEach(request => {
      if (error) {
        request.reject(error);
      } else if (token) {
        // Retry the request with the new token
        request.config.headers = {
          ...request.config.headers,
          Authorization: `Bearer ${token}`,
        };
        request.resolve(instance(request.config));
      }
    });
    
    // Clear the queue
    failedRequestsQueue = [];
  };

  // Request interceptor - Add JWT token to requests
  instance.interceptors.request.use(
    (config) => {
      const token = getAccessToken();
      
      // Only add token to /api/v1/* endpoints
      if (token && config.url?.startsWith('/api/v1/')) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor - Handle token refresh and errors
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
      
      // Only handle 401 errors for API endpoints and prevent infinite retry loops
      if (
        error.response?.status === 401 && 
        originalRequest && 
        !originalRequest._retry &&
        originalRequest.url?.startsWith('/api/v1/') &&
        // Don't try to refresh on auth endpoints
        originalRequest.url !== API_ENDPOINTS.auth.refresh &&
        originalRequest.url !== API_ENDPOINTS.auth.login
      ) {
        // Mark this request as retried to prevent loops
        originalRequest._retry = true;
        
        // If already refreshing, add to queue
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedRequestsQueue.push({ resolve, reject, config: originalRequest });
          });
        }
        
        isRefreshing = true;
        
        try {
          const refreshToken = getRefreshToken();
          
          if (!refreshToken) {
            // No refresh token available, clear tokens and reject
            clearTokens();
            processQueue(error);
            return Promise.reject(error);
          }
          
          // Attempt to refresh the token
          const response = await axios.post(
            `${API_URL}${API_ENDPOINTS.auth.refresh}`,
            { refreshToken },
            { headers: { 'Content-Type': 'application/json' } }
          );
          
          const { accessToken, refreshToken: newRefreshToken } = response.data;
          
          // Store the new tokens
          setTokens(accessToken, newRefreshToken);
          
          // Update authorization header for the original request
          originalRequest.headers = {
            ...originalRequest.headers,
            Authorization: `Bearer ${accessToken}`,
          };
          
          // Process the queue with the new token
          processQueue(null, accessToken);
          
          // Retry the original request
          return instance(originalRequest);
        } catch (refreshError) {
          // Token refresh failed, clear tokens and reject all queued requests
          clearTokens();
          processQueue(error);
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
      
      // Handle 403 errors (Forbidden) - usually means the user doesn't have permission
      if (error.response?.status === 403) {
        // You might want to redirect to an access denied page or show a notification
        console.error('Access denied:', error.response.data);
      }
      
      // Normalize the error for consistent handling
      const normalizedError = normalizeError(error);
      return Promise.reject(normalizedError);
    }
  );

  return instance;
};

// Create and export the axios instance
const axiosInstance = createAxiosInstance();
export default axiosInstance;