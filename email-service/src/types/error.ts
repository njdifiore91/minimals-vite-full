/**
 * Error handling type definitions for the Email Service
 * 
 * This module defines TypeScript interfaces and enums for error handling,
 * logging, and monitoring used by the Email Service. It provides type
 * definitions for standardized error structures, logging formats, and
 * error classification.
 */

/**
 * Error categories for classification
 */
export enum ErrorCategory {
  /** Unknown or unclassified error */
  UNKNOWN = 'unknown',
  
  /** Input validation error */
  VALIDATION = 'validation',
  
  /** Network or service connection error */
  CONNECTION = 'connection',
  
  /** Data processing error */
  PROCESSING = 'processing',
  
  /** Configuration error */
  CONFIGURATION = 'configuration',
  
  /** Security or authentication error */
  SECURITY = 'security',
  
  /** Storage or database error */
  STORAGE = 'storage',
  
  /** External service error */
  EXTERNAL = 'external'
}

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  /** Debug-level error, minimal impact */
  DEBUG = 'debug',
  
  /** Informational error, no impact */
  INFO = 'info',
  
  /** Warning-level error, potential impact */
  WARNING = 'warning',
  
  /** Standard error, operational impact */
  ERROR = 'error',
  
  /** Critical error, severe operational impact */
  CRITICAL = 'critical'
}

/**
 * Retry strategies for handling retryable errors
 */
export enum RetryStrategy {
  /** Fixed delay between retry attempts */
  FIXED = 'fixed',
  
  /** Linear increasing delay between retry attempts */
  LINEAR = 'linear',
  
  /** Exponential backoff with jitter */
  EXPONENTIAL_BACKOFF = 'exponential_backoff'
}

/**
 * Serialized error details for logging and monitoring
 */
export interface IErrorDetails {
  /** Error name or class */
  name: string;
  
  /** Error message */
  message: string;
  
  /** Error code for identification */
  code: string;
  
  /** Error category for classification */
  category: ErrorCategory;
  
  /** Error severity level */
  severity: ErrorSeverity;
  
  /** Whether this error is eligible for retry */
  retryable: boolean;
  
  /** Recommended retry strategy if applicable */
  retryStrategy?: RetryStrategy;
  
  /** Additional context information */
  context: Record<string, unknown>;
  
  /** Error stack trace */
  stack?: string;
  
  /** Original error if this is a wrapped error */
  cause?: {
    name: string;
    message: string;
    stack?: string;
  };
  
  /** Timestamp when the error occurred */
  timestamp: string;
}

/**
 * Log entry structure for error logging
 */
export interface IErrorLogEntry {
  /** Log timestamp */
  timestamp: string;
  
  /** Log level */
  level: string;
  
  /** Service name */
  service: string;
  
  /** Error details */
  error: IErrorDetails;
  
  /** Request ID for distributed tracing */
  requestId?: string;
  
  /** Additional context information */
  context?: Record<string, unknown>;
}

/**
 * Error monitoring metrics
 */
export interface IErrorMetrics {
  /** Error count by category */
  countByCategory: Record<ErrorCategory, number>;
  
  /** Error count by severity */
  countBySeverity: Record<ErrorSeverity, number>;
  
  /** Error count by code */
  countByCode: Record<string, number>;
  
  /** Total error count */
  totalCount: number;
  
  /** Time period for metrics (ISO string) */
  period: {
    start: string;
    end: string;
  };
}