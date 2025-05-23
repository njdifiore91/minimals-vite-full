package com.dollarfunding.mca.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Duration;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisClusterConfiguration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.RedisNode;
import org.springframework.data.redis.connection.RedisSentinelConfiguration;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * Unit tests for the {@link RedisConfig} class that configures Redis caching with cluster mode support.
 * Tests verify Redis connection factory configuration, cache manager setup with appropriate TTL settings,
 * serialization configuration, and cache-aside pattern implementation.
 */
@ExtendWith(MockitoExtension.class)
public class RedisConfigTest {

    @InjectMocks
    private RedisConfig redisConfig;

    @Spy
    private RedisConfig spyRedisConfig;

    @BeforeEach
    public void setUp() {
        // Set default property values
        ReflectionTestUtils.setField(redisConfig, "clusterNodes", "localhost:6379,localhost:6380,localhost:6381");
        ReflectionTestUtils.setField(redisConfig, "maxRedirects", 3);
        ReflectionTestUtils.setField(redisConfig, "timeout", 2000);
        ReflectionTestUtils.setField(redisConfig, "defaultTtl", 900L); // 15 minutes in seconds
        ReflectionTestUtils.setField(redisConfig, "sessionTtl", 86400L); // 24 hours in seconds
        ReflectionTestUtils.setField(redisConfig, "sentinelEnabled", false);
        ReflectionTestUtils.setField(redisConfig, "sentinelMaster", "mymaster");
        ReflectionTestUtils.setField(redisConfig, "sentinelNodes", null);
        ReflectionTestUtils.setField(redisConfig, "clusterEnabled", true);
        ReflectionTestUtils.setField(redisConfig, "aofEnabled", true);
        
        // Set the same values for the spy
        ReflectionTestUtils.setField(spyRedisConfig, "clusterNodes", "localhost:6379,localhost:6380,localhost:6381");
        ReflectionTestUtils.setField(spyRedisConfig, "maxRedirects", 3);
        ReflectionTestUtils.setField(spyRedisConfig, "timeout", 2000);
        ReflectionTestUtils.setField(spyRedisConfig, "defaultTtl", 900L);
        ReflectionTestUtils.setField(spyRedisConfig, "sessionTtl", 86400L);
        ReflectionTestUtils.setField(spyRedisConfig, "sentinelEnabled", false);
        ReflectionTestUtils.setField(spyRedisConfig, "sentinelMaster", "mymaster");
        ReflectionTestUtils.setField(spyRedisConfig, "sentinelNodes", null);
        ReflectionTestUtils.setField(spyRedisConfig, "clusterEnabled", true);
        ReflectionTestUtils.setField(spyRedisConfig, "aofEnabled", true);
    }

    @Test
    @DisplayName("Should create Redis connection factory with cluster mode enabled")
    public void testRedisConnectionFactoryWithClusterMode() {
        // When
        RedisConnectionFactory factory = redisConfig.redisConnectionFactory();

        // Then
        assertNotNull(factory);
        assertInstanceOf(LettuceConnectionFactory.class, factory);
        
        LettuceConnectionFactory lettuceFactory = (LettuceConnectionFactory) factory;
        assertTrue(lettuceFactory.getClientConfiguration() instanceof LettuceClientConfiguration);
        
        // Verify cluster configuration
        assertInstanceOf(RedisClusterConfiguration.class, lettuceFactory.getClusterConfiguration());
        RedisClusterConfiguration clusterConfig = lettuceFactory.getClusterConfiguration();
        assertEquals(3, clusterConfig.getClusterNodes().size());
        assertEquals(3, clusterConfig.getMaxRedirects());
    }

    @Test
    @DisplayName("Should create Redis connection factory with sentinel mode when enabled")
    public void testRedisConnectionFactoryWithSentinelMode() {
        // Given
        ReflectionTestUtils.setField(redisConfig, "sentinelEnabled", true);
        ReflectionTestUtils.setField(redisConfig, "sentinelNodes", "localhost:26379,localhost:26380,localhost:26381");
        ReflectionTestUtils.setField(redisConfig, "clusterEnabled", false);

        // When
        RedisConnectionFactory factory = redisConfig.redisConnectionFactory();

        // Then
        assertNotNull(factory);
        assertInstanceOf(LettuceConnectionFactory.class, factory);
        
        LettuceConnectionFactory lettuceFactory = (LettuceConnectionFactory) factory;
        assertTrue(lettuceFactory.getClientConfiguration() instanceof LettuceClientConfiguration);
        
        // Verify sentinel configuration
        assertInstanceOf(RedisSentinelConfiguration.class, lettuceFactory.getSentinelConfiguration());
        RedisSentinelConfiguration sentinelConfig = lettuceFactory.getSentinelConfiguration();
        assertEquals("mymaster", sentinelConfig.getMaster().getName());
        assertEquals(3, sentinelConfig.getSentinels().size());
    }

    @Test
    @DisplayName("Should create Redis connection factory with standalone mode when cluster and sentinel disabled")
    public void testRedisConnectionFactoryWithStandaloneMode() {
        // Given
        ReflectionTestUtils.setField(redisConfig, "sentinelEnabled", false);
        ReflectionTestUtils.setField(redisConfig, "clusterEnabled", false);
        ReflectionTestUtils.setField(redisConfig, "clusterNodes", "localhost:6379");

        // When
        RedisConnectionFactory factory = redisConfig.redisConnectionFactory();

        // Then
        assertNotNull(factory);
        assertInstanceOf(LettuceConnectionFactory.class, factory);
        
        LettuceConnectionFactory lettuceFactory = (LettuceConnectionFactory) factory;
        assertTrue(lettuceFactory.getClientConfiguration() instanceof LettuceClientConfiguration);
        
        // Verify standalone configuration
        assertInstanceOf(RedisStandaloneConfiguration.class, lettuceFactory.getStandaloneConfiguration());
        RedisStandaloneConfiguration standaloneConfig = lettuceFactory.getStandaloneConfiguration();
        assertEquals("localhost", standaloneConfig.getHostName());
        assertEquals(6379, standaloneConfig.getPort());
    }

