package com.dollarfunding.mca.cache;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/**
 * Implementation of the CacheService interface using Redis for the MCA application.
 * This class provides the concrete implementation of caching operations using Spring's RedisTemplate.
 * It handles serialization/deserialization of cached objects, implements TTL-based caching,
 * and includes comprehensive error handling and logging.
 *
 * Key features:
 * - TTL-based caching with configurable expiration times (15 minutes for application data, 24 hours for sessions)
 * - Serialization/deserialization of cached objects
 * - Comprehensive error handling and logging
 * - Optimized performance for high-throughput cache operations
 * - Support for both single values and collections
 */
@Service
public class RedisCacheService implements CacheService {

    private static final Logger log = LoggerFactory.getLogger(RedisCacheService.class);

    private final RedisTemplate<String, Object> redisTemplate;
    private final CacheMetricsCollector metricsCollector;
    private final CacheKeyGenerator keyGenerator;

    /**
     * Constructor for RedisCacheService.
     *
     * @param redisTemplate    The RedisTemplate for Redis operations
     * @param metricsCollector The metrics collector for cache performance monitoring
     * @param keyGenerator     The key generator for creating standardized cache keys
     */
    @Autowired
    public RedisCacheService(RedisTemplate<String, Object> redisTemplate,
                             CacheMetricsCollector metricsCollector,
                             CacheKeyGenerator keyGenerator) {
        this.redisTemplate = redisTemplate;
        this.metricsCollector = metricsCollector;
        this.keyGenerator = keyGenerator;
    }

    /**
     * Gets a value from the cache.
     *
     * @param key The cache key
     * @return The cached value, or null if not found
     */
    @Override
    public <T> T get(String key) {
        try {
            long startTime = System.nanoTime();
            @SuppressWarnings("unchecked")
            T value = (T) redisTemplate.opsForValue().get(key);
            long endTime = System.nanoTime();
            
            if (value != null) {
                metricsCollector.recordCacheHit(key, endTime - startTime);
                log.debug("Cache hit for key: {}", key);
            } else {
                metricsCollector.recordCacheMiss(key);
                log.debug("Cache miss for key: {}", key);
            }
            
            return value;
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while getting key: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return null;
        } catch (Exception e) {
            log.error("Error getting value from cache for key: {}", key, e);
            metricsCollector.recordCacheError(key, "get_error");
            return null;
        }
    }

    /**
     * Gets a value from the cache, or computes it if not present.
     *
     * @param key      The cache key
     * @param supplier The supplier to compute the value if not in cache
     * @return The cached or computed value
     */
    @Override
    public <T> T getOrCompute(String key, Supplier<T> supplier) {
        T value = get(key);
        if (value == null) {
            value = supplier.get();
            if (value != null) {
                set(key, value, Duration.ofMinutes(CacheConstants.APPLICATION_DATA_TTL_MINUTES));
            }
        }
        return value;
    }

    /**
     * Gets a value from the cache, or computes it if not present, with a custom TTL.
     *
     * @param key      The cache key
     * @param supplier The supplier to compute the value if not in cache
     * @param ttl      The time-to-live duration for the cached value
     * @return The cached or computed value
     */
    @Override
    public <T> T getOrCompute(String key, Supplier<T> supplier, Duration ttl) {
        T value = get(key);
        if (value == null) {
            value = supplier.get();
            if (value != null) {
                set(key, value, ttl);
            }
        }
        return value;
    }

    /**
     * Sets a value in the cache with the default application data TTL.
     *
     * @param key   The cache key
     * @param value The value to cache
     * @return true if successful, false otherwise
     */
    @Override
    public <T> boolean set(String key, T value) {
        return set(key, value, Duration.ofMinutes(CacheConstants.APPLICATION_DATA_TTL_MINUTES));
    }

    /**
     * Sets a value in the cache with a custom TTL.
     *
     * @param key   The cache key
     * @param value The value to cache
     * @param ttl   The time-to-live duration for the cached value
     * @return true if successful, false otherwise
     */
    @Override
    public <T> boolean set(String key, T value, Duration ttl) {
        try {
            long startTime = System.nanoTime();
            redisTemplate.opsForValue().set(key, value, ttl);
            long endTime = System.nanoTime();
            
            metricsCollector.recordCacheWrite(key, endTime - startTime);
            log.debug("Set value in cache for key: {} with TTL: {}", key, ttl);
            return true;
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while setting key: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return false;
        } catch (Exception e) {
            log.error("Error setting value in cache for key: {}", key, e);
            metricsCollector.recordCacheError(key, "set_error");
            return false;
        }
    }

    /**
     * Sets multiple values in the cache with the default application data TTL.
     *
     * @param keyValueMap The map of keys to values to cache
     * @return true if successful, false otherwise
     */
    @Override
    public <T> boolean setAll(Map<String, T> keyValueMap) {
        return setAll(keyValueMap, Duration.ofMinutes(CacheConstants.APPLICATION_DATA_TTL_MINUTES));
    }

