/**
 * Message Queue Type Definitions
 * 
 * This module defines TypeScript interfaces for RabbitMQ message structures,
 * exchange configurations, and queue operations used by the Email Service.
 * It provides type definitions for publishing extracted email attachments
 * to the message queue for processing by other services.
 *
 * The Email Service uses these types to publish messages to the 'mca.documents'
 * exchange (fanout) as specified in the technical requirements. Messages are
 * serialized in standardized JSON format and include document metadata and
 * processing information.
 *
 * Connection management types provide robust error handling and recovery
 * capabilities to ensure reliable message delivery even during temporary
 * RabbitMQ unavailability.
 */

import { IResult } from './common';

/**
 * RabbitMQ connection configuration
 */
export interface IRabbitMQConfig {
  /** RabbitMQ server hostname */
  host: string;
  
  /** RabbitMQ server port */
  port: number;
  
  /** RabbitMQ username */
  username: string;
  
  /** RabbitMQ password */
  password: string;
  
  /** RabbitMQ virtual host */
  vhost: string;
  
  /** Whether to use TLS for the connection */
  useTls: boolean;
  
  /** TLS certificate verification options */
  tlsOptions?: {
    /** CA certificate path for verification */
    ca?: string[];
    
    /** Whether to reject unauthorized connections */
    rejectUnauthorized: boolean;
  };
  
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
  arguments?: Record<string, unknown>;
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
  arguments?: Record<string, unknown>;
}

/**
 * Message publishing options
 */
export interface IPublishOptions {
  /** 
   * Delivery mode
   * 1 = Non-persistent (faster but messages may be lost if broker crashes)
   * 2 = Persistent (slower but messages survive broker crashes)
   */
  deliveryMode: 1 | 2;
  
  /** Message priority (0-9) */
  priority?: number;
  
  /** Message expiration in milliseconds */
  expiration?: string;
  
  /** Message ID */
  messageId?: string;
  
  /** Timestamp in seconds since the Epoch */
  timestamp?: number;
  
  /** Message type name */
  type?: string;
  
  /** Application ID */
  appId?: string;
  
  /** User ID */
  userId?: string;
  
  /** Content type (e.g., 'application/json') */
  contentType: string;
  
  /** Content encoding (e.g., 'utf-8') */
  contentEncoding?: string;
  
  /** Correlation ID */
  correlationId?: string;
  
  /** Reply to queue or exchange */
  replyTo?: string;
  
  /** Headers */
  headers?: Record<string, unknown>;
}

/**
 * Document message payload structure
 * Used for publishing document processing messages to RabbitMQ
 */
export interface IMessagePayload {
  /** Unique identifier for the document */
  documentId: string;
  
  /** S3 storage path where the document is stored */
  storagePath: string;
  
  /** Original filename */
  filename: string;
  
  /** File MIME type */
  mimeType: string;
  
  /** File size in bytes */
  fileSize: number;
  
  /** Document metadata */
  metadata: {
    /** Email sender information */
    sender: {
      /** Sender email address */
      email: string;
      
      /** Sender name if available */
      name?: string;
    };
    
    /** Email recipient information */
    recipient: {
      /** Recipient email address */
      email: string;
      
      /** Recipient name if available */
      name?: string;
    };
    
    /** Email subject */
    subject: string;
    
    /** Email received timestamp */
    receivedAt: string;
    
    /** Email message ID */
    messageId: string;
  };
  
  /** Processing information */
  processing: {
    /** Processing status */
    status: 'new' | 'processing' | 'completed' | 'failed';
    
    /** Timestamp when the document was received */
    receivedAt: string;
    
    /** Timestamp when processing started */
    startedAt?: string;
    
    /** Timestamp when processing completed */
    completedAt?: string;
    
    /** Error information if processing failed */
    error?: {
      /** Error message */
      message: string;
      
      /** Error code */
      code?: string;
    };
  };
}

/**
 * Connection management types for RabbitMQ
 */
export interface IConnectionManager {
  /** Current connection state */
  state: ConnectionState;
  
  /** Connect to RabbitMQ */
  connect(): Promise<IResult<void>>;
  
  /** Disconnect from RabbitMQ */
  disconnect(): Promise<IResult<void>>;
  
  /** Get the current connection */
  getConnection(): unknown;
  
  /** Get a channel from the connection */
  createChannel(): Promise<IResult<unknown>>;
  
  /** Check if connected to RabbitMQ */
  isConnected(): boolean;
  
  /** Add event listener for connection events */
  on(event: ConnectionEvent, listener: (data?: unknown) => void): void;
  
  /** Remove event listener */
  off(event: ConnectionEvent, listener: (data?: unknown) => void): void;
}

/**
 * Message publisher interface
 */
export interface IMessagePublisher {
  /**
   * Publish a message to an exchange
   * 
   * @param exchange - Exchange to publish to
   * @param routingKey - Routing key for the message
   * @param payload - Message payload
   * @param options - Publishing options
   */
  publish(
    exchange: string,
    routingKey: string,
    payload: IMessagePayload,
    options?: Partial<IPublishOptions>
  ): Promise<IResult<void>>;
  
  /**
   * Initialize the publisher
   */
  initialize(): Promise<IResult<void>>;
  
  /**
   * Close the publisher and release resources
   */
  close(): Promise<IResult<void>>;
}

/**
 * Connection states for RabbitMQ
 */
export enum ConnectionState {
  /** Not connected */
  DISCONNECTED = 'disconnected',
  
  /** Connection in progress */
  CONNECTING = 'connecting',
  
  /** Connected */
  CONNECTED = 'connected',
  
  /** Disconnection in progress */
  DISCONNECTING = 'disconnecting',
  
  /** Connection error */
  ERROR = 'error'
}

/**
 * Connection events for RabbitMQ
 */
export enum ConnectionEvent {
  /** Connected to RabbitMQ */
  CONNECTED = 'connected',
  
  /** Disconnected from RabbitMQ */
  DISCONNECTED = 'disconnected',
  
  /** Connection error */
  ERROR = 'error',
  
  /** Connection blocked by broker */
  BLOCKED = 'blocked',
  
  /** Connection unblocked by broker */
  UNBLOCKED = 'unblocked'
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
  
  /** Factor by which to increase delay on each retry */
  backoffFactor: number;
  
  /** Whether to add jitter to retry delays */
  jitter: boolean;
}

/**
 * Default MCA document exchange configuration
 * This matches the specification in section 0.1.3
 */
export const DEFAULT_MCA_EXCHANGE: IExchangeConfig = {
  name: 'mca.documents',
  type: 'fanout',
  durable: true,
  autoDelete: false
};

/**
 * Default publish options for document messages
 */
export const DEFAULT_PUBLISH_OPTIONS: IPublishOptions = {
  deliveryMode: 2, // Persistent
  contentType: 'application/json',
  contentEncoding: 'utf-8'
};