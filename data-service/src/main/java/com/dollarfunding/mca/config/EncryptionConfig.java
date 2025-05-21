package com.dollarfunding.mca.config;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import javax.persistence.AttributeConverter;
import java.nio.charset.StandardCharsets;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Map;

/**
 * Configuration class for field-level encryption in the MCA application.
 * 
 * This class provides the necessary beans and converters for encrypting sensitive
 * Personally Identifiable Information (PII) stored in the database. It implements
 * AES-256 encryption with GCM mode for authenticated encryption.
 * 
 * Key features:
 * - AES-256 encryption for sensitive data fields
 * - Secure key management with environment-specific keys
 * - Attribute converters for automatic encryption/decryption of entity fields
 * - Support for key rotation
 * - Multi-tenant encryption context support
 * 
 * Usage example in entity classes:
 * 
 * <pre>
 * @Entity
 * @Table(name = "merchant_details")
 * public class MerchantDetails {
 *     // ...
 *     
 *     @Convert(converter = StringEncryptionConverter.class)
 *     @Column(name = "legal_name")
 *     private String legalName;
 *     
 *     @Convert(converter = StringEncryptionConverter.class)
 *     @Column(name = "ein")
 *     private String ein;
 *     
 *     @Convert(converter = JsonEncryptionConverter.class)
 *     @Column(name = "address", columnDefinition = "TEXT")
 *     private Map<String, Object> address;
 *     
 *     // ...
 * }
 * </pre>
 */
@Configuration
public class EncryptionConfig {

    // AES-256 in GCM mode with no padding for authenticated encryption
    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH = 12; // 96 bits as recommended for GCM
    private static final int GCM_TAG_LENGTH = 128; // 128 bits authentication tag
    
    private final Environment environment;
    
    // Primary encryption key, loaded from environment or configuration
    @Value("${encryption.key.primary:#{null}}")
    private String primaryKeyString;
    
    // Secondary encryption key for key rotation, loaded from environment or configuration
    @Value("${encryption.key.secondary:#{null}}")
    private String secondaryKeyString;
    
    // Flag to enable/disable key rotation
    @Value("${encryption.key.rotation.enabled:false}")
    private boolean keyRotationEnabled;
    
    // Tenant ID for multi-tenant scenarios, used as additional authenticated data
    @Value("${encryption.tenant.id:default}")
    private String tenantId;

    public EncryptionConfig(Environment environment) {
        this.environment = environment;
    }
    
    /**
     * Creates a SecretKey for AES-256 encryption.
     * 
     * @return The SecretKey to be used for encryption/decryption
     * @throws NoSuchAlgorithmException if the algorithm is not available
     */
    @Bean(name = "primaryEncryptionKey")
    public SecretKey primaryEncryptionKey() throws NoSuchAlgorithmException {
        if (primaryKeyString != null && !primaryKeyString.isEmpty()) {
            // Use the provided key if available
            byte[] decodedKey = Base64.getDecoder().decode(primaryKeyString);
            return new SecretKeySpec(decodedKey, "AES");
        } else {
            // Generate a new key if none is provided (256-bit AES key)
            KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
            keyGenerator.init(256, new SecureRandom()); // Use 256 bits for AES-256
            SecretKey key = keyGenerator.generateKey();
            
            // Log the generated key for initial setup (should be stored securely)
            // Only in non-production environments to avoid security risks
            if (!environment.matchesProfiles("production")) {
                String encodedKey = Base64.getEncoder().encodeToString(key.getEncoded());
                System.out.println("WARNING: Generated encryption key: " + encodedKey);
                System.out.println("IMPORTANT: Add this key to your application properties as encryption.key.primary");
                System.out.println("SECURITY NOTICE: Store this key securely in a key management system for production use");
            }
            
            return key;
        }
    }
    
    /**
     * Creates a secondary SecretKey for key rotation purposes.
     * 
     * @return The secondary SecretKey or null if key rotation is disabled
     */
    @Bean(name = "secondaryEncryptionKey")
    public SecretKey secondaryEncryptionKey() {
        if (!keyRotationEnabled || secondaryKeyString == null || secondaryKeyString.isEmpty()) {
            return null;
        }
        
        byte[] decodedKey = Base64.getDecoder().decode(secondaryKeyString);
        return new SecretKeySpec(decodedKey, "AES");
    }
    
    /**
     * Creates a cipher for encryption operations.
     * 
     * @return The configured cipher
     * @throws NoSuchPaddingException if the padding scheme is not available
     * @throws NoSuchAlgorithmException if the algorithm is not available
     */
    @Bean(name = "encryptionCipher")
    public Cipher encryptionCipher() throws NoSuchPaddingException, NoSuchAlgorithmException {
        return Cipher.getInstance(ALGORITHM);
    }
    
