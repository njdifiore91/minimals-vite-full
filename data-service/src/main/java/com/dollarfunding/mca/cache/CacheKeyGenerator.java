package com.dollarfunding.mca.cache;

import java.util.Arrays;
import java.util.Collection;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import org.springframework.util.Assert;
import org.springframework.util.StringUtils;

/**
 * Utility class for generating consistent cache keys in the MCA application.
 * <p>
 * This class provides methods for creating standardized cache keys based on entity type and ID,
 * ensuring consistency across the application. It supports generating keys for collections,
 * single entities, and custom operations, with proper handling of multi-part keys and delimiters.
 * </p>
 * <p>
 * Consistent key generation is critical for Redis cluster mode, where keys are distributed
 * across nodes based on hash slots. Using standardized key formats ensures that related data
 * is properly co-located and can be efficiently accessed.
 * </p>
 * <p>
 * This class supports the cache-aside pattern implemented in the application, where the cache
 * is checked before database queries and updated with query results.
 * </p>
 */
public final class CacheKeyGenerator {

    /**
     * Pattern for validating cache keys to ensure they don't contain invalid characters.
     * Redis keys can contain any binary sequence, but for maintainability and debugging,
     * we restrict keys to alphanumeric characters, underscores, hyphens, and the delimiters
     * defined in CacheConstants.Delimiter.
     */
    private static final Pattern VALID_KEY_PATTERN = 
            Pattern.compile("^[\\w\\-" + 
                    Pattern.quote(CacheConstants.Delimiter.KEY_DELIMITER) + 
                    Pattern.quote(CacheConstants.Delimiter.LIST_DELIMITER) + 
                    Pattern.quote(CacheConstants.Delimiter.PAIR_DELIMITER) + 
                    "]+$");

    /**
     * Private constructor to prevent instantiation of this utility class.
     */
    private CacheKeyGenerator() {
        throw new AssertionError("CacheKeyGenerator is a utility class and should not be instantiated");
    }

    /**
     * Generates a cache key for a single entity based on entity type and ID.
     * 
     * @param entityPrefix the entity type prefix from CacheConstants.KeyPrefix
     * @param id the entity ID
     * @return the generated cache key
     * @throws IllegalArgumentException if entityPrefix is null or empty, or if id is null
     */
    public static String generateEntityKey(String entityPrefix, Object id) {
        validatePrefix(entityPrefix);
        Assert.notNull(id, "Entity ID must not be null");
        
        String key = entityPrefix + id.toString();
        validateKey(key);
        return key;
    }

    /**
     * Generates a cache key for an application entity.
     * 
     * @param applicationId the application ID
     * @return the generated cache key
     * @throws IllegalArgumentException if applicationId is null
     */
    public static String generateApplicationKey(Object applicationId) {
        return generateEntityKey(CacheConstants.KeyPrefix.APPLICATION, applicationId);
    }

    /**
     * Generates a cache key for a document entity.
     * 
     * @param documentId the document ID
     * @return the generated cache key
     * @throws IllegalArgumentException if documentId is null
     */
    public static String generateDocumentKey(Object documentId) {
        return generateEntityKey(CacheConstants.KeyPrefix.DOCUMENT, documentId);
    }

    /**
     * Generates a cache key for a merchant entity.
     * 
     * @param merchantId the merchant ID
     * @return the generated cache key
     * @throws IllegalArgumentException if merchantId is null
     */
    public static String generateMerchantKey(Object merchantId) {
        return generateEntityKey(CacheConstants.KeyPrefix.MERCHANT, merchantId);
    }

    /**
     * Generates a cache key for a session.
     * 
     * @param sessionId the session ID
     * @return the generated cache key
     * @throws IllegalArgumentException if sessionId is null
     */
    public static String generateSessionKey(String sessionId) {
        return generateEntityKey(CacheConstants.KeyPrefix.SESSION, sessionId);
    }

    /**
     * Generates a cache key for a collection of entities.
     * 
     * @param collectionName the name of the collection
     * @return the generated cache key
     * @throws IllegalArgumentException if collectionName is null or empty
     */
    public static String generateCollectionKey(String collectionName) {
        validateString(collectionName, "Collection name");
        
        String key = CacheConstants.KeyPrefix.COLLECTION + collectionName;
        validateKey(key);
        return key;
    }

    /**
     * Generates a cache key for a filtered collection of entities.
     * 
     * @param collectionName the name of the collection
     * @param filterParams a map of filter parameters
     * @return the generated cache key
     * @throws IllegalArgumentException if collectionName is null or empty, or if filterParams is null
     */
    public static String generateFilteredCollectionKey(String collectionName, Map<String, Object> filterParams) {
        validateString(collectionName, "Collection name");
        Assert.notNull(filterParams, "Filter parameters must not be null");
        
        // Sort filter parameters by key to ensure consistent key generation
        String filterString = filterParams.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .map(entry -> entry.getKey() + CacheConstants.Delimiter.PAIR_DELIMITER + 
                        (entry.getValue() == null ? "null" : entry.getValue().toString()))
                .collect(Collectors.joining(CacheConstants.Delimiter.LIST_DELIMITER));
        
        String key = CacheConstants.KeyPrefix.COLLECTION + collectionName + 
                CacheConstants.Delimiter.KEY_DELIMITER + filterString;
        validateKey(key);
        return key;
    }

