package com.dollarfunding.mca.cache;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.*;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link CacheEvictionScheduler} class.
 * 
 * These tests verify the scheduled cache maintenance tasks including:
 * - Eviction of stale data based on configurable TTL criteria
 * - Pattern-based cache clearing
 * - Logging of cache statistics for monitoring purposes
 * - Eviction policy configuration based on memory usage and access patterns
 */
@ExtendWith(MockitoExtension.class)
public class CacheEvictionSchedulerTest {

    @Mock
    private RedisTemplate<String, Object> redisTemplate;
    
    @Mock
    private CacheMetricsCollector metricsCollector;
    
    @Mock
    private RedisCacheService cacheService;
    
    @Mock
    private RedisConnectionFactory connectionFactory;
    
    @Mock
    private RedisConnection redisConnection;
    
    private CacheEvictionScheduler cacheEvictionScheduler;
    
    @BeforeEach
    public void setUp() {
        // Setup mock behavior for Redis connection
        when(redisTemplate.getConnectionFactory()).thenReturn(connectionFactory);
        when(connectionFactory.getConnection()).thenReturn(redisConnection);
        
        // Create the scheduler with mocked dependencies
        cacheEvictionScheduler = new CacheEvictionScheduler(redisTemplate, metricsCollector, cacheService);
        
        // Set configurable properties using reflection
        ReflectionTestUtils.setField(cacheEvictionScheduler, "memoryThreshold", 0.8);
        ReflectionTestUtils.setField(cacheEvictionScheduler, "idleTimeMinutes", 30L);
        ReflectionTestUtils.setField(cacheEvictionScheduler, "maxKeysPerScan", 1000L);
        ReflectionTestUtils.setField(cacheEvictionScheduler, "evictionEnabled", true);
        ReflectionTestUtils.setField(cacheEvictionScheduler, "logIntervalMinutes", 60L);
    }
    
    /**
     * Test that the eviction of stale application data works correctly.
     * This verifies that the scheduler correctly identifies and evicts stale data
     * based on the configured idle time threshold.
     */
    @Test
    public void testEvictStaleApplicationData() {
        // Setup test data
        Set<String> applicationKeys = new HashSet<>(Arrays.asList("app:1", "app:2", "app:3"));
        Set<String> documentKeys = new HashSet<>(Arrays.asList("doc:1", "doc:2"));
        Set<String> merchantKeys = new HashSet<>(Arrays.asList("merchant:1"));
        
        // Mock Redis keys method to return our test keys for different patterns
        when(redisTemplate.keys(CacheConstants.KeyPrefix.APPLICATION + "*")).thenReturn(applicationKeys);
        when(redisTemplate.keys(CacheConstants.KeyPrefix.DOCUMENT + "*")).thenReturn(documentKeys);
        when(redisTemplate.keys(CacheConstants.KeyPrefix.MERCHANT + "*")).thenReturn(merchantKeys);
        
        // Mock idle time for keys - some above threshold, some below
        mockIdleTime("app:1", 40 * 60); // 40 minutes (above threshold)
        mockIdleTime("app:2", 20 * 60); // 20 minutes (below threshold)
        mockIdleTime("app:3", 35 * 60); // 35 minutes (above threshold)
        mockIdleTime("doc:1", 15 * 60); // 15 minutes (below threshold)
        mockIdleTime("doc:2", 45 * 60); // 45 minutes (above threshold)
        mockIdleTime("merchant:1", 50 * 60); // 50 minutes (above threshold)
        
        // Mock successful deletion for some keys
        when(cacheService.delete("app:1")).thenReturn(true);
        when(cacheService.delete("app:3")).thenReturn(true);
        when(cacheService.delete("doc:2")).thenReturn(true);
        when(cacheService.delete("merchant:1")).thenReturn(true);
        
        // Execute the method under test
        cacheEvictionScheduler.evictStaleApplicationData();
        
        // Verify that keys with idle time above threshold were deleted
        verify(cacheService, times(1)).delete("app:1");
        verify(cacheService, times(0)).delete("app:2"); // Should not be deleted (below threshold)
        verify(cacheService, times(1)).delete("app:3");
        verify(cacheService, times(0)).delete("doc:1"); // Should not be deleted (below threshold)
        verify(cacheService, times(1)).delete("doc:2");
        verify(cacheService, times(1)).delete("merchant:1");
    }
    
