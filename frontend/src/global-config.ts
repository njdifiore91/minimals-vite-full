/**
 * Global Configuration for MCA Application Processing System
 * 
 * This file contains global configuration parameters for the MCA application,
 * including API endpoints, authentication settings, and theme colors.
 */

// API Endpoints
export const API_CONFIG = {
  baseUrl: '/api/v1',
  endpoints: {
    applications: '/api/v1/applications',
    documents: '/api/v1/documents',
    webhooks: '/api/v1/webhooks',
  },
  // Default request timeout in milliseconds
  timeout: 30000,
};

// Authentication Configuration
export const AUTH_CONFIG = {
  // JWT Configuration
  jwt: {
    algorithm: 'RS256', // RSA Signature with SHA-256
    accessTokenExpiry: 60 * 60 * 1000, // 60 minutes in milliseconds
    refreshTokenValidity: 7 * 24 * 60 * 60 * 1000, // 7 days in milliseconds
    tokenStorageType: 'sessionStorage', // Use sessionStorage for token storage
  },
  // Role-based permissions
  roles: {
    OPERATIONS_STAFF: 'operations_staff',
    SYSTEM_ADMIN: 'system_admin',
  },
};

// Theme Configuration
export const THEME_CONFIG = {
  // Funding-specific colors
  fundingColors: {
    // Primary colors for funding-related UI elements
    fundingPrimary: {
      main: '#1976d2', // Blue shade for primary funding elements
      light: '#42a5f5',
      dark: '#1565c0',
      contrastText: '#ffffff',
    },
    // Secondary colors for funding-related UI elements
    fundingSecondary: {
      main: '#388e3c', // Green shade for secondary funding elements
      light: '#4caf50',
      dark: '#2e7d32',
      contrastText: '#ffffff',
    },
  },
};

// Screen Resolution Configuration
export const SCREEN_CONFIG = {
  targetResolutions: {
    desktop: ['1920x1080', '1440x900'],
    tablet: ['1024x768', '768x1024'],
    mobile: ['375x667', '414x896'],
  },
  // Breakpoints (matching Material UI defaults)
  breakpoints: {
    xs: 0,
    sm: 600,
    md: 900,
    lg: 1200,
    xl: 1536,
  },
};

// Feature Flags for gradual rollout
export const FEATURE_FLAGS = {
  enableAutomatedDocumentClassification: true,
  enableOcrExtraction: true,
  enableWebhookConfiguration: true,
};

// Environment-specific configuration
export const ENV_CONFIG = {
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
  isStaging: process.env.NODE_ENV === 'staging',
  // API base URL can be overridden by environment variable
  apiBaseUrl: process.env.REACT_APP_API_BASE_URL || API_CONFIG.baseUrl,
};

// Default export for easier importing
export default {
  API_CONFIG,
  AUTH_CONFIG,
  THEME_CONFIG,
  SCREEN_CONFIG,
  FEATURE_FLAGS,
  ENV_CONFIG,
};