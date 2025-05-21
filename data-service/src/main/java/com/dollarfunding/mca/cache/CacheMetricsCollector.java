package com.dollarfunding.mca.cache;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Collector for cache performance metrics in the MCA application.
 * <p>
 * This class gathers and reports metrics such as hit rate, miss rate, and eviction rate
 * for the Redis cache. It integrates with Spring Boot Actuator to expose these metrics
 * for monitoring and supports custom metrics for specific cache operations.
 * <p>
 * The metrics collected by this class help ensure that the Redis cache is performing
 * optimally, which is critical for maintaining the 99.9% system uptime requirement
 * and ensuring that applications are processed within the 5-minute timeframe.
 */
@Component
public class CacheMetricsCollector implements HealthIndicator {

    private static final Logger logger = LoggerFactory.getLogger(CacheMetricsCollector.class);
    
    private final MeterRegistry meterRegistry;
    private final RedisTemplate<String, Object> redisTemplate;
    private final RedisConnectionFactory connectionFactory;
    
    private final Map<String, Timer> operationTimers = new ConcurrentHashMap<>();
    private final Map<String, Counter> operationCounters = new ConcurrentHashMap<>();
    
    private final AtomicLong cacheHits = new AtomicLong(0);
    private final AtomicLong cacheMisses = new AtomicLong(0);
    private final AtomicLong cacheEvictions = new AtomicLong(0);
    private final AtomicLong cacheSize = new AtomicLong(0);
    
    @Value("${spring.cache.redis.time-to-live:900000}")
    private long defaultTtlMillis; // Default 15 minutes
    
    @Value("${spring.cache.redis.key-prefix:mca:}")
    private String cacheKeyPrefix;
    
    @Value("${metrics.cache.alert.hit-rate-threshold:0.7}")
    private double hitRateAlertThreshold; // Alert if hit rate falls below 70%
    
    @Value("${metrics.cache.alert.eviction-rate-threshold:0.1}")
    private double evictionRateAlertThreshold; // Alert if eviction rate exceeds 10%

    /**
     * Constructs a new CacheMetricsCollector with the specified dependencies.
     *
     * @param meterRegistry     The Spring Boot Actuator meter registry for registering metrics
     * @param redisTemplate     The Redis template for interacting with the Redis cache
     * @param connectionFactory The Redis connection factory for low-level Redis operations
     */
    @Autowired
    public CacheMetricsCollector(MeterRegistry meterRegistry, 
                                RedisTemplate<String, Object> redisTemplate,
                                RedisConnectionFactory connectionFactory) {
        this.meterRegistry = meterRegistry;
        this.redisTemplate = redisTemplate;
        this.connectionFactory = connectionFactory;
    }

    /**
     * Initializes the cache metrics collector by registering metrics with the meter registry.
     * This method is called automatically after the bean is constructed.
     */
    @PostConstruct
    public void init() {
        logger.info("Initializing cache metrics collector");
        
        // Register gauges for cache statistics
        Gauge.builder("cache.hits", cacheHits, AtomicLong::get)
                .description("Number of cache hits")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        Gauge.builder("cache.misses", cacheMisses, AtomicLong::get)
                .description("Number of cache misses")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        Gauge.builder("cache.evictions", cacheEvictions, AtomicLong::get)
                .description("Number of cache evictions")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        Gauge.builder("cache.size", cacheSize, AtomicLong::get)
                .description("Current cache size")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        Gauge.builder("cache.hit.rate", this, CacheMetricsCollector::getHitRate)
                .description("Cache hit rate")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        Gauge.builder("cache.miss.rate", this, CacheMetricsCollector::getMissRate)
                .description("Cache miss rate")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        Gauge.builder("cache.eviction.rate", this, CacheMetricsCollector::getEvictionRate)
                .description("Cache eviction rate")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        Gauge.builder("cache.memory.usage", this, CacheMetricsCollector::getMemoryUsage)
                .description("Cache memory usage in bytes")
                .tag("cache", "redis")
                .register(meterRegistry);
        
        // Register timers for common cache operations
        registerOperationTimer("get");
        registerOperationTimer("set");
        registerOperationTimer("delete");
        registerOperationTimer("exists");
        
        logger.info("Cache metrics collector initialized with hit rate alert threshold: {}%, eviction rate alert threshold: {}%", 
                hitRateAlertThreshold * 100, evictionRateAlertThreshold * 100);
    }

