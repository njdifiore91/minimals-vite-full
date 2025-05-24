/**
 * Error Utility Module
 * 
 * Provides standardized error handling utilities for the Email Service. This module exports
 * functions for creating structured error objects, classifying errors, and formatting error
 * messages. It's essential for consistent error handling across the service and enables
 * proper error tracking and troubleshooting.
 */

import { v4 as uuidv4 } from 'uuid';
import { fDateTime } from './format-time';
import { formatError, LogLevel } from './logger';
import { isRetryableError, RetryableErrorType, NonRetryableErrorType } from './retry';
import {
  ErrorCategory,
  ErrorSeverity,
  IErrorDetails,
  IServiceError,
  IErrorResponse,
  ILogEntry
} from '../types/error';

/**
 * Error codes for different types of errors
 */
export enum ErrorCode {
  // Network and connection errors
  NETWORK_UNAVAILABLE = 'E_NETWORK_UNAVAILABLE',
  CONNECTION_FAILED = 'E_CONNECTION_FAILED',
  CONNECTION_TIMEOUT = 'E_CONNECTION_TIMEOUT',
  CONNECTION_CLOSED = 'E_CONNECTION_CLOSED',
  
  // Authentication errors
  AUTH_FAILED = 'E_AUTH_FAILED',
  CREDENTIALS_INVALID = 'E_CREDENTIALS_INVALID',
  TOKEN_EXPIRED = 'E_TOKEN_EXPIRED',
  
  // Validation errors
  VALIDATION_FAILED = 'E_VALIDATION_FAILED',
  INVALID_EMAIL = 'E_INVALID_EMAIL',
  INVALID_ATTACHMENT = 'E_INVALID_ATTACHMENT',
  UNSUPPORTED_FILE_TYPE = 'E_UNSUPPORTED_FILE_TYPE',
  FILE_TOO_LARGE = 'E_FILE_TOO_LARGE',
  
  // Processing errors
  PROCESSING_FAILED = 'E_PROCESSING_FAILED',
  EXTRACTION_FAILED = 'E_EXTRACTION_FAILED',
  PARSING_FAILED = 'E_PARSING_FAILED',
  TRANSFORMATION_FAILED = 'E_TRANSFORMATION_FAILED',
  
  // Message queue errors
  QUEUE_CONNECTION_FAILED = 'E_QUEUE_CONNECTION_FAILED',
  QUEUE_PUBLISH_FAILED = 'E_QUEUE_PUBLISH_FAILED',
  QUEUE_CONSUME_FAILED = 'E_QUEUE_CONSUME_FAILED',
  
  // Storage errors
  STORAGE_CONNECTION_FAILED = 'E_STORAGE_CONNECTION_FAILED',
  STORAGE_UPLOAD_FAILED = 'E_STORAGE_UPLOAD_FAILED',
  STORAGE_DOWNLOAD_FAILED = 'E_STORAGE_DOWNLOAD_FAILED',
  
  // IMAP specific errors
  IMAP_CONNECTION_FAILED = 'E_IMAP_CONNECTION_FAILED',
  IMAP_AUTHENTICATION_FAILED = 'E_IMAP_AUTHENTICATION_FAILED',
  IMAP_MAILBOX_NOT_FOUND = 'E_IMAP_MAILBOX_NOT_FOUND',
  IMAP_SEARCH_FAILED = 'E_IMAP_SEARCH_FAILED',
  IMAP_FETCH_FAILED = 'E_IMAP_FETCH_FAILED',
  
  // System errors
  SYSTEM_ERROR = 'E_SYSTEM_ERROR',
  RESOURCE_EXHAUSTED = 'E_RESOURCE_EXHAUSTED',
  INTERNAL_ERROR = 'E_INTERNAL_ERROR',
  
  // Unknown errors
  UNKNOWN_ERROR = 'E_UNKNOWN_ERROR'
}

/**
 * Maps error codes to their respective categories
 */
