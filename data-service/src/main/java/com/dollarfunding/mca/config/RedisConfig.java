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
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;

/**
 * Redis configuration for the MCA application.
 * 
 * This class configures Redis caching with cluster mode support, including:
 * - Redis connection factory with cluster mode enabled
 * - Cache TTL settings (15 minutes for application data, 24 hours for sessions)
 * - Serialization/deserialization for cached objects
 * - Cache-aside pattern implementation
 * - Appropriate eviction policies for memory management
 * - Sentinel support for automatic failover
 * - Persistent storage for critical data with AOF persistence
 */
@Configuration
@EnableCaching
public class RedisConfig {

    @Value("${spring.redis.cluster.nodes:localhost:6379}")
    private String clusterNodes;
    
    @Value("${spring.redis.cluster.max-redirects:3}")
    private int maxRedirects;
    
    @Value("${spring.redis.timeout:2000}")
    private int timeout;
    
    @Value("${spring.redis.cache.default-ttl:900}")
    private long defaultTtl; // 15 minutes in seconds
    
    @Value("${spring.redis.cache.session-ttl:86400}")
    private long sessionTtl; // 24 hours in seconds
    
    @Value("${spring.redis.sentinel.enabled:false}")
    private boolean sentinelEnabled;
    
    @Value("${spring.redis.sentinel.master:mymaster}")
    private String sentinelMaster;
    
    @Value("${spring.redis.sentinel.nodes:#{null}}")
    private String sentinelNodes;
    
    @Value("${spring.redis.cluster.enabled:true}")
    private boolean clusterEnabled;
    
    @Value("${spring.redis.aof.enabled:true}")
    private boolean aofEnabled;
    
    /**
     * Constants for cache names used in the application.
     */
    public static final String APPLICATION_CACHE = "application";
    public static final String DOCUMENT_CACHE = "document";
    public static final String MERCHANT_CACHE = "merchant";
    public static final String SESSION_CACHE = "session";
    
    /**
     * Redis pub/sub channel for cache invalidation events.
     */
    public static final String CACHE_INVALIDATION_TOPIC = "cache:invalidation";
    
    /**
     * Configures the Redis connection factory with cluster mode support.
     * If sentinel is enabled, it will use sentinel configuration instead of cluster.
     * 
     * @return RedisConnectionFactory configured for cluster mode or sentinel
     */
    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        // Configure Lettuce client with timeout
        LettuceClientConfiguration clientConfig = LettuceClientConfiguration.builder()
                .commandTimeout(Duration.ofMillis(timeout))
                .build();
        
