package com.dollarfunding.mca.config;

import com.dollarfunding.mca.util.EncryptionUtil;
import com.dollarfunding.mca.converter.EncryptedStringConverter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.env.Environment;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.PropertySource;

import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.security.NoSuchAlgorithmException;
import java.security.spec.InvalidKeySpecException;
import java.security.spec.KeySpec;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import javax.annotation.PostConstruct;
import org.springframework.context.ApplicationContext;

/**
 * Configuration class for field-level encryption in the MCA application.
 * 
 * This class configures AES-256 encryption for sensitive data, particularly
 * Personally Identifiable Information (PII). It sets up encryption keys,
 * algorithms, and converters for encrypting data at rest while still allowing
 * it to be used in business operations.
 * 
 * The encryption configuration supports:
 * - AES-256 encryption with GCM mode for authenticated encryption
 * - Secure key management with environment-based configuration
 * - Key rotation capabilities
 * - Multi-tenant encryption contexts (if needed)
 *
 * This implementation satisfies the security requirements specified in the technical
 * specification, including:
 * - Implementation of AES-256 encryption for sensitive data
 * - Secure PII with field-level encryption
 * - Support for key management and rotation
 */
@Configuration
@PropertySource(value = "classpath:encryption.properties", ignoreResourceNotFound = true)
public class EncryptionConfig {

    // Map of tenant IDs to encryption utilities for multi-tenant scenarios
    private final Map<String, EncryptionUtil> tenantEncryptionUtils = new HashMap<>();
    
    @Value("${encryption.multi-tenant.enabled:false}")
    private boolean multiTenantEnabled;

    private static final Logger logger = LoggerFactory.getLogger(EncryptionConfig.class);
    
    // Key derivation parameters
    private static final String KEY_DERIVATION_ALGORITHM = "PBKDF2WithHmacSHA256";
    private static final int KEY_LENGTH = 256; // Key length in bits
    private static final int ITERATION_COUNT = 65536; // Number of iterations for key derivation
    private static final String ALGORITHM = "AES";
    
    @Value("${encryption.secret:#{environment.ENCRYPTION_SECRET}}")
    private String encryptionSecret;
    
    @Value("${encryption.salt:#{environment.ENCRYPTION_SALT}}")
    private String encryptionSalt;
    
    @Value("${encryption.key-rotation.enabled:false}")
    private boolean keyRotationEnabled;
    
    @Value("${encryption.key-rotation.previous-secret:#{null}}")
    private String previousEncryptionSecret;
    
    @Value("${encryption.key-rotation.previous-salt:#{null}}")
    private String previousEncryptionSalt;
    
    /**
     * Creates the primary EncryptionUtil bean used for encrypting and decrypting sensitive data.
     * 
     * @param environment The Spring environment for accessing configuration properties
     * @return An EncryptionUtil instance configured with the current encryption keys
     */
    @Bean
    @Primary
    public EncryptionUtil encryptionUtil(Environment environment) {
        validateEncryptionConfiguration();
        
        EncryptionUtil encryptionUtil = new EncryptionUtil();
        
        // If environment variables are used, try to get them directly
        String secret = encryptionSecret;
        String salt = encryptionSalt;
        
        if (secret == null || secret.isEmpty()) {
            secret = environment.getProperty("ENCRYPTION_SECRET");
            logger.debug("Using encryption secret from environment variable");
        }
        
        if (salt == null || salt.isEmpty()) {
            salt = environment.getProperty("ENCRYPTION_SALT");
            logger.debug("Using encryption salt from environment variable");
        }
        
        if (secret == null || secret.isEmpty() || salt == null || salt.isEmpty()) {
            throw new IllegalStateException("Encryption secret and salt must be configured either in properties or environment variables");
        }
        
        // Set the encryption properties
        encryptionUtil.setEncryptionSecret(secret);
        encryptionUtil.setEncryptionSalt(salt);
        
        logger.info("Configured primary encryption utility with current encryption keys");
        return encryptionUtil;
    }
    
