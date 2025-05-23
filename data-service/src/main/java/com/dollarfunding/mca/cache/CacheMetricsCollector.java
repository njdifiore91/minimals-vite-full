package com.dollarfunding.mca.cache;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tag;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.binder.MeterBinder;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.actuate.autoconfigure.metrics.MeterRegistryCustomizer;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.context.annotation.Bean;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Collector for cache performance metrics in the MCA application.
 * <p>
 * This class gathers and reports metrics such as hit rate, miss rate, and eviction rate
 * for the Redis cache. It integrates with Spring Boot Actuator to expose these metrics
 * for monitoring and supports custom metrics for specific cache operations.
 * </p>
 * <p>
 * The metrics are exposed through Spring Boot Actuator's /actuator/metrics endpoint
 * and can be consumed by monitoring systems like Prometheus, Datadog, etc.
 * </p>
 * <p>
 * Key metrics collected include:
 * <ul>
 *   <li>Cache hit/miss counts and ratios</li>
 *   <li>Cache eviction counts</li>
 *   <li>Cache size</li>
 *   <li>Cache operation latency</li>
 *   <li>Custom metrics for specific cache operations</li>
 * </ul>
 * </p>
 */
@Component
public class CacheMetricsCollector implements MeterBinder, HealthIndicator {

    private static final Logger logger = LoggerFactory.getLogger(CacheMetricsCollector.class);
    
    private final RedisTemplate<String, Object> redisTemplate;
    private final RedisCacheManager cacheManager;
    private final RedisConnectionFactory connectionFactory;
    
    private MeterRegistry registry;
    
    // Counters for tracking cache operations
    private final Map<String, AtomicLong> cacheHits = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> cacheMisses = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> cacheEvictions = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> cachePuts = new ConcurrentHashMap<>();
    
    // Timers for tracking operation latency
    private final Map<String, Timer> getTimers = new ConcurrentHashMap<>();
    private final Map<String, Timer> putTimers = new ConcurrentHashMap<>();
    
    // Historical metrics for tracking performance over time
    private final Map<String, List<Map<String, Object>>> historicalMetrics = new ConcurrentHashMap<>();
    
    @Value("${management.metrics.cache.history-size:24}")
    private int historySize;
    
    @Value("${management.metrics.cache.alert-threshold.hit-ratio:0.7}")
    private double hitRatioThreshold;
    
    @Value("${management.metrics.cache.alert-threshold.eviction-rate:100}")
    private double evictionRateThreshold;
    
    @Value("${management.metrics.cache.alert-threshold.latency-ms:50}")
    private double latencyThresholdMs;
    
    /**
     * Creates a new CacheMetricsCollector with the specified dependencies.
     *
     * @param redisTemplate     the RedisTemplate for Redis operations
     * @param cacheManager     the RedisCacheManager for cache management
     * @param connectionFactory the RedisConnectionFactory for Redis connections
     */
    @Autowired
    public CacheMetricsCollector(RedisTemplate<String, Object> redisTemplate,
                                RedisCacheManager cacheManager,
                                RedisConnectionFactory connectionFactory) {
        this.redisTemplate = redisTemplate;
        this.cacheManager = cacheManager;
        this.connectionFactory = connectionFactory;
    }
    
    /**
     * Initializes the metrics collector after construction.
     * This method is called by Spring after the bean is constructed and dependencies are injected.
     */
    @PostConstruct
    public void initialize() {
        initializeCounters();
        
        // Initialize historical metrics maps for each cache
        for (String cacheName : cacheHits.keySet()) {
            historicalMetrics.put(cacheName, new ArrayList<>());
        }
        
        logger.info("CacheMetricsCollector initialized with alert thresholds: hitRatio={}, evictionRate={}, latencyMs={}, historySize={}",
                hitRatioThreshold, evictionRateThreshold, latencyThresholdMs, historySize);
        
        // Check Redis connection health on startup
        boolean redisHealthy = isRedisConnectionHealthy();
        if (redisHealthy) {
            logger.info("Redis connection is healthy");
        } else {
            logger.warn("Redis connection is not healthy");
        }
    }
    
