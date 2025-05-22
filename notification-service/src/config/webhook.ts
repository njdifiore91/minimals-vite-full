/**
 * Webhook Configuration
 * 
 * This file defines the configuration for webhook delivery, including:
 * - HMAC-SHA256 signature generation for webhook payloads
 * - Exponential backoff retry mechanism with configurable retry counts and intervals
 * - Dead letter queue for persistently failed notifications
 * - Timeout settings for webhook requests
 * - Payload structure validation with schema validation
 */

import { IWebhookConfig, IWebhookRetryPolicy } from '../types/webhook';

/**
 * Default retry policy for webhook deliveries
 * Implements exponential backoff with configurable parameters
 */
export const defaultRetryPolicy: IWebhookRetryPolicy = {
  // Maximum number of retry attempts before sending to dead letter queue
  maxRetries: Number(process.env.WEBHOOK_MAX_RETRIES) || 5,
  
  // Initial delay in milliseconds before the first retry
  initialDelayMs: Number(process.env.WEBHOOK_INITIAL_DELAY_MS) || 1000,
  
  // Multiplier for exponential backoff calculation
  backoffMultiplier: Number(process.env.WEBHOOK_BACKOFF_MULTIPLIER) || 2,
  
  // Maximum delay in milliseconds between retries
  maxDelayMs: Number(process.env.WEBHOOK_MAX_DELAY_MS) || 60000, // 1 minute
  
  // Whether to add jitter to the delay to prevent thundering herd problem
  useJitter: process.env.WEBHOOK_USE_JITTER === 'true',
  
  // Maximum jitter percentage (0-1) to apply to the delay
  jitterFactor: Number(process.env.WEBHOOK_JITTER_FACTOR) || 0.1,
};

/**
 * Dead letter queue configuration for persistently failed webhook deliveries
 */
export const deadLetterQueueConfig = {
  // Whether to enable the dead letter queue
  enabled: process.env.WEBHOOK_DLQ_ENABLED === 'true',
  
  // Exchange name for the dead letter queue
  exchangeName: process.env.WEBHOOK_DLQ_EXCHANGE || 'webhook.dlx',
  
  // Queue name for the dead letter queue
  queueName: process.env.WEBHOOK_DLQ_QUEUE || 'webhook.dlq',
  
  // Routing key for the dead letter queue
  routingKey: process.env.WEBHOOK_DLQ_ROUTING_KEY || 'webhook.failed',
  
  // TTL for messages in the dead letter queue (in milliseconds)
  // Default: 7 days
  messageTtl: Number(process.env.WEBHOOK_DLQ_MESSAGE_TTL) || 7 * 24 * 60 * 60 * 1000,
  
  // Whether to store the original payload with the failed delivery
  storePayload: process.env.WEBHOOK_DLQ_STORE_PAYLOAD === 'true',
  
  // Whether to store the error details with the failed delivery
  storeErrorDetails: process.env.WEBHOOK_DLQ_STORE_ERROR_DETAILS !== 'false',
};

/**
 * HMAC-SHA256 signature configuration for webhook payloads
 */
export const signatureConfig = {
  // Whether to sign webhook payloads
  enabled: process.env.WEBHOOK_SIGNATURE_ENABLED !== 'false',
  
  // Default secret key for HMAC-SHA256 signature generation
  // This should be overridden by customer-specific secret keys
  defaultSecretKey: process.env.WEBHOOK_SIGNATURE_DEFAULT_SECRET || 'default-webhook-secret',
  
  // Header name for the signature
  headerName: process.env.WEBHOOK_SIGNATURE_HEADER_NAME || 'X-Webhook-Signature',
  
  // Algorithm to use for signature generation
  algorithm: process.env.WEBHOOK_SIGNATURE_ALGORITHM || 'sha256',
  
  // Whether to include a timestamp in the signature
  includeTimestamp: process.env.WEBHOOK_SIGNATURE_INCLUDE_TIMESTAMP === 'true',
  
  // Header name for the timestamp (if included)
  timestampHeaderName: process.env.WEBHOOK_SIGNATURE_TIMESTAMP_HEADER_NAME || 'X-Webhook-Timestamp',
  
  // Maximum age of a webhook signature in milliseconds (default: 5 minutes)
  // Used to prevent replay attacks
  maxAge: Number(process.env.WEBHOOK_SIGNATURE_MAX_AGE) || 5 * 60 * 1000,
};

/**
 * HTTP request configuration for webhook delivery
 */
export const httpConfig = {
  // Timeout for webhook requests in milliseconds (default: 10 seconds)
  timeoutMs: Number(process.env.WEBHOOK_HTTP_TIMEOUT_MS) || 10000,
  
  // Whether to follow redirects
  followRedirects: process.env.WEBHOOK_HTTP_FOLLOW_REDIRECTS !== 'false',
  
  // Maximum number of redirects to follow
  maxRedirects: Number(process.env.WEBHOOK_HTTP_MAX_REDIRECTS) || 5,
  
  // Default headers to include with all webhook requests
  defaultHeaders: {
    'Content-Type': 'application/json',
    'User-Agent': `DollarFunding-Webhook-Service/${process.env.npm_package_version || '1.0.0'}`,
  },
  
  // Whether to validate SSL certificates
  validateSSL: process.env.WEBHOOK_HTTP_VALIDATE_SSL !== 'false',
};

/**
 * Schema validation configuration for webhook payloads
 */
