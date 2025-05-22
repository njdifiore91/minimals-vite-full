/**
 * Email Service Application Configuration
 * 
 * This module defines and exports the core application configuration for the Email Service microservice.
 * It centralizes environment variables, application settings, and environment-specific configurations
 * (development, staging, production).
 * 
 * The configuration is loaded from environment variables and validated to ensure all required values
 * are present and properly formatted.
 */

import { config as dotenvConfig } from 'dotenv';
import * as path from 'path';

// Load environment variables from .env file if not in production
if (process.env.NODE_ENV !== 'production') {
  const envPath = path.resolve(process.cwd(), '.env');
  dotenvConfig({ path: envPath });
}

/**
 * Configuration validation error
 */
export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

/**
 * Get required environment variable
 * Throws ConfigError if the variable is not defined
 */
function getRequiredEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new ConfigError(`Required environment variable ${key} is not defined`);
  }
  return value;
}

/**
 * Get optional environment variable with default value
 */
function getOptionalEnv(key: string, defaultValue: string): string {
  return process.env[key] || defaultValue;
}

/**
 * Parse boolean environment variable
 */
function parseBooleanEnv(key: string, defaultValue: boolean): boolean {
  const value = process.env[key];
  if (value === undefined) {
    return defaultValue;
  }
  return value.toLowerCase() === 'true';
}

/**
 * Parse number environment variable
 */
function parseNumberEnv(key: string, defaultValue: number): number {
  const value = process.env[key];
  if (value === undefined) {
    return defaultValue;
  }
  const parsed = parseInt(value, 10);
  if (isNaN(parsed)) {
    throw new ConfigError(`Environment variable ${key} is not a valid number`);
  }
  return parsed;
}

/**
 * Parse comma-separated list environment variable
 */
function parseListEnv(key: string, defaultValue: string[]): string[] {
  const value = process.env[key];
  if (value === undefined) {
    return defaultValue;
  }
  return value.split(',').map(item => item.trim());
}

/**
 * Environment type
 */
export type Environment = 'development' | 'staging' | 'production';

/**
 * Log level type
 */
export type LogLevel = 'error' | 'warn' | 'info' | 'debug';

/**
 * IMAP configuration
 */
export interface ImapConfig {
  server: string;
  port: number;
  user: string;
  password: string;
  tlsEnabled: boolean;
  rejectUnauthorized: boolean;
  mailbox: string;
  searchCriteria: string;
}

/**
 * RabbitMQ configuration
 */
export interface RabbitMQConfig {
  host: string;
  port: number;
  user: string;
  password: string;
  vhost: string;
  exchange: string;
  queue: string;
  tlsEnabled: boolean;
  certPath: string;
  keyPath: string;
  caPath: string;
}

/**
 * S3 storage configuration
 */
export interface S3Config {
  endpoint: string;
  region: string;
  bucket: string;
  accessKey: string;
  secretKey: string;
  useSsl: boolean;
  forcePathStyle: boolean;
  encryptionEnabled: boolean;
  uploadTimeoutMs: number;
}

/**
 * Email processing configuration
 */
export interface EmailProcessingConfig {
  maxAttachmentSizeMb: number;
  allowedAttachmentTypes: string[];
  attachmentStoragePath: string;
}

/**
 * Retry and error handling configuration
 */
export interface RetryConfig {
  maxRetryAttempts: number;
  retryDelayMs: number;
  errorNotificationEmail: string;
}

/**
 * Application configuration
 */
export interface AppConfig {
  env: Environment;
  name: string;
  version: string;
  port: number;
  logLevel: LogLevel;
  emailPollingIntervalMs: number;
  imap: ImapConfig;
  rabbitmq: RabbitMQConfig;
  s3: S3Config;
  emailProcessing: EmailProcessingConfig;
  retry: RetryConfig;
}

/**
 * Load and validate configuration
 */
