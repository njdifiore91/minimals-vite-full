package com.dollarfunding.mca.config;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisClusterConfiguration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.connection.lettuce.LettucePoolingClientConfiguration;
import org.apache.commons.pool2.impl.GenericObjectPoolConfig;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import com.dollarfunding.mca.cache.CacheConstants;

/**
 * Redis configuration for the MCA application with cluster mode support.
 * This class configures Redis connection factory, cache manager, and serialization settings.
 * It enables the application to cache frequently accessed data, reducing database load and improving response times.
 * The configuration includes TTL settings for different types of data:
 * - Application data: 15 minutes TTL
 * - User sessions: 24 hours TTL
 *
 * Redis 7.0 provides a distributed caching layer with the following features:
 * - Cluster mode enabled for horizontal scaling
 * - Key-based expiration policies
 * - Memory optimization with appropriate eviction policies
 * - Support for the Cache-Aside Pattern implementation
 */
@Configuration
@EnableCaching
public class RedisConfig {

    @Value("${spring.data.redis.cluster.nodes}")
    private String clusterNodes;
    
    @Value("${spring.data.redis.timeout:5000}")
    private int timeout;
    
    @Value("${spring.data.redis.cluster.max-redirects:3}")
    private int maxRedirects;
    
    @Value("${spring.data.redis.lettuce.pool.max-active:8}")
    private int maxActive;
    
    @Value("${spring.data.redis.lettuce.pool.max-idle:8}")
    private int maxIdle;
    
    @Value("${spring.data.redis.lettuce.pool.min-idle:0}")
    private int minIdle;
    
    @Value("${spring.data.redis.lettuce.pool.max-wait:-1}")
    private long maxWait;

    /**
     * Creates a Redis connection factory with cluster mode enabled.
     * This factory is used to create connections to the Redis cluster.
     * 
     * Redis 7.0 cluster mode provides horizontal scaling capabilities,
     * allowing the application to distribute cache data across multiple nodes.
     * 
     * @return RedisConnectionFactory configured for cluster mode
     */
    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        String[] nodes = clusterNodes.split(",");
        
        // Configure Redis cluster nodes
        RedisClusterConfiguration clusterConfiguration = new RedisClusterConfiguration();
        for (String node : nodes) {
            String[] hostAndPort = node.trim().split(":");
            clusterConfiguration.clusterNode(hostAndPort[0], Integer.parseInt(hostAndPort[1]));
        }
        
        // Set maximum number of redirects to follow during cluster operations
        clusterConfiguration.setMaxRedirects(maxRedirects);
        // Configure connection pooling
        GenericObjectPoolConfig<?> poolConfig = new GenericObjectPoolConfig<>();
        poolConfig.setMaxTotal(maxActive);
        poolConfig.setMaxIdle(maxIdle);
        poolConfig.setMinIdle(minIdle);
        poolConfig.setMaxWait(Duration.ofMillis(maxWait));
        
        // Configure Lettuce client with connection pooling
        LettuceClientConfiguration clientConfig = LettucePoolingClientConfiguration.builder()
                .commandTimeout(Duration.ofMillis(timeout))
                .poolConfig(poolConfig)
                .build();
        
        return new LettuceConnectionFactory(clusterConfiguration, clientConfig);
    }

    /**
     * Creates a RedisTemplate with appropriate serializers.
     * This template is used for Redis operations throughout the application.
     * 
     * The template is configured with JSON serialization for values and String serialization for keys,
     * providing efficient and readable data storage in Redis.
     * 
     * @param connectionFactory the Redis connection factory
     * @return configured RedisTemplate
     */
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory connectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);
        
        // Use StringRedisSerializer for keys
        template.setKeySerializer(new StringRedisSerializer());
        
        // Use GenericJackson2JsonRedisSerializer for values
        GenericJackson2JsonRedisSerializer jsonSerializer = new GenericJackson2JsonRedisSerializer();
        template.setValueSerializer(jsonSerializer);
        
        // Use the same serializers for hash operations
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(jsonSerializer);
        
        template.afterPropertiesSet();
        
        return template;
    }

    /**
     * Creates a RedisCacheManager with appropriate TTL settings for different cache types.
     * This manager is used for Spring's @Cacheable, @CachePut, and @CacheEvict annotations.
     * 
     * The cache manager implements the Cache-Aside Pattern, checking the cache before database queries
     * and updating the cache with query results. It applies different TTL settings based on data type:
     * - Application data: 15 minutes TTL
     * - User sessions: 24 hours TTL
     * 
     * @param connectionFactory the Redis connection factory
     * @return configured RedisCacheManager
     */
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        // Default serializer configuration
        RedisSerializationContext.SerializationPair<String> keySerializer = 
                RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer());
        
        RedisSerializationContext.SerializationPair<Object> valueSerializer = 
                RedisSerializationContext.SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer());
        
        // Default cache configuration with 15 minutes TTL for application data
        RedisCacheConfiguration defaultCacheConfig = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(15)) // Default TTL: 15 minutes
                .serializeKeysWith(keySerializer)
                .serializeValuesWith(valueSerializer);
        
        // Cache configurations with specific TTL settings
        Map<String, RedisCacheConfiguration> cacheConfigurations = new HashMap<>();
        
        // Session cache with 24 hours TTL
        cacheConfigurations.put(CacheConstants.CacheName.SESSIONS, 
                defaultCacheConfig.entryTtl(Duration.ofHours(24)));
        
        // Application cache with 15 minutes TTL (same as default, but explicitly defined)
        cacheConfigurations.put(CacheConstants.CacheName.APPLICATIONS, 
                defaultCacheConfig.entryTtl(Duration.ofMinutes(15)));
        
        // Document cache with 15 minutes TTL
        cacheConfigurations.put(CacheConstants.CacheName.DOCUMENTS, 
                defaultCacheConfig.entryTtl(Duration.ofMinutes(15)));
        
        // Merchant cache with 15 minutes TTL
        cacheConfigurations.put(CacheConstants.CacheName.MERCHANTS, 
                defaultCacheConfig.entryTtl(Duration.ofMinutes(15)));
        
        // Lookup cache with 1 hour TTL
        cacheConfigurations.put(CacheConstants.CacheName.LOOKUPS, 
                defaultCacheConfig.entryTtl(Duration.ofHours(1)));
        
        // Build the cache manager with the configured settings
        return RedisCacheManager.builder(connectionFactory)
                .cacheDefaults(defaultCacheConfig)
                .withInitialCacheConfigurations(cacheConfigurations)
                .transactionAware() // Enable transaction awareness for consistent cache operations
                .build();
    }
}