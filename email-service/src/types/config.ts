/**
 * Configuration type definitions for the Email Service
 * 
 * This file defines TypeScript interfaces for Email Service configuration,
 * environment variables, and application settings. It provides type definitions
 * for service configuration, ensuring consistent and type-safe access to
 * configuration values throughout the codebase.
 */

import { ILogLevel } from './common';

// ----------------------------------------------------------------------
// Environment Configuration
// ----------------------------------------------------------------------

/**
 * Environment names supported by the application
 */
export type Environment = 'development' | 'staging' | 'production';

/**
 * Environment variable schema for validation
 */
export interface IEnvSchema {
  /** Variable name */
  name: string;
  /** Whether the variable is required */
  required: boolean;
  /** Default value if not provided (for non-required variables) */
  default?: string;
  /** Validation function */
  validate?: (value: string) => boolean;
  /** Error message if validation fails */
  errorMessage?: string;
}

/**
 * Environment variable validation result
 */
export interface IEnvValidationResult {
  /** Whether validation was successful */
  isValid: boolean;
  /** Error messages if validation failed */
  errors: string[];
  /** Validated environment variables */
  env: Record<string, string>;
}

// ----------------------------------------------------------------------
// Application Configuration
// ----------------------------------------------------------------------

/**
 * Application configuration settings
 */
export interface IAppConfig {
  /** Service name */
  serviceName: string;
  /** Service version */
  version: string;
  /** HTTP port for the service */
  port: number;
  /** Current environment */
  environment: Environment;
  /** Node environment (development, production) */
  nodeEnv: string;
  /** Whether the service is running in debug mode */
  debug: boolean;
}

// ----------------------------------------------------------------------
// IMAP Configuration
// ----------------------------------------------------------------------

/**
 * TLS options for IMAP connection
 */
export interface IImapTlsOptions {
  /** Whether to require TLS */
  required: boolean;
  /** Minimum TLS version */
  minVersion: string;
  /** Whether to reject unauthorized certificates */
  rejectUnauthorized: boolean;
  /** Path to CA certificate file */
  ca?: string;
  /** Path to client certificate file */
  cert?: string;
  /** Path to client key file */
  key?: string;
}

/**
 * IMAP connection configuration
 */
export interface IImapConfig {
  /** IMAP server host */
  host: string;
  /** IMAP server port */
  port: number;
  /** Whether to use TLS */
  tls: boolean;
  /** TLS options */
  tlsOptions: IImapTlsOptions;
  /** Authentication username */
  user: string;
  /** Authentication password */
  password: string;
  /** Mailbox to monitor */
  mailbox: string;
  /** Polling interval in milliseconds */
  pollingInterval: number;
  /** Connection timeout in milliseconds */
  connectionTimeout: number;
  /** Idle timeout in milliseconds */
  idleTimeout: number;
  /** Maximum connection retries */
  maxRetries: number;
  /** Retry delay in milliseconds */
  retryDelay: number;
}

// ----------------------------------------------------------------------
// RabbitMQ Configuration
// ----------------------------------------------------------------------

/**
 * RabbitMQ connection configuration
 */
export interface IRabbitMQConfig {
  /** RabbitMQ server host */
  host: string;
  /** RabbitMQ server port */
  port: number;
  /** Virtual host */
  vhost: string;
  /** Authentication username */
  username: string;
  /** Authentication password */
  password: string;
  /** Whether to use TLS */
  useTls: boolean;
  /** Connection timeout in milliseconds */
  connectionTimeout: number;
  /** Heartbeat interval in seconds */
  heartbeat: number;
  /** Maximum connection retries */
  maxRetries: number;
  /** Retry delay in milliseconds */
  retryDelay: number;
}

/**
 * RabbitMQ exchange configuration
 */
export interface IExchangeConfig {
  /** Exchange name */
  name: string;
  /** Exchange type */
  type: 'direct' | 'fanout' | 'topic' | 'headers';
  /** Whether the exchange is durable */
  durable: boolean;
  /** Whether the exchange auto-deletes when no longer used */
  autoDelete: boolean;
}

/**
 * RabbitMQ message configuration
 */
export interface IMessageConfig {
  /** Content type */
  contentType: string;
  /** Content encoding */
  contentEncoding: string;
  /** Delivery mode (1 = non-persistent, 2 = persistent) */
  deliveryMode: 1 | 2;
  /** Message priority */
  priority: number;
  /** Message expiration in milliseconds */
  expiration?: number;
  /** Whether to use publisher confirms */
  usePublisherConfirms: boolean;
}

// ----------------------------------------------------------------------
// S3 Storage Configuration
// ----------------------------------------------------------------------

/**
 * S3 storage configuration
 */
export interface IS3Config {
  /** S3 endpoint */
  endpoint: string;
  /** Whether to force path style */
  forcePathStyle: boolean;
  /** S3 region */
  region: string;
  /** S3 access key */
  accessKey: string;
  /** S3 secret key */
  secretKey: string;
  /** Production bucket name */
  productionBucket: string;
  /** Staging bucket name */
  stagingBucket: string;
  /** Development bucket name */
  developmentBucket: string;
  /** Whether to use SSL */
  sslEnabled: boolean;
  /** Connection timeout in milliseconds */
  connectionTimeout: number;
  /** Maximum retries */
  maxRetries: number;
  /** Whether to use AES-256 encryption */
  useEncryption: boolean;
}

// ----------------------------------------------------------------------
// Logging Configuration
// ----------------------------------------------------------------------

/**
 * Logging configuration
 */
export interface ILoggingConfig {
  /** Log level */
  level: ILogLevel;
  /** Whether to pretty print logs */
  prettyPrint: boolean;
  /** Whether to include timestamps */
  timestamp: boolean;
  /** Whether to colorize logs */
  colorize: boolean;
  /** Whether to log to file */
  logToFile: boolean;
  /** Log file path */
  logFilePath?: string;
  /** Maximum log file size in bytes */
  maxLogFileSize?: number;
  /** Maximum number of log files to keep */
  maxLogFiles?: number;
}

// ----------------------------------------------------------------------
// Environment-specific Configuration
// ----------------------------------------------------------------------

/**
 * Environment-specific configuration
 */
export interface IEnvironmentConfig {
  /** IMAP configuration */
  imap: IImapConfig;
  /** RabbitMQ configuration */
  rabbitmq: IRabbitMQConfig;
  /** RabbitMQ exchange configuration */
  exchange: IExchangeConfig;
  /** RabbitMQ message configuration */
  message: IMessageConfig;
  /** S3 configuration */
  s3: IS3Config;
  /** Logging configuration */
  logging: ILoggingConfig;
}

// ----------------------------------------------------------------------
// Service Configuration
// ----------------------------------------------------------------------

/**
 * Complete service configuration
 */
export interface IServiceConfig {
  /** Application configuration */
  app: IAppConfig;
  /** Environment-specific configuration */
  env: IEnvironmentConfig;
}

/**
 * Configuration loading options
 */
export interface IConfigLoadOptions {
  /** Path to .env file */
  envPath?: string;
  /** Whether to validate environment variables */
  validate?: boolean;
  /** Whether to throw on validation error */
  throwOnError?: boolean;
}