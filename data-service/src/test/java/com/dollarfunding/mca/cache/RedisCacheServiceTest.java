package com.dollarfunding.mca.cache;

import com.dollarfunding.mca.TestData;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
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
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.ListOperations;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.SetOperations;
import org.springframework.data.redis.core.ValueOperations;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the RedisCacheService class that implements the CacheService interface using Redis.
 * 
 * These tests verify:
 * 1. Basic cache operations (get, set, delete, exists) with various data types
 * 2. TTL-based caching with 15-minute expiration for application data and 24-hour expiration for sessions
 * 3. Error handling and logging for cache operation failures
 * 4. Serialization/deserialization of complex objects
 * 5. Performance optimization for high-throughput cache operations
 */
@ExtendWith(MockitoExtension.class)
public class RedisCacheServiceTest {

    @Mock
    private RedisTemplate<String, Object> redisTemplate;

    @Mock
    private ValueOperations<String, Object> valueOperations;

    @Mock
    private ListOperations<String, Object> listOperations;

    @Mock
    private SetOperations<String, Object> setOperations;

    @Mock
    private HashOperations<String, Object, Object> hashOperations;

    @Mock
    private CacheMetricsCollector metricsCollector;

    @Captor
    private ArgumentCaptor<String> keyCaptor;

    @Captor
    private ArgumentCaptor<Object> valueCaptor;

    @Captor
    private ArgumentCaptor<Long> ttlCaptor;

    @Captor
    private ArgumentCaptor<TimeUnit> timeUnitCaptor;

    private RedisCacheService cacheService;

    @BeforeEach
    void setUp() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(redisTemplate.opsForList()).thenReturn(listOperations);
        when(redisTemplate.opsForSet()).thenReturn(setOperations);
        when(redisTemplate.opsForHash()).thenReturn(hashOperations);

