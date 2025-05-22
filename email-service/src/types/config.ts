/**
 * Configuration Type Definitions
 * 
 * This file defines TypeScript interfaces for Email Service configuration, environment variables,
 * and application settings. It provides type definitions for service configuration, ensuring
 * consistent and type-safe access to configuration values throughout the codebase.
 * 
 * The configuration system supports different environment configurations (development, staging, production)
 * and provides validation for environment variables to ensure required values are present.
 */

import { ILogLevel } from './common';

// ----------------------------------------------------------------------

/**
 * Supported deployment environments
 */
export type Environment = 'development' | 'staging' | 'production';

/**
 * Application-wide configuration settings
 */
export interface IAppConfig {
  /** Service name for identification in logs and metrics */
  serviceName: string;
  /** Service version for tracking and compatibility */
  version: string;
  /** HTTP port the service listens on */
  port: number;
  /** Current deployment environment */
  environment: Environment;
  /** Node environment (development, production, test) */
  nodeEnv: string;
  /** Debug mode flag */
  debug: boolean;
}

/**
 * S3 storage configuration
 */
export interface IS3Config {
  /** S3 endpoint URL */
  endpoint: string;
  /** Whether to use path style URLs */
  forcePathStyle: boolean;
  /** AWS region */
  region: string;
  /** S3 access key */
  accessKey: string;
  /** S3 secret key */
  secretKey: string;
  /** Production environment bucket name */
  productionBucket: string;
  /** Staging environment bucket name */
  stagingBucket: string;
  /** Development environment bucket name */
  developmentBucket: string;
  /** Whether to use SSL for S3 connections */
  sslEnabled: boolean;
  /** Connection timeout in milliseconds */
  connectionTimeout: number;
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Whether to use server-side encryption */
  useEncryption: boolean;
}

/**
 * TLS configuration options
 */
export interface ITlsOptions {
  /** Whether TLS is required */
  required: boolean;
  /** Minimum TLS version */
  minVersion: string;
  /** Whether to reject unauthorized certificates */
  rejectUnauthorized: boolean;
}

/**
 * IMAP email server configuration
 */
export interface IImapConfig {
  /** IMAP server hostname */
  host: string;
  /** IMAP server port */
  port: number;
  /** Whether to use TLS */
  tls: boolean;
  /** TLS configuration options */
  tlsOptions: ITlsOptions;
  /** IMAP username */
  user: string;
  /** IMAP password */
  password: string;
  /** Mailbox to monitor (default: INBOX) */
  mailbox: string;
  /** Email polling interval in milliseconds */
  pollingInterval: number;
  /** Connection timeout in milliseconds */
  connectionTimeout: number;
  /** IDLE command timeout in milliseconds */
  idleTimeout: number;
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial delay between retries in milliseconds */
  retryDelay: number;
}

/**
 * RabbitMQ connection configuration
 */
export interface IRabbitMQConfig {
  /** RabbitMQ server hostname */
  host: string;
  /** RabbitMQ server port */
  port: number;
  /** RabbitMQ virtual host */
  vhost: string;
  /** RabbitMQ username */
  username: string;
  /** RabbitMQ password */
  password: string;
  /** Whether to use TLS */
  useTls: boolean;
  /** Connection timeout in milliseconds */
  connectionTimeout: number;
  /** Heartbeat interval in seconds */
  heartbeat: number;
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial delay between retries in milliseconds */
  retryDelay: number;
}

/**
 * RabbitMQ exchange configuration
 */
export interface IExchangeConfig {
  /** Exchange name */
  name: string;
  /** Exchange type (direct, fanout, topic, headers) */
  type: 'direct' | 'fanout' | 'topic' | 'headers';
  /** Whether the exchange is durable */
  durable: boolean;
  /** Whether the exchange is automatically deleted when no longer used */
  autoDelete: boolean;
}

/**
 * RabbitMQ message configuration
 */
export interface IMessageConfig {
  /** Message content type */
  contentType: string;
  /** Message content encoding */
  contentEncoding: string;
  /** Message delivery mode (1 = non-persistent, 2 = persistent) */
  deliveryMode: 1 | 2;
  /** Message priority */
  priority: number;
  /** Whether to use publisher confirms */
  usePublisherConfirms: boolean;
}

/**
 * Logging configuration
 */
export interface ILoggingConfig {
  /** Log level */
  level: ILogLevel;
  /** Whether to use pretty printing for logs */
  prettyPrint: boolean;
  /** Whether to include timestamps in logs */
  timestamp: boolean;
  /** Whether to colorize log output */
  colorize: boolean;
  /** Whether to log to a file */
  logToFile: boolean;
  /** Path to log file */
  logFilePath?: string;
  /** Maximum log file size in bytes */
  maxLogFileSize: number;
  /** Maximum number of log files to keep */
  maxLogFiles: number;
}

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

/**
 * Combined service configuration
 */
export interface IServiceConfig {
  /** Application configuration */
  app: IAppConfig;
  /** Environment-specific configuration */
  env: IEnvironmentConfig;
}

/**
 * Environment variable schema definition
 */
export interface IEnvSchema {
  /** Environment variable name */
  name: string;
  /** Whether the environment variable is required */
  required: boolean;
  /** Default value if not provided */
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
  /** Validation error messages */
  errors: string[];
  /** Validated environment variables */
  env: Record<string, string>;
}