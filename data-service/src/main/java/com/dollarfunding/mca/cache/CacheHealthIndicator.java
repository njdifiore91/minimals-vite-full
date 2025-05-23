package com.dollarfunding.mca.cache;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

/**
 * Health indicator for Redis cache monitoring in the MCA application.
 * <p>
 * This class implements Spring Boot's HealthIndicator interface to provide health checks
 * for the Redis connection, report cache statistics, and integrate with Spring Boot Actuator
 * for health monitoring. It helps ensure the cache system is functioning properly and provides
 * visibility into its status.
 * </p>
 * <p>
 * The health check includes:
 * - Redis connection status verification
 * - Cache statistics reporting (memory usage, connected clients, etc.)
 * - Detailed health status reporting with metrics
 * </p>
 * <p>
 * This health indicator is automatically registered with Spring Boot Actuator and exposed
 * through the /actuator/health endpoint.
 * </p>
 */
@Component
public class CacheHealthIndicator implements HealthIndicator {

    private final RedisConnectionFactory redisConnectionFactory;
    private final RedisTemplate<String, Object> redisTemplate;

    /**
     * Constructs a new CacheHealthIndicator with the specified Redis connection factory and template.
     *
     * @param redisConnectionFactory the Redis connection factory used to check connection status
     * @param redisTemplate the Redis template used to collect cache statistics
     */
    public CacheHealthIndicator(RedisConnectionFactory redisConnectionFactory, 
                               RedisTemplate<String, Object> redisTemplate) {
        this.redisConnectionFactory = redisConnectionFactory;
        this.redisTemplate = redisTemplate;
    }

    /**
     * Performs a health check for the Redis cache and returns the status.
     * <p>
     * This method checks if the Redis connection is available and collects cache statistics.
     * It returns UP if the connection is available, and DOWN otherwise. The health response
     * includes detailed metrics about the Redis cache.
     * </p>
     *
     * @return a Health object representing the status of the Redis cache
     */
    @Override
    public Health health() {
        Health.Builder builder = new Health.Builder();
        try {
            if (checkConnection()) {
                Map<String, Object> details = getCacheStatistics();
                return builder.up().withDetails(details).build();
            } else {
                return builder.down().withDetail("error", "Redis connection failed").build();
            }
        } catch (Exception e) {
            return builder.down(e).build();
        }
    }

    /**
     * Checks if the Redis connection is available.
     *
     * @return true if the connection is available, false otherwise
     */
    private boolean checkConnection() {
        try (RedisConnection connection = redisConnectionFactory.getConnection()) {
            return connection.ping() != null;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Collects statistics about the Redis cache.
     * <p>
     * This method retrieves information about the Redis server, including memory usage,
     * connected clients, and other metrics. It returns a map of statistics that can be
     * included in the health response.
     * </p>
     *
     * @return a map of cache statistics
     */
    private Map<String, Object> getCacheStatistics() {
        Map<String, Object> stats = new HashMap<>();
        try (RedisConnection connection = redisConnectionFactory.getConnection()) {
            // Get Redis server info
            Properties info = connection.info();
            
            // Extract key metrics
            stats.put("version", info.getProperty("redis_version", "unknown"));
            stats.put("mode", info.getProperty("redis_mode", "unknown"));
            stats.put("uptime_seconds", parseLongSafely(info.getProperty("uptime_in_seconds")));
            stats.put("connected_clients", parseLongSafely(info.getProperty("connected_clients")));
            stats.put("used_memory_human", info.getProperty("used_memory_human", "unknown"));
            stats.put("total_commands_processed", parseLongSafely(info.getProperty("total_commands_processed")));
            
            // Add cluster-specific information if available
            if ("cluster".equals(info.getProperty("redis_mode"))) {
                stats.put("cluster_enabled", true);
                stats.put("cluster_size", parseLongSafely(info.getProperty("cluster_known_nodes")));
            }
            
            // Add database statistics
            stats.put("keyspace_hits", parseLongSafely(info.getProperty("keyspace_hits")));
            stats.put("keyspace_misses", parseLongSafely(info.getProperty("keyspace_misses")));
            
            // Calculate hit ratio if possible
            long hits = parseLongSafely(info.getProperty("keyspace_hits"));
            long misses = parseLongSafely(info.getProperty("keyspace_misses"));
            if (hits + misses > 0) {
                double hitRatio = (double) hits / (hits + misses);
                stats.put("hit_ratio", String.format("%.2f", hitRatio));
            }
            
            // Add cache names and sizes
            addCacheMetrics(stats);
            
        } catch (Exception e) {
            stats.put("error", "Failed to collect cache statistics: " + e.getMessage());
        }
        return stats;
    }

    /**
     * Adds metrics for each cache defined in CacheConstants.
     *
     * @param stats the map to add cache metrics to
     */
    private void addCacheMetrics(Map<String, Object> stats) {
        Map<String, Object> cacheMetrics = new HashMap<>();
        
        // Add size metrics for each cache
        try {
            // Applications cache
            String appCacheKeyPattern = CacheConstants.KeyPrefix.APPLICATION + "*";
            Long appCacheSize = redisTemplate.keys(appCacheKeyPattern).size();
            cacheMetrics.put(CacheConstants.CacheName.APPLICATIONS, appCacheSize);
            
            // Documents cache
            String docCacheKeyPattern = CacheConstants.KeyPrefix.DOCUMENT + "*";
            Long docCacheSize = redisTemplate.keys(docCacheKeyPattern).size();
            cacheMetrics.put(CacheConstants.CacheName.DOCUMENTS, docCacheSize);
            
            // Merchants cache
            String merchantCacheKeyPattern = CacheConstants.KeyPrefix.MERCHANT + "*";
            Long merchantCacheSize = redisTemplate.keys(merchantCacheKeyPattern).size();
            cacheMetrics.put(CacheConstants.CacheName.MERCHANTS, merchantCacheSize);
            
            // Sessions cache
            String sessionCacheKeyPattern = CacheConstants.KeyPrefix.SESSION + "*";
            Long sessionCacheSize = redisTemplate.keys(sessionCacheKeyPattern).size();
            cacheMetrics.put(CacheConstants.CacheName.SESSIONS, sessionCacheSize);
            
            // Lookups cache
            String lookupCacheKeyPattern = CacheConstants.KeyPrefix.LOOKUP + "*";
            Long lookupCacheSize = redisTemplate.keys(lookupCacheKeyPattern).size();
            cacheMetrics.put(CacheConstants.CacheName.LOOKUPS, lookupCacheSize);
            
        } catch (Exception e) {
            cacheMetrics.put("error", "Failed to collect cache size metrics: " + e.getMessage());
        }
        
        stats.put("caches", cacheMetrics);
    }

    /**
     * Safely parses a string to a long value, returning 0 if parsing fails.
     *
     * @param value the string value to parse
     * @return the parsed long value, or 0 if parsing fails
     */
    private long parseLongSafely(String value) {
        try {
            return value != null ? Long.parseLong(value) : 0;
        } catch (NumberFormatException e) {
            return 0;
        }
    }
}