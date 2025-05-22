/**
 * Error Message Utility
 * 
 * Provides a consistent way to extract error messages from different error types.
 * This utility ensures that all error messages throughout the application have
 * a consistent format, regardless of the error source.
 */

/**
 * Extracts a human-readable error message from any error object
 * 
 * @param error The error object (can be any type)
 * @returns A string error message
 */
export function getErrorMessage(error: unknown): string {
  // Handle standard Error objects
  if (error instanceof Error) {
    return error.message || error.name || 'An error occurred';
  }

  // Handle string errors
  if (typeof error === 'string') {
    return error;
  }

  // Handle objects with message property
  if (typeof error === 'object' && error !== null) {
    const errorMessage = (error as { message?: string }).message;
    if (typeof errorMessage === 'string') {
      return errorMessage;
    }
    
    // Handle axios error responses
    const response = (error as { response?: { data?: any } }).response;
    if (response && response.data) {
      if (typeof response.data === 'string') {
        return response.data;
      }
      if (typeof response.data === 'object' && response.data.message) {
        return response.data.message;
      }
    }
  }

  // Default fallback for unknown error types
  return `Unknown error: ${JSON.stringify(error)}`;
}

/**
 * Creates a standardized error object with consistent properties
 * 
 * @param message The error message
 * @param code Optional error code
 * @param details Optional additional error details
 * @returns A standardized error object
 */
export function createErrorObject(message: string, code?: string, details?: any) {
  return {
    status: 'error',
    message,
    code: code || 'UNKNOWN_ERROR',
    details: details || null,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Formats validation errors into a consistent structure
 * 
 * @param errors Array of validation errors
 * @returns A standardized validation error object
 */
export function formatValidationErrors(errors: Array<{ path: string; message: string }>) {
  return createErrorObject(
    'Validation failed',
    'VALIDATION_ERROR',
    { errors }
  );
}

/**
 * Creates a standardized HTTP error with status code
 * 
 * @param message The error message
 * @param statusCode HTTP status code
 * @param code Optional error code
 * @param details Optional additional error details
 * @returns A standardized HTTP error object
 */
export function createHttpError(message: string, statusCode: number, code?: string, details?: any) {
  return {
    ...createErrorObject(message, code, details),
    statusCode,
  };
}