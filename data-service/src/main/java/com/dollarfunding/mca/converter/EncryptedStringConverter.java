package com.dollarfunding.mca.converter;

import com.dollarfunding.mca.util.EncryptionUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;

import javax.persistence.AttributeConverter;
import javax.persistence.Converter;

/**
 * JPA attribute converter for automatically encrypting and decrypting sensitive string fields.
 * 
 * This converter implements the JPA AttributeConverter interface to provide transparent
 * field-level encryption for entity attributes. When an entity with this converter is
 * persisted, the converter automatically encrypts the field value before storing it in
 * the database. When the entity is loaded, the converter automatically decrypts the
 * field value.
 * 
 * Usage example in an entity class:
 * 
 * ```java
 * @Convert(converter = EncryptedStringConverter.class)
 * @Column(name = "sensitive_data")
 * private String sensitiveData;
 * ```
 */
@Converter
public class EncryptedStringConverter implements AttributeConverter<String, String> {

    private static final Logger logger = LoggerFactory.getLogger(EncryptedStringConverter.class);
    
    private final EncryptionUtil encryptionUtil;
    
    /**
     * Constructor with required EncryptionUtil dependency.
     * 
     * @param encryptionUtil The encryption utility to use for encryption/decryption
     */
    @Autowired
    public EncryptedStringConverter(EncryptionUtil encryptionUtil) {
        this.encryptionUtil = encryptionUtil;
    }
    
    /**
     * Converts the entity attribute value to the database column value.
     * This method encrypts the string value before it is stored in the database.
     * 
     * @param attribute The entity attribute value to be converted
     * @return The encrypted string to be stored in the database
     */
    @Override
    public String convertToDatabaseColumn(String attribute) {
        if (attribute == null || attribute.isEmpty()) {
            return attribute;
        }
        
        try {
            String encryptedValue = encryptionUtil.encrypt(attribute);
            logger.debug("Successfully encrypted sensitive data for database storage");
            return encryptedValue;
        } catch (Exception e) {
            logger.error("Failed to encrypt sensitive data", e);
            // In case of encryption failure, we return the original value to prevent data loss
            // This is a trade-off between data availability and security
            return attribute;
        }
    }
    
    /**
     * Converts the database column value to the entity attribute value.
     * This method decrypts the string value after it is loaded from the database.
     * 
     * @param dbData The database column value to be converted
     * @return The decrypted string to be stored in the entity attribute
     */
    @Override
    public String convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.isEmpty()) {
            return dbData;
        }
        
        try {
            // Check if the data is already encrypted
            if (isEncrypted(dbData)) {
                String decryptedValue = encryptionUtil.decrypt(dbData);
                logger.debug("Successfully decrypted sensitive data from database");
                return decryptedValue;
            } else {
                logger.warn("Found unencrypted sensitive data in database");
                return dbData;
            }
        } catch (Exception e) {
            logger.error("Failed to decrypt sensitive data", e);
            // In case of decryption failure, we return the encrypted value
            // This allows the application to continue functioning, but the data will be unusable
            return dbData;
        }
    }
    
    /**
     * Checks if a string is already encrypted.
     * This is a simple heuristic and may need to be improved.
     * 
     * @param value The string to check
     * @return true if the string appears to be encrypted
     */
    private boolean isEncrypted(String value) {
        // A simple heuristic: encrypted values are Base64 encoded and typically longer
        return value != null && value.length() > 20 && value.matches("^[A-Za-z0-9+/=]+$");
    }
}