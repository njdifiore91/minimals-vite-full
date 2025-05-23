/**
 * Application Configuration
 * 
 * This file defines the core application configuration for the Notification Service.
 * It centralizes environment variables, application settings, and environment-specific
 * configurations (development, staging, production).
 */

import { config as dotenvConfig } from 'dotenv';
import { join } from 'path';
import { Environment, IAppConfig } from '../types/config';

// Load environment variables from .env file
dotenvConfig({ path: join(process.cwd(), '.env') });

/**
 * Get environment variable with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value
 * @param required Whether the environment variable is required
 * @returns The environment variable value or default value
 * @throws Error if required environment variable is missing
 */
function getEnv(key: string, defaultValue?: string, required = false): string {
  const value = process.env[key] || defaultValue;
  
  if (required && !value) {
    throw new Error(`Environment variable ${key} is required but not set`);
  }
  
  return value || '';
}

/**
 * Get numeric environment variable with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value
 * @param required Whether the environment variable is required
 * @returns The environment variable value as a number or default value
 * @throws Error if required environment variable is missing or not a valid number
 */
function getNumericEnv(key: string, defaultValue?: number, required = false): number {
  const stringValue = getEnv(key, defaultValue?.toString(), required);
  
  if (stringValue === '') {
    return defaultValue || 0;
  }
  
  const numericValue = Number(stringValue);
  
  if (isNaN(numericValue)) {
    throw new Error(`Environment variable ${key} must be a valid number`);
  }
  
  return numericValue;
}

/**
 * Get boolean environment variable with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value
 * @returns The environment variable value as a boolean or default value
 */
function getBooleanEnv(key: string, defaultValue = false): boolean {
  const value = getEnv(key, defaultValue.toString());
  return value.toLowerCase() === 'true';
}

/**
 * Get current environment
 * @returns The current environment (development, staging, production, test)
 */
function getEnvironment(): Environment {
  const env = getEnv('NODE_ENV', 'development');
  
  switch (env) {
    case 'production':
      return Environment.PRODUCTION;
    case 'staging':
      return Environment.STAGING;
    case 'test':
      return Environment.TEST;
    default:
      return Environment.DEVELOPMENT;
  }
}

/**
 * Get CORS configuration based on environment
 * @param environment Current environment
 * @returns CORS configuration object
 */
function getCorsConfig(environment: Environment) {
  // Default CORS configuration
  const corsConfig = {
    enabled: true,
    origin: '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'X-Correlation-ID'],
    exposedHeaders: ['X-Correlation-ID'],
    credentials: true,
    maxAge: 86400, // 24 hours
  };
  
  // Environment-specific CORS configuration
  switch (environment) {
    case Environment.PRODUCTION:
      // In production, only allow specific origins
      return {
        ...corsConfig,
        origin: getEnv('CORS_ORIGIN', 'https://app.dollarfunding.com').split(','),
      };
    case Environment.STAGING:
      // In staging, allow staging domains
      return {
        ...corsConfig,
        origin: getEnv('CORS_ORIGIN', 'https://staging.dollarfunding.com').split(','),
      };
    default:
      // In development, allow all origins
      return corsConfig;
  }
}

// Determine the current environment
const environment = getEnvironment();

// Base configuration shared across all environments
const baseConfig: IAppConfig = {
  name: 'notification-service',
  version: getEnv('npm_package_version', '1.0.0'),
  environment,
  port: getNumericEnv('PORT', 3004),
  baseUrl: getEnv('BASE_URL', 'http://localhost:3004'),
  correlationIdHeader: 'X-Correlation-ID',
  enableRequestLogging: getBooleanEnv('ENABLE_REQUEST_LOGGING', true),
  enableCompression: getBooleanEnv('ENABLE_COMPRESSION', true),
  maxBodySize: getEnv('MAX_BODY_SIZE', '1mb'),
  requestTimeout: getNumericEnv('REQUEST_TIMEOUT', 30000), // 30 seconds
  cors: getCorsConfig(environment),
};

// Environment-specific configurations
const environmentConfigs: Record<Environment, Partial<IAppConfig>> = {
  [Environment.DEVELOPMENT]: {
    enableRequestLogging: true,
  },
  [Environment.STAGING]: {
    enableRequestLogging: true,
  },
  [Environment.PRODUCTION]: {
    enableRequestLogging: getBooleanEnv('ENABLE_REQUEST_LOGGING', false),
  },
  [Environment.TEST]: {
    port: getNumericEnv('TEST_PORT', 3005),
    enableRequestLogging: false,
  },
};

// Merge base config with environment-specific config
export const appConfig: IAppConfig = {
  ...baseConfig,
  ...environmentConfigs[environment],
};

export default appConfig;