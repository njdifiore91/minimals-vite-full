package com.dollarfunding.mca.config;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

import javax.crypto.Cipher;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.dollarfunding.mca.config.EncryptionConfig.EncryptionService;
import com.dollarfunding.mca.config.EncryptionConfig.JsonEncryptionConverter;
import com.dollarfunding.mca.config.EncryptionConfig.StringEncryptionConverter;

/**
 * Unit tests for the {@link EncryptionConfig} class that configures field-level encryption
 * for sensitive data in the MCA application.
 * 
 * These tests verify:
 * 1. AES-256 encryption configuration for sensitive data fields
 * 2. Encryption key management and rotation configuration
 * 3. Attribute converter configuration for automatic encryption/decryption of entity fields
 * 4. Secure key storage and access configuration
 * 5. Encryption context configuration for multi-tenant scenarios
 */
@ExtendWith(MockitoExtension.class)
public class EncryptionConfigTest {

    @Mock
    private Environment environment;
    
    private EncryptionConfig encryptionConfig;
    private ObjectMapper objectMapper;
    
    // Test encryption keys (Base64 encoded)
    private static final String TEST_PRIMARY_KEY = "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="; // 32 bytes for AES-256
    private static final String TEST_SECONDARY_KEY = "QUJDREVGMTIzNDU2Nzg5MEFCQ0RFRjEyMzQ1Njc4OTA="; // 32 bytes for AES-256
    private static final String TEST_TENANT_ID = "test-tenant";
    
    @BeforeEach
    void setUp() throws NoSuchAlgorithmException, NoSuchPaddingException {
        // Create a new EncryptionConfig instance for each test
        encryptionConfig = new EncryptionConfig(environment);
        
        // Set the encryption keys and tenant ID using reflection
        ReflectionTestUtils.setField(encryptionConfig, "primaryKeyString", TEST_PRIMARY_KEY);
        ReflectionTestUtils.setField(encryptionConfig, "secondaryKeyString", TEST_SECONDARY_KEY);
        ReflectionTestUtils.setField(encryptionConfig, "keyRotationEnabled", true);
        ReflectionTestUtils.setField(encryptionConfig, "tenantId", TEST_TENANT_ID);
        
        // Create a new ObjectMapper for JSON tests
        objectMapper = new ObjectMapper();
    }
    
    @Nested
    @DisplayName("Primary Encryption Key Tests")
    class PrimaryEncryptionKeyTests {
        
        @Test
        @DisplayName("Should create primary encryption key from provided key string")
        void shouldCreatePrimaryEncryptionKeyFromProvidedKeyString() throws Exception {
            // When
            SecretKey primaryKey = encryptionConfig.primaryEncryptionKey();
            
            // Then
            assertNotNull(primaryKey, "Primary encryption key should not be null");
            assertEquals("AES", primaryKey.getAlgorithm(), "Algorithm should be AES");
            assertEquals(32, primaryKey.getEncoded().length, "Key length should be 32 bytes (256 bits)");
            
            // Verify the key matches the expected value
            byte[] expectedKeyBytes = Base64.getDecoder().decode(TEST_PRIMARY_KEY);
            assertArrayEquals(expectedKeyBytes, primaryKey.getEncoded(), "Key bytes should match the provided key");
        }
        
        @Test
        @DisplayName("Should generate new primary encryption key when none is provided")
        void shouldGenerateNewPrimaryEncryptionKeyWhenNoneIsProvided() throws Exception {
            // Given
            ReflectionTestUtils.setField(encryptionConfig, "primaryKeyString", null);
            when(environment.matchesProfiles("production")).thenReturn(false);
            
            // When
            SecretKey primaryKey = encryptionConfig.primaryEncryptionKey();
            
            // Then
            assertNotNull(primaryKey, "Primary encryption key should not be null");
            assertEquals("AES", primaryKey.getAlgorithm(), "Algorithm should be AES");
            assertEquals(32, primaryKey.getEncoded().length, "Key length should be 32 bytes (256 bits)");
        }
        
        @Test
        @DisplayName("Should not log generated key in production environment")
        void shouldNotLogGeneratedKeyInProductionEnvironment() throws Exception {
            // Given
            ReflectionTestUtils.setField(encryptionConfig, "primaryKeyString", null);
            when(environment.matchesProfiles("production")).thenReturn(true);
            
            // When
            SecretKey primaryKey = encryptionConfig.primaryEncryptionKey();
            
            // Then
            assertNotNull(primaryKey, "Primary encryption key should not be null");
            verify(environment).matchesProfiles("production");
        }
    }
    
