package com.dollarfunding.mca.util;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link EncryptionUtil} class which provides field-level encryption
 * and decryption functionality for Personally Identifiable Information (PII) in the MCA application.
 * 
 * These tests verify AES-256 encryption/decryption operations, secure key management,
 * validation of encryption operations, logging of encryption activities, and field encryption determination.
 */
@ExtendWith(MockitoExtension.class)
public class EncryptionUtilTest {

    @Spy
    @InjectMocks
    private EncryptionUtil encryptionUtil;
    
    @Mock
    private Logger loggerMock;
    
    private final String testSecret = "test-encryption-secret-key-for-unit-tests";
    private final String testSalt = "test-encryption-salt-for-unit-tests";
    
    @BeforeEach
    void setUp() {
        // Set up the encryption secret and salt using reflection
        ReflectionTestUtils.setField(encryptionUtil, "encryptionSecret", testSecret);
        ReflectionTestUtils.setField(encryptionUtil, "encryptionSalt", testSalt);
        
        // Replace the logger with our mock
        ReflectionTestUtils.setField(encryptionUtil, "logger", loggerMock);
    }
    
    @Test
    @DisplayName("Should successfully encrypt and decrypt a string")
    void shouldEncryptAndDecryptString() {
        // Given
        String plaintext = "John Doe";
        
        // When
        String encrypted = encryptionUtil.encrypt(plaintext);
        String decrypted = encryptionUtil.decrypt(encrypted);
        
        // Then
        assertNotNull(encrypted, "Encrypted string should not be null");
        assertNotEquals(plaintext, encrypted, "Encrypted string should be different from plaintext");
        assertEquals(plaintext, decrypted, "Decrypted string should match original plaintext");
        
        // Verify logging
        verify(loggerMock).debug("Successfully encrypted data");
        verify(loggerMock).debug("Successfully decrypted data");
    }
    
    @Test
    @DisplayName("Should encrypt different strings to different ciphertexts")
    void shouldEncryptDifferentStringsToDifferentCiphertexts() {
        // Given
        String plaintext1 = "John Doe";
        String plaintext2 = "Jane Doe";
        
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
        String plaintext = "John Doe";
        
        // When
        String encrypted1 = encryptionUtil.encrypt(plaintext);
        String encrypted2 = encryptionUtil.encrypt(plaintext);
        
        // Then
        assertNotEquals(encrypted1, encrypted2, "Same plaintext should encrypt to different ciphertexts due to random IV");
    }
    
    @ParameterizedTest
    @NullAndEmptySource
    @DisplayName("Should handle null and empty inputs for encryption")
    void shouldHandleNullAndEmptyInputsForEncryption(String input) {
        // When
        String result = encryptionUtil.encrypt(input);
        
        // Then
        assertEquals(input, result, "Null or empty input should return unchanged");
        verify(loggerMock).warn("Attempted to encrypt null or empty string");
    }
    
    @ParameterizedTest
    @NullAndEmptySource
    @DisplayName("Should handle null and empty inputs for decryption")
    void shouldHandleNullAndEmptyInputsForDecryption(String input) {
        // When
        String result = encryptionUtil.decrypt(input);
        
        // Then
        assertEquals(input, result, "Null or empty input should return unchanged");
        verify(loggerMock).warn("Attempted to decrypt null or empty string");
    }
    
    @Test
    @DisplayName("Should handle decryption failure gracefully")
    void shouldHandleDecryptionFailureGracefully() {
        // Given
        String invalidEncryptedText = "invalidBase64EncodedString";
        
        // When
        String result = encryptionUtil.decrypt(invalidEncryptedText);
        
        // Then
        assertNull(result, "Failed decryption should return null");
        verify(loggerMock).error(contains("Decryption failed"), any(Exception.class));
    }
    
    @Test
    @DisplayName("Should handle encryption failure gracefully")
    void shouldHandleEncryptionFailureGracefully() {
        // Given
        // Create a spy to simulate an encryption failure
        doThrow(new RuntimeException("Simulated encryption failure")).when(encryptionUtil).encrypt(anyString());
        
        // When
        String result = encryptionUtil.encrypt("Test");
        
        // Then
        assertNull(result, "Failed encryption should return null");
        verify(loggerMock).error(contains("Encryption failed"), any(Exception.class));
    }
    
