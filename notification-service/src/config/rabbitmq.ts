/**
 * RabbitMQ Configuration
 * 
 * This file configures the RabbitMQ connection and messaging settings for the Notification Service.
 * It defines connection parameters, exchange and queue configurations, message consumption options,
 * and security settings. It enables the service to consume messages from the Data Service and
 * process them for webhook delivery.
 * 
 * Key features:
 * - TLS with client certificate authentication for secure connections
 * - Connection to the 'notification' queue for consuming messages
 * - Connection error handling and recovery strategies
 * - Message serialization for consistent JSON format
 * - Message acknowledgment settings for reliable delivery
 */

import path from 'path';
import fs from 'fs';
import { 
  IRabbitMQConnection, 
  IRabbitMQQueue, 
  IRabbitMQExchange, 
  IRabbitMQConsumerOptions,
  IRabbitMQTlsOptions,
  IRabbitMQRetryPolicy,
  RabbitMQExchangeType
} from '../types/rabbitmq';

/**
 * Load environment variables with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value
 * @param required Whether the variable is required
 * @returns The environment variable value or default
 */
const getEnvVar = (key: string, defaultValue?: string, required = false): string => {
  const value = process.env[key] || defaultValue;
  if (required && !value) {
    throw new Error(`Required environment variable ${key} is not set`);
  }
  return value || '';
};

/**
 * Load file content for certificates
 * @param filePath Path to the file
 * @returns File content as Buffer or undefined if file doesn't exist
 */
const loadCertFile = (filePath: string): Buffer | undefined => {
  try {
    return fs.readFileSync(filePath);
  } catch (error) {
    console.warn(`Warning: Could not load certificate file at ${filePath}`);
    return undefined;
  }
};

// Environment-specific settings
const NODE_ENV = getEnvVar('NODE_ENV', 'development');
const isProd = NODE_ENV === 'production';
const isStaging = NODE_ENV === 'staging';

// Base paths for certificates
const CERT_BASE_PATH = getEnvVar('CERT_BASE_PATH', '/app/certs');

// TLS configuration
const tlsOptions: IRabbitMQTlsOptions = {
  enabled: isProd || isStaging || getEnvVar('RABBITMQ_TLS_ENABLED', 'false') === 'true',
  ca: loadCertFile(path.join(CERT_BASE_PATH, getEnvVar('RABBITMQ_CA_CERT', 'ca.pem'))),
  cert: loadCertFile(path.join(CERT_BASE_PATH, getEnvVar('RABBITMQ_CLIENT_CERT', 'client.pem'))),
  key: loadCertFile(path.join(CERT_BASE_PATH, getEnvVar('RABBITMQ_CLIENT_KEY', 'client.key'))),
  passphrase: getEnvVar('RABBITMQ_KEY_PASSPHRASE'),
  rejectUnauthorized: isProd || isStaging || getEnvVar('RABBITMQ_REJECT_UNAUTHORIZED', 'true') === 'true',
};

// Connection retry policy
const connectionRetryPolicy: IRabbitMQRetryPolicy = {
  maxRetries: parseInt(getEnvVar('RABBITMQ_MAX_RETRIES', '10'), 10),
  initialDelay: parseInt(getEnvVar('RABBITMQ_INITIAL_DELAY', '1000'), 10), // 1 second
  maxDelay: parseInt(getEnvVar('RABBITMQ_MAX_DELAY', '30000'), 10), // 30 seconds
  backoffFactor: parseFloat(getEnvVar('RABBITMQ_BACKOFF_FACTOR', '2.0')),
  useJitter: getEnvVar('RABBITMQ_USE_JITTER', 'true') === 'true',
};

