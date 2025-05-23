/**
 * Error message utility functions
 * 
 * This file provides utility functions for extracting and formatting error messages
 * from different error types. It ensures consistent error message handling throughout
 * the Notification Service.
 */

/**
 * Extracts a human-readable error message from any error type
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
 * Formats an error message for API responses
 * 
 * @param error - The error object or value
 * @param includeStack - Whether to include the stack trace (default: false)
 * @returns A formatted error message object
 */
export function formatErrorForResponse(error: unknown, includeStack = false): Record<string, any> {
  const message = getErrorMessage(error);
  const formattedError: Record<string, any> = { message };
  
  // Include error code if available
  if (error instanceof Error && (error as any).code) {
    formattedError.code = (error as any).code;
  } else {
    formattedError.code = 'INTERNAL_ERROR';
  }
  
  // Include stack trace in development environment if requested
  if (includeStack && process.env.NODE_ENV !== 'production' && error instanceof Error) {
    formattedError.stack = error.stack;
  }
  
  return formattedError;
}

/**
 * Formats an error message for logging
 * 
 * @param error - The error object or value
 * @param context - Additional context information
 * @returns A formatted error object for logging
 */
export function formatErrorForLogging(error: unknown, context: Record<string, any> = {}): Record<string, any> {
  const message = getErrorMessage(error);
  const formattedError: Record<string, any> = { 
    message,
    ...context
  };
  
  // Include error code if available
  if (error instanceof Error && (error as any).code) {
    formattedError.code = (error as any).code;
  }
  
  // Include stack trace for Error objects
  if (error instanceof Error) {
    formattedError.stack = error.stack;
    formattedError.name = error.name;
  }
  
  return formattedError;
}