    /**
     * Initializes counters for each cache defined in CacheConstants.
     */
    private void initializeCounters() {
        List<String> cacheNames = Arrays.asList(
            CacheConstants.CacheName.APPLICATIONS,
            CacheConstants.CacheName.DOCUMENTS,
            CacheConstants.CacheName.MERCHANTS,
            CacheConstants.CacheName.SESSIONS,
            CacheConstants.CacheName.LOOKUPS
        );
        
        for (String cacheName : cacheNames) {
            cacheHits.put(cacheName, new AtomicLong(0));
            cacheMisses.put(cacheName, new AtomicLong(0));
            cacheEvictions.put(cacheName, new AtomicLong(0));
            cachePuts.put(cacheName, new AtomicLong(0));
        }
    }
    
    /**
     * Binds metrics to the MeterRegistry.
     * This method is called by Spring Boot Actuator to register metrics.
     *
     * @param registry the MeterRegistry to bind metrics to
     */
    @Override
    public void bindTo(MeterRegistry registry) {
        this.registry = registry;
        
        // Register metrics for each cache
        List<String> cacheNames = Arrays.asList(
            CacheConstants.CacheName.APPLICATIONS,
            CacheConstants.CacheName.DOCUMENTS,
            CacheConstants.CacheName.MERCHANTS,
            CacheConstants.CacheName.SESSIONS,
            CacheConstants.CacheName.LOOKUPS
        );
        
        for (String cacheName : cacheNames) {
            registerCacheMetrics(cacheName);
        }
        
        // Register global cache metrics
        registerGlobalCacheMetrics();
    }
    
    /**
     * Registers metrics for a specific cache.
     *
     * @param cacheName the name of the cache to register metrics for
     */
    private void registerCacheMetrics(String cacheName) {
        List<Tag> tags = Arrays.asList(
            Tag.of("cache", cacheName),
            Tag.of("cacheManager", "cacheManager")
        );
        
        // Register hit counter
        Counter.builder("cache.gets")
               .tags(tags)
               .tags("result", "hit")
               .description("The number of times cache lookup methods have returned a cached value")
               .baseUnit("hits")
               .register(registry);
        
        // Register miss counter
        Counter.builder("cache.gets")
               .tags(tags)
               .tags("result", "miss")
               .description("The number of times cache lookup methods have returned an uncached (newly loaded) value")
               .baseUnit("misses")
               .register(registry);
        
        // Register put counter
        Counter.builder("cache.puts")
               .tags(tags)
               .description("The number of entries added to the cache")
               .baseUnit("entries")
               .register(registry);
        
        // Register eviction counter
        Counter.builder("cache.evictions")
               .tags(tags)
               .description("The number of entries evicted from the cache")
               .baseUnit("entries")
               .register(registry);
        
        // Register size gauge
        Gauge.builder("cache.size", () -> estimateCacheSize(cacheName))
             .tags(tags)
             .description("The number of entries in the cache")
             .baseUnit("entries")
             .register(registry);
        
        // Register hit ratio gauge
        Gauge.builder("cache.hit.ratio", () -> calculateHitRatio(cacheName))
             .tags(tags)
             .description("The ratio of cache hits to total gets")
             .register(registry);
        
        // Register operation timers
        getTimers.put(cacheName, Timer.builder("cache.get.duration")
                                      .tags(tags)
                                      .description("The time it takes to get an entry from the cache")
                                      .register(registry));
        
        putTimers.put(cacheName, Timer.builder("cache.put.duration")
                                      .tags(tags)
                                      .description("The time it takes to put an entry into the cache")
                                      .register(registry));
    }
    
