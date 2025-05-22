/**
 * Configuration type definitions for the Notification Service
 * 
 * This file defines TypeScript interfaces for configuration settings used throughout
 * the Notification Service. It provides type definitions for application, logger,
 * Redis, webhook, RabbitMQ, notification, and retry configurations.
 */

/**
 * Log levels supported by the Notification Service
 */
export enum LogLevel {
  ERROR = 'error',
  WARN = 'warn',
  INFO = 'info',
  DEBUG = 'debug'
}

/**
 * Environment types for the Notification Service
 */
export enum Environment {
  DEVELOPMENT = 'development',
  STAGING = 'staging',
  PRODUCTION = 'production',
  TEST = 'test'
}

/**
 * Core application configuration interface
 */
export interface IAppConfig {
  /** Application name */
  name: string;
  /** Application version */
  version: string;
  /** Environment (development, staging, production, test) */
  environment: Environment;
  /** HTTP server port */
  port: number;
  /** Base URL for the service */
  baseUrl: string;
  /** Correlation ID header name for distributed tracing */
  correlationIdHeader: string;
  /** Enable/disable request logging */
  enableRequestLogging: boolean;
  /** Enable/disable response compression */
  enableCompression: boolean;
  /** Maximum request body size in bytes */
  maxBodySize: string;
  /** Request timeout in milliseconds */
  requestTimeout: number;
  /** Enable/disable CORS */
  cors: {
    /** Enable/disable CORS */
    enabled: boolean;
    /** Allowed origins */
    origin: string | string[];
    /** Allowed methods */
    methods: string[];
    /** Allowed headers */
    allowedHeaders: string[];
    /** Exposed headers */
    exposedHeaders: string[];
    /** Allow credentials */
    credentials: boolean;
    /** Max age in seconds */
    maxAge: number;
  };
}

/**
 * Logger configuration interface
 */
export interface ILoggerConfig {
  /** Log level (error, warn, info, debug) */
  level: LogLevel;
  /** Enable/disable pretty printing for development */
  prettyPrint: boolean;
  /** Enable/disable colorized output */
  colorize: boolean;
  /** Log file path (if file logging is enabled) */
  filePath?: string;
  /** Maximum log file size in bytes before rotation */
  maxFileSize?: number;
  /** Maximum number of log files to keep */
  maxFiles?: number;
  /** Enable/disable logging to console */
  console: boolean;
  /** Additional fields to include in every log entry */
  defaultMeta: Record<string, any>;
  /** Redact sensitive information patterns */
  redactPatterns: RegExp[];
}

/**
 * Redis configuration interface
 */
export interface IRedisConfig {
  /** Redis host */
  host: string;
  /** Redis port */
  port: number;
  /** Redis password */
  password?: string;
  /** Redis database number */
  db: number;
  /** Enable/disable TLS */
  tls: boolean;
  /** TLS certificate authority path */
  tlsCA?: string;
  /** TLS certificate path */
  tlsCert?: string;
  /** TLS key path */
  tlsKey?: string;
  /** Connection timeout in milliseconds */
  connectTimeout: number;
  /** Command timeout in milliseconds */
  commandTimeout: number;
  /** Enable/disable automatic reconnection */
  autoReconnect: boolean;
  /** Maximum reconnection attempts */
  maxReconnectAttempts: number;
  /** Reconnection interval in milliseconds */
  reconnectInterval: number;
  /** Enable/disable cluster mode */
  cluster: boolean;
  /** Cluster nodes (if cluster mode is enabled) */
  clusterNodes?: Array<{ host: string; port: number }>;
  /** Key prefix for all Redis keys */
  keyPrefix: string;
  /** Default TTL for application data in seconds (15 minutes) */
  defaultDataTTL: number;
  /** Default TTL for session data in seconds (24 hours) */
  defaultSessionTTL: number;
  /** Enable/disable Redis as a rate limiter */
  enableRateLimiter: boolean;
  /** Maximum number of connections in the pool */
  maxConnections: number;
}

/**
 * Webhook configuration interface
 */
export interface IWebhookConfig {
  /** Default timeout for webhook requests in milliseconds */
  defaultTimeout: number;
  /** Maximum payload size in bytes */
  maxPayloadSize: number;
  /** Enable/disable webhook signature validation */
  enableSignature: boolean;
  /** Signature algorithm (e.g., 'sha256') */
  signatureAlgorithm: string;
  /** Signature header name */
  signatureHeader: string;
  /** Enable/disable payload validation */
  validatePayload: boolean;
  /** Default webhook endpoint URL (for testing) */
  defaultEndpoint?: string;
  /** Enable/disable webhook batching */
  enableBatching: boolean;
  /** Maximum batch size */
  maxBatchSize: number;
  /** Batch interval in milliseconds */
  batchInterval: number;
  /** Enable/disable webhook delivery metrics */
  enableMetrics: boolean;
  /** Enable/disable webhook delivery logging */
  enableLogging: boolean;
  /** Default webhook headers */
  defaultHeaders: Record<string, string>;
}

