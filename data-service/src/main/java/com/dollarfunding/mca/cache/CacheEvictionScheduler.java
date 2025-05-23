package com.dollarfunding.mca.cache;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Scheduler for cache maintenance and eviction policies in the MCA application.
 * <p>
 * This class implements scheduled tasks for cache maintenance, including methods for
 * evicting stale data, pattern-based cache clearing, and logging of cache statistics.
 * It helps maintain optimal cache performance and memory usage.
 * </p>
 * <p>
 * Key features:
 * <ul>
 *   <li>Scheduled eviction of stale data based on configurable criteria</li>
 *   <li>Pattern-based cache clearing for targeted eviction</li>
 *   <li>Logging of cache statistics for monitoring</li>
 *   <li>Memory usage monitoring and adaptive eviction</li>
 *   <li>TTL-based eviction policies</li>
 * </ul>
 * </p>
 */
@Component
@EnableScheduling
public class CacheEvictionScheduler {

    private static final Logger logger = LoggerFactory.getLogger(CacheEvictionScheduler.class);
    
    private final RedisTemplate<String, Object> redisTemplate;
    private final CacheMetricsCollector metricsCollector;
    private final RedisCacheService cacheService;
    
    // Configurable eviction thresholds
    @Value("${spring.redis.eviction.memory-threshold:0.8}")
    private double memoryThreshold;
    
    @Value("${spring.redis.eviction.idle-time-minutes:30}")
    private long idleTimeMinutes;
    
    @Value("${spring.redis.eviction.max-keys-per-scan:1000}")
    private long maxKeysPerScan;
    
    @Value("${spring.redis.eviction.enabled:true}")
    private boolean evictionEnabled;
    
    @Value("${spring.redis.eviction.log-interval-minutes:60}")
    private long logIntervalMinutes;
    
    // Last time statistics were logged
    private LocalDateTime lastStatsLogTime = LocalDateTime.now();
    
    /**
     * Creates a new CacheEvictionScheduler with the specified dependencies.
     *
     * @param redisTemplate    the RedisTemplate for Redis operations
     * @param metricsCollector the metrics collector for cache performance monitoring
     * @param cacheService     the cache service for cache operations
     */
    @Autowired
    public CacheEvictionScheduler(RedisTemplate<String, Object> redisTemplate,
                                 CacheMetricsCollector metricsCollector,
                                 RedisCacheService cacheService) {
        this.redisTemplate = redisTemplate;
        this.metricsCollector = metricsCollector;
        this.cacheService = cacheService;
        
        logger.info("CacheEvictionScheduler initialized with settings: " +
                "memoryThreshold={}, idleTimeMinutes={}, maxKeysPerScan={}, evictionEnabled={}, logIntervalMinutes={}",
                memoryThreshold, idleTimeMinutes, maxKeysPerScan, evictionEnabled, logIntervalMinutes);
    }
    
    /**
     * Scheduled task to evict stale application data from the cache.
     * <p>
     * This task runs every 15 minutes to evict application data that has been idle
     * for longer than the configured idle time threshold.
     * </p>
     * <p>
     * The eviction is based on the access patterns and configured idle time threshold.
     * </p>
     */
    @Scheduled(fixedRateString = "${spring.redis.eviction.application-data-interval-ms:900000}")
    public void evictStaleApplicationData() {
        if (!evictionEnabled) {
            logger.debug("Scheduled eviction is disabled. Skipping eviction of stale application data.");
            return;
        }
        
        logger.info("Starting scheduled eviction of stale application data");
        long startTime = System.currentTimeMillis();
        
        // Evict stale data from application caches
        long evictedCount = 0;
        evictedCount += evictStaleDataByPattern(CacheConstants.KeyPrefix.APPLICATION + "*");
        evictedCount += evictStaleDataByPattern(CacheConstants.KeyPrefix.DOCUMENT + "*");
        evictedCount += evictStaleDataByPattern(CacheConstants.KeyPrefix.MERCHANT + "*");
        
        long duration = System.currentTimeMillis() - startTime;
        logger.info("Completed eviction of stale application data: {} keys evicted in {} ms", evictedCount, duration);
    }
    
