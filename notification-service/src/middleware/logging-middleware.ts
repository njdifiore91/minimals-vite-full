/**
 * Logging Middleware for Notification Service
 * 
 * This middleware logs all incoming requests and outgoing responses, including timing information,
 * request details, and response status. It supports different log levels based on the environment
 * and masks sensitive data to prevent security issues.
 * 
 * Features:
 * - Request/response logging with performance timing
 * - Sensitive data masking for security
 * - Configurable log levels based on environment
 * - Request context enrichment with metadata
 * - Correlation ID tracking for distributed tracing
 */

import { Request, Response, NextFunction } from 'express';
import { logger, createContextLogger } from '../config/logger';
import { getErrorMessage } from '../utils/error-utils';
import { ILogContext } from '../types/common';
import { LogLevel } from '../types/config';
import { v4 as uuidv4 } from 'uuid';

/**
 * Interface for request with added properties
 */
interface ExtendedRequest extends Request {
  id?: string;
  startTime?: [number, number]; // hrtime tuple
  logger?: any;
}

/**
 * Fields that should be masked in logs for security
 */
const SENSITIVE_FIELDS = [
  'password',
  'token',
  'secret',
  'apiKey',
  'api_key',
  'authorization',
  'accessToken',
  'access_token',
  'refreshToken',
  'refresh_token',
  'creditCard',
  'credit_card',
  'cardNumber',
  'card_number',
  'cvv',
  'cvc',
  'ssn',
  'socialSecurity',
  'social_security',
  'key',
  'private',
  'secret',
];

/**
 * Headers that should be masked in logs for security
 */
const SENSITIVE_HEADERS = [
  'authorization',
  'x-api-key',
  'cookie',
  'set-cookie',
  'x-auth-token',
  'x-access-token',
];

/**
 * Mask sensitive data in an object
 * 
 * @param obj - Object to mask sensitive data in
 * @param sensitiveFields - Array of field names to mask
 * @param maskChar - Character to use for masking
 * @returns Object with sensitive data masked
 */
const maskSensitiveData = (
  obj: Record<string, any>,
  sensitiveFields: string[] = SENSITIVE_FIELDS,
  maskChar: string = '*'
): Record<string, any> => {
  if (!obj || typeof obj !== 'object') {
    return obj;
  }

  // Create a deep copy to avoid modifying the original object
  const maskedObj = Array.isArray(obj) ? [...obj] : { ...obj };

  // Recursively mask sensitive data
  Object.keys(maskedObj).forEach((key) => {
    // Check if the current key contains any sensitive field name
    const isSensitive = sensitiveFields.some(field => 
      key.toLowerCase().includes(field.toLowerCase())
    );

    if (isSensitive) {
      // Mask the value if it's a string
      if (typeof maskedObj[key] === 'string') {
        maskedObj[key] = `${maskChar.repeat(4)}${maskedObj[key].slice(-4)}`;
      } else if (maskedObj[key] !== null && maskedObj[key] !== undefined) {
        // For non-string values, replace with a simple masked indicator
        maskedObj[key] = '[REDACTED]';
      }
    } else if (maskedObj[key] !== null && typeof maskedObj[key] === 'object') {
      // Recursively mask nested objects
      maskedObj[key] = maskSensitiveData(maskedObj[key], sensitiveFields, maskChar);
    }
  });

  return maskedObj;
};

/**
 * Mask sensitive headers in a request or response
 * 
 * @param headers - Headers object to mask
 * @param sensitiveHeaders - Array of header names to mask
 * @returns Headers object with sensitive data masked
 */
const maskSensitiveHeaders = (
  headers: Record<string, any>,
  sensitiveHeaders: string[] = SENSITIVE_HEADERS
): Record<string, any> => {
  if (!headers || typeof headers !== 'object') {
    return headers;
  }

  const maskedHeaders = { ...headers };

  Object.keys(maskedHeaders).forEach((key) => {
    if (sensitiveHeaders.some(header => key.toLowerCase() === header.toLowerCase())) {
      maskedHeaders[key] = '[REDACTED]';
    }
  });

  return maskedHeaders;
};

/**
 * Safely stringify an object for logging
 * 
 * @param obj - Object to stringify
 * @param maxLength - Maximum length of the resulting string
 * @returns Stringified object or error message
 */
