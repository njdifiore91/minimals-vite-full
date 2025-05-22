/**
 * Error Handling Middleware
 * 
 * This middleware catches all errors thrown during request processing,
 * normalizes them into a consistent format, and returns appropriate HTTP responses.
 * It ensures that all errors are properly logged and that clients receive useful
 * error information without exposing sensitive details.
 * 
 * Key features:
 * - Standardized error responses following the IErrorResponse interface
 * - Custom error classes for different error types
 * - Error normalization from various sources (Express, JWT, Axios, etc.)
 * - Configurable logging with context information
 * - Environment-aware error detail sanitization
 * - Support for correlation IDs for distributed tracing
 * 
 * Usage:
 * ```typescript
 * import { createErrorMiddleware } from './middleware/error-middleware';
 * 
 * // Use with default options
 * app.use(createErrorMiddleware());
 * 
 * // Or with custom options
 * app.use(createErrorMiddleware({
 *   includeStack: true,
 *   sensitiveFields: ['password', 'token', 'apiKey']
 * }));
 * ```
 */

import { Request, Response, NextFunction } from 'express';
import { ValidationError } from 'express-validator';
import { JsonWebTokenError, TokenExpiredError } from 'jsonwebtoken';
import { IErrorResponse, ILogContext } from '../types/common';

// Import logger (assuming it's defined elsewhere in the project)
// This allows for flexibility in logger implementation
import logger from '../utils/logger';

/**
 * Base application error class that all custom errors should extend
 */
