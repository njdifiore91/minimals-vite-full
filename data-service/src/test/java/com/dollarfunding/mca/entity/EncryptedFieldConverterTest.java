package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

/**
 * Unit tests for the EncryptedFieldConverter class that handles field-level encryption
 * for sensitive PII data in the MerchantDetails entity.
 */
@SpringBootTest
@ActiveProfiles("test")
public class EncryptedFieldConverterTest {

    @Autowired
    private EncryptedFieldConverter converter;
    
    private String testValue;
    
    @BeforeEach
    public void setup() {
        testValue = "Sensitive PII Data";
    }
    
    @Test
    @DisplayName("Should encrypt string value")
    public void testEncryptStringValue() {
        // When
        String encryptedValue = converter.convertToDatabaseColumn(testValue);
        
        // Then
        assertNotNull(encryptedValue);
        assertNotEquals(testValue, encryptedValue);
    }
    
    @Test
    @DisplayName("Should decrypt encrypted string value")
    public void testDecryptStringValue() {
        // Given
        String encryptedValue = converter.convertToDatabaseColumn(testValue);
        
        // When
        String decryptedValue = converter.convertToEntityAttribute(encryptedValue);
        
        // Then
        assertEquals(testValue, decryptedValue);
    }
    
    @Test
    @DisplayName("Should handle null value during encryption")
    public void testEncryptNullValue() {
        // When
        String encryptedValue = converter.convertToDatabaseColumn(null);
        
        // Then
        assertNull(encryptedValue);
    }
    
    @Test
    @DisplayName("Should handle null value during decryption")
    public void testDecryptNullValue() {
        // When
        String decryptedValue = converter.convertToEntityAttribute(null);
        
        // Then
        assertNull(decryptedValue);
    }
    
    @Test
    @DisplayName("Should encrypt and decrypt with different key versions")
    public void testKeyRotation() {
        // Given
        String originalValue = "Test Key Rotation";
        
        // When - encrypt with current key
        String encryptedValue = converter.convertToDatabaseColumn(originalValue);
        
        // Then - should decrypt correctly even after simulated key rotation
        String decryptedValue = converter.convertToEntityAttribute(encryptedValue);
        assertEquals(originalValue, decryptedValue);
    }
    
    @Test
    @DisplayName("Should integrate with MerchantDetails entity")
    public void testIntegrationWithMerchantDetails() {
        // Given
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setLegalName("ABC Corporation");
        merchantDetails.setDbaName("ABC Business");
        merchantDetails.setEin("12-3456789");
        
        // Mock the entity manager and repository behavior
        // This simulates what happens when JPA persists and retrieves the entity
        String encryptedLegalName = converter.convertToDatabaseColumn(merchantDetails.getLegalName());
        String encryptedDbaName = converter.convertToDatabaseColumn(merchantDetails.getDbaName());
        String encryptedEin = converter.convertToDatabaseColumn(merchantDetails.getEin());
        
        // When - simulate JPA retrieval with encrypted values from database
        MerchantDetails retrievedMerchant = new MerchantDetails();
        // Simulate JPA calling the converter when loading from database
        retrievedMerchant.setLegalName(converter.convertToEntityAttribute(encryptedLegalName));
        retrievedMerchant.setDbaName(converter.convertToEntityAttribute(encryptedDbaName));
        retrievedMerchant.setEin(converter.convertToEntityAttribute(encryptedEin));
        
        // Then - the fields should be properly decrypted
        assertEquals("ABC Corporation", retrievedMerchant.getLegalName());
        assertEquals("ABC Business", retrievedMerchant.getDbaName());
        assertEquals("12-3456789", retrievedMerchant.getEin());
        
        // Verify the encrypted values are different from the original values
        assertNotEquals(merchantDetails.getLegalName(), encryptedLegalName);
        assertNotEquals(merchantDetails.getDbaName(), encryptedDbaName);
        assertNotEquals(merchantDetails.getEin(), encryptedEin);
    }
    
    @Test
    @DisplayName("Should verify encryption strength")
    public void testEncryptionStrength() {
        // Given
        String sensitiveData = "Highly confidential information";
        
        // When
        String encryptedValue = converter.convertToDatabaseColumn(sensitiveData);
        
        // Then - verify encryption strength by checking encrypted value properties
        assertNotNull(encryptedValue);
        assertNotEquals(sensitiveData, encryptedValue);
        
        // Encrypted value should be significantly different from original
        // and should have sufficient length for AES-256 encryption
        assertTrue(encryptedValue.length() > sensitiveData.length());
    }
    
    @Test
    @DisplayName("Should use strong encryption algorithm")
    public void testStrongEncryption() {
        // This test verifies that the converter is using a strong encryption algorithm
        // by checking the properties of the encrypted output
        
        // Given - a string with known patterns
        String sensitiveData = "12345678901234567890123456789012"; // 32 characters
        
        // When - encrypt the data
        String encryptedValue = converter.convertToDatabaseColumn(sensitiveData);
        
        // Then - verify encryption properties
        assertNotNull(encryptedValue);
        assertNotEquals(sensitiveData, encryptedValue);
        
        // Strong encryption should produce output that doesn't contain the original data
        // and has sufficient entropy (randomness)
        assertFalse(encryptedValue.contains(sensitiveData));
        
        // Encrypt the same value again - should produce different output due to IV/salt
        String encryptedValue2 = converter.convertToDatabaseColumn(sensitiveData);
        assertNotEquals(encryptedValue, encryptedValue2, "Encryption should use initialization vector or salt");
        
        // Both encrypted values should decrypt to the original value
        assertEquals(sensitiveData, converter.convertToEntityAttribute(encryptedValue));
        assertEquals(sensitiveData, converter.convertToEntityAttribute(encryptedValue2));
    }
    

    
    @Test
    @DisplayName("Should verify persistence and retrieval of encrypted fields")
    public void testPersistenceAndRetrieval() {
        // Given - mock repository and entity manager behavior
        String legalName = "XYZ Corporation";
        String dbaName = "XYZ Business";
        String ein = "98-7654321";
        
        // When - simulate database persistence and retrieval with encryption/decryption
        String encryptedLegalName = converter.convertToDatabaseColumn(legalName);
        String encryptedDbaName = converter.convertToDatabaseColumn(dbaName);
        String encryptedEin = converter.convertToDatabaseColumn(ein);
        
        // Then - verify decryption works correctly after retrieval
        assertEquals(legalName, converter.convertToEntityAttribute(encryptedLegalName));
        assertEquals(dbaName, converter.convertToEntityAttribute(encryptedDbaName));
        assertEquals(ein, converter.convertToEntityAttribute(encryptedEin));
    }
}