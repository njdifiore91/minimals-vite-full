/**
 * Axios Configuration for MCA Application Processing System
 * 
 * This file configures the Axios HTTP client with:
 * - Base configuration (baseURL, timeout, headers)
 * - API endpoints for MCA-specific features
 * - JWT authentication interceptor
 * - Error handling and normalization
 * - Token refresh mechanism
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { API_CONFIG, AUTH_CONFIG, ENV_CONFIG } from '../global-config';

// =============================================================================
// Error Handling Types and Utilities
// =============================================================================

/**
 * Normalized error structure for consistent error handling
 */
export interface NormalizedError {
  status: number;
  message: string;
  code?: string;
  errors?: Record<string, string[]>;
  originalError?: any;
}

/**
 * Normalizes different error types into a consistent structure
 */
const normalizeError = (error: any): NormalizedError => {
  // Handle Axios response errors
  if (error.response) {
    const { status, data } = error.response;
    return {
      status,
      message: data.message || 'An error occurred with the server response',
      code: data.code,
      errors: data.errors,
      originalError: error,
    };
  }
  
  // Handle network errors
  if (error.request) {
    return {
      status: 0,
      message: 'Network error. Please check your connection.',
      originalError: error,
    };
  }
  
  // Handle other errors
  return {
    status: 500,
    message: error.message || 'An unexpected error occurred',
    originalError: error,
  };
};

/**
 * Gets a user-friendly error message
 */
export const getErrorMessage = (error: NormalizedError): string => {
  // Return specific field validation errors if available
  if (error.errors && Object.keys(error.errors).length > 0) {
    const firstField = Object.keys(error.errors)[0];
    return error.errors[firstField][0] || error.message;
  }
  
  // Return appropriate message based on status code
  switch (error.status) {
    case 400:
      return error.message || 'Invalid request. Please check your data.';
    case 401:
      return 'Authentication required. Please log in again.';
    case 403:
      return 'You do not have permission to perform this action.';
    case 404:
      return 'The requested resource was not found.';
    case 422:
      return error.message || 'Validation error. Please check your data.';
    case 429:
      return 'Too many requests. Please try again later.';
    case 500:
    case 502:
    case 503:
    case 504:
      return 'Server error. Please try again later.';
    case 0:
      return 'Network error. Please check your connection.';
    default:
      return error.message || 'An unexpected error occurred.';
  }
};

// =============================================================================
// Token Management
// =============================================================================

/**
 * JWT token structure
 */
interface JwtTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // Timestamp in milliseconds
}

/**
 * Gets JWT tokens from sessionStorage
 */
const getTokens = (): JwtTokens | null => {
  const tokensStr = sessionStorage.getItem('mca_auth_tokens');
  if (!tokensStr) return null;
  
  try {
    return JSON.parse(tokensStr) as JwtTokens;
  } catch (error) {
    console.error('Failed to parse auth tokens:', error);
    return null;
  }
};

/**
 * Saves JWT tokens to sessionStorage
 */
const saveTokens = (tokens: JwtTokens): void => {
  sessionStorage.setItem('mca_auth_tokens', JSON.stringify(tokens));
};

/**
 * Clears JWT tokens from sessionStorage
 */
const clearTokens = (): void => {
  sessionStorage.removeItem('mca_auth_tokens');
};

/**
 * Checks if access token is expired
 */
const isTokenExpired = (): boolean => {
  const tokens = getTokens();
  if (!tokens) return true;
  
  // Add a 30-second buffer to handle potential timing issues
  return Date.now() >= tokens.expiresAt - 30000;
};

/**
 * Refreshes the access token using the refresh token
 */
const refreshAccessToken = async (): Promise<boolean> => {
  const tokens = getTokens();
  if (!tokens || !tokens.refreshToken) return false;
  
  try {
    // Create a new axios instance to avoid interceptors loop
    const refreshResponse = await axios.post<{ accessToken: string; expiresAt: number }>(
      `${API_CONFIG.baseUrl}/auth/refresh`,
      { refreshToken: tokens.refreshToken }
    );
    
    // Update tokens in storage
    saveTokens({
      accessToken: refreshResponse.data.accessToken,
      refreshToken: tokens.refreshToken, // Keep the same refresh token
      expiresAt: refreshResponse.data.expiresAt,
    });
    
    return true;
  } catch (error) {
    console.error('Failed to refresh token:', error);
    // Clear tokens on refresh failure
    clearTokens();
    return false;
  }
};

