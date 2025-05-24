/**
 * Redis Configuration for Notification Service
 * 
 * This file configures Redis connection and caching settings for the Notification Service.
 * It defines connection parameters, TTL settings, and cache strategies.
 * It enables the service to implement rate limiting, store temporary data, and manage webhook delivery state.
 */

import { Redis, RedisOptions, ClusterOptions } from 'ioredis';
import * as fs from 'fs';
import * as path from 'path';
import { logger } from './logger';

// Environment-specific configuration
import { config } from './app';

/**
 * Redis connection types
 */
export enum RedisConnectionType {
  STANDALONE = 'standalone',
  CLUSTER = 'cluster',
}

/**
 * Redis cache namespaces to organize keys
 */
export enum RedisCacheNamespace {
  WEBHOOK_RATE_LIMIT = 'webhook:rate-limit',
  WEBHOOK_DELIVERY = 'webhook:delivery',
  APPLICATION_DATA = 'app:data',
  USER_SESSION = 'user:session',
}

/**
 * TTL settings in seconds
 */
export const REDIS_TTL = {
  // 15 minutes for application data
  APPLICATION_DATA: 15 * 60,
  // 24 hours for user sessions
  USER_SESSION: 24 * 60 * 60,
  // 1 hour for webhook delivery tracking
  WEBHOOK_DELIVERY: 60 * 60,
  // 1 minute for rate limiting
  RATE_LIMIT: 60,
};

/**
 * Base Redis connection options
 */
const baseRedisOptions: RedisOptions = {
  // Enable TLS for all Redis connections
  tls: config.redis.tls ? {
    // Load CA certificate if provided
    ca: config.redis.tlsCa ? fs.readFileSync(config.redis.tlsCa) : undefined,
    // Load client certificate if provided
    cert: config.redis.tlsCert ? fs.readFileSync(config.redis.tlsCert) : undefined,
    // Load client key if provided
    key: config.redis.tlsKey ? fs.readFileSync(config.redis.tlsKey) : undefined,
    // Reject unauthorized connections (self-signed certs not allowed in production)
    rejectUnauthorized: config.env === 'production',
  } : undefined,
  
  // Authentication
  username: config.redis.username,
  password: config.redis.password,
  
  // Connection settings
  connectTimeout: 15000, // 15 seconds
  maxRetriesPerRequest: 5,
  enableAutoPipelining: true,
  autoResubscribe: true,
  
  // Reconnection strategy
  retryStrategy(times) {
    const delay = Math.min(100 + times * 200, 5000);
    logger.info(`Redis connection retry attempt ${times} with delay ${delay}ms`);
    return delay;
  },
  
  // Error handling
  reconnectOnError(err) {
    const targetError = err.toString();
    // Reconnect on connection errors but not on command errors
    if (targetError.includes('READONLY') || 
        targetError.includes('ETIMEDOUT') || 
        targetError.includes('ECONNRESET') ||
        targetError.includes('ECONNREFUSED')) {
      logger.warn(`Redis reconnecting due to error: ${targetError}`);
      return true; // Reconnect
    }
    return false; // Don't reconnect
  },
};

/**
 * Cluster-specific options
 */
const clusterOptions: ClusterOptions = {
  // Cluster connection settings
  clusterRetryStrategy(times) {
    const delay = Math.min(100 + times * 200, 5000);
    logger.info(`Redis cluster connection retry attempt ${times} with delay ${delay}ms`);
    return delay;
  },
  redisOptions: baseRedisOptions,
  // Retry settings for various cluster scenarios
  maxRedirections: 16,
  retryDelayOnFailover: 200,
  retryDelayOnClusterDown: 1000,
  retryDelayOnTryAgain: 100,
  slotsRefreshTimeout: 15000,
  slotsRefreshInterval: 20000,
  enableOfflineQueue: true,
  enableReadyCheck: true,
  scaleReads: 'slave', // Read from replicas when possible
};

/**
 * Create Redis client based on configuration
 */
export function createRedisClient(): Redis {
  try {
    // Determine if we're using cluster mode
    if (config.redis.connectionType === RedisConnectionType.CLUSTER && config.redis.nodes) {
      logger.info(`Creating Redis cluster connection to ${config.redis.nodes.length} nodes`);
      return new Redis.Cluster(config.redis.nodes, clusterOptions);
    } else {
      // Standalone mode
      logger.info(`Creating Redis standalone connection to ${config.redis.host}:${config.redis.port}`);
      return new Redis({
        ...baseRedisOptions,
        host: config.redis.host,
        port: config.redis.port,
        db: config.redis.db || 0,
      });
    }
  } catch (error) {
    logger.error('Failed to create Redis client', { error });
    throw error;
  }
}

