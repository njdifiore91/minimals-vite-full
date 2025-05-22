/**
 * Rate Limiting Middleware for Notification Service
 * 
 * This middleware restricts the number of requests a client can make within a specified time window,
 * preventing abuse and ensuring fair resource allocation. It uses Redis for distributed rate limit
 * tracking and provides configurable limits based on client identity or IP address.
 * 
 * Default rate limits:
 * - 60 requests per minute for authenticated users
 * - 10 requests per minute for unauthenticated requests
 */

import { Request, Response, NextFunction } from 'express';
import Redis from 'ioredis';
import { getErrorMessage } from '../../src/auth/utils/error-message';

/**
 * Configuration options for the rate limit middleware
 */
export interface RateLimitOptions {
  /** Redis client instance for distributed rate limiting */
  redisClient: Redis;
  /** Time window in milliseconds for rate limiting (default: 60000 = 1 minute) */
  windowMs?: number;
  /** Maximum number of requests allowed in the window for authenticated users (default: 60) */
  maxRequestsAuthenticated?: number;
  /** Maximum number of requests allowed in the window for unauthenticated users (default: 10) */
  maxRequestsUnauthenticated?: number;
  /** Custom key generator function (default: uses IP address or user ID) */
  keyGenerator?: (req: Request) => string;
  /** Custom skip function to bypass rate limiting for certain requests (default: none) */
  skip?: (req: Request) => boolean;
  /** Custom error message when rate limit is exceeded (default: standard message) */
  message?: string;
  /** Custom status code when rate limit is exceeded (default: 429 Too Many Requests) */
  statusCode?: number;
  /** Whether to include standard rate limit headers (default: true) */
  standardHeaders?: boolean;
  /** Whether to include legacy X-RateLimit headers (default: false) */
  legacyHeaders?: boolean;
}

/**
 * Creates a rate limiting middleware with the specified options
 * 
 * @param options Configuration options for the rate limiter
 * @returns Express middleware function
 */
export const createRateLimitMiddleware = (options: RateLimitOptions) => {
  const {
    redisClient,
    windowMs = 60 * 1000, // 1 minute default
    maxRequestsAuthenticated = 60, // 60 requests per minute for authenticated users
    maxRequestsUnauthenticated = 10, // 10 requests per minute for unauthenticated users
    keyGenerator,
    skip,
    message = 'Too many requests, please try again later.',
    statusCode = 429,
    standardHeaders = true,
    legacyHeaders = false
  } = options;

  // Validate Redis client
  if (!redisClient) {
    throw new Error('Redis client is required for rate limit middleware');
  }

  // Default key generator function
  const defaultKeyGenerator = (req: Request): string => {
    // Use user ID from JWT token if authenticated, otherwise use IP
    const userId = req.user?.id || req.user?.sub;
    const ip = req.ip || req.connection.remoteAddress || '0.0.0.0';
    
    return userId ? `rate-limit:user:${userId}` : `rate-limit:ip:${ip}`;
  };

  // Return the middleware function
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      // Skip rate limiting if skip function returns true
      if (skip && skip(req)) {
        return next();
      }

      // Generate the rate limit key
      const key = keyGenerator ? keyGenerator(req) : defaultKeyGenerator(req);
      
      // Determine if the request is authenticated
      const isAuthenticated = !!req.user;
      
      // Set the appropriate rate limit based on authentication status
      const limit = isAuthenticated ? maxRequestsAuthenticated : maxRequestsUnauthenticated;

      // Get the current count from Redis
      const currentCount = await redisClient.get(key);
      const count = currentCount ? parseInt(currentCount, 10) : 0;

      // Calculate remaining requests
      const remaining = Math.max(0, limit - count);

      // Get TTL for the key
      const ttl = await redisClient.ttl(key);
      const reset = Date.now() + (ttl >= 0 ? ttl * 1000 : windowMs);
      const resetTime = Math.ceil(reset / 1000); // Reset time in seconds

      // Set rate limit headers
      if (standardHeaders) {
        res.setHeader('RateLimit-Limit', limit);
        res.setHeader('RateLimit-Remaining', remaining);
        res.setHeader('RateLimit-Reset', resetTime);
      }

      if (legacyHeaders) {
        res.setHeader('X-RateLimit-Limit', limit);
        res.setHeader('X-RateLimit-Remaining', remaining);
        res.setHeader('X-RateLimit-Reset', resetTime);
      }

      // Check if rate limit is exceeded
      if (count >= limit) {
        // Set Retry-After header
        const retryAfter = Math.ceil(windowMs / 1000);
        res.setHeader('Retry-After', retryAfter);

        // Return rate limit exceeded error
        return res.status(statusCode).json({
          error: 'Rate limit exceeded',
          message,
          retryAfter,
          limit,
          remaining: 0,
          reset: resetTime
        });
      }

      // Increment the counter
      await redisClient.incr(key);
      
      // Set expiration if this is the first request in the window
      if (count === 0) {
        await redisClient.expire(key, Math.ceil(windowMs / 1000));
      }

      // Continue to the next middleware
      next();
    } catch (error) {
      // Log the error but don't block the request
      console.error(`Rate limit error: ${getErrorMessage(error)}`);
      next();
    }
  };
};

/**
 * Creates a rate limiting middleware with default options
 * 
 * @param redisClient Redis client instance
 * @returns Express middleware function
 */
export const defaultRateLimiter = (redisClient: Redis) => {
  return createRateLimitMiddleware({
    redisClient,
    windowMs: 60 * 1000, // 1 minute
    maxRequestsAuthenticated: 60, // 60 requests per minute for authenticated users
    maxRequestsUnauthenticated: 10, // 10 requests per minute for unauthenticated users
    standardHeaders: true,
    legacyHeaders: false,
    message: 'Too many requests to the notification service. Please try again later.'
  });
};

/**
 * Creates a more restrictive rate limiting middleware for sensitive endpoints
 * 
 * @param redisClient Redis client instance
 * @returns Express middleware function
 */
export const sensitiveEndpointRateLimiter = (redisClient: Redis) => {
  return createRateLimitMiddleware({
    redisClient,
    windowMs: 60 * 1000, // 1 minute
    maxRequestsAuthenticated: 30, // 30 requests per minute for authenticated users
    maxRequestsUnauthenticated: 5, // 5 requests per minute for unauthenticated users
    standardHeaders: true,
    legacyHeaders: false,
    message: 'Too many requests to a sensitive endpoint. Please try again later.'
  });
};

/**
 * Creates a rate limiting middleware for webhook configuration endpoints
 * 
 * @param redisClient Redis client instance
 * @returns Express middleware function
 */
export const webhookConfigRateLimiter = (redisClient: Redis) => {
  return createRateLimitMiddleware({
    redisClient,
    windowMs: 5 * 60 * 1000, // 5 minutes
    maxRequestsAuthenticated: 20, // 20 requests per 5 minutes for authenticated users
    maxRequestsUnauthenticated: 0, // No access for unauthenticated users
    standardHeaders: true,
    legacyHeaders: false,
    message: 'Too many webhook configuration requests. Please try again later.'
  });
};

export default {
  createRateLimitMiddleware,
  defaultRateLimiter,
  sensitiveEndpointRateLimiter,
  webhookConfigRateLimiter
};