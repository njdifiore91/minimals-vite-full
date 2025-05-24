package com.dollarfunding.mca.cache;

/**
 * Constants for Redis caching in the MCA application.
 * 
 * This class centralizes all cache-related constants to ensure consistency across the application.
 * It defines TTL values, cache names, and key prefixes for different entity types and operations.
 * 
 * The MCA application uses Redis as a distributed caching layer with the following configuration:
 * - Key-based expiration policies (15 minutes for application data, 24 hours for sessions)
 * - Cluster mode enabled for horizontal scaling
 * - Memory optimization with appropriate eviction policies
 * - Persistent storage for critical data with AOF persistence
 * - Sentinel for automatic failover in case of node failures
 */
public final class CacheConstants {

    /**
     * Private constructor to prevent instantiation of this utility class.
     */
    private CacheConstants() {
        throw new AssertionError("CacheConstants utility class should not be instantiated");
    }

    /**
     * TTL (Time-To-Live) Constants
     */
    
    /**
     * TTL for application data in seconds (15 minutes).
     * Used for caching application-related data like application details, document metadata, etc.
     */
    public static final int APPLICATION_DATA_TTL_SECONDS = 15 * 60; // 15 minutes
    
    /**
     * TTL for session data in seconds (24 hours).
     * Used for caching user session information.
     */
    public static final int SESSION_DATA_TTL_SECONDS = 24 * 60 * 60; // 24 hours

    /**
     * Cache Name Constants
     * These constants define the names of different caches used in the application.
     */
    
    /**
     * Cache name for application entities.
     * Used to store and retrieve application data.
     */
    public static final String APPLICATIONS_CACHE = "applications";
    
    /**
     * Cache name for document entities.
     * Used to store and retrieve document metadata.
     */
    public static final String DOCUMENTS_CACHE = "documents";
    
    /**
     * Cache name for merchant entities.
     * Used to store and retrieve merchant details.
     */
    public static final String MERCHANTS_CACHE = "merchants";
    
    /**
     * Cache name for user session data.
     * Used to store and retrieve user session information.
     */
    public static final String SESSIONS_CACHE = "sessions";

    /**
     * Key Prefix Constants
     * These constants define the prefixes used for cache keys to ensure uniqueness and organization.
     */
    
    /**
     * Prefix for application entity cache keys.
     * Example usage: APPLICATION_KEY_PREFIX + applicationId
     */
    public static final String APPLICATION_KEY_PREFIX = "app:";
    
    /**
     * Prefix for document entity cache keys.
     * Example usage: DOCUMENT_KEY_PREFIX + documentId
     */
    public static final String DOCUMENT_KEY_PREFIX = "doc:";
    
    /**
     * Prefix for merchant entity cache keys.
     * Example usage: MERCHANT_KEY_PREFIX + merchantId
     */
    public static final String MERCHANT_KEY_PREFIX = "merchant:";
    
    /**
     * Prefix for user session cache keys.
     * Example usage: SESSION_KEY_PREFIX + userId
     */
    public static final String SESSION_KEY_PREFIX = "session:";
    
    /**
     * Prefix for list cache keys.
     * Example usage: LIST_KEY_PREFIX + entityType
     */
    public static final String LIST_KEY_PREFIX = "list:";

    /**
     * Cache Region Constants
     * These constants define the regions used for organizing caches.
     */
    
    /**
     * Region for entity data caches.
     * Used to group entity-related caches (applications, documents, merchants).
     */
    public static final String ENTITY_CACHE_REGION = "entity";
    
    /**
     * Region for session data caches.
     * Used to group session-related caches.
     */
    public static final String SESSION_CACHE_REGION = "session";
    
    /**
     * Region for query result caches.
     * Used to group query result caches.
     */
    public static final String QUERY_CACHE_REGION = "query";

    /**
     * Cache Operation Constants
     * These constants define operations that can be performed on caches.
     */
    
    /**
     * Maximum number of retry attempts for cache operations.
     */
    public static final int MAX_CACHE_RETRY_ATTEMPTS = 3;
    
    /**
     * Delay between cache retry attempts in milliseconds.
     */
    public static final int CACHE_RETRY_DELAY_MS = 100;
    
    /**
     * Default batch size for cache operations that process multiple items.
     */
    public static final int DEFAULT_CACHE_BATCH_SIZE = 100;
}