/**
 * Common Types
 * 
 * This file defines shared TypeScript type definitions used across the Notification Service.
 * It provides common interfaces for date handling, logging context, error responses,
 * service status, and retry options.
 */

/**
 * Interface for consistent date representation across the service
 */
export interface IDateValue {
  /** ISO 8601 formatted date string */
  iso: string;
  /** Unix timestamp in milliseconds */
  timestamp: number;
  /** JavaScript Date object */
  date: Date;
}

/**
 * Interface for structured logging with correlation IDs and metadata
 */
export interface ILogContext {
  /** Correlation ID for distributed tracing */
  correlationId?: string;
  /** Request ID for individual request tracking */
  requestId?: string;
  /** HTTP method of the request */
  method?: string;
  /** Request path */
  path?: string;
  /** Client IP address */
  ip?: string;
  /** User agent string */
  userAgent?: string;
  /** Additional context metadata */
  [key: string]: any;
}

/**
 * Interface for standardized error responses
 */
export interface IErrorResponse {
  /** HTTP status code */
  status: number;
  /** Error code for client-side error handling */
  code: string;
  /** Human-readable error message */
  message: string;
  /** Additional error details */
  details?: any;
  /** Request ID for error tracking */
  requestId?: string;
  /** Timestamp of the error */
  timestamp?: string;
}

/**
 * Interface for health check responses
 */
export interface IServiceStatus {
  /** Service name */
  service: string;
  /** Service status (up, down, degraded) */
  status: 'up' | 'down' | 'degraded';
  /** Service version */
  version: string;
  /** Uptime in seconds */
  uptime: number;
  /** Timestamp of the status check */
  timestamp: string;
  /** Additional status details */
  details?: {
    /** Database connection status */
    database?: 'up' | 'down' | 'degraded';
    /** Message queue connection status */
    messageQueue?: 'up' | 'down' | 'degraded';
    /** Cache connection status */
    cache?: 'up' | 'down' | 'degraded';
    /** Additional service-specific status details */
    [key: string]: any;
  };
}

/**
 * Interface for configuring retry behavior with backoff settings
 */
export interface IRetryOptions {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial delay in milliseconds before the first retry */
  initialDelayMs: number;
  /** Backoff factor for exponential backoff */
  backoffFactor: number;
  /** Maximum delay in milliseconds between retries */
  maxDelayMs: number;
  /** Whether to add jitter to retry delays */
  jitter: boolean;
  /** Specific status codes that should trigger a retry */
  retryableStatusCodes?: number[];
  /** Specific error types that should trigger a retry */
  retryableErrors?: string[];
}