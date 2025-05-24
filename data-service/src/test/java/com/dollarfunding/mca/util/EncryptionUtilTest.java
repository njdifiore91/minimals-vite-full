package com.dollarfunding.mca.util;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;

/**
 * Unit tests for the {@link EncryptionUtil} class that provides field-level encryption
 * and decryption functionality for Personally Identifiable Information (PII) in the MCA application.
 * 
 * These tests verify:
 * 1. AES-256 encryption/decryption operations
 * 2. Secure key management
 * 3. Validation of encryption operations
 * 4. Logging of encryption activities
 * 5. Field encryption determination
 */
@ExtendWith(MockitoExtension.class)
public class EncryptionUtilTest {

    private EncryptionUtil encryptionUtil;
    
    @Mock
    private Logger mockLogger;
    
    @Captor
    private ArgumentCaptor<String> logCaptor;
    
    // Test encryption keys
    private static final String TEST_SECRET = "ThisIsATestSecretForEncryption123";
    private static final String TEST_SALT = "TestSalt123456789";
    
    @BeforeEach
    void setUp() throws Exception {
        // Create a new EncryptionUtil instance for each test
        encryptionUtil = new EncryptionUtil();
        
        // Set the encryption secret and salt
        encryptionUtil.setEncryptionSecret(TEST_SECRET);
        encryptionUtil.setEncryptionSalt(TEST_SALT);
        
        // Replace the logger with a mock for testing logging behavior
        Field loggerField = EncryptionUtil.class.getDeclaredField("logger");
        loggerField.setAccessible(true);
        loggerField.set(null, mockLogger);
    }
    
    @Nested
    @DisplayName("Encryption Tests")
    class EncryptionTests {
        
        @Test
        @DisplayName("Should encrypt string correctly")
        void shouldEncryptStringCorrectly() {
            // Given
            String plaintext = "Sensitive personal information";
            
            // When
            String encrypted = encryptionUtil.encrypt(plaintext);
            
            // Then
            assertNotNull(encrypted, "Encrypted text should not be null");
            assertNotEquals(plaintext, encrypted, "Encrypted text should be different from plaintext");
            
            // Verify the encrypted text is Base64 encoded
            assertTrue(encrypted.matches("^[A-Za-z0-9+/=]+$"), "Encrypted text should be Base64 encoded");
            
            // Verify logging
            verify(mockLogger).debug("Successfully encrypted data");
        }
        
        @Test
        @DisplayName("Should encrypt different strings to different ciphertexts")
        void shouldEncryptDifferentStringsToDifferentCiphertexts() {
            // Given
            String plaintext1 = "First sensitive string";
            String plaintext2 = "Second sensitive string";
            
            // When
            String encrypted1 = encryptionUtil.encrypt(plaintext1);
            String encrypted2 = encryptionUtil.encrypt(plaintext2);
            
            // Then
            assertNotEquals(encrypted1, encrypted2, "Different plaintexts should encrypt to different ciphertexts");
        }
        
        @Test
        @DisplayName("Should encrypt same string to different ciphertexts due to random IV")
        void shouldEncryptSameStringToDifferentCiphertexts() {
            // Given
            String plaintext = "Same sensitive string";
            
            // When
            String encrypted1 = encryptionUtil.encrypt(plaintext);
            String encrypted2 = encryptionUtil.encrypt(plaintext);
            
            // Then
            assertNotEquals(encrypted1, encrypted2, "Same plaintext should encrypt to different ciphertexts due to random IV");
        }
        
        @Test
        @DisplayName("Should handle null input for encryption")
        void shouldHandleNullInputForEncryption() {
            // When
            String encrypted = encryptionUtil.encrypt(null);
            
            // Then
            assertNull(encrypted, "Encrypting null should return null");
            verify(mockLogger).warn("Attempted to encrypt null or empty string");
        }
        
        @Test
        @DisplayName("Should handle empty input for encryption")
        void shouldHandleEmptyInputForEncryption() {
            // Given
            String plaintext = "";
            
            // When
            String encrypted = encryptionUtil.encrypt(plaintext);
            
            // Then
            assertEquals(plaintext, encrypted, "Encrypting empty string should return empty string");
            verify(mockLogger).warn("Attempted to encrypt null or empty string");
        }
        
        @Test
        @DisplayName("Should log error when encryption fails")
        void shouldLogErrorWhenEncryptionFails() throws Exception {
            // Given
            encryptionUtil.setEncryptionSecret(null); // This will cause encryption to fail
            String plaintext = "This will fail to encrypt";
            
            // When
            String encrypted = encryptionUtil.encrypt(plaintext);
            
            // Then
            assertNull(encrypted, "Failed encryption should return null");
            verify(mockLogger).error(eq("Encryption failed"), any(Exception.class));
        }
    }
    
    @Nested
    @DisplayName("Decryption Tests")
    class DecryptionTests {
        