const ERROR_CODE_TO_CATEGORY: Record<ErrorCode, ErrorCategory> = {
  // Network errors
  [ErrorCode.NETWORK_UNAVAILABLE]: ErrorCategory.NETWORK,
  [ErrorCode.CONNECTION_FAILED]: ErrorCategory.NETWORK,
  [ErrorCode.CONNECTION_TIMEOUT]: ErrorCategory.NETWORK,
  [ErrorCode.CONNECTION_CLOSED]: ErrorCategory.NETWORK,
  
  // Authentication errors
  [ErrorCode.AUTH_FAILED]: ErrorCategory.AUTHENTICATION,
  [ErrorCode.CREDENTIALS_INVALID]: ErrorCategory.AUTHENTICATION,
  [ErrorCode.TOKEN_EXPIRED]: ErrorCategory.AUTHENTICATION,
  
  // Validation errors
  [ErrorCode.VALIDATION_FAILED]: ErrorCategory.VALIDATION,
  [ErrorCode.INVALID_EMAIL]: ErrorCategory.VALIDATION,
  [ErrorCode.INVALID_ATTACHMENT]: ErrorCategory.VALIDATION,
  [ErrorCode.UNSUPPORTED_FILE_TYPE]: ErrorCategory.VALIDATION,
  [ErrorCode.FILE_TOO_LARGE]: ErrorCategory.VALIDATION,
  
  // Processing errors
  [ErrorCode.PROCESSING_FAILED]: ErrorCategory.PROCESSING,
  [ErrorCode.EXTRACTION_FAILED]: ErrorCategory.PROCESSING,
  [ErrorCode.PARSING_FAILED]: ErrorCategory.PROCESSING,
  [ErrorCode.TRANSFORMATION_FAILED]: ErrorCategory.PROCESSING,
  
  // Message queue errors
  [ErrorCode.QUEUE_CONNECTION_FAILED]: ErrorCategory.MESSAGING,
  [ErrorCode.QUEUE_PUBLISH_FAILED]: ErrorCategory.MESSAGING,
  [ErrorCode.QUEUE_CONSUME_FAILED]: ErrorCategory.MESSAGING,
  
  // Storage errors
  [ErrorCode.STORAGE_CONNECTION_FAILED]: ErrorCategory.EXTERNAL,
  [ErrorCode.STORAGE_UPLOAD_FAILED]: ErrorCategory.EXTERNAL,
  [ErrorCode.STORAGE_DOWNLOAD_FAILED]: ErrorCategory.EXTERNAL,
  
  // IMAP specific errors
  [ErrorCode.IMAP_CONNECTION_FAILED]: ErrorCategory.NETWORK,
  [ErrorCode.IMAP_AUTHENTICATION_FAILED]: ErrorCategory.AUTHENTICATION,
  [ErrorCode.IMAP_MAILBOX_NOT_FOUND]: ErrorCategory.VALIDATION,
  [ErrorCode.IMAP_SEARCH_FAILED]: ErrorCategory.PROCESSING,
  [ErrorCode.IMAP_FETCH_FAILED]: ErrorCategory.PROCESSING,
  
  // System errors
  [ErrorCode.SYSTEM_ERROR]: ErrorCategory.SYSTEM,
  [ErrorCode.RESOURCE_EXHAUSTED]: ErrorCategory.SYSTEM,
  [ErrorCode.INTERNAL_ERROR]: ErrorCategory.SYSTEM,
  
  // Unknown errors
  [ErrorCode.UNKNOWN_ERROR]: ErrorCategory.UNKNOWN
};

/**
 * Maps error codes to their default severity levels
 */