    /**
     * Registers global cache metrics that apply to all caches.
     */
    private void registerGlobalCacheMetrics() {
        // Register connection pool metrics
        Gauge.builder("cache.pool.active", () -> getActiveConnections())
             .description("The number of active connections in the Redis connection pool")
             .baseUnit("connections")
             .register(registry);
        
        Gauge.builder("cache.pool.idle", () -> getIdleConnections())
             .description("The number of idle connections in the Redis connection pool")
             .baseUnit("connections")
             .register(registry);
        
        // Register memory usage metrics
        Gauge.builder("cache.memory.used", () -> getUsedMemory())
             .description("The amount of memory used by the Redis cache")
             .baseUnit("bytes")
             .register(registry);
        
        Gauge.builder("cache.memory.max", () -> getMaxMemory())
             .description("The maximum amount of memory available to the Redis cache")
             .baseUnit("bytes")
             .register(registry);
        
        // Register alert metrics
        Gauge.builder("cache.alert.hit.ratio", () -> getLowestHitRatio())
             .description("The lowest hit ratio across all caches")
             .register(registry);
        
        Gauge.builder("cache.alert.eviction.rate", () -> getHighestEvictionRate())
             .description("The highest eviction rate across all caches")
             .register(registry);
    }
    
    /**
     * Records a cache hit for the specified cache.
     *
     * @param cacheName the name of the cache
     */
    public void recordCacheHit(String cacheName) {
        AtomicLong hits = cacheHits.get(cacheName);
        if (hits != null) {
            hits.incrementAndGet();
            registry.counter("cache.gets", "cache", cacheName, "cacheManager", "cacheManager", "result", "hit").increment();
        }
    }
    
    /**
     * Records a cache miss for the specified cache.
     *
     * @param cacheName the name of the cache
     */
    public void recordCacheMiss(String cacheName) {
        AtomicLong misses = cacheMisses.get(cacheName);
        if (misses != null) {
            misses.incrementAndGet();
            registry.counter("cache.gets", "cache", cacheName, "cacheManager", "cacheManager", "result", "miss").increment();
        }
    }
    
    /**
     * Records a cache put for the specified cache.
     *
     * @param cacheName the name of the cache
     */
    public void recordCachePut(String cacheName) {
        AtomicLong puts = cachePuts.get(cacheName);
        if (puts != null) {
            puts.incrementAndGet();
            registry.counter("cache.puts", "cache", cacheName, "cacheManager", "cacheManager").increment();
        }
    }
    
    /**
     * Records a cache eviction for the specified cache.
     *
     * @param cacheName the name of the cache
     */
    public void recordCacheEviction(String cacheName) {
        AtomicLong evictions = cacheEvictions.get(cacheName);
        if (evictions != null) {
            evictions.incrementAndGet();
            registry.counter("cache.evictions", "cache", cacheName, "cacheManager", "cacheManager").increment();
        }
    }
    
    /**
     * Records the time it takes to get an entry from the cache.
     *
     * @param cacheName the name of the cache
     * @param timeNanos the time in nanoseconds
     */
    public void recordGetTime(String cacheName, long timeNanos) {
        Timer timer = getTimers.get(cacheName);
        if (timer != null) {
            timer.record(timeNanos, TimeUnit.NANOSECONDS);
            
            // Log a warning if the operation took longer than the threshold
            double timeMs = timeNanos / 1_000_000.0;
            if (timeMs > latencyThresholdMs) {
                logger.warn("Cache get operation for '{}' took {}ms, exceeding threshold of {}ms",
                        cacheName, String.format("%.2f", timeMs), latencyThresholdMs);
            }
        }
    }
    
    /**
     * Records the time it takes to put an entry into the cache.
     *
     * @param cacheName the name of the cache
     * @param timeNanos the time in nanoseconds
     */
    public void recordPutTime(String cacheName, long timeNanos) {
        Timer timer = putTimers.get(cacheName);
        if (timer != null) {
            timer.record(timeNanos, TimeUnit.NANOSECONDS);
            
            // Log a warning if the operation took longer than the threshold
            double timeMs = timeNanos / 1_000_000.0;
            if (timeMs > latencyThresholdMs) {
                logger.warn("Cache put operation for '{}' took {}ms, exceeding threshold of {}ms",
                        cacheName, String.format("%.2f", timeMs), latencyThresholdMs);
            }
        }
    }
    