/**
 * RabbitMQ configuration interface
 */
export interface IRabbitMQConfig {
  /** Connection URI */
  uri: string;
  /** RabbitMQ host */
  host: string;
  /** RabbitMQ port */
  port: number;
  /** RabbitMQ virtual host */
  vhost: string;
  /** RabbitMQ username */
  username: string;
  /** RabbitMQ password */
  password: string;
  /** Enable/disable TLS */
  tls: boolean;
  /** TLS certificate authority path */
  tlsCA?: string;
  /** TLS certificate path */
  tlsCert?: string;
  /** TLS key path */
  tlsKey?: string;
  /** Connection timeout in milliseconds */
  connectTimeout: number;
  /** Heartbeat interval in seconds */
  heartbeat: number;
  /** Enable/disable automatic reconnection */
  autoReconnect: boolean;
  /** Maximum reconnection attempts */
  maxReconnectAttempts: number;
  /** Reconnection interval in milliseconds */
  reconnectInterval: number;
  /** Exchange name */
  exchange: string;
  /** Exchange type (direct, fanout, topic, headers) */
  exchangeType: string;
  /** Enable/disable exchange durability */
  exchangeDurable: boolean;
  /** Queue name */
  queue: string;
  /** Enable/disable queue durability */
  queueDurable: boolean;
  /** Routing key for binding queue to exchange */
  routingKey: string;
  /** Message acknowledgment mode (auto, manual) */
  ackMode: 'auto' | 'manual';
  /** Prefetch count for consumer */
  prefetchCount: number;
  /** Dead letter exchange name */
  deadLetterExchange?: string;
  /** Dead letter routing key */
  deadLetterRoutingKey?: string;
  /** Message time-to-live in milliseconds */
  messageTTL?: number;
  /** Enable/disable message persistence */
  persistentMessages: boolean;
}

/**
 * Notification configuration interface
 */
export interface INotificationConfig {
  /** Default notification type */
  defaultType: string;
  /** Default notification priority */
  defaultPriority: string;
  /** Enable/disable email notifications */
  enableEmail: boolean;
  /** Enable/disable SMS notifications */
  enableSMS: boolean;
  /** Enable/disable push notifications */
  enablePush: boolean;
  /** Enable/disable webhook notifications */
  enableWebhook: boolean;
  /** Default email sender address */
  defaultEmailSender?: string;
  /** Default SMS sender ID */
  defaultSMSSender?: string;
  /** Default push notification title */
  defaultPushTitle?: string;
  /** Enable/disable notification batching */
  enableBatching: boolean;
  /** Maximum batch size */
  maxBatchSize: number;
  /** Batch interval in milliseconds */
  batchInterval: number;
  /** Enable/disable notification delivery metrics */
  enableMetrics: boolean;
  /** Enable/disable notification delivery logging */
  enableLogging: boolean;
  /** Template directory path */
  templateDir?: string;
}

/**
 * Retry configuration interface
 */
export interface IRetryConfig {
  /** Enable/disable retry mechanism */
  enabled: boolean;
  /** Maximum number of retry attempts */
  maxAttempts: number;
  /** Initial retry delay in milliseconds */
  initialDelay: number;
  /** Maximum retry delay in milliseconds */
  maxDelay: number;
  /** Retry delay multiplier for exponential backoff */
  backoffMultiplier: number;
  /** Enable/disable jitter for retry delays */
  enableJitter: boolean;
  /** Retry status codes (HTTP status codes that should trigger a retry) */
  retryStatusCodes: number[];
  /** Retry error types (error types that should trigger a retry) */
  retryErrorTypes: string[];
  /** Enable/disable retry logging */
  enableLogging: boolean;
}

/**
 * Complete configuration interface for the Notification Service
 */
export interface IConfig {
  /** Application configuration */
  app: IAppConfig;
  /** Logger configuration */
  logger: ILoggerConfig;
  /** Redis configuration */
  redis: IRedisConfig;
  /** Webhook configuration */
  webhook: IWebhookConfig;
  /** RabbitMQ configuration */
  rabbitmq: IRabbitMQConfig;
  /** Notification configuration */
  notification: INotificationConfig;
  /** Retry configuration */
  retry: IRetryConfig;
}