    /**
     * Test that the eviction of stale session data works correctly.
     * This verifies that the scheduler correctly identifies and evicts stale session data
     * based on the configured idle time threshold.
     */
    @Test
    public void testEvictStaleSessionData() {
        // Setup test data
        Set<String> sessionKeys = new HashSet<>(Arrays.asList("session:1", "session:2", "session:3"));
        
        // Mock Redis keys method to return our test keys
        when(redisTemplate.keys(CacheConstants.KeyPrefix.SESSION + "*")).thenReturn(sessionKeys);
        
        // Mock idle time for keys - some above threshold, some below
        mockIdleTime("session:1", 20 * 60); // 20 minutes (below threshold)
        mockIdleTime("session:2", 40 * 60); // 40 minutes (above threshold)
        mockIdleTime("session:3", 15 * 60); // 15 minutes (below threshold)
        
        // Mock successful deletion for some keys
        when(cacheService.delete("session:2")).thenReturn(true);
        
        // Execute the method under test
        cacheEvictionScheduler.evictStaleSessionData();
        
        // Verify that only keys with idle time above threshold were deleted
        verify(cacheService, times(0)).delete("session:1"); // Should not be deleted (below threshold)
        verify(cacheService, times(1)).delete("session:2");
        verify(cacheService, times(0)).delete("session:3"); // Should not be deleted (below threshold)
    }
    
    /**
     * Test that the eviction of stale lookup data works correctly.
     * This verifies that the scheduler correctly identifies and evicts stale lookup data
     * based on the configured idle time threshold.
     */
    @Test
    public void testEvictStaleLookupData() {
        // Setup test data
        Set<String> lookupKeys = new HashSet<>(Arrays.asList("lookup:1", "lookup:2", "lookup:3"));
        
        // Mock Redis keys method to return our test keys
        when(redisTemplate.keys(CacheConstants.KeyPrefix.LOOKUP + "*")).thenReturn(lookupKeys);
        
        // Mock idle time for keys - some above threshold, some below
        mockIdleTime("lookup:1", 35 * 60); // 35 minutes (above threshold)
        mockIdleTime("lookup:2", 25 * 60); // 25 minutes (below threshold)
        mockIdleTime("lookup:3", 45 * 60); // 45 minutes (above threshold)
        
        // Mock successful deletion for some keys
        when(cacheService.delete("lookup:1")).thenReturn(true);
        when(cacheService.delete("lookup:3")).thenReturn(true);
        
        // Execute the method under test
        cacheEvictionScheduler.evictStaleLookupData();
        
        // Verify that only keys with idle time above threshold were deleted
        verify(cacheService, times(1)).delete("lookup:1");
        verify(cacheService, times(0)).delete("lookup:2"); // Should not be deleted (below threshold)
        verify(cacheService, times(1)).delete("lookup:3");
    }
    
    /**
     * Test that the memory usage monitoring and adaptive eviction works correctly.
     * This verifies that the scheduler correctly monitors memory usage and performs
     * adaptive eviction when memory usage exceeds the configured threshold.
     */
    @Test
    public void testMonitorMemoryUsageWithHighMemoryUsage() {
        // Setup memory info with high memory usage (above threshold)
        Map<String, Object> memoryInfo = new HashMap<>();
        memoryInfo.put("used_memory", "800000"); // 800KB
        memoryInfo.put("maxmemory", "1000000"); // 1MB
        when(redisConnection.info("memory")).thenReturn(memoryInfo);
        
        // Mock the performAdaptiveEviction method to verify it's called
        CacheEvictionScheduler spyScheduler = Mockito.spy(cacheEvictionScheduler);
        doReturn(5L).when(spyScheduler).performAdaptiveEviction(anyDouble());
        
        // Execute the method under test
        spyScheduler.monitorMemoryUsage();
        
        // Verify that adaptive eviction was performed due to high memory usage
        verify(spyScheduler, times(1)).performAdaptiveEviction(0.8); // 800KB/1MB = 0.8
    }
    
