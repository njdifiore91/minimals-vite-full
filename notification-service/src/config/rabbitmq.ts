/**
 * RabbitMQ Configuration for Notification Service
 *
 * This file configures the RabbitMQ connection and messaging settings for the Notification Service.
 * It defines connection parameters, exchange and queue configurations, message consumption options,
 * and security settings with TLS and client certificate authentication.
 */

import fs from 'fs';
import path from 'path';
import { RabbitMQExchangeType } from '../types/rabbitmq';
import { IRabbitMQConfig } from '../types/config';

/**
 * Load TLS certificates if TLS is enabled
 * @param certPath Path to the certificate file
 * @returns Certificate content or undefined if TLS is disabled
 */
const loadCertificate = (certPath: string | undefined): string | undefined => {
  if (!certPath) return undefined;
  
  try {
    return fs.readFileSync(path.resolve(certPath), 'utf8');
  } catch (error) {
    console.error(`Error loading certificate from ${certPath}:`, error);
    throw new Error(`Failed to load certificate from ${certPath}`);
  }
};

/**
 * RabbitMQ configuration object
 * Configures the connection to RabbitMQ for the Notification Service
 */
export const rabbitMQConfig: IRabbitMQConfig = {
  // Connection URI (constructed from individual components)
  uri: `${process.env.RABBITMQ_TLS_ENABLED === 'true' ? 'amqps' : 'amqp'}://${process.env.RABBITMQ_USERNAME || 'guest'}:${process.env.RABBITMQ_PASSWORD || 'guest'}@${process.env.RABBITMQ_HOST || 'localhost'}:${process.env.RABBITMQ_PORT || '5672'}${process.env.RABBITMQ_VHOST && process.env.RABBITMQ_VHOST !== '/' ? `/${process.env.RABBITMQ_VHOST}` : ''}`,
  
  // Connection settings
  host: process.env.RABBITMQ_HOST || 'localhost',
  port: parseInt(process.env.RABBITMQ_PORT || '5672', 10),
  vhost: process.env.RABBITMQ_VHOST || '/',
  username: process.env.RABBITMQ_USERNAME || 'guest',
  password: process.env.RABBITMQ_PASSWORD || 'guest',
  
  // TLS configuration
  tls: process.env.RABBITMQ_TLS_ENABLED === 'true',
  tlsCA: process.env.RABBITMQ_TLS_CA,
  tlsCert: process.env.RABBITMQ_TLS_CERT,
  tlsKey: process.env.RABBITMQ_TLS_KEY,
  
  // Connection management
  connectTimeout: parseInt(process.env.RABBITMQ_CONNECT_TIMEOUT || '30000', 10),
  heartbeat: parseInt(process.env.RABBITMQ_HEARTBEAT || '60', 10),
  autoReconnect: process.env.RABBITMQ_AUTO_RECONNECT !== 'false',
  maxReconnectAttempts: parseInt(process.env.RABBITMQ_MAX_RECONNECT_ATTEMPTS || '10', 10),
  reconnectInterval: parseInt(process.env.RABBITMQ_RECONNECT_INTERVAL || '5000', 10),
  
  // Exchange settings
  exchange: process.env.RABBITMQ_EXCHANGE || 'mca.documents',
  exchangeType: process.env.RABBITMQ_EXCHANGE_TYPE || RabbitMQExchangeType.FANOUT,
  exchangeDurable: process.env.RABBITMQ_EXCHANGE_DURABLE !== 'false',
  
  // Queue settings
  queue: process.env.RABBITMQ_NOTIFICATION_QUEUE || 'notification',
  queueDurable: process.env.RABBITMQ_QUEUE_DURABLE !== 'false',
  routingKey: process.env.RABBITMQ_ROUTING_KEY || '',
  
  // Consumer settings
  ackMode: (process.env.RABBITMQ_ACK_MODE || 'manual') as 'auto' | 'manual',
  prefetchCount: parseInt(process.env.RABBITMQ_PREFETCH_COUNT || '10', 10),
  
  // Dead letter configuration
  deadLetterExchange: process.env.RABBITMQ_DEAD_LETTER_EXCHANGE || 'mca.deadletter',
  deadLetterRoutingKey: process.env.RABBITMQ_DEAD_LETTER_QUEUE || 'notification.deadletter',
  messageTTL: parseInt(process.env.RABBITMQ_MESSAGE_TTL || '604800000', 10), // 7 days in milliseconds
  
  // Message settings
  persistentMessages: process.env.RABBITMQ_PERSISTENT_MESSAGES !== 'false'
};