    @Nested
    @DisplayName("Secondary Encryption Key Tests")
    class SecondaryEncryptionKeyTests {
        
        @Test
        @DisplayName("Should create secondary encryption key when key rotation is enabled")
        void shouldCreateSecondaryEncryptionKeyWhenKeyRotationIsEnabled() throws Exception {
            // When
            SecretKey secondaryKey = encryptionConfig.secondaryEncryptionKey();
            
            // Then
            assertNotNull(secondaryKey, "Secondary encryption key should not be null");
            assertEquals("AES", secondaryKey.getAlgorithm(), "Algorithm should be AES");
            assertEquals(32, secondaryKey.getEncoded().length, "Key length should be 32 bytes (256 bits)");
            
            // Verify the key matches the expected value
            byte[] expectedKeyBytes = Base64.getDecoder().decode(TEST_SECONDARY_KEY);
            assertArrayEquals(expectedKeyBytes, secondaryKey.getEncoded(), "Key bytes should match the provided key");
        }
        
        @Test
        @DisplayName("Should return null for secondary key when key rotation is disabled")
        void shouldReturnNullForSecondaryKeyWhenKeyRotationIsDisabled() throws Exception {
            // Given
            ReflectionTestUtils.setField(encryptionConfig, "keyRotationEnabled", false);
            
            // When
            SecretKey secondaryKey = encryptionConfig.secondaryEncryptionKey();
            
            // Then
            assertNull(secondaryKey, "Secondary encryption key should be null when key rotation is disabled");
        }
        
        @Test
        @DisplayName("Should return null for secondary key when no secondary key is provided")
        void shouldReturnNullForSecondaryKeyWhenNoSecondaryKeyIsProvided() throws Exception {
            // Given
            ReflectionTestUtils.setField(encryptionConfig, "secondaryKeyString", null);
            
            // When
            SecretKey secondaryKey = encryptionConfig.secondaryEncryptionKey();
            
            // Then
            assertNull(secondaryKey, "Secondary encryption key should be null when no key is provided");
        }
    }
    
    @Nested
    @DisplayName("Encryption Cipher Tests")
    class EncryptionCipherTests {
        
        @Test
        @DisplayName("Should create encryption cipher with AES/GCM/NoPadding algorithm")
        void shouldCreateEncryptionCipherWithAesGcmNoPaddingAlgorithm() throws Exception {
            // When
            Cipher cipher = encryptionConfig.encryptionCipher();
            
            // Then
            assertNotNull(cipher, "Encryption cipher should not be null");
            assertEquals("AES/GCM/NoPadding", cipher.getAlgorithm(), "Algorithm should be AES/GCM/NoPadding");
        }
    }
    
    @Nested
    @DisplayName("Encryption Service Tests")
    class EncryptionServiceTests {
        
        private EncryptionService encryptionService;
        private SecretKey primaryKey;
        private SecretKey secondaryKey;
        private Cipher cipher;
        
        @BeforeEach
        void setUp() throws Exception {
            // Create the necessary components for the encryption service
            primaryKey = encryptionConfig.primaryEncryptionKey();
            secondaryKey = encryptionConfig.secondaryEncryptionKey();
            cipher = encryptionConfig.encryptionCipher();
            
            // Create the encryption service
            encryptionService = encryptionConfig.encryptionService(primaryKey, secondaryKey, cipher);
        }
        
        @Test
        @DisplayName("Should encrypt and decrypt string correctly")
        void shouldEncryptAndDecryptStringCorrectly() {
            // Given
            String plaintext = "Sensitive data that needs to be encrypted";
            
            // When
            String encrypted = encryptionService.encrypt(plaintext);
            String decrypted = encryptionService.decrypt(encrypted);
            
            // Then
            assertNotNull(encrypted, "Encrypted text should not be null");
            assertNotEquals(plaintext, encrypted, "Encrypted text should be different from plaintext");
            assertEquals(plaintext, decrypted, "Decrypted text should match the original plaintext");
        }
        
        @Test
        @DisplayName("Should handle null and empty strings")
        void shouldHandleNullAndEmptyStrings() {
            // Given
            String nullString = null;
            String emptyString = "";
            
            // When & Then
            assertNull(encryptionService.encrypt(nullString), "Encrypting null should return null");
            assertNull(encryptionService.decrypt(nullString), "Decrypting null should return null");
            assertEquals(emptyString, encryptionService.encrypt(emptyString), "Encrypting empty string should return empty string");
            assertEquals(emptyString, encryptionService.decrypt(emptyString), "Decrypting empty string should return empty string");
        }
        
