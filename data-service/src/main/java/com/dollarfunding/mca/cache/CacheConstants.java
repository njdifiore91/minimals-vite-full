package com.dollarfunding.mca.cache;

/**
 * Defines constants for Redis caching in the MCA application, including TTL values, cache names, and key prefixes.
 * This class centralizes all cache-related constants to ensure consistency across the application.
 * It specifies the TTL values for different types of data (15 minutes for application data, 24 hours for sessions)
 * and defines cache names for different entity types (applications, documents, merchants).
 */
public final class CacheConstants {

    private CacheConstants() {
        // Private constructor to prevent instantiation
    }

    /**
     * TTL for application data in minutes (15 minutes)
     */
    public static final int APPLICATION_DATA_TTL_MINUTES = 15;

    /**
     * TTL for session data in hours (24 hours)
     */
    public static final int SESSION_DATA_TTL_HOURS = 24;

    /**
     * Cache name for application entities
     */
    public static final String CACHE_NAME_APPLICATIONS = "applications";

    /**
     * Cache name for document entities
     */
    public static final String CACHE_NAME_DOCUMENTS = "documents";

    /**
     * Cache name for merchant entities
     */
    public static final String CACHE_NAME_MERCHANTS = "merchants";

    /**
     * Cache name for user session data
     */
    public static final String CACHE_NAME_SESSIONS = "sessions";

    /**
     * Prefix for application entity cache keys
     */
    public static final String KEY_PREFIX_APPLICATION = "app:";

    /**
     * Prefix for document entity cache keys
     */
    public static final String KEY_PREFIX_DOCUMENT = "doc:";

    /**
     * Prefix for merchant entity cache keys
     */
    public static final String KEY_PREFIX_MERCHANT = "merchant:";

    /**
     * Prefix for session cache keys
     */
    public static final String KEY_PREFIX_SESSION = "session:";

    /**
     * Prefix for collection cache keys
     */
    public static final String KEY_PREFIX_COLLECTION = "collection:";

    /**
     * Prefix for counter cache keys
     */
    public static final String KEY_PREFIX_COUNTER = "counter:";

    /**
     * Prefix for lock cache keys
     */
    public static final String KEY_PREFIX_LOCK = "lock:";

    /**
     * Delimiter for multi-part cache keys
     */
    public static final String KEY_DELIMITER = ":";

    /**
     * Pattern for application cache keys
     */
    public static final String PATTERN_APPLICATION_KEYS = KEY_PREFIX_APPLICATION + "*";

    /**
     * Pattern for document cache keys
     */
    public static final String PATTERN_DOCUMENT_KEYS = KEY_PREFIX_DOCUMENT + "*";

    /**
     * Pattern for merchant cache keys
     */
    public static final String PATTERN_MERCHANT_KEYS = KEY_PREFIX_MERCHANT + "*";

    /**
     * Pattern for session cache keys
     */
    public static final String PATTERN_SESSION_KEYS = KEY_PREFIX_SESSION + "*";
}