    /**
     * Records a cache hit for the specified cache name.
     *
     * @param cacheName The name of the cache
     */
    public void recordCacheHit(String cacheName) {
        cacheHits.incrementAndGet();
        Counter counter = getOrCreateCounter("cache.hit", cacheName);
        counter.increment();
    }

    /**
     * Records a cache miss for the specified cache name.
     *
     * @param cacheName The name of the cache
     */
    public void recordCacheMiss(String cacheName) {
        cacheMisses.incrementAndGet();
        Counter counter = getOrCreateCounter("cache.miss", cacheName);
        counter.increment();
    }

    /**
     * Records a cache eviction for the specified cache name.
     *
     * @param cacheName The name of the cache
     */
    public void recordCacheEviction(String cacheName) {
        cacheEvictions.incrementAndGet();
        Counter counter = getOrCreateCounter("cache.eviction", cacheName);
        counter.increment();
    }

    /**
     * Records the execution time of a cache operation.
     *
     * @param operation The name of the operation (e.g., "get", "set")
     * @param cacheName The name of the cache
     * @param duration The duration of the operation
     */
    public void recordOperationTime(String operation, String cacheName, Duration duration) {
        Timer timer = getOrCreateTimer(operation, cacheName);
        timer.record(duration);
    }

    /**
     * Creates or retrieves a timer for the specified operation and cache name.
     *
     * @param operation The name of the operation
     * @param cacheName The name of the cache
     * @return The timer for the operation
     */
    private Timer getOrCreateTimer(String operation, String cacheName) {
        String timerName = operation + "." + cacheName;
        return operationTimers.computeIfAbsent(timerName, name -> Timer.builder("cache.operation")
                .description("Cache operation execution time")
                .tag("operation", operation)
                .tag("cache", cacheName)
                .register(meterRegistry));
    }

    /**
     * Creates or retrieves a counter for the specified metric and cache name.
     *
     * @param metric The name of the metric
     * @param cacheName The name of the cache
     * @return The counter for the metric
     */
    private Counter getOrCreateCounter(String metric, String cacheName) {
        String counterName = metric + "." + cacheName;
        return operationCounters.computeIfAbsent(counterName, name -> Counter.builder(metric)
                .description("Cache " + metric + " count")
                .tag("cache", cacheName)
                .register(meterRegistry));
    }

    /**
     * Calculates the current cache hit rate.
     *
     * @return The cache hit rate as a value between 0 and 1
     */
    public double getHitRate() {
        long hits = cacheHits.get();
        long misses = cacheMisses.get();
        long total = hits + misses;
        return total > 0 ? (double) hits / total : 0;
    }

    /**
     * Calculates the current cache miss rate.
     *
     * @return The cache miss rate as a value between 0 and 1
     */
    public double getMissRate() {
        long hits = cacheHits.get();
        long misses = cacheMisses.get();
        long total = hits + misses;
        return total > 0 ? (double) misses / total : 0;
    }

    /**
     * Calculates the current cache eviction rate.
     *
     * @return The cache eviction rate as a value between 0 and 1
     */
    public double getEvictionRate() {
        long evictions = cacheEvictions.get();
        long total = cacheHits.get() + cacheMisses.get();
        return total > 0 ? (double) evictions / total : 0;
    }

    /**
     * Retrieves the current memory usage of the Redis cache in bytes.
     *
     * @return The memory usage in bytes
     */
    public long getMemoryUsage() {
        try {
            Properties info = redisTemplate.execute((RedisCallback<Properties>) connection -> 
                    connection.info("memory"));
            if (info != null && info.containsKey("used_memory")) {
                return Long.parseLong(info.getProperty("used_memory"));
            }
        } catch (Exception e) {
            logger.warn("Failed to retrieve Redis memory usage", e);
        }
        return 0;
    }

    /**
     * Retrieves the current size of the Redis cache (number of keys).
     *
     * @return The number of keys in the cache
     */
    public long getCacheSize() {
        try {
            Long size = redisTemplate.execute((RedisCallback<Long>) connection -> 
                    connection.dbSize());
            if (size != null) {
                cacheSize.set(size);
                return size;
            }
        } catch (Exception e) {
            logger.warn("Failed to retrieve Redis cache size", e);
        }
        return cacheSize.get();
    }

