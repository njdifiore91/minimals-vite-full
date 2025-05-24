/**
 * Error handling middleware for the Notification Service API
 * 
 * This middleware catches all errors thrown during request processing,
 * normalizes them into a consistent format, and returns appropriate HTTP responses.
 * It ensures that all errors are properly logged and that clients receive useful
 * error information without exposing sensitive details.
 */

import { Request, Response, NextFunction } from 'express';
import { getErrorMessage } from '../utils/error-message';
import { logger } from '../config/logger';

/**
 * Custom error classes for application-specific errors
 */

// Base error class for all application errors
export class AppError extends Error {
  public readonly statusCode: number;
  public readonly isOperational: boolean;
  public readonly errorCode: string;

  constructor(message: string, statusCode = 500, errorCode = 'INTERNAL_ERROR', isOperational = true) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    this.errorCode = errorCode;
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

// 400 Bad Request - Invalid input data
export class ValidationError extends AppError {
  public readonly validationErrors: Record<string, string>;

  constructor(message: string, validationErrors: Record<string, string> = {}) {
    super(message, 400, 'VALIDATION_ERROR');
    this.validationErrors = validationErrors;
  }
}

// 401 Unauthorized - Authentication failure
export class AuthenticationError extends AppError {
  constructor(message = 'Authentication required') {
    super(message, 401, 'AUTHENTICATION_ERROR');
  }
}

// 403 Forbidden - Authorization failure
export class AuthorizationError extends AppError {
  constructor(message = 'Insufficient permissions') {
    super(message, 403, 'AUTHORIZATION_ERROR');
  }
}

// 404 Not Found - Resource not found
export class NotFoundError extends AppError {
  constructor(message = 'Resource not found') {
    super(message, 404, 'NOT_FOUND_ERROR');
  }
}

// 409 Conflict - Resource conflict
export class ConflictError extends AppError {
  constructor(message = 'Resource conflict') {
    super(message, 409, 'CONFLICT_ERROR');
  }
}

// 429 Too Many Requests - Rate limit exceeded
export class RateLimitError extends AppError {
  constructor(message = 'Rate limit exceeded') {
    super(message, 429, 'RATE_LIMIT_ERROR');
  }
}

// 503 Service Unavailable - External service unavailable
export class ServiceUnavailableError extends AppError {
  constructor(message = 'Service temporarily unavailable') {
    super(message, 503, 'SERVICE_UNAVAILABLE_ERROR');
  }
}

/**
 * Standardized error response format
 */
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, string> | string[];
    requestId?: string;
  };
}

/**
 * Normalizes different error types into a consistent AppError format
 */
const normalizeError = (error: unknown): AppError => {
  // Already an AppError instance
  if (error instanceof AppError) {
    return error;
  }

  // Express validation errors (express-validator)
  if (Array.isArray(error) && error.length > 0 && error[0].param && error[0].msg) {
    const validationErrors: Record<string, string> = {};
    error.forEach((err) => {
      validationErrors[err.param] = err.msg;
    });
    return new ValidationError('Validation failed', validationErrors);
  }

  // Standard Error object
  if (error instanceof Error) {
    // Handle specific error types based on name or message
    if (error.name === 'UnauthorizedError' || error.message.includes('jwt')) {
      return new AuthenticationError(error.message);
    }
    
    if (error.name === 'ForbiddenError') {
      return new AuthorizationError(error.message);
    }
    
    if (error.name === 'NotFoundError') {
      return new NotFoundError(error.message);
    }

    // Default to internal server error
    return new AppError(error.message, 500, 'INTERNAL_ERROR', false);
  }

  // Handle string errors
  if (typeof error === 'string') {
    return new AppError(error);
  }

  // Handle unknown error types
  return new AppError('An unknown error occurred');
};

/**
 * Global error handling middleware
 */
export const errorMiddleware = (err: unknown, req: Request, res: Response, next: NextFunction): void => {
  // Normalize the error to ensure consistent format
  const normalizedError = normalizeError(err);
  
  // Extract correlation ID for request tracking
  const correlationId = req.headers['x-correlation-id'] as string || 'unknown';
  
  // Log the error with context information
  const logContext = {
    correlationId,
    path: req.path,
    method: req.method,
    statusCode: normalizedError.statusCode,
    errorCode: normalizedError.errorCode,
    isOperational: normalizedError.isOperational,
  };

  // Log operational errors as warnings, programming errors as errors
  if (normalizedError.isOperational) {
    logger.warn(`Operational error: ${normalizedError.message}`, logContext);
  } else {
    logger.error(`Programming error: ${normalizedError.message}`, {
      ...logContext,
      stack: normalizedError.stack,
    });
  }

  // Prepare the error response
  const errorResponse: ErrorResponse = {
    success: false,
    error: {
      code: normalizedError.errorCode,
      message: normalizedError.message,
      requestId: correlationId,
    },
  };

  // Add validation errors if present
  if (normalizedError instanceof ValidationError && Object.keys(normalizedError.validationErrors).length > 0) {
    errorResponse.error.details = normalizedError.validationErrors;
  }

  // Send the response
  res.status(normalizedError.statusCode).json(errorResponse);
};

/**
 * Not found middleware - catches 404 errors for undefined routes
 */
export const notFoundMiddleware = (req: Request, res: Response, next: NextFunction): void => {
  next(new NotFoundError(`Route not found: ${req.method} ${req.path}`));
};

/**
 * Utility function to create an async middleware that catches errors
 */
export const asyncHandler = (fn: (req: Request, res: Response, next: NextFunction) => Promise<any>) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * Error message utility function
 * Reuses the getErrorMessage function from the source file
 */
export const getDetailedErrorMessage = (error: unknown): string => {
  return getErrorMessage(error);
};