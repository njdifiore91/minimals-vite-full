/**
 * RabbitMQ Configuration
 * 
 * This module defines the RabbitMQ connection configuration for the Email Service.
 * It includes connection parameters, TLS settings, exchange configuration,
 * message publishing options, and retry strategies.
 * 
 * The configuration supports different environments (development, staging, production)
 * with appropriate settings for each environment.
 */

import path from 'path';
import fs from 'fs';

import {
  DEFAULT_MCA_EXCHANGE,
  DEFAULT_PUBLISH_OPTIONS,
  IExchangeConfig,
  IPublishOptions,
  IRabbitMQConfig,
  IRetryConfig
} from '../types/message-queue';

/**
 * Environment-specific RabbitMQ configurations
 */
const environmentConfigs: Record<string, Partial<IRabbitMQConfig>> = {
  development: {
    host: process.env.RABBITMQ_HOST || 'localhost',
    port: parseInt(process.env.RABBITMQ_PORT || '5672', 10),
    username: process.env.RABBITMQ_USERNAME || 'guest',
    password: process.env.RABBITMQ_PASSWORD || 'guest',
    vhost: process.env.RABBITMQ_VHOST || '/',
    useTls: process.env.RABBITMQ_USE_TLS === 'true',
    connectionTimeout: 30000, // 30 seconds
    heartbeat: 60, // 60 seconds
  },
  staging: {
    host: process.env.RABBITMQ_HOST || 'rabbitmq-staging',
    port: parseInt(process.env.RABBITMQ_PORT || '5671', 10), // TLS port
    username: process.env.RABBITMQ_USERNAME || 'mca-email-service',
    password: process.env.RABBITMQ_PASSWORD || '',
    vhost: process.env.RABBITMQ_VHOST || 'mca',
    useTls: true,
    connectionTimeout: 30000, // 30 seconds
    heartbeat: 60, // 60 seconds
  },
  production: {
    host: process.env.RABBITMQ_HOST || 'rabbitmq-production',
    port: parseInt(process.env.RABBITMQ_PORT || '5671', 10), // TLS port
    username: process.env.RABBITMQ_USERNAME || 'mca-email-service',
    password: process.env.RABBITMQ_PASSWORD || '',
    vhost: process.env.RABBITMQ_VHOST || 'mca',
    useTls: true,
    connectionTimeout: 30000, // 30 seconds
    heartbeat: 60, // 60 seconds
  },
};

/**
 * Get TLS configuration based on environment
 * 
 * In production and staging, we use client certificate authentication
 * with CA certificate verification.
 */
const getTlsOptions = (env: string): IRabbitMQConfig['tlsOptions'] => {
  if (env === 'development' && !process.env.RABBITMQ_USE_TLS) {
    return undefined;
  }

  // Base directory for certificates
  const certsDir = process.env.CERTS_DIR || '/app/certs';
  
  // Default paths for certificates
  const caPath = process.env.RABBITMQ_CA_PATH || path.join(certsDir, 'ca.pem');
  const certPath = process.env.RABBITMQ_CERT_PATH || path.join(certsDir, 'client-cert.pem');
  const keyPath = process.env.RABBITMQ_KEY_PATH || path.join(certsDir, 'client-key.pem');
  
  // Read certificates if they exist
  const ca = fs.existsSync(caPath) ? [fs.readFileSync(caPath, 'utf8')] : undefined;
  const cert = fs.existsSync(certPath) ? fs.readFileSync(certPath, 'utf8') : undefined;
  const key = fs.existsSync(keyPath) ? fs.readFileSync(keyPath, 'utf8') : undefined;
  
  return {
    ca,
    cert,
    key,
    rejectUnauthorized: env !== 'development', // Always verify certificates in non-dev environments
  };
};

/**
 * Get the current environment
 */
const getEnvironment = (): string => {
  return process.env.NODE_ENV || 'development';
};

/**
 * Build the complete RabbitMQ configuration
 */
const buildRabbitMQConfig = (): IRabbitMQConfig => {
  const env = getEnvironment();
  const envConfig = environmentConfigs[env] || environmentConfigs.development;
  const tlsOptions = getTlsOptions(env);
  
  return {
    host: envConfig.host!,
    port: envConfig.port!,
    username: envConfig.username!,
    password: envConfig.password!,
    vhost: envConfig.vhost!,
    useTls: envConfig.useTls!,
    tlsOptions,
    connectionTimeout: envConfig.connectionTimeout!,
    heartbeat: envConfig.heartbeat!,
  };
};

/**
 * Retry configuration for RabbitMQ operations
 */
export const retryConfig: IRetryConfig = {
  maxRetries: parseInt(process.env.RABBITMQ_MAX_RETRIES || '5', 10),
  initialDelay: parseInt(process.env.RABBITMQ_INITIAL_RETRY_DELAY || '100', 10),
  maxDelay: parseInt(process.env.RABBITMQ_MAX_RETRY_DELAY || '30000', 10),
  backoffFactor: parseFloat(process.env.RABBITMQ_BACKOFF_FACTOR || '2'),
  jitter: process.env.RABBITMQ_RETRY_JITTER !== 'false',
};

/**
 * MCA documents exchange configuration
 * This is the exchange where the Email Service publishes document messages
 */
export const mcaDocumentsExchange: IExchangeConfig = {
  ...DEFAULT_MCA_EXCHANGE,
  // Allow override from environment variables
  name: process.env.MCA_DOCUMENTS_EXCHANGE || DEFAULT_MCA_EXCHANGE.name,
  durable: process.env.MCA_DOCUMENTS_EXCHANGE_DURABLE !== 'false',
};

/**
 * Default publish options for document messages
 */
export const publishOptions: IPublishOptions = {
  ...DEFAULT_PUBLISH_OPTIONS,
  // Allow override from environment variables
  deliveryMode: parseInt(process.env.RABBITMQ_DELIVERY_MODE || '2', 10) as 1 | 2,
  contentType: process.env.RABBITMQ_CONTENT_TYPE || 'application/json',
  contentEncoding: process.env.RABBITMQ_CONTENT_ENCODING || 'utf-8',
  // Add application ID
  appId: 'mca-email-service',
};

/**
 * RabbitMQ configuration
 */
export const rabbitMQConfig: IRabbitMQConfig = buildRabbitMQConfig();

/**
 * Export default configuration
 */
export default rabbitMQConfig;