        @Test
        @DisplayName("Should decrypt encrypted string back to original plaintext")
        void shouldDecryptEncryptedStringBackToOriginalPlaintext() {
            // Given
            String plaintext = "Sensitive personal information";
            String encrypted = encryptionUtil.encrypt(plaintext);
            
            // When
            String decrypted = encryptionUtil.decrypt(encrypted);
            
            // Then
            assertEquals(plaintext, decrypted, "Decrypted text should match original plaintext");
            verify(mockLogger).debug("Successfully decrypted data");
        }
        
        @Test
        @DisplayName("Should handle null input for decryption")
        void shouldHandleNullInputForDecryption() {
            // When
            String decrypted = encryptionUtil.decrypt(null);
            
            // Then
            assertNull(decrypted, "Decrypting null should return null");
            verify(mockLogger).warn("Attempted to decrypt null or empty string");
        }
        
        @Test
        @DisplayName("Should handle empty input for decryption")
        void shouldHandleEmptyInputForDecryption() {
            // Given
            String encrypted = "";
            
            // When
            String decrypted = encryptionUtil.decrypt(encrypted);
            
            // Then
            assertEquals(encrypted, decrypted, "Decrypting empty string should return empty string");
            verify(mockLogger).warn("Attempted to decrypt null or empty string");
        }
        
        @Test
        @DisplayName("Should log error when decryption fails")
        void shouldLogErrorWhenDecryptionFails() {
            // Given
            String invalidEncrypted = "ThisIsNotValidBase64!@#$";
            
            // When
            String decrypted = encryptionUtil.decrypt(invalidEncrypted);
            
            // Then
            assertNull(decrypted, "Failed decryption should return null");
            verify(mockLogger).error(eq("Decryption failed"), any(Exception.class));
        }
        
        @Test
        @DisplayName("Should fail to decrypt with wrong key")
        void shouldFailToDecryptWithWrongKey() {
            // Given
            String plaintext = "Sensitive data";
            String encrypted = encryptionUtil.encrypt(plaintext);
            
            // Create a new EncryptionUtil with different keys
            EncryptionUtil differentKeyUtil = new EncryptionUtil();
            differentKeyUtil.setEncryptionSecret("DifferentSecret123");
            differentKeyUtil.setEncryptionSalt("DifferentSalt123");
            
            // When
            String decrypted = differentKeyUtil.decrypt(encrypted);
            
            // Then
            assertNull(decrypted, "Decryption with wrong key should fail and return null");
        }
    }
    
    @Nested
    @DisplayName("Key Management Tests")
    class KeyManagementTests {
        
        @Test
        @DisplayName("Should get and set encryption secret correctly")
        void shouldGetAndSetEncryptionSecretCorrectly() {
            // Given
            String newSecret = "NewTestSecret123";
            
            // When
            encryptionUtil.setEncryptionSecret(newSecret);
            String retrievedSecret = encryptionUtil.getEncryptionSecret();
            
            // Then
            assertEquals(newSecret, retrievedSecret, "Retrieved secret should match the set secret");
        }
        
        @Test
        @DisplayName("Should get and set encryption salt correctly")
        void shouldGetAndSetEncryptionSaltCorrectly() {
            // Given
            String newSalt = "NewTestSalt123";
            
            // When
            encryptionUtil.setEncryptionSalt(newSalt);
            String retrievedSalt = encryptionUtil.getEncryptionSalt();
            
            // Then
            assertEquals(newSalt, retrievedSalt, "Retrieved salt should match the set salt");
        }
        
        @Test
        @DisplayName("Should fail key derivation with null or empty secret")
        void shouldFailKeyDerivationWithNullOrEmptySecret() throws Exception {
            // Given
            encryptionUtil.setEncryptionSecret(null);
            String plaintext = "This will fail to encrypt";
            
            // When
            String encrypted = encryptionUtil.encrypt(plaintext);
            
            // Then
            assertNull(encrypted, "Encryption with null secret should fail");
            verify(mockLogger).error(eq("Encryption failed"), any(Exception.class));
        }
        
        @Test
        @DisplayName("Should fail key derivation with null or empty salt")
        void shouldFailKeyDerivationWithNullOrEmptySalt() throws Exception {
            // Given
            encryptionUtil.setEncryptionSalt(null);
            String plaintext = "This will fail to encrypt";
            
            // When
            String encrypted = encryptionUtil.encrypt(plaintext);
            
            // Then
            assertNull(encrypted, "Encryption with null salt should fail");
            verify(mockLogger).error(eq("Encryption failed"), any(Exception.class));
        }
    }
    
    @Nested
    @DisplayName("Field Encryption Determination Tests")
    class FieldEncryptionDeterminationTests {
        
