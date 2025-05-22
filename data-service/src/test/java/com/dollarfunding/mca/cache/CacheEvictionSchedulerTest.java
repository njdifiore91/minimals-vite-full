package com.dollarfunding.mca.cache;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisServerCommands;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link CacheEvictionScheduler} class.
 * 
 * These tests verify the scheduled cache maintenance tasks, including:
 * - Eviction of stale data based on configurable TTL criteria
 * - Pattern-based cache clearing for specific key patterns
 * - Logging of cache statistics for monitoring purposes
 * - Eviction policy configuration based on memory usage and access patterns
 */
@ExtendWith(MockitoExtension.class)
public class CacheEvictionSchedulerTest {

    @Mock
    private RedisTemplate<String, Object> redisTemplate;

    @Mock
    private RedisConnection redisConnection;

    @Mock
    private RedisServerCommands redisServerCommands;

    @InjectMocks
    private CacheEvictionScheduler cacheEvictionScheduler;

    @BeforeEach
    public void setUp() {
        // Set default property values using ReflectionTestUtils
        ReflectionTestUtils.setField(cacheEvictionScheduler, "applicationDataTtl", 900L);
        ReflectionTestUtils.setField(cacheEvictionScheduler, "sessionTtl", 86400L);
        ReflectionTestUtils.setField(cacheEvictionScheduler, "memoryThresholdPercent", 80);
        ReflectionTestUtils.setField(cacheEvictionScheduler, "evictionEnabled", true);
    }

    /**
     * Test that the evictStaleApplicationData method properly applies TTL to application cache entries
     * that don't have an expiration set.
     */
    @Test
    public void testEvictStaleApplicationData() {
        // Arrange
        Set<String> keys = new HashSet<>(Arrays.asList("application:1", "application:2", "application:3"));
        when(redisTemplate.keys("application:*")).thenReturn(keys);
        
        // Mock TTL responses: first key has no TTL, second has negative TTL, third has positive TTL
        when(redisTemplate.getExpire("application:1", TimeUnit.SECONDS)).thenReturn(null);
        when(redisTemplate.getExpire("application:2", TimeUnit.SECONDS)).thenReturn(-1L);
        when(redisTemplate.getExpire("application:3", TimeUnit.SECONDS)).thenReturn(600L);

        // Act
        cacheEvictionScheduler.evictStaleApplicationData();

        // Assert
        // Verify TTL was set for keys with null or negative TTL
        verify(redisTemplate).expire("application:1", 900L, TimeUnit.SECONDS);
        verify(redisTemplate).expire("application:2", 900L, TimeUnit.SECONDS);
        // Verify TTL was not set for key with positive TTL
        verify(redisTemplate, never()).expire("application:3", 900L, TimeUnit.SECONDS);
    }

    /**
     * Test that the evictStaleApplicationData method does nothing when eviction is disabled.
     */
    @Test
    public void testEvictStaleApplicationDataWhenDisabled() {
        // Arrange
        ReflectionTestUtils.setField(cacheEvictionScheduler, "evictionEnabled", false);

        // Act
        cacheEvictionScheduler.evictStaleApplicationData();

        // Assert
        verify(redisTemplate, never()).keys(anyString());
        verify(redisTemplate, never()).getExpire(anyString(), any(TimeUnit.class));
        verify(redisTemplate, never()).expire(anyString(), anyLong(), any(TimeUnit.class));
    }

    /**
     * Test that the evictStaleSessions method properly applies TTL to session cache entries
     * that don't have an expiration set.
     */
    @Test
    public void testEvictStaleSessions() {
        // Arrange
        Set<String> keys = new HashSet<>(Arrays.asList("session:1", "session:2", "session:3"));
        when(redisTemplate.keys("session:*")).thenReturn(keys);
        
        // Mock TTL responses: first key has no TTL, second has negative TTL, third has positive TTL
        when(redisTemplate.getExpire("session:1", TimeUnit.SECONDS)).thenReturn(null);
        when(redisTemplate.getExpire("session:2", TimeUnit.SECONDS)).thenReturn(-1L);
        when(redisTemplate.getExpire("session:3", TimeUnit.SECONDS)).thenReturn(3600L);

        // Act
        cacheEvictionScheduler.evictStaleSessions();

        // Assert
        // Verify TTL was set for keys with null or negative TTL
        verify(redisTemplate).expire("session:1", 86400L, TimeUnit.SECONDS);
        verify(redisTemplate).expire("session:2", 86400L, TimeUnit.SECONDS);
        // Verify TTL was not set for key with positive TTL
        verify(redisTemplate, never()).expire("session:3", 86400L, TimeUnit.SECONDS);
    }

