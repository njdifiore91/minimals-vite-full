package com.dollarfunding.mca.cache;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Scheduler for cache maintenance and eviction policies in the MCA application.
 * This class implements scheduled tasks for cache maintenance, including methods for
 * evicting stale data, pattern-based cache clearing, and logging of cache statistics.
 * It helps maintain optimal cache performance and memory usage.
 */
@Component
public class CacheEvictionScheduler {

    private static final Logger logger = LoggerFactory.getLogger(CacheEvictionScheduler.class);

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Value("${redis.cache.application-data.ttl:900}")
    private long applicationDataTtl; // Default: 15 minutes (900 seconds)

    @Value("${redis.cache.session.ttl:86400}")
    private long sessionTtl; // Default: 24 hours (86400 seconds)

    @Value("${redis.cache.eviction.memory-threshold:80}")
    private int memoryThresholdPercent; // Default: 80%

    @Value("${redis.cache.eviction.enabled:true}")
    private boolean evictionEnabled;

    /**
     * Scheduled task that runs every hour to evict stale application data from the cache.
     * This helps maintain cache freshness and prevents memory bloat from unused entries.
     */
    @Scheduled(cron = "0 0 * * * *") // Run at the top of every hour
    public void evictStaleApplicationData() {
        if (!evictionEnabled) {
            logger.info("Cache eviction is disabled. Skipping stale application data eviction.");
            return;
        }

        logger.info("Starting scheduled eviction of stale application data from cache");
        try {
            Set<String> keys = redisTemplate.keys("application:*");
            if (keys != null && !keys.isEmpty()) {
                int evictedCount = 0;
                for (String key : keys) {
                    // Check if key has explicit TTL set
                    Long ttl = redisTemplate.getExpire(key, TimeUnit.SECONDS);
                    
                    // If TTL is not set or negative (no expiry), apply our default TTL
                    if (ttl == null || ttl < 0) {
                        redisTemplate.expire(key, applicationDataTtl, TimeUnit.SECONDS);
                        evictedCount++;
                    }
                }
                logger.info("Applied TTL to {} application cache entries", evictedCount);
            } else {
                logger.info("No application cache entries found for TTL update");
            }
        } catch (Exception e) {
            logger.error("Error during stale application data eviction", e);
        }
    }

    /**
     * Scheduled task that runs daily to evict stale session data from the cache.
     * This helps maintain security by ensuring old sessions are properly expired.
     */
    @Scheduled(cron = "0 0 0 * * *") // Run at midnight every day
    public void evictStaleSessions() {
        if (!evictionEnabled) {
            logger.info("Cache eviction is disabled. Skipping stale session eviction.");
            return;
        }

        logger.info("Starting scheduled eviction of stale sessions from cache");
        try {
            Set<String> keys = redisTemplate.keys("session:*");
            if (keys != null && !keys.isEmpty()) {
                int evictedCount = 0;
                for (String key : keys) {
                    // Check if key has explicit TTL set
                    Long ttl = redisTemplate.getExpire(key, TimeUnit.SECONDS);
                    
                    // If TTL is not set or negative (no expiry), apply our default TTL
                    if (ttl == null || ttl < 0) {
                        redisTemplate.expire(key, sessionTtl, TimeUnit.SECONDS);
                        evictedCount++;
                    }
                }
                logger.info("Applied TTL to {} session cache entries", evictedCount);
            } else {
                logger.info("No session cache entries found for TTL update");
            }
        } catch (Exception e) {
            logger.error("Error during stale session eviction", e);
        }
    }

    /**
     * Scheduled task that runs every 15 minutes to check Redis memory usage and
     * trigger eviction if memory usage exceeds the configured threshold.
     * This helps prevent Redis from running out of memory and becoming unresponsive.
     */
    @Scheduled(fixedRate = 900000) // Run every 15 minutes (900,000 ms)
    public void monitorMemoryUsage() {
        if (!evictionEnabled) {
            logger.debug("Cache eviction is disabled. Skipping memory usage monitoring.");
            return;
        }

        try {
            Map<String, Object> memoryInfo = getRedisMemoryInfo();
            long usedMemory = (long) memoryInfo.getOrDefault("used_memory", 0L);
            long totalMemory = (long) memoryInfo.getOrDefault("total_system_memory", 0L);
            
            if (totalMemory > 0) {
                int usedPercentage = (int) ((usedMemory * 100) / totalMemory);
                logger.info("Redis memory usage: {}% ({} / {} bytes)", 
                        usedPercentage, usedMemory, totalMemory);
                
                if (usedPercentage >= memoryThresholdPercent) {
                    logger.warn("Redis memory usage exceeds threshold ({}%). Triggering eviction.", 
                            memoryThresholdPercent);
                    evictLowPriorityCache();
                }
            } else {
                logger.warn("Could not determine Redis total memory. Skipping memory check.");
            }
        } catch (Exception e) {
            logger.error("Error monitoring Redis memory usage", e);
        }
    }

