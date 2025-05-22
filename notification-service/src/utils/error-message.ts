/**
 * Error Message Utility
 * 
 * This utility provides a consistent way to extract error messages from different error types.
 * It handles various error formats and ensures a string message is always returned.
 */

/**
 * Extract a readable error message from any error type
 * 
 * @param error The error object or value
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