    /**
     * Test that the evictStaleSessions method does nothing when eviction is disabled.
     */
    @Test
    public void testEvictStaleSessionsWhenDisabled() {
        // Arrange
        ReflectionTestUtils.setField(cacheEvictionScheduler, "evictionEnabled", false);

        // Act
        cacheEvictionScheduler.evictStaleSessions();

        // Assert
        verify(redisTemplate, never()).keys(anyString());
        verify(redisTemplate, never()).getExpire(anyString(), any(TimeUnit.class));
        verify(redisTemplate, never()).expire(anyString(), anyLong(), any(TimeUnit.class));
    }

    /**
     * Test that the monitorMemoryUsage method triggers eviction when memory usage exceeds the threshold.
     */
    @Test
    @SuppressWarnings("unchecked")
    public void testMonitorMemoryUsageTriggersEviction() {
        // Arrange
        // Mock Redis memory info with usage above threshold (85%)
        when(redisConnection.serverCommands()).thenReturn(redisServerCommands);
        when(redisServerCommands.info("memory")).thenReturn(
                "used_memory:850000000\n" +
                "total_system_memory:1000000000\n");
        
        // Capture the RedisCallback
        ArgumentCaptor<RedisCallback<Object>> callbackCaptor = ArgumentCaptor.forClass(RedisCallback.class);
        when(redisTemplate.execute(callbackCaptor.capture())).thenAnswer(invocation -> {
            RedisCallback<Object> callback = callbackCaptor.getValue();
            return callback.doInRedis(redisConnection);
        });

        // Mock pattern-based cache clearing
        Set<String> lowPriorityKeys = new HashSet<>(Arrays.asList("application:lowpriority:1", "application:lowpriority:2"));
        when(redisTemplate.keys("application:lowpriority:*")).thenReturn(lowPriorityKeys);
        
        Set<String> tempKeys = new HashSet<>(Arrays.asList("temp:1", "temp:2"));
        when(redisTemplate.keys("temp:*")).thenReturn(tempKeys);

        // Act
        cacheEvictionScheduler.monitorMemoryUsage();

        // Assert
        // Verify Redis memory info was retrieved
        verify(redisServerCommands).info("memory");
        
        // Verify low-priority cache was cleared
        verify(redisTemplate).keys("application:lowpriority:*");
        verify(redisTemplate).delete(lowPriorityKeys);
        
        // Verify temp cache was cleared
        verify(redisTemplate).keys("temp:*");
        verify(redisTemplate).delete(tempKeys);
    }

    /**
     * Test that the monitorMemoryUsage method does not trigger eviction when memory usage is below the threshold.
     */
    @Test
    @SuppressWarnings("unchecked")
    public void testMonitorMemoryUsageBelowThreshold() {
        // Arrange
        // Mock Redis memory info with usage below threshold (70%)
        when(redisConnection.serverCommands()).thenReturn(redisServerCommands);
        when(redisServerCommands.info("memory")).thenReturn(
                "used_memory:700000000\n" +
                "total_system_memory:1000000000\n");
        
        // Capture the RedisCallback
        ArgumentCaptor<RedisCallback<Object>> callbackCaptor = ArgumentCaptor.forClass(RedisCallback.class);
        when(redisTemplate.execute(callbackCaptor.capture())).thenAnswer(invocation -> {
            RedisCallback<Object> callback = callbackCaptor.getValue();
            return callback.doInRedis(redisConnection);
        });

        // Act
        cacheEvictionScheduler.monitorMemoryUsage();

        // Assert
        // Verify Redis memory info was retrieved
        verify(redisServerCommands).info("memory");
        
        // Verify no cache clearing was performed
        verify(redisTemplate, never()).keys("application:lowpriority:*");
        verify(redisTemplate, never()).delete(anySet());
    }

    /**
     * Test that the monitorMemoryUsage method does nothing when eviction is disabled.
     */
    @Test
    public void testMonitorMemoryUsageWhenDisabled() {
        // Arrange
        ReflectionTestUtils.setField(cacheEvictionScheduler, "evictionEnabled", false);

        // Act
        cacheEvictionScheduler.monitorMemoryUsage();

        // Assert
        verify(redisTemplate, never()).execute(any(RedisCallback.class));
    }

