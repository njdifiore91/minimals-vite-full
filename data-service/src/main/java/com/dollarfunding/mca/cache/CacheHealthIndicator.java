package com.dollarfunding.mca.cache;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.RedisNode;
import org.springframework.data.redis.connection.RedisSentinelConfiguration;
import org.springframework.data.redis.connection.RedisServerCommands;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.stream.Collectors;

/**
 * Implementation of Spring Boot's HealthIndicator for monitoring Redis cache health in the MCA application.
 * <p>
 * This class provides health checks for the Redis connection, reports cache statistics, and integrates
 * with Spring Boot Actuator for health monitoring. It helps ensure the cache system is functioning properly
 * and provides visibility into its status.
 * <p>
 * The health checks include:
 * <ul>
 *   <li>Redis connection status</li>
 *   <li>Redis cluster health (if cluster mode is enabled)</li>
 *   <li>Redis sentinel status (for automatic failover)</li>
 *   <li>Memory usage and eviction policies</li>
 *   <li>Key expiration and TTL settings</li>
 * </ul>
 * <p>
 * This health indicator is critical for maintaining the 99.9% system uptime requirement
 * and ensuring that the Redis cache is functioning properly for the MCA application.
 */
@Component
public class CacheHealthIndicator implements HealthIndicator {

    private static final Logger logger = LoggerFactory.getLogger(CacheHealthIndicator.class);
    
    private final RedisTemplate<String, Object> redisTemplate;
    private final RedisConnectionFactory connectionFactory;
    
    @Value("${spring.redis.cluster.enabled:false}")
    private boolean clusterEnabled;
    
    @Value("${spring.redis.sentinel.master:}")
    private String sentinelMaster;
    
    @Value("${metrics.cache.memory.threshold:0.8}")
    private double memoryThreshold; // Alert if memory usage exceeds 80% of max memory
    
    @Value("${metrics.cache.connection.timeout:2000}")
    private long connectionTimeout; // Connection timeout in milliseconds

    /**
     * Constructs a new CacheHealthIndicator with the specified dependencies.
     *
     * @param redisTemplate     The Redis template for interacting with the Redis cache
     * @param connectionFactory The Redis connection factory for low-level Redis operations
     */
    @Autowired
    public CacheHealthIndicator(RedisTemplate<String, Object> redisTemplate,
                               RedisConnectionFactory connectionFactory) {
        this.redisTemplate = redisTemplate;
        this.connectionFactory = connectionFactory;
    }

