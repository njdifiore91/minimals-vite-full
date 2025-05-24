package com.dollarfunding.mca.cache;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Interface defining the core caching operations for the MCA application.
 * This service provides a standardized API for cache interactions, abstracting
 * the underlying cache implementation details (Redis 7.0).
 * 
 * The cache is configured with the following TTL defaults:
 * - Application data: 15 minutes
 * - Session information: 24 hours
 */
public interface CacheService {
    
    /**
     * Default TTL for application data in seconds (15 minutes)
     */
    long DEFAULT_DATA_TTL_SECONDS = 15 * 60;
    
    /**
     * Default TTL for session data in seconds (24 hours)
     */
    long DEFAULT_SESSION_TTL_SECONDS = 24 * 60 * 60;
    
    /**
     * Retrieves a value from the cache by key.
     *
     * @param <T> The type of the value to retrieve
     * @param key The cache key
     * @param clazz The class type of the value
     * @return An Optional containing the value if found, empty otherwise
     */
    <T> Optional<T> get(String key, Class<T> clazz);
    
    /**
     * Retrieves multiple values from the cache by keys.
     *
     * @param <T> The type of the values to retrieve
     * @param keys Collection of cache keys
     * @param clazz The class type of the values
     * @return A Map of keys to values for all keys that exist in the cache
     */
    <T> Map<String, T> multiGet(Collection<String> keys, Class<T> clazz);
    
    /**
     * Stores a value in the cache with the default application data TTL (15 minutes).
     *
     * @param <T> The type of the value to store
     * @param key The cache key
     * @param value The value to store
     * @return true if the operation was successful, false otherwise
     */
    <T> boolean set(String key, T value);
    
    /**
     * Stores a value in the cache with a custom TTL.
     *
     * @param <T> The type of the value to store
     * @param key The cache key
     * @param value The value to store
     * @param ttl The time-to-live duration
     * @param timeUnit The time unit of the TTL duration
     * @return true if the operation was successful, false otherwise
     */
    <T> boolean set(String key, T value, long ttl, TimeUnit timeUnit);
    
    /**
     * Stores multiple key-value pairs in the cache with the default application data TTL (15 minutes).
     *
     * @param <T> The type of the values to store
     * @param map The map of key-value pairs to store
     * @return true if the operation was successful, false otherwise
     */
    <T> boolean multiSet(Map<String, T> map);
    
    /**
     * Stores multiple key-value pairs in the cache with a custom TTL.
     *
     * @param <T> The type of the values to store
     * @param map The map of key-value pairs to store
     * @param ttl The time-to-live duration
     * @param timeUnit The time unit of the TTL duration
     * @return true if the operation was successful, false otherwise
     */
    <T> boolean multiSet(Map<String, T> map, long ttl, TimeUnit timeUnit);
    
    /**
     * Deletes a value from the cache by key.
     *
     * @param key The cache key to delete
     * @return true if the key was deleted, false if the key didn't exist
     */
    boolean delete(String key);
    
    /**
     * Deletes multiple values from the cache by keys.
     *
     * @param keys Collection of cache keys to delete
     * @return The number of keys that were deleted
     */
    long multiDelete(Collection<String> keys);
    
    /**
     * Checks if a key exists in the cache.
     *
     * @param key The cache key to check
     * @return true if the key exists, false otherwise
     */
    boolean exists(String key);
    
    /**
     * Checks if multiple keys exist in the cache.
     *
     * @param keys Collection of cache keys to check
     * @return A Set containing the keys that exist in the cache
     */
    Set<String> multiExists(Collection<String> keys);
    
    /**
     * Atomically increments a counter stored at the given key.
     * If the key does not exist, it is initialized to 0 before performing the increment.
     *
     * @param key The cache key of the counter
     * @param delta The value to increment by
     * @return The new value of the counter after the increment
     */
    long increment(String key, long delta);
    
