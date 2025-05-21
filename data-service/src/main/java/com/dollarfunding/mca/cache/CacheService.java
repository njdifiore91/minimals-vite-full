package com.dollarfunding.mca.cache;

import org.springframework.data.redis.core.RedisTemplate;

import java.time.Duration;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * Interface defining the core caching operations for the MCA application.
 * This interface provides a standardized API for cache interactions, abstracting the underlying cache implementation details.
 * It includes methods for get, set, delete, and exists operations, supporting both single values and collections,
 * with and without TTL specifications.
 */
public interface CacheService {

    /**
     * Gets a value from the cache.
     *
     * @param key The cache key
     * @param <T> The type of the value
     * @return The cached value, or null if not found
     */
    <T> T get(String key);

    /**
     * Gets a value from the cache, or computes it if not present.
     *
     * @param key      The cache key
     * @param supplier The supplier to compute the value if not in cache
     * @param <T>      The type of the value
     * @return The cached or computed value
     */
    <T> T getOrCompute(String key, Supplier<T> supplier);

    /**
     * Gets a value from the cache, or computes it if not present, with a custom TTL.
     *
     * @param key      The cache key
     * @param supplier The supplier to compute the value if not in cache
     * @param ttl      The time-to-live duration for the cached value
     * @param <T>      The type of the value
     * @return The cached or computed value
     */
    <T> T getOrCompute(String key, Supplier<T> supplier, Duration ttl);

    /**
     * Sets a value in the cache with the default application data TTL.
     *
     * @param key   The cache key
     * @param value The value to cache
     * @param <T>   The type of the value
     * @return true if successful, false otherwise
     */
    <T> boolean set(String key, T value);

    /**
     * Sets a value in the cache with a custom TTL.
     *
     * @param key   The cache key
     * @param value The value to cache
     * @param ttl   The time-to-live duration for the cached value
     * @param <T>   The type of the value
     * @return true if successful, false otherwise
     */
    <T> boolean set(String key, T value, Duration ttl);

    /**
     * Sets multiple values in the cache with the default application data TTL.
     *
     * @param keyValueMap The map of keys to values to cache
     * @param <T>         The type of the values
     * @return true if successful, false otherwise
     */
    <T> boolean setAll(Map<String, T> keyValueMap);

    /**
     * Sets multiple values in the cache with a custom TTL.
     *
     * @param keyValueMap The map of keys to values to cache
     * @param ttl         The time-to-live duration for the cached values
     * @param <T>         The type of the values
     * @return true if successful, false otherwise
     */
    <T> boolean setAll(Map<String, T> keyValueMap, Duration ttl);

    /**
     * Deletes a value from the cache.
     *
     * @param key The cache key to delete
     * @return true if successful, false otherwise
     */
    boolean delete(String key);

    /**
     * Deletes multiple values from the cache.
     *
     * @param keys The collection of cache keys to delete
     * @return The number of keys that were deleted
     */
    long deleteAll(Collection<String> keys);

    /**
     * Deletes all keys matching a pattern.
     *
     * @param pattern The pattern to match keys against
     * @return The number of keys that were deleted
     */
    long deleteByPattern(String pattern);

    /**
     * Checks if a key exists in the cache.
     *
     * @param key The cache key to check
     * @return true if the key exists, false otherwise
     */
    boolean exists(String key);

    /**
     * Gets the remaining time-to-live for a key.
     *
     * @param key The cache key
     * @return The remaining TTL in milliseconds, or -1 if the key does not exist or has no TTL
     */
    long getTimeToLive(String key);

    /**
     * Updates the time-to-live for a key.
     *
     * @param key The cache key
     * @param ttl The new time-to-live duration
     * @return true if successful, false otherwise
     */
    boolean updateTimeToLive(String key, Duration ttl);

    /**
     * Increments a counter in the cache.
     *
     * @param key       The cache key
     * @param increment The amount to increment by
     * @return The new value, or -1 if the operation failed
     */
    long increment(String key, long increment);

    /**
     * Decrements a counter in the cache.
     *
     * @param key       The cache key
     * @param decrement The amount to decrement by
     * @return The new value, or -1 if the operation failed
     */
    long decrement(String key, long decrement);

    /**
     * Gets multiple values from the cache.
     *
     * @param keys The collection of cache keys
     * @param <T>  The type of the values
     * @return A list of values in the same order as the keys
     */
    <T> List<T> multiGet(Collection<String> keys);

    /**
     * Gets the Redis template for direct access to Redis operations.
     * This should be used with caution and only for operations not covered by the standard methods.
     *
     * @return The RedisTemplate instance
     */
    RedisTemplate<String, Object> getRedisTemplate();

    /**
     * Executes a cache operation with fallback to a supplier if the cache operation fails.
     * This is a utility method for implementing resilient cache operations.
     *
     * @param cacheOperation The cache operation to execute
     * @param fallback       The fallback supplier to use if the cache operation fails
     * @param <T>            The type of the result
     * @return The result of the cache operation or fallback
     */
    <T> T executeWithFallback(Supplier<T> cacheOperation, Supplier<T> fallback);
}