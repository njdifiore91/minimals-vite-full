/**
 * Correlation ID Middleware
 * 
 * This middleware implements correlation ID handling for distributed tracing across microservices.
 * It either extracts an existing correlation ID from request headers or generates a new one,
 * adds it to the request context, and ensures it's included in response headers and logs.
 * 
 * The correlation ID serves as a unique identifier for tracking requests across multiple services,
 * making it easier to trace and debug distributed transactions.
 */

import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';

/**
 * Extended Express Request interface with correlation ID functionality
 */
declare global {
  namespace Express {
    interface Request {
      /**
       * Correlation ID utilities for the current request
       */
      correlator: {
        /**
         * Get the correlation ID for the current request
         */
        getCorrelationId(): string;
        
        /**
         * Forward the correlation ID to downstream service headers
         * @param headers Headers object to add the correlation ID to
         */
        forwardCorrelationId(options: { headers: Record<string, string> }): void;
        
        /**
         * Get correlation ID context for logging
         */
        getLogContext(): { correlationId: string };
      };
    }
  }
}

/**
 * Configuration options for the correlation ID middleware
 */
export interface CorrelationIdOptions {
  /**
   * Header name to use for the correlation ID
   * @default 'X-Correlation-ID'
   */
  headerName?: string;
  
  /**
   * List of alternative header names to check for existing correlation IDs
   * @default ['X-Request-ID', 'X-Correlation-Id', 'correlation-id', 'request-id']
   */
  alternativeHeaderNames?: string[];
  
  /**
   * Function to generate a new correlation ID when one doesn't exist
   * @default () => uuidv4()
   */
  generator?: () => string;
  
  /**
   * Function to validate a correlation ID from request headers
   * @default (id) => typeof id === 'string' && id.length > 0
   */
  validator?: (id: string) => boolean;
  
  /**
   * Whether to add the correlation ID to response headers
   * @default true
   */
  addToResponse?: boolean;
}

/**
 * Default correlation ID options
 */
const defaultOptions: CorrelationIdOptions = {
  headerName: 'X-Correlation-ID',
  alternativeHeaderNames: ['X-Request-ID', 'X-Correlation-Id', 'correlation-id', 'request-id'],
  generator: () => uuidv4(),
  validator: (id: string) => typeof id === 'string' && id.length > 0,
  addToResponse: true
};

/**
 * Thread-local storage for correlation ID in async contexts
 * This allows accessing the correlation ID outside the request handler
 */
const asyncLocalStorage = new (require('async_hooks').AsyncLocalStorage)();

/**
 * Get the current correlation ID from async local storage
 * @returns The current correlation ID or undefined if not in a request context
 */
export function getCurrentCorrelationId(): string | undefined {
  const store = asyncLocalStorage.getStore() as Map<string, string> | undefined;
  return store?.get('correlationId');
}

/**
 * Create correlation ID middleware with the specified options
 * 
 * @param options Configuration options for the correlation ID middleware
 * @returns Express middleware function
 */
export default function correlationMiddleware(options: CorrelationIdOptions = {}) {
  // Merge provided options with defaults
  const config = { ...defaultOptions, ...options };
  
  return (req: Request, res: Response, next: NextFunction) => {
    // Extract or generate correlation ID
    const correlationId = extractOrGenerateCorrelationId(req, config);
    
    // Store correlation ID in async local storage for access outside request context
    const store = new Map<string, string>();
    store.set('correlationId', correlationId);
    
    // Add correlation ID to response headers if configured
    if (config.addToResponse) {
      res.setHeader(config.headerName, correlationId);
    }
    
    // Add correlator object to request for accessing correlation ID in route handlers
    req.correlator = {
      getCorrelationId: () => correlationId,
      
      forwardCorrelationId: ({ headers }: { headers: Record<string, string> }) => {
        headers[config.headerName] = correlationId;
      },
      
      getLogContext: () => ({ correlationId })
    };
    
    // Continue with request handling in async local storage context
    asyncLocalStorage.run(store, next);
  };
}

/**
 * Extract correlation ID from request headers or generate a new one
 * 
 * @param req Express request object
 * @param options Correlation ID options
 * @returns Correlation ID string
 */
function extractOrGenerateCorrelationId(req: Request, options: CorrelationIdOptions): string {
  // First check the primary header name
  let correlationId = req.headers[options.headerName.toLowerCase()] as string;
  
  // If not found, check alternative header names
  if (!correlationId && options.alternativeHeaderNames) {
    for (const headerName of options.alternativeHeaderNames) {
      correlationId = req.headers[headerName.toLowerCase()] as string;
      if (correlationId) break;
    }
  }
  
  // Validate correlation ID if found
  if (correlationId && options.validator && !options.validator(correlationId)) {
    correlationId = null;
  }
  
  // Generate new correlation ID if not found or invalid
  if (!correlationId && options.generator) {
    correlationId = options.generator();
  }
  
  return correlationId;
}

/**
 * Helper function to get the correlation ID for the current request
 * This can be used outside of the request handler (e.g., in services)
 * 
 * @returns The current correlation ID or undefined if not in a request context
 */
correlationMiddleware.getId = getCurrentCorrelationId;

/**
 * Helper function to create headers with correlation ID for downstream service calls
 * 
 * @param headers Optional existing headers to add the correlation ID to
 * @returns Headers object with correlation ID
 */
correlationMiddleware.createHeaders = (headers: Record<string, string> = {}): Record<string, string> => {
  const correlationId = getCurrentCorrelationId();
  if (correlationId) {
    headers[defaultOptions.headerName] = correlationId;
  }
  return headers;
};