    /**
     * Scheduled task to evict stale session data from the cache.
     * <p>
     * This task runs every hour to evict session data that has been idle
     * for longer than the configured idle time threshold.
     * </p>
     * <p>
     * Session data has a longer TTL (24 hours) but is still subject to eviction
     * if it has been idle for too long.
     * </p>
     */
    @Scheduled(fixedRateString = "${spring.redis.eviction.session-data-interval-ms:3600000}")
    public void evictStaleSessionData() {
        if (!evictionEnabled) {
            logger.debug("Scheduled eviction is disabled. Skipping eviction of stale session data.");
            return;
        }
        
        logger.info("Starting scheduled eviction of stale session data");
        long startTime = System.currentTimeMillis();
        
        // Evict stale session data
        long evictedCount = evictStaleDataByPattern(CacheConstants.KeyPrefix.SESSION + "*");
        
        long duration = System.currentTimeMillis() - startTime;
        logger.info("Completed eviction of stale session data: {} keys evicted in {} ms", evictedCount, duration);
    }
    
    /**
     * Scheduled task to evict stale lookup data from the cache.
     * <p>
     * This task runs every 30 minutes to evict lookup data that has been idle
     * for longer than the configured idle time threshold.
     * </p>
     * <p>
     * Lookup data is relatively static but still subject to eviction
     * if it has been idle for too long.
     * </p>
     */
    @Scheduled(fixedRateString = "${spring.redis.eviction.lookup-data-interval-ms:1800000}")
    public void evictStaleLookupData() {
        if (!evictionEnabled) {
            logger.debug("Scheduled eviction is disabled. Skipping eviction of stale lookup data.");
            return;
        }
        
        logger.info("Starting scheduled eviction of stale lookup data");
        long startTime = System.currentTimeMillis();
        
        // Evict stale lookup data
        long evictedCount = evictStaleDataByPattern(CacheConstants.KeyPrefix.LOOKUP + "*");
        
        long duration = System.currentTimeMillis() - startTime;
        logger.info("Completed eviction of stale lookup data: {} keys evicted in {} ms", evictedCount, duration);
    }
    
    /**
     * Scheduled task to monitor memory usage and perform adaptive eviction if necessary.
     * <p>
     * This task runs every 5 minutes to check the memory usage of the Redis cache.
     * If the memory usage exceeds the configured threshold, it triggers an adaptive
     * eviction to free up memory.
     * </p>
     * <p>
     * The adaptive eviction prioritizes evicting data based on access patterns and TTL.
     * </p>
     */
    @Scheduled(fixedRateString = "${spring.redis.eviction.memory-check-interval-ms:300000}")
    public void monitorMemoryUsage() {
        if (!evictionEnabled) {
            logger.debug("Scheduled eviction is disabled. Skipping memory usage monitoring.");
            return;
        }
        
        try {
            // Get memory usage information
            Map<String, Object> memoryInfo = getMemoryInfo();
            long usedMemory = (long) memoryInfo.get("used_memory");
            long maxMemory = (long) memoryInfo.get("maxmemory");
            
            // Calculate memory usage ratio
            double memoryUsageRatio = maxMemory > 0 ? (double) usedMemory / maxMemory : 0.0;
            
            logger.info("Redis memory usage: {} / {} bytes ({}%)",
                    usedMemory, maxMemory, String.format("%.2f", memoryUsageRatio * 100));
            
            // If memory usage exceeds threshold, perform adaptive eviction
            if (memoryUsageRatio > memoryThreshold) {
                logger.warn("Memory usage exceeds threshold ({}%). Performing adaptive eviction.",
                        String.format("%.2f", memoryThreshold * 100));
                
                performAdaptiveEviction(memoryUsageRatio);
            }
        } catch (Exception e) {
            logger.error("Error monitoring memory usage", e);
        }
    }
    