    /**
     * Generates a cache key for a count operation.
     * 
     * @param entityPrefix the entity type prefix from CacheConstants.KeyPrefix
     * @param filterParams a map of filter parameters (can be null for total count)
     * @return the generated cache key
     * @throws IllegalArgumentException if entityPrefix is null or empty
     */
    public static String generateCountKey(String entityPrefix, Map<String, Object> filterParams) {
        validatePrefix(entityPrefix);
        
        StringBuilder keyBuilder = new StringBuilder(CacheConstants.KeyPrefix.COUNT)
                .append(entityPrefix.replace(CacheConstants.Delimiter.KEY_DELIMITER, ""));
        
        if (filterParams != null && !filterParams.isEmpty()) {
            // Sort filter parameters by key to ensure consistent key generation
            String filterString = filterParams.entrySet().stream()
                    .sorted(Map.Entry.comparingByKey())
                    .map(entry -> entry.getKey() + CacheConstants.Delimiter.PAIR_DELIMITER + 
                            (entry.getValue() == null ? "null" : entry.getValue().toString()))
                    .collect(Collectors.joining(CacheConstants.Delimiter.LIST_DELIMITER));
            
            keyBuilder.append(CacheConstants.Delimiter.KEY_DELIMITER).append(filterString);
        }
        
        String key = keyBuilder.toString();
        validateKey(key);
        return key;
    }

    /**
     * Generates a cache key for metadata associated with an entity.
     * 
     * @param entityPrefix the entity type prefix from CacheConstants.KeyPrefix
     * @param id the entity ID
     * @param metadataType the type of metadata
     * @return the generated cache key
     * @throws IllegalArgumentException if any parameter is null or empty
     */
    public static String generateMetadataKey(String entityPrefix, Object id, String metadataType) {
        validatePrefix(entityPrefix);
        Assert.notNull(id, "Entity ID must not be null");
        validateString(metadataType, "Metadata type");
        
        String key = CacheConstants.KeyPrefix.METADATA + entityPrefix + id.toString() + 
                CacheConstants.Delimiter.KEY_DELIMITER + metadataType;
        validateKey(key);
        return key;
    }

    /**
     * Generates a cache key for a custom operation.
     * 
     * @param operation the operation name
     * @param params the operation parameters
     * @return the generated cache key
     * @throws IllegalArgumentException if operation is null or empty, or if any parameter is null
     */
    public static String generateOperationKey(String operation, Object... params) {
        validateString(operation, "Operation");
        Assert.notNull(params, "Operation parameters must not be null");
        
        String paramsString = Arrays.stream(params)
                .filter(Objects::nonNull)
                .map(Object::toString)
                .collect(Collectors.joining(CacheConstants.Delimiter.KEY_DELIMITER));
        
        String key = operation + CacheConstants.Delimiter.KEY_DELIMITER + paramsString;
        validateKey(key);
        return key;
    }

    /**
     * Generates a cache key for a multi-part key.
     * 
     * @param parts the parts of the key
     * @return the generated cache key
     * @throws IllegalArgumentException if parts is null or empty, or if any part is null
     */
    public static String generateMultiPartKey(String... parts) {
        Assert.notNull(parts, "Key parts must not be null");
        Assert.isTrue(parts.length > 0, "At least one key part must be provided");
        
        for (int i = 0; i < parts.length; i++) {
            validateString(parts[i], "Key part at index " + i);
        }
        
        String key = String.join(CacheConstants.Delimiter.KEY_DELIMITER, parts);
        validateKey(key);
        return key;
    }

    /**
     * Generates a cache key for a collection of items.
     * 
     * @param prefix the key prefix
     * @param items the collection of items
     * @return the generated cache key
     * @throws IllegalArgumentException if prefix is null or empty, or if items is null or empty
     */
    public static String generateCollectionItemsKey(String prefix, Collection<?> items) {
        validatePrefix(prefix);
        Assert.notNull(items, "Items collection must not be null");
        Assert.isTrue(!items.isEmpty(), "Items collection must not be empty");
        
        String itemsString = items.stream()
                .filter(Objects::nonNull)
                .map(Object::toString)
                .sorted() // Sort items for consistent key generation
                .collect(Collectors.joining(CacheConstants.Delimiter.LIST_DELIMITER));
        
        String key = prefix + itemsString;
        validateKey(key);
        return key;
    }

    /**
     * Validates that a string is not null or empty.
     * 
     * @param value the string to validate
     * @param name the name of the parameter for error messages
     * @throws IllegalArgumentException if the string is null or empty
     */
    private static void validateString(String value, String name) {
        Assert.isTrue(StringUtils.hasText(value), name + " must not be null or empty");
    }

    /**
     * Validates that a prefix is not null or empty and ends with the key delimiter.
     * 
     * @param prefix the prefix to validate
     * @throws IllegalArgumentException if the prefix is null, empty, or doesn't end with the key delimiter
     */
    private static void validatePrefix(String prefix) {
        validateString(prefix, "Prefix");
        Assert.isTrue(prefix.endsWith(CacheConstants.Delimiter.KEY_DELIMITER), 
                "Prefix must end with the key delimiter: " + CacheConstants.Delimiter.KEY_DELIMITER);
    }

    /**
     * Validates that a cache key contains only valid characters.
     * 
     * @param key the cache key to validate
     * @throws IllegalArgumentException if the key contains invalid characters
     */
    private static void validateKey(String key) {
        Assert.isTrue(VALID_KEY_PATTERN.matcher(key).matches(), 
                "Cache key contains invalid characters: " + key);
    }
}