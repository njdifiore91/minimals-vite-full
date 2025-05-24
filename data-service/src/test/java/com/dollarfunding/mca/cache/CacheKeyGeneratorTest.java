package com.dollarfunding.mca.cache;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link CacheKeyGenerator} utility class.
 * 
 * These tests verify that cache keys are generated correctly and consistently,
 * which is critical for the Redis cluster mode where keys are distributed
 * across nodes based on hash slots.
 */
public class CacheKeyGeneratorTest {

    /**
     * Test that entity-based cache keys are generated correctly with proper prefixing.
     * 
     * This test verifies that the generateEntityKey method correctly combines
     * the entity prefix with the entity ID to create a valid cache key.
     */
    @Test
    @DisplayName("Test entity-based cache key generation")
    public void testGenerateEntityKey() {
        // Test with string ID
        String key1 = CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.APPLICATION, "123");
        assertEquals(CacheConstants.KeyPrefix.APPLICATION + "123", key1, 
                "Entity key should be prefix + ID");
        
        // Test with numeric ID
        String key2 = CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.DOCUMENT, 456);
        assertEquals(CacheConstants.KeyPrefix.DOCUMENT + "456", key2, 
                "Entity key should work with numeric IDs");
        
        // Test with UUID-like ID
        String uuid = "550e8400-e29b-41d4-a716-446655440000";
        String key3 = CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.MERCHANT, uuid);
        assertEquals(CacheConstants.KeyPrefix.MERCHANT + uuid, key3, 
                "Entity key should work with UUID-like IDs");
    }

    /**
     * Test that entity-based cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateEntityKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test entity-based cache key generation with invalid inputs")
    public void testGenerateEntityKeyWithInvalidInputs() {
        // Test with null prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateEntityKey(null, "123");
        }, "Should throw exception when prefix is null");
        
        // Test with empty prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateEntityKey("", "123");
        }, "Should throw exception when prefix is empty");
        
        // Test with prefix that doesn't end with delimiter
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateEntityKey("invalid", "123");
        }, "Should throw exception when prefix doesn't end with delimiter");
        
        // Test with null ID
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.APPLICATION, null);
        }, "Should throw exception when ID is null");
    }

    /**
     * Test that application cache keys are generated correctly.
     * 
     * This test verifies that the generateApplicationKey method correctly
     * creates a cache key for an application entity.
     */
    @Test
    @DisplayName("Test application cache key generation")
    public void testGenerateApplicationKey() {
        String key = CacheKeyGenerator.generateApplicationKey("123");
        assertEquals(CacheConstants.KeyPrefix.APPLICATION + "123", key, 
                "Application key should be APPLICATION prefix + ID");
    }

    /**
     * Test that document cache keys are generated correctly.
     * 
     * This test verifies that the generateDocumentKey method correctly
     * creates a cache key for a document entity.
     */
    @Test
    @DisplayName("Test document cache key generation")
    public void testGenerateDocumentKey() {
        String key = CacheKeyGenerator.generateDocumentKey("456");
        assertEquals(CacheConstants.KeyPrefix.DOCUMENT + "456", key, 
                "Document key should be DOCUMENT prefix + ID");
    }

    /**
     * Test that merchant cache keys are generated correctly.
     * 
     * This test verifies that the generateMerchantKey method correctly
     * creates a cache key for a merchant entity.
     */
    @Test
    @DisplayName("Test merchant cache key generation")
    public void testGenerateMerchantKey() {
        String key = CacheKeyGenerator.generateMerchantKey("789");
        assertEquals(CacheConstants.KeyPrefix.MERCHANT + "789", key, 
                "Merchant key should be MERCHANT prefix + ID");
    }

    /**
     * Test that session cache keys are generated correctly.
     * 
     * This test verifies that the generateSessionKey method correctly
     * creates a cache key for a session entity.
     */
    @Test
    @DisplayName("Test session cache key generation")
    public void testGenerateSessionKey() {
        String key = CacheKeyGenerator.generateSessionKey("user123");
        assertEquals(CacheConstants.KeyPrefix.SESSION + "user123", key, 
                "Session key should be SESSION prefix + ID");
    }

    /**
     * Test that collection cache keys are generated correctly.
     * 
     * This test verifies that the generateCollectionKey method correctly
     * creates a cache key for a collection of entities.
     */
    @Test
    @DisplayName("Test collection cache key generation")
    public void testGenerateCollectionKey() {
        String key = CacheKeyGenerator.generateCollectionKey("applications");
        assertEquals(CacheConstants.KeyPrefix.COLLECTION + "applications", key, 
                "Collection key should be COLLECTION prefix + collection name");
    }

    /**
     * Test that collection cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateCollectionKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test collection cache key generation with invalid inputs")
    public void testGenerateCollectionKeyWithInvalidInputs() {
        // Test with null collection name
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionKey(null);
        }, "Should throw exception when collection name is null");
        
        // Test with empty collection name
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionKey("");
        }, "Should throw exception when collection name is empty");
    }

    /**
     * Test that filtered collection cache keys are generated correctly.
     * 
     * This test verifies that the generateFilteredCollectionKey method correctly
     * creates a cache key for a filtered collection of entities.
     */
    @Test
    @DisplayName("Test filtered collection cache key generation")
    public void testGenerateFilteredCollectionKey() {
        // Create filter parameters
        Map<String, Object> filterParams = new HashMap<>();
        filterParams.put("status", "PENDING");
        filterParams.put("type", "INVOICE");
        
        String key = CacheKeyGenerator.generateFilteredCollectionKey("documents", filterParams);
        
        // The filter parameters should be sorted by key to ensure consistent key generation
        String expectedKey = CacheConstants.KeyPrefix.COLLECTION + "documents" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "status" + 
                CacheConstants.Delimiter.PAIR_DELIMITER + "PENDING" + 
                CacheConstants.Delimiter.LIST_DELIMITER + "type" + 
                CacheConstants.Delimiter.PAIR_DELIMITER + "INVOICE";
        
        assertEquals(expectedKey, key, 
                "Filtered collection key should include sorted filter parameters");
    }

    /**
     * Test that filtered collection cache key generation handles null values correctly.
     * 
     * This test verifies that the generateFilteredCollectionKey method correctly
     * handles null values in filter parameters.
     */
    @Test
    @DisplayName("Test filtered collection cache key generation with null values")
    public void testGenerateFilteredCollectionKeyWithNullValues() {
        // Create filter parameters with null value
        Map<String, Object> filterParams = new HashMap<>();
        filterParams.put("status", "PENDING");
        filterParams.put("type", null);
        
        String key = CacheKeyGenerator.generateFilteredCollectionKey("documents", filterParams);
        
        // The filter parameters should be sorted by key to ensure consistent key generation
        String expectedKey = CacheConstants.KeyPrefix.COLLECTION + "documents" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "status" + 
                CacheConstants.Delimiter.PAIR_DELIMITER + "PENDING" + 
                CacheConstants.Delimiter.LIST_DELIMITER + "type" + 
                CacheConstants.Delimiter.PAIR_DELIMITER + "null";
        
        assertEquals(expectedKey, key, 
                "Filtered collection key should handle null values correctly");
    }

    /**
     * Test that filtered collection cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateFilteredCollectionKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test filtered collection cache key generation with invalid inputs")
    public void testGenerateFilteredCollectionKeyWithInvalidInputs() {
        Map<String, Object> filterParams = new HashMap<>();
        filterParams.put("status", "PENDING");
        
        // Test with null collection name
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateFilteredCollectionKey(null, filterParams);
        }, "Should throw exception when collection name is null");
        
        // Test with empty collection name
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateFilteredCollectionKey("", filterParams);
        }, "Should throw exception when collection name is empty");
        
        // Test with null filter parameters
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateFilteredCollectionKey("documents", null);
        }, "Should throw exception when filter parameters are null");
    }

    /**
     * Test that count cache keys are generated correctly.
     * 
     * This test verifies that the generateCountKey method correctly
     * creates a cache key for a count operation.
     */
    @Test
    @DisplayName("Test count cache key generation")
    public void testGenerateCountKey() {
        // Test with filter parameters
        Map<String, Object> filterParams = new HashMap<>();
        filterParams.put("status", "PENDING");
        
        String key = CacheKeyGenerator.generateCountKey(CacheConstants.KeyPrefix.APPLICATION, filterParams);
        
        // The key should include the COUNT prefix, the entity prefix, and the filter parameters
        String expectedKey = CacheConstants.KeyPrefix.COUNT + 
                CacheConstants.KeyPrefix.APPLICATION.replace(CacheConstants.Delimiter.KEY_DELIMITER, "") + 
                CacheConstants.Delimiter.KEY_DELIMITER + "status" + 
                CacheConstants.Delimiter.PAIR_DELIMITER + "PENDING";
        
        assertEquals(expectedKey, key, 
                "Count key should include entity prefix and filter parameters");
        
        // Test without filter parameters
        String key2 = CacheKeyGenerator.generateCountKey(CacheConstants.KeyPrefix.APPLICATION, null);
        
        // The key should include only the COUNT prefix and the entity prefix
        String expectedKey2 = CacheConstants.KeyPrefix.COUNT + 
                CacheConstants.KeyPrefix.APPLICATION.replace(CacheConstants.Delimiter.KEY_DELIMITER, "");
        
        assertEquals(expectedKey2, key2, 
                "Count key without filter parameters should include only entity prefix");
    }

    /**
     * Test that count cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateCountKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test count cache key generation with invalid inputs")
    public void testGenerateCountKeyWithInvalidInputs() {
        // Test with null entity prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCountKey(null, null);
        }, "Should throw exception when entity prefix is null");
        
        // Test with empty entity prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCountKey("", null);
        }, "Should throw exception when entity prefix is empty");
        
        // Test with entity prefix that doesn't end with delimiter
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCountKey("invalid", null);
        }, "Should throw exception when entity prefix doesn't end with delimiter");
    }

    /**
     * Test that metadata cache keys are generated correctly.
     * 
     * This test verifies that the generateMetadataKey method correctly
     * creates a cache key for metadata associated with an entity.
     */
    @Test
    @DisplayName("Test metadata cache key generation")
    public void testGenerateMetadataKey() {
        String key = CacheKeyGenerator.generateMetadataKey(
                CacheConstants.KeyPrefix.APPLICATION, "123", "status");
        
        // The key should include the METADATA prefix, the entity prefix, the entity ID, and the metadata type
        String expectedKey = CacheConstants.KeyPrefix.METADATA + 
                CacheConstants.KeyPrefix.APPLICATION + "123" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "status";
        
        assertEquals(expectedKey, key, 
                "Metadata key should include entity prefix, ID, and metadata type");
    }

    /**
     * Test that metadata cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateMetadataKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test metadata cache key generation with invalid inputs")
    public void testGenerateMetadataKeyWithInvalidInputs() {
        // Test with null entity prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMetadataKey(null, "123", "status");
        }, "Should throw exception when entity prefix is null");
        
        // Test with empty entity prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMetadataKey("", "123", "status");
        }, "Should throw exception when entity prefix is empty");
        
        // Test with entity prefix that doesn't end with delimiter
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMetadataKey("invalid", "123", "status");
        }, "Should throw exception when entity prefix doesn't end with delimiter");
        
        // Test with null entity ID
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMetadataKey(CacheConstants.KeyPrefix.APPLICATION, null, "status");
        }, "Should throw exception when entity ID is null");
        
        // Test with null metadata type
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMetadataKey(CacheConstants.KeyPrefix.APPLICATION, "123", null);
        }, "Should throw exception when metadata type is null");
        
        // Test with empty metadata type
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMetadataKey(CacheConstants.KeyPrefix.APPLICATION, "123", "");
        }, "Should throw exception when metadata type is empty");
    }

    /**
     * Test that operation cache keys are generated correctly.
     * 
     * This test verifies that the generateOperationKey method correctly
     * creates a cache key for a custom operation.
     */
    @Test
    @DisplayName("Test operation cache key generation")
    public void testGenerateOperationKey() {
        String key = CacheKeyGenerator.generateOperationKey("calculateTotal", "123", "USD");
        
        // The key should include the operation name and the operation parameters
        String expectedKey = "calculateTotal" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "123" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "USD";
        
        assertEquals(expectedKey, key, 
                "Operation key should include operation name and parameters");
    }

    /**
     * Test that operation cache key generation handles null parameters correctly.
     * 
     * This test verifies that the generateOperationKey method correctly
     * handles null values in operation parameters.
     */
    @Test
    @DisplayName("Test operation cache key generation with null parameters")
    public void testGenerateOperationKeyWithNullParameters() {
        String key = CacheKeyGenerator.generateOperationKey("calculateTotal", "123", null, "USD");
        
        // The key should include the operation name and the non-null operation parameters
        String expectedKey = "calculateTotal" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "123" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "USD";
        
        assertEquals(expectedKey, key, 
                "Operation key should filter out null parameters");
    }

    /**
     * Test that operation cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateOperationKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test operation cache key generation with invalid inputs")
    public void testGenerateOperationKeyWithInvalidInputs() {
        // Test with null operation
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateOperationKey(null, "123");
        }, "Should throw exception when operation is null");
        
        // Test with empty operation
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateOperationKey("", "123");
        }, "Should throw exception when operation is empty");
        
        // Test with null parameters
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateOperationKey("calculateTotal", null);
        }, "Should throw exception when parameters are null");
    }

    /**
     * Test that multi-part cache keys are generated correctly.
     * 
     * This test verifies that the generateMultiPartKey method correctly
     * creates a cache key from multiple parts.
     */
    @Test
    @DisplayName("Test multi-part cache key generation")
    public void testGenerateMultiPartKey() {
        String key = CacheKeyGenerator.generateMultiPartKey("part1", "part2", "part3");
        
        // The key should include all parts joined by the key delimiter
        String expectedKey = "part1" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "part2" + 
                CacheConstants.Delimiter.KEY_DELIMITER + "part3";
        
        assertEquals(expectedKey, key, 
                "Multi-part key should include all parts joined by the key delimiter");
    }

    /**
     * Test that multi-part cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateMultiPartKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test multi-part cache key generation with invalid inputs")
    public void testGenerateMultiPartKeyWithInvalidInputs() {
        // Test with null parts
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMultiPartKey((String[]) null);
        }, "Should throw exception when parts are null");
        
        // Test with empty parts array
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMultiPartKey(new String[0]);
        }, "Should throw exception when parts array is empty");
        
        // Test with null part
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMultiPartKey("part1", null, "part3");
        }, "Should throw exception when a part is null");
        
        // Test with empty part
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateMultiPartKey("part1", "", "part3");
        }, "Should throw exception when a part is empty");
    }

    /**
     * Test that collection items cache keys are generated correctly.
     * 
     * This test verifies that the generateCollectionItemsKey method correctly
     * creates a cache key for a collection of items.
     */
    @Test
    @DisplayName("Test collection items cache key generation")
    public void testGenerateCollectionItemsKey() {
        List<String> items = Arrays.asList("item3", "item1", "item2");
        
        String key = CacheKeyGenerator.generateCollectionItemsKey(CacheConstants.KeyPrefix.APPLICATION, items);
        
        // The key should include the prefix and the items sorted alphabetically
        String expectedKey = CacheConstants.KeyPrefix.APPLICATION + 
                "item1" + CacheConstants.Delimiter.LIST_DELIMITER + 
                "item2" + CacheConstants.Delimiter.LIST_DELIMITER + 
                "item3";
        
        assertEquals(expectedKey, key, 
                "Collection items key should include prefix and sorted items");
    }

    /**
     * Test that collection items cache key generation handles null items correctly.
     * 
     * This test verifies that the generateCollectionItemsKey method correctly
     * handles null values in the collection of items.
     */
    @Test
    @DisplayName("Test collection items cache key generation with null items")
    public void testGenerateCollectionItemsKeyWithNullItems() {
        List<String> items = Arrays.asList("item1", null, "item2");
        
        String key = CacheKeyGenerator.generateCollectionItemsKey(CacheConstants.KeyPrefix.APPLICATION, items);
        
        // The key should include the prefix and the non-null items sorted alphabetically
        String expectedKey = CacheConstants.KeyPrefix.APPLICATION + 
                "item1" + CacheConstants.Delimiter.LIST_DELIMITER + 
                "item2";
        
        assertEquals(expectedKey, key, 
                "Collection items key should filter out null items");
    }

    /**
     * Test that collection items cache key generation fails with invalid inputs.
     * 
     * This test verifies that the generateCollectionItemsKey method throws appropriate
     * exceptions when given invalid inputs.
     */
    @Test
    @DisplayName("Test collection items cache key generation with invalid inputs")
    public void testGenerateCollectionItemsKeyWithInvalidInputs() {
        List<String> items = Arrays.asList("item1", "item2");
        
        // Test with null prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionItemsKey(null, items);
        }, "Should throw exception when prefix is null");
        
        // Test with empty prefix
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionItemsKey("", items);
        }, "Should throw exception when prefix is empty");
        
        // Test with prefix that doesn't end with delimiter
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionItemsKey("invalid", items);
        }, "Should throw exception when prefix doesn't end with delimiter");
        
        // Test with null items collection
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionItemsKey(CacheConstants.KeyPrefix.APPLICATION, null);
        }, "Should throw exception when items collection is null");
        
        // Test with empty items collection
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionItemsKey(CacheConstants.KeyPrefix.APPLICATION, 
                    Arrays.asList());
        }, "Should throw exception when items collection is empty");
    }

    /**
     * Test that cache keys with invalid characters are rejected.
     * 
     * This test verifies that the validateKey method correctly rejects
     * cache keys that contain invalid characters.
     */
    @Test
    @DisplayName("Test cache key validation with invalid characters")
    public void testCacheKeyValidationWithInvalidCharacters() {
        // We can't directly test the private validateKey method, but we can test it indirectly
        // by calling a public method that uses it with inputs that would result in invalid keys
        
        // Test with invalid characters in entity ID
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.APPLICATION, "123 456");
        }, "Should throw exception when entity ID contains spaces");
        
        // Test with invalid characters in collection name
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateCollectionKey("applications/documents");
        }, "Should throw exception when collection name contains slashes");
        
        // Test with invalid characters in operation name
        assertThrows(IllegalArgumentException.class, () -> {
            CacheKeyGenerator.generateOperationKey("calculate Total", "123");
        }, "Should throw exception when operation name contains spaces");
    }

    /**
     * Provides test cases for parameterized tests.
     * 
     * @return a stream of arguments for parameterized tests
     */
    private static Stream<Arguments> provideValidCacheKeys() {
        return Stream.of(
            // Entity keys
            Arguments.of(CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.APPLICATION, "123")),
            Arguments.of(CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.DOCUMENT, 456)),
            Arguments.of(CacheKeyGenerator.generateEntityKey(CacheConstants.KeyPrefix.MERCHANT, "789")),
            
            // Collection keys
            Arguments.of(CacheKeyGenerator.generateCollectionKey("applications")),
            Arguments.of(CacheKeyGenerator.generateCollectionKey("documents")),
            
            // Multi-part keys
            Arguments.of(CacheKeyGenerator.generateMultiPartKey("part1", "part2", "part3")),
            
            // Operation keys
            Arguments.of(CacheKeyGenerator.generateOperationKey("calculateTotal", "123", "USD"))
        );
    }

    /**
     * Test that all generated cache keys are valid according to the VALID_KEY_PATTERN.
     * 
     * This test verifies that all keys generated by the CacheKeyGenerator methods
     * conform to the pattern defined in the VALID_KEY_PATTERN constant.
     */
    @ParameterizedTest
    @MethodSource("provideValidCacheKeys")
    @DisplayName("Test that all generated cache keys are valid")
    public void testAllGeneratedKeysAreValid(String key) {
        // This test doesn't directly assert anything, but if the key is invalid,
        // the CacheKeyGenerator would have thrown an exception when generating it
        assertNotNull(key, "Generated key should not be null");
        assertTrue(key.length() > 0, "Generated key should not be empty");
    }

    /**
     * Test that the CacheKeyGenerator class cannot be instantiated.
     * 
     * This test verifies that the utility class is properly designed to prevent instantiation.
     */
    @Test
    @DisplayName("Test that CacheKeyGenerator cannot be instantiated")
    public void testCannotInstantiate() {
        // Verify that the class cannot be instantiated
        assertThrows(AssertionError.class, () -> {
            // Use reflection to call the private constructor
            java.lang.reflect.Constructor<CacheKeyGenerator> constructor = 
                    CacheKeyGenerator.class.getDeclaredConstructor();
            constructor.setAccessible(true);
            constructor.newInstance();
        }, "CacheKeyGenerator should not be instantiable");
    }
}