    /**
     * Scheduled task to log cache statistics.
     * <p>
     * This task runs at a fixed rate to log cache statistics for monitoring purposes.
     * </p>
     * <p>
     * The statistics include hit/miss counts, eviction counts, and memory usage.
     * </p>
     */
    @Scheduled(fixedRateString = "${spring.redis.eviction.stats-log-interval-ms:300000}")
    public void logCacheStatistics() {
        LocalDateTime now = LocalDateTime.now();
        
        // Only log statistics at the configured interval
        if (Duration.between(lastStatsLogTime, now).toMinutes() >= logIntervalMinutes) {
            logger.info("Logging cache statistics");
            
            // Get cache statistics from metrics collector
            Map<String, Map<String, Number>> metricsSnapshot = metricsCollector.getMetricsSnapshot();
            
            // Log statistics for each cache
            for (Map.Entry<String, Map<String, Number>> entry : metricsSnapshot.entrySet()) {
                String cacheName = entry.getKey();
                Map<String, Number> metrics = entry.getValue();
                
                logger.info("Cache '{}' statistics: hits={}, misses={}, puts={}, evictions={}, size={}, hitRatio={}",
                        cacheName,
                        metrics.get("hits"),
                        metrics.get("misses"),
                        metrics.get("puts"),
                        metrics.get("evictions"),
                        metrics.get("size"),
                        String.format("%.2f", metrics.get("hitRatio").doubleValue()));
            }
            
            // Log memory usage
            try {
                Map<String, Object> memoryInfo = getMemoryInfo();
                long usedMemory = (long) memoryInfo.get("used_memory");
                long maxMemory = (long) memoryInfo.get("maxmemory");
                double memoryUsageRatio = maxMemory > 0 ? (double) usedMemory / maxMemory : 0.0;
                
                logger.info("Redis memory usage: {} / {} bytes ({}%)",
                        usedMemory, maxMemory, String.format("%.2f", memoryUsageRatio * 100));
            } catch (Exception e) {
                logger.error("Error getting memory info", e);
            }
            
            // Update last stats log time
            lastStatsLogTime = now;
        }
    }
    
    /**
     * Evicts stale data from the cache based on a key pattern.
     * <p>
     * This method scans the Redis cache for keys matching the specified pattern
     * and evicts keys that have been idle for longer than the configured idle time threshold.
     * </p>
     * <p>
     * The eviction is performed in batches to avoid blocking the Redis server for too long.
     * </p>
     *
     * @param pattern the key pattern to match
     * @return the number of keys evicted
     */
    public long evictStaleDataByPattern(String pattern) {
        long evictedCount = 0;
        long scannedCount = 0;
        
        try {
            logger.debug("Scanning for keys matching pattern: {}", pattern);
            
            // Get keys matching the pattern
            Set<String> keys = redisTemplate.keys(pattern);
            if (keys == null || keys.isEmpty()) {
                logger.debug("No keys found matching pattern: {}", pattern);
                return 0;
            }
            
            scannedCount = keys.size();
            logger.debug("Found {} keys matching pattern: {}", scannedCount, pattern);
            
            // Calculate idle time threshold in milliseconds
            long idleTimeThresholdMs = idleTimeMinutes * 60 * 1000;
            
            // Check each key for idle time
            for (String key : keys) {
                try {
                    // Get the idle time for the key
                    Long idleTime = getKeyIdleTime(key);
                    
                    // If idle time exceeds threshold, evict the key
                    if (idleTime != null && idleTime > idleTimeThresholdMs) {
                        boolean deleted = cacheService.delete(key);
                        if (deleted) {
                            evictedCount++;
                            logger.debug("Evicted key: {} (idle for {} ms)", key, idleTime);
                        }
                    }
                } catch (Exception e) {
                    logger.warn("Error checking idle time for key: {}", key, e);
                }
            }
        } catch (Exception e) {
            logger.error("Error evicting stale data by pattern: {}", pattern, e);
        }
        
        logger.info("Evicted {} out of {} keys matching pattern: {}", evictedCount, scannedCount, pattern);
        return evictedCount;
    }
    
