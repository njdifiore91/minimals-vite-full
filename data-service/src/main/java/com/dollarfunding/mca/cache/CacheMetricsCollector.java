package com.dollarfunding.mca.cache;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

/**
 * Collector for cache performance metrics in the MCA application.
 * This class gathers and reports metrics such as hit rate, miss rate, and eviction rate for the Redis cache.
 * It integrates with Spring Boot Actuator to expose these metrics for monitoring and supports custom metrics
 * for specific cache operations.
 */
@Component
public class CacheMetricsCollector {

    private static final Logger log = LoggerFactory.getLogger(CacheMetricsCollector.class);

    private final MeterRegistry meterRegistry;

    // Cache operation counters
    private final Counter cacheHitCounter;
    private final Counter cacheMissCounter;
    private final Counter cacheErrorCounter;
    private final Counter cacheEvictionCounter;
    private final Counter cacheWriteCounter;

    // Cache operation timers
    private final Timer cacheGetTimer;
    private final Timer cacheSetTimer;
    private final Timer cacheDeleteTimer;

    /**
     * Constructor for CacheMetricsCollector.
     *
     * @param meterRegistry The meter registry for recording metrics
     */
    @Autowired
    public CacheMetricsCollector(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;

        // Initialize counters
        this.cacheHitCounter = Counter.builder("cache.hits")
                .description("Number of cache hits")
                .register(meterRegistry);

        this.cacheMissCounter = Counter.builder("cache.misses")
                .description("Number of cache misses")
                .register(meterRegistry);

        this.cacheErrorCounter = Counter.builder("cache.errors")
                .description("Number of cache errors")
                .register(meterRegistry);

        this.cacheEvictionCounter = Counter.builder("cache.evictions")
                .description("Number of cache evictions")
                .register(meterRegistry);

        this.cacheWriteCounter = Counter.builder("cache.writes")
                .description("Number of cache writes")
                .register(meterRegistry);

        // Initialize timers
        this.cacheGetTimer = Timer.builder("cache.get.time")
                .description("Time taken for cache get operations")
                .register(meterRegistry);

        this.cacheSetTimer = Timer.builder("cache.set.time")
                .description("Time taken for cache set operations")
                .register(meterRegistry);

        this.cacheDeleteTimer = Timer.builder("cache.delete.time")
                .description("Time taken for cache delete operations")
                .register(meterRegistry);

        log.info("Cache metrics collector initialized");
    }

    /**
     * Records a cache hit.
     *
     * @param key       The cache key
     * @param timeNanos The time taken for the operation in nanoseconds
     */
    public void recordCacheHit(String key, long timeNanos) {
        cacheHitCounter.increment();
        cacheGetTimer.record(timeNanos, TimeUnit.NANOSECONDS);

        // Record key-specific metrics
        meterRegistry.counter("cache.hits.key", "key", getKeyCategory(key)).increment();
    }

    /**
     * Records a cache miss.
     *
     * @param key The cache key
     */
    public void recordCacheMiss(String key) {
        cacheMissCounter.increment();

        // Record key-specific metrics
        meterRegistry.counter("cache.misses.key", "key", getKeyCategory(key)).increment();
    }

    /**
     * Records a cache error.
     *
     * @param key       The cache key
     * @param errorType The type of error
     */
    public void recordCacheError(String key, String errorType) {
        cacheErrorCounter.increment();

        // Record error-specific metrics
        meterRegistry.counter("cache.errors.type", "type", errorType).increment();
        meterRegistry.counter("cache.errors.key", "key", getKeyCategory(key)).increment();
    }

    /**
     * Records a cache eviction.
     *
     * @param key The cache key
     */
    public void recordCacheEviction(String key) {
        cacheEvictionCounter.increment();

        // Record key-specific metrics
        meterRegistry.counter("cache.evictions.key", "key", getKeyCategory(key)).increment();
    }

    /**
     * Records a cache write.
     *
     * @param key       The cache key
     * @param timeNanos The time taken for the operation in nanoseconds
     */
    public void recordCacheWrite(String key, long timeNanos) {
        cacheWriteCounter.increment();
        cacheSetTimer.record(timeNanos, TimeUnit.NANOSECONDS);

        // Record key-specific metrics
        meterRegistry.counter("cache.writes.key", "key", getKeyCategory(key)).increment();
    }