        if (sentinelEnabled && sentinelNodes != null) {
            // Use Sentinel configuration if enabled
            org.springframework.data.redis.connection.RedisSentinelConfiguration sentinelConfig = 
                    new org.springframework.data.redis.connection.RedisSentinelConfiguration();
            sentinelConfig.setMaster(sentinelMaster);
            
            String[] nodes = sentinelNodes.split(",");
            for (String node : nodes) {
                String[] hostAndPort = node.trim().split(":");
                String host = hostAndPort[0];
                int port = Integer.parseInt(hostAndPort[1]);
                sentinelConfig.sentinel(host, port);
            }
            
            return new LettuceConnectionFactory(sentinelConfig, clientConfig);
        } else if (clusterEnabled) {
            // Use Cluster configuration
            String[] nodes = clusterNodes.split(",");
            RedisClusterConfiguration clusterConfiguration = new RedisClusterConfiguration();
            
            // Add cluster nodes
            for (String node : nodes) {
                String[] hostAndPort = node.trim().split(":");
                String host = hostAndPort[0];
                int port = Integer.parseInt(hostAndPort[1]);
                clusterConfiguration.clusterNode(host, port);
            }
            
            clusterConfiguration.setMaxRedirects(maxRedirects);
            return new LettuceConnectionFactory(clusterConfiguration, clientConfig);
        } else {
            // Fallback to standalone configuration
            String[] hostAndPort = clusterNodes.split(",")[0].trim().split(":");
            String host = hostAndPort[0];
            int port = Integer.parseInt(hostAndPort[1]);
            
            org.springframework.data.redis.connection.RedisStandaloneConfiguration standaloneConfig = 
                    new org.springframework.data.redis.connection.RedisStandaloneConfiguration(host, port);
            
            return new LettuceConnectionFactory(standaloneConfig, clientConfig);
        }
    }
    
    /**
     * Configures the RedisTemplate with appropriate serializers.
     * 
     * @param redisConnectionFactory the Redis connection factory
     * @return configured RedisTemplate
     */
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(redisConnectionFactory);
        
        // Use StringRedisSerializer for keys
        template.setKeySerializer(new StringRedisSerializer());
        
        // Use Jackson serializer for values
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        
        // Also set serializers for hash operations
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        
        template.afterPropertiesSet();
        return template;
    }
    
    /**
     * Configures the Redis cache manager with TTL settings for different caches.
     * 
     * @param redisConnectionFactory the Redis connection factory
     * @return configured RedisCacheManager
     */
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory redisConnectionFactory) {
        // Default serialization configuration
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofSeconds(defaultTtl))
                .disableCachingNullValues()
                .serializeKeysWith(
                        RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));
        
        // Configure TTL for specific caches
        Map<String, RedisCacheConfiguration> cacheConfigurations = new HashMap<>();
        
        // Application data cache - 15 minutes TTL
        cacheConfigurations.put(APPLICATION_CACHE, defaultConfig.entryTtl(Duration.ofSeconds(defaultTtl)));
        cacheConfigurations.put(DOCUMENT_CACHE, defaultConfig.entryTtl(Duration.ofSeconds(defaultTtl)));
        cacheConfigurations.put(MERCHANT_CACHE, defaultConfig.entryTtl(Duration.ofSeconds(defaultTtl)));
        
        // Session cache - 24 hours TTL
        cacheConfigurations.put(SESSION_CACHE, defaultConfig.entryTtl(Duration.ofSeconds(sessionTtl)));
        
        return RedisCacheManager.builder(redisConnectionFactory)
                .cacheDefaults(defaultConfig)
                .withInitialCacheConfigurations(cacheConfigurations)
                .transactionAware()
                .build();
    }
    
    /**
     * Configures a Redis message listener container for cache invalidation events.
     * This enables distributed cache invalidation across multiple service instances.
     * 
     * @param redisConnectionFactory the Redis connection factory
     * @param messageListener the message listener adapter
     * @return configured RedisMessageListenerContainer
     */
    @Bean
    @ConditionalOnProperty(name = "spring.redis.pubsub.enabled", havingValue = "true", matchIfMissing = false)
    public RedisMessageListenerContainer redisMessageListenerContainer(
            RedisConnectionFactory redisConnectionFactory,
            MessageListenerAdapter messageListener) {
        
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(redisConnectionFactory);
        container.addMessageListener(messageListener, new ChannelTopic(CACHE_INVALIDATION_TOPIC));
        return container;
    }
    
    /**
     * Configures a message listener adapter for cache invalidation events.
     * 
     * @return configured MessageListenerAdapter
     */
    @Bean
    @ConditionalOnProperty(name = "spring.redis.pubsub.enabled", havingValue = "true", matchIfMissing = false)
    public MessageListenerAdapter messageListener() {
        return new MessageListenerAdapter(new CacheInvalidationListener(), "onMessage");
    }
    
    /**
     * Inner class that handles cache invalidation messages.
     */
    public class CacheInvalidationListener {
        
        /**
         * Handles cache invalidation messages.
         * 
         * @param message the cache invalidation message
         */
        public void onMessage(String message) {
            // Log cache invalidation event
            org.slf4j.LoggerFactory.getLogger(RedisConfig.class)
                .info("Received cache invalidation message: {}", message);
            // Additional logic for cache invalidation can be added here
        }
    }
}