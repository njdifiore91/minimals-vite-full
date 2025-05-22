/**
 * RabbitMQ TypeScript definitions for the Notification Service
 * 
 * This file defines the interfaces and types for RabbitMQ messaging used by the Notification Service.
 * It provides type definitions for messages, exchanges, queues, connections, and consumer/publisher options.
 * These types ensure type safety for all RabbitMQ operations and enable consistent message handling.
 */

import type { IDateValue } from './common';

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
 * Interface for RabbitMQ message headers
 */
export interface IRabbitMQMessageHeaders {
  [key: string]: string | number | boolean | null;
  contentType?: string;
  contentEncoding?: string;
  messageId?: string;
  correlationId?: string;
  timestamp?: number;
  appId?: string;
  userId?: string;
  clusterId?: string;
  type?: string;
  expiration?: string;
  priority?: number;
}

/**
 * Interface for RabbitMQ message structure
 */
export interface IRabbitMQMessage<T = unknown> {
  content: T;
  headers: IRabbitMQMessageHeaders;
  properties?: {
    persistent?: boolean;
    mandatory?: boolean;
    expiration?: string;
    userId?: string;
    CC?: string | string[];
    BCC?: string | string[];
  };
  createdAt?: IDateValue;
}

/**
 * Interface for RabbitMQ exchange configuration
 */
export interface IRabbitMQExchange {
  name: string;
  type: RabbitMQExchangeType;
  options?: {
    durable?: boolean;
    internal?: boolean;
    autoDelete?: boolean;
    alternateExchange?: string;
    arguments?: Record<string, any>;
  };
}

/**
 * Interface for RabbitMQ queue binding configuration
 */
export interface IRabbitMQBinding {
  exchange: string;
  routingKey: string;
  arguments?: Record<string, any>;
}

/**
 * Interface for RabbitMQ queue configuration
 */
export interface IRabbitMQQueue {
  name: string;
  options?: {
    exclusive?: boolean;
    durable?: boolean;
    autoDelete?: boolean;
    messageTtl?: number;
    expires?: number;
    deadLetterExchange?: string;
    deadLetterRoutingKey?: string;
    maxLength?: number;
    maxPriority?: number;
    arguments?: Record<string, any>;
  };
  bindings?: IRabbitMQBinding[];
}

/**
 * Interface for RabbitMQ TLS configuration
 */
export interface IRabbitMQTlsOptions {
  enabled: boolean;
  ca?: string | Buffer | Array<string | Buffer>;
  cert?: string | Buffer;
  key?: string | Buffer;
  passphrase?: string;
  rejectUnauthorized?: boolean;
  serverName?: string;
}

/**
 * Interface for RabbitMQ connection parameters
 */
export interface IRabbitMQConnection {
  protocol: 'amqp' | 'amqps';
  hostname: string;
  port: number;
  username: string;
  password: string;
  vhost?: string;
  frameMax?: number;
  heartbeat?: number;
  connectionTimeout?: number;
  tls?: IRabbitMQTlsOptions;
  retry?: {
    enabled: boolean;
    initialDelay?: number;
    maxDelay?: number;
    maxAttempts?: number;
    factor?: number;
  };
}

/**
 * Interface for RabbitMQ consumer options
 */
export interface IRabbitMQConsumerOptions {
  queue: string;
  consumerTag?: string;
  noLocal?: boolean;
  noAck?: boolean;
  exclusive?: boolean;
  priority?: number;
  arguments?: Record<string, any>;
  prefetch?: number;
  defaultEncoding?: BufferEncoding;
  manualAck?: boolean;
  manualNack?: boolean;
  manualRequeue?: boolean;
}

/**
 * Interface for RabbitMQ publish options
 */
export interface IRabbitMQPublishOptions {
  exchange: string;
  routingKey: string;
  mandatory?: boolean;
  persistent?: boolean;
  contentType?: string;
  contentEncoding?: string;
  expiration?: string | number;
  messageId?: string;
  correlationId?: string;
  timestamp?: number;
  type?: string;
  appId?: string;
  userId?: string;
  CC?: string | string[];
  BCC?: string | string[];
  priority?: number;
  headers?: Record<string, any>;
  deliveryMode?: 1 | 2; // 1 = Non-persistent, 2 = Persistent
}

/**
 * Interface for RabbitMQ connection status
 */
export interface IRabbitMQConnectionStatus {
  connected: boolean;
  connectionAttempts: number;
  lastError?: Error;
  lastConnectedAt?: IDateValue;
  lastDisconnectedAt?: IDateValue;
}

/**
 * Interface for RabbitMQ message processing result
 */
export interface IRabbitMQProcessResult {
  success: boolean;
  error?: Error;
  retryable?: boolean;
  retryAfter?: number;
}

/**
 * Type for RabbitMQ message handler function
 */
export type RabbitMQMessageHandler<T = unknown> = (
  message: IRabbitMQMessage<T>,
  channel: any, // amqplib Channel type
  originalMessage: any // amqplib original message
) => Promise<IRabbitMQProcessResult>;