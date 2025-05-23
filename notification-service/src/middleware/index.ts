/**
 * Middleware Index
 * 
 * This file serves as the central entry point for all middleware components in the Notification Service.
 * It exports all middleware components and provides a middleware registration function for the Express app.
 * 
 * The middleware is applied in a specific order to ensure proper request processing:
 * 1. Correlation middleware - Adds correlation IDs for distributed tracing
 * 2. Logging middleware - Logs all requests and responses
 * 3. Rate limiting middleware - Prevents API abuse
 * 4. HMAC verification middleware - Verifies webhook payload signatures
 * 5. Authentication middleware - Validates JWT tokens and enforces role-based access
 * 6. Error middleware - Handles all errors in a consistent way
 */

import { Express, RequestHandler } from 'express';
import { Logger } from 'winston';

// Import all middleware components
import { correlationMiddleware } from './correlation-middleware';
import { loggingMiddleware } from './logging-middleware';
import { rateLimitMiddleware } from './rate-limit-middleware';
import { hmacMiddleware } from './hmac-middleware';
import { authMiddleware } from './auth-middleware';
import { errorMiddleware } from './error-middleware';

// Re-export all middleware components for individual use
export { correlationMiddleware } from './correlation-middleware';
export { loggingMiddleware } from './logging-middleware';
export { rateLimitMiddleware } from './rate-limit-middleware';
export { hmacMiddleware } from './hmac-middleware';
export { authMiddleware } from './auth-middleware';
export { errorMiddleware } from './error-middleware';

/**
 * Middleware configuration interface
 * Defines the structure for middleware configuration options
 */
export interface MiddlewareConfig {
  /** Enable correlation ID middleware */
  enableCorrelation?: boolean;
  /** Enable request/response logging middleware */
  enableLogging?: boolean;
  /** Enable rate limiting middleware */
  enableRateLimit?: boolean;
  /** Enable HMAC signature verification middleware */
  enableHmac?: boolean;
  /** Enable JWT authentication middleware */
  enableAuth?: boolean;
  /** Enable global error handling middleware */
  enableError?: boolean;
  /** Logger instance for middleware components */
  logger?: Logger;
  /** Current environment (development, staging, production) */
  environment?: string;
  /** Redis client for rate limiting */
  redisClient?: any;
  /** HMAC secret key for webhook signature verification */
  hmacSecret?: string;
  /** JWT public key for token verification */
  jwtPublicKey?: string;
  /** Correlation ID header name */
  correlationHeader?: string;
}

/**
 * Default middleware configuration
 * Provides sensible defaults for middleware options
 */
export const defaultMiddlewareConfig: MiddlewareConfig = {
  enableCorrelation: true,
  enableLogging: true,
  enableRateLimit: true,
  enableHmac: true,
  enableAuth: true,
  enableError: true,
  environment: process.env.NODE_ENV || 'development',
  correlationHeader: 'X-Correlation-ID'
};

/**
 * Middleware registration function
 * Applies middleware to an Express application in the correct order
 * 
 * @param app - Express application instance
 * @param config - Middleware configuration options
 * @returns The Express application instance for chaining
 */