/**
 * Helper function to create a masked connection URL from config
 * Used for logging and connection string generation
 * Masks password for security
 */
export const getConnectionUrl = (config: IRabbitMQConfig): string => {
  const { host, port, username, vhost } = config;
  const protocol = config.tls ? 'amqps' : 'amqp';
  return `${protocol}://${username}:***@${host}:${port}${vhost !== '/' ? `/${vhost}` : ''}`;
};

/**
 * Helper function to validate RabbitMQ configuration
 * Throws error if required configuration is missing
 */
export const validateRabbitMQConfig = (config: IRabbitMQConfig): void => {
  const requiredFields = ['host', 'port', 'username', 'password', 'queue', 'exchange'];
  
  for (const field of requiredFields) {
    if (!config[field as keyof IRabbitMQConfig]) {
      throw new Error(`Missing required RabbitMQ configuration: ${field}`);
    }
  }
  
  // Validate TLS configuration if enabled
  if (config.tls) {
    // Client certificate authentication requires both cert and key
    if ((config.tlsCert && !config.tlsKey) || (!config.tlsCert && config.tlsKey)) {
      throw new Error('Both certificate and key must be provided for client certificate authentication');
    }
  }
  
  // Validate exchange type
  const validExchangeTypes = Object.values(RabbitMQExchangeType);
  if (!validExchangeTypes.includes(config.exchangeType as RabbitMQExchangeType)) {
    throw new Error(`Invalid exchange type: ${config.exchangeType}. Must be one of: ${validExchangeTypes.join(', ')}`);
  }
};

// Validate configuration on module load
validateRabbitMQConfig(rabbitMQConfig);

/**
 * Load TLS certificates for RabbitMQ connection
 * @returns Object containing loaded certificates
 */
export const loadTlsCertificates = () => {
  if (!rabbitMQConfig.tls) {
    return undefined;
  }
  
  return {
    ca: rabbitMQConfig.tlsCA ? loadCertificate(rabbitMQConfig.tlsCA) : undefined,
    cert: rabbitMQConfig.tlsCert ? loadCertificate(rabbitMQConfig.tlsCert) : undefined,
    key: rabbitMQConfig.tlsKey ? loadCertificate(rabbitMQConfig.tlsKey) : undefined,
    rejectUnauthorized: true
  };
};

/**
 * Get RabbitMQ connection options with loaded certificates
 * @returns Connection options for amqplib
 */
export const getRabbitMQConnectionOptions = () => {
  const { host, port, username, password, vhost, heartbeat, connectTimeout } = rabbitMQConfig;
  
  return {
    protocol: rabbitMQConfig.tls ? 'amqps' : 'amqp',
    hostname: host,
    port,
    username,
    password,
    vhost,
    frameMax: 0, // No limit
    heartbeat,
    connectionTimeout: connectTimeout,
    tls: rabbitMQConfig.tls ? loadTlsCertificates() : undefined
  };
};

/**
 * Get queue assertion options for RabbitMQ
 * @returns Queue options for assertQueue
 */
export const getQueueOptions = () => {
  return {
    durable: rabbitMQConfig.queueDurable,
    arguments: {
      'x-dead-letter-exchange': rabbitMQConfig.deadLetterExchange,
      'x-dead-letter-routing-key': rabbitMQConfig.deadLetterRoutingKey,
      'x-message-ttl': rabbitMQConfig.messageTTL
    }
  };
};

/**
 * Get consumer options for RabbitMQ
 * @returns Consumer options for consume
 */
export const getConsumerOptions = () => {
  return {
    noAck: rabbitMQConfig.ackMode === 'auto',
    exclusive: false,
    arguments: {}
  };
};

/**
 * Get publish options for RabbitMQ
 * @returns Publish options for publish
 */
export const getPublishOptions = () => {
  return {
    persistent: rabbitMQConfig.persistentMessages,
    contentType: 'application/json',
    contentEncoding: 'utf-8'
  };
};

export default rabbitMQConfig;