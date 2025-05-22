/**
 * Middleware Index
 * 
 * This file serves as the central export point for all middleware components in the Notification Service.
 * It provides a consistent interface for importing middleware throughout the application and includes
 * a middleware registration function for the Express app.
 *
 * The middleware components are organized in the recommended order of application:
 * 1. Security middleware (helmet)
 * 2. CORS middleware
 * 3. Body parsing middleware
 * 4. Compression middleware
 * 5. Correlation ID middleware (for request tracking)
 * 6. Logging middleware
 * 7. Rate limiting middleware
 * 8. Authentication middleware
 * 9. Validation middleware
 * 10. HMAC signature verification middleware
 * 11. Error handling middleware (applied last)
 */

import { Application as ExpressApplication, RequestHandler, ErrorRequestHandler } from 'express';
import { ILoggerConfig, IRedisConfig, IAppConfig } from '../types/config';

// Import middleware components
import { default as correlationMiddleware } from './correlation-middleware';
import { default as loggingMiddleware } from './logging-middleware';
import { default as errorMiddleware } from './error-middleware';
import { default as authMiddleware } from './auth-middleware';
import { default as validationMiddleware } from './validation-middleware';
import { default as rateLimitMiddleware } from './rate-limit-middleware';
import { default as hmacMiddleware } from './hmac-middleware';

// Export all middleware components
export {
  correlationMiddleware,
  loggingMiddleware,
  errorMiddleware,
  authMiddleware,
  validationMiddleware,
  rateLimitMiddleware,
  hmacMiddleware
};

/**
 * Middleware configuration options interface
 */
export interface IMiddlewareOptions {
  /** Logger configuration */
  loggerConfig: ILoggerConfig;
  /** Redis configuration for rate limiting */
  redisConfig: IRedisConfig;
  /** CORS allowed origins */
  corsOrigins: string | string[];
  /** Current environment (development, staging, production) */
  environment: string;
  /** Enable request body parsing */
  enableBodyParser?: boolean;
  /** Enable compression */
  enableCompression?: boolean;
  /** Enable security headers (helmet) */
  enableHelmet?: boolean;
  /** Enable CORS */
  enableCors?: boolean;
  /** Enable rate limiting */
  enableRateLimiting?: boolean;
  /** Request body size limit */
  bodySizeLimit?: string;
  /** JWT authentication options */
  jwtOptions?: {
    /** Algorithm used for token verification */
    algorithm: string;
    /** Token expiry time in seconds */
    expiryTime: number;
    /** Public key path for RS256 verification */
    publicKeyPath: string;
  };
  /** Webhook signature verification options */
  webhookSignatureOptions?: {
    /** Header name for the signature */
    signatureHeader: string;
    /** Header name for the timestamp */
    timestampHeader: string;
    /** Maximum age of timestamp in seconds */
    maxTimestampAge: number;
  };
}

/**
 * Middleware stack configuration interface
 */
export interface IMiddlewareStack {
  /** Pre-route middleware (applied before routes) */
  preRouteMiddleware: RequestHandler[];
  /** Post-route middleware (applied after routes) */
  postRouteMiddleware: RequestHandler[];
  /** Error middleware (applied last) */
  errorMiddleware: ErrorRequestHandler[];
}

/**
 * Default middleware options
 */
const defaultMiddlewareOptions: Partial<IMiddlewareOptions> = {
  enableBodyParser: true,
  enableCompression: true,
  enableHelmet: true,
  enableCors: true,
  enableRateLimiting: true,
  bodySizeLimit: '1mb'
};

/**
 * Configure and register middleware for an Express application
 * 
 * @param app Express application instance
 * @param options Middleware configuration options
 * @returns The configured middleware stack
 */
export function registerMiddleware(
  app: ExpressApplication,
  options: IMiddlewareOptions
): IMiddlewareStack {
  // Merge options with defaults
  const config = { ...defaultMiddlewareOptions, ...options };
  
  // Initialize middleware stacks
  const preRouteMiddleware: RequestHandler[] = [];
  const postRouteMiddleware: RequestHandler[] = [];
  const errorMiddlewareHandlers: ErrorRequestHandler[] = [];

  // Import required middleware based on configuration
  const express = require('express');
  const helmet = config.enableHelmet ? require('helmet') : null;
  const cors = config.enableCors ? require('cors') : null;
  const compression = config.enableCompression ? require('compression') : null;

  // Add security middleware (should be first)
  if (config.enableHelmet) {
    preRouteMiddleware.push(helmet());
  }

  // Add CORS middleware
  if (config.enableCors) {
    preRouteMiddleware.push(cors({
      origin: config.corsOrigins,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Correlation-ID', 'X-Webhook-Signature'],
      credentials: true,
      maxAge: 86400 // 24 hours
    }));
  }

  // Add body parsing middleware
  if (config.enableBodyParser) {
    preRouteMiddleware.push(express.json({ limit: config.bodySizeLimit }));
    preRouteMiddleware.push(express.urlencoded({ extended: true, limit: config.bodySizeLimit }));
  }

  // Add compression middleware
  if (config.enableCompression) {
    preRouteMiddleware.push(compression());
  }

  // Add correlation ID middleware (for request tracking)
  preRouteMiddleware.push(correlationMiddleware());

  // Add logging middleware
  preRouteMiddleware.push(loggingMiddleware(config.loggerConfig));

  // Add rate limiting middleware if enabled
  if (config.enableRateLimiting) {
    // Apply rate limiting to API routes only
    app.use('/api', rateLimitMiddleware(config.redisConfig));
  }
  
  // Note: Auth middleware and validation middleware are not applied globally
  // They should be applied to specific routes as needed

  // Add 404 handler to post-route middleware
  postRouteMiddleware.push((req, res, next) => {
    res.status(404).json({
      error: 'Not Found',
      message: `Route ${req.method} ${req.path} not found`,
      status: 404
    });
  });

  // Add error middleware (should be last)
  errorMiddlewareHandlers.push(errorMiddleware());

  // Apply pre-route middleware to the app
  preRouteMiddleware.forEach(middleware => app.use(middleware));

  // Post-route middleware will be applied after routes are registered
  // Error middleware will be applied last

  return {
    preRouteMiddleware,
    postRouteMiddleware,
    errorMiddleware: errorMiddlewareHandlers
  };
}