    /**
     * Test that the memory usage monitoring does not trigger adaptive eviction
     * when memory usage is below the configured threshold.
     */
    @Test
    public void testMonitorMemoryUsageWithLowMemoryUsage() {
        // Setup memory info with low memory usage (below threshold)
        Map<String, Object> memoryInfo = new HashMap<>();
        memoryInfo.put("used_memory", "500000"); // 500KB
        memoryInfo.put("maxmemory", "1000000"); // 1MB
        when(redisConnection.info("memory")).thenReturn(memoryInfo);
        
        // Mock the performAdaptiveEviction method to verify it's not called
        CacheEvictionScheduler spyScheduler = Mockito.spy(cacheEvictionScheduler);
        
        // Execute the method under test
        spyScheduler.monitorMemoryUsage();
        
        // Verify that adaptive eviction was not performed due to low memory usage
        verify(spyScheduler, never()).performAdaptiveEviction(anyDouble());
    }
    
    /**
     * Test that the adaptive eviction correctly evicts keys based on memory usage.
     * This verifies that the scheduler correctly prioritizes keys for eviction
     * based on TTL and access patterns.
     */
    @Test
    public void testPerformAdaptiveEviction() {
        // Setup memory info for initial and post-eviction checks
        Map<String, Object> initialMemoryInfo = new HashMap<>();
        initialMemoryInfo.put("used_memory", "900000"); // 900KB
        initialMemoryInfo.put("maxmemory", "1000000"); // 1MB
        
        Map<String, Object> reducedMemoryInfo = new HashMap<>();
        reducedMemoryInfo.put("used_memory", "700000"); // 700KB after eviction
        reducedMemoryInfo.put("maxmemory", "1000000"); // 1MB
        
        // Mock the memory info calls to return different values on successive calls
        when(redisConnection.info("memory"))
            .thenReturn(initialMemoryInfo)
            .thenReturn(reducedMemoryInfo);
        
        // Mock the eviction methods to return counts of evicted keys
        CacheEvictionScheduler spyScheduler = Mockito.spy(cacheEvictionScheduler);
        doReturn(5L).when(spyScheduler).evictNearExpiryKeys();
        doReturn(0L).when(spyScheduler).evictLeastRecentlyUsedKeys(anyString());
        
        // Execute the method under test
        long evictedCount = spyScheduler.performAdaptiveEviction(0.9); // 90% memory usage
        
        // Verify that the correct number of keys were evicted
        assertEquals(5L, evictedCount);
        
        // Verify that near-expiry keys were evicted first
        verify(spyScheduler, times(1)).evictNearExpiryKeys();
        
        // Verify that LRU eviction was not needed since memory usage was reduced enough
        verify(spyScheduler, never()).evictLeastRecentlyUsedKeys(anyString());
    }
    
