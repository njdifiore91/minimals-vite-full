import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../config/logger';
import { ILogContext } from '../types/common';

/**
 * Interface for logging middleware options
 */
export interface LoggingMiddlewareOptions {
  /** Fields to mask in request/response logs for security */
  sensitiveFields?: string[];
  /** Whether to log request body */
  logRequestBody?: boolean;
  /** Whether to log response body */
  logResponseBody?: boolean;
  /** Maximum length for logged bodies */
  maxBodyLength?: number;
  /** Custom request ID header name */
  correlationIdHeader?: string;
  /** Whether to include timing information */
  includeTimingInfo?: boolean;
}

/**
 * Default options for logging middleware
 */
const defaultOptions: LoggingMiddlewareOptions = {
  sensitiveFields: ['password', 'token', 'authorization', 'apiKey', 'secret', 'x-api-key', 'api-key'],
  logRequestBody: true,
  logResponseBody: false,
  maxBodyLength: 1024,
  correlationIdHeader: 'x-correlation-id',
  includeTimingInfo: true,
};

/**
 * Masks sensitive data in objects to prevent logging security-sensitive information
 * 
 * @param obj - The object to mask sensitive fields in
 * @param sensitiveFields - Array of field names to mask
 * @returns A new object with sensitive fields masked
 */
const maskSensitiveData = (obj: any, sensitiveFields: string[]): any => {
  if (!obj || typeof obj !== 'object') {
    return obj;
  }

  // Create a copy to avoid modifying the original object
  const masked = Array.isArray(obj) ? [...obj] : { ...obj };

  for (const key in masked) {
    if (Object.prototype.hasOwnProperty.call(masked, key)) {
      // Check if the current key is sensitive
      const isSensitive = sensitiveFields.some(field => 
        key.toLowerCase() === field.toLowerCase() || 
        key.toLowerCase().includes(field.toLowerCase())
      );

      if (isSensitive) {
        masked[key] = '********';
      } else if (typeof masked[key] === 'object' && masked[key] !== null) {
        // Recursively mask nested objects
        masked[key] = maskSensitiveData(masked[key], sensitiveFields);
      }
    }
  }

  return masked;
};

/**
 * Safely stringifies an object for logging, handling circular references
 * 
 * @param obj - The object to stringify
 * @param maxLength - Maximum length of the resulting string
 * @returns A string representation of the object
 */
const safeStringify = (obj: any, maxLength: number): string => {
  if (!obj) return '';
  
  try {
    const cache: any[] = [];
    const str = JSON.stringify(obj, (key, value) => {
      if (typeof value === 'object' && value !== null) {
        if (cache.includes(value)) {
          return '[Circular]';
        }
        cache.push(value);
      }
      return value;
    }, 2);
    
    return str.length > maxLength ? `${str.substring(0, maxLength)}... (truncated)` : str;
  } catch (error) {
    return `[Unstringifiable Object: ${error instanceof Error ? error.message : String(error)}]`;
  }
};

/**
 * Creates a logging middleware for Express that logs requests and responses
 * with correlation IDs for distributed tracing
 * 
 * @param options - Configuration options for the logging middleware
 * @returns Express middleware function
 */
