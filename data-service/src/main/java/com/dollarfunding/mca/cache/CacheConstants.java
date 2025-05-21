package com.dollarfunding.mca.cache;

/**
 * Constants for Redis caching in the MCA application.
 * <p>
 * This class centralizes all cache-related constants to ensure consistency across the application.
 * It includes TTL values, cache names, and key prefixes for different entity types and operations.
 * </p>
 * <p>
 * The TTL values are based on the technical specification requirements:
 * - 15 minutes (900 seconds) for application data
 * - 24 hours (86400 seconds) for session data
 * </p>
 */
public final class CacheConstants {

    /**
     * Private constructor to prevent instantiation of this utility class.
     */
    private CacheConstants() {
        throw new AssertionError("CacheConstants is a utility class and should not be instantiated");
    }

    /**
     * TTL (Time-To-Live) constants for different types of cached data.
     * These values determine how long data remains in the cache before expiration.
     */
    public static final class TTL {
        /**
         * TTL for application data: 15 minutes (900 seconds).
         * Used for caching application-related data such as application details, status, etc.
         */
        public static final long APPLICATION_DATA_SECONDS = 900L;

        /**
         * TTL for session data: 24 hours (86400 seconds).
         * Used for caching user session information.
         */
        public static final long SESSION_DATA_SECONDS = 86400L;

        /**
         * TTL for merchant data: 15 minutes (900 seconds).
         * Used for caching merchant-related information.
         */
        public static final long MERCHANT_DATA_SECONDS = APPLICATION_DATA_SECONDS;

        /**
         * TTL for document metadata: 15 minutes (900 seconds).
         * Used for caching document metadata without the actual document content.
         */
        public static final long DOCUMENT_METADATA_SECONDS = APPLICATION_DATA_SECONDS;

        /**
         * TTL for lookup data: 1 hour (3600 seconds).
         * Used for caching relatively static reference data.
         */
        public static final long LOOKUP_DATA_SECONDS = 3600L;

        /**
         * No expiration TTL value.
         * Used for data that should remain in cache until explicitly removed.
         */
        public static final long NO_EXPIRATION = -1L;
    }

    /**
     * Cache name constants for different entity types.
     * These values are used to identify different cache regions in Redis.
     */
    public static final class CacheName {
        /**
         * Cache name for applications data.
         */
        public static final String APPLICATIONS = "applications";

        /**
         * Cache name for documents data.
         */
        public static final String DOCUMENTS = "documents";

        /**
         * Cache name for merchants data.
         */
        public static final String MERCHANTS = "merchants";

        /**
         * Cache name for user sessions.
         */
        public static final String SESSIONS = "sessions";

        /**
         * Cache name for lookup/reference data.
         */
        public static final String LOOKUPS = "lookups";
    }

    /**
     * Key prefix constants for different cache operations.
     * These prefixes are used to create standardized cache keys across the application.
     */
    public static final class KeyPrefix {
        /**
         * Prefix for application-related cache keys.
         */
        public static final String APPLICATION = "app:";

        /**
         * Prefix for document-related cache keys.
         */
        public static final String DOCUMENT = "doc:";

        /**
         * Prefix for merchant-related cache keys.
         */
        public static final String MERCHANT = "merch:";

        /**
         * Prefix for session-related cache keys.
         */
        public static final String SESSION = "sess:";

        /**
         * Prefix for lookup/reference data cache keys.
         */
        public static final String LOOKUP = "lookup:";

        /**
         * Prefix for collection cache keys.
         */
        public static final String COLLECTION = "col:";

        /**
         * Prefix for count cache keys.
         */
        public static final String COUNT = "count:";

        /**
         * Prefix for metadata cache keys.
         */
        public static final String METADATA = "meta:";
    }

    /**
     * Constants for cache region names.
     * These values are used to configure different cache regions with specific settings.
     */
    public static final class Region {
        /**
         * Region for application data with 15-minute TTL.
         */
        public static final String APPLICATION_REGION = "applicationRegion";

        /**
         * Region for session data with 24-hour TTL.
         */
        public static final String SESSION_REGION = "sessionRegion";

        /**
         * Region for merchant data with 15-minute TTL.
         */
        public static final String MERCHANT_REGION = "merchantRegion";

        /**
         * Region for document metadata with 15-minute TTL.
         */
        public static final String DOCUMENT_REGION = "documentRegion";

        /**
         * Region for lookup data with 1-hour TTL.
         */
        public static final String LOOKUP_REGION = "lookupRegion";
    }

    /**
     * Constants for cache key delimiters and separators.
     * These values are used to create and parse structured cache keys.
     */
    public static final class Delimiter {
        /**
         * Main delimiter for separating parts of a cache key.
         */
        public static final String KEY_DELIMITER = ":";

        /**
         * Secondary delimiter for separating items in a list within a cache key.
         */
        public static final String LIST_DELIMITER = ",";

        /**
         * Delimiter for separating key-value pairs in a cache key.
         */
        public static final String PAIR_DELIMITER = "=";
    }
}