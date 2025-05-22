/**
 * Type definitions for RabbitMQ message structures, exchange configurations, and queue operations
 * used by the Email Service to publish extracted email attachments to the message queue.
 */

/**
 * RabbitMQ connection configuration parameters
 */
export interface IRabbitMQConfig {
  /** RabbitMQ server hostname */
  host: string;
  /** RabbitMQ server port (default: 5672, or 5671 for TLS) */
  port: number;
  /** RabbitMQ username */
  username: string;
  /** RabbitMQ password */
  password: string;
  /** RabbitMQ virtual host (default: '/') */
  vhost: string;
  /** Whether to use TLS for the connection */
  useTls: boolean;
  /** Path to client certificate for TLS authentication (optional) */
  certPath?: string;
  /** Path to client key for TLS authentication (optional) */
  keyPath?: string;
  /** Path to CA certificate for TLS authentication (optional) */
  caPath?: string;
  /** Connection timeout in milliseconds */
  connectionTimeout: number;
  /** Heartbeat interval in seconds */
  heartbeat: number;
}

/**
 * Exchange configuration for RabbitMQ
 */
export interface IExchangeConfig {
  /** Exchange name */
  name: string;
  /** Exchange type (direct, fanout, topic, headers) */
  type: 'direct' | 'fanout' | 'topic' | 'headers';
  /** Whether the exchange should survive broker restarts */
  durable: boolean;
  /** Whether the exchange should be deleted when no longer used */
  autoDelete: boolean;
  /** Exchange arguments */
  arguments?: Record<string, any>;
}

/**
 * Queue configuration for RabbitMQ
 */
export interface IQueueConfig {
  /** Queue name */
  name: string;
  /** Whether the queue should survive broker restarts */
  durable: boolean;
  /** Whether the queue should be deleted when no longer used */
  autoDelete: boolean;
  /** Whether the queue is exclusive to the connection */
  exclusive: boolean;
  /** Queue arguments */
  arguments?: Record<string, any>;
}

/**
 * Message publishing options
 */
export interface IPublishOptions {
  /** Content type of the message (default: 'application/json') */
  contentType: string;
  /** Content encoding of the message */
  contentEncoding?: string;
  /** Message priority (0-9) */
  priority?: number;
  /** Message correlation ID */
  correlationId?: string;
  /** Reply to queue or exchange */
  replyTo?: string;
  /** Message expiration time in milliseconds */
  expiration?: string;
  /** Message ID */
  messageId?: string;
  /** Message timestamp */
  timestamp?: number;
  /** Message type */
  type?: string;
  /** User ID */
  userId?: string;
  /** Application ID */
  appId?: string;
  /** Cluster ID */
  clusterId?: string;
  /** Delivery mode (1 = non-persistent, 2 = persistent) */
  deliveryMode: 1 | 2;
  /** Custom headers */
  headers?: Record<string, any>;
}

/**
 * Email attachment metadata for message payload
 */
export interface IAttachmentMetadata {
  /** Original filename of the attachment */
  filename: string;
  /** Content type of the attachment */
  contentType: string;
  /** Size of the attachment in bytes */
  size: number;
  /** MD5 hash of the attachment content */
  contentMd5?: string;
  /** S3 storage path where the attachment is stored */
  storagePath?: string;
  /** Timestamp when the attachment was processed */
  processedAt: string;
}

/**
 * Email metadata for message payload
 */
export interface IEmailMetadata {
  /** Email sender address */
  sender: string;
  /** Email recipient addresses */
  recipients: string[];
  /** Email subject */
  subject: string;
  /** Email received timestamp */
  receivedAt: string;
  /** Email message ID */
  messageId: string;
  /** Email headers */
  headers?: Record<string, string>;
}

/**
 * Message payload for document processing
 */
export interface IMessagePayload {
  /** Unique identifier for the message */
  id: string;
  /** Type of document being processed */
  documentType: string;
  /** Email metadata */
  emailMetadata: IEmailMetadata;
  /** Attachment metadata */
  attachmentMetadata: IAttachmentMetadata;
  /** S3 storage path where the document is stored */
  storagePath: string;
  /** Timestamp when the message was created */
  timestamp: string;
  /** Version of the message format */
  version: string;
  /** Additional properties */
  [key: string]: any;
}

/**
 * Connection state for RabbitMQ
 */
export enum ConnectionState {
  DISCONNECTED = 'DISCONNECTED',
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  RECONNECTING = 'RECONNECTING',
  CLOSING = 'CLOSING',
  CLOSED = 'CLOSED',
}

/**
 * Connection event types for RabbitMQ
 */
export enum ConnectionEventType {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
  CLOSE = 'close',
  BLOCKED = 'blocked',
  UNBLOCKED = 'unblocked',
}

/**
 * Retry configuration for RabbitMQ operations
 */
export interface IRetryConfig {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial retry delay in milliseconds */
  initialDelay: number;
  /** Maximum retry delay in milliseconds */
  maxDelay: number;
  /** Factor by which the delay increases with each retry */
  backoffFactor: number;
  /** Whether to add jitter to the delay to prevent thundering herd */
  jitter: boolean;
}

/**
 * Default exchange configuration for the MCA documents exchange
 */
export const DEFAULT_MCA_EXCHANGE: IExchangeConfig = {
  name: 'mca.documents',
  type: 'fanout',
  durable: true,
  autoDelete: false,
};

/**
 * Default publish options for document messages
 */
export const DEFAULT_PUBLISH_OPTIONS: IPublishOptions = {
  contentType: 'application/json',
  contentEncoding: 'utf-8',
  deliveryMode: 2, // persistent
  headers: {
    'x-source': 'email-service',
  },
};

/**
 * Default retry configuration for RabbitMQ operations
 */
export const DEFAULT_RETRY_CONFIG: IRetryConfig = {
  maxRetries: 5,
  initialDelay: 1000, // 1 second
  maxDelay: 60000, // 1 minute
  backoffFactor: 2,
  jitter: true,
};