    /**
     * Creates a secondary EncryptionUtil bean for decrypting data encrypted with previous keys.
     * This bean is only created if key rotation is enabled and previous keys are configured.
     * 
     * Key rotation is an important security practice that allows for periodic updates of
     * encryption keys without losing access to previously encrypted data.
     * 
     * @param environment The Spring environment for accessing configuration properties
     * @return An EncryptionUtil instance configured with the previous encryption keys, or null if not applicable
     */
    @Bean(name = "previousEncryptionUtil")
    public EncryptionUtil previousEncryptionUtil(Environment environment) {
        if (!keyRotationEnabled) {
            logger.info("Key rotation is disabled, not creating previous encryption utility");
            return null;
        }
        
        String prevSecret = previousEncryptionSecret;
        String prevSalt = previousEncryptionSalt;
        
        if (prevSecret == null || prevSecret.isEmpty()) {
            prevSecret = environment.getProperty("ENCRYPTION_PREVIOUS_SECRET");
            logger.debug("Using previous encryption secret from environment variable");
        }
        
        if (prevSalt == null || prevSalt.isEmpty()) {
            prevSalt = environment.getProperty("ENCRYPTION_PREVIOUS_SALT");
            logger.debug("Using previous encryption salt from environment variable");
        }
        
        if (prevSecret == null || prevSecret.isEmpty() || prevSalt == null || prevSalt.isEmpty()) {
            logger.warn("Key rotation is enabled but previous encryption keys are not configured");
            return null;
        }
        
        EncryptionUtil previousEncryptionUtil = new EncryptionUtil();
        previousEncryptionUtil.setEncryptionSecret(prevSecret);
        previousEncryptionUtil.setEncryptionSalt(prevSalt);
        
        logger.info("Configured secondary encryption utility with previous encryption keys");
        return previousEncryptionUtil;
    }
    
    /**
     * Creates a bean for the current encryption key derived from the secret and salt.
     * This key is used for encryption operations.
     * 
     * @return The current encryption key
     */
    @Bean(name = "currentEncryptionKey")
    public Key currentEncryptionKey() {
        try {
            return deriveKey(encryptionSecret, encryptionSalt);
        } catch (Exception e) {
            logger.error("Failed to derive current encryption key", e);
            throw new IllegalStateException("Failed to derive current encryption key", e);
        }
    }
    
    /**
     * Creates a bean for the previous encryption key derived from the previous secret and salt.
     * This key is used for decryption of data encrypted with the previous key during key rotation.
     * 
     * @return The previous encryption key, or null if key rotation is not enabled
     */
    @Bean(name = "previousEncryptionKey")
    public Key previousEncryptionKey() {
        if (!keyRotationEnabled || previousEncryptionSecret == null || previousEncryptionSalt == null) {
            return null;
        }
        
        try {
            return deriveKey(previousEncryptionSecret, previousEncryptionSalt);
        } catch (Exception e) {
            logger.error("Failed to derive previous encryption key", e);
            return null;
        }
    }
    
    /**
     * Validates the encryption configuration to ensure it meets security requirements.
     * Throws an exception if the configuration is invalid.
     * 
     * This method enforces security standards for encryption keys to ensure
     * that the AES-256 encryption provides adequate protection for sensitive data.
     */
    private void validateEncryptionConfiguration() {
        if (encryptionSecret == null || encryptionSecret.isEmpty()) {
            logger.error("Encryption secret is not configured");
            throw new IllegalStateException("Encryption secret must be configured");
        }
        
        if (encryptionSalt == null || encryptionSalt.isEmpty()) {
            logger.error("Encryption salt is not configured");
            throw new IllegalStateException("Encryption salt must be configured");
        }
        
        // Check for minimum security requirements
        if (encryptionSecret.length() < 16) {
            logger.warn("Encryption secret is less than 16 characters, which may compromise security");
        }
        
        // Validate entropy if the secret appears to be Base64 encoded
        if (encryptionSecret.matches("^[A-Za-z0-9+/=]+$") && encryptionSecret.length() >= 44) {
            logger.info("Encryption secret appears to be a strong Base64-encoded key");
        } else if (encryptionSecret.length() < 32) {
            logger.warn("Encryption secret may not have sufficient entropy for AES-256 encryption");
        }
        
        if (keyRotationEnabled) {
            logger.info("Key rotation is enabled");
            if (previousEncryptionSecret == null || previousEncryptionSalt == null) {
                logger.warn("Key rotation is enabled but previous keys are not configured");
            }
        } else {
            logger.info("Key rotation is disabled");
        }
    }
    
    /**
     * Derives an AES key from the provided secret and salt using PBKDF2.
     * 
     * @param secret The secret used for key derivation
     * @param salt The salt used for key derivation
     * @return A SecretKey for AES encryption/decryption
     * @throws NoSuchAlgorithmException If the key derivation algorithm is not available
     * @throws InvalidKeySpecException If the key specification is invalid
     */
    private SecretKey deriveKey(String secret, String salt) throws NoSuchAlgorithmException, InvalidKeySpecException {
        if (secret == null || secret.isEmpty() || salt == null || salt.isEmpty()) {
            throw new IllegalArgumentException("Secret and salt must not be null or empty");
        }
        
        SecretKeyFactory factory = SecretKeyFactory.getInstance(KEY_DERIVATION_ALGORITHM);
        KeySpec spec = new PBEKeySpec(
            secret.toCharArray(),
            salt.getBytes(StandardCharsets.UTF_8),
            ITERATION_COUNT,
            KEY_LENGTH
        );
        
        SecretKey tmp = factory.generateSecret(spec);
        return new SecretKeySpec(tmp.getEncoded(), ALGORITHM);
    }
    
