/**
 * Common TypeScript type definitions for the Email Service
 * 
 * This file contains essential shared type aliases used throughout the Email Service microservice.
 * It provides fundamental data structures for consistent date representation, standardized logging,
 * and uniform error handling.
 */

// ----------------------------------------------------------------------

/**
 * Represents a date value that can be a string, number, or null
 * Used for consistent date representation across the service
 */
export type IDateValue = string | number | null;

/**
 * Standard log levels for the Email Service
 * Follows the logging requirements specified in section 0.2.5
 */
export type ILogLevel = 'ERROR' | 'WARN' | 'INFO' | 'DEBUG';

/**
 * Structured error details for comprehensive error reporting
 */
export interface IErrorDetails {
  /** Error code for categorizing errors */
  code: string;
  /** Human-readable error message */
  message: string;
  /** Optional stack trace for debugging */
  stack?: string;
  /** Optional additional context about the error */
  context?: Record<string, unknown>;
  /** Timestamp when the error occurred */
  timestamp: number;
}

/**
 * Generic result type for uniform error handling
 * Used to represent the result of any operation in a consistent way
 */
export interface IResult<T = unknown> {
  /** Whether the operation was successful */
  success: boolean;
  /** The data returned by the operation (if successful) */
  data?: T;
  /** Error details (if the operation failed) */
  error?: IErrorDetails;
}

/**
 * Represents an asynchronous result
 * A Promise wrapper around the IResult type
 */
export type IAsyncResult<T = unknown> = Promise<IResult<T>>;

/**
 * Standard service response structure
 * Used for consistent API responses
 */
export interface IServiceResponse<T = unknown> {
  /** Status code of the response */
  statusCode: number;
  /** Whether the operation was successful */
  success: boolean;
  /** The data returned by the operation */
  data?: T;
  /** Error message if the operation failed */
  message?: string;
  /** Timestamp of the response */
  timestamp: number;
}

/**
 * Email processing status
 * Represents the various states an email can be in during processing
 */
export type IEmailProcessingStatus = 
  | 'RECEIVED'
  | 'PROCESSING'
  | 'PROCESSED'
  | 'FAILED'
  | 'INVALID';

/**
 * Retry configuration for failed operations
 * Used to configure retry behavior for operations that might fail temporarily
 */
export interface IRetryConfig {
  /** Maximum number of retry attempts */
  maxAttempts: number;
  /** Base delay between retry attempts in milliseconds */
  baseDelayMs: number;
  /** Whether to use exponential backoff for retries */
  useExponentialBackoff: boolean;
  /** Maximum delay between retry attempts in milliseconds */
  maxDelayMs: number;
}