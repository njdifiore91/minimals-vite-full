package com.dollarfunding.mca.config;

import com.dollarfunding.mca.converter.EncryptedStringConverter;
import com.dollarfunding.mca.util.EncryptionUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationContext;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import javax.crypto.SecretKey;
import java.lang.reflect.Method;
import java.security.Key;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link EncryptionConfig} class.
 * 
 * These tests verify that the encryption configuration correctly implements
 * AES-256 encryption for sensitive data, properly manages encryption keys,
 * configures attribute converters, and handles multi-tenant scenarios.
 */
@ExtendWith(MockitoExtension.class)
public class EncryptionConfigTest {

    @Mock
    private Environment environment;
    
    @Mock
    private ApplicationContext applicationContext;
    
    private EncryptionConfig encryptionConfig;
    
    private static final String TEST_SECRET = "testEncryptionSecretWithAtLeast32Chars";
    private static final String TEST_SALT = "testEncryptionSalt";
    private static final String TEST_PREVIOUS_SECRET = "testPreviousEncryptionSecretWithAtLeast32Chars";
    private static final String TEST_PREVIOUS_SALT = "testPreviousEncryptionSalt";
    private static final String TEST_TENANT_ID = "tenant1";
    private static final String TEST_TENANT_SECRET = "testTenantEncryptionSecretWithAtLeast32Chars";
    private static final String TEST_TENANT_SALT = "testTenantEncryptionSalt";
    
    @BeforeEach
    public void setUp() {
        encryptionConfig = new EncryptionConfig();
        
        // Set required properties using reflection
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSecret", TEST_SECRET);
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSalt", TEST_SALT);
        ReflectionTestUtils.setField(encryptionConfig, "keyRotationEnabled", false);
        ReflectionTestUtils.setField(encryptionConfig, "multiTenantEnabled", false);
    }
    
    /**
     * Tests that the encryption configuration correctly creates an EncryptionUtil bean
     * with the configured encryption secret and salt.
     */
    @Test
    public void testEncryptionUtilCreation() {
        // When
        EncryptionUtil encryptionUtil = encryptionConfig.encryptionUtil(environment);
        
        // Then
        assertNotNull(encryptionUtil, "EncryptionUtil should not be null");
        assertEquals(TEST_SECRET, encryptionUtil.getEncryptionSecret(), "Encryption secret should match");
        assertEquals(TEST_SALT, encryptionUtil.getEncryptionSalt(), "Encryption salt should match");
    }
    
    /**
     * Tests that the encryption configuration correctly falls back to environment variables
     * when properties are not set.
     */
    @Test
    public void testEncryptionUtilWithEnvironmentVariables() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSecret", null);
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSalt", null);
        when(environment.getProperty("ENCRYPTION_SECRET")).thenReturn(TEST_SECRET);
        when(environment.getProperty("ENCRYPTION_SALT")).thenReturn(TEST_SALT);
        
        // When
        EncryptionUtil encryptionUtil = encryptionConfig.encryptionUtil(environment);
        