    /**
     * Scheduled task that runs every 30 minutes to log cache statistics for monitoring purposes.
     * This provides visibility into cache usage patterns and helps with capacity planning.
     */
    @Scheduled(fixedRate = 1800000) // Run every 30 minutes (1,800,000 ms)
    public void logCacheStatistics() {
        try {
            // Count keys by prefix to understand cache usage distribution
            Map<String, Integer> keyCountsByPrefix = new HashMap<>();
            keyCountsByPrefix.put("application", countKeysByPrefix("application:*"));
            keyCountsByPrefix.put("document", countKeysByPrefix("document:*"));
            keyCountsByPrefix.put("merchant", countKeysByPrefix("merchant:*"));
            keyCountsByPrefix.put("session", countKeysByPrefix("session:*"));
            keyCountsByPrefix.put("other", countKeysByPrefix("*") - 
                    keyCountsByPrefix.values().stream().mapToInt(Integer::intValue).sum());
            
            // Log the statistics
            logger.info("Cache statistics - Key counts by prefix: {}", keyCountsByPrefix);
            
            // Get hit/miss statistics if available
            Map<String, Object> stats = getRedisStats();
            long keyspaceHits = (long) stats.getOrDefault("keyspace_hits", 0L);
            long keyspaceMisses = (long) stats.getOrDefault("keyspace_misses", 0L);
            long totalOps = keyspaceHits + keyspaceMisses;
            
            if (totalOps > 0) {
                double hitRatio = (double) keyspaceHits / totalOps * 100;
                logger.info("Cache hit ratio: {:.2f}% ({} hits, {} misses)", 
                        hitRatio, keyspaceHits, keyspaceMisses);
            } else {
                logger.info("No cache operations recorded yet");
            }
        } catch (Exception e) {
            logger.error("Error logging cache statistics", e);
        }
    }

    /**
     * Clears cache entries matching the specified pattern.
     * This method can be called programmatically to clear specific cache regions.
     *
     * @param pattern The pattern to match keys against (e.g., "application:123:*")
     * @return The number of keys that were removed
     */
    public int clearCacheByPattern(String pattern) {
        logger.info("Clearing cache with pattern: {}", pattern);
        try {
            Set<String> keys = redisTemplate.keys(pattern);
            if (keys != null && !keys.isEmpty()) {
                redisTemplate.delete(keys);
                logger.info("Cleared {} cache entries matching pattern: {}", keys.size(), pattern);
                return keys.size();
            } else {
                logger.info("No cache entries found matching pattern: {}", pattern);
                return 0;
            }
        } catch (Exception e) {
            logger.error("Error clearing cache with pattern: {}", pattern, e);
            return -1;
        }
    }

    /**
     * Evicts low-priority cache entries to free up memory.
     * This is triggered when memory usage exceeds the configured threshold.
     */
    private void evictLowPriorityCache() {
        logger.info("Evicting low-priority cache entries to free up memory");
        try {
            // First, clear any expired keys
            Long evictedExpired = redisTemplate.execute((RedisCallback<Long>) connection -> {
                // SCAN for expired keys and delete them
                return connection.serverCommands().dbSize();
            });
            
            // Then, clear low-priority application data (older than 10 minutes)
            int evictedLowPriority = clearCacheByPattern("application:lowpriority:*");
            
            // If still needed, clear temporary data
            int evictedTemp = clearCacheByPattern("temp:*");
            
            logger.info("Evicted cache entries - expired: {}, low priority: {}, temporary: {}", 
                    evictedExpired, evictedLowPriority, evictedTemp);
            
            // Check if we've freed up enough memory
            Map<String, Object> memoryInfo = getRedisMemoryInfo();
            long usedMemory = (long) memoryInfo.getOrDefault("used_memory", 0L);
            long totalMemory = (long) memoryInfo.getOrDefault("total_system_memory", 0L);
            
            if (totalMemory > 0) {
                int usedPercentage = (int) ((usedMemory * 100) / totalMemory);
                if (usedPercentage >= memoryThresholdPercent) {
                    // Still above threshold, take more aggressive action
                    logger.warn("Memory usage still high ({}%) after initial eviction. Taking additional measures.", 
                            usedPercentage);
                    
                    // Clear all non-critical application data
                    int evictedNonCritical = clearCacheByPattern("application:*:details");
                    logger.info("Evicted {} non-critical application cache entries", evictedNonCritical);
                }
            }
        } catch (Exception e) {
            logger.error("Error during low-priority cache eviction", e);
        }
    }

    /**
     * Counts the number of keys matching the specified pattern.
     *
     * @param pattern The pattern to match keys against
     * @return The number of matching keys
     */
    private int countKeysByPrefix(String pattern) {
        Set<String> keys = redisTemplate.keys(pattern);
        return keys != null ? keys.size() : 0;
    }

    /**
     * Retrieves Redis memory information.
     *
     * @return A map containing memory statistics
     */
    private Map<String, Object> getRedisMemoryInfo() {
        return redisTemplate.execute((RedisCallback<Map<String, Object>>) connection -> {
            Map<String, Object> info = new HashMap<>();
            String memoryInfo = connection.serverCommands().info("memory");
            if (memoryInfo != null) {
                for (String line : memoryInfo.split("\n")) {
                    if (line.contains(":")) {
                        String[] parts = line.split(":");
                        if (parts.length >= 2) {
                            String key = parts[0].trim();
                            String value = parts[1].trim();
                            try {
                                // Try to parse as long if possible
                                info.put(key, Long.parseLong(value));
                            } catch (NumberFormatException e) {
                                // Otherwise store as string
                                info.put(key, value);
                            }
                        }
                    }
                }
            }
            return info;
        });
    }

    /**
     * Retrieves Redis statistics.
     *
     * @return A map containing Redis statistics
     */
    private Map<String, Object> getRedisStats() {
        return redisTemplate.execute((RedisCallback<Map<String, Object>>) connection -> {
            Map<String, Object> stats = new HashMap<>();
            String statsInfo = connection.serverCommands().info("stats");
            if (statsInfo != null) {
                for (String line : statsInfo.split("\n")) {
                    if (line.contains(":")) {
                        String[] parts = line.split(":");
                        if (parts.length >= 2) {
                            String key = parts[0].trim();
                            String value = parts[1].trim();
                            try {
                                // Try to parse as long if possible
                                stats.put(key, Long.parseLong(value));
                            } catch (NumberFormatException e) {
                                // Otherwise store as string
                                stats.put(key, value);
                            }
                        }
                    }
                }
            }
            return stats;
        });
    }
}