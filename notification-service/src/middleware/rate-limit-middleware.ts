/**
 * Rate Limiting Middleware
 * 
 * This middleware implements request rate limiting based on client identity or IP address.
 * It uses Redis for distributed rate limit tracking and provides configurable limits
 * based on authentication status, user role, and endpoint sensitivity.
 * 
 * Features:
 * - Configurable rate limit windows and thresholds
 * - Redis-based storage for distributed environments
 * - Rate limit response headers (X-RateLimit-*)
 * - Detailed error responses for rate limit exceeded
 * - Support for different limits based on authentication status
 */

import { Request, Response, NextFunction } from 'express';
import Redis from 'ioredis';
import { getErrorMessage } from '../utils/error-message';

/**
 * Rate limit options interface
 */
export interface RateLimitOptions {
  // The maximum number of requests allowed within the window
  max: number;
  // The time window in seconds
  windowMs: number;
  // The Redis client instance
  redisClient: Redis;
  // The Redis key prefix for rate limit keys
  keyPrefix?: string;
  // Function to generate the rate limit key from the request
  keyGenerator?: (req: Request) => string;
  // Skip rate limiting for certain requests
  skip?: (req: Request) => boolean;
  // Custom response handler for rate limit exceeded
  handler?: (req: Request, res: Response) => void;
  // Whether to include rate limit headers in the response
  headers?: boolean;
  // The status code to use when rate limit is exceeded
  statusCode?: number;
  // The message to send when rate limit is exceeded
  message?: string;
  // Whether to use a sliding window for rate limiting
  slidingWindow?: boolean;
}

/**
 * Default rate limit options
 */
const defaultOptions: Partial<RateLimitOptions> = {
  keyPrefix: 'ratelimit:',
  keyGenerator: (req: Request): string => {
    // Use client ID from authenticated user if available, otherwise use IP
    const clientId = req.user?.id || req.ip || req.headers['x-forwarded-for'] || 'unknown';
    return `${clientId}`;
  },
  skip: (): boolean => false,
  headers: true,
  statusCode: 429,
  message: 'Too many requests, please try again later.',
  slidingWindow: true,
};

/**
 * Rate limit middleware factory function
 * 
 * @param options Rate limit options
 * @returns Express middleware function
 */
export const rateLimitMiddleware = (options: Partial<RateLimitOptions>) => {
  // Merge default options with provided options
  const opts: RateLimitOptions = { ...defaultOptions, ...options } as RateLimitOptions;
  
  // Validate required options
  if (!opts.max || !opts.windowMs) {
    throw new Error('Rate limit middleware requires max and windowMs options');
  }
  
  if (!opts.redisClient) {
    throw new Error('Rate limit middleware requires a Redis client');
  }

  // Return the middleware function
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      // Skip rate limiting if the skip function returns true
      if (opts.skip && opts.skip(req)) {
        return next();
      }

      // Generate the rate limit key
      const key = `${opts.keyPrefix}${opts.keyGenerator!(req)}`;
      
      // Get the current timestamp
      const now = Date.now();
      
      // Calculate the window start time
      const windowStart = now - (opts.windowMs * 1000);

      let result: number;
      
      if (opts.slidingWindow) {
        // Sliding window implementation using Redis sorted sets
        // 1. Add the current request to the sorted set with score = current timestamp
        // 2. Remove all requests older than the window start time
        // 3. Count the remaining items in the sorted set
        const multi = opts.redisClient.multi();
        multi.zadd(key, now, `${now}-${Math.random().toString(36).substring(2, 10)}`);
        multi.zremrangebyscore(key, 0, windowStart);
        multi.zcard(key);
        multi.pexpire(key, opts.windowMs * 1000);
        
        const results = await multi.exec();
        result = results ? (results[2][1] as number) : 0;
      } else {
        // Fixed window implementation using Redis counters
        const count = await opts.redisClient.incr(key);
        
        // Set expiration on first request
        if (count === 1) {
          await opts.redisClient.pexpire(key, opts.windowMs * 1000);
        }
        
        result = count;
      }

      // Get the TTL of the key
      const ttl = await opts.redisClient.pttl(key);
      
      // Calculate remaining requests
      const remaining = Math.max(0, opts.max - result);
      
      // Set rate limit headers if enabled
      if (opts.headers) {
        res.setHeader('X-RateLimit-Limit', opts.max);
        res.setHeader('X-RateLimit-Remaining', remaining);
        res.setHeader('X-RateLimit-Reset', Math.ceil(Date.now() + ttl));
      }

      // Check if rate limit is exceeded
      if (result > opts.max) {
        if (opts.headers) {
          res.setHeader('Retry-After', Math.ceil(ttl / 1000));
        }
        
        // Use custom handler if provided, otherwise send standard response
        if (opts.handler) {
          return opts.handler(req, res);
        }
        
        return res.status(opts.statusCode!).json({
          status: 'error',
          statusCode: opts.statusCode,
          message: opts.message,
          retryAfter: Math.ceil(ttl / 1000),
        });
      }

      // Continue to the next middleware
      return next();
    } catch (error) {
      // Log the error and continue to the next middleware
      console.error(`Rate limit error: ${getErrorMessage(error)}`);
      return next();
    }
  };
};

