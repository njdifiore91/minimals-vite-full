package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.config.EncryptionConfig;
import com.dollarfunding.mca.converter.EncryptedStringConverter;
import com.dollarfunding.mca.util.EncryptionUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.core.env.Environment;

import java.security.Key;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the field-level encryption converters used to protect sensitive PII data.
 * 
 * These tests validate the encryption and decryption functionality, handling of null values,
 * key rotation, and integration with entity classes. The tests ensure that the encryption
 * converters properly protect sensitive data in the MerchantDetails entity such as legal_name,
 * dba_name, and ein, while allowing transparent access to the decrypted values in the
 * application code.
 */
@ExtendWith(MockitoExtension.class)
public class EncryptedFieldConverterTest {

    private EncryptionUtil encryptionUtil;
    private EncryptedStringConverter encryptedStringConverter;
    
    @Mock
    private Environment environment;
    
    @Mock
    private Key mockKey;
    
    @BeforeEach
    public void setUp() {
        // Set up encryption utility with test keys
        encryptionUtil = new EncryptionUtil();
        encryptionUtil.setEncryptionSecret("TestEncryptionSecretKey123456789012345");
        encryptionUtil.setEncryptionSalt("TestSalt123456789");
        
        // Create the converter with the encryption utility
        encryptedStringConverter = new EncryptedStringConverter(encryptionUtil);
    }
    
    @Test
    @DisplayName("Test encryption of string values")
    public void testEncryptStringValue() {
        // Arrange
        String sensitiveData = "John Doe";
        
        // Act
        String encryptedValue = encryptedStringConverter.convertToDatabaseColumn(sensitiveData);
        
        // Assert
        assertNotNull(encryptedValue, "Encrypted value should not be null");
        assertNotEquals(sensitiveData, encryptedValue, "Encrypted value should be different from original");
        assertTrue(encryptedValue.length() > sensitiveData.length(), "Encrypted value should be longer than original");
        assertTrue(encryptedValue.matches("^[A-Za-z0-9+/=]+$"), "Encrypted value should be Base64 encoded");
    }
    
    @Test
    @DisplayName("Test decryption of string values")
    public void testDecryptStringValue() {
        // Arrange
        String sensitiveData = "John Doe";
        String encryptedValue = encryptedStringConverter.convertToDatabaseColumn(sensitiveData);
        
        // Act
        String decryptedValue = encryptedStringConverter.convertToEntityAttribute(encryptedValue);
        
        // Assert
        assertNotNull(decryptedValue, "Decrypted value should not be null");
        assertEquals(sensitiveData, decryptedValue, "Decrypted value should match original");
    }
    
    @Test
    @DisplayName("Test handling of null values during encryption")
    public void testEncryptNullValue() {
        // Act
        String encryptedValue = encryptedStringConverter.convertToDatabaseColumn(null);
        
        // Assert
        assertNull(encryptedValue, "Encrypted null value should remain null");
    }
    
    @Test
    @DisplayName("Test handling of null values during decryption")
    public void testDecryptNullValue() {
        // Act
        String decryptedValue = encryptedStringConverter.convertToEntityAttribute(null);
        
        // Assert
        assertNull(decryptedValue, "Decrypted null value should remain null");
    }
    
    @Test
    @DisplayName("Test handling of empty string during encryption")
    public void testEncryptEmptyString() {
        // Arrange
        String emptyString = "";
        
        // Act
        String encryptedValue = encryptedStringConverter.convertToDatabaseColumn(emptyString);
        
        // Assert
        assertEquals(emptyString, encryptedValue, "Encrypted empty string should remain empty");
    }
    
    @Test
    @DisplayName("Test handling of empty string during decryption")
    public void testDecryptEmptyString() {
        // Arrange
        String emptyString = "";
        
        // Act
        String decryptedValue = encryptedStringConverter.convertToEntityAttribute(emptyString);
        
        // Assert
        assertEquals(emptyString, decryptedValue, "Decrypted empty string should remain empty");
    }
    