    /**
     * Sets multiple values in the cache with a custom TTL.
     *
     * @param keyValueMap The map of keys to values to cache
     * @param ttl         The time-to-live duration for the cached values
     * @return true if successful, false otherwise
     */
    @Override
    public <T> boolean setAll(Map<String, T> keyValueMap, Duration ttl) {
        try {
            if (keyValueMap == null || keyValueMap.isEmpty()) {
                return true;
            }
            
            long startTime = System.nanoTime();
            redisTemplate.opsForValue().multiSet(keyValueMap);
            
            // Set expiration for each key
            for (String key : keyValueMap.keySet()) {
                redisTemplate.expire(key, ttl.toMillis(), TimeUnit.MILLISECONDS);
            }
            
            long endTime = System.nanoTime();
            metricsCollector.recordCacheBatchWrite(keyValueMap.size(), endTime - startTime);
            log.debug("Set {} values in cache with TTL: {}", keyValueMap.size(), ttl);
            return true;
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while setting multiple keys", e);
            metricsCollector.recordCacheError("batch", "connection_failure");
            return false;
        } catch (Exception e) {
            log.error("Error setting multiple values in cache", e);
            metricsCollector.recordCacheError("batch", "set_all_error");
            return false;
        }
    }

    /**
     * Deletes a value from the cache.
     *
     * @param key The cache key to delete
     * @return true if successful, false otherwise
     */
    @Override
    public boolean delete(String key) {
        try {
            Boolean result = redisTemplate.delete(key);
            if (Boolean.TRUE.equals(result)) {
                log.debug("Deleted key from cache: {}", key);
                metricsCollector.recordCacheEviction(key);
                return true;
            } else {
                log.debug("Key not found for deletion: {}", key);
                return false;
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while deleting key: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return false;
        } catch (Exception e) {
            log.error("Error deleting key from cache: {}", key, e);
            metricsCollector.recordCacheError(key, "delete_error");
            return false;
        }
    }

    /**
     * Deletes multiple values from the cache.
     *
     * @param keys The collection of cache keys to delete
     * @return The number of keys that were deleted
     */
    @Override
    public long deleteAll(Collection<String> keys) {
        try {
            if (keys == null || keys.isEmpty()) {
                return 0;
            }
            
            Long count = redisTemplate.delete(keys);
            if (count != null && count > 0) {
                log.debug("Deleted {} keys from cache", count);
                metricsCollector.recordCacheBatchEviction(count.intValue());
                return count;
            } else {
                log.debug("No keys found for deletion from collection of size: {}", keys.size());
                return 0;
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while deleting multiple keys", e);
            metricsCollector.recordCacheError("batch", "connection_failure");
            return 0;
        } catch (Exception e) {
            log.error("Error deleting multiple keys from cache", e);
            metricsCollector.recordCacheError("batch", "delete_all_error");
            return 0;
        }
    }

    /**
     * Deletes all keys matching a pattern.
     *
     * @param pattern The pattern to match keys against
     * @return The number of keys that were deleted
     */
    @Override
    public long deleteByPattern(String pattern) {
        try {
            Set<String> keys = redisTemplate.keys(pattern);
            if (keys != null && !keys.isEmpty()) {
                Long count = redisTemplate.delete(keys);
                if (count != null && count > 0) {
                    log.debug("Deleted {} keys matching pattern: {}", count, pattern);
                    metricsCollector.recordCacheBatchEviction(count.intValue());
                    return count;
                }
            }
            log.debug("No keys found matching pattern: {}", pattern);
            return 0;
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while deleting keys by pattern: {}", pattern, e);
            metricsCollector.recordCacheError(pattern, "connection_failure");
            return 0;
        } catch (Exception e) {
            log.error("Error deleting keys by pattern: {}", pattern, e);
            metricsCollector.recordCacheError(pattern, "delete_pattern_error");
            return 0;
        }
    }

    /**
     * Checks if a key exists in the cache.
     *
     * @param key The cache key to check
     * @return true if the key exists, false otherwise
     */
    @Override
    public boolean exists(String key) {
        try {
            Boolean exists = redisTemplate.hasKey(key);
            if (Boolean.TRUE.equals(exists)) {
                log.debug("Key exists in cache: {}", key);
                return true;
            } else {
                log.debug("Key does not exist in cache: {}", key);
                return false;
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while checking key existence: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return false;
        } catch (Exception e) {
            log.error("Error checking if key exists in cache: {}", key, e);
            metricsCollector.recordCacheError(key, "exists_error");
            return false;
        }
    }

    /**
     * Gets the remaining time-to-live for a key.
     *
     * @param key The cache key
     * @return The remaining TTL in milliseconds, or -1 if the key does not exist or has no TTL
     */
    @Override
    public long getTimeToLive(String key) {
        try {
            Long ttl = redisTemplate.getExpire(key, TimeUnit.MILLISECONDS);
            if (ttl != null && ttl > 0) {
                log.debug("TTL for key {}: {} ms", key, ttl);
                return ttl;
            } else {
                log.debug("No TTL found for key: {}", key);
                return -1;
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while getting TTL for key: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return -1;
        } catch (Exception e) {
            log.error("Error getting TTL for key: {}", key, e);
            metricsCollector.recordCacheError(key, "ttl_error");
            return -1;
        }
    }

    /**
     * Updates the time-to-live for a key.
     *
     * @param key The cache key
     * @param ttl The new time-to-live duration
     * @return true if successful, false otherwise
     */
    @Override
    public boolean updateTimeToLive(String key, Duration ttl) {
        try {
            Boolean result = redisTemplate.expire(key, ttl.toMillis(), TimeUnit.MILLISECONDS);
            if (Boolean.TRUE.equals(result)) {
                log.debug("Updated TTL for key {} to {} ms", key, ttl.toMillis());
                return true;
            } else {
                log.debug("Failed to update TTL for key: {}", key);
                return false;
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while updating TTL for key: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return false;
        } catch (Exception e) {
            log.error("Error updating TTL for key: {}", key, e);
            metricsCollector.recordCacheError(key, "update_ttl_error");
            return false;
        }
    }

    /**
     * Increments a counter in the cache.
     *
     * @param key       The cache key
     * @param increment The amount to increment by
     * @return The new value, or -1 if the operation failed
     */
    @Override
    public long increment(String key, long increment) {
        try {
            Long newValue = redisTemplate.opsForValue().increment(key, increment);
            if (newValue != null) {
                log.debug("Incremented key {} by {} to new value: {}", key, increment, newValue);
                return newValue;
            } else {
                log.warn("Failed to increment key: {}", key);
                return -1;
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while incrementing key: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return -1;
        } catch (Exception e) {
            log.error("Error incrementing key: {}", key, e);
            metricsCollector.recordCacheError(key, "increment_error");
            return -1;
        }
    }

    /**
     * Decrements a counter in the cache.
     *
     * @param key       The cache key
     * @param decrement The amount to decrement by
     * @return The new value, or -1 if the operation failed
     */
    @Override
    public long decrement(String key, long decrement) {
        try {
            Long newValue = redisTemplate.opsForValue().decrement(key, decrement);
            if (newValue != null) {
                log.debug("Decremented key {} by {} to new value: {}", key, decrement, newValue);
                return newValue;
            } else {
                log.warn("Failed to decrement key: {}", key);
                return -1;
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure while decrementing key: {}", key, e);
            metricsCollector.recordCacheError(key, "connection_failure");
            return -1;
        } catch (Exception e) {
            log.error("Error decrementing key: {}", key, e);
            metricsCollector.recordCacheError(key, "decrement_error");
            return -1;
        }
    }

    /**
     * Gets multiple values from the cache.
     *
     * @param keys The collection of cache keys
     * @return A list of values in the same order as the keys
     */
    @Override
    public <T> List<T> multiGet(Collection<String> keys) {
        try {
            if (keys == null || keys.isEmpty()) {
                return Collections.emptyList();
            }
            
            long startTime = System.nanoTime();
            List<Object> values = redisTemplate.opsForValue().multiGet(keys);
            long endTime = System.nanoTime();
            
            if (values != null) {
                int hitCount = 0;
                for (Object value : values) {
                    if (value != null) {
                        hitCount++;
                    }
                }
                
                metricsCollector.recordCacheBatchHit(hitCount, keys.size() - hitCount, endTime - startTime);
                log.debug("Multi-get for {} keys: {} hits, {} misses", keys.size(), hitCount, keys.size() - hitCount);
                
                @SuppressWarnings("unchecked")
                List<T> typedValues = (List<T>) values;
                return typedValues;
            } else {
                log.debug("Multi-get returned null for {} keys", keys.size());
                metricsCollector.recordCacheBatchMiss(keys.size());
                return Collections.emptyList();
            }
        } catch (RedisConnectionFailureException e) {
            log.error("Redis connection failure during multi-get operation", e);
            metricsCollector.recordCacheError("batch", "connection_failure");
            return Collections.emptyList();
        } catch (Exception e) {
            log.error("Error performing multi-get operation", e);
            metricsCollector.recordCacheError("batch", "multi_get_error");
            return Collections.emptyList();
        }
    }

    /**
     * Gets the Redis template for direct access to Redis operations.
     * This should be used with caution and only for operations not covered by the standard methods.
     *
     * @return The RedisTemplate instance
     */
    @Override
    public RedisTemplate<String, Object> getRedisTemplate() {
        return redisTemplate;
    }

    /**
     * Executes a cache operation with fallback to a supplier if the cache operation fails.
     * This is a utility method for implementing resilient cache operations.
     *
     * @param cacheOperation The cache operation to execute
     * @param fallback       The fallback supplier to use if the cache operation fails
     * @return The result of the cache operation or fallback
     */
    @Override
    public <T> T executeWithFallback(Supplier<T> cacheOperation, Supplier<T> fallback) {
        try {
            return cacheOperation.get();
        } catch (Exception e) {
            log.warn("Cache operation failed, using fallback", e);
            metricsCollector.recordCacheError("fallback", "operation_failure");
            return fallback.get();
        }
    }
}