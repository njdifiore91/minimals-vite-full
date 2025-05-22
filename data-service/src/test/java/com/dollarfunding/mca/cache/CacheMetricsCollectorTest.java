package com.dollarfunding.mca.cache;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the {@link CacheMetricsCollector} class.
 * 
 * These tests verify the collection of cache performance metrics such as hit rate, miss rate,
 * and eviction rate, as well as integration with Spring Boot Actuator's MeterRegistry.
 */
@ExtendWith(MockitoExtension.class)
public class CacheMetricsCollectorTest {

    @Mock
    private MeterRegistry mockMeterRegistry;
    
    @Mock
    private Counter mockCounter;
    
    @Mock
    private Timer mockTimer;
    
    private CacheMetricsCollector collectorWithMocks;
    private CacheMetricsCollector collectorWithSimpleRegistry;
    private SimpleMeterRegistry simpleMeterRegistry;

    @BeforeEach
    void setUp() {
        // Set up mock registry for specific interaction tests
        when(mockMeterRegistry.counter(anyString(), any())).thenReturn(mockCounter);
        when(mockMeterRegistry.counter(anyString())).thenReturn(mockCounter);
        when(mockMeterRegistry.timer(anyString())).thenReturn(mockTimer);
        when(Counter.builder(anyString())).thenReturn(Counter.builder("test"));
        when(Timer.builder(anyString())).thenReturn(Timer.builder("test"));
        
        // Create collector with mocks for verifying interactions
        collectorWithMocks = new CacheMetricsCollector(mockMeterRegistry);
        
        // Create collector with SimpleMeterRegistry for verifying actual behavior
        simpleMeterRegistry = new SimpleMeterRegistry();
        collectorWithSimpleRegistry = new CacheMetricsCollector(simpleMeterRegistry);
    }

    @Test
    @DisplayName("Should initialize counters and timers during construction")
    void shouldInitializeCountersAndTimersDuringConstruction() {
        // Verify that counters are created during initialization
        verify(mockMeterRegistry, times(5)).counter(any(Counter.class));
        
        // Verify that timers are created during initialization
        verify(mockMeterRegistry, times(3)).timer(any(Timer.class));
    }