/**
 * Apply post-route middleware to an Express application
 * 
 * @param app Express application instance
 * @param middlewareStack Middleware stack configuration
 */
export function applyPostRouteMiddleware(
  app: ExpressApplication,
  middlewareStack: IMiddlewareStack
): void {
  // Apply post-route middleware
  middlewareStack.postRouteMiddleware.forEach(middleware => app.use(middleware));
  
  // Apply error middleware (must be last)
  middlewareStack.errorMiddleware.forEach(middleware => app.use(middleware));
}

/**
 * Apply authentication middleware to specific routes
 * 
 * @param app Express application instance
 * @param routes Array of route paths to protect
 * @param roles Optional array of required roles for access
 */
export function applyAuthMiddleware(
  app: ExpressApplication,
  routes: string[],
  roles?: string[]
): void {
  routes.forEach(route => {
    if (roles && roles.length > 0) {
      // Apply role-based authentication
      app.use(route, authMiddleware({ requiredRoles: roles }));
    } else {
      // Apply standard authentication
      app.use(route, authMiddleware());
    }
  });
}

/**
 * Apply HMAC signature verification middleware to webhook routes
 * 
 * @param app Express application instance
 * @param routes Array of webhook route paths to protect
 */
export function applyHmacMiddleware(
  app: ExpressApplication,
  routes: string[]
): void {
  routes.forEach(route => {
    app.use(route, hmacMiddleware());
  });
}

/**
 * Apply validation middleware to specific routes
 * 
 * @param app Express application instance
 * @param validationRules Object mapping routes to validation schemas
 */
export function applyValidationMiddleware(
  app: ExpressApplication,
  validationRules: Record<string, any>
): void {
  Object.entries(validationRules).forEach(([route, schema]) => {
    app.use(route, validationMiddleware(schema));
  });
}

/**
 * Create environment-specific middleware configuration
 * 
 * @param environment Current environment (development, staging, production)
 * @param baseOptions Base middleware options
 * @returns Environment-specific middleware options
 */
export function createEnvironmentMiddlewareOptions(
  environment: string,
  baseOptions: Partial<IMiddlewareOptions>
): IMiddlewareOptions {
  // Default options for all environments
  const defaultOptions: IMiddlewareOptions = {
    loggerConfig: {
      level: 'info',
      format: 'json',
      timestamp: true
    },
    redisConfig: {
      host: 'localhost',
      port: 6379,
      password: '',
      enableTLS: false,
      ttl: {
        applicationData: 900, // 15 minutes in seconds
        userSessions: 86400 // 24 hours in seconds
      }
    },
    corsOrigins: '*',
    environment,
    enableBodyParser: true,
    enableCompression: true,
    enableHelmet: true,
    enableCors: true,
    enableRateLimiting: true,
    bodySizeLimit: '1mb'
  };

  // Environment-specific overrides
  const environmentOptions: Partial<IMiddlewareOptions> = {};

  switch (environment) {
    case 'development':
      environmentOptions.loggerConfig = {
        level: 'debug',
        format: 'pretty',
        timestamp: true
      };
      environmentOptions.enableRateLimiting = false;
      environmentOptions.corsOrigins = '*';
      break;

    case 'staging':
      environmentOptions.loggerConfig = {
        level: 'info',
        format: 'json',
        timestamp: true
      };
      environmentOptions.enableRateLimiting = true;
      environmentOptions.corsOrigins = ['https://staging.dollarfunding.com'];
      environmentOptions.redisConfig = {
        host: process.env.REDIS_HOST || 'redis',
        port: parseInt(process.env.REDIS_PORT || '6379', 10),
        password: process.env.REDIS_PASSWORD || '',
        enableTLS: true,
        ttl: {
          applicationData: 900, // 15 minutes in seconds
          userSessions: 86400 // 24 hours in seconds
        }
      };
      break;

    case 'production':
      environmentOptions.loggerConfig = {
        level: 'info',
        format: 'json',
        timestamp: true
      };
      environmentOptions.enableRateLimiting = true;
      environmentOptions.corsOrigins = ['https://dollarfunding.com'];
      environmentOptions.enableHelmet = true;
      environmentOptions.redisConfig = {
        host: process.env.REDIS_HOST || 'redis',
        port: parseInt(process.env.REDIS_PORT || '6379', 10),
        password: process.env.REDIS_PASSWORD || '',
        enableTLS: true,
        ttl: {
          applicationData: 900, // 15 minutes in seconds
          userSessions: 86400 // 24 hours in seconds
        }
      };
      break;

    default:
      // Use development settings for unknown environments
      return createEnvironmentMiddlewareOptions('development', baseOptions);
  }

  // Merge options in order of precedence: default < environment < base
  return { ...defaultOptions, ...environmentOptions, ...baseOptions };
}