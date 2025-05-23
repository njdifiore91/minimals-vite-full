/**
 * @file webhook.ts
 * @description Configuration for webhook delivery settings in the Notification Service.
 * This file defines retry logic, timeout settings, signature generation, and payload formatting.
 * It enables the service to reliably deliver notifications to external systems with proper
 * authentication and error handling.
 */

import { createHmac, timingSafeEqual } from 'crypto';
import { config } from './app';
import {
  IWebhookPayload,
  IWebhookSignature,
  IWebhookRetryPolicy,
  IWebhookConfig,
} from '../types/webhook';
import logger from './logger';

/**
 * Configuration for webhook HTTP requests
 */
export const httpConfig = {
  /**
   * Default timeout for webhook requests in milliseconds
   * This is the maximum time to wait for a response from the webhook endpoint
   */
  timeoutMs: config.webhook.defaultTimeout,

  /**
   * Maximum number of redirects to follow
   * Set to 0 to disable following redirects
   */
  maxRedirects: 3,

  /**
   * Maximum payload size in bytes
   * Payloads larger than this will be rejected
   */
  maxPayloadSize: config.webhook.maxPayloadSize,

  /**
   * User agent string to use in webhook requests
   */
  userAgent: `DollarFunding-Webhook-Service/${process.env.npm_package_version || '1.0.0'}`,

  /**
   * Default content type for webhook payloads
   */
  contentType: 'application/json',

  /**
   * Whether to allow insecure SSL connections (not recommended for production)
   */
  allowInsecureSSL: process.env.NODE_ENV !== 'production',

  /**
   * Connection timeout in milliseconds (separate from request timeout)
   */
  connectionTimeoutMs: 5000,
};

/**
 * Configuration for webhook signature generation and verification
 */
export const signatureConfig = {
  /**
   * Whether to enable webhook signature generation and verification
   */
  enabled: config.webhook.enableSignature,

  /**
   * Algorithm to use for signature generation (always HMAC-SHA256)
   */
  algorithm: 'sha256',

  /**
   * Header name for the webhook signature
   */
  headerName: config.webhook.signatureHeader,

  /**
   * Header name for the webhook timestamp
   */
  timestampHeaderName: 'X-Webhook-Timestamp',

  /**
   * Whether to include the timestamp in the signature
   * When true, the signature is generated as HMAC(timestamp + '.' + payload)
   * When false, the signature is generated as HMAC(payload)
   */
  includeTimestamp: true,

  /**
   * Encoding format for the signature
   */
  encoding: 'hex' as const,

  /**
   * Maximum age of a webhook signature in milliseconds
   * Signatures older than this will be rejected
   * Default: 5 minutes (300000 ms)
   */
  maxSignatureAgeMs: 300000,

  /**
   * Whether to enforce signature verification for incoming webhooks
   */
  enforceVerification: true,
};

/**
 * Configuration for webhook acknowledgment and response handling
 */
export const acknowledgmentConfig = {
  /**
   * HTTP status codes that indicate successful webhook delivery
   */
  successCodes: [200, 201, 202, 204],

  /**
   * Whether to require an acknowledgment response from the webhook recipient
   */
  requireAcknowledgment: true,

  /**
   * Maximum time to wait for an acknowledgment response in milliseconds
   */
  acknowledgmentTimeoutMs: config.webhook.defaultTimeout,

  /**
   * Whether to treat a timeout as a delivery failure
   */
  timeoutIsFailure: true,
};

/**
 * Configuration for webhook payload schema validation
 */
export const schemaValidationConfig = {
  /**
   * Whether to enable schema validation for webhook payloads
   */
  enabled: config.webhook.validatePayload,

  /**
   * Whether to reject invalid payloads or just log a warning
   */
  rejectInvalid: true,

  /**
   * Directory containing JSON schema files for validation
   */
  schemaDir: './schemas',

  /**
   * Default schema version to use
   */
  defaultSchemaVersion: '1.0',

  /**
   * Whether to cache schemas in memory
   */
  cacheSchemas: true,
};

/**
 * Default retry policy for webhook deliveries
 */
export const defaultRetryPolicy: IWebhookRetryPolicy = {
  /**
   * Maximum number of retry attempts
   */
  maxRetries: config.retry.maxAttempts,

  /**
   * Initial retry delay in milliseconds
   */
  initialDelayMs: config.retry.initialDelay,

  /**
   * Backoff factor for exponential backoff
   * Each retry will wait backoffFactor times longer than the previous retry
   */
  backoffFactor: config.retry.backoffMultiplier,

  /**
   * Maximum delay between retries in milliseconds
   */
  maxDelayMs: config.retry.maxDelay,

  /**
   * Whether to add jitter to retry delays to prevent thundering herd problems
   */
  useJitter: config.retry.enableJitter,

  /**
   * HTTP status codes that should trigger a retry
   */
  retryableStatusCodes: config.retry.retryStatusCodes,

  /**
   * Whether to retry on network errors
   */
  retryOnNetworkError: true,
};

