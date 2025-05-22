package com.dollarfunding.mca.cache;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.Status;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.RedisServerCommands;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.cache.RedisCache;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.cache.CacheStatistics;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link CacheHealthIndicator} class that implements Spring Boot's
 * HealthIndicator for Redis cache health monitoring.
 * 
 * Tests verify Redis connection health checks, cache statistics reporting, integration
 * with Spring Boot Actuator health endpoints, and detailed health status reporting with metrics.
 */
@ExtendWith(MockitoExtension.class)
public class CacheHealthIndicatorTest {

    @Mock
    private RedisConnectionFactory redisConnectionFactory;

    @Mock
    private RedisConnection redisConnection;

    @Mock
    private RedisServerCommands redisServerCommands;

    @Mock
    private RedisCacheManager redisCacheManager;

    @Mock
    private RedisCache redisCache;

    @Mock
    private CacheStatistics cacheStatistics;

    private CacheHealthIndicator cacheHealthIndicator;

    @BeforeEach
    public void setUp() {
        cacheHealthIndicator = new CacheHealthIndicator(redisConnectionFactory, redisCacheManager);
        when(redisConnectionFactory.getConnection()).thenReturn(redisConnection);
        when(redisConnection.serverCommands()).thenReturn(redisServerCommands);
    }

    /**
     * Test that health status is UP when Redis connection is successful
     * and server info is available.
     */
    @Test
    public void testHealthStatusUp() {
        // Arrange
        Properties serverInfo = new Properties();
        serverInfo.setProperty("redis_version", "7.0.0");
        serverInfo.setProperty("uptime_in_seconds", "3600");
        when(redisServerCommands.info()).thenReturn(serverInfo);
        
        // Mock cache statistics
        when(redisCacheManager.getCacheNames()).thenReturn(Collections.singleton("applicationData"));
        when(redisCacheManager.getCache("applicationData")).thenReturn(redisCache);
        when(redisCache.getStatistics()).thenReturn(cacheStatistics);
        when(cacheStatistics.getHits()).thenReturn(100L);
        when(cacheStatistics.getMisses()).thenReturn(20L);
        when(cacheStatistics.getPuts()).thenReturn(120L);

        // Act
        Health health = cacheHealthIndicator.health();

        // Assert
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsKey("redis_version");
        assertThat(health.getDetails()).containsKey("uptime_in_seconds");
        assertThat(health.getDetails()).containsKey("cache.applicationData.hits");
        assertThat(health.getDetails()).containsKey("cache.applicationData.misses");
        assertThat(health.getDetails()).containsKey("cache.applicationData.puts");
        assertThat(health.getDetails().get("cache.applicationData.hits")).isEqualTo(100L);
        assertThat(health.getDetails().get("cache.applicationData.misses")).isEqualTo(20L);
        assertThat(health.getDetails().get("cache.applicationData.puts")).isEqualTo(120L);
        
        // Verify interactions
        verify(redisConnectionFactory).getConnection();
        verify(redisConnection).serverCommands();
        verify(redisServerCommands).info();
        verify(redisConnection).close();
    }

    /**
     * Test that health status is DOWN when Redis connection fails.
     */
    @Test
    public void testHealthStatusDown() {
        // Arrange
        when(redisServerCommands.info()).thenThrow(new RuntimeException("Connection refused"));

        // Act
        Health health = cacheHealthIndicator.health();

        // Assert
        assertThat(health.getStatus()).isEqualTo(Status.DOWN);
        assertThat(health.getDetails()).containsKey("error");
        assertThat(health.getDetails().get("error").toString()).contains("Connection refused");
        
        // Verify interactions
        verify(redisConnectionFactory).getConnection();
        verify(redisConnection).serverCommands();
        verify(redisServerCommands).info();
        verify(redisConnection).close();
    }

    /**
     * Test that health status is UNKNOWN when Redis connection returns null info.
     */
    @Test
    public void testHealthStatusUnknown() {
        // Arrange
        when(redisServerCommands.info()).thenReturn(null);

        // Act
        Health health = cacheHealthIndicator.health();

        // Assert
        assertThat(health.getStatus()).isEqualTo(Status.UNKNOWN);
        assertThat(health.getDetails()).containsKey("error");
        assertThat(health.getDetails().get("error").toString()).contains("No server info available");
        
        // Verify interactions
        verify(redisConnectionFactory).getConnection();
        verify(redisConnection).serverCommands();
        verify(redisServerCommands).info();
        verify(redisConnection).close();
    }