const ERROR_CODE_TO_SEVERITY: Record<ErrorCode, ErrorSeverity> = {
  // Network errors - typically HIGH as they affect core functionality
  [ErrorCode.NETWORK_UNAVAILABLE]: ErrorSeverity.HIGH,
  [ErrorCode.CONNECTION_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.CONNECTION_TIMEOUT]: ErrorSeverity.MEDIUM,
  [ErrorCode.CONNECTION_CLOSED]: ErrorSeverity.MEDIUM,
  
  // Authentication errors - typically HIGH as they prevent access
  [ErrorCode.AUTH_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.CREDENTIALS_INVALID]: ErrorSeverity.HIGH,
  [ErrorCode.TOKEN_EXPIRED]: ErrorSeverity.MEDIUM,
  
  // Validation errors - typically MEDIUM or LOW as they're often user-fixable
  [ErrorCode.VALIDATION_FAILED]: ErrorSeverity.MEDIUM,
  [ErrorCode.INVALID_EMAIL]: ErrorSeverity.MEDIUM,
  [ErrorCode.INVALID_ATTACHMENT]: ErrorSeverity.MEDIUM,
  [ErrorCode.UNSUPPORTED_FILE_TYPE]: ErrorSeverity.LOW,
  [ErrorCode.FILE_TOO_LARGE]: ErrorSeverity.LOW,
  
  // Processing errors - typically MEDIUM as they affect specific operations
  [ErrorCode.PROCESSING_FAILED]: ErrorSeverity.MEDIUM,
  [ErrorCode.EXTRACTION_FAILED]: ErrorSeverity.MEDIUM,
  [ErrorCode.PARSING_FAILED]: ErrorSeverity.MEDIUM,
  [ErrorCode.TRANSFORMATION_FAILED]: ErrorSeverity.MEDIUM,
  
  // Message queue errors - typically HIGH as they affect core functionality
  [ErrorCode.QUEUE_CONNECTION_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.QUEUE_PUBLISH_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.QUEUE_CONSUME_FAILED]: ErrorSeverity.HIGH,
  
  // Storage errors - typically HIGH as they affect core functionality
  [ErrorCode.STORAGE_CONNECTION_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.STORAGE_UPLOAD_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.STORAGE_DOWNLOAD_FAILED]: ErrorSeverity.HIGH,
  
  // IMAP specific errors - severity depends on the specific error
  [ErrorCode.IMAP_CONNECTION_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.IMAP_AUTHENTICATION_FAILED]: ErrorSeverity.HIGH,
  [ErrorCode.IMAP_MAILBOX_NOT_FOUND]: ErrorSeverity.MEDIUM,
  [ErrorCode.IMAP_SEARCH_FAILED]: ErrorSeverity.MEDIUM,
  [ErrorCode.IMAP_FETCH_FAILED]: ErrorSeverity.MEDIUM,
  
  // System errors - typically CRITICAL as they affect the entire system
  [ErrorCode.SYSTEM_ERROR]: ErrorSeverity.CRITICAL,
  [ErrorCode.RESOURCE_EXHAUSTED]: ErrorSeverity.CRITICAL,
  [ErrorCode.INTERNAL_ERROR]: ErrorSeverity.HIGH,
  
  // Unknown errors - typically HIGH as we don't know their impact
  [ErrorCode.UNKNOWN_ERROR]: ErrorSeverity.HIGH
};

/**
 * Maps error codes to their retry eligibility
 */