    /**
     * Measures and records the execution time of a cache operation.
     * <p>
     * This method is useful for wrapping cache operations to measure their execution time.
     * </p>
     *
     * @param <T>       the return type of the operation
     * @param cacheName the name of the cache
     * @param isGet     true if this is a get operation, false if it's a put operation
     * @param operation the operation to measure
     * @return the result of the operation
     */
    public <T> T measureOperation(String cacheName, boolean isGet, java.util.function.Supplier<T> operation) {
        long startTime = System.nanoTime();
        try {
            return operation.get();
        } finally {
            long timeNanos = System.nanoTime() - startTime;
            if (isGet) {
                recordGetTime(cacheName, timeNanos);
            } else {
                recordPutTime(cacheName, timeNanos);
            }
        }
    }
    
    /**
     * Calculates the hit ratio for the specified cache.
     *
     * @param cacheName the name of the cache
     * @return the hit ratio (hits / (hits + misses))
     */
    public double calculateHitRatio(String cacheName) {
        AtomicLong hits = cacheHits.get(cacheName);
        AtomicLong misses = cacheMisses.get(cacheName);
        
        if (hits == null || misses == null) {
            return 0.0;
        }
        
        long hitCount = hits.get();
        long missCount = misses.get();
        long total = hitCount + missCount;
        
        return total == 0 ? 0.0 : (double) hitCount / total;
    }
    
    /**
     * Estimates the size of the specified cache.
     * <p>
     * This method uses Redis commands to estimate the number of keys in the cache.
     * The accuracy depends on the Redis configuration and the size of the cache.
     * </p>
     *
     * @param cacheName the name of the cache
     * @return the estimated number of entries in the cache
     */
    public long estimateCacheSize(String cacheName) {
        try {
            String keyPattern = cacheName + "::*";
            return redisTemplate.keys(keyPattern).size();
        } catch (Exception e) {
            logger.warn("Failed to estimate cache size for {}: {}", cacheName, e.getMessage());
            return 0;
        }
    }
    
    /**
     * Gets the number of active connections in the Redis connection pool.
     *
     * @return the number of active connections
     */
    private int getActiveConnections() {
        try {
            // This is a simplified implementation and may need to be adjusted based on the actual connection pool implementation
            Map<String, Object> info = redisTemplate.getConnectionFactory().getConnection().info("clients");
            String connectedClients = (String) info.get("connected_clients");
            return connectedClients != null ? Integer.parseInt(connectedClients) : 0;
        } catch (Exception e) {
            logger.warn("Failed to get active connections: {}", e.getMessage());
            return 0;
        }
    }
    
    /**
     * Checks if the Redis connection is healthy.
     * <p>
     * This method sends a PING command to Redis and checks if it responds with PONG.
     * </p>
     *
     * @return true if the Redis connection is healthy, false otherwise
     */
    public boolean isRedisConnectionHealthy() {
        try {
            String pong = redisTemplate.getConnectionFactory().getConnection().ping();
            return "PONG".equalsIgnoreCase(pong);
        } catch (Exception e) {
            logger.warn("Redis connection health check failed: {}", e.getMessage());
            return false;
        }
    }
    
    /**
     * Gets the number of idle connections in the Redis connection pool.
     *
     * @return the number of idle connections
     */
    private int getIdleConnections() {
        try {
            // This is a simplified implementation and may need to be adjusted based on the actual connection pool implementation
            return 0; // Placeholder - actual implementation would depend on the connection pool metrics
        } catch (Exception e) {
            logger.warn("Failed to get idle connections: {}", e.getMessage());
            return 0;
        }
    }
    
    /**
     * Gets the amount of memory used by the Redis cache.
     *
     * @return the amount of memory used in bytes
     */
    private long getUsedMemory() {
        try {
            Map<String, Object> info = redisTemplate.getConnectionFactory().getConnection().info("memory");
            String usedMemory = (String) info.get("used_memory");
            return usedMemory != null ? Long.parseLong(usedMemory) : 0;
        } catch (Exception e) {
            logger.warn("Failed to get used memory: {}", e.getMessage());
            return 0;
        }
    }
    
