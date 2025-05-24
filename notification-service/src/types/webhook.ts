/**
 * @file webhook.ts
 * @description TypeScript interfaces and types for webhook configuration, delivery, and security.
 * This file provides type definitions for webhook endpoints, HTTP methods, headers, payloads,
 * signatures, and retry policies. It ensures type safety for webhook operations and enables
 * secure and reliable webhook delivery.
 */

/**
 * Supported HTTP methods for webhook endpoints.
 */
export enum WebhookMethod {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  PATCH = 'PATCH',
  DELETE = 'DELETE',
}

/**
 * Status of a webhook endpoint.
 */
export enum WebhookStatus {
  /** Webhook is active and receiving notifications */
  ACTIVE = 'ACTIVE',
  /** Webhook is temporarily disabled */
  INACTIVE = 'INACTIVE',
  /** Webhook has failed too many times and is disabled */
  FAILED = 'FAILED',
}

/**
 * Authentication types supported for webhook endpoints.
 */
export enum WebhookAuthType {
  /** No authentication */
  NONE = 'NONE',
  /** Basic HTTP authentication */
  BASIC = 'BASIC',
  /** Bearer token authentication */
  BEARER = 'BEARER',
  /** API key authentication */
  API_KEY = 'API_KEY',
  /** Custom authentication scheme */
  CUSTOM = 'CUSTOM',
}

/**
 * Interface for webhook authentication configuration.
 */
export interface IWebhookAuth {
  /** Type of authentication to use */
  type: WebhookAuthType;
  /** Username for BASIC auth */
  username?: string;
  /** Password for BASIC auth */
  password?: string;
  /** Token for BEARER auth */
  token?: string;
  /** API key name for API_KEY auth */
  apiKeyName?: string;
  /** API key value for API_KEY auth */
  apiKeyValue?: string;
  /** Header name for CUSTOM auth */
  headerName?: string;
  /** Header value for CUSTOM auth */
  headerValue?: string;
}

/**
 * Interface for webhook endpoint configuration.
 */
export interface IWebhookConfig {
  /** Unique identifier for the webhook */
  id: string;
  /** Name of the webhook for display purposes */
  name: string;
  /** Description of the webhook purpose */
  description?: string;
  /** URL of the webhook endpoint */
  url: string;
  /** HTTP method to use when calling the webhook */
  method: WebhookMethod;
  /** Current status of the webhook */
  status: WebhookStatus;
  /** Authentication configuration for the webhook */
  auth?: IWebhookAuth;
  /** Custom headers to include in webhook requests */
  headers?: IWebhookHeaders;
  /** Secret key used for HMAC-SHA256 signature generation */
  secretKey: string;
  /** Retry policy for failed webhook deliveries */
  retryPolicy: IWebhookRetryPolicy;
  /** Event types this webhook should receive */
  eventTypes: string[];
  /** Timestamp when the webhook was created */
  createdAt: string;
  /** Timestamp when the webhook was last updated */
  updatedAt: string;
  /** Timestamp when the webhook was last called */
  lastCalledAt?: string;
  /** Result of the last webhook call */
  lastCallResult?: IWebhookDeliveryResult;
}

/**
 * Interface for HTTP headers in webhook requests.
 */
export interface IWebhookHeaders {
  /** Content-Type header, defaults to application/json */
  'Content-Type'?: string;
  /** Accept header */
  'Accept'?: string;
  /** User-Agent header */
  'User-Agent'?: string;
  /** X-Webhook-Signature header for HMAC signature */
  'X-Webhook-Signature'?: string;
  /** X-Webhook-Timestamp header for signature timestamp */
  'X-Webhook-Timestamp'?: string;
  /** X-Webhook-ID header for webhook identifier */
  'X-Webhook-ID'?: string;
  /** X-Webhook-Event header for event type */
  'X-Webhook-Event'?: string;
  /** Additional custom headers */
  [key: string]: string | undefined;
}

/**
 * Interface for structured webhook payload.
 * All webhook payloads must follow this structure to ensure consistency.
 */