    /**
     * Provides a health check for the Redis cache.
     * This method is part of the Spring Boot Actuator health endpoint.
     *
     * @return The health status of the Redis cache
     */
    @Override
    public Health health() {
        Health.Builder builder = new Health.Builder();
        Map<String, Object> details = new HashMap<>();
        
        try {
            // Check basic connectivity
            boolean connected = checkConnection();
            if (!connected) {
                return builder.down()
                        .withDetail("error", "Cannot connect to Redis")
                        .build();
            }
            
            // Get Redis info
            Properties info = getRedisInfo();
            if (info == null) {
                return builder.down()
                        .withDetail("error", "Cannot retrieve Redis INFO")
                        .build();
            }
            
            // Add basic Redis info to details
            details.put("version", info.getProperty("redis_version", "unknown"));
            details.put("mode", info.getProperty("redis_mode", "standalone"));
            details.put("uptime_seconds", info.getProperty("uptime_in_seconds", "0"));
            
            // Check memory usage
            long usedMemory = Long.parseLong(info.getProperty("used_memory", "0"));
            long maxMemory = Long.parseLong(info.getProperty("maxmemory", "0"));
            double memoryUsageRatio = maxMemory > 0 ? (double) usedMemory / maxMemory : 0;
            
            details.put("memory_usage_bytes", usedMemory);
            details.put("max_memory_bytes", maxMemory);
            details.put("memory_usage_ratio", String.format("%.2f", memoryUsageRatio));
            
            // Check cluster status if enabled
            if (clusterEnabled) {
                Map<String, Object> clusterInfo = getClusterInfo();
                details.put("cluster", clusterInfo);
                
                // Check if cluster is in a failed state
                if (clusterInfo.containsKey("cluster_state") && 
                    !"ok".equals(clusterInfo.get("cluster_state"))) {
                    return builder.down()
                            .withDetails(details)
                            .build();
                }
            }
            
            // Check sentinel status if configured
            if (sentinelMaster != null && !sentinelMaster.isEmpty()) {
                Map<String, Object> sentinelInfo = getSentinelInfo();
                details.put("sentinel", sentinelInfo);
                
                // Check if sentinel has enough quorum
                if (sentinelInfo.containsKey("sentinels") && 
                    (Integer) sentinelInfo.get("sentinels") < 2) {
                    return builder.down()
                            .withDetails(details)
                            .build();
                }
            }
            
            // Check key statistics
            long totalKeys = getTotalKeys();
            long expiringKeys = getExpiringKeys();
            
            details.put("total_keys", totalKeys);
            details.put("expiring_keys", expiringKeys);
            details.put("expiring_keys_ratio", totalKeys > 0 ? 
                    String.format("%.2f", (double) expiringKeys / totalKeys) : "0.00");
            
            // Check eviction policy
            String evictionPolicy = info.getProperty("maxmemory_policy", "unknown");
            details.put("eviction_policy", evictionPolicy);
            
            // Check if memory usage exceeds threshold
            if (memoryUsageRatio > memoryThreshold) {
                logger.warn("Redis memory usage ({}) exceeds threshold ({})", 
                        String.format("%.2f%%", memoryUsageRatio * 100), 
                        String.format("%.2f%%", memoryThreshold * 100));
                
                return builder.down()
                        .withDetail("error", "Memory usage exceeds threshold")
                        .withDetails(details)
                        .build();
            }
            
            // Check if eviction policy is not set when it should be
            if (maxMemory > 0 && "noeviction".equals(evictionPolicy)) {
                logger.warn("Redis has maxmemory set but eviction policy is 'noeviction'");
                
                return builder.down()
                        .withDetail("error", "Inappropriate eviction policy")
                        .withDetails(details)
                        .build();
            }
            
            // All checks passed, Redis is healthy
            return builder.up()
                    .withDetails(details)
                    .build();
            
        } catch (Exception e) {
            logger.error("Redis health check failed", e);
            return builder.down(e)
                    .withDetail("error", e.getMessage())
                    .build();
        }
    }

    /**
     * Checks if a connection to Redis can be established.
     *
     * @return true if the connection is successful, false otherwise
     */
    private boolean checkConnection() {
        try {
            return redisTemplate.execute((RedisCallback<Boolean>) connection -> {
                try {
                    return connection.ping() != null;
                } catch (Exception e) {
                    logger.error("Redis ping failed", e);
                    return false;
                }
            });
        } catch (Exception e) {
            logger.error("Redis connection check failed", e);
            return false;
        }
    }

    /**
     * Retrieves Redis INFO command output as Properties.
     *
     * @return Properties containing Redis INFO output, or null if the operation fails
     */
    private Properties getRedisInfo() {
        try {
            return redisTemplate.execute((RedisCallback<Properties>) connection -> {
                try {
                    return connection.info();
                } catch (Exception e) {
                    logger.error("Failed to retrieve Redis INFO", e);
                    return null;
                }
            });
        } catch (Exception e) {
            logger.error("Redis INFO retrieval failed", e);
            return null;
        }
    }

    /**
     * Retrieves Redis cluster information.
     *
     * @return Map containing cluster information, or an empty map if the operation fails
     */
    private Map<String, Object> getClusterInfo() {
        try {
            return redisTemplate.execute((RedisCallback<Map<String, Object>>) connection -> {
                try {
                    Properties clusterInfo = connection.info("cluster");
                    Map<String, Object> result = new HashMap<>();
                    
                    if (clusterInfo != null) {
                        clusterInfo.forEach((k, v) -> result.put(k.toString(), v));
                    }
                    
                    // Get cluster nodes if available
                    if (connection instanceof RedisServerCommands) {
                        String nodesInfo = ((RedisServerCommands) connection).clusterNodes();
                        if (nodesInfo != null) {
                            int nodeCount = nodesInfo.split("\n").length;
                            result.put("node_count", nodeCount);
                        }
                    }
                    
                    return result;
                } catch (Exception e) {
                    logger.error("Failed to retrieve Redis cluster info", e);
                    return new HashMap<>();
                }
            });
        } catch (Exception e) {
            logger.error("Redis cluster info retrieval failed", e);
            return new HashMap<>();
        }
    }