const ERROR_CODE_TO_RETRYABLE: Record<ErrorCode, boolean> = {
  // Network errors - typically retryable
  [ErrorCode.NETWORK_UNAVAILABLE]: true,
  [ErrorCode.CONNECTION_FAILED]: true,
  [ErrorCode.CONNECTION_TIMEOUT]: true,
  [ErrorCode.CONNECTION_CLOSED]: true,
  
  // Authentication errors - typically not retryable without intervention
  [ErrorCode.AUTH_FAILED]: false,
  [ErrorCode.CREDENTIALS_INVALID]: false,
  [ErrorCode.TOKEN_EXPIRED]: false,
  
  // Validation errors - not retryable without fixing the input
  [ErrorCode.VALIDATION_FAILED]: false,
  [ErrorCode.INVALID_EMAIL]: false,
  [ErrorCode.INVALID_ATTACHMENT]: false,
  [ErrorCode.UNSUPPORTED_FILE_TYPE]: false,
  [ErrorCode.FILE_TOO_LARGE]: false,
  
  // Processing errors - may be retryable depending on the specific error
  [ErrorCode.PROCESSING_FAILED]: false,
  [ErrorCode.EXTRACTION_FAILED]: false,
  [ErrorCode.PARSING_FAILED]: false,
  [ErrorCode.TRANSFORMATION_FAILED]: false,
  
  // Message queue errors - typically retryable
  [ErrorCode.QUEUE_CONNECTION_FAILED]: true,
  [ErrorCode.QUEUE_PUBLISH_FAILED]: true,
  [ErrorCode.QUEUE_CONSUME_FAILED]: true,
  
  // Storage errors - typically retryable
  [ErrorCode.STORAGE_CONNECTION_FAILED]: true,
  [ErrorCode.STORAGE_UPLOAD_FAILED]: true,
  [ErrorCode.STORAGE_DOWNLOAD_FAILED]: true,
  
  // IMAP specific errors - some are retryable, some are not
  [ErrorCode.IMAP_CONNECTION_FAILED]: true,
  [ErrorCode.IMAP_AUTHENTICATION_FAILED]: false,
  [ErrorCode.IMAP_MAILBOX_NOT_FOUND]: false,
  [ErrorCode.IMAP_SEARCH_FAILED]: true,
  [ErrorCode.IMAP_FETCH_FAILED]: true,
  
  // System errors - typically not retryable without intervention
  [ErrorCode.SYSTEM_ERROR]: false,
  [ErrorCode.RESOURCE_EXHAUSTED]: true, // Retryable after resources are freed
  [ErrorCode.INTERNAL_ERROR]: false,
  
  // Unknown errors - default to not retryable for safety
  [ErrorCode.UNKNOWN_ERROR]: false
};

/**
 * Creates error details object with standardized format
 * 
 * @param message - Human-readable error message
 * @param code - Error code for programmatic handling
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Structured error details object
 */