        cacheService = new RedisCacheService(redisTemplate, metricsCollector);
    }

    @Nested
    @DisplayName("Basic Cache Operations Tests")
    class BasicCacheOperationsTests {

        @Test
        @DisplayName("get() should return value when key exists")
        void getShouldReturnValueWhenKeyExists() {
            // Arrange
            String key = "test-key";
            String value = "test-value";
            when(valueOperations.get(key)).thenReturn(value);

            // Act
            Optional<String> result = cacheService.get(key, String.class);

            // Assert
            assertTrue(result.isPresent());
            assertEquals(value, result.get());
            verify(metricsCollector).recordCacheHit(key);
        }

        @Test
        @DisplayName("get() should return empty when key does not exist")
        void getShouldReturnEmptyWhenKeyDoesNotExist() {
            // Arrange
            String key = "non-existent-key";
            when(valueOperations.get(key)).thenReturn(null);

            // Act
            Optional<String> result = cacheService.get(key, String.class);

            // Assert
            assertFalse(result.isPresent());
            verify(metricsCollector).recordCacheMiss(key);
        }

        @Test
        @DisplayName("set() should store value with default TTL")
        void setShouldStoreValueWithDefaultTTL() {
            // Arrange
            String key = "test-key";
            String value = "test-value";

            // Act
            boolean result = cacheService.set(key, value);

            // Assert
            assertTrue(result);
            verify(valueOperations).set(keyCaptor.capture(), valueCaptor.capture(), ttlCaptor.capture(), timeUnitCaptor.capture());
            assertEquals(key, keyCaptor.getValue());
            assertEquals(value, valueCaptor.getValue());
            assertEquals(CacheService.DEFAULT_DATA_TTL_SECONDS, ttlCaptor.getValue());
            assertEquals(TimeUnit.SECONDS, timeUnitCaptor.getValue());
            verify(metricsCollector).recordCacheWrite(key);
        }

        @Test
        @DisplayName("set() should store value with custom TTL")
        void setShouldStoreValueWithCustomTTL() {
            // Arrange
            String key = "test-key";
            String value = "test-value";
            long ttl = 3600L;
            TimeUnit timeUnit = TimeUnit.SECONDS;

            // Act
            boolean result = cacheService.set(key, value, ttl, timeUnit);

            // Assert
            assertTrue(result);
            verify(valueOperations).set(keyCaptor.capture(), valueCaptor.capture(), ttlCaptor.capture(), timeUnitCaptor.capture());
            assertEquals(key, keyCaptor.getValue());
            assertEquals(value, valueCaptor.getValue());
            assertEquals(ttl, ttlCaptor.getValue());
            assertEquals(timeUnit, timeUnitCaptor.getValue());
            verify(metricsCollector).recordCacheWrite(key);
        }

        @Test
        @DisplayName("delete() should remove value when key exists")
        void deleteShouldRemoveValueWhenKeyExists() {
            // Arrange
            String key = "test-key";
            when(redisTemplate.delete(key)).thenReturn(true);

            // Act
            boolean result = cacheService.delete(key);

            // Assert
            assertTrue(result);
            verify(redisTemplate).delete(key);
            verify(metricsCollector).recordCacheDelete(key);
        }

        @Test
        @DisplayName("delete() should return false when key does not exist")
        void deleteShouldReturnFalseWhenKeyDoesNotExist() {
            // Arrange
            String key = "non-existent-key";
            when(redisTemplate.delete(key)).thenReturn(false);

            // Act
            boolean result = cacheService.delete(key);

            // Assert
            assertFalse(result);
            verify(redisTemplate).delete(key);
            verify(metricsCollector, never()).recordCacheDelete(key);
        }

        @Test
        @DisplayName("exists() should return true when key exists")
        void existsShouldReturnTrueWhenKeyExists() {
            // Arrange
            String key = "test-key";
            when(redisTemplate.hasKey(key)).thenReturn(true);

            // Act
            boolean result = cacheService.exists(key);

            // Assert
            assertTrue(result);
            verify(redisTemplate).hasKey(key);
        }

        @Test
        @DisplayName("exists() should return false when key does not exist")
        void existsShouldReturnFalseWhenKeyDoesNotExist() {
            // Arrange
            String key = "non-existent-key";
            when(redisTemplate.hasKey(key)).thenReturn(false);

            // Act
            boolean result = cacheService.exists(key);

            // Assert
            assertFalse(result);
            verify(redisTemplate).hasKey(key);
        }
    }

    @Nested
    @DisplayName("Complex Data Type Tests")
    class ComplexDataTypeTests {

        @Test
        @DisplayName("get() and set() should work with complex objects")
        void getAndSetShouldWorkWithComplexObjects() {
            // Arrange
            String key = "application:123";
            Application application = TestData.createApplication();
            when(valueOperations.get(key)).thenReturn(application);

            // Act - Set the value
            boolean setResult = cacheService.set(key, application);

            // Assert - Set operation
            assertTrue(setResult);
            verify(valueOperations).set(eq(key), eq(application), anyLong(), any(TimeUnit.class));
            verify(metricsCollector).recordCacheWrite(key);

            // Act - Get the value
            Optional<Application> getResult = cacheService.get(key, Application.class);

            // Assert - Get operation
            assertTrue(getResult.isPresent());
            assertEquals(application, getResult.get());
            verify(metricsCollector).recordCacheHit(key);
        }

        @Test
        @DisplayName("multiGet() should retrieve multiple values")
        void multiGetShouldRetrieveMultipleValues() {
            // Arrange
            List<String> keys = Arrays.asList("key1", "key2", "key3");
            List<Object> values = Arrays.asList("value1", "value2", "value3");
            when(valueOperations.multiGet(keys)).thenReturn(values);

            // Act
            Map<String, String> result = cacheService.multiGet(keys, String.class);

            // Assert
            assertEquals(3, result.size());
            assertEquals("value1", result.get("key1"));
            assertEquals("value2", result.get("key2"));
            assertEquals("value3", result.get("key3"));
            verify(metricsCollector, times(3)).recordCacheHit(anyString());
        }

        @Test
        @DisplayName("multiSet() should store multiple values with default TTL")
        void multiSetShouldStoreMultipleValuesWithDefaultTTL() {
            // Arrange
            Map<String, String> map = new HashMap<>();
            map.put("key1", "value1");
            map.put("key2", "value2");
            map.put("key3", "value3");

            // Act
            boolean result = cacheService.multiSet(map);

            // Assert
            assertTrue(result);
            verify(valueOperations).multiSet(anyMap());
            verify(redisTemplate, times(3)).expire(anyString(), eq(CacheService.DEFAULT_DATA_TTL_SECONDS), eq(TimeUnit.SECONDS));
            verify(metricsCollector, times(3)).recordCacheWrite(anyString());
        }

        @Test
        @DisplayName("listOperations should work correctly")
        void listOperationsShouldWorkCorrectly() {
            // Arrange
            String key = "list:test";
            String value = "list-item";
            when(listOperations.rightPush(key, value)).thenReturn(1L);
            when(listOperations.size(key)).thenReturn(1L);
            when(listOperations.range(key, 0, 0)).thenReturn(Collections.singletonList(value));

            // Act - Add to list
            long addResult = cacheService.listAdd(key, value);

            // Assert - Add operation
            assertEquals(1L, addResult);
            verify(listOperations).rightPush(key, value);
            verify(metricsCollector).recordCacheWrite(key);

            // Act - Get all from list
            List<String> getAllResult = cacheService.listGetAll(key, String.class);

            // Assert - Get all operation
            assertEquals(1, getAllResult.size());
            assertEquals(value, getAllResult.get(0));
            verify(listOperations).size(key);
            verify(listOperations).range(key, 0, 0);
            verify(metricsCollector).recordCacheHit(key);
        }

        @Test
        @DisplayName("setOperations should work correctly")
        void setOperationsShouldWorkCorrectly() {
            // Arrange
            String key = "set:test";
            String value = "set-item";
            when(setOperations.add(key, value)).thenReturn(1L);
            when(setOperations.members(key)).thenReturn(Collections.singleton(value));

            // Act - Add to set
            boolean addResult = cacheService.setAdd(key, value);

            // Assert - Add operation
            assertTrue(addResult);
            verify(setOperations).add(key, value);
            verify(metricsCollector).recordCacheWrite(key);

            // Act - Get all from set
            Set<String> getAllResult = cacheService.setGetAll(key, String.class);

            // Assert - Get all operation
            assertEquals(1, getAllResult.size());
            assertTrue(getAllResult.contains(value));
            verify(setOperations).members(key);
            verify(metricsCollector).recordCacheHit(key);
        }

        @Test
        @DisplayName("hashOperations should work correctly")
        void hashOperationsShouldWorkCorrectly() {
            // Arrange
            String key = "hash:test";
            String field = "field1";
            String value = "hash-value";
            Map<Object, Object> entries = new HashMap<>();
            entries.put(field, value);

            when(hashOperations.get(key, field)).thenReturn(value);
            when(hashOperations.entries(key)).thenReturn(entries);

            // Act - Set hash field
            boolean setResult = cacheService.hashSet(key, field, value);

            // Assert - Set operation
            assertTrue(setResult);
            verify(hashOperations).put(key, field, value);
            verify(metricsCollector).recordCacheWrite(key + ":" + field);

            // Act - Get hash field
            Optional<String> getResult = cacheService.hashGet(key, field, String.class);

            // Assert - Get operation
            assertTrue(getResult.isPresent());
            assertEquals(value, getResult.get());
            verify(hashOperations).get(key, field);
            verify(metricsCollector).recordCacheHit(key + ":" + field);

            // Act - Get all hash fields
            Map<String, String> getAllResult = cacheService.hashGetAll(key, String.class);

            // Assert - Get all operation
            assertEquals(1, getAllResult.size());
            assertEquals(value, getAllResult.get(field));
            verify(hashOperations).entries(key);
            verify(metricsCollector).recordCacheHit(key);
        }
    }

    @Nested
    @DisplayName("TTL-Based Caching Tests")
    class TTLBasedCachingTests {

        @Test
        @DisplayName("set() should use default application data TTL (15 minutes)")
        void setShouldUseDefaultApplicationDataTTL() {
            // Arrange
            String key = "application:data";
            String value = "application-data";

            // Act
            cacheService.set(key, value);

            // Assert
            verify(valueOperations).set(eq(key), eq(value), eq(CacheService.DEFAULT_DATA_TTL_SECONDS), eq(TimeUnit.SECONDS));
        }

        @Test
        @DisplayName("set() should use custom session TTL (24 hours)")
        void setShouldUseCustomSessionTTL() {
            // Arrange
            String key = "session:data";
            String value = "session-data";

            // Act
            cacheService.set(key, value, CacheService.DEFAULT_SESSION_TTL_SECONDS, TimeUnit.SECONDS);

            // Assert
            verify(valueOperations).set(eq(key), eq(value), eq(CacheService.DEFAULT_SESSION_TTL_SECONDS), eq(TimeUnit.SECONDS));
        }

        @Test
        @DisplayName("expire() should set TTL for existing key")
        void expireShouldSetTTLForExistingKey() {
            // Arrange
            String key = "test-key";
            long ttl = 3600L;
            TimeUnit timeUnit = TimeUnit.SECONDS;
            when(redisTemplate.expire(key, ttl, timeUnit)).thenReturn(true);

            // Act
            boolean result = cacheService.expire(key, ttl, timeUnit);

            // Assert
            assertTrue(result);
            verify(redisTemplate).expire(key, ttl, timeUnit);
        }

        @Test
        @DisplayName("getExpire() should return TTL for existing key")
        void getExpireShouldReturnTTLForExistingKey() {
            // Arrange
            String key = "test-key";
            long ttl = 3600L;
            TimeUnit timeUnit = TimeUnit.SECONDS;
            when(redisTemplate.getExpire(key, timeUnit)).thenReturn(ttl);

            // Act
            long result = cacheService.getExpire(key, timeUnit);

            // Assert
            assertEquals(ttl, result);
            verify(redisTemplate).getExpire(key, timeUnit);
        }

        @Test
        @DisplayName("persist() should remove TTL for existing key")
        void persistShouldRemoveTTLForExistingKey() {
            // Arrange
            String key = "test-key";
            when(redisTemplate.persist(key)).thenReturn(true);

            // Act
            boolean result = cacheService.persist(key);

            // Assert
            assertTrue(result);
            verify(redisTemplate).persist(key);
        }
    }

    @Nested
    @DisplayName("Error Handling Tests")
    class ErrorHandlingTests {

        @Test
        @DisplayName("get() should handle RedisConnectionFailureException")
        void getShouldHandleRedisConnectionFailureException() {
            // Arrange
            String key = "test-key";
            when(valueOperations.get(key)).thenThrow(new RedisConnectionFailureException("Connection failed"));

            // Act
            Optional<String> result = cacheService.get(key, String.class);

            // Assert
            assertFalse(result.isPresent());
            verify(metricsCollector).recordCacheError(eq(key), eq("connection_failure"));
        }

        @Test
        @DisplayName("get() should handle ClassCastException")
        void getShouldHandleClassCastException() {
            // Arrange
            String key = "test-key";
            Integer value = 123; // Return Integer when String is expected
            when(valueOperations.get(key)).thenReturn(value);

            // Act
            Optional<String> result = cacheService.get(key, String.class);

            // Assert
            assertFalse(result.isPresent());
            verify(metricsCollector).recordCacheError(eq(key), eq("type_mismatch"));
        }

        @Test
        @DisplayName("set() should handle RedisConnectionFailureException")
        void setShouldHandleRedisConnectionFailureException() {
            // Arrange
            String key = "test-key";
            String value = "test-value";
            doThrow(new RedisConnectionFailureException("Connection failed"))
                    .when(valueOperations).set(eq(key), eq(value), anyLong(), any(TimeUnit.class));

            // Act
            boolean result = cacheService.set(key, value);

            // Assert
            assertFalse(result);
            verify(metricsCollector).recordCacheError(eq(key), eq("connection_failure"));
        }

        @Test
        @DisplayName("delete() should handle RedisConnectionFailureException")
        void deleteShouldHandleRedisConnectionFailureException() {
            // Arrange
            String key = "test-key";
            when(redisTemplate.delete(key)).thenThrow(new RedisConnectionFailureException("Connection failed"));

            // Act
            boolean result = cacheService.delete(key);

            // Assert
            assertFalse(result);
            verify(metricsCollector).recordCacheError(eq(key), eq("connection_failure"));
        }

        @Test
        @DisplayName("multiGet() should handle null values")
        void multiGetShouldHandleNullValues() {
            // Arrange
            List<String> keys = Arrays.asList("key1", "key2", "key3");
            when(valueOperations.multiGet(keys)).thenReturn(null);

            // Act
            Map<String, String> result = cacheService.multiGet(keys, String.class);

            // Assert
            assertTrue(result.isEmpty());
        }

        @Test
        @DisplayName("multiGet() should handle type mismatches")
        void multiGetShouldHandleTypeMismatches() {
            // Arrange
            List<String> keys = Arrays.asList("key1", "key2");
            List<Object> values = Arrays.asList("value1", 123); // Second value is Integer, not String
            when(valueOperations.multiGet(keys)).thenReturn(values);

            // Act
            Map<String, String> result = cacheService.multiGet(keys, String.class);

            // Assert
            assertEquals(1, result.size());
            assertEquals("value1", result.get("key1"));
            assertFalse(result.containsKey("key2"));
            verify(metricsCollector).recordCacheError(eq("key2"), eq("type_mismatch"));
        }
    }

    @Nested
    @DisplayName("Performance Optimization Tests")
    class PerformanceOptimizationTests {

        @Test
        @DisplayName("multiSet() should use pipelined operations for better performance")
        void multiSetShouldUsePipelinedOperationsForBetterPerformance() {
            // Arrange
            Map<String, String> map = new HashMap<>();
            map.put("key1", "value1");
            map.put("key2", "value2");
            map.put("key3", "value3");

            // Act
            boolean result = cacheService.multiSet(map);

            // Assert
            assertTrue(result);
            verify(valueOperations).multiSet(anyMap()); // Should use multiSet for better performance
            verify(redisTemplate, times(3)).expire(anyString(), anyLong(), any(TimeUnit.class));
        }

        @Test
        @DisplayName("multiDelete() should use batch delete for better performance")
        void multiDeleteShouldUseBatchDeleteForBetterPerformance() {
            // Arrange
            List<String> keys = Arrays.asList("key1", "key2", "key3");
            when(redisTemplate.delete(keys)).thenReturn(3L);

            // Act
            long result = cacheService.multiDelete(keys);

            // Assert
            assertEquals(3L, result);
            verify(redisTemplate).delete(keys); // Should use batch delete for better performance
            verify(metricsCollector, times(3)).recordCacheDelete(anyString());
        }

        @Test
        @DisplayName("multiExists() should optimize key existence checks")
        void multiExistsShouldOptimizeKeyExistenceChecks() {
            // Arrange
            List<String> keys = Arrays.asList("key1", "key2", "key3");
            when(redisTemplate.hasKey("key1")).thenReturn(true);
            when(redisTemplate.hasKey("key2")).thenReturn(false);
            when(redisTemplate.hasKey("key3")).thenReturn(true);

            // Act
            Set<String> result = cacheService.multiExists(keys);

            // Assert
            assertEquals(2, result.size());
            assertTrue(result.contains("key1"));
            assertTrue(result.contains("key3"));
            assertFalse(result.contains("key2"));
            verify(redisTemplate, times(3)).hasKey(anyString());
        }

        @Test
        @DisplayName("clear() should efficiently clear all keys")
        void clearShouldEfficientlyClearAllKeys() {
            // Arrange
            Set<String> allKeys = new HashSet<>(Arrays.asList("key1", "key2", "key3"));
            when(redisTemplate.keys("*")).thenReturn(allKeys);
            when(redisTemplate.delete(allKeys)).thenReturn(3L);

            // Act
            boolean result = cacheService.clear();

            // Assert
            assertTrue(result);
            verify(redisTemplate).keys("*");
            verify(redisTemplate).delete(allKeys);
            verify(metricsCollector).recordCacheClear();
        }
    }

    @Nested
    @DisplayName("Counter Operations Tests")
    class CounterOperationsTests {

        @Test
        @DisplayName("increment() should atomically increase counter")
        void incrementShouldAtomicallyIncreaseCounter() {
            // Arrange
            String key = "counter:test";
            long delta = 5L;
            when(valueOperations.increment(key, delta)).thenReturn(5L);

            // Act
            long result = cacheService.increment(key, delta);

            // Assert
            assertEquals(5L, result);
            verify(valueOperations).increment(key, delta);
            verify(metricsCollector).recordCacheWrite(key);
        }

        @Test
        @DisplayName("decrement() should atomically decrease counter")
        void decrementShouldAtomicallyDecreaseCounter() {
            // Arrange
            String key = "counter:test";
            long delta = 3L;
            when(valueOperations.decrement(key, delta)).thenReturn(7L);

            // Act
            long result = cacheService.decrement(key, delta);

            // Assert
            assertEquals(7L, result);
            verify(valueOperations).decrement(key, delta);
            verify(metricsCollector).recordCacheWrite(key);
        }

        @Test
        @DisplayName("increment() should handle RedisConnectionFailureException")
        void incrementShouldHandleRedisConnectionFailureException() {
            // Arrange
            String key = "counter:test";
            long delta = 5L;
            when(valueOperations.increment(key, delta))
                    .thenThrow(new RedisConnectionFailureException("Connection failed"));

            // Act
            long result = cacheService.increment(key, delta);

            // Assert
            assertEquals(0L, result);
            verify(metricsCollector).recordCacheError(eq(key), eq("connection_failure"));
        }
    }
}