        // Then
        assertNotNull(encryptionUtil, "EncryptionUtil should not be null");
        assertEquals(TEST_SECRET, encryptionUtil.getEncryptionSecret(), "Encryption secret should match");
        assertEquals(TEST_SALT, encryptionUtil.getEncryptionSalt(), "Encryption salt should match");
    }
    
    /**
     * Tests that the encryption configuration throws an exception when encryption
     * secret and salt are not configured.
     */
    @Test
    public void testEncryptionUtilWithMissingConfiguration() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSecret", null);
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSalt", null);
        when(environment.getProperty("ENCRYPTION_SECRET")).thenReturn(null);
        when(environment.getProperty("ENCRYPTION_SALT")).thenReturn(null);
        
        // Then
        Exception exception = assertThrows(IllegalStateException.class, () -> {
            encryptionConfig.encryptionUtil(environment);
        }, "Should throw IllegalStateException when encryption keys are not configured");
        
        assertTrue(exception.getMessage().contains("Encryption secret and salt must be configured"),
                "Exception message should indicate missing configuration");
    }
    
    /**
     * Tests that the encryption configuration correctly creates a previous EncryptionUtil bean
     * when key rotation is enabled.
     */
    @Test
    public void testPreviousEncryptionUtilWithKeyRotation() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "keyRotationEnabled", true);
        ReflectionTestUtils.setField(encryptionConfig, "previousEncryptionSecret", TEST_PREVIOUS_SECRET);
        ReflectionTestUtils.setField(encryptionConfig, "previousEncryptionSalt", TEST_PREVIOUS_SALT);
        
        // When
        EncryptionUtil previousEncryptionUtil = encryptionConfig.previousEncryptionUtil(environment);
        
        // Then
        assertNotNull(previousEncryptionUtil, "Previous EncryptionUtil should not be null when key rotation is enabled");
        assertEquals(TEST_PREVIOUS_SECRET, previousEncryptionUtil.getEncryptionSecret(), "Previous encryption secret should match");
        assertEquals(TEST_PREVIOUS_SALT, previousEncryptionUtil.getEncryptionSalt(), "Previous encryption salt should match");
    }
    
    /**
     * Tests that the encryption configuration returns null for the previous EncryptionUtil bean
     * when key rotation is disabled.
     */
    @Test
    public void testPreviousEncryptionUtilWithoutKeyRotation() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "keyRotationEnabled", false);
        
        // When
        EncryptionUtil previousEncryptionUtil = encryptionConfig.previousEncryptionUtil(environment);
        
        // Then
        assertNull(previousEncryptionUtil, "Previous EncryptionUtil should be null when key rotation is disabled");
    }
    
    /**
     * Tests that the encryption configuration correctly creates a current encryption key
     * from the configured secret and salt.
     */
    @Test
    public void testCurrentEncryptionKey() {
        // When
        Key currentKey = encryptionConfig.currentEncryptionKey();
        
        // Then
        assertNotNull(currentKey, "Current encryption key should not be null");
        assertEquals("AES", currentKey.getAlgorithm(), "Key algorithm should be AES");
        assertEquals(32, currentKey.getEncoded().length, "Key length should be 32 bytes (256 bits)");
    }
    
    /**
     * Tests that the encryption configuration correctly creates a previous encryption key
     * when key rotation is enabled.
     */
    @Test
    public void testPreviousEncryptionKeyWithKeyRotation() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "keyRotationEnabled", true);
        ReflectionTestUtils.setField(encryptionConfig, "previousEncryptionSecret", TEST_PREVIOUS_SECRET);
        ReflectionTestUtils.setField(encryptionConfig, "previousEncryptionSalt", TEST_PREVIOUS_SALT);
        
        // When
        Key previousKey = encryptionConfig.previousEncryptionKey();
        
        // Then
        assertNotNull(previousKey, "Previous encryption key should not be null when key rotation is enabled");
        assertEquals("AES", previousKey.getAlgorithm(), "Key algorithm should be AES");
        assertEquals(32, previousKey.getEncoded().length, "Key length should be 32 bytes (256 bits)");
    }
    
    /**
     * Tests that the encryption configuration returns null for the previous encryption key
     * when key rotation is disabled.
     */
    @Test
    public void testPreviousEncryptionKeyWithoutKeyRotation() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "keyRotationEnabled", false);
        
        // When
        Key previousKey = encryptionConfig.previousEncryptionKey();
        
        // Then
        assertNull(previousKey, "Previous encryption key should be null when key rotation is disabled");
    }
    
    /**
     * Tests that the encryption configuration correctly creates an EncryptedStringConverter bean
     * with the configured EncryptionUtil.
     */
    @Test
    public void testEncryptedStringConverter() {
        // Given
        EncryptionUtil encryptionUtil = encryptionConfig.encryptionUtil(environment);
        
        // When
        EncryptedStringConverter converter = encryptionConfig.encryptedStringConverter(encryptionUtil);
        
        // Then
        assertNotNull(converter, "EncryptedStringConverter should not be null");
        
        // Test that the converter uses the provided EncryptionUtil
        // We need to use reflection to access the private field
        EncryptionUtil converterEncryptionUtil = (EncryptionUtil) ReflectionTestUtils.getField(converter, "encryptionUtil");
        assertNotNull(converterEncryptionUtil, "EncryptionUtil in converter should not be null");
        assertSame(encryptionUtil, converterEncryptionUtil, "EncryptionUtil in converter should be the same instance");
    }
    
    /**
     * Tests that the encryption configuration correctly validates the encryption configuration
     * and throws an exception when the encryption secret is not configured.
     */
    @Test
    public void testValidateEncryptionConfigurationWithMissingSecret() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSecret", null);
        
        // Then
        Exception exception = assertThrows(IllegalStateException.class, () -> {
            // Call the private method using reflection
            Method validateMethod = EncryptionConfig.class.getDeclaredMethod("validateEncryptionConfiguration");
            validateMethod.setAccessible(true);
            validateMethod.invoke(encryptionConfig);
        }, "Should throw IllegalStateException when encryption secret is not configured");
        
        assertTrue(exception.getCause().getMessage().contains("Encryption secret must be configured"),
                "Exception message should indicate missing secret");
    }
    
    /**
     * Tests that the encryption configuration correctly validates the encryption configuration
     * and throws an exception when the encryption salt is not configured.
     */
    @Test
    public void testValidateEncryptionConfigurationWithMissingSalt() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "encryptionSalt", null);
        
        // Then
        Exception exception = assertThrows(IllegalStateException.class, () -> {
            // Call the private method using reflection
            Method validateMethod = EncryptionConfig.class.getDeclaredMethod("validateEncryptionConfiguration");
            validateMethod.setAccessible(true);
            validateMethod.invoke(encryptionConfig);
        }, "Should throw IllegalStateException when encryption salt is not configured");
        
        assertTrue(exception.getCause().getMessage().contains("Encryption salt must be configured"),
                "Exception message should indicate missing salt");
    }
    
    /**
     * Tests that the encryption configuration correctly derives an AES key from the
     * provided secret and salt.
     */
    @Test
    public void testDeriveKey() throws Exception {
        // Call the private method using reflection
        Method deriveKeyMethod = EncryptionConfig.class.getDeclaredMethod("deriveKey", String.class, String.class);
        deriveKeyMethod.setAccessible(true);
        SecretKey key = (SecretKey) deriveKeyMethod.invoke(encryptionConfig, TEST_SECRET, TEST_SALT);
        
        // Then
        assertNotNull(key, "Derived key should not be null");
        assertEquals("AES", key.getAlgorithm(), "Key algorithm should be AES");
        assertEquals(32, key.getEncoded().length, "Key length should be 32 bytes (256 bits)");
    }
    
    /**
     * Tests that the encryption configuration correctly generates a random encryption key.
     */
    @Test
    public void testGenerateRandomEncryptionKey() {
        // When
        String key1 = EncryptionConfig.generateRandomEncryptionKey();
        String key2 = EncryptionConfig.generateRandomEncryptionKey();
        
        // Then
        assertNotNull(key1, "Generated key should not be null");
        assertNotNull(key2, "Generated key should not be null");
        assertNotEquals(key1, key2, "Generated keys should be different");
        
        // Decode the Base64 key and check its length
        byte[] keyBytes = java.util.Base64.getDecoder().decode(key1);
        assertEquals(32, keyBytes.length, "Key length should be 32 bytes (256 bits)");
    }
    
    /**
     * Tests that the encryption configuration correctly generates a random salt.
     */
    @Test
    public void testGenerateRandomSalt() {
        // When
        String salt1 = EncryptionConfig.generateRandomSalt();
        String salt2 = EncryptionConfig.generateRandomSalt();
        
        // Then
        assertNotNull(salt1, "Generated salt should not be null");
        assertNotNull(salt2, "Generated salt should not be null");
        assertNotEquals(salt1, salt2, "Generated salts should be different");
        
        // Decode the Base64 salt and check its length
        byte[] saltBytes = java.util.Base64.getDecoder().decode(salt1);
        assertEquals(16, saltBytes.length, "Salt length should be 16 bytes (128 bits)");
    }
    
    /**
     * Tests that the encryption configuration correctly generates a sample properties file.
     */
    @Test
    public void testGenerateSamplePropertiesFile() {
        // When
        String propertiesFile = EncryptionConfig.generateSamplePropertiesFile();
        
        // Then
        assertNotNull(propertiesFile, "Generated properties file should not be null");
        assertTrue(propertiesFile.contains("encryption.secret="), "Properties file should contain encryption.secret");
        assertTrue(propertiesFile.contains("encryption.salt="), "Properties file should contain encryption.salt");
        assertTrue(propertiesFile.contains("encryption.key-rotation.enabled=false"), "Properties file should contain key rotation setting");
        assertTrue(propertiesFile.contains("encryption.key-rotation.previous-secret="), "Properties file should contain previous secret");
        assertTrue(propertiesFile.contains("encryption.key-rotation.previous-salt="), "Properties file should contain previous salt");
        assertTrue(propertiesFile.contains("encryption.multi-tenant.enabled=false"), "Properties file should contain multi-tenant setting");
    }
    
    /**
     * Tests that the encryption configuration correctly initializes after construction.
     */
    @Test
    public void testInit() {
        // When
        encryptionConfig.init();
        
        // Then - no exception should be thrown
        // This test primarily verifies that the init method doesn't throw exceptions
        // with valid configuration
    }
    
    /**
     * Tests that the encryption configuration correctly handles multi-tenant scenarios
     * when multi-tenant encryption is enabled.
     */
    @Test
    public void testGetEncryptionUtilForTenantWithMultiTenantEnabled() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "multiTenantEnabled", true);
        EncryptionUtil defaultEncryptionUtil = encryptionConfig.encryptionUtil(environment);
        when(applicationContext.getBean(EncryptionUtil.class)).thenReturn(defaultEncryptionUtil);
        when(applicationContext.getEnvironment()).thenReturn(environment);
        when(environment.getProperty("encryption.tenant." + TEST_TENANT_ID + ".secret")).thenReturn(TEST_TENANT_SECRET);
        when(environment.getProperty("encryption.tenant." + TEST_TENANT_ID + ".salt")).thenReturn(TEST_TENANT_SALT);
        
        // When
        EncryptionUtil tenantEncryptionUtil = encryptionConfig.getEncryptionUtilForTenant(TEST_TENANT_ID, applicationContext);
        
        // Then
        assertNotNull(tenantEncryptionUtil, "Tenant EncryptionUtil should not be null");
        assertEquals(TEST_TENANT_SECRET, tenantEncryptionUtil.getEncryptionSecret(), "Tenant encryption secret should match");
        assertEquals(TEST_TENANT_SALT, tenantEncryptionUtil.getEncryptionSalt(), "Tenant encryption salt should match");
    }
    
    /**
     * Tests that the encryption configuration correctly falls back to the default encryption util
     * when multi-tenant encryption is enabled but tenant-specific keys are not configured.
     */
    @Test
    public void testGetEncryptionUtilForTenantWithMissingTenantKeys() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "multiTenantEnabled", true);
        EncryptionUtil defaultEncryptionUtil = encryptionConfig.encryptionUtil(environment);
        when(applicationContext.getBean(EncryptionUtil.class)).thenReturn(defaultEncryptionUtil);
        when(applicationContext.getEnvironment()).thenReturn(environment);
        when(environment.getProperty("encryption.tenant." + TEST_TENANT_ID + ".secret")).thenReturn(null);
        when(environment.getProperty("encryption.tenant." + TEST_TENANT_ID + ".salt")).thenReturn(null);
        
        // When
        EncryptionUtil tenantEncryptionUtil = encryptionConfig.getEncryptionUtilForTenant(TEST_TENANT_ID, applicationContext);
        
        // Then
        assertNotNull(tenantEncryptionUtil, "Tenant EncryptionUtil should not be null");
        assertEquals(defaultEncryptionUtil.getEncryptionSecret(), tenantEncryptionUtil.getEncryptionSecret(), "Tenant encryption secret should fall back to default");
        assertEquals(defaultEncryptionUtil.getEncryptionSalt(), tenantEncryptionUtil.getEncryptionSalt(), "Tenant encryption salt should fall back to default");
    }
    
    /**
     * Tests that the encryption configuration correctly returns the default encryption util
     * when multi-tenant encryption is disabled.
     */
    @Test
    public void testGetEncryptionUtilForTenantWithMultiTenantDisabled() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "multiTenantEnabled", false);
        EncryptionUtil defaultEncryptionUtil = encryptionConfig.encryptionUtil(environment);
        when(applicationContext.getBean(EncryptionUtil.class)).thenReturn(defaultEncryptionUtil);
        
        // When
        EncryptionUtil tenantEncryptionUtil = encryptionConfig.getEncryptionUtilForTenant(TEST_TENANT_ID, applicationContext);
        
        // Then
        assertNotNull(tenantEncryptionUtil, "Tenant EncryptionUtil should not be null");
        assertSame(defaultEncryptionUtil, tenantEncryptionUtil, "Should return the default EncryptionUtil when multi-tenant is disabled");
    }
    
    /**
     * Tests that the encryption configuration correctly returns the default encryption util
     * when the tenant ID is null or empty.
     */
    @Test
    public void testGetEncryptionUtilForTenantWithNullTenantId() {
        // Given
        ReflectionTestUtils.setField(encryptionConfig, "multiTenantEnabled", true);
        EncryptionUtil defaultEncryptionUtil = encryptionConfig.encryptionUtil(environment);
        when(applicationContext.getBean(EncryptionUtil.class)).thenReturn(defaultEncryptionUtil);
        
        // When
        EncryptionUtil tenantEncryptionUtil = encryptionConfig.getEncryptionUtilForTenant(null, applicationContext);
        
        // Then
        assertNotNull(tenantEncryptionUtil, "Tenant EncryptionUtil should not be null");
        assertSame(defaultEncryptionUtil, tenantEncryptionUtil, "Should return the default EncryptionUtil when tenant ID is null");
    }
}