/**
 * Configuration for webhook batching
 */
export const batchingConfig = {
  /**
   * Whether to enable webhook batching
   */
  enabled: config.webhook.enableBatching,

  /**
   * Maximum number of webhooks to include in a batch
   */
  maxBatchSize: config.webhook.maxBatchSize,

  /**
   * Interval in milliseconds to wait before sending a batch
   */
  batchIntervalMs: config.webhook.batchInterval,

  /**
   * Whether to send partial batches if the batch interval expires
   */
  sendPartialBatches: true,
};

/**
 * Configuration for dead letter queue
 */
export const deadLetterConfig = {
  /**
   * Whether to enable the dead letter queue
   */
  enabled: true,

  /**
   * Exchange name for the dead letter queue
   */
  exchange: config.rabbitmq.deadLetterExchange,

  /**
   * Routing key for the dead letter queue
   */
  routingKey: config.rabbitmq.deadLetterRoutingKey,

  /**
   * Whether to include the full payload in the dead letter message
   */
  includePayload: true,

  /**
   * Whether to include the delivery result in the dead letter message
   */
  includeResult: true,

  /**
   * Time-to-live for messages in the dead letter queue in milliseconds
   * Default: 7 days
   */
  messageTTL: config.rabbitmq.messageTTL || 604800000,
};

/**
 * Configuration for webhook metrics
 */
export const metricsConfig = {
  /**
   * Whether to enable webhook metrics collection
   */
  enabled: config.webhook.enableMetrics,

  /**
   * Prefix for metric names
   */
  prefix: 'webhook_',

  /**
   * Tags to include with all metrics
   */
  defaultTags: {
    service: 'notification-service',
    version: process.env.npm_package_version || '1.0.0',
  },

  /**
   * Whether to track delivery times
   */
  trackDeliveryTime: true,

  /**
   * Whether to track success/failure rates
   */
  trackSuccessRate: true,

  /**
   * Whether to track retry attempts
   */
  trackRetryAttempts: true,
};

/**
 * Main webhook configuration object
 */
export const webhookConfig = {
  /**
   * HTTP configuration
   */
  http: httpConfig,

  /**
   * Signature configuration
   */
  signature: signatureConfig,

  /**
   * Acknowledgment configuration
   */
  acknowledgment: acknowledgmentConfig,

  /**
   * Schema validation configuration
   */
  schemaValidation: schemaValidationConfig,

  /**
   * Default retry policy
   */
  defaultRetryPolicy,

  /**
   * Batching configuration
   */
  batching: batchingConfig,

  /**
   * Dead letter configuration
   */
  deadLetter: deadLetterConfig,

  /**
   * Metrics configuration
   */
  metrics: metricsConfig,

  /**
   * Default headers to include in all webhook requests
   */
  defaultHeaders: config.webhook.defaultHeaders,
};

/**
 * Generates an HMAC-SHA256 signature for a webhook payload
 * @param payload The webhook payload to sign
 * @param secretKey The secret key to use for signing
 * @returns The signature object containing the signature and timestamp
 */
export const generateWebhookSignature = (
  payload: IWebhookPayload,
  secretKey: string
): IWebhookSignature => {
  const timestamp = Date.now().toString();
  const payloadString = JSON.stringify(payload);
  
  // Create HMAC using the secret key
  const hmac = createHmac(signatureConfig.algorithm, secretKey);
  
  // Update HMAC with timestamp and payload
  if (signatureConfig.includeTimestamp) {
    hmac.update(`${timestamp}.${payloadString}`);
  } else {
    hmac.update(payloadString);
  }
  
  // Generate the signature
  const signature = hmac.digest(signatureConfig.encoding);
  
  logger.debug('Generated webhook signature', { signature, timestamp });
  
  return {
    signature,
    timestamp,
    algorithm: 'HMAC-SHA256',
    encoding: signatureConfig.encoding,
  };
};

/**
 * Verifies an HMAC-SHA256 signature for a webhook payload
 * @param payload The webhook payload
 * @param signature The signature to verify
 * @param secretKey The secret key used for signing
 * @param timestamp The timestamp included in the signature
 * @returns Whether the signature is valid
 */
