package com.dollarfunding.mca.cache;

import org.springframework.util.Assert;
import org.springframework.util.StringUtils;

import java.util.Arrays;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Utility class for generating consistent cache keys in the MCA application.
 * <p>
 * This class provides methods for creating standardized cache keys based on entity type and ID,
 * ensuring consistency across the application. It supports generating keys for collections,
 * single entities, and custom operations, with proper handling of multi-part keys and delimiters.
 * </p>
 * <p>
 * The generated keys follow the format: prefix:entityType:id or prefix:entityType:operation:id
 * where prefix is a namespace for the application, entityType is the type of entity being cached,
 * operation is an optional operation name, and id is the entity identifier.
 * </p>
 * <p>
 * For collection keys, the format is: prefix:entityType:collection
 * </p>
 *
 * @author MCA Development Team
 */
public final class CacheKeyGenerator {

    /**
     * The default namespace prefix for all cache keys
     */
    private static final String DEFAULT_PREFIX = "mca";
    
    /**
     * The delimiter used to separate parts of the cache key
     */
    private static final String DELIMITER = ":";
    
    /**
     * Pattern for validating cache key components
     * Allows alphanumeric characters, underscores, hyphens, and periods
     */
    private static final Pattern VALID_KEY_PATTERN = Pattern.compile("^[\\w\\-\\.]+$");

    /**
     * Private constructor to prevent instantiation
     */
    private CacheKeyGenerator() {
        // Utility class should not be instantiated
    }

    /**
     * Generates a cache key for a specific entity instance
     *
     * @param entityType the type of entity (e.g., "application", "document")
     * @param id the entity identifier
     * @return the generated cache key
     * @throws IllegalArgumentException if entityType or id is null or empty
     */
    public static String generateKey(String entityType, String id) {
        validateKeyComponent(entityType, "Entity type");
        validateKeyComponent(id, "ID");
        
        return joinKeyParts(DEFAULT_PREFIX, entityType, id);
    }

    /**
     * Generates a cache key for a specific entity instance with a custom prefix
     *
     * @param prefix the custom prefix to use instead of the default
     * @param entityType the type of entity (e.g., "application", "document")
     * @param id the entity identifier
     * @return the generated cache key
     * @throws IllegalArgumentException if any parameter is null or empty
     */
    public static String generateKey(String prefix, String entityType, String id) {
        validateKeyComponent(prefix, "Prefix");
        validateKeyComponent(entityType, "Entity type");
        validateKeyComponent(id, "ID");
        
        return joinKeyParts(prefix, entityType, id);
    }

    /**
     * Generates a cache key for a specific entity instance with a numeric ID
     *
     * @param entityType the type of entity (e.g., "application", "document")
     * @param id the numeric entity identifier
     * @return the generated cache key
     * @throws IllegalArgumentException if entityType is null or empty
     */
    public static String generateKey(String entityType, Long id) {
        validateKeyComponent(entityType, "Entity type");
        Assert.notNull(id, "ID must not be null");
        
        return joinKeyParts(DEFAULT_PREFIX, entityType, id.toString());
    }

    /**
     * Generates a cache key for a collection of entities
     *
     * @param entityType the type of entity collection (e.g., "applications", "documents")
     * @return the generated cache key
     * @throws IllegalArgumentException if entityType is null or empty
     */
    public static String generateCollectionKey(String entityType) {
        validateKeyComponent(entityType, "Entity type");
        
        return joinKeyParts(DEFAULT_PREFIX, entityType, "collection");
    }

    /**
     * Generates a cache key for a collection of entities with a custom prefix
     *
     * @param prefix the custom prefix to use instead of the default
     * @param entityType the type of entity collection (e.g., "applications", "documents")
     * @return the generated cache key
     * @throws IllegalArgumentException if any parameter is null or empty
     */
    public static String generateCollectionKey(String prefix, String entityType) {
        validateKeyComponent(prefix, "Prefix");
        validateKeyComponent(entityType, "Entity type");
        
        return joinKeyParts(prefix, entityType, "collection");
    }

    /**
     * Generates a cache key for a custom operation on an entity
     *
     * @param entityType the type of entity (e.g., "application", "document")
     * @param operation the operation name (e.g., "count", "summary")
     * @param id the entity identifier
     * @return the generated cache key
     * @throws IllegalArgumentException if any parameter is null or empty
     */
    public static String generateOperationKey(String entityType, String operation, String id) {
        validateKeyComponent(entityType, "Entity type");
        validateKeyComponent(operation, "Operation");
        validateKeyComponent(id, "ID");
        
        return joinKeyParts(DEFAULT_PREFIX, entityType, operation, id);
    }

    /**
     * Generates a cache key for a custom operation on an entity with a numeric ID
     *
     * @param entityType the type of entity (e.g., "application", "document")
     * @param operation the operation name (e.g., "count", "summary")
     * @param id the numeric entity identifier
     * @return the generated cache key
     * @throws IllegalArgumentException if entityType or operation is null or empty
     */
    public static String generateOperationKey(String entityType, String operation, Long id) {
        validateKeyComponent(entityType, "Entity type");
        validateKeyComponent(operation, "Operation");
        Assert.notNull(id, "ID must not be null");
        
        return joinKeyParts(DEFAULT_PREFIX, entityType, operation, id.toString());
    }

    /**
     * Generates a cache key for a custom operation on a collection of entities
     *
     * @param entityType the type of entity collection (e.g., "applications", "documents")
     * @param operation the operation name (e.g., "count", "summary")
     * @return the generated cache key
     * @throws IllegalArgumentException if any parameter is null or empty
     */
    public static String generateCollectionOperationKey(String entityType, String operation) {
        validateKeyComponent(entityType, "Entity type");
        validateKeyComponent(operation, "Operation");
        
        return joinKeyParts(DEFAULT_PREFIX, entityType, operation, "collection");
    }

    /**
     * Generates a multi-part cache key with custom components
     *
     * @param components the key components to join
     * @return the generated cache key
     * @throws IllegalArgumentException if components is null or empty
     */
    public static String generateCustomKey(String... components) {
        Assert.notEmpty(components, "Components must not be null or empty");
        
        for (int i = 0; i < components.length; i++) {
            validateKeyComponent(components[i], "Component at index " + i);
        }
        
        return joinKeyParts(components);
    }

    /**
     * Joins key parts with the delimiter
     *
     * @param parts the parts to join
     * @return the joined key
     */
    private static String joinKeyParts(String... parts) {
        return Arrays.stream(parts)
                .collect(Collectors.joining(DELIMITER));
    }

    /**
     * Validates a key component
     *
     * @param component the component to validate
     * @param componentName the name of the component for error messages
     * @throws IllegalArgumentException if the component is invalid
     */
    private static void validateKeyComponent(String component, String componentName) {
        Assert.hasText(component, componentName + " must not be null or empty");
        
        if (!VALID_KEY_PATTERN.matcher(component).matches()) {
            throw new IllegalArgumentException(componentName + 
                    " contains invalid characters. Only alphanumeric characters, underscores, hyphens, and periods are allowed.");
        }
    }
}