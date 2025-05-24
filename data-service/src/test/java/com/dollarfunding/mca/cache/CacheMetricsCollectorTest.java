package com.dollarfunding.mca.cache;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.Status;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Unit tests for the {@link CacheMetricsCollector} class.
 * 
 * These tests verify the collection of cache performance metrics such as hit rate, miss rate,
 * and eviction rate, as well as integration with Spring Boot Actuator for metrics exposure.
 * The tests also validate custom metrics for specific cache operations, performance tracking
 * over time, and alerting threshold configuration for critical metrics.
 */
@ExtendWith(MockitoExtension.class)
public class CacheMetricsCollectorTest {

    @Mock
    private RedisTemplate<String, Object> redisTemplate;
    
    @Mock
    private RedisCacheManager cacheManager;
    
    @Mock
    private RedisConnectionFactory connectionFactory;
    
    @Mock
    private RedisConnection redisConnection;
    
    private MeterRegistry meterRegistry;
    
    private CacheMetricsCollector cacheMetricsCollector;
    
    @BeforeEach
    public void setUp() {
        // Use a real SimpleMeterRegistry for testing
        meterRegistry = new SimpleMeterRegistry();
        
        // Create the CacheMetricsCollector with mocked dependencies
        cacheMetricsCollector = new CacheMetricsCollector(redisTemplate, cacheManager, connectionFactory);
        
        // Set up common mock behaviors
        when(connectionFactory.getConnection()).thenReturn(redisConnection);
        when(redisConnection.ping()).thenReturn("PONG");
        
        // Set up test values for alert thresholds
        ReflectionTestUtils.setField(cacheMetricsCollector, "hitRatioThreshold", 0.7);
        ReflectionTestUtils.setField(cacheMetricsCollector, "evictionRateThreshold", 100.0);
        ReflectionTestUtils.setField(cacheMetricsCollector, "latencyThresholdMs", 50.0);
        ReflectionTestUtils.setField(cacheMetricsCollector, "historySize", 24);
        
        // Initialize the collector and bind it to the meter registry
        cacheMetricsCollector.initialize();
        cacheMetricsCollector.bindTo(meterRegistry);
    }
    
    @Test
    @DisplayName("Should record cache hits correctly")
    public void testRecordCacheHit() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Act
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheHit(cacheName);
        
        // Assert
        double hitRatio = cacheMetricsCollector.calculateHitRatio(cacheName);
        assertEquals(1.0, hitRatio, "Hit ratio should be 1.0 when there are only hits");
        
        // Verify the counter was incremented in the registry
        Counter counter = meterRegistry.find("cache.gets").
                tag("cache", cacheName).
                tag("result", "hit").
                counter();
        
