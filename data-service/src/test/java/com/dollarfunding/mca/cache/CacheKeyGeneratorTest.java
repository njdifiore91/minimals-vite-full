package com.dollarfunding.mca.cache;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link CacheKeyGenerator} utility class.
 * 
 * These tests verify that the CacheKeyGenerator correctly creates standardized cache keys
 * for use with Redis, following the required patterns and validation rules.
 */
@DisplayName("CacheKeyGenerator Tests")
class CacheKeyGeneratorTest {

    private static final String TEST_ENTITY_TYPE = "application";
    private static final String TEST_ID = "abc123";
    private static final Long TEST_NUMERIC_ID = 123456L;
    private static final String TEST_PREFIX = "test";
    private static final String TEST_OPERATION = "count";

    @Nested
    @DisplayName("Entity Key Generation Tests")
    class EntityKeyGenerationTests {

        @Test
        @DisplayName("Should generate entity key with default prefix")
        void shouldGenerateEntityKeyWithDefaultPrefix() {
            // When
            String key = CacheKeyGenerator.generateKey(TEST_ENTITY_TYPE, TEST_ID);
            
            // Then
            assertEquals("mca:application:abc123", key);
        }

        @Test
        @DisplayName("Should generate entity key with custom prefix")
        void shouldGenerateEntityKeyWithCustomPrefix() {
            // When
            String key = CacheKeyGenerator.generateKey(TEST_PREFIX, TEST_ENTITY_TYPE, TEST_ID);
            
            // Then
            assertEquals("test:application:abc123", key);
        }

        @Test
        @DisplayName("Should generate entity key with numeric ID")
        void shouldGenerateEntityKeyWithNumericId() {
            // When
            String key = CacheKeyGenerator.generateKey(TEST_ENTITY_TYPE, TEST_NUMERIC_ID);
            
            // Then
            assertEquals("mca:application:123456", key);
        }
    }

    @Nested
    @DisplayName("Collection Key Generation Tests")
    class CollectionKeyGenerationTests {

        @Test
        @DisplayName("Should generate collection key with default prefix")
        void shouldGenerateCollectionKeyWithDefaultPrefix() {
            // When
            String key = CacheKeyGenerator.generateCollectionKey(TEST_ENTITY_TYPE);
            
            // Then
            assertEquals("mca:application:collection", key);
        }

        @Test
        @DisplayName("Should generate collection key with custom prefix")
        void shouldGenerateCollectionKeyWithCustomPrefix() {
            // When
            String key = CacheKeyGenerator.generateCollectionKey(TEST_PREFIX, TEST_ENTITY_TYPE);
            
            // Then
            assertEquals("test:application:collection", key);
        }
    }

    @Nested
    @DisplayName("Operation Key Generation Tests")
    class OperationKeyGenerationTests {

        @Test
        @DisplayName("Should generate operation key with string ID")
        void shouldGenerateOperationKeyWithStringId() {
            // When
            String key = CacheKeyGenerator.generateOperationKey(TEST_ENTITY_TYPE, TEST_OPERATION, TEST_ID);
            
            // Then
            assertEquals("mca:application:count:abc123", key);
        }

        @Test
        @DisplayName("Should generate operation key with numeric ID")
        void shouldGenerateOperationKeyWithNumericId() {
            // When
            String key = CacheKeyGenerator.generateOperationKey(TEST_ENTITY_TYPE, TEST_OPERATION, TEST_NUMERIC_ID);
            
            // Then
            assertEquals("mca:application:count:123456", key);
        }

        @Test
        @DisplayName("Should generate collection operation key")
        void shouldGenerateCollectionOperationKey() {
            // When
            String key = CacheKeyGenerator.generateCollectionOperationKey(TEST_ENTITY_TYPE, TEST_OPERATION);
            
            // Then
            assertEquals("mca:application:count:collection", key);
        }
    }

    @Nested
    @DisplayName("Custom Key Generation Tests")
    class CustomKeyGenerationTests {

        @Test
        @DisplayName("Should generate custom key with multiple parts")
        void shouldGenerateCustomKeyWithMultipleParts() {
            // When
            String key = CacheKeyGenerator.generateCustomKey("part1", "part2", "part3");
            
            // Then
            assertEquals("part1:part2:part3", key);
        }

        @Test
        @DisplayName("Should generate custom key with single part")
        void shouldGenerateCustomKeyWithSinglePart() {
            // When
            String key = CacheKeyGenerator.generateCustomKey("singlepart");
            
            // Then
            assertEquals("singlepart", key);
        }
    }