    /**
     * Gets the maximum amount of memory available to the Redis cache.
     *
     * @return the maximum amount of memory in bytes
     */
    private long getMaxMemory() {
        try {
            Map<String, Object> info = redisTemplate.getConnectionFactory().getConnection().info("memory");
            String maxMemory = (String) info.get("maxmemory");
            return maxMemory != null ? Long.parseLong(maxMemory) : 0;
        } catch (Exception e) {
            logger.warn("Failed to get max memory: {}", e.getMessage());
            return 0;
        }
    }
    
    /**
     * Gets the lowest hit ratio across all caches.
     * <p>
     * This is used for alerting when the hit ratio falls below the threshold.
     * </p>
     *
     * @return the lowest hit ratio
     */
    private double getLowestHitRatio() {
        double lowest = 1.0;
        
        for (String cacheName : cacheHits.keySet()) {
            double ratio = calculateHitRatio(cacheName);
            if (ratio < lowest) {
                lowest = ratio;
            }
        }
        
        // Log an alert if the lowest hit ratio is below the threshold
        if (lowest < hitRatioThreshold) {
            logger.warn("Cache hit ratio alert: lowest ratio {} is below threshold {}", lowest, hitRatioThreshold);
        }
        
        return lowest;
    }
    
    /**
     * Gets the highest eviction rate across all caches.
     * <p>
     * This is used for alerting when the eviction rate exceeds the threshold.
     * </p>
     *
     * @return the highest eviction rate
     */
    private double getHighestEvictionRate() {
        double highest = 0.0;
        
        for (String cacheName : cacheEvictions.keySet()) {
            AtomicLong evictions = cacheEvictions.get(cacheName);
            if (evictions != null) {
                double rate = evictions.get(); // Simplified - in a real implementation, this would be evictions per time period
                if (rate > highest) {
                    highest = rate;
                }
            }
        }
        
        // Log an alert if the highest eviction rate exceeds the threshold
        if (highest > evictionRateThreshold) {
            logger.warn("Cache eviction rate alert: highest rate {} exceeds threshold {}", highest, evictionRateThreshold);
        }
        
        return highest;
    }
    
    /**
     * Resets all metrics for the specified cache.
     * <p>
     * This is useful for testing or when a cache is cleared.
     * </p>
     *
     * @param cacheName the name of the cache
     */
    public void resetMetrics(String cacheName) {
        AtomicLong hits = cacheHits.get(cacheName);
        AtomicLong misses = cacheMisses.get(cacheName);
        AtomicLong evictions = cacheEvictions.get(cacheName);
        AtomicLong puts = cachePuts.get(cacheName);
        
        if (hits != null) hits.set(0);
        if (misses != null) misses.set(0);
        if (evictions != null) evictions.set(0);
        if (puts != null) puts.set(0);
    }
    
    /**
     * Provides a customizer for the MeterRegistry to add common tags to all metrics.
     *
     * @return a MeterRegistryCustomizer that adds common tags
     */
    @Bean
    public MeterRegistryCustomizer<MeterRegistry> metricsCommonTags() {
        return registry -> registry.config()
                .commonTags("application", "mca-data-service", "component", "cache");
    }
    