// RabbitMQ connection configuration
const rabbitMQConnection: IRabbitMQConnection = {
  protocol: tlsOptions.enabled ? 'amqps' : 'amqp',
  hostname: getEnvVar('RABBITMQ_HOST', 'localhost', isProd),
  port: parseInt(getEnvVar('RABBITMQ_PORT', tlsOptions.enabled ? '5671' : '5672'), 10),
  vhost: getEnvVar('RABBITMQ_VHOST', '/'),
  username: getEnvVar('RABBITMQ_USERNAME', 'guest', isProd),
  password: getEnvVar('RABBITMQ_PASSWORD', 'guest', isProd),
  tls: tlsOptions,
  timeout: parseInt(getEnvVar('RABBITMQ_CONNECTION_TIMEOUT', '30000'), 10), // 30 seconds
  heartbeat: parseInt(getEnvVar('RABBITMQ_HEARTBEAT', '60'), 10), // 60 seconds
  connectionName: `notification-service-${NODE_ENV}`,
  maxReconnectAttempts: connectionRetryPolicy.maxRetries,
  reconnectInterval: connectionRetryPolicy.initialDelay,
};

// Exchange configuration
const exchange: IRabbitMQExchange = {
  name: getEnvVar('RABBITMQ_EXCHANGE', 'mca.documents'),
  type: RabbitMQExchangeType.FANOUT,
  durable: true,
  autoDelete: false,
};

// Queue configuration
const queue: IRabbitMQQueue = {
  name: getEnvVar('RABBITMQ_QUEUE', 'notification'),
  durable: true,
  autoDelete: false,
  exclusive: false,
  arguments: {
    'x-queue-mode': 'lazy', // Optimize for throughput over latency
    'x-message-ttl': 604800000, // 7 days in milliseconds
  },
  bindings: [
    {
      exchange: exchange.name,
      pattern: '#', // Bind to all messages in the exchange
    },
  ],
  deadLetterExchange: getEnvVar('RABBITMQ_DLX', 'mca.documents.dlx'),
  deadLetterRoutingKey: getEnvVar('RABBITMQ_DLX_ROUTING_KEY', 'notification.failed'),
};

// Consumer options
const consumerOptions: IRabbitMQConsumerOptions = {
  consumerTag: `notification-consumer-${process.pid}`,
  noAck: false, // Require explicit acknowledgment
  exclusive: false,
  prefetchCount: parseInt(getEnvVar('RABBITMQ_PREFETCH_COUNT', '10'), 10),
  prefetchGlobal: false,
};

// Dead letter exchange configuration for failed messages
const deadLetterExchange: IRabbitMQExchange = {
  name: queue.deadLetterExchange || 'mca.documents.dlx',
  type: RabbitMQExchangeType.DIRECT,
  durable: true,
  autoDelete: false,
};

// Dead letter queue configuration
const deadLetterQueue: IRabbitMQQueue = {
  name: `${queue.name}.failed`,
  durable: true,
  autoDelete: false,
  exclusive: false,
  arguments: {
    'x-queue-mode': 'lazy',
    'x-message-ttl': 2592000000, // 30 days in milliseconds
  },
  bindings: [
    {
      exchange: deadLetterExchange.name,
      pattern: queue.deadLetterRoutingKey || 'notification.failed',
    },
  ],
};

/**
 * RabbitMQ configuration object
 */
export const rabbitmqConfig = {
  connection: rabbitMQConnection,
  exchange,
  queue,
  consumerOptions,
  deadLetterExchange,
  deadLetterQueue,
  retryPolicy: connectionRetryPolicy,
  
  // Message serialization options
  serialization: {
    contentType: 'application/json',
    contentEncoding: 'utf-8',
  },
  
  // Health check configuration
  healthCheck: {
    enabled: true,
    interval: parseInt(getEnvVar('RABBITMQ_HEALTH_CHECK_INTERVAL', '30000'), 10), // 30 seconds
    timeout: parseInt(getEnvVar('RABBITMQ_HEALTH_CHECK_TIMEOUT', '5000'), 10), // 5 seconds
  },
};

export default rabbitmqConfig;