export const schemaValidationConfig = {
  // Whether to validate webhook payloads against schemas
  enabled: process.env.WEBHOOK_SCHEMA_VALIDATION_ENABLED !== 'false',
  
  // Whether to reject payloads that fail validation
  rejectInvalid: process.env.WEBHOOK_SCHEMA_VALIDATION_REJECT_INVALID !== 'false',
  
  // Whether to log validation errors
  logErrors: process.env.WEBHOOK_SCHEMA_VALIDATION_LOG_ERRORS !== 'false',
  
  // Path to schema definitions (relative to project root)
  schemaPath: process.env.WEBHOOK_SCHEMA_VALIDATION_PATH || './schemas',
};

/**
 * Acknowledgment configuration for webhook delivery
 */
export const acknowledgmentConfig = {
  // Whether to require acknowledgment from webhook recipients
  required: process.env.WEBHOOK_ACK_REQUIRED !== 'false',
  
  // HTTP status codes that are considered successful acknowledgments
  successCodes: (process.env.WEBHOOK_ACK_SUCCESS_CODES || '200,201,202,204')
    .split(',')
    .map(code => parseInt(code.trim(), 10)),
  
  // Timeout for acknowledgment in milliseconds (default: 30 seconds)
  timeoutMs: Number(process.env.WEBHOOK_ACK_TIMEOUT_MS) || 30000,
};

/**
 * Main webhook configuration that combines all settings
 */
export const webhookConfig: IWebhookConfig = {
  // Whether the webhook service is enabled
  enabled: process.env.WEBHOOK_ENABLED !== 'false',
  
  // Retry policy configuration
  retryPolicy: defaultRetryPolicy,
  
  // Dead letter queue configuration
  deadLetterQueue: deadLetterQueueConfig,
  
  // Signature configuration
  signature: signatureConfig,
  
  // HTTP request configuration
  http: httpConfig,
  
  // Schema validation configuration
  schemaValidation: schemaValidationConfig,
  
  // Acknowledgment configuration
  acknowledgment: acknowledgmentConfig,
  
  // Maximum concurrent webhook deliveries
  maxConcurrent: Number(process.env.WEBHOOK_MAX_CONCURRENT) || 50,
  
  // Whether to batch webhook deliveries when possible
  batchDeliveries: process.env.WEBHOOK_BATCH_DELIVERIES === 'true',
  
  // Maximum batch size for webhook deliveries
  maxBatchSize: Number(process.env.WEBHOOK_MAX_BATCH_SIZE) || 10,
};

/**
 * Helper function to calculate the exponential backoff delay with jitter
 * @param attempt The current retry attempt (0-based)
 * @param policy The retry policy to use
 * @returns The delay in milliseconds before the next retry
 */
export function calculateBackoffDelay(attempt: number, policy = defaultRetryPolicy): number {
  // Calculate the base delay using exponential backoff
  const baseDelay = Math.min(
    policy.initialDelayMs * Math.pow(policy.backoffMultiplier, attempt),
    policy.maxDelayMs
  );
  
  // Add jitter if enabled to prevent thundering herd problem
  if (policy.useJitter) {
    const jitterAmount = baseDelay * policy.jitterFactor;
    return baseDelay + (Math.random() * jitterAmount * 2) - jitterAmount;
  }
  
  return baseDelay;
}

/**
 * Helper function to generate an HMAC-SHA256 signature for a webhook payload
 * @param payload The webhook payload to sign
 * @param secretKey The secret key to use for signing
 * @param timestamp Optional timestamp to include in the signature
 * @returns The HMAC-SHA256 signature as a hexadecimal string
 */
export function generateWebhookSignature(
  payload: Record<string, any>,
  secretKey: string = signatureConfig.defaultSecretKey,
  timestamp?: number
): string {
  const crypto = require('crypto');
  
  // Create the string to sign
  let stringToSign: string;
  
  if (timestamp && signatureConfig.includeTimestamp) {
    // Include timestamp in the signature
    stringToSign = `${timestamp}.${JSON.stringify(payload)}`;
  } else {
    // Sign only the payload
    stringToSign = JSON.stringify(payload);
  }
  
  // Generate the HMAC-SHA256 signature
  const hmac = crypto.createHmac(signatureConfig.algorithm, secretKey);
  hmac.update(stringToSign);
  
  // Return the signature as a hexadecimal string
  return hmac.digest('hex');
}

/**
 * Helper function to verify a webhook signature
 * @param payload The webhook payload
 * @param signature The signature to verify
 * @param secretKey The secret key used for signing
 * @param timestamp Optional timestamp included in the signature
 * @returns Whether the signature is valid
 */
export function verifyWebhookSignature(
  payload: Record<string, any>,
  signature: string,
  secretKey: string = signatureConfig.defaultSecretKey,
  timestamp?: number
): boolean {
  const crypto = require('crypto');
  
  // Generate the expected signature
  const expectedSignature = generateWebhookSignature(payload, secretKey, timestamp);
  
  // Use a constant-time comparison to prevent timing attacks
  try {
    const signatureBuffer = Buffer.from(signature, 'hex');
    const expectedBuffer = Buffer.from(expectedSignature, 'hex');
    
    return crypto.timingSafeEqual(signatureBuffer, expectedBuffer);
  } catch (error) {
    // If there's an error (e.g., invalid hex string), the signature is invalid
    return false;
  }
}

export default webhookConfig;