    /**
     * Scheduled task to log cache metrics summary periodically.
     * <p>
     * This task runs every 15 minutes to provide regular insights into cache performance.
     * </p>
     */
    @Scheduled(fixedRateString = "${management.metrics.cache.log-interval-ms:900000}")
    public void scheduledMetricsLogging() {
        logMetricsSummary();
        
        // Evaluate cache health and log any issues
        Map<String, Map<String, Object>> healthStatus = evaluateCacheHealth();
        boolean hasIssues = false;
        
        for (Map.Entry<String, Map<String, Object>> entry : healthStatus.entrySet()) {
            String cacheName = entry.getKey();
            Map<String, Object> cacheHealth = entry.getValue();
            
            boolean isHealthy = (boolean) cacheHealth.get("healthy");
            if (!isHealthy) {
                hasIssues = true;
                @SuppressWarnings("unchecked")
                List<String> issues = (List<String>) cacheHealth.get("issues");
                logger.warn("Cache '{}' has health issues: {}", cacheName, String.join(", ", issues));
            }
        }
        
        if (!hasIssues) {
            logger.info("All caches are healthy");
        }
        
        // Record historical metrics
        recordHistoricalMetrics();
    }
    
    /**
     * Records current metrics for historical tracking.
     * <p>
     * This method captures a snapshot of current metrics for each cache and stores it
     * in a historical record for trend analysis.
     * </p>
     */
    private void recordHistoricalMetrics() {
        LocalDateTime now = LocalDateTime.now();
        String timestamp = now.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        
        for (String cacheName : cacheHits.keySet()) {
            // Create a metrics snapshot
            Map<String, Object> snapshot = new HashMap<>();
            snapshot.put("timestamp", timestamp);
            snapshot.put("hits", cacheHits.get(cacheName).get());
            snapshot.put("misses", cacheMisses.get(cacheName).get());
            snapshot.put("puts", cachePuts.get(cacheName).get());
            snapshot.put("evictions", cacheEvictions.get(cacheName).get());
            snapshot.put("size", estimateCacheSize(cacheName));
            snapshot.put("hitRatio", calculateHitRatio(cacheName));
            
            // Get or create the history list for this cache
            List<Map<String, Object>> history = historicalMetrics.computeIfAbsent(cacheName, k -> new ArrayList<>());
            
            // Add the snapshot to the history
            history.add(snapshot);
            
            // Trim the history if it exceeds the maximum size
            if (history.size() > historySize) {
                history.remove(0);
            }
        }
    }
    
    /**
     * Gets the historical metrics for the specified cache.
     * <p>
     * This method returns a list of metric snapshots for the specified cache,
     * allowing for trend analysis and performance tracking over time.
     * </p>
     *
     * @param cacheName the name of the cache
     * @return a list of metric snapshots, or an empty list if no history is available
     */
    public List<Map<String, Object>> getHistoricalMetrics(String cacheName) {
        return historicalMetrics.getOrDefault(cacheName, new ArrayList<>());
    }
    
    /**
     * Analyzes historical metrics to detect trends and potential issues.
     * <p>
     * This method analyzes the historical metrics for each cache to detect trends
     * and potential issues, such as decreasing hit ratios or increasing eviction rates.
     * </p>
     *
     * @return a map of cache names to trend analysis results
     */
    public Map<String, Map<String, Object>> analyzeMetricsTrends() {
        Map<String, Map<String, Object>> trends = new HashMap<>();
        
        for (String cacheName : historicalMetrics.keySet()) {
            List<Map<String, Object>> history = historicalMetrics.get(cacheName);
            if (history.size() < 2) {
                continue; // Need at least 2 data points for trend analysis
            }
            
            Map<String, Object> trend = new HashMap<>();
            
            // Calculate hit ratio trend
            double firstHitRatio = (double) history.get(0).get("hitRatio");
            double lastHitRatio = (double) history.get(history.size() - 1).get("hitRatio");
            double hitRatioChange = lastHitRatio - firstHitRatio;
            
            // Calculate eviction rate trend
            long firstEvictions = ((Number) history.get(0).get("evictions")).longValue();
            long lastEvictions = ((Number) history.get(history.size() - 1).get("evictions")).longValue();
            long evictionChange = lastEvictions - firstEvictions;
            
            // Calculate size trend
            long firstSize = ((Number) history.get(0).get("size")).longValue();
            long lastSize = ((Number) history.get(history.size() - 1).get("size")).longValue();
            long sizeChange = lastSize - firstSize;
            
            // Add trend data
            trend.put("hitRatioChange", hitRatioChange);
            trend.put("evictionChange", evictionChange);
            trend.put("sizeChange", sizeChange);
            
            // Detect potential issues
            List<String> issues = new ArrayList<>();
            if (hitRatioChange < -0.1) { // Hit ratio decreased by more than 10%
                issues.add("Decreasing hit ratio: " + String.format("%.2f", hitRatioChange));
            }
            if (evictionChange > 100) { // Evictions increased by more than 100
                issues.add("Increasing eviction rate: " + evictionChange);
            }
            if (sizeChange > 1000) { // Size increased by more than 1000 entries
                issues.add("Rapidly growing cache size: " + sizeChange);
            }
            
            trend.put("issues", issues);
            trend.put("hasIssues", !issues.isEmpty());
            
            trends.put(cacheName, trend);
        }
        
        return trends;
    }
    