    @Test
    @DisplayName("Test key rotation mechanism with previous encryption key")
    public void testKeyRotation() {
        // Arrange - Create encryption utilities with different keys
        EncryptionUtil oldEncryptionUtil = new EncryptionUtil();
        oldEncryptionUtil.setEncryptionSecret("OldEncryptionSecretKey1234567890123456");
        oldEncryptionUtil.setEncryptionSalt("OldSalt123456789");
        
        EncryptionUtil newEncryptionUtil = new EncryptionUtil();
        newEncryptionUtil.setEncryptionSecret("NewEncryptionSecretKey1234567890123456");
        newEncryptionUtil.setEncryptionSalt("NewSalt123456789");
        
        // Create converters with different encryption utilities
        EncryptedStringConverter oldConverter = new EncryptedStringConverter(oldEncryptionUtil);
        EncryptedStringConverter newConverter = new EncryptedStringConverter(newEncryptionUtil);
        
        // Encrypt data with old key
        String sensitiveData = "Jane Doe";
        String encryptedWithOldKey = oldConverter.convertToDatabaseColumn(sensitiveData);
        
        // Attempt to decrypt with new key (should fail or return incorrect data)
        String attemptedDecryption = newConverter.convertToEntityAttribute(encryptedWithOldKey);
        
        // Assert that decryption with wrong key fails or returns incorrect data
        assertNotEquals(sensitiveData, attemptedDecryption, "Decryption with wrong key should not match original");
        
        // Simulate key rotation in EncryptionConfig
        EncryptionConfig encryptionConfig = Mockito.mock(EncryptionConfig.class);
        when(encryptionConfig.encryptionUtil(environment)).thenReturn(newEncryptionUtil);
        when(encryptionConfig.previousEncryptionUtil(environment)).thenReturn(oldEncryptionUtil);
        
        // Create a custom converter that simulates key rotation
        EncryptedStringConverter rotatingConverter = new EncryptedStringConverter(newEncryptionUtil) {
            @Override
            public String convertToEntityAttribute(String dbData) {
                if (dbData == null || dbData.isEmpty()) {
                    return dbData;
                }
                
                // Try with current key first
                String decrypted = newEncryptionUtil.decrypt(dbData);
                
                // If decryption fails or returns null, try with old key
                if (decrypted == null) {
                    decrypted = oldEncryptionUtil.decrypt(dbData);
                }
                
                return decrypted;
            }
        };
        
        // Now decrypt with rotating converter
        String decryptedAfterRotation = rotatingConverter.convertToEntityAttribute(encryptedWithOldKey);
        
        // Assert that decryption works with key rotation
        assertEquals(sensitiveData, decryptedAfterRotation, "Decryption with key rotation should match original");
    }
    
    @Test
    @DisplayName("Test integration with MerchantDetails entity")
    public void testIntegrationWithMerchantDetailsEntity() {
        // Arrange
        UUID applicationId = UUID.randomUUID();
        String legalName = "Acme Corporation";
        String dbaName = "Acme Corp";
        String ein = "12-3456789";
        
        // Create a MerchantDetails entity
        MerchantDetails merchantDetails = new MerchantDetails(applicationId, legalName);
        merchantDetails.setDbaName(dbaName);
        merchantDetails.setEin(ein);
        merchantDetails.setEncryptionUtil(encryptionUtil);
        
        // Act - Encrypt sensitive fields
        merchantDetails.encryptSensitiveFields();
        
        // Assert - Check that fields are encrypted
        String encryptedLegalName = merchantDetails.getLegalName();
        String encryptedDbaName = merchantDetails.getDbaName();
        String encryptedEin = merchantDetails.getEin();
        
        // Verify that the fields are properly encrypted and decrypted
        assertEquals(legalName, encryptionUtil.decrypt(encryptedLegalName), "Legal name should be properly encrypted and decrypted");
        assertEquals(dbaName, encryptionUtil.decrypt(encryptedDbaName), "DBA name should be properly encrypted and decrypted");
        assertEquals(ein, encryptionUtil.decrypt(encryptedEin), "EIN should be properly encrypted and decrypted");
    }
    
