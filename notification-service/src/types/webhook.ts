/**
 * Webhook Types
 * 
 * This file defines TypeScript interfaces and types for webhook configuration, delivery, and security.
 * It provides type definitions for webhook endpoints, HTTP methods, headers, payloads, signatures,
 * and retry policies to ensure type safety for webhook operations and enable secure and reliable
 * webhook delivery.
 */

import type { IDateValue, IRetryOptions } from './common';

// ----------------------------------------------------------------------

/**
 * Enum representing the HTTP methods supported for webhook requests.
 */
export enum WebhookMethod {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  PATCH = 'PATCH',
  DELETE = 'DELETE'
}

/**
 * Enum representing the possible statuses of a webhook endpoint.
 */
export enum WebhookStatus {
  ACTIVE = 'active',     // Webhook endpoint is active and receiving notifications
  INACTIVE = 'inactive', // Webhook endpoint is temporarily disabled
  FAILED = 'failed'      // Webhook endpoint has failed too many times and is disabled
}

/**
 * Interface for webhook endpoint configuration.
 */
export interface IWebhookConfig {
  /** Unique identifier for the webhook configuration */
  id: string;
  /** Name of the webhook for display purposes */
  name: string;
  /** Description of the webhook purpose */
  description?: string;
  /** URL of the webhook endpoint */
  url: string;
  /** HTTP method to use for the webhook request */
  method: WebhookMethod;
  /** Current status of the webhook endpoint */
  status: WebhookStatus;
  /** Secret key used for signing webhook payloads with HMAC-SHA256 */
  secret: string;
  /** Whether to verify SSL certificates when making webhook requests */
  verifySSL: boolean;
  /** Timeout in milliseconds for webhook requests */
  timeoutMs: number;
  /** Content type for the webhook payload */
  contentType: string;
  /** Authentication type (none, basic, bearer, custom) */
  authType?: 'none' | 'basic' | 'bearer' | 'custom';
  /** Authentication credentials if using basic auth */
  basicAuth?: {
    username: string;
    password: string;
  };
  /** Bearer token if using bearer auth */
  bearerToken?: string;
  /** Custom authentication header if using custom auth */
  customAuth?: {
    headerName: string;
    headerValue: string;
  };
  /** Event types this webhook should receive */
  eventTypes: string[];
  /** Retry policy for failed webhook deliveries */
  retryPolicy: IWebhookRetryPolicy;
  /** Created timestamp */
  createdAt: IDateValue;
  /** Last updated timestamp */
  updatedAt: IDateValue;
  /** Last successful delivery timestamp */
  lastSuccessAt?: IDateValue;
  /** Last failed delivery timestamp */
  lastFailureAt?: IDateValue;
  /** Consecutive failure count */
  consecutiveFailures: number;
  /** Maximum allowed consecutive failures before marking as failed */
  maxConsecutiveFailures: number;
  /** Tags for categorizing webhooks */
  tags?: string[];
  /** Owner or creator of the webhook */
  ownerId?: string;
  /** Associated application or merchant ID */
  applicationId?: string;
}

/**
 * Interface for HTTP headers used in webhook requests.
 */
export interface IWebhookHeaders {
  /** Content type header */
  'Content-Type': string;
  /** User agent header */
  'User-Agent'?: string;
  /** Webhook signature header */
  'X-Webhook-Signature'?: string;
  /** Timestamp of the request */
  'X-Webhook-Timestamp'?: string;
  /** ID of the webhook delivery attempt */
  'X-Webhook-ID'?: string;
  /** Event type that triggered the webhook */
  'X-Webhook-Event'?: string;
  /** Additional custom headers */
  [key: string]: string | undefined;
}

/**
 * Interface for structured webhook payload.
 */
export interface IWebhookPayload {
  /** Unique identifier for the webhook event */
  id: string;
  /** Type of event that triggered the webhook */
  event: string;
  /** Timestamp when the event occurred */
  timestamp: string;
  /** Version of the webhook payload schema */
  version: string;
  /** Environment the webhook was sent from (development, staging, production) */
  environment: string;
  /** Data associated with the webhook event */
  data: Record<string, any>;
  /** Additional metadata about the webhook event */
  metadata?: {
    /** ID of the application associated with the event */
    applicationId?: string;
    /** ID of the merchant associated with the event */
    merchantId?: string;
    /** IDs of documents associated with the event */
    documentIds?: string[];
    /** Additional custom metadata */
    [key: string]: any;
  };
}

/**
 * Interface for webhook response handling.
 */