    /**
     * Retrieves Redis sentinel information.
     *
     * @return Map containing sentinel information, or an empty map if the operation fails
     */
    private Map<String, Object> getSentinelInfo() {
        try {
            Map<String, Object> result = new HashMap<>();
            
            // Check if sentinel configuration is available
            if (connectionFactory.getSentinelConnection() != null) {
                RedisSentinelConfiguration sentinelConfig = 
                        (RedisSentinelConfiguration) connectionFactory.getSentinelConfiguration();
                
                if (sentinelConfig != null) {
                    result.put("master", sentinelConfig.getMaster().getName());
                    
                    List<String> sentinels = sentinelConfig.getSentinels().stream()
                            .map(RedisNode::asString)
                            .collect(Collectors.toList());
                    
                    result.put("sentinels", sentinels.size());
                    result.put("sentinel_nodes", sentinels);
                }
            }
            
            return result;
        } catch (Exception e) {
            logger.error("Redis sentinel info retrieval failed", e);
            return new HashMap<>();
        }
    }

    /**
     * Retrieves the total number of keys in Redis.
     *
     * @return The total number of keys, or 0 if the operation fails
     */
    private long getTotalKeys() {
        try {
            Long size = redisTemplate.execute(RedisConnection::dbSize);
            return size != null ? size : 0;
        } catch (Exception e) {
            logger.error("Failed to retrieve Redis key count", e);
            return 0;
        }
    }

    /**
     * Retrieves the number of keys with an expiration set.
     *
     * @return The number of expiring keys, or 0 if the operation fails
     */
    private long getExpiringKeys() {
        try {
            return redisTemplate.execute((RedisCallback<Long>) connection -> {
                try {
                    // This is a rough approximation using the keyspace info
                    Properties keyspaceInfo = connection.info("keyspace");
                    if (keyspaceInfo == null || keyspaceInfo.isEmpty()) {
                        return 0L;
                    }
                    
                    long expiringKeys = 0;
                    for (Object key : keyspaceInfo.keySet()) {
                        String keyStr = key.toString();
                        if (keyStr.startsWith("db")) {
                            String value = keyspaceInfo.getProperty(keyStr);
                            if (value != null && value.contains("expires=")) {
                                String expiresStr = value.substring(
                                        value.indexOf("expires=") + 8, 
                                        value.indexOf(",", value.indexOf("expires=")));
                                expiringKeys += Long.parseLong(expiresStr);
                            }
                        }
                    }
                    return expiringKeys;
                } catch (Exception e) {
                    logger.error("Failed to retrieve Redis expiring keys count", e);
                    return 0L;
                }
            });
        } catch (Exception e) {
            logger.error("Redis expiring keys retrieval failed", e);
            return 0;
        }
    }