export function registerMiddleware(app: Express, config: MiddlewareConfig = {}): Express {
  // Merge provided config with defaults
  const mergedConfig: MiddlewareConfig = { ...defaultMiddlewareConfig, ...config };
  const { 
    enableCorrelation, 
    enableLogging, 
    enableRateLimit, 
    enableHmac, 
    enableAuth, 
    enableError,
    logger,
    redisClient,
    hmacSecret,
    jwtPublicKey,
    correlationHeader
  } = mergedConfig;

  // Apply middleware in the correct order
  
  // 1. Correlation ID middleware (first to enable request tracking)
  if (enableCorrelation) {
    app.use(correlationMiddleware({ 
      headerName: correlationHeader,
      logger
    }));
  }

  // 2. Logging middleware (early to log all requests)
  if (enableLogging) {
    app.use(loggingMiddleware({ 
      logger,
      level: mergedConfig.environment === 'development' ? 'debug' : 'info'
    }));
  }

  // 3. Rate limiting middleware (before auth to prevent abuse)
  if (enableRateLimit && redisClient) {
    app.use(rateLimitMiddleware({
      redisClient,
      windowMs: 60 * 1000, // 1 minute
      max: 60, // 60 requests per minute
      standardHeaders: true,
      logger
    }));
  }

  // 4. HMAC verification middleware (for webhook endpoints)
  if (enableHmac && hmacSecret) {
    // Apply only to webhook routes
    app.use('/api/webhooks', hmacMiddleware({
      secret: hmacSecret,
      algorithm: 'sha256',
      logger
    }));
  }

  // 5. Authentication middleware (for protected routes)
  if (enableAuth && jwtPublicKey) {
    // Apply to all routes except health check and webhook endpoints
    app.use(/^\/(?!health|api\/webhooks).*/, authMiddleware({
      publicKey: jwtPublicKey,
      algorithm: 'RS256',
      logger
    }));
  }

  // 6. Error middleware (last to catch all errors)
  if (enableError) {
    app.use(errorMiddleware({
      logger,
      showStack: mergedConfig.environment === 'development'
    }));
  }

  return app;
}

/**
 * Middleware stack types
 * Defines the available middleware stacks for different use cases
 */
export enum MiddlewareStack {
  /** Full middleware stack for API routes */
  API = 'api',
  /** Minimal stack for webhook endpoints */
  WEBHOOK = 'webhook',
  /** Basic stack for health check endpoints */
  HEALTH = 'health',
  /** Custom stack for specific routes */
  CUSTOM = 'custom'
}

/**
 * Register a predefined middleware stack
 * Applies a specific set of middleware based on the stack type
 * 
 * @param app - Express application instance
 * @param stack - Middleware stack type
 * @param config - Middleware configuration options
 * @returns The Express application instance for chaining
 */
export function registerMiddlewareStack(
  app: Express, 
  stack: MiddlewareStack, 
  config: MiddlewareConfig = {}
): Express {
  const mergedConfig: MiddlewareConfig = { ...defaultMiddlewareConfig, ...config };
  
  switch (stack) {
    case MiddlewareStack.API:
      // Full middleware stack for API routes
      return registerMiddleware(app, mergedConfig);
      
    case MiddlewareStack.WEBHOOK:
      // Minimal stack for webhook endpoints (correlation, logging, HMAC, error)
      return registerMiddleware(app, {
        ...mergedConfig,
        enableRateLimit: false,
        enableAuth: false
      });
      
    case MiddlewareStack.HEALTH:
      // Basic stack for health check endpoints (correlation, logging, error)
      return registerMiddleware(app, {
        ...mergedConfig,
        enableRateLimit: false,
        enableHmac: false,
        enableAuth: false
      });
      
    case MiddlewareStack.CUSTOM:
      // Use the provided config as is
      return registerMiddleware(app, mergedConfig);
      
    default:
      // Default to full API stack
      return registerMiddleware(app, mergedConfig);
  }
}

/**
 * Create a middleware function that can be applied to specific routes
 * 
 * @param middleware - Express middleware function
 * @param condition - Function that determines whether to apply the middleware
 * @returns Conditional middleware function
 */
export function conditionalMiddleware(
  middleware: RequestHandler,
  condition: (req: any, res: any) => boolean
): RequestHandler {
  return (req, res, next) => {
    if (condition(req, res)) {
      return middleware(req, res, next);
    }
    return next();
  };
}

/**
 * Apply multiple middleware functions in sequence
 * 
 * @param middlewares - Array of Express middleware functions
 * @returns Combined middleware function
 */
export function combineMiddleware(middlewares: RequestHandler[]): RequestHandler {
  return (req, res, next) => {
    // Create a middleware chain
    const chain = middlewares.reduceRight(
      (nextMiddleware, currentMiddleware) => {
        return (err?: any) => {
          if (err) {
            return next(err);
          }
          try {
            currentMiddleware(req, res, nextMiddleware);
          } catch (error) {
            next(error);
          }
        };
      },
      next
    );
    
    // Start the chain
    chain();
  };
}