    /**
     * Test that the logCacheStatistics method properly collects and logs cache statistics.
     */
    @Test
    @SuppressWarnings("unchecked")
    public void testLogCacheStatistics() {
        // Arrange
        // Mock key counts by prefix
        when(redisTemplate.keys("application:*")).thenReturn(new HashSet<>(Arrays.asList("application:1", "application:2")));
        when(redisTemplate.keys("document:*")).thenReturn(new HashSet<>(Arrays.asList("document:1")));
        when(redisTemplate.keys("merchant:*")).thenReturn(new HashSet<>(Arrays.asList("merchant:1", "merchant:2", "merchant:3")));
        when(redisTemplate.keys("session:*")).thenReturn(new HashSet<>(Arrays.asList("session:1")));
        when(redisTemplate.keys("*")).thenReturn(new HashSet<>(Arrays.asList(
                "application:1", "application:2", "document:1", "merchant:1", "merchant:2", "merchant:3", "session:1", "other:1")));
        
        // Mock Redis stats
        when(redisConnection.serverCommands()).thenReturn(redisServerCommands);
        when(redisServerCommands.info("stats")).thenReturn(
                "keyspace_hits:150\n" +
                "keyspace_misses:50\n");
        
        // Capture the RedisCallback
        ArgumentCaptor<RedisCallback<Object>> callbackCaptor = ArgumentCaptor.forClass(RedisCallback.class);
        when(redisTemplate.execute(callbackCaptor.capture())).thenAnswer(invocation -> {
            RedisCallback<Object> callback = callbackCaptor.getValue();
            return callback.doInRedis(redisConnection);
        });

        // Act
        cacheEvictionScheduler.logCacheStatistics();

        // Assert
        // Verify key counts were retrieved
        verify(redisTemplate).keys("application:*");
        verify(redisTemplate).keys("document:*");
        verify(redisTemplate).keys("merchant:*");
        verify(redisTemplate).keys("session:*");
        verify(redisTemplate).keys("*");
        
        // Verify Redis stats were retrieved
        verify(redisServerCommands).info("stats");
    }

    /**
     * Test that the clearCacheByPattern method properly clears cache entries matching a pattern.
     */
    @Test
    public void testClearCacheByPattern() {
        // Arrange
        String pattern = "test:pattern:*";
        Set<String> keys = new HashSet<>(Arrays.asList("test:pattern:1", "test:pattern:2", "test:pattern:3"));
        when(redisTemplate.keys(pattern)).thenReturn(keys);

        // Act
        int result = cacheEvictionScheduler.clearCacheByPattern(pattern);

        // Assert
        assertEquals(3, result, "Should return the number of keys cleared");
        verify(redisTemplate).keys(pattern);
        verify(redisTemplate).delete(keys);
    }

    /**
     * Test that the clearCacheByPattern method returns 0 when no keys match the pattern.
     */
    @Test
    public void testClearCacheByPatternNoMatches() {
        // Arrange
        String pattern = "test:pattern:*";
        when(redisTemplate.keys(pattern)).thenReturn(new HashSet<>());

        // Act
        int result = cacheEvictionScheduler.clearCacheByPattern(pattern);

        // Assert
        assertEquals(0, result, "Should return 0 when no keys match");
        verify(redisTemplate).keys(pattern);
        verify(redisTemplate, never()).delete(anySet());
    }

    /**
     * Test that the clearCacheByPattern method returns -1 when an exception occurs.
     */
    @Test
    public void testClearCacheByPatternException() {
        // Arrange
        String pattern = "test:pattern:*";
        when(redisTemplate.keys(pattern)).thenThrow(new RuntimeException("Test exception"));

        // Act
        int result = cacheEvictionScheduler.clearCacheByPattern(pattern);

        // Assert
        assertEquals(-1, result, "Should return -1 when an exception occurs");
        verify(redisTemplate).keys(pattern);
        verify(redisTemplate, never()).delete(anySet());
    }

