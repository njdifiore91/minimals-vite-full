/**
 * Correlation ID Middleware for Distributed Tracing
 * 
 * This middleware generates or extracts correlation IDs from request headers,
 * adds them to the request context, and ensures they are included in all logs
 * and downstream service calls. It enables end-to-end request tracking across
 * the microservice architecture.
 */

import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { createContextLogger } from '../config/logger';
import { ILogContext } from '../types/common';

/**
 * Configuration options for the correlation middleware
 */
export interface ICorrelationOptions {
  /** Header name for the correlation ID (default: 'x-correlation-id') */
  headerName?: string;
  
  /** Whether to generate a new ID if none is provided (default: true) */
  generateIfMissing?: boolean;
  
  /** Whether to include the correlation ID in response headers (default: true) */
  includeInResponse?: boolean;
  
  /** Additional headers to check for correlation ID if primary header is missing */
  alternativeHeaders?: string[];
  
  /** Function to generate a correlation ID if none is provided */
  generator?: () => string;
  
  /** Whether to propagate the correlation ID to downstream services (default: true) */
  propagateToDownstream?: boolean;
}

/**
 * Default correlation middleware options
 */
const defaultOptions: ICorrelationOptions = {
  headerName: 'x-correlation-id',
  generateIfMissing: true,
  includeInResponse: true,
  alternativeHeaders: ['x-request-id', 'request-id', 'x-amzn-trace-id'],
  generator: () => uuidv4(),
  propagateToDownstream: true,
};

/**
 * Request with correlation ID and logger
 */
export interface ICorrelatedRequest extends Request {
  correlationId?: string;
  logger?: ReturnType<typeof createContextLogger>;
}

/**
 * Creates a middleware function that handles correlation IDs for distributed tracing
 * 
 * @param options - Configuration options for the correlation middleware
 * @returns Express middleware function
 */
export const correlationMiddleware = (options: ICorrelationOptions = {}) => {
  // Merge provided options with defaults
  const config = { ...defaultOptions, ...options };
  
  return (req: ICorrelatedRequest, res: Response, next: NextFunction) => {
    // Extract correlation ID from headers or generate a new one
    let correlationId = req.headers[config.headerName!.toLowerCase()] as string;
    
    // Check alternative headers if primary header is missing
    if (!correlationId && config.alternativeHeaders && config.alternativeHeaders.length > 0) {
      for (const header of config.alternativeHeaders) {
        const altId = req.headers[header.toLowerCase()] as string;
        if (altId) {
          correlationId = altId;
          break;
        }
      }
    }
    
    // Generate a new correlation ID if none was found and generation is enabled
    if (!correlationId && config.generateIfMissing) {
      correlationId = config.generator!();
    }
    
    if (correlationId) {
      // Add correlation ID to request object for use in route handlers
      req.correlationId = correlationId;
      
      // Include correlation ID in response headers if enabled
      if (config.includeInResponse) {
        res.setHeader(config.headerName!, correlationId);
      }
      
      // Create a request-scoped logger with correlation context
      const logContext: ILogContext = {
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
      
      // Add user ID to log context if available
      if (req.user && (req.user as any).id) {
        logContext.userId = (req.user as any).id;
      }
      
      // Create and attach logger to request
      req.logger = createContextLogger(logContext);
      
      // Log the incoming request
      req.logger.info(`Incoming ${req.method} request to ${req.path}`);
      
      // Track response time
      const startTime = Date.now();
      
      // Capture response data
      const originalEnd = res.end;
      res.end = function(this: Response, ...args: any[]) {
        // Calculate request duration
        const duration = Date.now() - startTime;
        
        // Log the response
        if (req.logger) {
          const logLevel = res.statusCode >= 500 ? 'error' : 
                          res.statusCode >= 400 ? 'warn' : 'info';
          
          req.logger[logLevel](`${req.method} ${req.path} completed with status ${res.statusCode} in ${duration}ms`);
        }
        
        // Call the original end method
        return originalEnd.apply(this, args);
      };
    }
    
    next();
  };
};

/**
 * Utility function to extract correlation ID from a request
 * 
 * @param req - Express request object
 * @param headerName - Header name to check for correlation ID
 * @returns Correlation ID or undefined if not found
 */
export const getCorrelationId = (req: ICorrelatedRequest, headerName: string = 'x-correlation-id'): string | undefined => {
  return req.correlationId || req.headers[headerName.toLowerCase()] as string | undefined;
};

/**
 * Utility function to add correlation ID to outgoing requests
 * 
 * @param headers - Headers object to add correlation ID to
 * @param correlationId - Correlation ID to add
 * @param headerName - Header name to use for correlation ID
 * @returns Updated headers object
 */
export const addCorrelationIdToHeaders = (
  headers: Record<string, string> = {},
  correlationId?: string,
  headerName: string = 'x-correlation-id'
): Record<string, string> => {
  if (correlationId) {
    return { ...headers, [headerName.toLowerCase()]: correlationId };
  }
  return headers;
};

/**
 * Utility function to create Axios request interceptor for correlation ID propagation
 * 
 * @param axiosInstance - Axios instance to add interceptor to
 * @param headerName - Header name to use for correlation ID
 * @returns Function to remove the interceptor
 */
export const createAxiosCorrelationInterceptor = (axiosInstance: any, headerName: string = 'x-correlation-id') => {
  const interceptorId = axiosInstance.interceptors.request.use((config: any) => {
    // Get correlation ID from current request context (if available)
    const correlationId = global.currentCorrelationId;
    
    if (correlationId && config.headers) {
      // Add correlation ID to request headers
      config.headers[headerName.toLowerCase()] = correlationId;
    }
    
    return config;
  });
  
  // Return function to remove the interceptor
  return () => axiosInstance.interceptors.request.eject(interceptorId);
};

/**
 * Middleware to store correlation ID in async local storage for background processing
 * 
 * This middleware stores the correlation ID in AsyncLocalStorage to make it available
 * to background tasks and asynchronous operations that are not directly connected to
 * the request-response cycle.
 * 
 * @param asyncLocalStorage - AsyncLocalStorage instance to use
 * @returns Express middleware function
 */
export const asyncLocalStorageMiddleware = (asyncLocalStorage: any) => {
  return (req: ICorrelatedRequest, res: Response, next: NextFunction) => {
    if (req.correlationId) {
      // Store correlation ID in AsyncLocalStorage
      asyncLocalStorage.run({ correlationId: req.correlationId }, () => {
        next();
      });
    } else {
      next();
    }
  };
};

export default correlationMiddleware;