export const verifyWebhookSignature = (
  payload: IWebhookPayload,
  signature: string,
  secretKey: string,
  timestamp?: string
): boolean => {
  try {
    // Verify timestamp if provided and includeTimestamp is enabled
    if (timestamp && signatureConfig.includeTimestamp) {
      const timestampAge = Date.now() - parseInt(timestamp, 10);
      
      // Reject if timestamp is too old
      if (timestampAge > signatureConfig.maxSignatureAgeMs) {
        logger.warn('Webhook signature timestamp too old', { timestamp, age: timestampAge });
        return false;
      }
    }
    
    const payloadString = JSON.stringify(payload);
    
    // Create HMAC using the secret key
    const hmac = createHmac(signatureConfig.algorithm, secretKey);
    
    // Update HMAC with timestamp and payload if timestamp is provided
    if (timestamp && signatureConfig.includeTimestamp) {
      hmac.update(`${timestamp}.${payloadString}`);
    } else {
      hmac.update(payloadString);
    }
    
    // Generate the expected signature
    const expectedSignature = hmac.digest(signatureConfig.encoding);
    
    // Use constant-time comparison to prevent timing attacks
    const signatureBuffer = Buffer.from(signature, signatureConfig.encoding);
    const expectedBuffer = Buffer.from(expectedSignature, signatureConfig.encoding);
    
    const isValid = signatureBuffer.length === expectedBuffer.length && 
                    timingSafeEqual(signatureBuffer, expectedBuffer);
    
    logger.debug('Verified webhook signature', { isValid, timestamp });
    
    return isValid;
  } catch (error) {
    logger.error('Error verifying webhook signature', { error });
    return false;
  }
};

/**
 * Calculates the next retry time for a failed webhook delivery
 * @param retryAttempt The current retry attempt (0-based)
 * @param retryPolicy The retry policy to use
 * @returns The timestamp for the next retry attempt
 */
export const calculateNextRetryTime = (
  retryAttempt: number,
  retryPolicy: IWebhookRetryPolicy = defaultRetryPolicy
): Date => {
  // Calculate the base delay using exponential backoff
  const baseDelayMs = Math.min(
    retryPolicy.initialDelayMs * Math.pow(retryPolicy.backoffFactor, retryAttempt),
    retryPolicy.maxDelayMs
  );
  
  // Add jitter if enabled to prevent thundering herd problem
  let delayMs = baseDelayMs;
  if (retryPolicy.useJitter) {
    const jitterAmount = baseDelayMs * 0.1; // 10% jitter
    delayMs = baseDelayMs + (Math.random() * jitterAmount * 2) - jitterAmount;
  }
  
  // Calculate the next retry time
  const nextRetryTime = new Date(Date.now() + delayMs);
  
  logger.debug('Calculated next retry time', {
    retryAttempt,
    baseDelayMs,
    actualDelayMs: delayMs,
    nextRetryTime: nextRetryTime.toISOString(),
  });
  
  return nextRetryTime;
};

/**
 * Determines if a webhook delivery should be retried based on the result and policy
 * @param statusCode HTTP status code from the delivery attempt
 * @param retryCount Current retry count
 * @param retryPolicy Retry policy to use
 * @returns Whether the delivery should be retried
 */
export const shouldRetryDelivery = (
  statusCode: number | undefined,
  retryCount: number,
  retryPolicy: IWebhookRetryPolicy = defaultRetryPolicy
): boolean => {
  // Don't retry if max retries reached
  if (retryCount >= retryPolicy.maxRetries) {
    logger.info('Max retry attempts reached for webhook', {
      maxRetries: retryPolicy.maxRetries,
      retryCount,
    });
    return false;
  }
  
  // Check if status code is retryable
  if (statusCode) {
    const isRetryableStatusCode = retryPolicy.retryableStatusCodes.includes(statusCode);
    
    if (!isRetryableStatusCode) {
      // Check if it's a 5xx error, which is typically retryable
      const isServerError = statusCode >= 500 && statusCode < 600;
      
      if (!isServerError) {
        logger.info('Non-retryable status code for webhook', {
          statusCode,
        });
        return false;
      }
    }
  }
  
  // If we got here, we should retry
  logger.info('Scheduling webhook delivery for retry', {
    retryCount,
    nextRetryAttempt: retryCount + 1,
  });
  
  return true;
};

/**
 * Creates a webhook configuration with default values
 * @param id Unique identifier for the webhook
 * @param url URL of the webhook endpoint
 * @param secretKey Secret key for signature generation
 * @param options Additional options for the webhook
 * @returns A complete webhook configuration
 */
export const createWebhookConfig = (
  id: string,
  url: string,
  secretKey: string,
  options: Partial<IWebhookConfig> = {}
): IWebhookConfig => {
  return {
    id,
    name: options.name || `Webhook ${id}`,
    description: options.description,
    url,
    method: options.method || 'POST',
    status: options.status || 'ACTIVE',
    auth: options.auth,
    headers: options.headers,
    secretKey,
    retryPolicy: options.retryPolicy || defaultRetryPolicy,
    eventTypes: options.eventTypes || ['*'],
    createdAt: options.createdAt || new Date().toISOString(),
    updatedAt: options.updatedAt || new Date().toISOString(),
    lastCalledAt: options.lastCalledAt,
    lastCallResult: options.lastCallResult,
  };
};

export default webhookConfig;