    /**
     * Atomically decrements a counter stored at the given key.
     * If the key does not exist, it is initialized to 0 before performing the decrement.
     *
     * @param key The cache key of the counter
     * @param delta The value to decrement by
     * @return The new value of the counter after the decrement
     */
    long decrement(String key, long delta);
    
    /**
     * Sets the expiration time for a key.
     *
     * @param key The cache key
     * @param ttl The time-to-live duration
     * @param timeUnit The time unit of the TTL duration
     * @return true if the expiration was set, false if the key doesn't exist
     */
    boolean expire(String key, long ttl, TimeUnit timeUnit);
    
    /**
     * Gets the remaining time-to-live for a key.
     *
     * @param key The cache key
     * @param timeUnit The time unit for the result
     * @return The remaining TTL in the specified time unit, or -1 if the key doesn't exist or has no TTL
     */
    long getExpire(String key, TimeUnit timeUnit);
    
    /**
     * Removes the expiration from a key, making it persist indefinitely.
     *
     * @param key The cache key
     * @return true if the operation was successful, false if the key doesn't exist
     */
    boolean persist(String key);
    
    /**
     * Adds a value to a list stored at the given key.
     * If the key does not exist, a new list is created.
     *
     * @param <T> The type of the value to add
     * @param key The cache key of the list
     * @param value The value to add to the list
     * @return The new size of the list after the addition
     */
    <T> long listAdd(String key, T value);
    
    /**
     * Retrieves all values from a list stored at the given key.
     *
     * @param <T> The type of the values in the list
     * @param key The cache key of the list
     * @param clazz The class type of the values
     * @return A List containing all values, or an empty list if the key doesn't exist
     */
    <T> List<T> listGetAll(String key, Class<T> clazz);
    
    /**
     * Adds a value to a set stored at the given key.
     * If the key does not exist, a new set is created.
     *
     * @param <T> The type of the value to add
     * @param key The cache key of the set
     * @param value The value to add to the set
     * @return true if the value was added, false if the value already existed
     */
    <T> boolean setAdd(String key, T value);
    
    /**
     * Retrieves all values from a set stored at the given key.
     *
     * @param <T> The type of the values in the set
     * @param key The cache key of the set
     * @param clazz The class type of the values
     * @return A Set containing all values, or an empty set if the key doesn't exist
     */
    <T> Set<T> setGetAll(String key, Class<T> clazz);
    
    /**
     * Adds a field-value pair to a hash stored at the given key.
     * If the key does not exist, a new hash is created.
     *
     * @param <T> The type of the value to add
     * @param key The cache key of the hash
     * @param field The field name within the hash
     * @param value The value to store
     * @return true if a new field was created, false if the field was updated
     */
    <T> boolean hashSet(String key, String field, T value);
    
    /**
     * Retrieves a value from a hash stored at the given key.
     *
     * @param <T> The type of the value to retrieve
     * @param key The cache key of the hash
     * @param field The field name within the hash
     * @param clazz The class type of the value
     * @return An Optional containing the value if found, empty otherwise
     */
    <T> Optional<T> hashGet(String key, String field, Class<T> clazz);
    
    /**
     * Retrieves all field-value pairs from a hash stored at the given key.
     *
     * @param <T> The type of the values in the hash
     * @param key The cache key of the hash
     * @param clazz The class type of the values
     * @return A Map containing all field-value pairs, or an empty map if the key doesn't exist
     */
    <T> Map<String, T> hashGetAll(String key, Class<T> clazz);
    
    /**
     * Deletes a field from a hash stored at the given key.
     *
     * @param key The cache key of the hash
     * @param field The field name within the hash to delete
     * @return true if the field was deleted, false if the field or key didn't exist
     */
    boolean hashDelete(String key, String field);
    
    /**
     * Clears all entries from the cache.
     * This operation should be used with caution and typically only in testing environments.
     *
     * @return true if the operation was successful, false otherwise
     */
    boolean clear();
}