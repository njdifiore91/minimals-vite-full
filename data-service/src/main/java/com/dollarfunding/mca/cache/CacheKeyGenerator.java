package com.dollarfunding.mca.cache;

import org.springframework.stereotype.Component;

/**
 * Utility class for generating consistent cache keys in the MCA application.
 * This class provides methods for creating standardized cache keys based on entity type and ID,
 * ensuring consistency across the application. It supports generating keys for collections,
 * single entities, and custom operations, with proper handling of multi-part keys and delimiters.
 */
@Component
public class CacheKeyGenerator {

    /**
     * Generates a cache key for an application entity.
     *
     * @param applicationId The application ID
     * @return The cache key
     */
    public String generateApplicationKey(String applicationId) {
        validateId(applicationId);
        return CacheConstants.KEY_PREFIX_APPLICATION + applicationId;
    }

    /**
     * Generates a cache key for a document entity.
     *
     * @param documentId The document ID
     * @return The cache key
     */
    public String generateDocumentKey(String documentId) {
        validateId(documentId);
        return CacheConstants.KEY_PREFIX_DOCUMENT + documentId;
    }

    /**
     * Generates a cache key for a merchant entity.
     *
     * @param merchantId The merchant ID
     * @return The cache key
     */
    public String generateMerchantKey(String merchantId) {
        validateId(merchantId);
        return CacheConstants.KEY_PREFIX_MERCHANT + merchantId;
    }

    /**
     * Generates a cache key for a session.
     *
     * @param sessionId The session ID
     * @return The cache key
     */
    public String generateSessionKey(String sessionId) {
        validateId(sessionId);
        return CacheConstants.KEY_PREFIX_SESSION + sessionId;
    }

    /**
     * Generates a cache key for a collection of entities.
     *
     * @param entityType The entity type (e.g., "applications", "documents")
     * @param qualifier  An optional qualifier for the collection (e.g., "pending", "approved")
     * @return The cache key
     */
    public String generateCollectionKey(String entityType, String qualifier) {
        validateEntityType(entityType);
        
        if (qualifier == null || qualifier.isEmpty()) {
            return CacheConstants.KEY_PREFIX_COLLECTION + entityType;
        } else {
            validateQualifier(qualifier);
            return CacheConstants.KEY_PREFIX_COLLECTION + entityType + CacheConstants.KEY_DELIMITER + qualifier;
        }
    }

    /**
     * Generates a cache key for a counter.
     *
     * @param counterName The counter name
     * @return The cache key
     */
    public String generateCounterKey(String counterName) {
        validateName(counterName);
        return CacheConstants.KEY_PREFIX_COUNTER + counterName;
    }

    /**
     * Generates a cache key for a distributed lock.
     *
     * @param lockName The lock name
     * @return The cache key
     */
    public String generateLockKey(String lockName) {
        validateName(lockName);
        return CacheConstants.KEY_PREFIX_LOCK + lockName;
    }

    /**
     * Generates a custom cache key with multiple parts.
     *
     * @param prefix The key prefix
     * @param parts  The key parts
     * @return The cache key
     */
    public String generateCustomKey(String prefix, String... parts) {
        validatePrefix(prefix);
        
        if (parts == null || parts.length == 0) {
            return prefix;
        }
        
        StringBuilder keyBuilder = new StringBuilder(prefix);
        
        for (String part : parts) {
            if (part != null && !part.isEmpty()) {
                validateKeyPart(part);
                keyBuilder.append(CacheConstants.KEY_DELIMITER).append(part);
            }
        }
        
        return keyBuilder.toString();
    }

    /**
     * Validates an entity ID.
     *
     * @param id The entity ID to validate
     * @throws IllegalArgumentException if the ID is invalid
     */
    private void validateId(String id) {
        if (id == null || id.isEmpty()) {
            throw new IllegalArgumentException("Entity ID cannot be null or empty");
        }
        
        if (id.contains(CacheConstants.KEY_DELIMITER)) {
            throw new IllegalArgumentException("Entity ID cannot contain the delimiter: " + CacheConstants.KEY_DELIMITER);
        }
    }

    /**
     * Validates an entity type.
     *
     * @param entityType The entity type to validate
     * @throws IllegalArgumentException if the entity type is invalid
     */
    private void validateEntityType(String entityType) {
        if (entityType == null || entityType.isEmpty()) {
            throw new IllegalArgumentException("Entity type cannot be null or empty");
        }
        
        if (entityType.contains(CacheConstants.KEY_DELIMITER)) {
            throw new IllegalArgumentException("Entity type cannot contain the delimiter: " + CacheConstants.KEY_DELIMITER);
        }
    }

    /**
     * Validates a qualifier.
     *
     * @param qualifier The qualifier to validate
     * @throws IllegalArgumentException if the qualifier is invalid
     */
    private void validateQualifier(String qualifier) {
        if (qualifier.contains(CacheConstants.KEY_DELIMITER)) {
            throw new IllegalArgumentException("Qualifier cannot contain the delimiter: " + CacheConstants.KEY_DELIMITER);
        }
    }

    /**
     * Validates a name.
     *
     * @param name The name to validate
     * @throws IllegalArgumentException if the name is invalid
     */
    private void validateName(String name) {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("Name cannot be null or empty");
        }
        
        if (name.contains(CacheConstants.KEY_DELIMITER)) {
            throw new IllegalArgumentException("Name cannot contain the delimiter: " + CacheConstants.KEY_DELIMITER);
        }
    }

    /**
     * Validates a key prefix.
     *
     * @param prefix The prefix to validate
     * @throws IllegalArgumentException if the prefix is invalid
     */
    private void validatePrefix(String prefix) {
        if (prefix == null || prefix.isEmpty()) {
            throw new IllegalArgumentException("Prefix cannot be null or empty");
        }
    }

    /**
     * Validates a key part.
     *
     * @param part The key part to validate
     * @throws IllegalArgumentException if the key part is invalid
     */
    private void validateKeyPart(String part) {
        if (part.contains(CacheConstants.KEY_DELIMITER)) {
            throw new IllegalArgumentException("Key part cannot contain the delimiter: " + CacheConstants.KEY_DELIMITER);
        }
    }
}