// Create and export the Redis client instance
let redisClient: Redis;

/**
 * Get the Redis client instance (creates it if it doesn't exist)
 */
export function getRedisClient(): Redis {
  if (!redisClient) {
    redisClient = createRedisClient();
    
    // Set up event handlers
    redisClient.on('error', (err) => {
      logger.error('Redis client error', { error: err.message });
    });
    
    redisClient.on('connect', () => {
      logger.info('Redis client connected');
    });
    
    redisClient.on('ready', () => {
      logger.info('Redis client ready');
    });
    
    redisClient.on('close', () => {
      logger.info('Redis client connection closed');
    });
  }
  
  return redisClient;
}

/**
 * Helper function to generate cache key with namespace
 */
export function generateCacheKey(namespace: RedisCacheNamespace, key: string): string {
  return `${namespace}:${key}`;
}

/**
 * Helper function to set a value with TTL
 */
export async function setCacheValue(
  namespace: RedisCacheNamespace,
  key: string,
  value: string | object,
  ttlSeconds?: number
): Promise<void> {
  const client = getRedisClient();
  const cacheKey = generateCacheKey(namespace, key);
  const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
  
  try {
    if (ttlSeconds) {
      await client.set(cacheKey, stringValue, 'EX', ttlSeconds);
    } else {
      // Use default TTL based on namespace
      const defaultTtl = namespace === RedisCacheNamespace.USER_SESSION
        ? REDIS_TTL.USER_SESSION
        : REDIS_TTL.APPLICATION_DATA;
      
      await client.set(cacheKey, stringValue, 'EX', defaultTtl);
    }
  } catch (error) {
    logger.error('Error setting cache value', { namespace, key, error });
    throw error;
  }
}

/**
 * Helper function to get a cached value
 */
export async function getCacheValue<T = any>(
  namespace: RedisCacheNamespace,
  key: string
): Promise<T | null> {
  const client = getRedisClient();
  const cacheKey = generateCacheKey(namespace, key);
  
  try {
    const value = await client.get(cacheKey);
    
    if (!value) {
      return null;
    }
    
    try {
      return JSON.parse(value) as T;
    } catch {
      // If not JSON, return as is
      return value as unknown as T;
    }
  } catch (error) {
    logger.error('Error getting cache value', { namespace, key, error });
    return null;
  }
}

/**
 * Helper function to delete a cached value
 */
export async function deleteCacheValue(
  namespace: RedisCacheNamespace,
  key: string
): Promise<boolean> {
  const client = getRedisClient();
  const cacheKey = generateCacheKey(namespace, key);
  
  try {
    const result = await client.del(cacheKey);
    return result > 0;
  } catch (error) {
    logger.error('Error deleting cache value', { namespace, key, error });
    return false;
  }
}

/**
 * Helper function to implement rate limiting
 * Returns true if the rate limit is exceeded
 */
export async function checkRateLimit(
  key: string,
  limit: number,
  windowSeconds: number
): Promise<boolean> {
  const client = getRedisClient();
  const cacheKey = generateCacheKey(RedisCacheNamespace.WEBHOOK_RATE_LIMIT, key);
  
  try {
    // Increment the counter
    const count = await client.incr(cacheKey);
    
    // Set expiry on first request
    if (count === 1) {
      await client.expire(cacheKey, windowSeconds);
    }
    
    // Check if rate limit exceeded
    return count > limit;
  } catch (error) {
    logger.error('Error checking rate limit', { key, error });
    // In case of error, allow the request to proceed
    return false;
  }
}

/**
 * Close Redis connection
 */
export async function closeRedisConnection(): Promise<void> {
  if (redisClient) {
    try {
      await redisClient.quit();
      logger.info('Redis connection closed gracefully');
    } catch (error) {
      logger.error('Error closing Redis connection', { error });
      // Force disconnect if quit fails
      redisClient.disconnect();
    } finally {
      redisClient = undefined as unknown as Redis;
    }
  }
}

export default {
  getRedisClient,
  setCacheValue,
  getCacheValue,
  deleteCacheValue,
  checkRateLimit,
  closeRedisConnection,
  REDIS_TTL,
  RedisCacheNamespace,
};