const safeStringify = (obj: any, maxLength: number = 10000): string => {
  try {
    if (!obj) return String(obj);
    
    const str = JSON.stringify(obj);
    if (str.length > maxLength) {
      return `${str.substring(0, maxLength)}... [truncated]`;
    }
    return str;
  } catch (error) {
    return `[Unstringifiable Object: ${getErrorMessage(error)}]`;
  }
};

/**
 * Get a safe copy of request body for logging
 * 
 * @param req - Express request object
 * @returns Safe copy of request body with sensitive data masked
 */
const getSafeRequestBody = (req: Request): Record<string, any> => {
  try {
    // Skip logging for multipart/form-data (file uploads)
    const contentType = req.headers['content-type'] || '';
    if (contentType.includes('multipart/form-data')) {
      return { _note: '[multipart form data - body not logged]' };
    }

    // Mask sensitive data in the request body
    return maskSensitiveData(req.body);
  } catch (error) {
    return { _error: `Error processing request body: ${getErrorMessage(error)}` };
  }
};

/**
 * Get a safe copy of request query parameters for logging
 * 
 * @param req - Express request object
 * @returns Safe copy of query parameters with sensitive data masked
 */
const getSafeRequestQuery = (req: Request): Record<string, any> => {
  try {
    // Mask sensitive data in query parameters
    return maskSensitiveData(req.query);
  } catch (error) {
    return { _error: `Error processing request query: ${getErrorMessage(error)}` };
  }
};

/**
 * Get a safe copy of request headers for logging
 * 
 * @param req - Express request object
 * @returns Safe copy of headers with sensitive data masked
 */
const getSafeRequestHeaders = (req: Request): Record<string, any> => {
  try {
    // Mask sensitive headers
    return maskSensitiveHeaders(req.headers);
  } catch (error) {
    return { _error: `Error processing request headers: ${getErrorMessage(error)}` };
  }
};

/**
 * Get a safe copy of response body for logging
 * 
 * @param res - Express response object
 * @returns Safe copy of response body with sensitive data masked
 */
const getSafeResponseBody = (res: Response): Record<string, any> | string => {
  try {
    // Access the response body if it was captured
    const body = (res as any)._body;
    
    if (!body) {
      return '[No response body captured]';
    }

    // If body is a string, try to parse it as JSON
    if (typeof body === 'string') {
      try {
        const jsonBody = JSON.parse(body);
        return maskSensitiveData(jsonBody);
      } catch {
        // If not valid JSON, return truncated string
        return body.length > 1000 ? `${body.substring(0, 1000)}... [truncated]` : body;
      }
    }

    // If body is an object, mask sensitive data
    return maskSensitiveData(body);
  } catch (error) {
    return { _error: `Error processing response body: ${getErrorMessage(error)}` };
  }
};

/**
 * Capture the original response methods to intercept and log responses
 * 
 * @param res - Express response object
 */
const captureResponseBody = (res: Response): void => {
  const originalSend = res.send;
  const originalJson = res.json;
  const originalEnd = res.end;

  // Capture the response body when res.send() is called
  res.send = function (body?: any): Response {
    (res as any)._body = body;
    return originalSend.apply(res, [body]);
  };

  // Capture the response body when res.json() is called
  res.json = function (body?: any): Response {
    (res as any)._body = body;
    return originalJson.apply(res, [body]);
  };

  // Ensure we capture when res.end() is called directly
  res.end = function (chunk?: any): Response {
    if (chunk && !(res as any)._body) {
      (res as any)._body = chunk;
    }
    return originalEnd.apply(res, [chunk]);
  };
};

/**
 * Calculate the duration of a request in milliseconds
 * 
 * @param startTime - High-resolution time tuple from process.hrtime()
 * @returns Duration in milliseconds
 */
const calculateDuration = (startTime: [number, number]): number => {
  const [seconds, nanoseconds] = process.hrtime(startTime);
  return seconds * 1000 + nanoseconds / 1000000;
};

/**
 * Get the appropriate log level based on HTTP status code
 * 
 * @param statusCode - HTTP status code
 * @returns Log level (error, warn, info)
 */
const getLogLevelForStatus = (statusCode: number): LogLevel => {
  if (statusCode >= 500) {
    return LogLevel.ERROR;
  } else if (statusCode >= 400) {
    return LogLevel.WARN;
  }
  return LogLevel.INFO;
};