    /**
     * Test that cache statistics are properly reported in health details.
     */
    @Test
    public void testCacheStatisticsReporting() {
        // Arrange
        Properties serverInfo = new Properties();
        serverInfo.setProperty("redis_version", "7.0.0");
        when(redisServerCommands.info()).thenReturn(serverInfo);
        
        // Mock multiple caches with statistics
        when(redisCacheManager.getCacheNames()).thenReturn(java.util.Set.of("userSessions", "applicationData"));
        
        // First cache
        RedisCache userSessionsCache = mock(RedisCache.class);
        CacheStatistics userSessionsStats = mock(CacheStatistics.class);
        when(redisCacheManager.getCache("userSessions")).thenReturn(userSessionsCache);
        when(userSessionsCache.getStatistics()).thenReturn(userSessionsStats);
        when(userSessionsStats.getHits()).thenReturn(500L);
        when(userSessionsStats.getMisses()).thenReturn(50L);
        when(userSessionsStats.getPuts()).thenReturn(550L);
        when(userSessionsStats.getDeletes()).thenReturn(50L);
        
        // Second cache
        when(redisCacheManager.getCache("applicationData")).thenReturn(redisCache);
        when(redisCache.getStatistics()).thenReturn(cacheStatistics);
        when(cacheStatistics.getHits()).thenReturn(1000L);
        when(cacheStatistics.getMisses()).thenReturn(200L);
        when(cacheStatistics.getPuts()).thenReturn(1200L);
        when(cacheStatistics.getDeletes()).thenReturn(100L);

        // Act
        Health health = cacheHealthIndicator.health();

        // Assert
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        
        // Check first cache statistics
        assertThat(health.getDetails()).containsKey("cache.userSessions.hits");
        assertThat(health.getDetails()).containsKey("cache.userSessions.misses");
        assertThat(health.getDetails()).containsKey("cache.userSessions.puts");
        assertThat(health.getDetails()).containsKey("cache.userSessions.deletes");
        assertThat(health.getDetails().get("cache.userSessions.hits")).isEqualTo(500L);
        assertThat(health.getDetails().get("cache.userSessions.misses")).isEqualTo(50L);
        assertThat(health.getDetails().get("cache.userSessions.puts")).isEqualTo(550L);
        assertThat(health.getDetails().get("cache.userSessions.deletes")).isEqualTo(50L);
        
        // Check second cache statistics
        assertThat(health.getDetails()).containsKey("cache.applicationData.hits");
        assertThat(health.getDetails()).containsKey("cache.applicationData.misses");
        assertThat(health.getDetails()).containsKey("cache.applicationData.puts");
        assertThat(health.getDetails()).containsKey("cache.applicationData.deletes");
        assertThat(health.getDetails().get("cache.applicationData.hits")).isEqualTo(1000L);
        assertThat(health.getDetails().get("cache.applicationData.misses")).isEqualTo(200L);
        assertThat(health.getDetails().get("cache.applicationData.puts")).isEqualTo(1200L);
        assertThat(health.getDetails().get("cache.applicationData.deletes")).isEqualTo(100L);
        
        // Calculate and check hit ratio
        double userSessionsHitRatio = 500.0 / (500.0 + 50.0);
        double applicationDataHitRatio = 1000.0 / (1000.0 + 200.0);
        assertThat(health.getDetails().get("cache.userSessions.hitRatio")).isEqualTo(userSessionsHitRatio);
        assertThat(health.getDetails().get("cache.applicationData.hitRatio")).isEqualTo(applicationDataHitRatio);
    }