    @Nested
    @DisplayName("Validation Tests")
    class ValidationTests {

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "\t", "\n"})
        @DisplayName("Should throw exception for null or empty entity type")
        void shouldThrowExceptionForNullOrEmptyEntityType(String entityType) {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateKey(entityType, TEST_ID);
            });
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "\t", "\n"})
        @DisplayName("Should throw exception for null or empty ID")
        void shouldThrowExceptionForNullOrEmptyId(String id) {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateKey(TEST_ENTITY_TYPE, id);
            });
        }

        @Test
        @DisplayName("Should throw exception for null numeric ID")
        void shouldThrowExceptionForNullNumericId() {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateKey(TEST_ENTITY_TYPE, (Long) null);
            });
        }

        @ParameterizedTest
        @ValueSource(strings = {"invalid:key", "invalid key", "invalid/key", "invalid\\key", "invalid*key", "invalid?key"})
        @DisplayName("Should throw exception for invalid characters in entity type")
        void shouldThrowExceptionForInvalidCharactersInEntityType(String invalidEntityType) {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateKey(invalidEntityType, TEST_ID);
            });
        }

        @ParameterizedTest
        @ValueSource(strings = {"invalid:id", "invalid id", "invalid/id", "invalid\\id", "invalid*id", "invalid?id"})
        @DisplayName("Should throw exception for invalid characters in ID")
        void shouldThrowExceptionForInvalidCharactersInId(String invalidId) {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateKey(TEST_ENTITY_TYPE, invalidId);
            });
        }

        @ParameterizedTest
        @ValueSource(strings = {"invalid:prefix", "invalid prefix", "invalid/prefix", "invalid\\prefix", "invalid*prefix", "invalid?prefix"})
        @DisplayName("Should throw exception for invalid characters in prefix")
        void shouldThrowExceptionForInvalidCharactersInPrefix(String invalidPrefix) {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateKey(invalidPrefix, TEST_ENTITY_TYPE, TEST_ID);
            });
        }

        @ParameterizedTest
        @ValueSource(strings = {"invalid:operation", "invalid operation", "invalid/operation", "invalid\\operation", "invalid*operation", "invalid?operation"})
        @DisplayName("Should throw exception for invalid characters in operation")
        void shouldThrowExceptionForInvalidCharactersInOperation(String invalidOperation) {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateOperationKey(TEST_ENTITY_TYPE, invalidOperation, TEST_ID);
            });
        }

        @Test
        @DisplayName("Should throw exception for empty components array in custom key")
        void shouldThrowExceptionForEmptyComponentsArrayInCustomKey() {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateCustomKey(new String[0]);
            });
        }

        @Test
        @DisplayName("Should throw exception for null components array in custom key")
        void shouldThrowExceptionForNullComponentsArrayInCustomKey() {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateCustomKey((String[]) null);
            });
        }

        @Test
        @DisplayName("Should throw exception for invalid component in custom key")
        void shouldThrowExceptionForInvalidComponentInCustomKey() {
            // Then
            assertThrows(IllegalArgumentException.class, () -> {
                CacheKeyGenerator.generateCustomKey("valid", "invalid:component", "valid2");
            });
        }
    }

    @Nested
    @DisplayName("Performance Requirement Tests")
    class PerformanceRequirementTests {

        @Test
        @DisplayName("Should generate keys with consistent format for high-volume operations")
        void shouldGenerateKeysWithConsistentFormatForHighVolumeOperations() {
            // This test verifies that key generation is consistent for high-volume operations
            // which is important for the 99.9% system uptime requirement
            
            // When generating multiple keys for the same entity type and operation
            String key1 = CacheKeyGenerator.generateOperationKey(TEST_ENTITY_TYPE, TEST_OPERATION, "id1");
            String key2 = CacheKeyGenerator.generateOperationKey(TEST_ENTITY_TYPE, TEST_OPERATION, "id2");
            
            // Then the keys should follow the same format with only the ID differing
            assertTrue(key1.startsWith("mca:application:count:"));
            assertTrue(key2.startsWith("mca:application:count:"));
            assertEquals("mca:application:count:id1", key1);
            assertEquals("mca:application:count:id2", key2);
        }

        @Test
        @DisplayName("Should support valid characters needed for all entity types")
        void shouldSupportValidCharactersNeededForAllEntityTypes() {
            // This test verifies that the key generator supports all valid characters
            // needed for entity types, which is important for application processing
            
            // When using entity types with various valid characters
            String key1 = CacheKeyGenerator.generateKey("application-type", TEST_ID);
            String key2 = CacheKeyGenerator.generateKey("application_type", TEST_ID);
            String key3 = CacheKeyGenerator.generateKey("application.type", TEST_ID);
            
            // Then all keys should be generated successfully
            assertEquals("mca:application-type:abc123", key1);
            assertEquals("mca:application_type:abc123", key2);
            assertEquals("mca:application.type:abc123", key3);
        }
    }
}