    /**
     * Provides an encryption service for handling encryption/decryption operations.
     * 
     * @param primaryKey The primary encryption key
     * @param secondaryKey The secondary encryption key (may be null)
     * @param cipher The cipher to use for encryption/decryption
     * @return The encryption service
     */
    @Bean
    public EncryptionService encryptionService(
            @Value("#{primaryEncryptionKey}") SecretKey primaryKey,
            @Value("#{secondaryEncryptionKey}") SecretKey secondaryKey,
            @Value("#{encryptionCipher}") Cipher cipher) {
        return new EncryptionService(primaryKey, secondaryKey, cipher, tenantId);
    }
    
    /**
     * Provides a String attribute converter for JPA entities.
     * 
     * @param encryptionService The encryption service
     * @return The string attribute converter
     */
    @Bean
    public StringEncryptionConverter stringEncryptionConverter(EncryptionService encryptionService) {
        return new StringEncryptionConverter(encryptionService);
    }
    
    /**
     * Provides a JSON attribute converter for JPA entities.
     * 
     * @param encryptionService The encryption service
     * @param objectMapper The Jackson object mapper
     * @return The JSON attribute converter
     */
    @Bean
    public JsonEncryptionConverter jsonEncryptionConverter(EncryptionService encryptionService, ObjectMapper objectMapper) {
        return new JsonEncryptionConverter(encryptionService, objectMapper);
    }
    
    /**
     * Provides an object mapper for JSON serialization/deserialization.
     * 
     * @return The object mapper
     */
    @Bean
    public ObjectMapper objectMapper() {
        return new ObjectMapper();
    }
    
    /**
     * Service class for handling encryption and decryption operations.
     */
    public static class EncryptionService {
        private final SecretKey primaryKey;
        private final SecretKey secondaryKey;
        private final Cipher cipher;
        private final String tenantId;
        private final SecureRandom secureRandom;
        
        public EncryptionService(SecretKey primaryKey, SecretKey secondaryKey, Cipher cipher, String tenantId) {
            this.primaryKey = primaryKey;
            this.secondaryKey = secondaryKey;
            this.cipher = cipher;
            this.tenantId = tenantId;
            this.secureRandom = new SecureRandom();
        }
        
        /**
         * Encrypts the given plaintext using AES-256 GCM.
         * 
         * The encryption process:
         * 1. Generates a random 12-byte IV (nonce)
         * 2. Initializes the cipher with the IV and primary key
         * 3. Adds tenant ID as additional authenticated data (AAD) if applicable
         * 4. Encrypts the plaintext
         * 5. Combines the IV and encrypted data
         * 6. Encodes the result as Base64
         * 
         * @param plaintext The text to encrypt
         * @return The encrypted text in Base64 format
         */
        public String encrypt(String plaintext) {
            if (plaintext == null || plaintext.isEmpty()) {
                return plaintext;
            }
            
            try {
                // Generate a random IV (nonce) for GCM mode
                // Each encryption operation must use a unique IV
                byte[] iv = new byte[GCM_IV_LENGTH];
                secureRandom.nextBytes(iv);
                
                // Initialize cipher for encryption with GCM parameters
                GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
                cipher.init(Cipher.ENCRYPT_MODE, primaryKey, parameterSpec);
                
                // Add tenant ID as associated data if multi-tenant
                // This adds an additional authentication factor without encrypting the tenant ID
                if (tenantId != null && !tenantId.equals("default")) {
                    cipher.updateAAD(tenantId.getBytes(StandardCharsets.UTF_8));
                }
                
                // Encrypt the plaintext
                byte[] encryptedBytes = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
                
                // Combine IV and encrypted data for storage
                // Format: [12 bytes IV][N bytes encrypted data]
                byte[] combined = new byte[iv.length + encryptedBytes.length];
                System.arraycopy(iv, 0, combined, 0, iv.length);
                System.arraycopy(encryptedBytes, 0, combined, iv.length, encryptedBytes.length);
                
                // Encode as Base64 for safe storage in text columns
                return Base64.getEncoder().encodeToString(combined);
            } catch (Exception e) {
                throw new RuntimeException("Error encrypting data", e);
            }
        }
        
