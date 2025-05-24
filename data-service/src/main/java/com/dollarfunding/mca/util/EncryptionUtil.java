package com.dollarfunding.mca.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.security.spec.KeySpec;
import java.util.Base64;

/**
 * Utility class for field-level encryption and decryption of Personally Identifiable Information (PII)
 * in the MCA application. Implements AES-256 encryption with GCM mode for authenticated encryption.
 * 
 * This class provides methods to encrypt and decrypt sensitive data such as names, contact information,
 * identification numbers, and financial details.
 */
@Component
public class EncryptionUtil {

    private static final Logger logger = LoggerFactory.getLogger(EncryptionUtil.class);
    
    // AES-GCM parameters
    private static final String ALGORITHM = "AES";
    private static final String CIPHER_TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int GCM_TAG_LENGTH = 128; // Authentication tag length in bits
    private static final int GCM_IV_LENGTH = 12; // Initialization Vector length in bytes
    
    // Key derivation parameters
    private static final String KEY_DERIVATION_ALGORITHM = "PBKDF2WithHmacSHA256";
    private static final int KEY_LENGTH = 256; // Key length in bits
    private static final int ITERATION_COUNT = 65536; // Number of iterations for key derivation
    
    private String encryptionSecret;
    
    private String encryptionSalt;
    
    /**
     * Sets the encryption secret used for key derivation.
     * 
     * @param encryptionSecret The encryption secret
     */
    public void setEncryptionSecret(String encryptionSecret) {
        this.encryptionSecret = encryptionSecret;
    }
    
    /**
     * Sets the encryption salt used for key derivation.
     * 
     * @param encryptionSalt The encryption salt
     */
    public void setEncryptionSalt(String encryptionSalt) {
        this.encryptionSalt = encryptionSalt;
    }
    
    /**
     * Gets the encryption secret.
     * This method is used by the EncryptionConfig class for key rotation.
     * 
     * @return The encryption secret
     */
    public String getEncryptionSecret() {
        return encryptionSecret;
    }
    
    /**
     * Gets the encryption salt.
     * This method is used by the EncryptionConfig class for key rotation.
     * 
     * @return The encryption salt
     */
    public String getEncryptionSalt() {
        return encryptionSalt;
    }

    /**
     * Encrypts a string using AES-256 encryption with GCM mode.
     * 
     * @param plaintext The string to encrypt
     * @return Base64-encoded encrypted string with IV prepended, or null if encryption fails
     */
    public String encrypt(String plaintext) {
        if (plaintext == null || plaintext.isEmpty()) {
            logger.warn("Attempted to encrypt null or empty string");
            return plaintext;
        }
        
        try {
            // Generate a random IV for this encryption
            byte[] iv = generateRandomIV();
            
            // Derive the secret key
            SecretKey secretKey = deriveKey(encryptionSecret, encryptionSalt);
            
            // Initialize cipher for encryption
            Cipher cipher = Cipher.getInstance(CIPHER_TRANSFORMATION);
            GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, parameterSpec);
            
            // Encrypt the plaintext
            byte[] plaintextBytes = plaintext.getBytes(StandardCharsets.UTF_8);
            byte[] ciphertext = cipher.doFinal(plaintextBytes);
            
            // Combine IV and ciphertext and encode as Base64
            ByteBuffer byteBuffer = ByteBuffer.allocate(iv.length + ciphertext.length);
            byteBuffer.put(iv);
            byteBuffer.put(ciphertext);
            byte[] cipherMessage = byteBuffer.array();
            
            String encryptedText = Base64.getEncoder().encodeToString(cipherMessage);
            logger.debug("Successfully encrypted data");
            
            return encryptedText;
        } catch (Exception e) {
            logger.error("Encryption failed", e);
            return null;
        }
    }

    /**
     * Decrypts a previously encrypted string.
     * 
     * @param encryptedText Base64-encoded encrypted string with IV prepended
     * @return The decrypted plaintext, or null if decryption fails
     */
    public String decrypt(String encryptedText) {
        if (encryptedText == null || encryptedText.isEmpty()) {
            logger.warn("Attempted to decrypt null or empty string");
            return encryptedText;
        }
        
        try {
            // Decode the Base64 string
            byte[] cipherMessage = Base64.getDecoder().decode(encryptedText);
            
            // Extract the IV and ciphertext
            ByteBuffer byteBuffer = ByteBuffer.wrap(cipherMessage);
            byte[] iv = new byte[GCM_IV_LENGTH];
            byteBuffer.get(iv);
            
            byte[] ciphertext = new byte[byteBuffer.remaining()];
            byteBuffer.get(ciphertext);
            
            // Derive the secret key
            SecretKey secretKey = deriveKey(encryptionSecret, encryptionSalt);
            
            // Initialize cipher for decryption
            Cipher cipher = Cipher.getInstance(CIPHER_TRANSFORMATION);
            GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, parameterSpec);
            
            // Decrypt the ciphertext
            byte[] plaintextBytes = cipher.doFinal(ciphertext);
            String plaintext = new String(plaintextBytes, StandardCharsets.UTF_8);
            
            logger.debug("Successfully decrypted data");
            return plaintext;
        } catch (Exception e) {
            logger.error("Decryption failed", e);
            return null;
        }
    }
    
    /**
     * Determines if a field requires encryption based on its name or content.
     * This method can be extended to check annotations or other criteria.
     * 
     * @param fieldName The name of the field to check
     * @return true if the field should be encrypted, false otherwise
     */
    public boolean requiresEncryption(String fieldName) {
        if (fieldName == null || fieldName.isEmpty()) {
            return false;
        }
        
        // List of field names that contain PII and require encryption
        return fieldName.toLowerCase().contains("name") ||
               fieldName.toLowerCase().contains("ssn") ||
               fieldName.toLowerCase().contains("social") ||
               fieldName.toLowerCase().contains("tax") ||
               fieldName.toLowerCase().contains("ein") ||
               fieldName.toLowerCase().contains("phone") ||
               fieldName.toLowerCase().contains("email") ||
               fieldName.toLowerCase().contains("address") ||
               fieldName.toLowerCase().contains("account") ||
               fieldName.toLowerCase().contains("card") ||
               fieldName.toLowerCase().contains("license") ||
               fieldName.toLowerCase().contains("passport") ||
               fieldName.toLowerCase().contains("dob") ||
               fieldName.toLowerCase().contains("birth");
    }

    /**
     * Generates a random initialization vector (IV) for AES-GCM encryption.
     * 
     * @return A random IV of the specified length
     */
    private byte[] generateRandomIV() {
        byte[] iv = new byte[GCM_IV_LENGTH];
        new SecureRandom().nextBytes(iv);
        return iv;
    }
    
    /**
     * Derives an AES key from the provided secret and salt using PBKDF2.
     * 
     * @param secret The secret used for key derivation
     * @param salt The salt used for key derivation
     * @return A SecretKey for AES encryption/decryption
     * @throws Exception If key derivation fails
     */
    private SecretKey deriveKey(String secret, String salt) throws Exception {
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
}