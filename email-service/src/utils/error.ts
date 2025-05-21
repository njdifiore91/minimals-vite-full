/**
 * Error handling utilities for the Email Service
 * 
 * This module provides standardized error handling utilities for creating structured error objects,
 * classifying errors, and formatting error messages. It enables consistent error handling across
 * the service and supports proper error tracking and troubleshooting.
 */

import { IErrorDetails, ErrorCategory, ErrorSeverity, RetryStrategy } from '../types';

/**
 * Base service error class that extends the built-in Error object
 * Provides additional context and classification for service errors
 */
export class ServiceError extends Error {
  /** Unique error code for identification */
  public readonly code: string;
  
  /** Error category for classification */
  public readonly category: ErrorCategory;
  
  /** Error severity level */
  public readonly severity: ErrorSeverity;
  
  /** Whether this error is eligible for retry */
  public readonly retryable: boolean;
  
  /** Recommended retry strategy if applicable */
  public readonly retryStrategy?: RetryStrategy;
  
  /** Additional context information */
  public readonly context: Record<string, unknown>;
  
  /** Original error if this is a wrapped error */
  public readonly cause?: Error;
  
  /** Timestamp when the error occurred */
  public readonly timestamp: Date;

  /**
   * Creates a new ServiceError instance
   * 
   * @param message Error message
   * @param options Error options
   */
  constructor(message: string, options?: {
    code?: string;
    category?: ErrorCategory;
    severity?: ErrorSeverity;
    retryable?: boolean;
    retryStrategy?: RetryStrategy;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message);
    
    // Ensure proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, ServiceError.prototype);
    
    this.name = this.constructor.name;
    this.code = options?.code || 'ERR_UNKNOWN';
    this.category = options?.category || ErrorCategory.UNKNOWN;
    this.severity = options?.severity || ErrorSeverity.ERROR;
    this.retryable = options?.retryable ?? false;
    this.retryStrategy = options?.retryStrategy;
    this.context = options?.context || {};
    this.cause = options?.cause;
    this.timestamp = new Date();
    
    // Capture stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  /**
   * Serializes the error to a plain object for logging or message publishing
   * 
   * @returns Serialized error details
   */
  public toJSON(): IErrorDetails {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      category: this.category,
      severity: this.severity,
      retryable: this.retryable,
      retryStrategy: this.retryStrategy,
      context: this.context,
      stack: this.stack,
      cause: this.cause ? {
        name: this.cause.name,
        message: this.cause.message,
        stack: this.cause.stack
      } : undefined,
      timestamp: this.timestamp.toISOString()
    };
  }
}

/**
 * Validation error for invalid input data
 */
export class ValidationError extends ServiceError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_VALIDATION',
      category: ErrorCategory.VALIDATION,
      severity: options?.severity || ErrorSeverity.WARNING,
      retryable: false, // Validation errors are not retryable
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * Connection error for network and service connectivity issues
 */
export class ConnectionError extends ServiceError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    retryable?: boolean;
    retryStrategy?: RetryStrategy;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_CONNECTION',
      category: ErrorCategory.CONNECTION,
      severity: options?.severity || ErrorSeverity.ERROR,
      retryable: options?.retryable ?? true, // Connection errors are typically retryable
      retryStrategy: options?.retryStrategy || RetryStrategy.EXPONENTIAL_BACKOFF,
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * IMAP connection error for email server connectivity issues
 */
export class ImapConnectionError extends ConnectionError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    retryable?: boolean;
    retryStrategy?: RetryStrategy;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_IMAP_CONNECTION',
      severity: options?.severity || ErrorSeverity.ERROR,
      retryable: options?.retryable ?? true,
      retryStrategy: options?.retryStrategy || RetryStrategy.EXPONENTIAL_BACKOFF,
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * RabbitMQ connection error for message queue connectivity issues
 */
export class RabbitMQConnectionError extends ConnectionError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    retryable?: boolean;
    retryStrategy?: RetryStrategy;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_RABBITMQ_CONNECTION',
      severity: options?.severity || ErrorSeverity.ERROR,
      retryable: options?.retryable ?? true,
      retryStrategy: options?.retryStrategy || RetryStrategy.EXPONENTIAL_BACKOFF,
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * S3 storage error for document storage issues
 */
export class StorageError extends ServiceError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    retryable?: boolean;
    retryStrategy?: RetryStrategy;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_STORAGE',
      category: ErrorCategory.STORAGE,
      severity: options?.severity || ErrorSeverity.ERROR,
      retryable: options?.retryable ?? true, // Storage errors are typically retryable
      retryStrategy: options?.retryStrategy || RetryStrategy.EXPONENTIAL_BACKOFF,
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * Processing error for email and attachment processing issues
 */
export class ProcessingError extends ServiceError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    retryable?: boolean;
    retryStrategy?: RetryStrategy;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_PROCESSING',
      category: ErrorCategory.PROCESSING,
      severity: options?.severity || ErrorSeverity.ERROR,
      retryable: options?.retryable ?? false, // Processing errors are typically not retryable
      retryStrategy: options?.retryStrategy,
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * Configuration error for service configuration issues
 */
export class ConfigurationError extends ServiceError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_CONFIGURATION',
      category: ErrorCategory.CONFIGURATION,
      severity: options?.severity || ErrorSeverity.CRITICAL,
      retryable: false, // Configuration errors are not retryable
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * Security error for authentication and authorization issues
 */