export class AppError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly details?: any;

  constructor(message: string, status: number = 500, code: string = 'INTERNAL_SERVER_ERROR', details?: any) {
    super(message);
    this.name = this.constructor.name;
    this.status = status;
    this.code = code;
    this.details = details;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Error thrown when a resource is not found
 */
export class NotFoundError extends AppError {
  constructor(message: string = 'Resource not found', details?: any) {
    super(message, 404, 'RESOURCE_NOT_FOUND', details);
  }
}

/**
 * Error thrown when validation fails
 */
export class ValidationFailedError extends AppError {
  constructor(message: string = 'Validation failed', details?: any) {
    super(message, 400, 'VALIDATION_ERROR', details);
  }
}

/**
 * Error thrown when authentication fails
 */
export class AuthenticationError extends AppError {
  constructor(message: string = 'Authentication failed', details?: any) {
    super(message, 401, 'AUTHENTICATION_ERROR', details);
  }
}

/**
 * Error thrown when authorization fails
 */
export class AuthorizationError extends AppError {
  constructor(message: string = 'Not authorized', details?: any) {
    super(message, 403, 'AUTHORIZATION_ERROR', details);
  }
}

/**
 * Error thrown when rate limit is exceeded
 */
export class RateLimitError extends AppError {
  constructor(message: string = 'Rate limit exceeded', details?: any) {
    super(message, 429, 'RATE_LIMIT_EXCEEDED', details);
  }
}

/**
 * Error thrown when a webhook delivery fails
 */
export class WebhookError extends AppError {
  constructor(message: string = 'Webhook delivery failed', details?: any) {
    super(message, 500, 'WEBHOOK_ERROR', details);
  }
}

/**
 * Error thrown when webhook signature verification fails
 */
export class WebhookSignatureError extends AppError {
  constructor(message: string = 'Invalid webhook signature', details?: any) {
    super(message, 401, 'INVALID_WEBHOOK_SIGNATURE', details);
  }
}

/**
 * Error thrown when webhook payload validation fails
 */
export class WebhookPayloadError extends AppError {
  constructor(message: string = 'Invalid webhook payload', details?: any) {
    super(message, 400, 'INVALID_WEBHOOK_PAYLOAD', details);
  }
}

/**
 * Error thrown when a service dependency is unavailable
 */
export class ServiceUnavailableError extends AppError {
  constructor(message: string = 'Service unavailable', details?: any) {
    super(message, 503, 'SERVICE_UNAVAILABLE', details);
  }
}

/**
 * Gets a standardized error message from any error type
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
 * Normalizes any error into a standardized error response
 */
export function normalizeError(error: unknown, req: Request): IErrorResponse {
  const requestId = req.headers['x-request-id'] as string || req.headers['x-correlation-id'] as string || 'unknown';
  const timestamp = new Date().toISOString();

  // Handle AppError instances
  if (error instanceof AppError) {
    return {
      status: error.status,
      code: error.code,
      message: error.message,
      details: error.details,
      requestId,
      timestamp
    };
  }

  // Handle JWT errors
  if (error instanceof JsonWebTokenError) {
    return {
      status: 401,
      code: 'INVALID_TOKEN',
      message: 'Invalid authentication token',
      details: { error: error.message },
      requestId,
      timestamp
    };
  }

  if (error instanceof TokenExpiredError) {
    return {
      status: 401,
      code: 'TOKEN_EXPIRED',
      message: 'Authentication token expired',
      details: { expiredAt: error.expiredAt },
      requestId,
      timestamp
    };
  }

  // Handle express-validator validation errors
  if (Array.isArray(error) && error.length > 0 && error[0] instanceof ValidationError) {
    return {
      status: 400,
      code: 'VALIDATION_ERROR',
      message: 'Validation failed',
      details: error.map(err => ({
        param: err.param,
        value: err.value,
        location: err.location,
        msg: err.msg
      })),
      requestId,
      timestamp
    };
  }
  
  // Handle Axios errors
  if (error && typeof error === 'object' && 'isAxiosError' in error && (error as any).isAxiosError) {
    const axiosError = error as any;
    const status = axiosError.response?.status || 500;
    const responseData = axiosError.response?.data;
    
    return {
      status,
      code: axiosError.code || 'HTTP_ERROR',
      message: axiosError.message || 'HTTP request failed',
      details: {
        url: axiosError.config?.url,
        method: axiosError.config?.method,
        status: axiosError.response?.status,
        statusText: axiosError.response?.statusText,
        data: responseData
      },
      requestId,
      timestamp
    };
  }
  
  // Handle RabbitMQ errors
  if (error && typeof error === 'object' && 'code' in error && 
      ['ECONNREFUSED', 'ETIMEDOUT', 'ENOTFOUND'].includes((error as any).code)) {
    return {
      status: 503,
      code: 'SERVICE_UNAVAILABLE',
      message: 'Message queue connection failed',
      details: {
        code: (error as any).code,
        errno: (error as any).errno,
        syscall: (error as any).syscall,
        address: (error as any).address,
        port: (error as any).port
      },
      requestId,
      timestamp
    };
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    // Check for common error patterns in the message
    const message = error.message.toLowerCase();
    
    if (message.includes('timeout') || message.includes('timed out')) {
      return {
        status: 504,
        code: 'TIMEOUT_ERROR',
        message: 'Request timed out',
        details: { originalMessage: error.message },
        requestId,
        timestamp
      };
    }
    
    if (message.includes('rate limit') || message.includes('too many requests')) {
      return {
        status: 429,
        code: 'RATE_LIMIT_EXCEEDED',
        message: 'Rate limit exceeded',
        details: { originalMessage: error.message },
        requestId,
        timestamp
      };
    }
    
    return {
      status: 500,
      code: 'INTERNAL_SERVER_ERROR',
      message: error.message || 'An unexpected error occurred',
      requestId,
      timestamp
    };
  }

  // Handle unknown errors
  return {
    status: 500,
    code: 'INTERNAL_SERVER_ERROR',
    message: getErrorMessage(error),
    requestId,
    timestamp
  };
}

/**
 * Creates a log context object from the request
 */
function createLogContext(req: Request, error: unknown): ILogContext {
  return {
    correlationId: req.headers['x-correlation-id'] as string,
    requestId: req.headers['x-request-id'] as string,
    method: req.method,
    path: req.path,
    ip: req.ip,
    userAgent: req.headers['user-agent'] as string,
    error: error instanceof Error ? {
      name: error.name,
      message: error.message,
      stack: error.stack
    } : error
  };
}

/**
 * Error middleware configuration options
 */
export interface ErrorMiddlewareOptions {
  /** Whether to include stack traces in error responses (default: false in production) */
  includeStack?: boolean;
  /** Whether to log errors (default: true) */
  logErrors?: boolean;
  /** Custom fields to redact from error logs */
  sensitiveFields?: string[];
  /** Whether to sanitize error details in production (default: true) */
  sanitizeDetails?: boolean;
}

/**
 * Creates a configured error handling middleware
 */
export function createErrorMiddleware(options: ErrorMiddlewareOptions = {}) {
  return function errorMiddleware(err: unknown, req: Request, res: Response, next: NextFunction): void {
  // Normalize the error
  const normalizedError = normalizeError(err, req);
  
  // Create log context
  const logContext = createLogContext(req, err);
  
  // Add request body to log context for debugging (excluding sensitive data)
  if (req.body) {
    const sanitizedBody = { ...req.body };
    
    // Remove sensitive fields
    const sensitiveFields = options.sensitiveFields || [
      'password', 'token', 'secret', 'apiKey', 'authorization',
      'creditCard', 'ssn', 'ein', 'taxId', 'signature'
    ];
    
    sensitiveFields.forEach(field => {
      if (field in sanitizedBody) {
        sanitizedBody[field] = '[REDACTED]';
      }
    });
    
    logContext.body = sanitizedBody;
  }
  
  // Add request query parameters to log context
  if (Object.keys(req.query).length > 0) {
    logContext.query = req.query;
  }
  
  // Log the error with appropriate level based on status code
  if (options.logErrors !== false) {
    if (normalizedError.status >= 500) {
      logger.error(`Server error (${normalizedError.code}): ${normalizedError.message}`, logContext);
    } else if (normalizedError.status >= 400) {
      logger.warn(`Client error (${normalizedError.code}): ${normalizedError.message}`, logContext);
    } else {
      logger.info(`Other error (${normalizedError.code}): ${normalizedError.message}`, logContext);
    }
  }
  
  // Add debugging information based on environment
  const environment = process.env.NODE_ENV || 'development';
  const includeStack = options.includeStack ?? (environment === 'development' || environment === 'test');
  
  if (includeStack) {
    // Include detailed error information in development and test environments
    if (err instanceof Error) {
      normalizedError.details = {
        ...normalizedError.details,
        stack: err.stack,
        name: err.name
      };
    }
  } else if (options.sanitizeDetails !== false && environment === 'production') {
    // In production, ensure we don't leak sensitive information
    // Keep only safe details if they exist
    if (normalizedError.details) {
      const safeDetails: Record<string, any> = {};
      
      // Only copy safe fields to the response
      const safeFields = ['param', 'field', 'value', 'reason', 'code'];
      for (const field of safeFields) {
        if (field in normalizedError.details) {
          safeDetails[field] = normalizedError.details[field];
        }
      }
      
      normalizedError.details = Object.keys(safeDetails).length > 0 ? safeDetails : undefined;
    }
  }
  
  // Send the response
  res.status(normalizedError.status).json(normalizedError);
  };
}

/**
 * Default error handling middleware with standard configuration
 */
export default createErrorMiddleware();

/**
 * Middleware to handle 404 errors for routes that don't exist
 */
export function notFoundMiddleware(req: Request, res: Response, next: NextFunction): void {
  next(new NotFoundError(`Route not found: ${req.method} ${req.path}`));
}

/**
 * Middleware to handle uncaught errors in async route handlers
 */
export function asyncErrorHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<any>) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

/**
 * Creates a standardized error response object
 */
export function createErrorResponse(status: number, code: string, message: string, details?: any): IErrorResponse {
  return {
    status,
    code,
    message,
    details,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Utility to determine if an error is a specific type
 */
export function isErrorType<T extends Error>(error: unknown, errorType: new (...args: any[]) => T): error is T {
  return error instanceof Error && error.constructor === errorType;
}

/**
 * Utility to determine if an error is a specific HTTP status code
 */
export function isHttpError(error: unknown, statusCode: number): boolean {
  return error instanceof AppError && error.status === statusCode;
}