        /**
         * Decrypts the given ciphertext using AES-256 GCM.
         * 
         * The decryption process:
         * 1. Decodes the Base64 ciphertext
         * 2. Extracts the IV and encrypted data
         * 3. Attempts decryption with the primary key
         * 4. If that fails and key rotation is enabled, tries with the secondary key
         * 5. Returns the decrypted plaintext or throws an exception if decryption fails
         * 
         * @param ciphertext The Base64-encoded encrypted text
         * @return The decrypted plaintext
         * @throws RuntimeException if decryption fails with all available keys
         */
        public String decrypt(String ciphertext) {
            if (ciphertext == null || ciphertext.isEmpty()) {
                return ciphertext;
            }
            
            try {
                // Decode from Base64
                byte[] combined = Base64.getDecoder().decode(ciphertext);
                
                // Ensure the ciphertext is long enough to contain the IV
                if (combined.length < GCM_IV_LENGTH) {
                    throw new RuntimeException("Invalid ciphertext format");
                }
                
                // Extract IV and encrypted data
                // Format: [12 bytes IV][N bytes encrypted data]
                byte[] iv = new byte[GCM_IV_LENGTH];
                byte[] encryptedBytes = new byte[combined.length - GCM_IV_LENGTH];
                System.arraycopy(combined, 0, iv, 0, iv.length);
                System.arraycopy(combined, iv.length, encryptedBytes, 0, encryptedBytes.length);
                
                // Try with primary key first
                String result = tryDecrypt(encryptedBytes, iv, primaryKey);
                
                // If primary key fails and secondary key is available, try with secondary key
                // This supports key rotation scenarios where data may have been encrypted with an older key
                if (result == null && secondaryKey != null) {
                    result = tryDecrypt(encryptedBytes, iv, secondaryKey);
                }
                
                if (result != null) {
                    return result;
                }
                
                throw new RuntimeException("Failed to decrypt data with available keys");
            } catch (Exception e) {
                throw new RuntimeException("Error decrypting data", e);
            }
        }
        
        /**
         * Attempts to decrypt data with a specific key.
         * 
         * @param encryptedBytes The encrypted data
         * @param iv The initialization vector
         * @param key The key to try
         * @return The decrypted string or null if decryption fails
         */
        private String tryDecrypt(byte[] encryptedBytes, byte[] iv, SecretKey key) {
            try {
                // Initialize cipher for decryption with GCM parameters
                GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
                cipher.init(Cipher.DECRYPT_MODE, key, parameterSpec);
                
                // Add tenant ID as associated data if multi-tenant
                // Must match the AAD used during encryption
                if (tenantId != null && !tenantId.equals("default")) {
                    cipher.updateAAD(tenantId.getBytes(StandardCharsets.UTF_8));
                }
                
                // Decrypt the data
                // This will throw an exception if the authentication tag doesn't match
                // (data tampering) or if the wrong key is used
                byte[] decryptedBytes = cipher.doFinal(encryptedBytes);
                return new String(decryptedBytes, StandardCharsets.UTF_8);
            } catch (InvalidKeyException | InvalidAlgorithmParameterException e) {
                // Key not valid for this ciphertext
                return null;
            } catch (Exception e) {
                // Other decryption error (authentication failure, etc.)
                return null;
            }
        }
    }
    
    /**
     * JPA attribute converter for automatically encrypting/decrypting String fields.
     */
    public static class StringEncryptionConverter implements AttributeConverter<String, String> {
        private final EncryptionService encryptionService;
        
        public StringEncryptionConverter(EncryptionService encryptionService) {
            this.encryptionService = encryptionService;
        }
        
        @Override
        public String convertToDatabaseColumn(String attribute) {
            return encryptionService.encrypt(attribute);
        }
        
        @Override
        public String convertToEntityAttribute(String dbData) {
            return encryptionService.decrypt(dbData);
        }
    }
    
    /**
     * JPA attribute converter for automatically encrypting/decrypting JSON fields.
     */
    public static class JsonEncryptionConverter implements AttributeConverter<Map<String, Object>, String> {
        private final EncryptionService encryptionService;
        private final ObjectMapper objectMapper;
        
        public JsonEncryptionConverter(EncryptionService encryptionService, ObjectMapper objectMapper) {
            this.encryptionService = encryptionService;
            this.objectMapper = objectMapper;
        }
        
        @Override
        public String convertToDatabaseColumn(Map<String, Object> attribute) {
            if (attribute == null) {
                return null;
            }
            
            try {
                String json = objectMapper.writeValueAsString(attribute);
                return encryptionService.encrypt(json);
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Error converting JSON to database column", e);
            }
        }
        
        @Override
        @SuppressWarnings("unchecked")
        public Map<String, Object> convertToEntityAttribute(String dbData) {
            if (dbData == null || dbData.isEmpty()) {
                return null;
            }
            
            try {
                String json = encryptionService.decrypt(dbData);
                return objectMapper.readValue(json, Map.class);
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Error converting database column to JSON", e);
            }
        }
    }
}