// =============================================================================
// Axios Instance Configuration
// =============================================================================

/**
 * Base Axios configuration
 */
const axiosConfig: AxiosRequestConfig = {
  baseURL: ENV_CONFIG.apiBaseUrl,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
};

/**
 * Create Axios instance
 */
const axiosInstance: AxiosInstance = axios.create(axiosConfig);

// =============================================================================
// Request Interceptor
// =============================================================================

axiosInstance.interceptors.request.use(
  async (config) => {
    // Only add auth header for API endpoints
    if (config.url?.startsWith('/api/v1/')) {
      // Check if token is expired and needs refresh
      if (isTokenExpired()) {
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
          // Redirect to login if refresh failed
          window.location.href = '/auth/login';
          return Promise.reject(new Error('Authentication required'));
        }
      }
      
      // Add authorization header with token
      const tokens = getTokens();
      if (tokens?.accessToken) {
        config.headers.Authorization = `Bearer ${tokens.accessToken}`;
      }
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// =============================================================================
// Response Interceptor
// =============================================================================

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
    
    // Handle 401 Unauthorized error - attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/api/v1/auth/refresh') {
      originalRequest._retry = true;
      
      try {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          // Retry the original request with new token
          const tokens = getTokens();
          if (tokens?.accessToken && originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${tokens.accessToken}`;
          }
          return axiosInstance(originalRequest);
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
      }
      
      // Redirect to login if refresh failed
      clearTokens();
      window.location.href = '/auth/login';
    }
    
    // Handle 403 Forbidden - user doesn't have permission
    if (error.response?.status === 403) {
      // No need to clear tokens, just notify the user
      console.error('Permission denied:', error.response.data);
    }
    
    // Normalize the error for consistent handling
    const normalizedError = normalizeError(error);
    return Promise.reject(normalizedError);
  }
);

// =============================================================================
// API Endpoints
// =============================================================================

/**
 * MCA Application endpoints
 */
export const applicationEndpoints = {
  list: (params?: Record<string, any>) => axiosInstance.get(API_CONFIG.endpoints.applications, { params }),
  getById: (id: string) => axiosInstance.get(`${API_CONFIG.endpoints.applications}/${id}`),
  create: (data: any) => axiosInstance.post(API_CONFIG.endpoints.applications, data),
  update: (id: string, data: any) => axiosInstance.put(`${API_CONFIG.endpoints.applications}/${id}`, data),
  updateStatus: (id: string, status: string) => 
    axiosInstance.patch(`${API_CONFIG.endpoints.applications}/${id}/status`, { status }),
  bulkAction: (ids: string[], action: string) => 
    axiosInstance.post(`${API_CONFIG.endpoints.applications}/bulk`, { ids, action }),
};

/**
 * Document endpoints
 */
export const documentEndpoints = {
  list: (applicationId?: string, params?: Record<string, any>) => 
    axiosInstance.get(API_CONFIG.endpoints.documents, { 
      params: { ...params, application_id: applicationId } 
    }),
  getById: (id: string) => axiosInstance.get(`${API_CONFIG.endpoints.documents}/${id}`),
  upload: (applicationId: string, file: File, metadata?: any) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('application_id', applicationId);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }
    return axiosInstance.post(API_CONFIG.endpoints.documents, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  download: (id: string) => axiosInstance.get(`${API_CONFIG.endpoints.documents}/${id}/download`, {
    responseType: 'blob',
  }),
};

/**
 * Webhook endpoints
 */
export const webhookEndpoints = {
  list: (params?: Record<string, any>) => axiosInstance.get(API_CONFIG.endpoints.webhooks, { params }),
  getById: (id: string) => axiosInstance.get(`${API_CONFIG.endpoints.webhooks}/${id}`),
  create: (data: any) => axiosInstance.post(API_CONFIG.endpoints.webhooks, data),
  update: (id: string, data: any) => axiosInstance.put(`${API_CONFIG.endpoints.webhooks}/${id}`, data),
  delete: (id: string) => axiosInstance.delete(`${API_CONFIG.endpoints.webhooks}/${id}`),
  test: (id: string, eventType: string) => 
    axiosInstance.post(`${API_CONFIG.endpoints.webhooks}/${id}/test`, { eventType }),
  logs: (id: string, params?: Record<string, any>) => 
    axiosInstance.get(`${API_CONFIG.endpoints.webhooks}/${id}/logs`, { params }),
};

// Export the configured axios instance as default
export default axiosInstance;