        @Test
        @DisplayName("Should use tenant ID as additional authenticated data when provided")
        void shouldUseTenantIdAsAdditionalAuthenticatedDataWhenProvided() {
            // Given
            String plaintext = "Multi-tenant sensitive data";
            
            // When
            String encrypted = encryptionService.encrypt(plaintext);
            String decrypted = encryptionService.decrypt(encrypted);
            
            // Then
            assertEquals(plaintext, decrypted, "Decrypted text should match the original plaintext");
            
            // Create a new encryption service with a different tenant ID
            EncryptionService differentTenantService = new EncryptionService(primaryKey, secondaryKey, cipher, "different-tenant");
            
            // This should fail because the tenant ID is different
            Exception exception = assertThrows(RuntimeException.class, () -> {
                differentTenantService.decrypt(encrypted);
            }, "Decryption with different tenant ID should fail");
            
            assertTrue(exception.getMessage().contains("Error decrypting data"), "Exception message should indicate decryption error");
        }
        
        @Test
        @DisplayName("Should decrypt data with secondary key when primary key fails")
        void shouldDecryptDataWithSecondaryKeyWhenPrimaryKeyFails() throws Exception {
            // Given
            String plaintext = "Data encrypted with old key";
            
            // Create a service with the secondary key as primary for encryption
            EncryptionService oldKeyService = new EncryptionService(secondaryKey, null, cipher, TEST_TENANT_ID);
            String encryptedWithOldKey = oldKeyService.encrypt(plaintext);
            
            // When - decrypt with the new service that has the old key as secondary
            String decrypted = encryptionService.decrypt(encryptedWithOldKey);
            
            // Then
            assertEquals(plaintext, decrypted, "Should decrypt data encrypted with old key using secondary key");
        }
    }
    
    @Nested
    @DisplayName("String Encryption Converter Tests")
    class StringEncryptionConverterTests {
        
        private StringEncryptionConverter converter;
        private EncryptionService encryptionService;
        
        @BeforeEach
        void setUp() throws Exception {
            // Create the necessary components for the encryption service
            SecretKey primaryKey = encryptionConfig.primaryEncryptionKey();
            SecretKey secondaryKey = encryptionConfig.secondaryEncryptionKey();
            Cipher cipher = encryptionConfig.encryptionCipher();
            
            // Create the encryption service
            encryptionService = encryptionConfig.encryptionService(primaryKey, secondaryKey, cipher);
            
            // Create the converter
            converter = encryptionConfig.stringEncryptionConverter(encryptionService);
        }
        
        @Test
        @DisplayName("Should convert entity attribute to encrypted database column")
        void shouldConvertEntityAttributeToEncryptedDatabaseColumn() {
            // Given
            String attribute = "Sensitive personal information";
            
            // When
            String dbColumn = converter.convertToDatabaseColumn(attribute);
            
            // Then
            assertNotNull(dbColumn, "Database column should not be null");
            assertNotEquals(attribute, dbColumn, "Database column should be encrypted");
        }
        
        @Test
        @DisplayName("Should convert encrypted database column to entity attribute")
        void shouldConvertEncryptedDatabaseColumnToEntityAttribute() {
            // Given
            String attribute = "Sensitive personal information";
            String dbColumn = converter.convertToDatabaseColumn(attribute);
            
            // When
            String convertedAttribute = converter.convertToEntityAttribute(dbColumn);
            
            // Then
            assertEquals(attribute, convertedAttribute, "Converted attribute should match original");
        }
        
        @Test
        @DisplayName("Should handle null values")
        void shouldHandleNullValues() {
            // When & Then
            assertNull(converter.convertToDatabaseColumn(null), "Converting null attribute should return null");
            assertNull(converter.convertToEntityAttribute(null), "Converting null database column should return null");
        }
    }
    
    @Nested
    @DisplayName("JSON Encryption Converter Tests")
    class JsonEncryptionConverterTests {
        
        private JsonEncryptionConverter converter;
        private EncryptionService encryptionService;
        
        @BeforeEach
        void setUp() throws Exception {
            // Create the necessary components for the encryption service
            SecretKey primaryKey = encryptionConfig.primaryEncryptionKey();
            SecretKey secondaryKey = encryptionConfig.secondaryEncryptionKey();
            Cipher cipher = encryptionConfig.encryptionCipher();
            
            // Create the encryption service
            encryptionService = encryptionConfig.encryptionService(primaryKey, secondaryKey, cipher);
            
            // Create the converter
            converter = encryptionConfig.jsonEncryptionConverter(encryptionService, objectMapper);
        }
        
