/**
 * Configuration Types
 * 
 * This file defines TypeScript interfaces for configuration settings used throughout
 * the Notification Service. It provides type definitions for application, logger,
 * Redis, webhook, RabbitMQ, notification, and retry configurations.
 */

import { IRetryOptions } from './common';

/**
 * Interface for core application settings
 */
export interface IAppConfig {
  /** Application name */
  name: string;
  /** Application version */
  version: string;
  /** Environment (development, staging, production) */
  environment: string;
  /** HTTP port to listen on */
  port: number;
  /** Base URL for the service */
  baseUrl: string;
  /** Shutdown timeout in milliseconds */
  shutdownTimeoutMs: number;
}

/**
 * Interface for logging configuration
 */
export interface ILoggerConfig {
  /** Log level (error, warn, info, debug) */
  level: string;
  /** Log format (json, pretty) */
  format: 'json' | 'pretty';
  /** Whether to include timestamps in logs */
  timestamp: boolean;
  /** Additional logger-specific options */
  options?: {
    /** Directory for log files */
    logDir?: string;
    /** Maximum log file size in bytes */
    maxSize?: number;
    /** Maximum number of log files to keep */
    maxFiles?: number;
    /** Whether to log to console */
    console?: boolean;
    /** Whether to log to file */
    file?: boolean;
  };
}

/**
 * Interface for Redis connection and caching settings
 */
export interface IRedisConfig {
  /** Redis host */
  host: string;
  /** Redis port */
  port: number;
  /** Redis password */
  password: string;
  /** Whether to use TLS for Redis connection */
  enableTLS: boolean;
  /** TTL settings for different data types */
  ttl: {
    /** TTL for application data in seconds */
    applicationData: number;
    /** TTL for user sessions in seconds */
    userSessions: number;
  };
  /** Redis database index */
  db?: number;
  /** Redis connection options */
  options?: {
    /** Connection timeout in milliseconds */
    connectTimeout?: number;
    /** Command timeout in milliseconds */
    commandTimeout?: number;
    /** Whether to retry failed commands */
    enableRetryStrategy?: boolean;
    /** Maximum number of retries for failed commands */
    maxRetries?: number;
  };
}

/**
 * Interface for webhook delivery configuration
 */
export interface IWebhookConfig {
  /** Default timeout for webhook requests in milliseconds */
  timeoutMs: number;
  /** Retry options for failed webhook deliveries */
  retry: IRetryOptions;
  /** HMAC signature settings */
  signature: {
    /** Whether to sign webhook payloads */
    enabled: boolean;
    /** Algorithm to use for signatures */
    algorithm: 'sha256' | 'sha512';
    /** Header name for the signature */
    headerName: string;
    /** Header name for the timestamp */
    timestampHeaderName: string;
    /** Maximum age of timestamp in seconds */
    maxTimestampAge: number;
  };
  /** Default headers to include in webhook requests */
  defaultHeaders?: Record<string, string>;
}

/**
 * Interface for RabbitMQ connection and settings
 */
export interface IRabbitMQConfig {
  /** RabbitMQ host */
  host: string;
  /** RabbitMQ port */
  port: number;
  /** RabbitMQ username */
  username: string;
  /** RabbitMQ password */
  password: string;
  /** RabbitMQ virtual host */
  vhost: string;
  /** Whether to use TLS for RabbitMQ connection */
  enableTLS: boolean;
  /** Exchange name */
  exchange: string;
  /** Queue name */
  queue: string;
  /** Routing key */
  routingKey: string;
  /** Connection options */
  options?: {
    /** Connection timeout in milliseconds */
    connectTimeout?: number;
    /** Heartbeat interval in seconds */
    heartbeat?: number;
    /** Whether to automatically reconnect */
    reconnect?: boolean;
    /** Path to client certificate for TLS */
    certPath?: string;
    /** Path to client key for TLS */
    keyPath?: string;
    /** Path to CA certificate for TLS */
    caPath?: string;
  };
}

/**
 * Interface for notification delivery settings
 */
export interface INotificationConfig {
  /** Default notification channel */
  defaultChannel: 'webhook' | 'email' | 'sms' | 'push';
  /** Whether to batch notifications */
  enableBatching: boolean;
  /** Maximum batch size */
  maxBatchSize: number;
  /** Batch interval in milliseconds */
  batchIntervalMs: number;
  /** Channel-specific configurations */
  channels: {
    /** Webhook channel configuration */
    webhook: IWebhookConfig;
    /** Email channel configuration */
    email?: {
      /** SMTP server */
      host: string;
      /** SMTP port */
      port: number;
      /** SMTP username */
      username: string;
      /** SMTP password */
      password: string;
      /** Whether to use TLS */
      secure: boolean;
      /** Default sender email */
      defaultFrom: string;
    };
    /** SMS channel configuration */
    sms?: {
      /** SMS provider API key */
      apiKey: string;
      /** SMS provider API URL */
      apiUrl: string;
      /** Default sender phone number */
      defaultFrom: string;
    };
    /** Push notification channel configuration */
    push?: {
      /** Push notification provider */
      provider: string;
      /** Provider API key */
      apiKey: string;
      /** Provider API URL */
      apiUrl: string;
    };
  };
}