    /**
     * Periodically collects cache statistics and checks for alert conditions.
     * This method is scheduled to run every minute.
     */
    @Scheduled(fixedRateString = "${metrics.cache.collection.interval:60000}")
    public void collectCacheStatistics() {
        logger.debug("Collecting cache statistics");
        
        // Update cache size
        getCacheSize();
        
        // Check for alert conditions
        checkAlertConditions();
        
        // Log cache statistics at INFO level every 10 minutes
        if (System.currentTimeMillis() % 600000 < 60000) {
            logCacheStatistics();
        }
    }

    /**
     * Checks for alert conditions based on configured thresholds.
     */
    private void checkAlertConditions() {
        double hitRate = getHitRate();
        double evictionRate = getEvictionRate();
        
        if (hitRate < hitRateAlertThreshold) {
            logger.warn("Cache hit rate ({}) is below threshold ({})", 
                    String.format("%.2f", hitRate * 100), 
                    String.format("%.2f", hitRateAlertThreshold * 100));
        }
        
        if (evictionRate > evictionRateAlertThreshold) {
            logger.warn("Cache eviction rate ({}) is above threshold ({})", 
                    String.format("%.2f", evictionRate * 100), 
                    String.format("%.2f", evictionRateAlertThreshold * 100));
        }
    }

    /**
     * Logs cache statistics at INFO level.
     */
    private void logCacheStatistics() {
        logger.info("Cache statistics: size={}, hits={}, misses={}, evictions={}, hit_rate={}%, miss_rate={}%, eviction_rate={}%, memory_usage={} bytes",
                getCacheSize(),
                cacheHits.get(),
                cacheMisses.get(),
                cacheEvictions.get(),
                String.format("%.2f", getHitRate() * 100),
                String.format("%.2f", getMissRate() * 100),
                String.format("%.2f", getEvictionRate() * 100),
                getMemoryUsage());
    }

    /**
     * Resets all cache metrics to zero.
     * This method is useful for testing or when metrics need to be reset.
     */
    public void resetMetrics() {
        cacheHits.set(0);
        cacheMisses.set(0);
        cacheEvictions.set(0);
        cacheSize.set(0);
        logger.info("Cache metrics have been reset");
    }

    /**
     * Provides a health check for the Redis cache.
     * This method is part of the Spring Boot Actuator health endpoint.
     *
     * @return The health status of the Redis cache
     */
    @Override
    public Health health() {
        try {
            redisTemplate.execute((RedisCallback<Object>) connection -> {
                connection.ping();
                return null;
            });
            
            double hitRate = getHitRate();
            double evictionRate = getEvictionRate();
            long memoryUsage = getMemoryUsage();
            long size = getCacheSize();
            
            Map<String, Object> details = new HashMap<>();
            details.put("size", size);
            details.put("hit_rate", String.format("%.2f%%", hitRate * 100));
            details.put("miss_rate", String.format("%.2f%%", getMissRate() * 100));
            details.put("eviction_rate", String.format("%.2f%%", evictionRate * 100));
            details.put("memory_usage", memoryUsage);
            details.put("hits", cacheHits.get());
            details.put("misses", cacheMisses.get());
            details.put("evictions", cacheEvictions.get());
            
            // Determine health status based on metrics
            if (hitRate < hitRateAlertThreshold || evictionRate > evictionRateAlertThreshold) {
                return Health.down()
                        .withDetails(details)
                        .build();
            }
            
            return Health.up()
                    .withDetails(details)
                    .build();
            
        } catch (Exception e) {
            logger.error("Redis health check failed", e);
            return Health.down(e).build();
        }
    }

    /**
     * Retrieves detailed cache metrics as a map.
     * This method is useful for custom reporting or API endpoints.
     *
     * @return A map containing all cache metrics
     */
    public Map<String, Object> getDetailedMetrics() {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("size", getCacheSize());
        metrics.put("hits", cacheHits.get());
        metrics.put("misses", cacheMisses.get());
        metrics.put("evictions", cacheEvictions.get());
        metrics.put("hit_rate", getHitRate());
        metrics.put("miss_rate", getMissRate());
        metrics.put("eviction_rate", getEvictionRate());
        metrics.put("memory_usage", getMemoryUsage());
        metrics.put("default_ttl_millis", defaultTtlMillis);
        metrics.put("key_prefix", cacheKeyPrefix);
        return metrics;
    }
}