export function createErrorDetails(
  message: string,
  code?: string,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IErrorDetails {
  return {
    message,
    code,
    stack: originalError instanceof Error ? originalError.stack : undefined,
    timestamp: fDateTime(new Date(), 'YYYY-MM-DDTHH:mm:ss.SSSZ'),
    context,
    originalError
  };
}

/**
 * Creates a standardized service error object
 * 
 * @param message - Human-readable error message
 * @param code - Error code for programmatic handling
 * @param severity - Error severity level
 * @param category - Error category for classification
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @param source - Source of the error (service/component name)
 * @returns Standardized service error object
 */
export function createServiceError(
  message: string,
  code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
  severity?: ErrorSeverity,
  category?: ErrorCategory,
  originalError?: Error | unknown,
  context?: Record<string, any>,
  source: string = 'email-service'
): IServiceError {
  // Determine severity and category from code if not provided
  const errorSeverity = severity || ERROR_CODE_TO_SEVERITY[code] || ErrorSeverity.MEDIUM;
  const errorCategory = category || ERROR_CODE_TO_CATEGORY[code] || ErrorCategory.UNKNOWN;
  
  // Determine if the error is retryable
  const retryable = ERROR_CODE_TO_RETRYABLE[code] || false;
  
  return {
    id: uuidv4(),
    message,
    code,
    severity: errorSeverity,
    category: errorCategory,
    details: createErrorDetails(message, code, originalError, context),
    retryable,
    source
  };
}

/**
 * Creates a network error
 * 
 * @param message - Human-readable error message
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Network error object
 */
export function createNetworkError(
  message: string,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  return createServiceError(
    message,
    ErrorCode.NETWORK_UNAVAILABLE,
    ErrorSeverity.HIGH,
    ErrorCategory.NETWORK,
    originalError,
    context
  );
}

/**
 * Creates a connection error
 * 
 * @param message - Human-readable error message
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Connection error object
 */
export function createConnectionError(
  message: string,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  return createServiceError(
    message,
    ErrorCode.CONNECTION_FAILED,
    ErrorSeverity.HIGH,
    ErrorCategory.NETWORK,
    originalError,
    context
  );
}

/**
 * Creates an authentication error
 * 
 * @param message - Human-readable error message
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Authentication error object
 */
export function createAuthenticationError(
  message: string,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  return createServiceError(
    message,
    ErrorCode.AUTH_FAILED,
    ErrorSeverity.HIGH,
    ErrorCategory.AUTHENTICATION,
    originalError,
    context
  );
}

/**
 * Creates a validation error
 * 
 * @param message - Human-readable error message
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Validation error object
 */
export function createValidationError(
  message: string,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  return createServiceError(
    message,
    ErrorCode.VALIDATION_FAILED,
    ErrorSeverity.MEDIUM,
    ErrorCategory.VALIDATION,
    originalError,
    context
  );
}

/**
 * Creates a processing error
 * 
 * @param message - Human-readable error message
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Processing error object
 */
export function createProcessingError(
  message: string,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  return createServiceError(
    message,
    ErrorCode.PROCESSING_FAILED,
    ErrorSeverity.MEDIUM,
    ErrorCategory.PROCESSING,
    originalError,
    context
  );
}

/**
 * Creates an IMAP-specific error
 * 
 * @param message - Human-readable error message
 * @param code - Specific IMAP error code
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns IMAP error object
 */
export function createImapError(
  message: string,
  code: ErrorCode = ErrorCode.IMAP_CONNECTION_FAILED,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  // Validate that the code is an IMAP error code
  if (!code.toString().includes('IMAP')) {
    code = ErrorCode.IMAP_CONNECTION_FAILED;
  }
  
  return createServiceError(
    message,
    code,
    undefined, // Use default severity for the code
    undefined, // Use default category for the code
    originalError,
    context
  );
}

/**
 * Creates a message queue error
 * 
 * @param message - Human-readable error message
 * @param code - Specific queue error code
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Message queue error object
 */
export function createQueueError(
  message: string,
  code: ErrorCode = ErrorCode.QUEUE_CONNECTION_FAILED,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  // Validate that the code is a queue error code
  if (!code.toString().includes('QUEUE')) {
    code = ErrorCode.QUEUE_CONNECTION_FAILED;
  }
  
  return createServiceError(
    message,
    code,
    undefined, // Use default severity for the code
    undefined, // Use default category for the code
    originalError,
    context
  );
}

/**
 * Creates a storage error
 * 
 * @param message - Human-readable error message
 * @param code - Specific storage error code
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns Storage error object
 */
export function createStorageError(
  message: string,
  code: ErrorCode = ErrorCode.STORAGE_CONNECTION_FAILED,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  // Validate that the code is a storage error code
  if (!code.toString().includes('STORAGE')) {
    code = ErrorCode.STORAGE_CONNECTION_FAILED;
  }
  
  return createServiceError(
    message,
    code,
    undefined, // Use default severity for the code
    undefined, // Use default category for the code
    originalError,
    context
  );
}

/**
 * Creates a system error
 * 
 * @param message - Human-readable error message
 * @param originalError - Original error object if available
 * @param context - Additional context information
 * @returns System error object
 */
export function createSystemError(
  message: string,
  originalError?: Error | unknown,
  context?: Record<string, any>
): IServiceError {
  return createServiceError(
    message,
    ErrorCode.SYSTEM_ERROR,
    ErrorSeverity.CRITICAL,
    ErrorCategory.SYSTEM,
    originalError,
    context
  );
}

/**
 * Enriches an error with additional context information
 * 
 * @param error - The error to enrich
 * @param context - Additional context information
 * @returns Enriched error object
 */
export function enrichErrorContext(
  error: IServiceError,
  context: Record<string, any>
): IServiceError {
  return {
    ...error,
    details: {
      ...error.details,
      context: {
        ...error.details.context,
        ...context
      }
    }
  };
}

/**
 * Determines if an error is retryable based on its category and code
 * 
 * @param error - The error to check
 * @returns True if the error is retryable, false otherwise
 */
export function isErrorRetryable(error: IServiceError | Error): boolean {
  // If it's a service error, use the retryable property
  if ('retryable' in error) {
    return error.retryable;
  }
  
  // If it's a standard Error, use the isRetryableError function from retry.ts
  return isRetryableError(error);
}

/**
 * Maps a standard Error to a structured IServiceError
 * 
 * @param error - The error to map
 * @param defaultMessage - Default message if the error doesn't have one
 * @param context - Additional context information
 * @returns Mapped service error
 */
export function mapErrorToServiceError(
  error: Error | unknown,
  defaultMessage: string = 'An unexpected error occurred',
  context?: Record<string, any>
): IServiceError {
  // If it's already a service error, just return it
  if (error && typeof error === 'object' && 'id' in error && 'code' in error && 'severity' in error) {
    return error as IServiceError;
  }
  
  const errorMessage = error instanceof Error ? error.message : defaultMessage;
  
  // Check for network errors
  if (error instanceof Error) {
    if (
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('ECONNRESET') ||
      error.message.includes('ETIMEDOUT') ||
      error.message.includes('EHOSTUNREACH') ||
      error.message.includes('ENETUNREACH') ||
      error.message.includes('socket hang up') ||
      error.message.includes('network error')
    ) {
      return createNetworkError(errorMessage, error, context);
    }
    
    // Check for IMAP-specific errors
    if (
      error.message.includes('IMAP connection') ||
      error.message.includes('imap failure') ||
      error.message.includes('connection closed') ||
      error.message.includes('connection dropped')
    ) {
      return createImapError(errorMessage, ErrorCode.IMAP_CONNECTION_FAILED, error, context);
    }
    
    // Check for authentication errors
    if (
      error.message.includes('authentication failed') ||
      error.message.includes('auth failed') ||
      error.message.includes('unauthorized') ||
      error.message.includes('invalid credentials')
    ) {
      return createAuthenticationError(errorMessage, error, context);
    }
    
    // Check for RabbitMQ-specific errors
    if (
      error.message.includes('AMQP connection') ||
      error.message.includes('channel closed') ||
      error.message.includes('connection closed')
    ) {
      return createQueueError(errorMessage, ErrorCode.QUEUE_CONNECTION_FAILED, error, context);
    }
    
    // Check for S3/storage-specific errors
    if (
      error.message.includes('SlowDown') ||
      error.message.includes('RequestTimeout') ||
      error.message.includes('RequestTimeTooSkewed') ||
      error.message.includes('OperationAborted')
    ) {
      return createStorageError(errorMessage, ErrorCode.STORAGE_CONNECTION_FAILED, error, context);
    }
  }
  
  // Default to unknown error
  return createServiceError(
    errorMessage,
    ErrorCode.UNKNOWN_ERROR,
    ErrorSeverity.HIGH,
    ErrorCategory.UNKNOWN,
    error,
    context
  );
}

/**
 * Converts a service error to a log entry
 * 
 * @param error - The service error to convert
 * @param correlationId - Optional correlation ID for distributed tracing
 * @returns Log entry object
 */
export function errorToLogEntry(error: IServiceError, correlationId?: string): ILogEntry {
  return {
    timestamp: error.details.timestamp,
    level: LogLevel.ERROR,
    message: error.message,
    service: error.source,
    context: {
      errorId: error.id,
      errorCode: error.code,
      errorCategory: error.category,
      errorSeverity: error.severity,
      ...error.details.context
    },
    correlationId,
    error: error.details
  };
}

/**
 * Converts a service error to a client-friendly error response
 * 
 * @param error - The service error to convert
 * @param requestId - Optional request ID for tracking
 * @param includeDetails - Whether to include detailed error information (for development)
 * @returns Client-friendly error response
 */
export function errorToResponse(error: IServiceError, requestId?: string, includeDetails: boolean = false): IErrorResponse {
  const response: IErrorResponse = {
    status: 'error',
    message: error.message,
    code: error.code,
    timestamp: error.details.timestamp,
    requestId
  };
  
  // Include additional details in development mode
  if (includeDetails && process.env.NODE_ENV !== 'production') {
    response.details = {
      severity: error.severity,
      category: error.category,
      stack: error.details.stack
    };
  }
  
  return response;
}

/**
 * Serializes an error for logging or message publishing
 * 
 * @param error - The error to serialize
 * @returns Serialized error object
 */
export function serializeError(error: IServiceError | Error): Record<string, any> {
  if ('id' in error) {
    // It's a service error, serialize it
    return {
      id: error.id,
      message: error.message,
      code: error.code,
      severity: error.severity,
      category: error.category,
      timestamp: error.details.timestamp,
      stack: error.details.stack,
      context: error.details.context,
      source: error.source,
      retryable: error.retryable
    };
  }
  
  // It's a standard Error, convert it to a serializable object
  return {
    message: error.message,
    stack: error.stack,
    name: error.name,
    // Include any additional properties from the error object
    ...(error as any)
  };
}

/**
 * Handles an error by logging it and optionally publishing it to a monitoring system
 * 
 * @param error - The error to handle
 * @param context - Additional context information
 * @param correlationId - Optional correlation ID for distributed tracing
 * @returns The handled error
 */
export function handleError(
  error: Error | unknown,
  context?: Record<string, any>,
  correlationId?: string
): IServiceError {
  // Convert to service error if needed
  const serviceError = error instanceof Error && !('id' in error)
    ? mapErrorToServiceError(error, undefined, context)
    : (error as IServiceError);
  
  // Log the error
  const logEntry = errorToLogEntry(serviceError, correlationId);
  console.error(JSON.stringify(logEntry));
  
  // Here you would add code to publish the error to a monitoring system if needed
  // For example, sending to a centralized logging system or error tracking service
  
  return serviceError;
}

/**
 * Creates a custom error class with additional properties
 * 
 * @param name - The name of the error class
 * @param defaultMessage - Default message for the error
 * @returns Custom error class
 */
export function createCustomError(name: string, defaultMessage: string = 'An error occurred') {
  return class CustomError extends Error {
    code?: string;
    category?: ErrorCategory;
    retryable?: boolean;
    context?: Record<string, any>;
    
    constructor(message: string = defaultMessage, options: {
      code?: string;
      category?: ErrorCategory;
      retryable?: boolean;
      context?: Record<string, any>;
    } = {}) {
      super(message);
      this.name = name;
      this.code = options.code;
      this.category = options.category;
      this.retryable = options.retryable;
      this.context = options.context;
      
      // Ensure proper prototype chain for instanceof checks
      Object.setPrototypeOf(this, CustomError.prototype);
    }
  };
}

/**
 * Predefined custom error classes for common error types
 */
export const ImapConnectionError = createCustomError('ImapConnectionError', 'IMAP connection failed');
export const ImapAuthenticationError = createCustomError('ImapAuthenticationError', 'IMAP authentication failed');
export const QueueConnectionError = createCustomError('QueueConnectionError', 'Message queue connection failed');
export const StorageConnectionError = createCustomError('StorageConnectionError', 'Storage connection failed');
export const ValidationError = createCustomError('ValidationError', 'Validation failed');
export const ProcessingError = createCustomError('ProcessingError', 'Processing failed');

/**
 * Wraps a function with error handling
 * 
 * @param fn - The function to wrap
 * @param errorMapper - Optional function to map errors to service errors
 * @returns Wrapped function with error handling
 */
export function withErrorHandling<T, Args extends any[]>(
  fn: (...args: Args) => Promise<T>,
  errorMapper?: (error: Error, ...args: Args) => IServiceError
): (...args: Args) => Promise<T> {
  return async (...args: Args): Promise<T> => {
    try {
      return await fn(...args);
    } catch (error) {
      // Map the error if a mapper is provided
      const serviceError = errorMapper
        ? errorMapper(error instanceof Error ? error : new Error(String(error)), ...args)
        : mapErrorToServiceError(error);
      
      // Handle the error (log it, etc.)
      handleError(serviceError);
      
      // Re-throw the error
      throw serviceError;
    }
  };
}