    /**
     * Records a batch cache hit.
     *
     * @param hitCount  The number of hits
     * @param missCount The number of misses
     * @param timeNanos The time taken for the operation in nanoseconds
     */
    public void recordCacheBatchHit(int hitCount, int missCount, long timeNanos) {
        cacheHitCounter.increment(hitCount);
        cacheMissCounter.increment(missCount);
        cacheGetTimer.record(timeNanos, TimeUnit.NANOSECONDS);

        // Record batch-specific metrics
        meterRegistry.counter("cache.batch.hits").increment(hitCount);
        meterRegistry.counter("cache.batch.misses").increment(missCount);
    }

    /**
     * Records a batch cache miss.
     *
     * @param missCount The number of misses
     */
    public void recordCacheBatchMiss(int missCount) {
        cacheMissCounter.increment(missCount);

        // Record batch-specific metrics
        meterRegistry.counter("cache.batch.misses").increment(missCount);
    }

    /**
     * Records a batch cache write.
     *
     * @param writeCount The number of writes
     * @param timeNanos  The time taken for the operation in nanoseconds
     */
    public void recordCacheBatchWrite(int writeCount, long timeNanos) {
        cacheWriteCounter.increment(writeCount);
        cacheSetTimer.record(timeNanos, TimeUnit.NANOSECONDS);

        // Record batch-specific metrics
        meterRegistry.counter("cache.batch.writes").increment(writeCount);
    }

    /**
     * Records a batch cache eviction.
     *
     * @param evictionCount The number of evictions
     */
    public void recordCacheBatchEviction(int evictionCount) {
        cacheEvictionCounter.increment(evictionCount);

        // Record batch-specific metrics
        meterRegistry.counter("cache.batch.evictions").increment(evictionCount);
    }

    /**
     * Gets the hit rate as a percentage.
     *
     * @return The hit rate percentage
     */
    public double getHitRate() {
        double hits = cacheHitCounter.count();
        double misses = cacheMissCounter.count();
        double total = hits + misses;

        if (total == 0) {
            return 0.0;
        }

        return (hits / total) * 100.0;
    }

    /**
     * Gets the error rate as a percentage.
     *
     * @return The error rate percentage
     */
    public double getErrorRate() {
        double errors = cacheErrorCounter.count();
        double operations = cacheHitCounter.count() + cacheMissCounter.count() + cacheWriteCounter.count();

        if (operations == 0) {
            return 0.0;
        }

        return (errors / operations) * 100.0;
    }

    /**
     * Gets the average get operation time in milliseconds.
     *
     * @return The average get time in milliseconds
     */
    public double getAverageGetTimeMs() {
        return cacheGetTimer.mean(TimeUnit.MILLISECONDS);
    }

    /**
     * Gets the average set operation time in milliseconds.
     *
     * @return The average set time in milliseconds
     */
    public double getAverageSetTimeMs() {
        return cacheSetTimer.mean(TimeUnit.MILLISECONDS);
    }

    /**
     * Gets the key category for metrics grouping.
     * This extracts the prefix from the key to group similar keys together.
     *
     * @param key The cache key
     * @return The key category for metrics
     */
    private String getKeyCategory(String key) {
        if (key == null || key.isEmpty()) {
            return "unknown";
        }

        // Extract the prefix from the key
        if (key.startsWith(CacheConstants.KEY_PREFIX_APPLICATION)) {
            return "application";
        } else if (key.startsWith(CacheConstants.KEY_PREFIX_DOCUMENT)) {
            return "document";
        } else if (key.startsWith(CacheConstants.KEY_PREFIX_MERCHANT)) {
            return "merchant";
        } else if (key.startsWith(CacheConstants.KEY_PREFIX_SESSION)) {
            return "session";
        } else if (key.startsWith(CacheConstants.KEY_PREFIX_COLLECTION)) {
            return "collection";
        } else if (key.startsWith(CacheConstants.KEY_PREFIX_COUNTER)) {
            return "counter";
        } else if (key.startsWith(CacheConstants.KEY_PREFIX_LOCK)) {
            return "lock";
        } else {
            return "other";
        }
    }
}