/**
 * Create authenticated user rate limit middleware
 * 
 * @param redisClient Redis client instance
 * @param customOptions Custom rate limit options
 * @returns Express middleware function
 */
export const createAuthenticatedRateLimit = (
  redisClient: Redis,
  customOptions: Partial<RateLimitOptions> = {}
) => {
  return rateLimitMiddleware({
    max: 60, // 60 requests per minute for authenticated users
    windowMs: 60 * 1000, // 1 minute window
    redisClient,
    keyPrefix: 'ratelimit:auth:',
    keyGenerator: (req: Request): string => {
      // Use authenticated user ID as the key
      return req.user?.id || 'unknown';
    },
    skip: (req: Request): boolean => {
      // Skip rate limiting if user is not authenticated
      return !req.user;
    },
    ...customOptions,
  });
};

/**
 * Create unauthenticated user rate limit middleware
 * 
 * @param redisClient Redis client instance
 * @param customOptions Custom rate limit options
 * @returns Express middleware function
 */
export const createUnauthenticatedRateLimit = (
  redisClient: Redis,
  customOptions: Partial<RateLimitOptions> = {}
) => {
  return rateLimitMiddleware({
    max: 10, // 10 requests per minute for unauthenticated users
    windowMs: 60 * 1000, // 1 minute window
    redisClient,
    keyPrefix: 'ratelimit:unauth:',
    keyGenerator: (req: Request): string => {
      // Use IP address as the key
      return req.ip || req.headers['x-forwarded-for'] as string || 'unknown';
    },
    skip: (req: Request): boolean => {
      // Skip rate limiting if user is authenticated
      return !!req.user;
    },
    ...customOptions,
  });
};

/**
 * Create role-based rate limit middleware
 * 
 * @param redisClient Redis client instance
 * @param roleRateLimits Map of role to rate limit configuration
 * @param defaultRateLimit Default rate limit for roles not specified
 * @returns Express middleware function
 */
export const createRoleBasedRateLimit = (
  redisClient: Redis,
  roleRateLimits: Record<string, { max: number; windowMs: number }>,
  defaultRateLimit: { max: number; windowMs: number } = { max: 30, windowMs: 60 * 1000 }
) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    // Get user role from request
    const role = req.user?.role || 'anonymous';
    
    // Get rate limit configuration for the role or use default
    const rateLimitConfig = roleRateLimits[role] || defaultRateLimit;
    
    // Create and apply rate limit middleware
    const middleware = rateLimitMiddleware({
      max: rateLimitConfig.max,
      windowMs: rateLimitConfig.windowMs,
      redisClient,
      keyPrefix: `ratelimit:role:${role}:`,
      keyGenerator: (req: Request): string => {
        // Use user ID or IP address as the key
        return req.user?.id || req.ip || 'unknown';
      },
    });
    
    return middleware(req, res, next);
  };
};

/**
 * Create endpoint-specific rate limit middleware
 * 
 * @param redisClient Redis client instance
 * @param max Maximum number of requests allowed
 * @param windowMs Time window in milliseconds
 * @param customOptions Custom rate limit options
 * @returns Express middleware function
 */
export const createEndpointRateLimit = (
  redisClient: Redis,
  max: number,
  windowMs: number,
  customOptions: Partial<RateLimitOptions> = {}
) => {
  return rateLimitMiddleware({
    max,
    windowMs,
    redisClient,
    keyPrefix: 'ratelimit:endpoint:',
    keyGenerator: (req: Request): string => {
      // Use endpoint path and user ID or IP as the key
      const identifier = req.user?.id || req.ip || 'unknown';
      return `${req.method}:${req.path}:${identifier}`;
    },
    ...customOptions,
  });
};