        assertNotNull(counter, "Hit counter should be registered");
        assertEquals(3, counter.count(), "Hit counter should be incremented 3 times");
    }
    
    @Test
    @DisplayName("Should record cache misses correctly")
    public void testRecordCacheMiss() {
        // Arrange
        String cacheName = CacheConstants.CacheName.DOCUMENTS;
        
        // Act
        cacheMetricsCollector.recordCacheMiss(cacheName);
        cacheMetricsCollector.recordCacheMiss(cacheName);
        
        // Assert
        double hitRatio = cacheMetricsCollector.calculateHitRatio(cacheName);
        assertEquals(0.0, hitRatio, "Hit ratio should be 0.0 when there are only misses");
        
        // Verify the counter was incremented in the registry
        Counter counter = meterRegistry.find("cache.gets").
                tag("cache", cacheName).
                tag("result", "miss").
                counter();
        
        assertNotNull(counter, "Miss counter should be registered");
        assertEquals(2, counter.count(), "Miss counter should be incremented 2 times");
    }
    
    @Test
    @DisplayName("Should calculate hit ratio correctly with mixed hits and misses")
    public void testCalculateHitRatio() {
        // Arrange
        String cacheName = CacheConstants.CacheName.MERCHANTS;
        
        // Act - 3 hits and 2 misses
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheMiss(cacheName);
        cacheMetricsCollector.recordCacheMiss(cacheName);
        
        // Assert
        double hitRatio = cacheMetricsCollector.calculateHitRatio(cacheName);
        assertEquals(0.6, hitRatio, 0.001, "Hit ratio should be 0.6 (3 hits out of 5 total)");
    }
    
    @Test
    @DisplayName("Should record cache evictions correctly")
    public void testRecordCacheEviction() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Act
        cacheMetricsCollector.recordCacheEviction(cacheName);
        cacheMetricsCollector.recordCacheEviction(cacheName);
        cacheMetricsCollector.recordCacheEviction(cacheName);
        cacheMetricsCollector.recordCacheEviction(cacheName);
        
        // Assert
        Counter counter = meterRegistry.find("cache.evictions").
                tag("cache", cacheName).
                counter();
        
        assertNotNull(counter, "Eviction counter should be registered");
        assertEquals(4, counter.count(), "Eviction counter should be incremented 4 times");
    }
    
    @Test
    @DisplayName("Should record cache puts correctly")
    public void testRecordCachePut() {
        // Arrange
        String cacheName = CacheConstants.CacheName.DOCUMENTS;
        
        // Act
        cacheMetricsCollector.recordCachePut(cacheName);
        cacheMetricsCollector.recordCachePut(cacheName);
        
        // Assert
        Counter counter = meterRegistry.find("cache.puts").
                tag("cache", cacheName).
                counter();
        
        assertNotNull(counter, "Put counter should be registered");
        assertEquals(2, counter.count(), "Put counter should be incremented 2 times");
    }
    
    @Test
    @DisplayName("Should record operation timing correctly")
    public void testMeasureOperation() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        String result = "test result";
        
        // Act - Measure a get operation
        String getResult = cacheMetricsCollector.measureOperation(cacheName, true, () -> {
            // Simulate some work
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            return result;
        });
        
        // Act - Measure a put operation
        String putResult = cacheMetricsCollector.measureOperation(cacheName, false, () -> {
            // Simulate some work
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            return result;
        });
        
        // Assert
        assertEquals(result, getResult, "Get operation should return the correct result");
        assertEquals(result, putResult, "Put operation should return the correct result");
        
        // Verify timers were recorded
        Timer getTimer = meterRegistry.find("cache.get.duration").
                tag("cache", cacheName).
                timer();
        
        Timer putTimer = meterRegistry.find("cache.put.duration").
                tag("cache", cacheName).
                timer();
        
        assertNotNull(getTimer, "Get timer should be registered");
        assertNotNull(putTimer, "Put timer should be registered");
        assertEquals(1, getTimer.count(), "Get timer should record 1 operation");
        assertEquals(1, putTimer.count(), "Put timer should record 1 operation");
    }
    
    @Test
    @DisplayName("Should estimate cache size correctly")
    public void testEstimateCacheSize() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        Set<String> mockKeys = Set.of("applications::1", "applications::2", "applications::3");
        
        when(redisTemplate.keys(cacheName + "::*")).thenReturn(mockKeys);
        
        // Act
        long size = cacheMetricsCollector.estimateCacheSize(cacheName);
        
        // Assert
        assertEquals(3, size, "Cache size should be 3");
        verify(redisTemplate).keys(cacheName + "::*");
    }
    
    @Test
    @DisplayName("Should handle Redis connection errors gracefully when estimating cache size")
    public void testEstimateCacheSizeWithError() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        when(redisTemplate.keys(cacheName + "::*")).thenThrow(new RuntimeException("Redis connection error"));
        
        // Act
        long size = cacheMetricsCollector.estimateCacheSize(cacheName);
        
        // Assert
        assertEquals(0, size, "Cache size should be 0 when there's an error");
    }
    
    @Test
    @DisplayName("Should check Redis connection health correctly")
    public void testIsRedisConnectionHealthy() {
        // Arrange - Default setup returns "PONG"
        
        // Act
        boolean isHealthy = cacheMetricsCollector.isRedisConnectionHealthy();
        
        // Assert
        assertTrue(isHealthy, "Redis connection should be healthy when ping returns PONG");
        verify(redisConnection).ping();
    }
    
    @Test
    @DisplayName("Should detect unhealthy Redis connection")
    public void testIsRedisConnectionUnhealthy() {
        // Arrange
        when(redisConnection.ping()).thenReturn("ERROR");
        
        // Act
        boolean isHealthy = cacheMetricsCollector.isRedisConnectionHealthy();
        
        // Assert
        assertFalse(isHealthy, "Redis connection should be unhealthy when ping doesn't return PONG");
    }
    
    @Test
    @DisplayName("Should handle Redis connection exceptions when checking health")
    public void testIsRedisConnectionHealthyWithException() {
        // Arrange
        when(redisConnection.ping()).thenThrow(new RuntimeException("Redis connection error"));
        
        // Act
        boolean isHealthy = cacheMetricsCollector.isRedisConnectionHealthy();
        
        // Assert
        assertFalse(isHealthy, "Redis connection should be unhealthy when ping throws an exception");
    }
    
    @Test
    @DisplayName("Should reset metrics correctly")
    public void testResetMetrics() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Record some metrics
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheMiss(cacheName);
        cacheMetricsCollector.recordCachePut(cacheName);
        cacheMetricsCollector.recordCacheEviction(cacheName);
        
        // Verify metrics were recorded
        double hitRatioBefore = cacheMetricsCollector.calculateHitRatio(cacheName);
        assertTrue(hitRatioBefore > 0, "Hit ratio should be positive before reset");
        
        // Act
        cacheMetricsCollector.resetMetrics(cacheName);
        
        // Assert
        double hitRatioAfter = cacheMetricsCollector.calculateHitRatio(cacheName);
        assertEquals(0.0, hitRatioAfter, "Hit ratio should be 0 after reset");
        
        // Note: We can't easily verify the counters in the registry were reset because
        // SimpleMeterRegistry doesn't support removing or resetting counters
    }
    
    @Test
    @DisplayName("Should provide health status correctly when Redis is healthy")
    public void testHealthWhenRedisIsHealthy() {
        // Arrange
        // Default setup has Redis returning "PONG"
        Map<String, String> memoryInfo = new HashMap<>();
        memoryInfo.put("used_memory", "1000000");
        memoryInfo.put("maxmemory", "10000000");
        
        when(redisConnection.info("memory")).thenReturn(memoryInfo);
        
        // Record some metrics that are within healthy thresholds
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        for (int i = 0; i < 8; i++) {
            cacheMetricsCollector.recordCacheHit(cacheName);
        }
        for (int i = 0; i < 2; i++) {
            cacheMetricsCollector.recordCacheMiss(cacheName);
        }
        
        // Act
        Health health = cacheMetricsCollector.health();
        
        // Assert
        assertEquals(Status.UP, health.getStatus(), "Health status should be UP when Redis is healthy");
        
        // Verify details
        @SuppressWarnings("unchecked")
        Map<String, Object> details = (Map<String, Object>) health.getDetails();
        assertNotNull(details, "Health details should not be null");
        
        @SuppressWarnings("unchecked")
        Map<String, Object> memoryDetails = (Map<String, Object>) details.get("memory");
        assertNotNull(memoryDetails, "Memory details should not be null");
        assertEquals("0.10", memoryDetails.get("usageRatio"), "Memory usage ratio should be 0.10");
    }
    
    @Test
    @DisplayName("Should provide health status correctly when Redis is unhealthy")
    public void testHealthWhenRedisIsUnhealthy() {
        // Arrange
        when(redisConnection.ping()).thenReturn("ERROR");
        
        // Act
        Health health = cacheMetricsCollector.health();
        
        // Assert
        assertEquals(Status.DOWN, health.getStatus(), "Health status should be DOWN when Redis is unhealthy");
    }
    
    @Test
    @DisplayName("Should provide health status correctly when cache metrics indicate issues")
    public void testHealthWithCacheIssues() {
        // Arrange
        // Default setup has Redis returning "PONG"
        Map<String, String> memoryInfo = new HashMap<>();
        memoryInfo.put("used_memory", "1000000");
        memoryInfo.put("maxmemory", "10000000");
        
        when(redisConnection.info("memory")).thenReturn(memoryInfo);
        
        // Record metrics that indicate issues (low hit ratio)
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        for (int i = 0; i < 2; i++) {
            cacheMetricsCollector.recordCacheHit(cacheName);
        }
        for (int i = 0; i < 8; i++) {
            cacheMetricsCollector.recordCacheMiss(cacheName);
        }
        
        // Act
        Health health = cacheMetricsCollector.health();
        
        // Assert
        assertEquals(Status.DOWN, health.getStatus(), "Health status should be DOWN when cache metrics indicate issues");
        
        // Verify details
        @SuppressWarnings("unchecked")
        Map<String, Object> details = (Map<String, Object>) health.getDetails();
        assertNotNull(details, "Health details should not be null");
        
        @SuppressWarnings("unchecked")
        Map<String, Object> applicationsCacheHealth = (Map<String, Object>) details.get(cacheName);
        assertNotNull(applicationsCacheHealth, "Applications cache health details should not be null");
        assertFalse((Boolean) applicationsCacheHealth.get("healthy"), "Applications cache should be marked as unhealthy");
        
        @SuppressWarnings("unchecked")
        List<String> issues = (List<String>) applicationsCacheHealth.get("issues");
        assertNotNull(issues, "Issues list should not be null");
        assertFalse(issues.isEmpty(), "Issues list should not be empty");
        assertTrue(issues.get(0).contains("Low hit ratio"), "Issues should mention low hit ratio");
    }
    
    @Test
    @DisplayName("Should record and retrieve historical metrics correctly")
    public void testHistoricalMetrics() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Record some metrics
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheMiss(cacheName);
        cacheMetricsCollector.recordCachePut(cacheName);
        cacheMetricsCollector.recordCacheEviction(cacheName);
        
        // Act - Trigger recording of historical metrics
        cacheMetricsCollector.scheduledMetricsLogging();
        
        // Get the historical metrics
        List<Map<String, Object>> history = cacheMetricsCollector.getHistoricalMetrics(cacheName);
        
        // Assert
        assertNotNull(history, "Historical metrics should not be null");
        assertEquals(1, history.size(), "Should have 1 historical record");
        
        Map<String, Object> snapshot = history.get(0);
        assertNotNull(snapshot, "Snapshot should not be null");
        assertEquals(2L, ((Number) snapshot.get("hits")).longValue(), "Should have 2 hits");
        assertEquals(1L, ((Number) snapshot.get("misses")).longValue(), "Should have 1 miss");
        assertEquals(1L, ((Number) snapshot.get("puts")).longValue(), "Should have 1 put");
        assertEquals(1L, ((Number) snapshot.get("evictions")).longValue(), "Should have 1 eviction");
        assertEquals(2.0/3.0, ((Number) snapshot.get("hitRatio")).doubleValue(), 0.001, "Hit ratio should be 2/3");
    }
    
    @Test
    @DisplayName("Should analyze metrics trends correctly")
    public void testAnalyzeMetricsTrends() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Create a map to hold historical metrics
        Map<String, List<Map<String, Object>>> historicalMetrics = new HashMap<>();
        List<Map<String, Object>> history = List.of(
            // First snapshot
            Map.of(
                "timestamp", "2023-01-01T00:00:00",
                "hits", 100L,
                "misses", 20L,
                "puts", 50L,
                "evictions", 10L,
                "size", 500L,
                "hitRatio", 0.83
            ),
            // Second snapshot with decreasing hit ratio and increasing evictions
            Map.of(
                "timestamp", "2023-01-01T01:00:00",
                "hits", 150L,
                "misses", 50L,
                "puts", 80L,
                "evictions", 120L,
                "size", 600L,
                "hitRatio", 0.75
            )
        );
        
        historicalMetrics.put(cacheName, history);
        
        // Set the historical metrics using reflection
        ReflectionTestUtils.setField(cacheMetricsCollector, "historicalMetrics", historicalMetrics);
        
        // Act
        Map<String, Map<String, Object>> trends = cacheMetricsCollector.analyzeMetricsTrends();
        
        // Assert
        assertNotNull(trends, "Trends should not be null");
        assertTrue(trends.containsKey(cacheName), "Trends should contain the cache name");
        
        Map<String, Object> cacheTrends = trends.get(cacheName);
        assertNotNull(cacheTrends, "Cache trends should not be null");
        
        // Check trend values
        assertEquals(-0.08, (Double) cacheTrends.get("hitRatioChange"), 0.001, "Hit ratio change should be -0.08");
        assertEquals(110L, ((Number) cacheTrends.get("evictionChange")).longValue(), "Eviction change should be 110");
        assertEquals(100L, ((Number) cacheTrends.get("sizeChange")).longValue(), "Size change should be 100");
        
        // Check issues detection
        @SuppressWarnings("unchecked")
        List<String> issues = (List<String>) cacheTrends.get("issues");
        assertNotNull(issues, "Issues should not be null");
        assertEquals(2, issues.size(), "Should have 2 issues");
        assertTrue(issues.get(0).contains("Decreasing hit ratio"), "Should detect decreasing hit ratio");
        assertTrue(issues.get(1).contains("Increasing eviction rate"), "Should detect increasing eviction rate");
        assertTrue((Boolean) cacheTrends.get("hasIssues"), "Should have issues flag set to true");
    }
    
    @Test
    @DisplayName("Should get metrics snapshot correctly")
    public void testGetMetricsSnapshot() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Record some metrics
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheHit(cacheName);
        cacheMetricsCollector.recordCacheMiss(cacheName);
        cacheMetricsCollector.recordCachePut(cacheName);
        cacheMetricsCollector.recordCacheEviction(cacheName);
        
        // Mock the cache size estimation
        when(redisTemplate.keys(cacheName + "::*")).thenReturn(Set.of("applications::1", "applications::2"));
        
        // Act
        Map<String, Map<String, Number>> snapshot = cacheMetricsCollector.getMetricsSnapshot();
        
        // Assert
        assertNotNull(snapshot, "Metrics snapshot should not be null");
        assertTrue(snapshot.containsKey(cacheName), "Snapshot should contain the cache name");
        
        Map<String, Number> cacheMetrics = snapshot.get(cacheName);
        assertNotNull(cacheMetrics, "Cache metrics should not be null");
        assertEquals(2L, cacheMetrics.get("hits").longValue(), "Should have 2 hits");
        assertEquals(1L, cacheMetrics.get("misses").longValue(), "Should have 1 miss");
        assertEquals(1L, cacheMetrics.get("puts").longValue(), "Should have 1 put");
        assertEquals(1L, cacheMetrics.get("evictions").longValue(), "Should have 1 eviction");
        assertEquals(2L, cacheMetrics.get("size").longValue(), "Should have size 2");
        assertEquals(2.0/3.0, cacheMetrics.get("hitRatio").doubleValue(), 0.001, "Hit ratio should be 2/3");
    }
    
    @Test
    @DisplayName("Should evaluate cache health correctly")
    public void testEvaluateCacheHealth() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Scenario 1: Healthy cache
        // Record metrics that indicate a healthy cache (high hit ratio, low evictions)
        cacheMetricsCollector.resetMetrics(cacheName);
        for (int i = 0; i < 80; i++) {
            cacheMetricsCollector.recordCacheHit(cacheName);
        }
        for (int i = 0; i < 20; i++) {
            cacheMetricsCollector.recordCacheMiss(cacheName);
        }
        
        // Act
        Map<String, Map<String, Object>> healthStatus = cacheMetricsCollector.evaluateCacheHealth();
        
        // Assert
        assertNotNull(healthStatus, "Health status should not be null");
        assertTrue(healthStatus.containsKey(cacheName), "Health status should contain the cache name");
        
        Map<String, Object> cacheHealth = healthStatus.get(cacheName);
        assertNotNull(cacheHealth, "Cache health should not be null");
        assertTrue((Boolean) cacheHealth.get("healthy"), "Cache should be marked as healthy");
        
        @SuppressWarnings("unchecked")
        List<String> issues = (List<String>) cacheHealth.get("issues");
        assertTrue(issues.isEmpty(), "Healthy cache should have no issues");
        
        // Scenario 2: Unhealthy cache (low hit ratio)
        cacheMetricsCollector.resetMetrics(cacheName);
        for (int i = 0; i < 20; i++) {
            cacheMetricsCollector.recordCacheHit(cacheName);
        }
        for (int i = 0; i < 80; i++) {
            cacheMetricsCollector.recordCacheMiss(cacheName);
        }
        
        // Act again
        healthStatus = cacheMetricsCollector.evaluateCacheHealth();
        cacheHealth = healthStatus.get(cacheName);
        
        // Assert
        assertFalse((Boolean) cacheHealth.get("healthy"), "Cache should be marked as unhealthy");
        issues = (List<String>) cacheHealth.get("issues");
        assertFalse(issues.isEmpty(), "Unhealthy cache should have issues");
        assertTrue(issues.get(0).contains("Low hit ratio"), "Issues should mention low hit ratio");
        
        // Scenario 3: Unhealthy cache (high eviction count)
        cacheMetricsCollector.resetMetrics(cacheName);
        for (int i = 0; i < 80; i++) {
            cacheMetricsCollector.recordCacheHit(cacheName);
        }
        for (int i = 0; i < 20; i++) {
            cacheMetricsCollector.recordCacheMiss(cacheName);
        }
        for (int i = 0; i < 150; i++) {
            cacheMetricsCollector.recordCacheEviction(cacheName);
        }
        
        // Act again
        healthStatus = cacheMetricsCollector.evaluateCacheHealth();
        cacheHealth = healthStatus.get(cacheName);
        
        // Assert
        assertFalse((Boolean) cacheHealth.get("healthy"), "Cache should be marked as unhealthy");
        issues = (List<String>) cacheHealth.get("issues");
        assertFalse(issues.isEmpty(), "Unhealthy cache should have issues");
        assertTrue(issues.get(0).contains("High eviction count"), "Issues should mention high eviction count");
    }
    
    @Test
    @DisplayName("Should handle high latency operations correctly")
    public void testHighLatencyOperations() {
        // Arrange
        String cacheName = CacheConstants.CacheName.APPLICATIONS;
        
        // Set a low latency threshold for testing
        ReflectionTestUtils.setField(cacheMetricsCollector, "latencyThresholdMs", 5.0);
        
        // Act - Record a high latency get operation
        cacheMetricsCollector.recordGetTime(cacheName, 10_000_000); // 10ms in nanoseconds
        
        // Act - Record a high latency put operation
        cacheMetricsCollector.recordPutTime(cacheName, 20_000_000); // 20ms in nanoseconds
        
        // Assert - We can't easily verify the log messages, but we can verify the timers were recorded
        Timer getTimer = meterRegistry.find("cache.get.duration").
                tag("cache", cacheName).
                timer();
        
        Timer putTimer = meterRegistry.find("cache.put.duration").
                tag("cache", cacheName).
                timer();
        
        assertNotNull(getTimer, "Get timer should be registered");
        assertNotNull(putTimer, "Put timer should be registered");
        assertEquals(1, getTimer.count(), "Get timer should record 1 operation");
        assertEquals(1, putTimer.count(), "Put timer should record 1 operation");
        
        // Verify the total time recorded is approximately correct
        assertTrue(getTimer.totalTime(TimeUnit.NANOSECONDS) >= 10_000_000, 
                "Get timer should record at least 10ms");
        assertTrue(putTimer.totalTime(TimeUnit.NANOSECONDS) >= 20_000_000, 
                "Put timer should record at least 20ms");
    }
}