    /**
     * Generates a secure random encryption key that can be used for configuration.
     * This is a utility method that can be used to generate keys for configuration.
     * 
     * @return A Base64-encoded random encryption key
     */
    public static String generateRandomEncryptionKey() {
        byte[] key = new byte[32]; // 256 bits
        java.security.SecureRandom secureRandom = new java.security.SecureRandom();
        secureRandom.nextBytes(key);
        return Base64.getEncoder().encodeToString(key);
    }
    
    /**
     * Generates a secure random salt that can be used for key derivation.
     * 
     * @return A Base64-encoded random salt
     */
    public static String generateRandomSalt() {
        byte[] salt = new byte[16]; // 128 bits
        java.security.SecureRandom secureRandom = new java.security.SecureRandom();
        secureRandom.nextBytes(salt);
        return Base64.getEncoder().encodeToString(salt);
    }
    
    /**
     * Generates a sample encryption.properties file content that can be used as a template.
     * This is a utility method for generating configuration templates.
     * 
     * @return A string containing sample encryption.properties content
     */
    public static String generateSamplePropertiesFile() {
        String encryptionKey = generateRandomEncryptionKey();
        String encryptionSalt = generateRandomSalt();
        String previousKey = generateRandomEncryptionKey();
        String previousSalt = generateRandomSalt();
        
        return "# Encryption Configuration\n" +
               "# IMPORTANT: These values should be stored securely and not committed to version control\n\n" +
               "# Primary encryption keys\n" +
               "encryption.secret=" + encryptionKey + "\n" +
               "encryption.salt=" + encryptionSalt + "\n\n" +
               "# Key rotation configuration\n" +
               "encryption.key-rotation.enabled=false\n" +
               "encryption.key-rotation.previous-secret=" + previousKey + "\n" +
               "encryption.key-rotation.previous-salt=" + previousSalt + "\n\n" +
               "# Multi-tenant encryption configuration\n" +
               "encryption.multi-tenant.enabled=false\n" +
               "# Example tenant-specific keys\n" +
               "# encryption.tenant.tenant1.secret=\n" +
               "# encryption.tenant.tenant1.salt=\n";
    }
    
    /**
     * Creates a JPA attribute converter for automatically encrypting and decrypting
     * sensitive string fields in entity classes.
     * 
     * This converter can be used with the @Convert annotation on entity fields to
     * automatically encrypt and decrypt sensitive data when it is persisted to or
     * retrieved from the database.
     * 
     * @param encryptionUtil The primary encryption utility
     * @return An EncryptedStringConverter instance
     */
    @Bean
    public EncryptedStringConverter encryptedStringConverter(EncryptionUtil encryptionUtil) {
        logger.info("Configuring JPA attribute converter for encrypted string fields");
        return new EncryptedStringConverter(encryptionUtil);
    }
    
    /**
     * Initializes the encryption configuration after all properties have been set.
     * This method is called automatically by Spring after the bean is constructed.
     */
    @PostConstruct
    public void init() {
        logger.info("Initializing encryption configuration");
        validateEncryptionConfiguration();
        
        if (multiTenantEnabled) {
            logger.info("Multi-tenant encryption is enabled");
        }
    }
    
    /**
     * Gets an encryption utility for a specific tenant in a multi-tenant environment.
     * If multi-tenant encryption is not enabled, returns the default encryption utility.
     * 
     * @param tenantId The ID of the tenant
     * @param applicationContext The Spring application context
     * @return An EncryptionUtil instance for the specified tenant
     */
    public EncryptionUtil getEncryptionUtilForTenant(String tenantId, ApplicationContext applicationContext) {
        if (!multiTenantEnabled || tenantId == null || tenantId.isEmpty()) {
            return applicationContext.getBean(EncryptionUtil.class);
        }
        
        return tenantEncryptionUtils.computeIfAbsent(tenantId, id -> {
            logger.info("Creating encryption utility for tenant: {}", id);
            EncryptionUtil util = new EncryptionUtil();
            // Configure tenant-specific encryption keys if available
            String tenantSecret = applicationContext.getEnvironment().getProperty("encryption.tenant." + id + ".secret");
            String tenantSalt = applicationContext.getEnvironment().getProperty("encryption.tenant." + id + ".salt");
            
            if (tenantSecret != null && !tenantSecret.isEmpty() && tenantSalt != null && !tenantSalt.isEmpty()) {
                util.setEncryptionSecret(tenantSecret);
                util.setEncryptionSalt(tenantSalt);
            } else {
                // Fall back to default encryption keys
                EncryptionUtil defaultUtil = applicationContext.getBean(EncryptionUtil.class);
                util.setEncryptionSecret(defaultUtil.getEncryptionSecret());
                util.setEncryptionSalt(defaultUtil.getEncryptionSalt());
            }
            
            return util;
        });
    }
}