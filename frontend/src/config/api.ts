/**
 * API endpoint configuration for the MCA Application Processing System
 * 
 * This file defines all API endpoints used throughout the application,
 * organized by domain/service for better maintainability.
 */

// Base API URL from environment variables or default to local development
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/api/v1';

/**
 * API endpoints organized by domain/service
 */
export const API_ENDPOINTS = {
  // Authentication endpoints
  auth: {
    login: `${API_BASE_URL}/auth/login`,
    register: `${API_BASE_URL}/auth/register`,
    refreshToken: `${API_BASE_URL}/auth/refresh-token`,
    forgotPassword: `${API_BASE_URL}/auth/forgot-password`,
    resetPassword: `${API_BASE_URL}/auth/reset-password`,
    verifyEmail: `${API_BASE_URL}/auth/verify-email`,
  },
  
  // User management endpoints
  users: {
    me: `${API_BASE_URL}/users/me`,
    update: `${API_BASE_URL}/users/me`,
    changePassword: `${API_BASE_URL}/users/me/change-password`,
    preferences: `${API_BASE_URL}/users/me/preferences`,
  },
  
  // Application management endpoints
  applications: {
    list: `${API_BASE_URL}/applications`,
    create: `${API_BASE_URL}/applications`,
    getById: `${API_BASE_URL}/applications`, // Append /{id} when using
    update: `${API_BASE_URL}/applications`, // Append /{id} when using
    delete: `${API_BASE_URL}/applications`, // Append /{id} when using
    getDocuments: `${API_BASE_URL}/applications`, // Append /{id}/documents when using
    getStatus: `${API_BASE_URL}/applications`, // Append /{id}/status when using
    updateStatus: `${API_BASE_URL}/applications`, // Append /{id}/status when using
  },
  
  // Document management endpoints
  documents: {
    list: `${API_BASE_URL}/documents`,
    getById: `${API_BASE_URL}/documents`, // Append /{id} when using
    getSecureUrl: `${API_BASE_URL}/documents/secure-url`,
    getUploadUrl: `${API_BASE_URL}/documents/upload-url`,
    getClassification: `${API_BASE_URL}/documents`, // Append /{id}/classification when using
    updateClassification: `${API_BASE_URL}/documents`, // Append /{id}/classification when using
    verifyField: `${API_BASE_URL}/documents`, // Append /{id}/fields/{fieldId}/verify when using
    delete: `${API_BASE_URL}/documents`, // Append /{id} when using
  },
  
  // Webhook management endpoints
  webhooks: {
    list: `${API_BASE_URL}/webhooks`,
    create: `${API_BASE_URL}/webhooks`,
    getById: `${API_BASE_URL}/webhooks`, // Append /{id} when using
    update: `${API_BASE_URL}/webhooks`, // Append /{id} when using
    delete: `${API_BASE_URL}/webhooks`, // Append /{id} when using
    testDelivery: `${API_BASE_URL}/webhooks`, // Append /{id}/test when using
    deliveryHistory: `${API_BASE_URL}/webhooks`, // Append /{id}/history when using
  },
};

/**
 * Default request timeout in milliseconds
 */
export const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Default request headers
 */
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};

/**
 * API rate limits (requests per minute)
 */
export const API_RATE_LIMITS = {
  auth: 10,
  users: 30,
  applications: 60,
  documents: 120,
  webhooks: 30,
};