    /**
     * Implements the HealthIndicator interface to provide cache health information
     * for Spring Boot Actuator's health endpoint.
     * <p>
     * This method is called by Spring Boot Actuator to determine the health status
     * of the cache system. It checks various metrics against thresholds to determine
     * if the cache system is healthy or if there are potential issues.
     * </p>
     * <p>
     * The health information is exposed through Spring Boot Actuator's /actuator/health endpoint
     * and can be used by Kubernetes for liveness and readiness probes.
     * </p>
     *
     * @return a Health object representing the health status of the cache system
     */
    @Override
    public Health health() {
        try {
            // Check if Redis is accessible
            boolean redisAccessible = isRedisConnectionHealthy();
            if (!redisAccessible) {
                return Health.down()
                        .withDetail("error", "Redis connection failed")
                        .build();
            }
            
            // Evaluate cache health
            Map<String, Map<String, Object>> healthStatus = evaluateCacheHealth();
            boolean allHealthy = true;
            Map<String, Object> healthDetails = new HashMap<>();
            
            for (Map.Entry<String, Map<String, Object>> entry : healthStatus.entrySet()) {
                String cacheName = entry.getKey();
                Map<String, Object> cacheHealth = entry.getValue();
                
                boolean isHealthy = (boolean) cacheHealth.get("healthy");
                if (!isHealthy) {
                    allHealthy = false;
                }
                
                healthDetails.put(cacheName, cacheHealth);
            }
            
            // Add memory usage information
            long usedMemory = getUsedMemory();
            long maxMemory = getMaxMemory();
            double memoryUsageRatio = maxMemory > 0 ? (double) usedMemory / maxMemory : 0.0;
            
            // Add memory usage information
            Map<String, Object> memoryDetails = new HashMap<>();
            memoryDetails.put("used", usedMemory);
            memoryDetails.put("max", maxMemory);
            memoryDetails.put("usageRatio", String.format("%.2f", memoryUsageRatio));
            healthDetails.put("memory", memoryDetails);
            
            // Add connection pool information
            Map<String, Object> connectionDetails = new HashMap<>();
            connectionDetails.put("active", getActiveConnections());
            connectionDetails.put("idle", getIdleConnections());
            healthDetails.put("connections", connectionDetails);
            
            if (allHealthy) {
                return Health.up()
                        .withDetails(healthDetails)
                        .build();
            } else {
                return Health.down()
                        .withDetails(healthDetails)
                        .build();
            }
        } catch (Exception e) {
            logger.error("Error checking cache health", e);
            return Health.down()
                    .withDetail("error", e.getMessage())
                    .build();
        }
    }
    