export const loggingMiddleware = (options: LoggingMiddlewareOptions = {}) => {
  // Merge provided options with defaults
  const config = { ...defaultOptions, ...options };
  
  return (req: Request, res: Response, next: NextFunction): void => {
    // Start timing the request
    const startTime = process.hrtime();
    
    // Get or generate correlation ID
    const correlationId = req.headers[config.correlationIdHeader!] as string || 
                         req.correlationId || 
                         uuidv4();
    
    // Store correlation ID on request object for other middleware and route handlers
    req.correlationId = correlationId;
    
    // Add correlation ID to response headers
    res.setHeader(config.correlationIdHeader!, correlationId);
    
    // Create log context with correlation ID
    const logContext: ILogContext = {
      correlationId,
      requestId: req.id || uuidv4(),
      method: req.method,
      path: req.path,
      ip: req.ip,
      userAgent: req.get('user-agent') || 'unknown',
    };
    
    // Log the incoming request
    const requestLog = {
      type: 'request',
      method: req.method,
      url: req.originalUrl || req.url,
      path: req.path,
      params: maskSensitiveData(req.params, config.sensitiveFields!),
      query: maskSensitiveData(req.query, config.sensitiveFields!),
      headers: maskSensitiveData(req.headers, config.sensitiveFields!),
      ip: req.ip,
      userAgent: req.get('user-agent'),
    };
    
    // Add request body if configured
    if (config.logRequestBody && req.body) {
      requestLog['body'] = maskSensitiveData(req.body, config.sensitiveFields!);
    }
    
    logger.info(`Incoming request: ${req.method} ${req.originalUrl || req.url}`, {
      ...logContext,
      request: requestLog,
    });
    
    // Capture the original end method
    const originalEnd = res.end;
    
    // Override the end method to log the response
    res.end = function(this: Response, ...args: any[]): any {
      // Calculate request duration
      const hrDuration = process.hrtime(startTime);
      const durationMs = (hrDuration[0] * 1000 + hrDuration[1] / 1000000).toFixed(3);
      
      // Restore original end method
      res.end = originalEnd;
      
      // Call the original end method
      const result = originalEnd.apply(this, args);
      
      // Prepare response log
      const responseLog = {
        type: 'response',
        statusCode: res.statusCode,
        statusMessage: res.statusMessage,
        headers: maskSensitiveData(res.getHeaders(), config.sensitiveFields!),
        durationMs,
      };
      
      // Add response body if configured and available
      if (config.logResponseBody && res.locals.responseBody) {
        responseLog['body'] = maskSensitiveData(
          res.locals.responseBody, 
          config.sensitiveFields!
        );
      }
      
      // Determine log level based on status code
      let logLevel = 'info';
      if (res.statusCode >= 500) {
        logLevel = 'error';
      } else if (res.statusCode >= 400) {
        logLevel = 'warn';
      }
      
      // Log the response with appropriate level
      logger[logLevel](
        `Response sent: ${res.statusCode} ${req.method} ${req.originalUrl || req.url} - ${durationMs}ms`,
        {
          ...logContext,
          response: responseLog,
        }
      );
      
      return result;
    };
    
    // Continue to the next middleware
    next();
  };
};

/**
 * Middleware to capture response body for logging
 * This should be used if logResponseBody is enabled
 */
export const responseBodyCaptureMiddleware = () => {
  return (req: Request, res: Response, next: NextFunction): void => {
    // Store the original methods
    const originalSend = res.send;
    const originalJson = res.json;
    
    // Override send
    res.send = function(this: Response, body: any): Response {
      res.locals.responseBody = body;
      return originalSend.call(this, body);
    };
    
    // Override json
    res.json = function(this: Response, body: any): Response {
      res.locals.responseBody = body;
      return originalJson.call(this, body);
    };
    
    next();
  };
};

/**
 * Middleware to log errors
 */
export const errorLoggingMiddleware = () => {
  return (err: Error, req: Request, res: Response, next: NextFunction): void => {
    const correlationId = req.correlationId || req.headers['x-correlation-id'] || 'unknown';
    
    logger.error(`Error processing request: ${req.method} ${req.originalUrl || req.url}`, {
      correlationId,
      error: {
        message: err.message,
        stack: err.stack,
        name: err.name,
      },
      request: {
        method: req.method,
        url: req.originalUrl || req.url,
        headers: maskSensitiveData(req.headers, defaultOptions.sensitiveFields!),
        query: req.query,
        params: req.params,
      },
    });
    
    next(err);
  };
};

// Extend Express Request interface to include correlationId
declare global {
  namespace Express {
    interface Request {
      correlationId?: string;
      id?: string;
    }
  }
}

export default loggingMiddleware;