/**
 * Create a context logger with correlation ID and request metadata
 * 
 * @param req - Express request object
 * @returns Context logger instance
 */
const createRequestLogger = (req: ExtendedRequest): any => {
  // Generate or use existing correlation ID
  const correlationId = req.id || 
                        req.headers['x-correlation-id'] as string || 
                        req.headers['x-request-id'] as string || 
                        uuidv4();
  
  // Store the correlation ID on the request object
  req.id = correlationId;
  
  // Create a context object for the logger
  const context: ILogContext = {
    correlationId,
    serviceName: 'notification-service',
    timestamp: new Date().toISOString(),
    metadata: {
      method: req.method,
      path: req.path,
      ip: req.ip,
      userAgent: req.headers['user-agent'],
    },
  };

  // Add user ID if available
  if ((req as any).user && (req as any).user.id) {
    context.userId = (req as any).user.id;
  }

  return createContextLogger(context);
};

/**
 * Logging middleware for Express
 * 
 * This middleware logs all incoming requests and outgoing responses,
 * including timing information, request details, and response status.
 * 
 * @returns Express middleware function
 */
export const loggingMiddleware = () => {
  return (req: ExtendedRequest, res: Response, next: NextFunction): void => {
    // Skip logging for health check endpoints to reduce noise
    if (req.path === '/health' || req.path === '/healthz') {
      return next();
    }

    // Record the start time for performance measurement
    req.startTime = process.hrtime();
    
    // Create a request-specific logger with correlation ID
    req.logger = createRequestLogger(req);
    
    // Add correlation ID to response headers for tracking
    res.setHeader('x-correlation-id', req.id as string);
    
    // Capture the response body for logging
    captureResponseBody(res);
    
    // Log the incoming request
    req.logger.info({
      message: `Incoming request: ${req.method} ${req.path}`,
      request: {
        method: req.method,
        path: req.originalUrl || req.url,
        query: getSafeRequestQuery(req),
        headers: getSafeRequestHeaders(req),
        body: getSafeRequestBody(req),
        ip: req.ip,
        protocol: req.protocol,
      },
    });
    
    // Capture the original end method to log the response
    const originalEnd = res.end;
    res.end = function (chunk?: any, encoding?: BufferEncoding, callback?: () => void): Response {
      // Calculate request duration
      const duration = calculateDuration(req.startTime as [number, number]);
      
      // Determine log level based on response status
      const logLevel = getLogLevelForStatus(res.statusCode);
      
      // Log the response
      req.logger[logLevel]({
        message: `Outgoing response: ${res.statusCode} ${req.method} ${req.path} (${duration.toFixed(2)}ms)`,
        response: {
          statusCode: res.statusCode,
          headers: maskSensitiveHeaders(res.getHeaders()),
          body: getSafeResponseBody(res),
          duration: `${duration.toFixed(2)}ms`,
        },
        performance: {
          duration,
          durationFormatted: `${duration.toFixed(2)}ms`,
        },
      });
      
      // Call the original end method
      return originalEnd.apply(res, [chunk, encoding, callback]);
    };
    
    next();
  };
};

/**
 * Error logging middleware for Express
 * 
 * This middleware logs all errors that occur during request processing.
 * It should be registered after all other middleware and routes.
 * 
 * @returns Express error middleware function
 */
export const errorLoggingMiddleware = () => {
  return (err: Error, req: ExtendedRequest, res: Response, next: NextFunction): void => {
    // Create a logger if it doesn't exist
    if (!req.logger) {
      req.logger = createRequestLogger(req);
    }
    
    // Calculate request duration if start time exists
    let duration = 0;
    if (req.startTime) {
      duration = calculateDuration(req.startTime);
    }
    
    // Log the error
    req.logger.error({
      message: `Error processing request: ${req.method} ${req.path}`,
      error: {
        name: err.name,
        message: err.message,
        stack: err.stack,
      },
      request: {
        method: req.method,
        path: req.originalUrl || req.url,
        query: getSafeRequestQuery(req),
        headers: getSafeRequestHeaders(req),
        body: getSafeRequestBody(req),
      },
      performance: {
        duration,
        durationFormatted: `${duration.toFixed(2)}ms`,
      },
    });
    
    // Continue to the next error handler
    next(err);
  };
};

export default loggingMiddleware;