    /**
     * Gets a snapshot of all cache metrics.
     * <p>
     * This is useful for reporting or debugging purposes.
     * </p>
     *
     * @return a map of cache names to metric snapshots
     */
    public Map<String, Map<String, Number>> getMetricsSnapshot() {
        Map<String, Map<String, Number>> snapshot = new HashMap<>();
        
        for (String cacheName : cacheHits.keySet()) {
            Map<String, Number> cacheMetrics = new HashMap<>();
            
            AtomicLong hits = cacheHits.get(cacheName);
            AtomicLong misses = cacheMisses.get(cacheName);
            AtomicLong evictions = cacheEvictions.get(cacheName);
            AtomicLong puts = cachePuts.get(cacheName);
            
            cacheMetrics.put("hits", hits != null ? hits.get() : 0);
            cacheMetrics.put("misses", misses != null ? misses.get() : 0);
            cacheMetrics.put("evictions", evictions != null ? evictions.get() : 0);
            cacheMetrics.put("puts", puts != null ? puts.get() : 0);
            cacheMetrics.put("size", estimateCacheSize(cacheName));
            cacheMetrics.put("hitRatio", calculateHitRatio(cacheName));
            
            snapshot.put(cacheName, cacheMetrics);
        }
        
        return snapshot;
    }
    
    /**
     * Logs a summary of cache metrics.
     * <p>
     * This is useful for periodic reporting of cache performance.
     * </p>
     */
    public void logMetricsSummary() {
        logger.info("Cache Metrics Summary:");
        
        for (String cacheName : cacheHits.keySet()) {
            AtomicLong hits = cacheHits.get(cacheName);
            AtomicLong misses = cacheMisses.get(cacheName);
            AtomicLong evictions = cacheEvictions.get(cacheName);
            AtomicLong puts = cachePuts.get(cacheName);
            
            long hitCount = hits != null ? hits.get() : 0;
            long missCount = misses != null ? misses.get() : 0;
            long evictionCount = evictions != null ? evictions.get() : 0;
            long putCount = puts != null ? puts.get() : 0;
            long size = estimateCacheSize(cacheName);
            double hitRatio = calculateHitRatio(cacheName);
            
            logger.info("Cache '{}': hits={}, misses={}, puts={}, evictions={}, size={}, hitRatio={}",
                    cacheName, hitCount, missCount, putCount, evictionCount, size, String.format("%.2f", hitRatio));
            
            // Log warnings for concerning metrics
            if (hitRatio < hitRatioThreshold) {
                logger.warn("Cache '{}' has a low hit ratio: {} (threshold: {})", 
                        cacheName, String.format("%.2f", hitRatio), hitRatioThreshold);
            }
            
            if (evictionCount > evictionRateThreshold) {
                logger.warn("Cache '{}' has a high eviction count: {} (threshold: {})", 
                        cacheName, evictionCount, evictionRateThreshold);
            }
        }
    }
    
    /**
     * Evaluates the health of the cache system based on current metrics.
     * <p>
     * This method checks various metrics against thresholds to determine if the cache
     * system is healthy or if there are potential issues that need attention.
     * </p>
     *
     * @return a map containing health status information for each cache
     */
    public Map<String, Map<String, Object>> evaluateCacheHealth() {
        Map<String, Map<String, Object>> healthStatus = new HashMap<>();
        
        for (String cacheName : cacheHits.keySet()) {
            Map<String, Object> cacheHealth = new HashMap<>();
            
            // Calculate key health metrics
            double hitRatio = calculateHitRatio(cacheName);
            long evictionCount = cacheEvictions.get(cacheName) != null ? cacheEvictions.get(cacheName).get() : 0;
            long size = estimateCacheSize(cacheName);
            
            // Determine health status
            boolean isHealthy = true;
            List<String> issues = new ArrayList<>();
            
            if (hitRatio < hitRatioThreshold) {
                isHealthy = false;
                issues.add("Low hit ratio: " + String.format("%.2f", hitRatio));
            }
            
            if (evictionCount > evictionRateThreshold) {
                isHealthy = false;
                issues.add("High eviction count: " + evictionCount);
            }
            
            // Add health information to the map
            cacheHealth.put("healthy", isHealthy);
            cacheHealth.put("issues", issues);
            cacheHealth.put("hitRatio", hitRatio);
            cacheHealth.put("evictionCount", evictionCount);
            cacheHealth.put("size", size);
            
            healthStatus.put(cacheName, cacheHealth);
        }
        
        return healthStatus;
    }
}