    /**
     * Test that the adaptive eviction correctly evicts LRU keys when near-expiry
     * eviction is not sufficient to reduce memory usage.
     */
    @Test
    public void testPerformAdaptiveEvictionWithLRU() {
        // Setup memory info for initial, post-near-expiry, and post-LRU checks
        Map<String, Object> initialMemoryInfo = new HashMap<>();
        initialMemoryInfo.put("used_memory", "900000"); // 900KB
        initialMemoryInfo.put("maxmemory", "1000000"); // 1MB
        
        Map<String, Object> afterNearExpiryMemoryInfo = new HashMap<>();
        afterNearExpiryMemoryInfo.put("used_memory", "850000"); // 850KB after near-expiry eviction
        afterNearExpiryMemoryInfo.put("maxmemory", "1000000"); // 1MB
        
        Map<String, Object> afterLRUMemoryInfo = new HashMap<>();
        afterLRUMemoryInfo.put("used_memory", "700000"); // 700KB after LRU eviction
        afterLRUMemoryInfo.put("maxmemory", "1000000"); // 1MB
        
        // Mock the memory info calls to return different values on successive calls
        when(redisConnection.info("memory"))
            .thenReturn(initialMemoryInfo)
            .thenReturn(afterNearExpiryMemoryInfo)
            .thenReturn(afterLRUMemoryInfo);
        
        // Mock the eviction methods to return counts of evicted keys
        CacheEvictionScheduler spyScheduler = Mockito.spy(cacheEvictionScheduler);
        doReturn(3L).when(spyScheduler).evictNearExpiryKeys();
        doReturn(5L).when(spyScheduler).evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.APPLICATION + "*");
        doReturn(2L).when(spyScheduler).evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.DOCUMENT + "*");
        doReturn(1L).when(spyScheduler).evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.MERCHANT + "*");
        
        // Execute the method under test
        long evictedCount = spyScheduler.performAdaptiveEviction(0.9); // 90% memory usage
        
        // Verify that the correct number of keys were evicted
        assertEquals(11L, evictedCount); // 3 + 5 + 2 + 1 = 11
        
        // Verify that near-expiry keys were evicted first
        verify(spyScheduler, times(1)).evictNearExpiryKeys();
        
        // Verify that LRU eviction was performed for application data
        verify(spyScheduler, times(1)).evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.APPLICATION + "*");
        verify(spyScheduler, times(1)).evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.DOCUMENT + "*");
        verify(spyScheduler, times(1)).evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.MERCHANT + "*");
        
        // Verify that session data eviction was not needed
        verify(spyScheduler, never()).evictLeastRecentlyUsedKeys(CacheConstants.KeyPrefix.SESSION + "*");
    }
    
    /**
     * Test that the pattern-based cache clearing works correctly.
     * This verifies that the scheduler correctly identifies and clears all keys
     * matching a specified pattern.
     */
    @Test
    public void testClearCacheByPattern() {
        // Setup test data
        String pattern = "test:*";
        Set<String> matchingKeys = new HashSet<>(Arrays.asList("test:1", "test:2", "test:3"));
        
        // Mock Redis keys method to return our test keys
        when(redisTemplate.keys(pattern)).thenReturn(matchingKeys);
        
        // Mock successful deletion
        when(redisTemplate.delete(matchingKeys)).thenReturn(3L);
        
        // Execute the method under test
        long deletedCount = cacheEvictionScheduler.clearCacheByPattern(pattern);
        
        // Verify that the correct number of keys were deleted
        assertEquals(3L, deletedCount);
        
        // Verify that the delete method was called with the correct keys
        verify(redisTemplate, times(1)).delete(matchingKeys);
    }
    
    /**
     * Test that the cache statistics logging works correctly.
     * This verifies that the scheduler correctly logs cache statistics
     * at the configured interval.
     */
    @Test
    public void testLogCacheStatistics() {
        // Setup memory info
        Map<String, Object> memoryInfo = new HashMap<>();
        memoryInfo.put("used_memory", "500000"); // 500KB
        memoryInfo.put("maxmemory", "1000000"); // 1MB
        when(redisConnection.info("memory")).thenReturn(memoryInfo);
        
        // Mock metrics snapshot
        Map<String, Map<String, Number>> metricsSnapshot = new HashMap<>();
        Map<String, Number> appMetrics = new HashMap<>();
        appMetrics.put("hits", 100);
        appMetrics.put("misses", 20);
        appMetrics.put("puts", 50);
        appMetrics.put("evictions", 5);
        appMetrics.put("size", 45);
        appMetrics.put("hitRatio", 0.83);
        metricsSnapshot.put(CacheConstants.CacheName.APPLICATIONS, appMetrics);
        
        when(metricsCollector.getMetricsSnapshot()).thenReturn(metricsSnapshot);
        
        // Set last stats log time to be older than the log interval
        ReflectionTestUtils.setField(cacheEvictionScheduler, "lastStatsLogTime", 
                java.time.LocalDateTime.now().minusMinutes(61));
        
        // Execute the method under test
        cacheEvictionScheduler.logCacheStatistics();
        
        // Verify that metrics were retrieved
        verify(metricsCollector, times(1)).getMetricsSnapshot();
        
        // Verify that memory info was retrieved
        verify(redisConnection, times(1)).info("memory");
    }
    
    /**
     * Test that the eviction settings can be updated correctly.
     * This verifies that the scheduler correctly updates its configuration
     * when the updateEvictionSettings method is called.
     */
    @Test
    public void testUpdateEvictionSettings() {
        // Setup new settings
        Map<String, Object> newSettings = new HashMap<>();
        newSettings.put("evictionEnabled", false);
        newSettings.put("memoryThreshold", 0.7);
        newSettings.put("idleTimeMinutes", 45L);
        newSettings.put("maxKeysPerScan", 500L);
        newSettings.put("logIntervalMinutes", 30L);
        
        // Execute the method under test
        cacheEvictionScheduler.updateEvictionSettings(newSettings);
        
        // Verify that the settings were updated
        assertEquals(false, ReflectionTestUtils.getField(cacheEvictionScheduler, "evictionEnabled"));
        assertEquals(0.7, ReflectionTestUtils.getField(cacheEvictionScheduler, "memoryThreshold"));
        assertEquals(45L, ReflectionTestUtils.getField(cacheEvictionScheduler, "idleTimeMinutes"));
        assertEquals(500L, ReflectionTestUtils.getField(cacheEvictionScheduler, "maxKeysPerScan"));
        assertEquals(30L, ReflectionTestUtils.getField(cacheEvictionScheduler, "logIntervalMinutes"));
    }
    
    /**
     * Test that the eviction is skipped when evictionEnabled is set to false.
     * This verifies that the scheduler respects the evictionEnabled flag.
     */
    @Test
    public void testEvictionSkippedWhenDisabled() {
        // Disable eviction
        ReflectionTestUtils.setField(cacheEvictionScheduler, "evictionEnabled", false);
        
        // Execute the methods under test
        cacheEvictionScheduler.evictStaleApplicationData();
        cacheEvictionScheduler.evictStaleSessionData();
        cacheEvictionScheduler.evictStaleLookupData();
        cacheEvictionScheduler.monitorMemoryUsage();
        
        // Verify that no Redis operations were performed
        verify(redisTemplate, never()).keys(anyString());
        verify(redisConnection, never()).info(anyString());
    }
    
    /**
     * Test that the getEvictionSettings method returns the correct settings.
     * This verifies that the scheduler correctly reports its current configuration.
     */
    @Test
    public void testGetEvictionSettings() {
        // Setup expected settings
        boolean evictionEnabled = true;
        double memoryThreshold = 0.8;
        long idleTimeMinutes = 30L;
        long maxKeysPerScan = 1000L;
        long logIntervalMinutes = 60L;
        
        // Execute the method under test
        Map<String, Object> settings = cacheEvictionScheduler.getEvictionSettings();
        
        // Verify that the settings match the expected values
        assertEquals(evictionEnabled, settings.get("evictionEnabled"));
        assertEquals(memoryThreshold, settings.get("memoryThreshold"));
        assertEquals(idleTimeMinutes, settings.get("idleTimeMinutes"));
        assertEquals(maxKeysPerScan, settings.get("maxKeysPerScan"));
        assertEquals(logIntervalMinutes, settings.get("logIntervalMinutes"));
    }
    
    /**
     * Helper method to mock the idle time for a key.
     * 
     * @param key the key to mock idle time for
     * @param idleTimeSeconds the idle time in seconds
     */
    private void mockIdleTime(String key, long idleTimeSeconds) {
        when(redisConnection.objectCommands().idletime(key.getBytes())).thenReturn(idleTimeSeconds);
    }
}