export interface IWebhookPayload<T = unknown> {
  /** Unique identifier for this webhook delivery */
  id: string;
  /** Timestamp when the event occurred */
  timestamp: string;
  /** Type of event that triggered this webhook */
  eventType: string;
  /** Version of the webhook payload schema */
  version: string;
  /** The actual data payload */
  data: T;
  /** Additional metadata about the event */
  metadata?: Record<string, unknown>;
}

/**
 * Interface for webhook response handling.
 */
export interface IWebhookResponse {
  /** HTTP status code returned by the webhook endpoint */
  statusCode: number;
  /** Response headers */
  headers: Record<string, string | string[] | undefined>;
  /** Response body */
  body?: unknown;
  /** Time taken to receive the response in milliseconds */
  responseTime: number;
  /** Whether the response is considered successful (2xx status code) */
  isSuccess: boolean;
  /** Error message if the request failed */
  errorMessage?: string;
}

/**
 * Interface for HMAC-SHA256 signature generation.
 */
export interface IWebhookSignature {
  /** The generated signature */
  signature: string;
  /** Timestamp used in the signature generation */
  timestamp: string;
  /** Algorithm used for signature generation (always HMAC-SHA256) */
  algorithm: 'HMAC-SHA256';
  /** Encoding format of the signature (hex or base64) */
  encoding: 'hex' | 'base64';
  /** Headers included in the signature */
  includedHeaders?: string[];
}

/**
 * Interface for configuring retry behavior for failed webhook deliveries.
 */
export interface IWebhookRetryPolicy {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial retry delay in milliseconds */
  initialDelayMs: number;
  /** Backoff factor for exponential backoff (e.g., 2 means each retry waits twice as long as the previous) */
  backoffFactor: number;
  /** Maximum delay between retries in milliseconds */
  maxDelayMs: number;
  /** Whether to add jitter to retry delays to prevent thundering herd problems */
  useJitter: boolean;
  /** HTTP status codes that should trigger a retry */
  retryableStatusCodes: number[];
  /** Whether to retry on network errors */
  retryOnNetworkError: boolean;
}

/**
 * Interface for tracking webhook delivery outcomes.
 */
export interface IWebhookDeliveryResult {
  /** Unique identifier for this delivery attempt */
  id: string;
  /** ID of the webhook configuration */
  webhookId: string;
  /** ID of the event that triggered this webhook */
  eventId: string;
  /** Timestamp when the delivery was attempted */
  timestamp: string;
  /** Whether the delivery was successful */
  success: boolean;
  /** HTTP status code returned by the webhook endpoint */
  statusCode?: number;
  /** Error message if the delivery failed */
  errorMessage?: string;
  /** Response body from the webhook endpoint */
  responseBody?: string;
  /** Time taken to deliver the webhook in milliseconds */
  deliveryTimeMs: number;
  /** Number of retry attempts made */
  retryCount: number;
  /** Timestamp of the next retry attempt if applicable */
  nextRetryAt?: string;
}

/**
 * Interface for webhook delivery request.
 */
export interface IWebhookDeliveryRequest {
  /** The webhook configuration to use */
  webhook: IWebhookConfig;
  /** The payload to deliver */
  payload: IWebhookPayload;
  /** The signature to include with the request */
  signature: IWebhookSignature;
  /** Additional headers to include */
  additionalHeaders?: Record<string, string>;
  /** Timeout for the request in milliseconds */
  timeoutMs?: number;
  /** Current retry attempt (0 for initial attempt) */
  retryAttempt?: number;
}

/**
 * Interface for webhook verification request.
 */
export interface IWebhookVerificationRequest {
  /** URL to verify */
  url: string;
  /** HTTP method to use */
  method: WebhookMethod;
  /** Headers to include */
  headers?: IWebhookHeaders;
  /** Authentication to use */
  auth?: IWebhookAuth;
  /** Timeout for the request in milliseconds */
  timeoutMs?: number;
}

/**
 * Interface for webhook verification response.
 */
export interface IWebhookVerificationResult {
  /** Whether the verification was successful */
  success: boolean;
  /** HTTP status code returned by the webhook endpoint */
  statusCode?: number;
  /** Response time in milliseconds */
  responseTimeMs?: number;
  /** Error message if the verification failed */
  errorMessage?: string;
  /** Detailed error information if available */
  errorDetails?: Record<string, unknown>;
}