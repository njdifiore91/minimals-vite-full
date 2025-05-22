package com.dollarfunding.mca.cache;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.Duration;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link RedisCacheService} that implements the {@link CacheService} interface using Redis.
 * 
 * These tests verify:
 * - Basic cache operations (get, set, delete, exists) with various data types
 * - TTL-based caching with configurable expiration times (15 minutes for application data, 24 hours for sessions)
 * - Error handling and logging for cache operation failures
 * - Serialization/deserialization of complex objects
 * - Performance optimization for high-throughput operations
 */
@ExtendWith(MockitoExtension.class)
public class RedisCacheServiceTest {

    @Mock
    private RedisTemplate<String, Object> redisTemplate;

    @Mock
    private ValueOperations<String, Object> valueOperations;

    @Mock
    private CacheMetricsCollector metricsCollector;

    @Mock
    private CacheKeyGenerator keyGenerator;

    @Captor
    private ArgumentCaptor<Duration> durationCaptor;

    private RedisCacheService cacheService;

    // Test data
    private static final String TEST_KEY = "test:key";
    private static final String TEST_VALUE = "test-value";
    private static final Long TEST_NUMERIC_VALUE = 42L;
    private static final Duration TEST_TTL = Duration.ofMinutes(15);

    @BeforeEach
    void setUp() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        cacheService = new RedisCacheService(redisTemplate, metricsCollector, keyGenerator);
    }

    @Nested
    @DisplayName("Basic Cache Operations Tests")
    class BasicCacheOperationsTests {

        @Test
        @DisplayName("get() should return cached value when key exists")
        void getShouldReturnCachedValueWhenKeyExists() {
            // Arrange
            when(valueOperations.get(TEST_KEY)).thenReturn(TEST_VALUE);

            // Act
            Object result = cacheService.get(TEST_KEY);

            // Assert
            assertEquals(TEST_VALUE, result);
            verify(metricsCollector).recordCacheHit(eq(TEST_KEY), anyLong());
        }

        @Test
        @DisplayName("get() should return null when key does not exist")
        void getShouldReturnNullWhenKeyDoesNotExist() {
            // Arrange
            when(valueOperations.get(TEST_KEY)).thenReturn(null);

            // Act
            Object result = cacheService.get(TEST_KEY);

            // Assert
            assertNull(result);
            verify(metricsCollector).recordCacheMiss(TEST_KEY);
        }

        @Test
        @DisplayName("set() should store value with default TTL")
        void setShouldStoreValueWithDefaultTTL() {
            // Act
            boolean result = cacheService.set(TEST_KEY, TEST_VALUE);

            // Assert
            assertTrue(result);
            verify(valueOperations).set(eq(TEST_KEY), eq(TEST_VALUE), any(Duration.class));
            verify(metricsCollector).recordCacheWrite(eq(TEST_KEY), anyLong());
        }

        @Test
        @DisplayName("set() should store value with custom TTL")
        void setShouldStoreValueWithCustomTTL() {
            // Act
            boolean result = cacheService.set(TEST_KEY, TEST_VALUE, TEST_TTL);

            // Assert
            assertTrue(result);
            verify(valueOperations).set(eq(TEST_KEY), eq(TEST_VALUE), eq(TEST_TTL));
            verify(metricsCollector).recordCacheWrite(eq(TEST_KEY), anyLong());
        }

        @Test
        @DisplayName("delete() should remove value from cache")
        void deleteShouldRemoveValueFromCache() {
            // Arrange
            when(redisTemplate.delete(TEST_KEY)).thenReturn(true);

            // Act
            boolean result = cacheService.delete(TEST_KEY);

            // Assert
            assertTrue(result);
            verify(redisTemplate).delete(TEST_KEY);
            verify(metricsCollector).recordCacheEviction(TEST_KEY);
        }

        @Test
        @DisplayName("delete() should return false when key does not exist")
        void deleteShouldReturnFalseWhenKeyDoesNotExist() {
            // Arrange
            when(redisTemplate.delete(TEST_KEY)).thenReturn(false);

            // Act
            boolean result = cacheService.delete(TEST_KEY);

            // Assert
            assertFalse(result);
            verify(redisTemplate).delete(TEST_KEY);
            verify(metricsCollector, never()).recordCacheEviction(any());
        }

        @Test
        @DisplayName("exists() should return true when key exists")
        void existsShouldReturnTrueWhenKeyExists() {
            // Arrange
            when(redisTemplate.hasKey(TEST_KEY)).thenReturn(true);

            // Act
            boolean result = cacheService.exists(TEST_KEY);

            // Assert
            assertTrue(result);
            verify(redisTemplate).hasKey(TEST_KEY);
        }

        @Test
        @DisplayName("exists() should return false when key does not exist")
        void existsShouldReturnFalseWhenKeyDoesNotExist() {
            // Arrange
            when(redisTemplate.hasKey(TEST_KEY)).thenReturn(false);

            // Act
            boolean result = cacheService.exists(TEST_KEY);

            // Assert
            assertFalse(result);
            verify(redisTemplate).hasKey(TEST_KEY);
        }
    }

    @Nested
    @DisplayName("TTL-based Caching Tests")
    class TTLBasedCachingTests {

        @Test
        @DisplayName("set() should use 15-minute TTL for application data by default")
        void setShouldUse15MinuteTTLForApplicationDataByDefault() {
            // Act
            cacheService.set(TEST_KEY, TEST_VALUE);

            // Assert
            verify(valueOperations).set(eq(TEST_KEY), eq(TEST_VALUE), durationCaptor.capture());
            Duration capturedDuration = durationCaptor.getValue();
            assertEquals(Duration.ofMinutes(CacheConstants.APPLICATION_DATA_TTL_MINUTES), capturedDuration);
        }

        @Test
        @DisplayName("getOrCompute() should use 15-minute TTL for application data by default")
        void getOrComputeShouldUse15MinuteTTLForApplicationDataByDefault() {
            // Arrange
            when(valueOperations.get(TEST_KEY)).thenReturn(null);
            Supplier<String> supplier = () -> TEST_VALUE;

            // Act
            String result = cacheService.getOrCompute(TEST_KEY, supplier);

            // Assert
            assertEquals(TEST_VALUE, result);
            verify(valueOperations).set(eq(TEST_KEY), eq(TEST_VALUE), durationCaptor.capture());
            Duration capturedDuration = durationCaptor.getValue();
            assertEquals(Duration.ofMinutes(CacheConstants.APPLICATION_DATA_TTL_MINUTES), capturedDuration);
        }

        @Test
        @DisplayName("getOrCompute() should use custom TTL when specified")
        void getOrComputeShouldUseCustomTTLWhenSpecified() {
            // Arrange
            when(valueOperations.get(TEST_KEY)).thenReturn(null);
            Supplier<String> supplier = () -> TEST_VALUE;
            Duration customTTL = Duration.ofHours(24);

            // Act
            String result = cacheService.getOrCompute(TEST_KEY, supplier, customTTL);

            // Assert
            assertEquals(TEST_VALUE, result);
            verify(valueOperations).set(eq(TEST_KEY), eq(TEST_VALUE), eq(customTTL));
        }

        @Test
        @DisplayName("getTimeToLive() should return remaining TTL for a key")
        void getTimeToLiveShouldReturnRemainingTTLForKey() {
            // Arrange
            long ttlMillis = 3600000; // 1 hour in milliseconds
            when(redisTemplate.getExpire(TEST_KEY, TimeUnit.MILLISECONDS)).thenReturn(ttlMillis);

            // Act
            long result = cacheService.getTimeToLive(TEST_KEY);

            // Assert
            assertEquals(ttlMillis, result);
            verify(redisTemplate).getExpire(TEST_KEY, TimeUnit.MILLISECONDS);
        }

        @Test
        @DisplayName("updateTimeToLive() should update TTL for a key")
        void updateTimeToLiveShouldUpdateTTLForKey() {
            // Arrange
            Duration newTTL = Duration.ofHours(2);
            when(redisTemplate.expire(TEST_KEY, newTTL.toMillis(), TimeUnit.MILLISECONDS)).thenReturn(true);

            // Act
            boolean result = cacheService.updateTimeToLive(TEST_KEY, newTTL);

            // Assert
            assertTrue(result);
            verify(redisTemplate).expire(TEST_KEY, newTTL.toMillis(), TimeUnit.MILLISECONDS);
        }
    }

    @Nested
    @DisplayName("Error Handling and Logging Tests")
    class ErrorHandlingAndLoggingTests {

        @Test
        @DisplayName("get() should handle Redis connection failure")
        void getShouldHandleRedisConnectionFailure() {
            // Arrange
            when(valueOperations.get(TEST_KEY)).thenThrow(new RedisConnectionFailureException("Connection failed"));

            // Act
            Object result = cacheService.get(TEST_KEY);

            // Assert
            assertNull(result);
            verify(metricsCollector).recordCacheError(eq(TEST_KEY), eq("connection_failure"));
        }

        @Test
        @DisplayName("set() should handle Redis connection failure")
        void setShouldHandleRedisConnectionFailure() {
            // Arrange
            doThrow(new RedisConnectionFailureException("Connection failed"))
                    .when(valueOperations).set(eq(TEST_KEY), eq(TEST_VALUE), any(Duration.class));

            // Act
            boolean result = cacheService.set(TEST_KEY, TEST_VALUE);

            // Assert
            assertFalse(result);
            verify(metricsCollector).recordCacheError(eq(TEST_KEY), eq("connection_failure"));
        }

        @Test
        @DisplayName("delete() should handle Redis connection failure")
        void deleteShouldHandleRedisConnectionFailure() {
            // Arrange
            when(redisTemplate.delete(TEST_KEY)).thenThrow(new RedisConnectionFailureException("Connection failed"));

            // Act
            boolean result = cacheService.delete(TEST_KEY);

            // Assert
            assertFalse(result);
            verify(metricsCollector).recordCacheError(eq(TEST_KEY), eq("connection_failure"));
        }

        @Test
        @DisplayName("executeWithFallback() should use fallback when cache operation fails")
        void executeWithFallbackShouldUseFallbackWhenCacheOperationFails() {
            // Arrange
            Supplier<String> cacheOperation = () -> {
                throw new RuntimeException("Cache operation failed");
            };
            Supplier<String> fallback = () -> "fallback-value";

            // Act
            String result = cacheService.executeWithFallback(cacheOperation, fallback);

            // Assert
            assertEquals("fallback-value", result);
            verify(metricsCollector).recordCacheError(eq("fallback"), eq("operation_failure"));
        }
    }

    @Nested
    @DisplayName("Serialization and Deserialization Tests")
    class SerializationAndDeserializationTests {

        // Test complex object for serialization/deserialization
        static class TestComplexObject {
            private String name;
            private int age;
            private List<String> tags;

            public TestComplexObject(String name, int age, List<String> tags) {
                this.name = name;
                this.age = age;
                this.tags = tags;
            }

            // Getters and setters omitted for brevity

            @Override
            public boolean equals(Object o) {
                if (this == o) return true;
                if (o == null || getClass() != o.getClass()) return false;
                TestComplexObject that = (TestComplexObject) o;
                return age == that.age && 
                       name.equals(that.name) && 
                       tags.equals(that.tags);
            }
        }

        private TestComplexObject testObject;

        @BeforeEach
        void setUpComplexObject() {
            testObject = new TestComplexObject("Test Name", 30, Arrays.asList("tag1", "tag2"));
        }

        @Test
        @DisplayName("set() and get() should handle complex objects correctly")
        void setAndGetShouldHandleComplexObjectsCorrectly() {
            // Arrange
            String complexObjectKey = "test:complex-object";
            when(valueOperations.get(complexObjectKey)).thenReturn(testObject);

            // Act - Set the complex object
            boolean setResult = cacheService.set(complexObjectKey, testObject);
            
            // Act - Get the complex object
            Object getResult = cacheService.get(complexObjectKey);

            // Assert
            assertTrue(setResult);
            assertEquals(testObject, getResult);
            verify(valueOperations).set(eq(complexObjectKey), eq(testObject), any(Duration.class));
            verify(valueOperations).get(complexObjectKey);
        }

        @Test
        @DisplayName("setAll() and multiGet() should handle maps of complex objects")
        void setAllAndMultiGetShouldHandleComplexObjects() {
            // Arrange
            Map<String, TestComplexObject> objectMap = new HashMap<>();
            objectMap.put("test:obj1", testObject);
            objectMap.put("test:obj2", new TestComplexObject("Another Name", 25, Collections.singletonList("tag3")));
            
            List<String> keys = Arrays.asList("test:obj1", "test:obj2");
            List<Object> values = Arrays.asList(objectMap.get("test:obj1"), objectMap.get("test:obj2"));
            
            when(redisTemplate.opsForValue().multiGet(keys)).thenReturn(values);

            // Act
            boolean setResult = cacheService.setAll(objectMap);
            List<Object> getResult = cacheService.multiGet(keys);

            // Assert
            assertTrue(setResult);
            assertEquals(values, getResult);
            verify(redisTemplate.opsForValue()).multiSet(objectMap);
            verify(redisTemplate.opsForValue()).multiGet(keys);
        }
    }

    @Nested
    @DisplayName("Performance Optimization Tests")
    class PerformanceOptimizationTests {

        @Test
        @DisplayName("multiGet() should optimize batch retrieval of cache entries")
        void multiGetShouldOptimizeBatchRetrievalOfCacheEntries() {
            // Arrange
            List<String> keys = Arrays.asList("test:key1", "test:key2", "test:key3");
            List<Object> values = Arrays.asList("value1", "value2", null);
            when(redisTemplate.opsForValue().multiGet(keys)).thenReturn(values);

            // Act
            List<Object> result = cacheService.multiGet(keys);

            // Assert
            assertEquals(values, result);
            verify(redisTemplate.opsForValue(), times(1)).multiGet(keys); // Only one Redis call for multiple keys
            verify(metricsCollector).recordCacheBatchHit(eq(2), eq(1), anyLong()); // 2 hits, 1 miss
        }

        @Test
        @DisplayName("setAll() should optimize batch storage of cache entries")
        void setAllShouldOptimizeBatchStorageOfCacheEntries() {
            // Arrange
            Map<String, String> entries = new HashMap<>();
            entries.put("test:key1", "value1");
            entries.put("test:key2", "value2");
            entries.put("test:key3", "value3");

            // Act
            boolean result = cacheService.setAll(entries);

            // Assert
            assertTrue(result);
            verify(redisTemplate.opsForValue(), times(1)).multiSet(entries); // Only one Redis call for multiple entries
            verify(metricsCollector).recordCacheBatchWrite(eq(entries.size()), anyLong());
        }

        @Test
        @DisplayName("deleteAll() should optimize batch deletion of cache entries")
        void deleteAllShouldOptimizeBatchDeletionOfCacheEntries() {
            // Arrange
            List<String> keys = Arrays.asList("test:key1", "test:key2", "test:key3");
            when(redisTemplate.delete(keys)).thenReturn(3L);

            // Act
            long result = cacheService.deleteAll(keys);

            // Assert
            assertEquals(3L, result);
            verify(redisTemplate, times(1)).delete(keys); // Only one Redis call for multiple deletions
            verify(metricsCollector).recordCacheBatchEviction(3);
        }

        @Test
        @DisplayName("deleteByPattern() should optimize deletion of multiple related cache entries")
        void deleteByPatternShouldOptimizeDeletionOfMultipleRelatedCacheEntries() {
            // Arrange
            String pattern = "test:*";
            Set<String> matchingKeys = Set.of("test:key1", "test:key2", "test:key3");
            when(redisTemplate.keys(pattern)).thenReturn(matchingKeys);
            when(redisTemplate.delete(matchingKeys)).thenReturn(3L);

            // Act
            long result = cacheService.deleteByPattern(pattern);

            // Assert
            assertEquals(3L, result);
            verify(redisTemplate).keys(pattern);
            verify(redisTemplate).delete(matchingKeys);
            verify(metricsCollector).recordCacheBatchEviction(3);
        }
    }
}