export class SecurityError extends ServiceError {
  constructor(message: string, options?: {
    code?: string;
    severity?: ErrorSeverity;
    context?: Record<string, unknown>;
    cause?: Error;
  }) {
    super(message, {
      code: options?.code || 'ERR_SECURITY',
      category: ErrorCategory.SECURITY,
      severity: options?.severity || ErrorSeverity.CRITICAL,
      retryable: false, // Security errors are not retryable
      context: options?.context,
      cause: options?.cause
    });
  }
}

/**
 * Determines if an error is a ServiceError instance
 * 
 * @param error Error to check
 * @returns True if the error is a ServiceError instance
 */
export function isServiceError(error: unknown): error is ServiceError {
  return error instanceof ServiceError;
}

/**
 * Creates a ServiceError from any error type
 * 
 * @param error Original error
 * @param options Additional error options
 * @returns ServiceError instance
 */
export function createServiceError(error: unknown, options?: {
  message?: string;
  code?: string;
  category?: ErrorCategory;
  severity?: ErrorSeverity;
  retryable?: boolean;
  retryStrategy?: RetryStrategy;
  context?: Record<string, unknown>;
}): ServiceError {
  if (isServiceError(error)) {
    // If it's already a ServiceError, return it with merged options
    if (options) {
      return new ServiceError(options.message || error.message, {
        code: options.code || error.code,
        category: options.category || error.category,
        severity: options.severity || error.severity,
        retryable: options.retryable !== undefined ? options.retryable : error.retryable,
        retryStrategy: options.retryStrategy || error.retryStrategy,
        context: { ...error.context, ...options.context },
        cause: error.cause
      });
    }
    return error;
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    return new ServiceError(options?.message || error.message, {
      code: options?.code || 'ERR_UNKNOWN',
      category: options?.category || ErrorCategory.UNKNOWN,
      severity: options?.severity || ErrorSeverity.ERROR,
      retryable: options?.retryable ?? false,
      retryStrategy: options?.retryStrategy,
      context: options?.context || {},
      cause: error
    });
  }

  // Handle non-Error objects (string, number, etc.)
  const errorMessage = options?.message || 
    (typeof error === 'string' ? error : 
    (error ? String(error) : 'Unknown error'));

  return new ServiceError(errorMessage, {
    code: options?.code || 'ERR_UNKNOWN',
    category: options?.category || ErrorCategory.UNKNOWN,
    severity: options?.severity || ErrorSeverity.ERROR,
    retryable: options?.retryable ?? false,
    retryStrategy: options?.retryStrategy,
    context: options?.context || { originalError: error }
  });
}

/**
 * Determines if an error is retryable based on its type and properties
 * 
 * @param error Error to check
 * @returns True if the error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  if (isServiceError(error)) {
    return error.retryable;
  }

  // Default retry logic for standard errors
  if (error instanceof Error) {
    // Network errors are typically retryable
    if (
      error.name === 'NetworkError' ||
      error.name === 'FetchError' ||
      error.name === 'AbortError' ||
      error.name === 'TimeoutError' ||
      error.message.includes('ECONNRESET') ||
      error.message.includes('ETIMEDOUT') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('network timeout') ||
      error.message.includes('network error')
    ) {
      return true;
    }
  }

  return false;
}

/**
 * Enriches an error with additional context information
 * 
 * @param error Original error
 * @param context Additional context information
 * @returns Enriched ServiceError
 */
export function enrichError(error: unknown, context: Record<string, unknown>): ServiceError {
  if (isServiceError(error)) {
    return new ServiceError(error.message, {
      code: error.code,
      category: error.category,
      severity: error.severity,
      retryable: error.retryable,
      retryStrategy: error.retryStrategy,
      context: { ...error.context, ...context },
      cause: error.cause
    });
  }

  return createServiceError(error, { context });
}

/**
 * Gets a recommended retry delay in milliseconds based on the error and attempt count
 * 
 * @param error Error that occurred
 * @param attempt Current attempt number (1-based)
 * @param baseDelay Base delay in milliseconds
 * @param maxDelay Maximum delay in milliseconds
 * @returns Recommended delay in milliseconds
 */
export function getRetryDelay(
  error: unknown,
  attempt: number,
  baseDelay = 1000,
  maxDelay = 30000
): number {
  if (!isRetryableError(error)) {
    return 0; // Not retryable
  }

  const serviceError = isServiceError(error) ? error : createServiceError(error);
  const strategy = serviceError.retryStrategy || RetryStrategy.EXPONENTIAL_BACKOFF;

  switch (strategy) {
    case RetryStrategy.FIXED:
      return Math.min(baseDelay, maxDelay);

    case RetryStrategy.LINEAR:
      return Math.min(baseDelay * attempt, maxDelay);

    case RetryStrategy.EXPONENTIAL_BACKOFF:
      // Exponential backoff with jitter to prevent thundering herd
      const exponentialDelay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
      const jitter = Math.random() * 0.3 * exponentialDelay; // 0-30% jitter
      return Math.floor(exponentialDelay + jitter);

    default:
      return Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
  }
}

/**
 * Formats an error for logging
 * 
 * @param error Error to format
 * @returns Formatted error object for logging
 */
export function formatErrorForLogging(error: unknown): Record<string, unknown> {
  if (isServiceError(error)) {
    return error.toJSON();
  }

  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    };
  }

  return {
    error: typeof error === 'string' ? error : String(error),
    timestamp: new Date().toISOString()
  };
}