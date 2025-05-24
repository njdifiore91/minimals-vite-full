/**
 * RabbitMQ Type Definitions
 * 
 * This file defines TypeScript interfaces and types for RabbitMQ messaging used by the Notification Service.
 * It provides type definitions for messages, exchanges, queues, connections, and consumer/publisher options.
 * 
 * The Notification Service consumes messages from RabbitMQ for status updates, errors, and completions.
 * All RabbitMQ connections require TLS with client certificate authentication as specified in section 3.2.3.
 * Message serialization between services uses standardized JSON schemas as specified in section 3.2.3.
 */

/**
 * Enum representing the different types of RabbitMQ exchanges
 */
export enum RabbitMQExchangeType {
  DIRECT = 'direct',
  FANOUT = 'fanout',
  TOPIC = 'topic',
  HEADERS = 'headers'
}

/**
 * Interface for RabbitMQ message structure
 */
export interface IRabbitMQMessage {
  /** Message content as a JSON object */
  content: Record<string, any>;
  /** Message headers for metadata */
  headers?: Record<string, any>;
  /** Correlation ID for distributed tracing */
  correlationId?: string;
  /** Message timestamp */
  timestamp?: number;
  /** Content type (default: application/json) */
  contentType?: string;
  /** Content encoding */
  contentEncoding?: string;
  /** Message expiration in milliseconds */
  expiration?: string;
  /** Message ID */
  messageId?: string;
  /** Message type identifier */
  type?: string;
  /** User ID who sent the message */
  userId?: string;
  /** Application ID that sent the message */
  appId?: string;
}

/**
 * Interface for RabbitMQ exchange configuration
 */
export interface IRabbitMQExchange {
  /** Exchange name */
  name: string;
  /** Exchange type (direct, fanout, topic, headers) */
  type: RabbitMQExchangeType;
  /** Whether the exchange should survive broker restarts */
  durable?: boolean;
  /** Whether the exchange should be deleted when last queue is unbound */
  autoDelete?: boolean;
  /** Exchange arguments */
  arguments?: Record<string, any>;
  /** Whether the exchange is internal (can't publish directly to it) */
  internal?: boolean;
}

/**
 * Interface for RabbitMQ queue binding configuration
 */
export interface IRabbitMQBinding {
  /** Exchange to bind to */
  exchange: string;
  /** Routing pattern for the binding */
  pattern: string;
  /** Binding arguments */
  arguments?: Record<string, any>;
}

/**
 * Interface for RabbitMQ queue configuration
 */
export interface IRabbitMQQueue {
  /** Queue name */
  name: string;
  /** Whether the queue should survive broker restarts */
  durable?: boolean;
  /** Whether the queue should be deleted when last consumer unsubscribes */
  autoDelete?: boolean;
  /** Whether the queue is exclusive to the connection */
  exclusive?: boolean;
  /** Queue arguments */
  arguments?: Record<string, any>;
  /** Queue bindings to exchanges */
  bindings?: IRabbitMQBinding[];
  /** Dead letter exchange for failed messages */
  deadLetterExchange?: string;
  /** Dead letter routing key */
  deadLetterRoutingKey?: string;
  /** Message time-to-live in milliseconds */
  messageTtl?: number;
  /** Maximum queue length */
  maxLength?: number;
  /** Maximum queue size in bytes */
  maxLengthBytes?: number;
  /** Queue overflow behavior */
  overflowBehavior?: 'drop-head' | 'reject-publish' | 'reject-publish-dlx';
}

/**
 * Interface for TLS configuration for RabbitMQ connections
 */
export interface IRabbitMQTlsOptions {
  /** Whether to enable TLS */
  enabled: boolean;
  /** Path to CA certificate file */
  ca?: string | Buffer;
  /** Path to client certificate file */
  cert?: string | Buffer;
  /** Path to client key file */
  key?: string | Buffer;
  /** Passphrase for client key */
  passphrase?: string;
  /** Whether to reject unauthorized connections */
  rejectUnauthorized?: boolean;
  /** Server name for SNI */
  servername?: string;
}

/**
 * Interface for RabbitMQ connection parameters
 */
export interface IRabbitMQConnection {
  /** Connection protocol (amqp or amqps) */
  protocol: 'amqp' | 'amqps';
  /** Hostname of the RabbitMQ server */
  hostname: string;
  /** Port of the RabbitMQ server */
  port: number;
  /** Virtual host */
  vhost?: string;
  /** Username for authentication */
  username: string;
  /** Password for authentication */
  password: string;
  /** TLS options for secure connections */
  tls: IRabbitMQTlsOptions;
  /** Connection timeout in milliseconds */
  timeout?: number;
  /** Heartbeat interval in seconds */
  heartbeat?: number;
  /** Connection name for identification */
  connectionName?: string;
  /** Maximum reconnection attempts */
  maxReconnectAttempts?: number;
  /** Reconnection interval in milliseconds */
  reconnectInterval?: number;
}

/**
 * Interface for RabbitMQ consumer options
 */
export interface IRabbitMQConsumerOptions {
  /** Consumer tag for identification */
  consumerTag?: string;
  /** Whether to automatically acknowledge messages */
  noAck?: boolean;
  /** Whether to get exclusive access to the queue */
  exclusive?: boolean;
  /** Priority for the consumer */
  priority?: number;
  /** Consumer arguments */
  arguments?: Record<string, any>;
  /** Prefetch count (max unacknowledged messages) */
  prefetchCount?: number;
  /** Whether prefetch applies to the channel or consumer */
  prefetchGlobal?: boolean;
}

/**
 * Interface for RabbitMQ publish options
 */
export interface IRabbitMQPublishOptions {
  /** Whether message should be persistent */
  persistent?: boolean;
  /** Message expiration in milliseconds */
  expiration?: string;
  /** Content type (default: application/json) */
  contentType?: string;
  /** Content encoding */
  contentEncoding?: string;
  /** Message headers */
  headers?: Record<string, any>;
  /** Message priority (0-9) */
  priority?: number;
  /** Correlation ID for request-reply pattern */
  correlationId?: string;
  /** Reply-to queue for request-reply pattern */
  replyTo?: string;
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
}

/**
 * Interface for RabbitMQ message handler function
 */
export type RabbitMQMessageHandler = (
  message: IRabbitMQMessage,
  ack: () => void,
  nack: (requeue?: boolean) => void,
  reject: (requeue?: boolean) => void
) => Promise<void> | void;

/**
 * Interface for RabbitMQ connection error handler function
 */
export type RabbitMQErrorHandler = (error: Error) => void;

/**
 * Interface for RabbitMQ retry policy
 */
export interface IRabbitMQRetryPolicy {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial retry delay in milliseconds */
  initialDelay: number;
  /** Maximum retry delay in milliseconds */
  maxDelay: number;
  /** Backoff factor for exponential backoff */
  backoffFactor: number;
  /** Whether to use jitter to randomize delay */
  useJitter?: boolean;
}