    /**
     * Test that detailed Redis metrics are reported in health details.
     */
    @Test
    public void testDetailedMetricsReporting() {
        // Arrange
        Properties serverInfo = new Properties();
        serverInfo.setProperty("redis_version", "7.0.0");
        serverInfo.setProperty("uptime_in_seconds", "3600");
        serverInfo.setProperty("connected_clients", "42");
        serverInfo.setProperty("used_memory", "1048576");
        serverInfo.setProperty("used_memory_peak", "2097152");
        serverInfo.setProperty("mem_fragmentation_ratio", "1.5");
        serverInfo.setProperty("instantaneous_ops_per_sec", "1000");
        when(redisServerCommands.info()).thenReturn(serverInfo);
        
        // Mock cache statistics
        when(redisCacheManager.getCacheNames()).thenReturn(Collections.singleton("applicationData"));
        when(redisCacheManager.getCache("applicationData")).thenReturn(redisCache);
        when(redisCache.getStatistics()).thenReturn(cacheStatistics);

        // Act
        Health health = cacheHealthIndicator.health();

        // Assert
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsKey("redis_version");
        assertThat(health.getDetails()).containsKey("uptime_in_seconds");
        assertThat(health.getDetails()).containsKey("connected_clients");
        assertThat(health.getDetails()).containsKey("used_memory");
        assertThat(health.getDetails()).containsKey("used_memory_peak");
        assertThat(health.getDetails()).containsKey("mem_fragmentation_ratio");
        assertThat(health.getDetails()).containsKey("instantaneous_ops_per_sec");
        
        assertThat(health.getDetails().get("redis_version")).isEqualTo("7.0.0");
        assertThat(health.getDetails().get("connected_clients")).isEqualTo("42");
        assertThat(health.getDetails().get("used_memory")).isEqualTo("1048576");
    }

    /**
     * Test that health indicator detects automatic recovery after connection failure.
     */
    @Test
    public void testAutomaticRecoveryDetection() {
        // Arrange - first call fails
        when(redisServerCommands.info())
            .thenThrow(new RuntimeException("Connection refused"))
            .thenReturn(new Properties()); // second call succeeds

        // Act - first health check
        Health firstCheck = cacheHealthIndicator.health();
        
        // Assert - should be DOWN
        assertThat(firstCheck.getStatus()).isEqualTo(Status.DOWN);
        assertThat(firstCheck.getDetails()).containsKey("error");
        
        // Act - second health check (recovery)
        Health secondCheck = cacheHealthIndicator.health();
        
        // Assert - should be UP
        assertThat(secondCheck.getStatus()).isEqualTo(Status.UP);
        assertThat(secondCheck.getDetails()).doesNotContainKey("error");
        
        // Verify interactions
        verify(redisConnectionFactory, times(2)).getConnection();
        verify(redisConnection, times(2)).serverCommands();
        verify(redisServerCommands, times(2)).info();
        verify(redisConnection, times(2)).close();
    }

    /**
     * Test integration with Spring Boot Actuator health endpoint.
     */
    @Test
    public void testIntegrationWithActuatorHealthEndpoint() {
        // Arrange
        Properties serverInfo = new Properties();
        serverInfo.setProperty("redis_version", "7.0.0");
        when(redisServerCommands.info()).thenReturn(serverInfo);
        
        // Mock cache with statistics for hit ratio calculation
        when(redisCacheManager.getCacheNames()).thenReturn(Collections.singleton("applicationData"));
        when(redisCacheManager.getCache("applicationData")).thenReturn(redisCache);
        when(redisCache.getStatistics()).thenReturn(cacheStatistics);
        when(cacheStatistics.getHits()).thenReturn(800L);
        when(cacheStatistics.getMisses()).thenReturn(200L);

        // Act
        Health health = cacheHealthIndicator.health();

        // Assert
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        
        // Check cache hit ratio is calculated and included
        double expectedHitRatio = 800.0 / (800.0 + 200.0); // 0.8 or 80%
        assertThat(health.getDetails()).containsKey("cache.applicationData.hitRatio");
        assertThat(health.getDetails().get("cache.applicationData.hitRatio")).isEqualTo(expectedHitRatio);
        
        // Check overall cache metrics are included
        assertThat(health.getDetails()).containsKey("cache.applicationData.hits");
        assertThat(health.getDetails()).containsKey("cache.applicationData.misses");
        assertThat(health.getDetails().get("cache.applicationData.hits")).isEqualTo(800L);
        assertThat(health.getDetails().get("cache.applicationData.misses")).isEqualTo(200L);
    }
}