    @ParameterizedTest
    @CsvSource({
        "name, true",
        "firstName, true",
        "last_name, true",
        "ssn, true",
        "socialSecurityNumber, true",
        "taxId, true",
        "ein, true",
        "phoneNumber, true",
        "email, true",
        "emailAddress, true",
        "homeAddress, true",
        "billingAddress, true",
        "accountNumber, true",
        "creditCardNumber, true",
        "driversLicense, true",
        "passport, true",
        "dateOfBirth, true",
        "dob, true",
        "birthDate, true",
        "id, false",
        "status, false",
        "createdAt, false",
        "updatedAt, false",
        "amount, false",
        "description, false"
    })
    @DisplayName("Should correctly identify fields requiring encryption")
    void shouldCorrectlyIdentifyFieldsRequiringEncryption(String fieldName, boolean shouldEncrypt) {
        // When
        boolean result = encryptionUtil.requiresEncryption(fieldName);
        
        // Then
        assertEquals(shouldEncrypt, result, 
                String.format("Field '%s' should %s require encryption", fieldName, shouldEncrypt ? "" : "not "));
    }
    
    @ParameterizedTest
    @NullAndEmptySource
    @DisplayName("Should handle null and empty field names for encryption determination")
    void shouldHandleNullAndEmptyFieldNamesForEncryptionDetermination(String fieldName) {
        // When
        boolean result = encryptionUtil.requiresEncryption(fieldName);
        
        // Then
        assertFalse(result, "Null or empty field name should not require encryption");
    }
    
    @Test
    @DisplayName("Should encrypt and decrypt a long text correctly")
    void shouldEncryptAndDecryptLongTextCorrectly() {
        // Given
        String longText = "This is a very long text that contains sensitive information such as names, "
                + "addresses, and other personally identifiable information. It should be encrypted "
                + "and then decrypted back to the original text without any loss of information. "
                + "The encryption should use AES-256 with GCM mode for authenticated encryption.";
        
        // When
        String encrypted = encryptionUtil.encrypt(longText);
        String decrypted = encryptionUtil.decrypt(encrypted);
        
        // Then
        assertNotNull(encrypted, "Encrypted string should not be null");
        assertNotEquals(longText, encrypted, "Encrypted string should be different from plaintext");
        assertEquals(longText, decrypted, "Decrypted string should match original plaintext");
    }
    
    @Test
    @DisplayName("Should encrypt and decrypt special characters correctly")
    void shouldEncryptAndDecryptSpecialCharactersCorrectly() {
        // Given
        String specialChars = "!@#$%^&*()_+-=[]{}|;':,.<>/?`~\\";
        
        // When
        String encrypted = encryptionUtil.encrypt(specialChars);
        String decrypted = encryptionUtil.decrypt(encrypted);
        
        // Then
        assertNotNull(encrypted, "Encrypted string should not be null");
        assertNotEquals(specialChars, encrypted, "Encrypted string should be different from plaintext");
        assertEquals(specialChars, decrypted, "Decrypted string should match original plaintext");
    }
    
    @Test
    @DisplayName("Should encrypt and decrypt Unicode characters correctly")
    void shouldEncryptAndDecryptUnicodeCharactersCorrectly() {
        // Given
        String unicodeChars = "こんにちは世界 • ¥£€$¢ • ❤♠♣♦♥ • 你好世界";
        
        // When
        String encrypted = encryptionUtil.encrypt(unicodeChars);
        String decrypted = encryptionUtil.decrypt(encrypted);
        
        // Then
        assertNotNull(encrypted, "Encrypted string should not be null");
        assertNotEquals(unicodeChars, encrypted, "Encrypted string should be different from plaintext");
        assertEquals(unicodeChars, decrypted, "Decrypted string should match original plaintext");
    }
    
    @Test
    @DisplayName("Should use different encryption keys for different environments")
    void shouldUseDifferentEncryptionKeysForDifferentEnvironments() {
        // Given
        String plaintext = "John Doe";
        String prodSecret = "production-encryption-secret-key";
        String prodSalt = "production-encryption-salt";
        
        // First encrypt with test environment keys
        String encryptedWithTestKeys = encryptionUtil.encrypt(plaintext);
        
        // Then change to production environment keys
        ReflectionTestUtils.setField(encryptionUtil, "encryptionSecret", prodSecret);
        ReflectionTestUtils.setField(encryptionUtil, "encryptionSalt", prodSalt);
        
        // When
        // Try to decrypt with production keys
        String decryptedWithProdKeys = encryptionUtil.decrypt(encryptedWithTestKeys);
        
        // Then
        assertNull(decryptedWithProdKeys, "Decryption with different keys should fail");
        verify(loggerMock, times(1)).error(contains("Decryption failed"), any(Exception.class));
        
        // Reset to test keys for other tests
        ReflectionTestUtils.setField(encryptionUtil, "encryptionSecret", testSecret);
        ReflectionTestUtils.setField(encryptionUtil, "encryptionSalt", testSalt);
    }
}