        @Test
        @DisplayName("Should convert entity attribute to encrypted database column")
        void shouldConvertEntityAttributeToEncryptedDatabaseColumn() throws JsonProcessingException {
            // Given
            Map<String, Object> attribute = new HashMap<>();
            attribute.put("name", "John Doe");
            attribute.put("ssn", "123-45-6789");
            attribute.put("address", "123 Main St, Anytown, USA");
            
            // When
            String dbColumn = converter.convertToDatabaseColumn(attribute);
            
            // Then
            assertNotNull(dbColumn, "Database column should not be null");
            assertNotEquals(objectMapper.writeValueAsString(attribute), dbColumn, "Database column should be encrypted");
        }
        
        @Test
        @DisplayName("Should convert encrypted database column to entity attribute")
        void shouldConvertEncryptedDatabaseColumnToEntityAttribute() {
            // Given
            Map<String, Object> attribute = new HashMap<>();
            attribute.put("name", "John Doe");
            attribute.put("ssn", "123-45-6789");
            attribute.put("address", "123 Main St, Anytown, USA");
            
            String dbColumn = converter.convertToDatabaseColumn(attribute);
            
            // When
            Map<String, Object> convertedAttribute = converter.convertToEntityAttribute(dbColumn);
            
            // Then
            assertNotNull(convertedAttribute, "Converted attribute should not be null");
            assertEquals(attribute.get("name"), convertedAttribute.get("name"), "Name should match");
            assertEquals(attribute.get("ssn"), convertedAttribute.get("ssn"), "SSN should match");
            assertEquals(attribute.get("address"), convertedAttribute.get("address"), "Address should match");
        }
        
        @Test
        @DisplayName("Should handle null values")
        void shouldHandleNullValues() {
            // When & Then
            assertNull(converter.convertToDatabaseColumn(null), "Converting null attribute should return null");
            assertNull(converter.convertToEntityAttribute(null), "Converting null database column should return null");
        }
        
        @Test
        @DisplayName("Should throw RuntimeException when JSON processing fails")
        void shouldThrowRuntimeExceptionWhenJsonProcessingFails() throws Exception {
            // Given
            ObjectMapper mockMapper = mock(ObjectMapper.class);
            when(mockMapper.writeValueAsString(any())).thenThrow(new JsonProcessingException("Test exception") {});
            
            JsonEncryptionConverter brokenConverter = new JsonEncryptionConverter(encryptionService, mockMapper);
            Map<String, Object> attribute = new HashMap<>();
            attribute.put("test", "value");
            
            // When & Then
            Exception exception = assertThrows(RuntimeException.class, () -> {
                brokenConverter.convertToDatabaseColumn(attribute);
            }, "Should throw RuntimeException when JSON processing fails");
            
            assertTrue(exception.getMessage().contains("Error converting JSON to database column"), 
                    "Exception message should indicate JSON conversion error");
        }
    }
    
    @Nested
    @DisplayName("Bean Creation Tests")
    class BeanCreationTests {
        
        @Test
        @DisplayName("Should create ObjectMapper bean")
        void shouldCreateObjectMapperBean() {
            // When
            ObjectMapper mapper = encryptionConfig.objectMapper();
            
            // Then
            assertNotNull(mapper, "ObjectMapper bean should not be null");
        }
        
        @Test
        @DisplayName("Should create StringEncryptionConverter bean")
        void shouldCreateStringEncryptionConverterBean() throws Exception {
            // Given
            EncryptionService service = mock(EncryptionService.class);
            
            // When
            StringEncryptionConverter converter = encryptionConfig.stringEncryptionConverter(service);
            
            // Then
            assertNotNull(converter, "StringEncryptionConverter bean should not be null");
        }
        
        @Test
        @DisplayName("Should create JsonEncryptionConverter bean")
        void shouldCreateJsonEncryptionConverterBean() throws Exception {
            // Given
            EncryptionService service = mock(EncryptionService.class);
            ObjectMapper mapper = mock(ObjectMapper.class);
            
            // When
            JsonEncryptionConverter converter = encryptionConfig.jsonEncryptionConverter(service, mapper);
            
            // Then
            assertNotNull(converter, "JsonEncryptionConverter bean should not be null");
        }
    }
}