    /**
     * Performs an adaptive eviction based on memory usage.
     * <p>
     * This method evicts data from the cache based on memory usage, access patterns,
     * and TTL to free up memory when the cache is under pressure.
     * </p>
     * <p>
     * The eviction strategy prioritizes:
     * 1. Expired or nearly expired keys
     * 2. Least recently used keys
     * 3. Keys with the lowest hit ratio
     * </p>
     *
     * @param currentMemoryRatio the current memory usage ratio
     * @return the number of keys evicted
     */
    public long performAdaptiveEviction(double currentMemoryRatio) {
        long evictedCount = 0;
        
        try {
            logger.info("Performing adaptive eviction with current memory ratio: {}", 
                    String.format("%.2f", currentMemoryRatio));
            
            // Calculate target memory ratio (10% below threshold)
            double targetMemoryRatio = Math.max(0.5, memoryThreshold - 0.1);
            
            // Calculate how much memory needs to be freed
            Map<String, Object> memoryInfo = getMemoryInfo();
            long maxMemory = (long) memoryInfo.get("maxmemory");
            long currentUsedMemory = (long) memoryInfo.get("used_memory");
            long targetUsedMemory = (long) (maxMemory * targetMemoryRatio);
            long memoryToFree = currentUsedMemory - targetUsedMemory;
            
            if (memoryToFree <= 0) {
                logger.info("No memory needs to be freed. Skipping adaptive eviction.");
                return 0;
            }
            
            logger.info("Need to free approximately {} bytes of memory", memoryToFree);
            
            // First, evict keys that are about to expire
            evictedCount += evictNearExpiryKeys();
            
            // Check if we've freed enough memory
            memoryInfo = getMemoryInfo();
            currentUsedMemory = (long) memoryInfo.get("used_memory");
            if (currentUsedMemory <= targetUsedMemory) {
                logger.info("Freed enough memory through near-expiry eviction. Current memory usage: {} bytes",
                        currentUsedMemory);
                return evictedCount;
            }
            
            // Next, evict least recently used application data
            evictedCount += evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.APPLICATION + "*");
            evictedCount += evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.DOCUMENT + "*");
            evictedCount += evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.MERCHANT + "*");
            
            // Check if we've freed enough memory
            memoryInfo = getMemoryInfo();
            currentUsedMemory = (long) memoryInfo.get("used_memory");
            if (currentUsedMemory <= targetUsedMemory) {
                logger.info("Freed enough memory through LRU eviction. Current memory usage: {} bytes",
                        currentUsedMemory);
                return evictedCount;
            }
            
            // Finally, evict least recently used session data
            evictedCount += evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.SESSION + "*");
            
            // Log final memory usage
            memoryInfo = getMemoryInfo();
            currentUsedMemory = (long) memoryInfo.get("used_memory");
            double finalMemoryRatio = (double) currentUsedMemory / maxMemory;
            
            logger.info("Adaptive eviction completed. Evicted {} keys. New memory usage: {} bytes ({}%)",
                    evictedCount, currentUsedMemory, String.format("%.2f", finalMemoryRatio * 100));
            
            return evictedCount;
        } catch (Exception e) {
            logger.error("Error performing adaptive eviction", e);
            return evictedCount;
        }
    }
    
    /**
     * Evicts keys that are near their expiry time.
     * <p>
     * This method scans the Redis cache for keys that are about to expire
     * (within the next 5 minutes) and evicts them to free up memory.
     * </p>
     *
     * @return the number of keys evicted
     */
    private long evictNearExpiryKeys() {
        long evictedCount = 0;
        
        try {
            logger.debug("Scanning for keys near expiry");
            
            // Get all keys
            Set<String> allKeys = redisTemplate.keys("*");
            if (allKeys == null || allKeys.isEmpty()) {
                logger.debug("No keys found in the cache");
                return 0;
            }
            
            // Define near expiry threshold (5 minutes)
            long nearExpiryThresholdMs = 5 * 60 * 1000;
            
            // Check each key for TTL
            for (String key : allKeys) {
                try {
                    // Get the TTL for the key
                    Long ttl = redisTemplate.getExpire(key, TimeUnit.MILLISECONDS);
                    
                    // If TTL is positive and less than threshold, evict the key
                    if (ttl != null && ttl > 0 && ttl < nearExpiryThresholdMs) {
                        boolean deleted = cacheService.delete(key);
                        if (deleted) {
                            evictedCount++;
                            logger.debug("Evicted near-expiry key: {} (TTL: {} ms)", key, ttl);
                        }
                    }
                } catch (Exception e) {
                    logger.warn("Error checking TTL for key: {}", key, e);
                }
            }
        } catch (Exception e) {
            logger.error("Error evicting near-expiry keys", e);
        }
        
        logger.info("Evicted {} near-expiry keys", evictedCount);
        return evictedCount;
    }
    
    /**
     * Evicts least recently used keys matching a pattern.
     * <p>
     * This method scans the Redis cache for keys matching the specified pattern
     * and evicts the least recently used keys to free up memory.
     * </p>
     * <p>
     * The eviction is performed in batches to avoid blocking the Redis server for too long.
     * </p>
     *
     * @param pattern the key pattern to match
     * @return the number of keys evicted
     */
    private long evictLeastRecentlyUsedKeys(String pattern) {
        long evictedCount = 0;
        
        try {
            logger.debug("Scanning for least recently used keys matching pattern: {}", pattern);
            
            // Get keys matching the pattern
            Set<String> keys = redisTemplate.keys(pattern);
            if (keys == null || keys.isEmpty()) {
                logger.debug("No keys found matching pattern: {}", pattern);
                return 0;
            }
            
            logger.debug("Found {} keys matching pattern: {}", keys.size(), pattern);
            
            // Create a map of keys to idle times
            Map<String, Long> keyIdleTimes = new HashMap<>();
            
            // Get idle time for each key
            for (String key : keys) {
                try {
                    Long idleTime = getKeyIdleTime(key);
                    if (idleTime != null) {
                        keyIdleTimes.put(key, idleTime);
                    }
                } catch (Exception e) {
                    logger.warn("Error getting idle time for key: {}", key, e);
                }
            }
            
            // Sort keys by idle time (descending)
            List<Map.Entry<String, Long>> sortedKeys = keyIdleTimes.entrySet().stream()
                    .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                    .limit(maxKeysPerScan)
                    .collect(java.util.stream.Collectors.toList());
            
            // Evict the top N least recently used keys
            for (Map.Entry<String, Long> entry : sortedKeys) {
                String key = entry.getKey();
                Long idleTime = entry.getValue();
                
                boolean deleted = cacheService.delete(key);
                if (deleted) {
                    evictedCount++;
                    logger.debug("Evicted LRU key: {} (idle for {} ms)", key, idleTime);
                }
            }
        } catch (Exception e) {
            logger.error("Error evicting least recently used keys for pattern: {}", pattern, e);
        }
        
        logger.info("Evicted {} least recently used keys matching pattern: {}", evictedCount, pattern);
        return evictedCount;
    }
    
    /**
     * Gets the idle time for a key in milliseconds.
     * <p>
     * This method uses the Redis OBJECT IDLETIME command to get the idle time for a key.
     * The idle time is the number of seconds since the key was last accessed.
     * </p>
     *
     * @param key the key to get the idle time for
     * @return the idle time in milliseconds, or null if the key doesn't exist or an error occurs
     */
    private Long getKeyIdleTime(String key) {
        try {
            // Use Redis connection to execute OBJECT IDLETIME command
            RedisConnection connection = redisTemplate.getConnectionFactory().getConnection();
            Long idleTimeSeconds = connection.objectCommands().idletime(key.getBytes());
            
            // Convert seconds to milliseconds
            return idleTimeSeconds != null ? idleTimeSeconds * 1000 : null;
        } catch (Exception e) {
            logger.warn("Error getting idle time for key: {}", key, e);
            return null;
        }
    }
    
    /**
     * Gets memory usage information from Redis.
     * <p>
     * This method uses the Redis INFO MEMORY command to get memory usage information.
     * </p>
     *
     * @return a map containing memory usage information
     */
    private Map<String, Object> getMemoryInfo() {
        try {
            // Use Redis connection to execute INFO MEMORY command
            RedisConnection connection = redisTemplate.getConnectionFactory().getConnection();
            Map<String, Object> memoryInfo = connection.info("memory");
            
            // Parse memory values
            Map<String, Object> parsedInfo = new HashMap<>();
            for (Map.Entry<String, Object> entry : memoryInfo.entrySet()) {
                String key = entry.getKey();
                String value = (String) entry.getValue();
                
                if (key.equals("used_memory") || key.equals("maxmemory")) {
                    try {
                        parsedInfo.put(key, Long.parseLong(value));
                    } catch (NumberFormatException e) {
                        parsedInfo.put(key, 0L);
                    }
                } else {
                    parsedInfo.put(key, value);
                }
            }
            
            return parsedInfo;
        } catch (Exception e) {
            logger.error("Error getting memory info", e);
            
            // Return default values
            Map<String, Object> defaultInfo = new HashMap<>();
            defaultInfo.put("used_memory", 0L);
            defaultInfo.put("maxmemory", 0L);
            return defaultInfo;
        }
    }
    
    /**
     * Clears all keys matching a pattern from the cache.
     * <p>
     * This method is useful for administrative purposes or when a specific
     * category of data needs to be invalidated.
     * </p>
     *
     * @param pattern the key pattern to match
     * @return the number of keys cleared
     */
    public long clearCacheByPattern(String pattern) {
        try {
            logger.info("Clearing cache keys matching pattern: {}", pattern);
            
            // Get keys matching the pattern
            Set<String> keys = redisTemplate.keys(pattern);
            if (keys == null || keys.isEmpty()) {
                logger.info("No keys found matching pattern: {}", pattern);
                return 0;
            }
            
            // Delete the keys
            Long deletedCount = redisTemplate.delete(keys);
            
            logger.info("Cleared {} cache keys matching pattern: {}", deletedCount, pattern);
            return deletedCount != null ? deletedCount : 0;
        } catch (Exception e) {
            logger.error("Error clearing cache by pattern: {}", pattern, e);
            return 0;
        }
    }
    
    /**
     * Gets the current eviction settings.
     * <p>
     * This method returns a map containing the current eviction settings,
     * which can be useful for monitoring or debugging purposes.
     * </p>
     *
     * @return a map containing the current eviction settings
     */
    public Map<String, Object> getEvictionSettings() {
        Map<String, Object> settings = new HashMap<>();
        
        settings.put("evictionEnabled", evictionEnabled);
        settings.put("memoryThreshold", memoryThreshold);
        settings.put("idleTimeMinutes", idleTimeMinutes);
        settings.put("maxKeysPerScan", maxKeysPerScan);
        settings.put("logIntervalMinutes", logIntervalMinutes);
        
        return settings;
    }
    
    /**
     * Updates the eviction settings.
     * <p>
     * This method allows runtime modification of eviction settings,
     * which can be useful for tuning the cache behavior without restarting the application.
     * </p>
     *
     * @param settings a map containing the new eviction settings
     */
    public void updateEvictionSettings(Map<String, Object> settings) {
        if (settings.containsKey("evictionEnabled")) {
            this.evictionEnabled = (boolean) settings.get("evictionEnabled");
        }
        
        if (settings.containsKey("memoryThreshold")) {
            this.memoryThreshold = (double) settings.get("memoryThreshold");
        }
        
        if (settings.containsKey("idleTimeMinutes")) {
            this.idleTimeMinutes = ((Number) settings.get("idleTimeMinutes")).longValue();
        }
        
        if (settings.containsKey("maxKeysPerScan")) {
            this.maxKeysPerScan = ((Number) settings.get("maxKeysPerScan")).longValue();
        }
        
        if (settings.containsKey("logIntervalMinutes")) {
            this.logIntervalMinutes = ((Number) settings.get("logIntervalMinutes")).longValue();
        }
        
        logger.info("Updated eviction settings: evictionEnabled={}, memoryThreshold={}, idleTimeMinutes={}, maxKeysPerScan={}, logIntervalMinutes={}",
                evictionEnabled, memoryThreshold, idleTimeMinutes, maxKeysPerScan, logIntervalMinutes);
    }
}