export function loadConfig(): AppConfig {
  // Determine environment
  const env = (getOptionalEnv('NODE_ENV', 'development') as Environment);
  if (env !== 'development' && env !== 'staging' && env !== 'production') {
    throw new ConfigError(`Invalid NODE_ENV: ${env}. Must be one of: development, staging, production`);
  }

  // Load application configuration
  const config: AppConfig = {
    env,
    name: getOptionalEnv('APP_NAME', 'email-service'),
    version: getOptionalEnv('APP_VERSION', '1.0.0'),
    port: parseNumberEnv('PORT', 3000),
    logLevel: (getOptionalEnv('LOG_LEVEL', env === 'production' ? 'info' : 'debug') as LogLevel),
    emailPollingIntervalMs: parseNumberEnv('EMAIL_POLLING_INTERVAL_MS', 60000), // Default: 1 minute

    // IMAP configuration
    imap: {
      server: getRequiredEnv('IMAP_SERVER'),
      port: parseNumberEnv('IMAP_PORT', 993),
      user: getRequiredEnv('IMAP_USER'),
      password: getRequiredEnv('IMAP_PASSWORD'),
      tlsEnabled: parseBooleanEnv('IMAP_TLS_ENABLED', true),
      rejectUnauthorized: parseBooleanEnv('IMAP_REJECT_UNAUTHORIZED', true),
      mailbox: getOptionalEnv('IMAP_MAILBOX', 'INBOX'),
      searchCriteria: getOptionalEnv('IMAP_SEARCH_CRITERIA', 'UNSEEN'),
    },

    // RabbitMQ configuration
    rabbitmq: {
      host: getRequiredEnv('RABBITMQ_HOST'),
      port: parseNumberEnv('RABBITMQ_PORT', 5672),
      user: getRequiredEnv('RABBITMQ_USER'),
      password: getRequiredEnv('RABBITMQ_PASSWORD'),
      vhost: getOptionalEnv('RABBITMQ_VHOST', '/'),
      exchange: getOptionalEnv('RABBITMQ_EXCHANGE', 'mca.documents'),
      queue: getOptionalEnv('RABBITMQ_QUEUE', 'document-processing'),
      tlsEnabled: parseBooleanEnv('RABBITMQ_TLS_ENABLED', env !== 'development'),
      certPath: getOptionalEnv('RABBITMQ_CERT_PATH', ''),
      keyPath: getOptionalEnv('RABBITMQ_KEY_PATH', ''),
      caPath: getOptionalEnv('RABBITMQ_CA_PATH', ''),
    },

    // S3 storage configuration
    s3: {
      endpoint: getRequiredEnv('S3_ENDPOINT'),
      region: getOptionalEnv('S3_REGION', 'us-east-1'),
      bucket: getOptionalEnv('S3_BUCKET', env === 'production' ? 'mca-documents-production' : 'mca-documents-staging'),
      accessKey: getRequiredEnv('S3_ACCESS_KEY'),
      secretKey: getRequiredEnv('S3_SECRET_KEY'),
      useSsl: parseBooleanEnv('S3_USE_SSL', true),
      forcePathStyle: parseBooleanEnv('S3_FORCE_PATH_STYLE', false),
      encryptionEnabled: parseBooleanEnv('S3_ENCRYPTION_ENABLED', true),
      uploadTimeoutMs: parseNumberEnv('S3_UPLOAD_TIMEOUT_MS', 30000), // Default: 30 seconds
    },

    // Email processing configuration
    emailProcessing: {
      maxAttachmentSizeMb: parseNumberEnv('MAX_ATTACHMENT_SIZE_MB', 25), // Default: 25MB
      allowedAttachmentTypes: parseListEnv('ALLOWED_ATTACHMENT_TYPES', [
        'application/pdf',
        'image/tiff',
        'image/png',
        'image/jpeg',
      ]),
      attachmentStoragePath: getOptionalEnv('ATTACHMENT_STORAGE_PATH', 'attachments'),
    },

    // Retry and error handling configuration
    retry: {
      maxRetryAttempts: parseNumberEnv('MAX_RETRY_ATTEMPTS', 3),
      retryDelayMs: parseNumberEnv('RETRY_DELAY_MS', 5000), // Default: 5 seconds
      errorNotificationEmail: getOptionalEnv('ERROR_NOTIFICATION_EMAIL', 'errors@dollarfunding.com'),
    },
  };

  // Validate environment-specific requirements
  if (env !== 'development') {
    // In staging and production, TLS must be enabled for IMAP
    if (!config.imap.tlsEnabled) {
      throw new ConfigError('TLS must be enabled for IMAP in staging and production environments');
    }

    // In staging and production, TLS must be enabled for RabbitMQ
    if (!config.rabbitmq.tlsEnabled) {
      throw new ConfigError('TLS must be enabled for RabbitMQ in staging and production environments');
    }

    // In staging and production, certificate paths must be provided for RabbitMQ TLS
    if (config.rabbitmq.tlsEnabled) {
      if (!config.rabbitmq.certPath || !config.rabbitmq.keyPath || !config.rabbitmq.caPath) {
        throw new ConfigError('Certificate paths must be provided for RabbitMQ TLS in staging and production environments');
      }
    }

    // In staging and production, encryption must be enabled for S3
    if (!config.s3.encryptionEnabled) {
      throw new ConfigError('Encryption must be enabled for S3 in staging and production environments');
    }
  }

  return config;
}

/**
 * Default configuration instance
 */
export const appConfig = loadConfig();

/**
 * Export default configuration
 */
export default appConfig;