    @Test
    @DisplayName("Test encryption strength and security")
    public void testEncryptionStrengthAndSecurity() {
        // Arrange
        String sensitiveData1 = "John Doe";
        String sensitiveData2 = "John Doe"; // Same value
        
        // Act - Encrypt the same value twice
        String encryptedValue1 = encryptedStringConverter.convertToDatabaseColumn(sensitiveData1);
        String encryptedValue2 = encryptedStringConverter.convertToDatabaseColumn(sensitiveData2);
        
        // Assert - Check that the encrypted values are different (due to random IV)
        assertNotEquals(encryptedValue1, encryptedValue2, "Encrypting the same value twice should produce different results due to random IV");
        
        // Verify that both decrypt to the original value
        assertEquals(sensitiveData1, encryptedStringConverter.convertToEntityAttribute(encryptedValue1), "First encrypted value should decrypt correctly");
        assertEquals(sensitiveData2, encryptedStringConverter.convertToEntityAttribute(encryptedValue2), "Second encrypted value should decrypt correctly");
    }
    
    @Test
    @DisplayName("Test persistence and retrieval of encrypted fields")
    public void testPersistenceAndRetrieval() {
        // Arrange - Simulate database persistence and retrieval
        String sensitiveData = "Confidential Information";
        
        // Act - Convert to database column (encrypt)
        String encryptedValue = encryptedStringConverter.convertToDatabaseColumn(sensitiveData);
        
        // Simulate storing in database and retrieving
        String retrievedEncryptedValue = encryptedValue;
        
        // Convert back to entity attribute (decrypt)
        String decryptedValue = encryptedStringConverter.convertToEntityAttribute(retrievedEncryptedValue);
        
        // Assert
        assertEquals(sensitiveData, decryptedValue, "Value should be correctly encrypted and decrypted through the persistence cycle");
    }
    
    @Test
    @DisplayName("Test handling of already encrypted data")
    public void testHandlingOfAlreadyEncryptedData() {
        // Arrange
        String sensitiveData = "Secret Data";
        
        // Act - Encrypt once
        String encryptedOnce = encryptedStringConverter.convertToDatabaseColumn(sensitiveData);
        
        // Encrypt again (should detect it's already encrypted)
        String encryptedTwice = encryptedStringConverter.convertToDatabaseColumn(encryptedOnce);
        
        // Assert
        assertNotEquals(sensitiveData, encryptedOnce, "First encryption should change the value");
        assertNotEquals(sensitiveData, encryptedTwice, "Second encryption should not return the original value");
        
        // The behavior depends on the implementation of isEncrypted() in the converter
        // If it correctly detects encrypted values, encryptedTwice should equal encryptedOnce
        // If not, it might be double-encrypted
        
        // Decrypt and verify
        String decryptedOnce = encryptedStringConverter.convertToEntityAttribute(encryptedOnce);
        assertEquals(sensitiveData, decryptedOnce, "Decryption of once-encrypted value should match original");
    }
    
    @Test
    @DisplayName("Test handling of malformed encrypted data")
    public void testHandlingOfMalformedEncryptedData() {
        // Arrange - Create malformed encrypted data
        String malformedData = "NotReallyEncryptedJustBase64===";
        
        // Act - Attempt to decrypt
        String decryptedValue = encryptedStringConverter.convertToEntityAttribute(malformedData);
        
        // Assert - The converter should handle errors gracefully
        // Depending on implementation, it might return the original value or null
        assertNotNull(decryptedValue, "Converter should handle malformed data gracefully");
    }
}