    @Test
    @DisplayName("Should record cache hit with correct metrics")
    void shouldRecordCacheHitWithCorrectMetrics() {
        // Given
        String key = CacheConstants.KeyPrefix.APPLICATION + "123";
        long timeNanos = 1_000_000; // 1ms in nanoseconds
        
        // When
        collectorWithSimpleRegistry.recordCacheHit(key, timeNanos);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.hits").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.hits.key").tags("key", "application").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.get.time").timer().totalTime(TimeUnit.NANOSECONDS)).isEqualTo(timeNanos);
    }

    @Test
    @DisplayName("Should record cache miss with correct metrics")
    void shouldRecordCacheMissWithCorrectMetrics() {
        // Given
        String key = CacheConstants.KeyPrefix.DOCUMENT + "456";
        
        // When
        collectorWithSimpleRegistry.recordCacheMiss(key);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.misses").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.misses.key").tags("key", "document").counter().count()).isEqualTo(1);
    }

    @Test
    @DisplayName("Should record cache error with correct metrics")
    void shouldRecordCacheErrorWithCorrectMetrics() {
        // Given
        String key = CacheConstants.KeyPrefix.MERCHANT + "789";
        String errorType = "connection_timeout";
        
        // When
        collectorWithSimpleRegistry.recordCacheError(key, errorType);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.errors").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.errors.type").tags("type", errorType).counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.errors.key").tags("key", "merchant").counter().count()).isEqualTo(1);
    }

    @Test
    @DisplayName("Should record cache eviction with correct metrics")
    void shouldRecordCacheEvictionWithCorrectMetrics() {
        // Given
        String key = CacheConstants.KeyPrefix.SESSION + "abc";
        
        // When
        collectorWithSimpleRegistry.recordCacheEviction(key);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.evictions").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.evictions.key").tags("key", "session").counter().count()).isEqualTo(1);
    }

    @Test
    @DisplayName("Should record cache write with correct metrics")
    void shouldRecordCacheWriteWithCorrectMetrics() {
        // Given
        String key = CacheConstants.KeyPrefix.COLLECTION + "list";
        long timeNanos = 2_000_000; // 2ms in nanoseconds
        
        // When
        collectorWithSimpleRegistry.recordCacheWrite(key, timeNanos);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.writes").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.writes.key").tags("key", "collection").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.set.time").timer().totalTime(TimeUnit.NANOSECONDS)).isEqualTo(timeNanos);
    }

    @Test
    @DisplayName("Should record batch cache hit with correct metrics")
    void shouldRecordBatchCacheHitWithCorrectMetrics() {
        // Given
        int hitCount = 5;
        int missCount = 2;
        long timeNanos = 3_000_000; // 3ms in nanoseconds
        
        // When
        collectorWithSimpleRegistry.recordCacheBatchHit(hitCount, missCount, timeNanos);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.hits").counter().count()).isEqualTo(hitCount);
        assertThat(simpleMeterRegistry.get("cache.misses").counter().count()).isEqualTo(missCount);
        assertThat(simpleMeterRegistry.get("cache.batch.hits").counter().count()).isEqualTo(hitCount);
        assertThat(simpleMeterRegistry.get("cache.batch.misses").counter().count()).isEqualTo(missCount);
        assertThat(simpleMeterRegistry.get("cache.get.time").timer().totalTime(TimeUnit.NANOSECONDS)).isEqualTo(timeNanos);
    }

    @Test
    @DisplayName("Should record batch cache miss with correct metrics")
    void shouldRecordBatchCacheMissWithCorrectMetrics() {
        // Given
        int missCount = 7;
        
        // When
        collectorWithSimpleRegistry.recordCacheBatchMiss(missCount);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.misses").counter().count()).isEqualTo(missCount);
        assertThat(simpleMeterRegistry.get("cache.batch.misses").counter().count()).isEqualTo(missCount);
    }

    @Test
    @DisplayName("Should record batch cache write with correct metrics")
    void shouldRecordBatchCacheWriteWithCorrectMetrics() {
        // Given
        int writeCount = 3;
        long timeNanos = 4_000_000; // 4ms in nanoseconds
        
        // When
        collectorWithSimpleRegistry.recordCacheBatchWrite(writeCount, timeNanos);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.writes").counter().count()).isEqualTo(writeCount);
        assertThat(simpleMeterRegistry.get("cache.batch.writes").counter().count()).isEqualTo(writeCount);
        assertThat(simpleMeterRegistry.get("cache.set.time").timer().totalTime(TimeUnit.NANOSECONDS)).isEqualTo(timeNanos);
    }

    @Test
    @DisplayName("Should record batch cache eviction with correct metrics")
    void shouldRecordBatchCacheEvictionWithCorrectMetrics() {
        // Given
        int evictionCount = 10;
        
        // When
        collectorWithSimpleRegistry.recordCacheBatchEviction(evictionCount);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.evictions").counter().count()).isEqualTo(evictionCount);
        assertThat(simpleMeterRegistry.get("cache.batch.evictions").counter().count()).isEqualTo(evictionCount);
    }

    @Test
    @DisplayName("Should calculate hit rate correctly")
    void shouldCalculateHitRateCorrectly() {
        // Given
        collectorWithSimpleRegistry.recordCacheHit("key1", 1000);
        collectorWithSimpleRegistry.recordCacheHit("key2", 1000);
        collectorWithSimpleRegistry.recordCacheHit("key3", 1000);
        collectorWithSimpleRegistry.recordCacheMiss("key4");
        collectorWithSimpleRegistry.recordCacheMiss("key5");
        
        // When
        double hitRate = collectorWithSimpleRegistry.getHitRate();
        
        // Then
        assertThat(hitRate).isEqualTo(60.0); // 3 hits out of 5 total = 60%
    }

    @Test
    @DisplayName("Should calculate error rate correctly")
    void shouldCalculateErrorRateCorrectly() {
        // Given
        collectorWithSimpleRegistry.recordCacheHit("key1", 1000);
        collectorWithSimpleRegistry.recordCacheMiss("key2");
        collectorWithSimpleRegistry.recordCacheWrite("key3", 1000);
        collectorWithSimpleRegistry.recordCacheError("key4", "timeout");
        collectorWithSimpleRegistry.recordCacheError("key5", "connection");
        
        // When
        double errorRate = collectorWithSimpleRegistry.getErrorRate();
        
        // Then
        assertThat(errorRate).isEqualTo(40.0); // 2 errors out of 5 operations = 40%
    }

    @Test
    @DisplayName("Should calculate average get time correctly")
    void shouldCalculateAverageGetTimeCorrectly() {
        // Given
        collectorWithSimpleRegistry.recordCacheHit("key1", 1_000_000); // 1ms
        collectorWithSimpleRegistry.recordCacheHit("key2", 3_000_000); // 3ms
        
        // When
        double avgGetTimeMs = collectorWithSimpleRegistry.getAverageGetTimeMs();
        
        // Then
        assertThat(avgGetTimeMs).isEqualTo(2.0); // Average of 1ms and 3ms = 2ms
    }

    @Test
    @DisplayName("Should calculate average set time correctly")
    void shouldCalculateAverageSetTimeCorrectly() {
        // Given
        collectorWithSimpleRegistry.recordCacheWrite("key1", 2_000_000); // 2ms
        collectorWithSimpleRegistry.recordCacheWrite("key2", 4_000_000); // 4ms
        
        // When
        double avgSetTimeMs = collectorWithSimpleRegistry.getAverageSetTimeMs();
        
        // Then
        assertThat(avgSetTimeMs).isEqualTo(3.0); // Average of 2ms and 4ms = 3ms
    }

    @Test
    @DisplayName("Should handle unknown key categories gracefully")
    void shouldHandleUnknownKeyCategoriesGracefully() {
        // Given
        String unknownKey = "unknown-key-format";
        
        // When
        collectorWithSimpleRegistry.recordCacheHit(unknownKey, 1000);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.hits.key").tags("key", "other").counter().count()).isEqualTo(1);
    }

    @Test
    @DisplayName("Should handle null or empty keys gracefully")
    void shouldHandleNullOrEmptyKeysGracefully() {
        // Given
        String nullKey = null;
        String emptyKey = "";
        
        // When
        collectorWithSimpleRegistry.recordCacheHit(nullKey, 1000);
        collectorWithSimpleRegistry.recordCacheMiss(emptyKey);
        
        // Then
        assertThat(simpleMeterRegistry.get("cache.hits.key").tags("key", "unknown").counter().count()).isEqualTo(1);
        assertThat(simpleMeterRegistry.get("cache.misses.key").tags("key", "unknown").counter().count()).isEqualTo(1);
    }

    @Test
    @DisplayName("Should handle zero operations when calculating rates")
    void shouldHandleZeroOperationsWhenCalculatingRates() {
        // When no operations have been recorded
        double hitRate = collectorWithSimpleRegistry.getHitRate();
        double errorRate = collectorWithSimpleRegistry.getErrorRate();
        
        // Then rates should be zero
        assertThat(hitRate).isEqualTo(0.0);
        assertThat(errorRate).isEqualTo(0.0);
    }

    @Test
    @DisplayName("Should integrate with Spring Boot Actuator's MeterRegistry")
    void shouldIntegrateWithSpringBootActuatorMeterRegistry() {
        // Given
        ArgumentCaptor<Counter> counterCaptor = ArgumentCaptor.forClass(Counter.class);
        
        // When
        verify(mockMeterRegistry, times(5)).counter(counterCaptor.capture());
        
        // Then
        assertThat(counterCaptor.getAllValues()).hasSize(5);
    }

    @Test
    @DisplayName("Should track performance metrics over time")
    void shouldTrackPerformanceMetricsOverTime() {
        // Given - simulate cache operations over time
        // First batch of operations
        collectorWithSimpleRegistry.recordCacheHit("key1", 1_000_000);
        collectorWithSimpleRegistry.recordCacheMiss("key2");
        
        // Verify first batch metrics
        assertThat(collectorWithSimpleRegistry.getHitRate()).isEqualTo(50.0); // 1 hit out of 2 = 50%
        
        // Second batch of operations
        collectorWithSimpleRegistry.recordCacheHit("key3", 2_000_000);
        collectorWithSimpleRegistry.recordCacheHit("key4", 3_000_000);
        collectorWithSimpleRegistry.recordCacheMiss("key5");
        
        // Then - verify metrics have been updated correctly
        assertThat(collectorWithSimpleRegistry.getHitRate()).isEqualTo(60.0); // 3 hits out of 5 = 60%
        assertThat(collectorWithSimpleRegistry.getAverageGetTimeMs()).isEqualTo(2.0); // Average of 1ms, 2ms, and 3ms = 2ms
    }

    @Test
    @DisplayName("Should support alerting thresholds for critical cache metrics")
    void shouldSupportAlertingThresholdsForCriticalCacheMetrics() {
        // Given - simulate a high error rate scenario
        for (int i = 0; i < 8; i++) {
            collectorWithSimpleRegistry.recordCacheError("key" + i, "timeout");
        }
        for (int i = 0; i < 2; i++) {
            collectorWithSimpleRegistry.recordCacheHit("key" + i, 1000);
        }
        
        // When - calculate error rate
        double errorRate = collectorWithSimpleRegistry.getErrorRate();
        
        // Then - verify error rate exceeds critical threshold (e.g., 50%)
        assertThat(errorRate).isGreaterThan(50.0);
        assertThat(errorRate).isEqualTo(80.0); // 8 errors out of 10 operations = 80%
    }
}