export interface IWebhookResponse {
  /** HTTP status code returned by the webhook endpoint */
  statusCode: number;
  /** Response headers */
  headers: Record<string, string>;
  /** Response body */
  body: string;
  /** Whether the response indicates success (2xx status code) */
  success: boolean;
  /** Response time in milliseconds */
  responseTimeMs: number;
  /** Timestamp when the response was received */
  timestamp: IDateValue;
  /** Error message if the request failed */
  error?: string;
  /** Whether the response indicates the webhook should be retried */
  shouldRetry: boolean;
}

/**
 * Interface for HMAC-SHA256 signature generation and validation.
 */
export interface IWebhookSignature {
  /** Algorithm used for signature generation (sha256) */
  algorithm: 'sha256';
  /** Secret key used for signature generation */
  secret: string;
  /** Generated signature */
  signature: string;
  /** Timestamp used in signature generation */
  timestamp: string;
  /** Raw payload that was signed */
  payload: string;
  /** Header name where the signature is sent */
  headerName: string;
  /** Format of the signature header value */
  signatureFormat: 't={timestamp},v1={signature}' | 'v1={signature}' | '{signature}';
}

/**
 * Interface for configuring webhook retry behavior.
 */
export interface IWebhookRetryPolicy extends IRetryOptions {
  /** Whether to enable retries for this webhook */
  enabled: boolean;
  /** Whether to use exponential backoff for retry delays */
  useExponentialBackoff: boolean;
  /** Whether to add jitter to retry delays to prevent thundering herd */
  useJitter: boolean;
  /** HTTP status codes that should trigger a retry */
  retryableStatusCodes: number[];
  /** Whether to retry on connection errors */
  retryOnConnectionError: boolean;
  /** Whether to retry on timeout errors */
  retryOnTimeout: boolean;
  /** Whether to use a dead letter queue for failed webhooks */
  useDeadLetterQueue: boolean;
  /** Whether to notify administrators on persistent failures */
  notifyOnPersistentFailure: boolean;
}

/**
 * Interface for tracking webhook delivery outcomes.
 */
export interface IWebhookDeliveryResult {
  /** Unique identifier for the delivery attempt */
  id: string;
  /** ID of the webhook configuration */
  webhookId: string;
  /** ID of the webhook event */
  eventId: string;
  /** URL the webhook was sent to */
  url: string;
  /** HTTP method used for the request */
  method: WebhookMethod;
  /** Request headers */
  requestHeaders: IWebhookHeaders;
  /** Request payload */
  requestPayload: IWebhookPayload;
  /** Response from the webhook endpoint */
  response?: IWebhookResponse;
  /** Whether the delivery was successful */
  success: boolean;
  /** Timestamp when the delivery was attempted */
  timestamp: IDateValue;
  /** Duration of the delivery attempt in milliseconds */
  durationMs: number;
  /** Error message if the delivery failed */
  error?: string;
  /** Error code if the delivery failed */
  errorCode?: string;
  /** Current retry attempt number (0 for initial attempt) */
  retryCount: number;
  /** Maximum number of retries allowed */
  maxRetries: number;
  /** Whether the delivery will be retried */
  willRetry: boolean;
  /** Timestamp for the next retry attempt */
  nextRetryAt?: IDateValue;
  /** IP address the webhook was sent from */
  sourceIp?: string;
  /** Signature details if signing was enabled */
  signature?: {
    /** Generated signature */
    value: string;
    /** Timestamp used in signature generation */
    timestamp: string;
    /** Algorithm used for signature generation */
    algorithm: string;
  };
}

/**
 * Interface for webhook event types that can trigger notifications.
 */
export interface IWebhookEventType {
  /** Unique identifier for the event type */
  id: string;
  /** Name of the event type */
  name: string;
  /** Description of when this event is triggered */
  description: string;
  /** Example payload for this event type */
  examplePayload: Record<string, any>;
  /** Schema for validating payloads of this event type */
  schema: Record<string, any>;
  /** Whether this event type is enabled */
  enabled: boolean;
  /** Categories this event belongs to */
  categories: string[];
}

/**
 * Interface for webhook delivery statistics.
 */
export interface IWebhookStats {
  /** Webhook configuration ID */
  webhookId: string;
  /** Total number of delivery attempts */
  totalAttempts: number;
  /** Number of successful deliveries */
  successCount: number;
  /** Number of failed deliveries */
  failureCount: number;
  /** Success rate as a percentage */
  successRate: number;
  /** Average response time in milliseconds */
  avgResponseTimeMs: number;
  /** 95th percentile response time in milliseconds */
  p95ResponseTimeMs: number;
  /** 99th percentile response time in milliseconds */
  p99ResponseTimeMs: number;
  /** Number of retried deliveries */
  retryCount: number;
  /** Average number of retries per delivery */
  avgRetryCount: number;
  /** Time period these stats cover */
  period: {
    /** Start of the period */
    start: IDateValue;
    /** End of the period */
    end: IDateValue;
  };
}