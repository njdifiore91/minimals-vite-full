/**
 * Error utility functions for the Notification Service
 * 
 * This file provides utility functions for handling and formatting errors
 * consistently throughout the Notification Service.
 */

/**
 * Extract a meaningful error message from any error type
 * 
 * @param error - The error object or value
 * @returns A string representation of the error message
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message || error.name || 'An error occurred';
  }

  if (typeof error === 'string') {
    return error;
  }

  if (typeof error === 'object' && error !== null) {
    const errorMessage = (error as { message?: string }).message;
    if (typeof errorMessage === 'string') {
      return errorMessage;
    }
  }

  return `Unknown error: ${error}`;
}

/**
 * Create a standardized error object for API responses
 * 
 * @param statusCode - HTTP status code
 * @param message - Error message
 * @param errorCode - Application-specific error code
 * @param correlationId - Request correlation ID for tracing
 * @param details - Additional error details
 * @returns Standardized error object
 */
export function createErrorResponse(
  statusCode: number,
  message: string,
  errorCode: string,
  correlationId: string,
  details?: Record<string, unknown>
): {
  statusCode: number;
  message: string;
  errorCode: string;
  correlationId: string;
  timestamp: string;
  details?: Record<string, unknown>;
} {
  return {
    statusCode,
    message,
    errorCode,
    correlationId,
    timestamp: new Date().toISOString(),
    ...(details && { details }),
  };
}

/**
 * Determine if an error is retryable based on its type or status code
 * 
 * @param error - The error object
 * @returns Boolean indicating if the error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  // Network errors are generally retryable
  if (
    error instanceof Error &&
    (
      error.message.includes('ECONNRESET') ||
      error.message.includes('ETIMEDOUT') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('EHOSTUNREACH') ||
      error.message.includes('EPIPE') ||
      error.message.includes('ENOTFOUND')
    )
  ) {
    return true;
  }

  // Check for HTTP status codes that are retryable
  if (
    error &&
    typeof error === 'object' &&
    'statusCode' in error
  ) {
    const statusCode = (error as { statusCode: number }).statusCode;
    // 429 (Too Many Requests) and 5xx errors are retryable
    return statusCode === 429 || (statusCode >= 500 && statusCode < 600);
  }

  return false;
}

/**
 * Format an error stack trace for logging
 * 
 * @param error - The error object
 * @returns Formatted stack trace or error message
 */
export function formatErrorStack(error: unknown): string {
  if (error instanceof Error && error.stack) {
    return error.stack;
  }
  
  return getErrorMessage(error);
}

/**
 * Safely parse JSON with error handling
 * 
 * @param jsonString - JSON string to parse
 * @param defaultValue - Default value to return if parsing fails
 * @returns Parsed object or default value
 */
export function safeJsonParse<T>(jsonString: string, defaultValue: T): T {
  try {
    return JSON.parse(jsonString) as T;
  } catch (error) {
    return defaultValue;
  }
}