        @ParameterizedTest
        @ValueSource(strings = {
            "firstName", "lastName", "fullName", "customerName", 
            "ssn", "socialSecurityNumber", 
            "taxId", "taxIdentificationNumber", 
            "ein", "employerIdentificationNumber", 
            "phoneNumber", "mobilePhone", 
            "emailAddress", "email", 
            "homeAddress", "billingAddress", "shippingAddress", 
            "accountNumber", "bankAccountNumber", 
            "creditCardNumber", "cardNumber", 
            "driversLicense", "licenseNumber", 
            "passportNumber", "passport", 
            "dateOfBirth", "dob", "birthDate"
        })
        @DisplayName("Should identify PII fields that require encryption")
        void shouldIdentifyPiiFieldsThatRequireEncryption(String fieldName) {
            // When
            boolean requiresEncryption = encryptionUtil.requiresEncryption(fieldName);
            
            // Then
            assertTrue(requiresEncryption, "Field '" + fieldName + "' should require encryption");
        }
        
        @ParameterizedTest
        @ValueSource(strings = {
            "id", "status", "createdAt", "updatedAt", 
            "amount", "total", "count", 
            "isActive", "isEnabled", "isDeleted", 
            "description", "notes", "comments", 
            "type", "category", "group", 
            "version", "sequence", "order"
        })
        @DisplayName("Should identify non-PII fields that do not require encryption")
        void shouldIdentifyNonPiiFieldsThatDoNotRequireEncryption(String fieldName) {
            // When
            boolean requiresEncryption = encryptionUtil.requiresEncryption(fieldName);
            
            // Then
            assertFalse(requiresEncryption, "Field '" + fieldName + "' should not require encryption");
        }
        
        @Test
        @DisplayName("Should handle null field name")
        void shouldHandleNullFieldName() {
            // When
            boolean requiresEncryption = encryptionUtil.requiresEncryption(null);
            
            // Then
            assertFalse(requiresEncryption, "Null field name should not require encryption");
        }
        
        @Test
        @DisplayName("Should handle empty field name")
        void shouldHandleEmptyFieldName() {
            // When
            boolean requiresEncryption = encryptionUtil.requiresEncryption("");
            
            // Then
            assertFalse(requiresEncryption, "Empty field name should not require encryption");
        }
    }
    
    @Nested
    @DisplayName("Integration Tests")
    class IntegrationTests {
        
        @Test
        @DisplayName("Should encrypt and decrypt large text")
        void shouldEncryptAndDecryptLargeText() {
            // Given
            StringBuilder largeTextBuilder = new StringBuilder();
            for (int i = 0; i < 1000; i++) {
                largeTextBuilder.append("This is a large text that needs to be encrypted. Line ").append(i).append("\n");
            }
            String largeText = largeTextBuilder.toString();
            
            // When
            String encrypted = encryptionUtil.encrypt(largeText);
            String decrypted = encryptionUtil.decrypt(encrypted);
            
            // Then
            assertEquals(largeText, decrypted, "Decrypted large text should match original");
        }
        
        @Test
        @DisplayName("Should encrypt and decrypt text with special characters")
        void shouldEncryptAndDecryptTextWithSpecialCharacters() {
            // Given
            String specialText = "Special characters: !@#$%^&*()_+-=[]{}|;':,.<>/?`~\\";
            
            // When
            String encrypted = encryptionUtil.encrypt(specialText);
            String decrypted = encryptionUtil.decrypt(encrypted);
            
            // Then
            assertEquals(specialText, decrypted, "Decrypted text with special characters should match original");
        }
        
        @Test
        @DisplayName("Should encrypt and decrypt text with non-ASCII characters")
        void shouldEncryptAndDecryptTextWithNonAsciiCharacters() {
            // Given
            String nonAsciiText = "Non-ASCII characters: áéíóúñÁÉÍÓÚÑ¿¡€£¥©®™ßµ¶§";
            
            // When
            String encrypted = encryptionUtil.encrypt(nonAsciiText);
            String decrypted = encryptionUtil.decrypt(encrypted);
            
            // Then
            assertEquals(nonAsciiText, decrypted, "Decrypted text with non-ASCII characters should match original");
        }
        
        @Test
        @DisplayName("Should encrypt and decrypt binary data")
        void shouldEncryptAndDecryptBinaryData() {
            // Given
            byte[] binaryData = new byte[256];
            for (int i = 0; i < binaryData.length; i++) {
                binaryData[i] = (byte) i;
            }
            String binaryString = Base64.getEncoder().encodeToString(binaryData);
            
            // When
            String encrypted = encryptionUtil.encrypt(binaryString);
            String decrypted = encryptionUtil.decrypt(encrypted);
            
            // Then
            assertEquals(binaryString, decrypted, "Decrypted binary data should match original");
            
            // Verify we can convert back to binary
            byte[] decryptedBinary = Base64.getDecoder().decode(decrypted);
            assertArrayEquals(binaryData, decryptedBinary, "Decoded binary data should match original");
        }
    }
}