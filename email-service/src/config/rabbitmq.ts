/**
 * RabbitMQ Configuration
 * 
 * Configures the RabbitMQ connection and messaging settings for the Email Service.
 * This file defines connection parameters, exchange and queue configurations,
 * message publishing options, and security settings.
 * 
 * Features:
 * - TLS with client certificate authentication
 * - Fanout exchange configuration for document processing
 * - Persistent message delivery with appropriate headers
 * - Retry configuration with exponential backoff
 * - Connection error handling and recovery strategies
 */

import fs from 'fs';
import path from 'path';
import { Options } from 'amqplib';
import { 
  IRabbitMQConfig, 
  IExchangeConfig, 
  IPublishOptions, 
  IRetryConfig,
  DEFAULT_MCA_EXCHANGE,
  DEFAULT_PUBLISH_OPTIONS,
  DEFAULT_RETRY_CONFIG
} from '../types/message-queue';
import { RetryOptions } from '../utils/retry';
import { createComponentLogger } from './logger';

const logger = createComponentLogger('RabbitMQConfig');

/**
 * Load TLS certificates and keys if TLS is enabled
 * 
 * @param certPath - Path to client certificate
 * @param keyPath - Path to client key
 * @param caPath - Path to CA certificate
 * @returns TLS options object or undefined if TLS is disabled
 */
const loadTlsOptions = (certPath?: string, keyPath?: string, caPath?: string): Options.Socket | undefined => {
  if (!certPath || !keyPath) {
    return undefined;
  }

  try {
    const options: Options.Socket = {};
    
    // Load client certificate and key if provided
    if (certPath && keyPath) {
      options.cert = fs.readFileSync(path.resolve(certPath));
      options.key = fs.readFileSync(path.resolve(keyPath));
    }
    
    // Load CA certificate if provided
    if (caPath) {
      options.ca = [fs.readFileSync(path.resolve(caPath))];
    }
    
    // Set TLS options
    options.rejectUnauthorized = true; // Always validate server certificate
    
    return options;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    logger.error('Failed to load TLS certificates', { error: err.message });
    throw err;
  }
};

/**
 * RabbitMQ connection configuration
 * 
 * Loads connection parameters from environment variables with sensible defaults
 */
export const rabbitMQConfig: IRabbitMQConfig = {
  host: process.env.RABBITMQ_HOST || 'localhost',
  port: parseInt(process.env.RABBITMQ_PORT || '5671', 10),
  username: process.env.RABBITMQ_USER || 'guest',
  password: process.env.RABBITMQ_PASSWORD || 'guest',
  vhost: process.env.RABBITMQ_VHOST || '/',
  useTls: process.env.RABBITMQ_TLS_ENABLED === 'true',
  certPath: process.env.RABBITMQ_CERT_PATH,
  keyPath: process.env.RABBITMQ_KEY_PATH,
  caPath: process.env.RABBITMQ_CA_PATH,
  connectionTimeout: 30000, // 30 seconds
  heartbeat: 60, // 60 seconds
};

/**
 * TLS options for RabbitMQ connection
 * 
 * Loaded from certificate files specified in environment variables
 */
export const tlsOptions = rabbitMQConfig.useTls
  ? loadTlsOptions(
      rabbitMQConfig.certPath,
      rabbitMQConfig.keyPath,
      rabbitMQConfig.caPath
    )
  : undefined;

// Add TLS options to RabbitMQ config
rabbitMQConfig.tlsOptions = tlsOptions;

/**
 * MCA Documents Exchange Configuration
 * 
 * Configures the fanout exchange for document processing
 */
export const mcaDocumentsExchange: IExchangeConfig = {
  name: process.env.RABBITMQ_EXCHANGE || DEFAULT_MCA_EXCHANGE.name,
  type: 'fanout',
  durable: true,
  autoDelete: false,
  arguments: {
    'x-message-ttl': 86400000, // 24 hours in milliseconds
    'x-queue-mode': 'lazy', // Optimize for throughput over latency
  },
};

/**
 * Message publishing options
 * 
 * Configures how messages are published to RabbitMQ
 */
export const publishOptions: IPublishOptions = {
  contentType: 'application/json',
  contentEncoding: 'utf-8',
  deliveryMode: 2, // persistent
  headers: {
    'x-source': 'email-service',
    'x-version': process.env.APP_VERSION || '1.0.0',
    'x-environment': process.env.NODE_ENV || 'development',
  },
  appId: 'email-service',
};

/**
 * Retry configuration for RabbitMQ operations
 * 
 * Configures retry attempts, delays, and backoff strategy
 */
export const retryConfig: IRetryConfig = {
  maxRetries: parseInt(process.env.MAX_RETRY_ATTEMPTS || '5', 10),
  initialDelay: parseInt(process.env.RETRY_DELAY_MS || '1000', 10),
  maxDelay: 60000, // 1 minute
  backoffFactor: 2, // Exponential backoff
  jitter: true, // Add randomness to prevent thundering herd
};

/**
 * RabbitMQ retry options for use with the retry utility
 */
export const RABBITMQ_RETRY_OPTIONS: RetryOptions = {
  maxRetries: retryConfig.maxRetries,
  initialDelayMs: retryConfig.initialDelay,
  maxDelayMs: retryConfig.maxDelay,
  backoffFactor: retryConfig.backoffFactor,
  jitter: retryConfig.jitter,
};

// Log configuration on startup
logger.info('RabbitMQ configuration loaded', {
  host: rabbitMQConfig.host,
  port: rabbitMQConfig.port,
  vhost: rabbitMQConfig.vhost,
  useTls: rabbitMQConfig.useTls,
  exchange: mcaDocumentsExchange.name,
  exchangeType: mcaDocumentsExchange.type,
});

// Export default objects for easy importing
export default {
  rabbitMQConfig,
  tlsOptions,
  mcaDocumentsExchange,
  publishOptions,
  retryConfig,
  RABBITMQ_RETRY_OPTIONS,
};