    /**
     * Retrieves detailed Redis health information as a map.
     * This method is useful for custom reporting or API endpoints.
     *
     * @return A map containing detailed Redis health information
     */
    public Map<String, Object> getDetailedHealthInfo() {
        Map<String, Object> healthInfo = new HashMap<>();
        
        try {
            // Basic connectivity check
            boolean connected = checkConnection();
            healthInfo.put("connected", connected);
            
            if (!connected) {
                healthInfo.put("status", "DOWN");
                healthInfo.put("error", "Cannot connect to Redis");
                return healthInfo;
            }
            
            // Get Redis info
            Properties info = getRedisInfo();
            if (info == null) {
                healthInfo.put("status", "DOWN");
                healthInfo.put("error", "Cannot retrieve Redis INFO");
                return healthInfo;
            }
            
            // Add basic Redis info
            healthInfo.put("version", info.getProperty("redis_version", "unknown"));
            healthInfo.put("mode", info.getProperty("redis_mode", "standalone"));
            healthInfo.put("uptime_seconds", info.getProperty("uptime_in_seconds", "0"));
            healthInfo.put("connected_clients", info.getProperty("connected_clients", "0"));
            healthInfo.put("used_memory", info.getProperty("used_memory", "0"));
            healthInfo.put("used_memory_human", info.getProperty("used_memory_human", "0"));
            healthInfo.put("maxmemory", info.getProperty("maxmemory", "0"));
            healthInfo.put("maxmemory_human", info.getProperty("maxmemory_human", "0"));
            healthInfo.put("maxmemory_policy", info.getProperty("maxmemory_policy", "unknown"));
            
            // Calculate memory usage ratio
            long usedMemory = Long.parseLong(info.getProperty("used_memory", "0"));
            long maxMemory = Long.parseLong(info.getProperty("maxmemory", "0"));
            double memoryUsageRatio = maxMemory > 0 ? (double) usedMemory / maxMemory : 0;
            healthInfo.put("memory_usage_ratio", String.format("%.2f", memoryUsageRatio));
            
            // Add key statistics
            long totalKeys = getTotalKeys();
            long expiringKeys = getExpiringKeys();
            healthInfo.put("total_keys", totalKeys);
            healthInfo.put("expiring_keys", expiringKeys);
            healthInfo.put("expiring_keys_ratio", totalKeys > 0 ? 
                    String.format("%.2f", (double) expiringKeys / totalKeys) : "0.00");
            
            // Add cluster info if enabled
            if (clusterEnabled) {
                healthInfo.put("cluster", getClusterInfo());
            }
            
            // Add sentinel info if configured
            if (sentinelMaster != null && !sentinelMaster.isEmpty()) {
                healthInfo.put("sentinel", getSentinelInfo());
            }
            
            // Add performance metrics
            healthInfo.put("instantaneous_ops_per_sec", info.getProperty("instantaneous_ops_per_sec", "0"));
            healthInfo.put("hit_rate", info.getProperty("keyspace_hits", "0") + "/" + 
                    (Long.parseLong(info.getProperty("keyspace_hits", "0")) + 
                     Long.parseLong(info.getProperty("keyspace_misses", "0"))));
            
            // Determine overall status
            boolean healthy = true;
            String statusReason = "";
            
            // Check memory usage
            if (memoryUsageRatio > memoryThreshold) {
                healthy = false;
                statusReason = "Memory usage exceeds threshold";
            }
            
            // Check eviction policy
            if (maxMemory > 0 && "noeviction".equals(info.getProperty("maxmemory_policy"))) {
                healthy = false;
                statusReason = "Inappropriate eviction policy";
            }
            
            // Check cluster status if enabled
            if (clusterEnabled) {
                Map<String, Object> clusterInfo = (Map<String, Object>) healthInfo.get("cluster");
                if (clusterInfo.containsKey("cluster_state") && 
                    !"ok".equals(clusterInfo.get("cluster_state"))) {
                    healthy = false;
                    statusReason = "Cluster is in failed state";
                }
            }
            
            // Check sentinel status if configured
            if (sentinelMaster != null && !sentinelMaster.isEmpty()) {
                Map<String, Object> sentinelInfo = (Map<String, Object>) healthInfo.get("sentinel");
                if (sentinelInfo.containsKey("sentinels") && 
                    (Integer) sentinelInfo.get("sentinels") < 2) {
                    healthy = false;
                    statusReason = "Insufficient sentinel quorum";
                }
            }
            
            healthInfo.put("status", healthy ? "UP" : "DOWN");
            if (!healthy) {
                healthInfo.put("status_reason", statusReason);
            }
            
            return healthInfo;
            
        } catch (Exception e) {
            logger.error("Detailed Redis health check failed", e);
            healthInfo.put("status", "DOWN");
            healthInfo.put("error", e.getMessage());
            return healthInfo;
        }
    }
}