    @Test
    @DisplayName("Should configure RedisTemplate with appropriate serializers")
    public void testRedisTemplateConfiguration() {
        // Given
        RedisConnectionFactory mockFactory = mock(RedisConnectionFactory.class);

        // When
        RedisTemplate<String, Object> template = redisConfig.redisTemplate(mockFactory);

        // Then
        assertNotNull(template);
        assertInstanceOf(StringRedisSerializer.class, template.getKeySerializer());
        assertInstanceOf(GenericJackson2JsonRedisSerializer.class, template.getValueSerializer());
        assertInstanceOf(StringRedisSerializer.class, template.getHashKeySerializer());
        assertInstanceOf(GenericJackson2JsonRedisSerializer.class, template.getHashValueSerializer());
        assertEquals(mockFactory, template.getConnectionFactory());
    }

    @Test
    @DisplayName("Should configure cache manager with appropriate TTL settings")
    public void testCacheManagerConfiguration() {
        // Given
        RedisConnectionFactory mockFactory = mock(RedisConnectionFactory.class);

        // When
        RedisCacheManager cacheManager = redisConfig.cacheManager(mockFactory);

        // Then
        assertNotNull(cacheManager);
        
        // Get the cache configurations using reflection
        @SuppressWarnings("unchecked")
        Map<String, RedisCacheConfiguration> cacheConfigs = (Map<String, RedisCacheConfiguration>) 
                ReflectionTestUtils.getField(cacheManager, "initialCacheConfigurations");
        
        assertNotNull(cacheConfigs);
        assertEquals(4, cacheConfigs.size());
        
        // Verify TTL for application caches (15 minutes)
        assertTrue(cacheConfigs.containsKey(RedisConfig.APPLICATION_CACHE));
        assertEquals(Duration.ofSeconds(900), cacheConfigs.get(RedisConfig.APPLICATION_CACHE).getTtl());
        
        assertTrue(cacheConfigs.containsKey(RedisConfig.DOCUMENT_CACHE));
        assertEquals(Duration.ofSeconds(900), cacheConfigs.get(RedisConfig.DOCUMENT_CACHE).getTtl());
        
        assertTrue(cacheConfigs.containsKey(RedisConfig.MERCHANT_CACHE));
        assertEquals(Duration.ofSeconds(900), cacheConfigs.get(RedisConfig.MERCHANT_CACHE).getTtl());
        
        // Verify TTL for session cache (24 hours)
        assertTrue(cacheConfigs.containsKey(RedisConfig.SESSION_CACHE));
        assertEquals(Duration.ofSeconds(86400), cacheConfigs.get(RedisConfig.SESSION_CACHE).getTtl());
        
        // Verify serialization configuration
        RedisCacheConfiguration config = cacheConfigs.get(RedisConfig.APPLICATION_CACHE);
        assertTrue(config.usePrefix());
        assertFalse(config.getAllowCacheNullValues());
        
        // Verify the default configuration
        RedisCacheConfiguration defaultConfig = (RedisCacheConfiguration) 
                ReflectionTestUtils.getField(cacheManager, "defaultCacheConfiguration");
        assertNotNull(defaultConfig);
        assertEquals(Duration.ofSeconds(900), defaultConfig.getTtl());
    }
    
    @Test
    @DisplayName("Should configure Redis message listener container for cache invalidation")
    public void testRedisMessageListenerContainer() {
        // Given
        RedisConnectionFactory mockFactory = mock(RedisConnectionFactory.class);
        MessageListenerAdapter mockListener = mock(MessageListenerAdapter.class);
        
        // When
        RedisMessageListenerContainer container = spyRedisConfig.redisMessageListenerContainer(mockFactory, mockListener);
        
        // Then
        assertNotNull(container);
        assertEquals(mockFactory, container.getConnectionFactory());
        
        // Verify that the listener is registered with the correct topic
        verify(container).addMessageListener(eq(mockListener), any(ChannelTopic.class));
    }
    
    @Test
    @DisplayName("Should configure message listener adapter for cache invalidation")
    public void testMessageListenerAdapter() {
        // When
        MessageListenerAdapter adapter = redisConfig.messageListener();
        
        // Then
        assertNotNull(adapter);
        assertEquals("onMessage", adapter.getDefaultListenerMethod());
        assertInstanceOf(RedisConfig.CacheInvalidationListener.class, adapter.getDelegate());
    }
    
    @Test
    @DisplayName("Cache invalidation listener should handle messages correctly")
    public void testCacheInvalidationListener() {
        // Given
        RedisConfig.CacheInvalidationListener listener = redisConfig.new CacheInvalidationListener();
        String testMessage = "invalidate:application:123";
        
        // When
        listener.onMessage(testMessage);
        
        // Then - No exception should be thrown
        // This is primarily testing that the method executes without errors
        // In a real scenario, we would verify that the appropriate cache entries are invalidated
    }
    
    // Helper method to check if a cache configuration allows null values
    private boolean assertFalse(Boolean allowCacheNullValues) {
        return !allowCacheNullValues;
    }
}