    /**
     * Test that the monitorMemoryUsage method takes more aggressive action when memory usage
     * remains high after initial eviction.
     */
    @Test
    @SuppressWarnings("unchecked")
    public void testMonitorMemoryUsageWithAggressiveEviction() {
        // Arrange
        // Mock Redis memory info with usage above threshold (85%)
        when(redisConnection.serverCommands()).thenReturn(redisServerCommands);
        
        // First call returns high memory usage
        when(redisServerCommands.info("memory"))
            .thenReturn("used_memory:850000000\ntotal_system_memory:1000000000\n")
            .thenReturn("used_memory:820000000\ntotal_system_memory:1000000000\n"); // Still above threshold after initial eviction
        
        // Capture the RedisCallback
        ArgumentCaptor<RedisCallback<Object>> callbackCaptor = ArgumentCaptor.forClass(RedisCallback.class);
        when(redisTemplate.execute(callbackCaptor.capture())).thenAnswer(invocation -> {
            RedisCallback<Object> callback = callbackCaptor.getValue();
            return callback.doInRedis(redisConnection);
        });

        // Mock pattern-based cache clearing
        Set<String> lowPriorityKeys = new HashSet<>(Arrays.asList("application:lowpriority:1", "application:lowpriority:2"));
        when(redisTemplate.keys("application:lowpriority:*")).thenReturn(lowPriorityKeys);
        
        Set<String> tempKeys = new HashSet<>(Arrays.asList("temp:1", "temp:2"));
        when(redisTemplate.keys("temp:*")).thenReturn(tempKeys);
        
        Set<String> nonCriticalKeys = new HashSet<>(Arrays.asList("application:1:details", "application:2:details"));
        when(redisTemplate.keys("application:*:details")).thenReturn(nonCriticalKeys);

        // Mock dbSize for expired keys eviction
        when(redisServerCommands.dbSize()).thenReturn(10L);

        // Act
        cacheEvictionScheduler.monitorMemoryUsage();

        // Assert
        // Verify Redis memory info was retrieved twice (before and after initial eviction)
        verify(redisServerCommands, times(2)).info("memory");
        
        // Verify initial cache clearing was performed
        verify(redisTemplate).keys("application:lowpriority:*");
        verify(redisTemplate).delete(lowPriorityKeys);
        verify(redisTemplate).keys("temp:*");
        verify(redisTemplate).delete(tempKeys);
        
        // Verify aggressive cache clearing was performed
        verify(redisTemplate).keys("application:*:details");
        verify(redisTemplate).delete(nonCriticalKeys);
    }

    /**
     * Test that the scheduled tasks are properly configured with the expected cron expressions or fixed rates.
     * This test verifies the presence of the @Scheduled annotation with the correct parameters.
     */
    @Test
    public void testScheduledAnnotations() throws NoSuchMethodException {
        // Verify evictStaleApplicationData is scheduled with cron = "0 0 * * * *"
        org.springframework.scheduling.annotation.Scheduled evictStaleDataAnnotation = 
                CacheEvictionScheduler.class.getMethod("evictStaleApplicationData").getAnnotation(org.springframework.scheduling.annotation.Scheduled.class);
        assertNotNull(evictStaleDataAnnotation, "evictStaleApplicationData should have @Scheduled annotation");
        assertEquals("0 0 * * * *", evictStaleDataAnnotation.cron(), "evictStaleApplicationData should run at the top of every hour");
        
        // Verify evictStaleSessions is scheduled with cron = "0 0 0 * * *"
        org.springframework.scheduling.annotation.Scheduled evictSessionsAnnotation = 
                CacheEvictionScheduler.class.getMethod("evictStaleSessions").getAnnotation(org.springframework.scheduling.annotation.Scheduled.class);
        assertNotNull(evictSessionsAnnotation, "evictStaleSessions should have @Scheduled annotation");
        assertEquals("0 0 0 * * *", evictSessionsAnnotation.cron(), "evictStaleSessions should run at midnight every day");
        
        // Verify monitorMemoryUsage is scheduled with fixedRate = 900000 (15 minutes)
        org.springframework.scheduling.annotation.Scheduled monitorMemoryAnnotation = 
                CacheEvictionScheduler.class.getMethod("monitorMemoryUsage").getAnnotation(org.springframework.scheduling.annotation.Scheduled.class);
        assertNotNull(monitorMemoryAnnotation, "monitorMemoryUsage should have @Scheduled annotation");
        assertEquals(900000, monitorMemoryAnnotation.fixedRate(), "monitorMemoryUsage should run every 15 minutes");
        
        // Verify logCacheStatistics is scheduled with fixedRate = 1800000 (30 minutes)
        org.springframework.scheduling.annotation.Scheduled logStatsAnnotation = 
                CacheEvictionScheduler.class.getMethod("logCacheStatistics").getAnnotation(org.springframework.scheduling.annotation.Scheduled.class);
        assertNotNull(logStatsAnnotation, "logCacheStatistics should have @Scheduled annotation");
        assertEquals(1800000, logStatsAnnotation.fixedRate(), "logCacheStatistics should run every 30 minutes");
    }
}