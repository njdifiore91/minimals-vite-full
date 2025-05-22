/**
 * Redis Configuration for Notification Service
 * 
 * This file configures Redis connection and caching settings for the Notification Service.
 * It defines connection parameters, TTL settings, and cache strategies.
 * It enables the service to implement rate limiting, store temporary data, and manage webhook delivery state.
 */

import Redis from 'ioredis';
import { IRedisConfig } from '../types/config';
import { logger } from './logger';
import { config } from './app';

/**
 * Default TTL values in seconds
 */
export const DEFAULT_TTL = {
  // 15 minutes for application data
  APPLICATION_DATA: 15 * 60,
  // 24 hours for sessions
  SESSION: 24 * 60 * 60,
  // 1 hour for rate limiting
  RATE_LIMIT: 60 * 60,
  // 30 minutes for webhook delivery state
  WEBHOOK_STATE: 30 * 60,
};

/**
 * Cache namespace prefixes to avoid key collisions
 */
export const CACHE_NAMESPACES = {
  WEBHOOK: 'webhook:',
  RATE_LIMIT: 'rate-limit:',
  SESSION: 'session:',
  APPLICATION: 'app:',
  NOTIFICATION: 'notification:',
};

/**
 * Redis configuration object
 */
export const redisConfig: IRedisConfig = {
  // Connection options
  host: config.redis.host,
  port: config.redis.port,
  username: config.redis.username,
  password: config.redis.password,
  db: config.redis.db || 0,
  
  // Enable TLS if configured
  tls: config.redis.tls ? {
    // TLS configuration
    rejectUnauthorized: true,
    ca: config.redis.tlsCa ? [config.redis.tlsCa] : undefined,
  } : undefined,
  
  // Connection management
  connectTimeout: 10000,
  disconnectTimeout: 2000,
  keepAlive: 10000,
  noDelay: true,
  
  // Retry strategy
  retryStrategy: (times: number) => {
    const delay = Math.min(times * 50, 2000);
    logger.warn(`Redis connection attempt ${times} failed. Retrying in ${delay}ms`);
    return delay;
  },
  
  // Reconnect on error only for specific errors
  reconnectOnError: (err: Error) => {
    const targetErrors = ['READONLY', 'ETIMEDOUT', 'ECONNRESET', 'ECONNREFUSED'];
    const shouldReconnect = targetErrors.some(errorType => 
      err.message.includes(errorType)
    );
    
    if (shouldReconnect) {
      logger.warn(`Redis reconnecting due to error: ${err.message}`);
    } else {
      logger.error(`Redis error without reconnection: ${err.message}`);
    }
    
    return shouldReconnect;
  },
  
  // Enable offline queue for commands when disconnected
  enableOfflineQueue: true,
  
  // Enable ready check to ensure Redis is ready to accept commands
  enableReadyCheck: true,
  
  // Auto-pipelining for performance optimization
  enableAutoPipelining: true,
  
  // Maximum number of retries per request
  maxRetriesPerRequest: 3,
  
  // Cluster mode configuration (if enabled)
  ...(config.redis.cluster ? {
    redisOptions: {
      // Inherit base options
      password: config.redis.password,
      tls: config.redis.tls ? {
        rejectUnauthorized: true,
        ca: config.redis.tlsCa ? [config.redis.tlsCa] : undefined,
      } : undefined,
    },
    // Cluster-specific options
    clusterRetryStrategy: (times: number) => {
      const delay = Math.min(times * 100, 3000);
      logger.warn(`Redis cluster connection attempt ${times} failed. Retrying in ${delay}ms`);
      return delay;
    },
    // Read from all replicas for load balancing
    scaleReads: 'all',
    // Maximum number of redirections to follow for cluster operations
    maxRedirections: 16,
  } : {}),
};

/**
 * Creates and returns a Redis client instance
 */
export const createRedisClient = (): Redis => {
  let client: Redis;

  // Create cluster client if cluster mode is enabled
  if (config.redis.cluster && Array.isArray(config.redis.nodes) && config.redis.nodes.length > 0) {
    logger.info(`Initializing Redis cluster connection with ${config.redis.nodes.length} nodes`);
    client = new Redis.Cluster(config.redis.nodes, redisConfig);
  } else {
    // Create standalone client
    logger.info(`Initializing Redis standalone connection to ${config.redis.host}:${config.redis.port}`);
    client = new Redis(redisConfig);
  }

  // Set up event handlers
  client.on('connect', () => {
    logger.info('Redis client connected');
  });

  client.on('ready', () => {
    logger.info('Redis client ready');
  });

  client.on('error', (err) => {
    logger.error(`Redis client error: ${err.message}`);
  });

  client.on('close', () => {
    logger.warn('Redis client connection closed');
  });

  client.on('reconnecting', () => {
    logger.info('Redis client reconnecting...');
  });

  client.on('end', () => {
    logger.warn('Redis client connection ended');
  });

  return client;
};

/**
 * Redis client singleton instance
 */
export const redisClient = createRedisClient();

/**
 * Helper function to build cache key with namespace
 */
export const buildCacheKey = (namespace: string, key: string): string => {
  return `${namespace}${key}`;
};

/**
 * Helper function to set a value in Redis with TTL
 */
export const setWithTTL = async (
  key: string, 
  value: string | number | Buffer | object, 
  ttlSeconds: number = DEFAULT_TTL.APPLICATION_DATA
): Promise<'OK'> => {
  const serializedValue = typeof value === 'object' ? JSON.stringify(value) : String(value);
  return redisClient.set(key, serializedValue, 'EX', ttlSeconds);
};

/**
 * Helper function to get a value from Redis with automatic deserialization
 */
export const getAndParse = async <T = any>(key: string): Promise<T | null> => {
  const value = await redisClient.get(key);
  if (!value) return null;
  
  try {
    return JSON.parse(value) as T;
  } catch (e) {
    // If not JSON, return as is
    return value as unknown as T;
  }
};

/**
 * Helper function for implementing rate limiting
 */
export const incrementRateLimit = async (
  key: string,
  ttlSeconds: number = DEFAULT_TTL.RATE_LIMIT
): Promise<number> => {
  const rateLimitKey = buildCacheKey(CACHE_NAMESPACES.RATE_LIMIT, key);
  
  // Use multi to ensure atomic operations
  const multi = redisClient.multi();
  multi.incr(rateLimitKey);
  multi.expire(rateLimitKey, ttlSeconds);
  
  const results = await multi.exec();
  // Return the incremented value (first command result)
  return results?.[0]?.[1] as number || 1;
};

/**
 * Helper function to check if a rate limit has been exceeded
 */
export const checkRateLimit = async (
  key: string,
  limit: number
): Promise<boolean> => {
  const rateLimitKey = buildCacheKey(CACHE_NAMESPACES.RATE_LIMIT, key);
  const count = await redisClient.get(rateLimitKey);
  return count !== null && parseInt(count, 10) >= limit;
};

export default {
  redisClient,
  buildCacheKey,
  setWithTTL,
  getAndParse,
  incrementRateLimit,
  checkRateLimit,
  CACHE_NAMESPACES,
  DEFAULT_TTL,
};