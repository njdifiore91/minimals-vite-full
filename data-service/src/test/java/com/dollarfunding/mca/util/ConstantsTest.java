package com.dollarfunding.mca.util;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link Constants} class which defines application-wide constants
 * for the MCA (Merchant Cash Advance) application.
 * 
 * These tests verify that all constants are properly defined with the correct values and types.
 * This helps maintain the integrity of constant values used throughout the application.
 */
public class ConstantsTest {

    /**
     * Tests for ApplicationStatus constants.
     * Verifies that application status constants are properly defined with the correct values.
     */
    @Test
    @DisplayName("Should verify ApplicationStatus constants have correct values")
    void shouldVerifyApplicationStatusConstants() {
        // Verify all constants are non-null and have the expected type
        assertNotNull(Constants.ApplicationStatus.NEW);
        assertNotNull(Constants.ApplicationStatus.PROCESSING);
        assertNotNull(Constants.ApplicationStatus.PENDING);
        assertNotNull(Constants.ApplicationStatus.APPROVED);
        assertNotNull(Constants.ApplicationStatus.REJECTED);
        assertNotNull(Constants.ApplicationStatus.COMPLETE);
        assertNotNull(Constants.ApplicationStatus.EXCEPTION);
        assertNotNull(Constants.ApplicationStatus.ERROR);
        
        // Verify specific values
        assertEquals("NEW", Constants.ApplicationStatus.NEW);
        assertEquals("PROCESSING", Constants.ApplicationStatus.PROCESSING);
        assertEquals("PENDING", Constants.ApplicationStatus.PENDING);
        assertEquals("APPROVED", Constants.ApplicationStatus.APPROVED);
        assertEquals("REJECTED", Constants.ApplicationStatus.REJECTED);
        assertEquals("COMPLETE", Constants.ApplicationStatus.COMPLETE);
        assertEquals("EXCEPTION", Constants.ApplicationStatus.EXCEPTION);
        assertEquals("ERROR", Constants.ApplicationStatus.ERROR);
    }
    
    /**
     * Tests for DocumentType constants.
     * Verifies that document type constants are properly defined for document classification.
     */
    @Test
    @DisplayName("Should verify DocumentType constants have correct values")
    void shouldVerifyDocumentTypeConstants() {
        // Verify all constants are non-null and have the expected type
        assertNotNull(Constants.DocumentType.LOAN_APPLICATION);
        assertNotNull(Constants.DocumentType.TAX_RETURN);
        assertNotNull(Constants.DocumentType.BANK_STATEMENT);
        assertNotNull(Constants.DocumentType.PAY_STUB);
        assertNotNull(Constants.DocumentType.IDENTITY_DOCUMENT);
        assertNotNull(Constants.DocumentType.OTHER);
        
        // Verify specific values
        assertEquals("LOAN_APPLICATION", Constants.DocumentType.LOAN_APPLICATION);
        assertEquals("TAX_RETURN", Constants.DocumentType.TAX_RETURN);
        assertEquals("BANK_STATEMENT", Constants.DocumentType.BANK_STATEMENT);
        assertEquals("PAY_STUB", Constants.DocumentType.PAY_STUB);
        assertEquals("IDENTITY_DOCUMENT", Constants.DocumentType.IDENTITY_DOCUMENT);
        assertEquals("OTHER", Constants.DocumentType.OTHER);
    }
    
    /**
     * Tests for ErrorCode constants.
     * Verifies that error code constants are properly defined for consistent error handling.
     */
    @Test
    @DisplayName("Should verify ErrorCode constants have correct values and follow the pattern")
    void shouldVerifyErrorCodeConstants() {
        // Verify general error codes
        assertNotNull(Constants.ErrorCode.GENERAL_ERROR);
        assertNotNull(Constants.ErrorCode.VALIDATION_ERROR);
        assertNotNull(Constants.ErrorCode.UNAUTHORIZED);
        assertNotNull(Constants.ErrorCode.FORBIDDEN);
        assertNotNull(Constants.ErrorCode.NOT_FOUND);
        
        // Verify application-specific error codes
        assertNotNull(Constants.ErrorCode.APPLICATION_NOT_FOUND);
        assertNotNull(Constants.ErrorCode.APPLICATION_INVALID_STATE);
        assertNotNull(Constants.ErrorCode.APPLICATION_PROCESSING_ERROR);
        
        // Verify document-specific error codes
        assertNotNull(Constants.ErrorCode.DOCUMENT_NOT_FOUND);
        assertNotNull(Constants.ErrorCode.DOCUMENT_INVALID_TYPE);
        assertNotNull(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR);
        assertNotNull(Constants.ErrorCode.DOCUMENT_STORAGE_ERROR);
        
        // Verify OCR-specific error codes
        assertNotNull(Constants.ErrorCode.OCR_PROCESSING_ERROR);
        assertNotNull(Constants.ErrorCode.OCR_LOW_CONFIDENCE);
        
        // Verify data-specific error codes
        assertNotNull(Constants.ErrorCode.DATA_VALIDATION_ERROR);
        assertNotNull(Constants.ErrorCode.DATA_INTEGRITY_ERROR);
        
        // Verify messaging-specific error codes
        assertNotNull(Constants.ErrorCode.MESSAGING_PUBLISH_ERROR);
        assertNotNull(Constants.ErrorCode.MESSAGING_CONSUME_ERROR);
        
        // Verify error code format (prefix-number)
        assertTrue(Constants.ErrorCode.GENERAL_ERROR.matches("[A-Z]+-\\d+"));
        assertTrue(Constants.ErrorCode.APPLICATION_NOT_FOUND.matches("[A-Z]+-\\d+"));
        assertTrue(Constants.ErrorCode.DOCUMENT_NOT_FOUND.matches("[A-Z]+-\\d+"));
        assertTrue(Constants.ErrorCode.OCR_PROCESSING_ERROR.matches("[A-Z]+-\\d+"));
        assertTrue(Constants.ErrorCode.DATA_VALIDATION_ERROR.matches("[A-Z]+-\\d+"));
        assertTrue(Constants.ErrorCode.MESSAGING_PUBLISH_ERROR.matches("[A-Z]+-\\d+"));
        
        // Verify specific values
        assertEquals("GEN-001", Constants.ErrorCode.GENERAL_ERROR);
        assertEquals("APP-001", Constants.ErrorCode.APPLICATION_NOT_FOUND);
        assertEquals("DOC-001", Constants.ErrorCode.DOCUMENT_NOT_FOUND);
        assertEquals("OCR-001", Constants.ErrorCode.OCR_PROCESSING_ERROR);
        assertEquals("DAT-001", Constants.ErrorCode.DATA_VALIDATION_ERROR);
        assertEquals("MSG-001", Constants.ErrorCode.MESSAGING_PUBLISH_ERROR);
    }
    
    /**
     * Tests for ValidationRegex constants.
     * Verifies that regex pattern constants are properly defined and valid for pattern matching.
     */
    @Test
    @DisplayName("Should verify ValidationRegex constants are valid regex patterns")
    void shouldVerifyValidationRegexConstants() {
        // Verify all constants are non-null
        assertNotNull(Constants.ValidationRegex.EMAIL);
        assertNotNull(Constants.ValidationRegex.PHONE);
        assertNotNull(Constants.ValidationRegex.EIN);
        assertNotNull(Constants.ValidationRegex.SSN);
        assertNotNull(Constants.ValidationRegex.CURRENCY);
        assertNotNull(Constants.ValidationRegex.PERCENTAGE);
        assertNotNull(Constants.ValidationRegex.ZIP_CODE);
        assertNotNull(Constants.ValidationRegex.STATE_CODE);
        
        // Verify that all regex patterns are valid by compiling them
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.EMAIL));
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.PHONE));
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.EIN));
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.SSN));
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.CURRENCY));
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.PERCENTAGE));
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.ZIP_CODE));
        assertDoesNotThrow(() -> Pattern.compile(Constants.ValidationRegex.STATE_CODE));
    }
    
    /**
     * Tests for ValidationRegex pattern matching.
     * Verifies that regex patterns correctly match valid inputs and reject invalid inputs.
     */
    @ParameterizedTest
    @CsvSource({
        "EMAIL, test@example.com, true",
        "EMAIL, invalid-email, false",
        "PHONE, +12345678901, true",
        "PHONE, 123, false",
        "EIN, 12-3456789, true",
        "EIN, 123-456789, false",
        "SSN, 123-45-6789, true",
        "SSN, 123-456-789, false",
        "CURRENCY, $1,234.56, true",
        "CURRENCY, 1,234.56, true",
        "CURRENCY, $1234.5, false",
        "PERCENTAGE, 12.34%, true",
        "PERCENTAGE, 12.345%, false",
        "ZIP_CODE, 12345, true",
        "ZIP_CODE, 12345-6789, true",
        "ZIP_CODE, 1234, false",
        "STATE_CODE, CA, true",
        "STATE_CODE, ca, false"
    })
    @DisplayName("Should verify ValidationRegex patterns match correctly")
    void shouldVerifyValidationRegexPatternMatching(String regexName, String input, boolean shouldMatch) {
        String regexPattern = null;
        
        // Get the regex pattern based on the name
        switch (regexName) {
            case "EMAIL":
                regexPattern = Constants.ValidationRegex.EMAIL;
                break;
            case "PHONE":
                regexPattern = Constants.ValidationRegex.PHONE;
                break;
            case "EIN":
                regexPattern = Constants.ValidationRegex.EIN;
                break;
            case "SSN":
                regexPattern = Constants.ValidationRegex.SSN;
                break;
            case "CURRENCY":
                regexPattern = Constants.ValidationRegex.CURRENCY;
                break;
            case "PERCENTAGE":
                regexPattern = Constants.ValidationRegex.PERCENTAGE;
                break;
            case "ZIP_CODE":
                regexPattern = Constants.ValidationRegex.ZIP_CODE;
                break;
            case "STATE_CODE":
                regexPattern = Constants.ValidationRegex.STATE_CODE;
                break;
            default:
                fail("Unknown regex name: " + regexName);
        }
        
        // Verify pattern matching
        Pattern pattern = Pattern.compile(regexPattern);
        assertEquals(shouldMatch, pattern.matcher(input).matches(),
                String.format("%s pattern should %s match input '%s'", 
                        regexName, shouldMatch ? "" : "not ", input));
    }
    
    /**
     * Tests for CacheTTL constants.
     * Verifies that cache TTL constants have the correct values as specified in requirements.
     */
    @Test
    @DisplayName("Should verify CacheTTL constants have correct values")
    void shouldVerifyCacheTTLConstants() {
        // Verify all constants are positive integers
        assertTrue(Constants.CacheTTL.APPLICATION_DATA > 0);
        assertTrue(Constants.CacheTTL.USER_SESSION > 0);
        assertTrue(Constants.CacheTTL.METADATA > 0);
        assertTrue(Constants.CacheTTL.CONFIGURATION > 0);
        
        // Verify specific values from requirements
        assertEquals(15 * 60, Constants.CacheTTL.APPLICATION_DATA, "Application data TTL should be 15 minutes (900 seconds)");
        assertEquals(24 * 60 * 60, Constants.CacheTTL.USER_SESSION, "User session TTL should be 24 hours (86400 seconds)");
        assertEquals(30 * 60, Constants.CacheTTL.METADATA, "Metadata TTL should be 30 minutes (1800 seconds)");
        assertEquals(60 * 60, Constants.CacheTTL.CONFIGURATION, "Configuration TTL should be 1 hour (3600 seconds)");
    }
    
    /**
     * Tests for QueueName constants.
     * Verifies that queue name constants are properly defined for RabbitMQ configuration.
     */
    @Test
    @DisplayName("Should verify QueueName constants have correct values")
    void shouldVerifyQueueNameConstants() {
        // Verify all constants are non-null and non-empty
        assertNotNull(Constants.QueueName.DOCUMENTS_EXCHANGE);
        assertNotNull(Constants.QueueName.DOCUMENT_PROCESSING);
        assertNotNull(Constants.QueueName.DATA_EXTRACTION);
        assertNotNull(Constants.QueueName.NOTIFICATION);
        assertNotNull(Constants.QueueName.DOCUMENT_NEW);
        assertNotNull(Constants.QueueName.OCR_REQUEST);
        assertNotNull(Constants.QueueName.DATA_PROCESSING);
        
        assertFalse(Constants.QueueName.DOCUMENTS_EXCHANGE.isEmpty());
        assertFalse(Constants.QueueName.DOCUMENT_PROCESSING.isEmpty());
        assertFalse(Constants.QueueName.DATA_EXTRACTION.isEmpty());
        assertFalse(Constants.QueueName.NOTIFICATION.isEmpty());
        assertFalse(Constants.QueueName.DOCUMENT_NEW.isEmpty());
        assertFalse(Constants.QueueName.OCR_REQUEST.isEmpty());
        assertFalse(Constants.QueueName.DATA_PROCESSING.isEmpty());
        
        // Verify specific values from requirements
        assertEquals("mca.documents", Constants.QueueName.DOCUMENTS_EXCHANGE);
        assertEquals("document-processing", Constants.QueueName.DOCUMENT_PROCESSING);
        assertEquals("data-extraction", Constants.QueueName.DATA_EXTRACTION);
        assertEquals("notification", Constants.QueueName.NOTIFICATION);
    }
    
    /**
     * Tests for SecurityConstants.
     * Verifies that security constants are properly defined for encryption parameters.
     */
    @Test
    @DisplayName("Should verify SecurityConstants have correct values")
    void shouldVerifySecurityConstants() {
        // Verify all constants are non-null
        assertNotNull(Constants.SecurityConstants.ENCRYPTION_ALGORITHM);
        assertTrue(Constants.SecurityConstants.AES_KEY_SIZE > 0);
        assertTrue(Constants.SecurityConstants.GCM_IV_LENGTH > 0);
        assertTrue(Constants.SecurityConstants.GCM_TAG_LENGTH > 0);
        assertNotNull(Constants.SecurityConstants.JWT_ALGORITHM);
        assertTrue(Constants.SecurityConstants.JWT_EXPIRY > 0);
        assertTrue(Constants.SecurityConstants.REFRESH_TOKEN_EXPIRY > 0);
        assertNotNull(Constants.SecurityConstants.PII_FIELDS);
        assertTrue(Constants.SecurityConstants.PII_FIELDS.length > 0);
        
        // Verify specific values from requirements
        assertEquals("AES/GCM/NoPadding", Constants.SecurityConstants.ENCRYPTION_ALGORITHM);
        assertEquals(256, Constants.SecurityConstants.AES_KEY_SIZE, "AES key size should be 256 bits");
        assertEquals("RS256", Constants.SecurityConstants.JWT_ALGORITHM);
        assertEquals(60, Constants.SecurityConstants.JWT_EXPIRY, "JWT expiry should be 60 minutes");
        assertEquals(7 * 24 * 60, Constants.SecurityConstants.REFRESH_TOKEN_EXPIRY, "Refresh token expiry should be 7 days");
        
        // Verify PII fields include critical fields
        boolean hasSsn = false;
        boolean hasEin = false;
        boolean hasBankAccount = false;
        
        for (String field : Constants.SecurityConstants.PII_FIELDS) {
            if ("ssn".equals(field)) hasSsn = true;
            if ("ein".equals(field)) hasEin = true;
            if ("bankAccountNumber".equals(field)) hasBankAccount = true;
        }
        
        assertTrue(hasSsn, "PII fields should include SSN");
        assertTrue(hasEin, "PII fields should include EIN");
        assertTrue(hasBankAccount, "PII fields should include bank account number");
    }
    
    /**
     * Tests for BusinessRule constants.
     * Verifies that business rule constants have the correct values as specified in requirements.
     */
    @Test
    @DisplayName("Should verify BusinessRule constants have correct values")
    void shouldVerifyBusinessRuleConstants() {
        // Verify all constants have appropriate values
        assertTrue(Constants.BusinessRule.MAX_PROCESSING_TIME > 0);
        assertTrue(Constants.BusinessRule.AUTOMATION_RATE_TARGET > 0 && Constants.BusinessRule.AUTOMATION_RATE_TARGET <= 1.0);
        assertTrue(Constants.BusinessRule.DATA_EXTRACTION_ACCURACY > 0 && Constants.BusinessRule.DATA_EXTRACTION_ACCURACY <= 1.0);
        assertTrue(Constants.BusinessRule.OCR_HIGH_CONFIDENCE > 0 && Constants.BusinessRule.OCR_HIGH_CONFIDENCE <= 1.0);
        assertTrue(Constants.BusinessRule.OCR_LOW_CONFIDENCE > 0 && Constants.BusinessRule.OCR_LOW_CONFIDENCE <= 1.0);
        assertTrue(Constants.BusinessRule.CLASSIFICATION_CONFIDENCE > 0 && Constants.BusinessRule.CLASSIFICATION_CONFIDENCE <= 1.0);
        
        // Verify specific values from requirements
        assertEquals(5, Constants.BusinessRule.MAX_PROCESSING_TIME, "Max processing time should be 5 minutes");
        assertEquals(0.93, Constants.BusinessRule.AUTOMATION_RATE_TARGET, 0.001, "Automation rate target should be 93%");
        assertEquals(0.99, Constants.BusinessRule.DATA_EXTRACTION_ACCURACY, 0.001, "Data extraction accuracy should be 99%");
    }
    
    /**
     * Tests for ApiEndpoint constants.
     * Verifies that API endpoint constants are properly defined with the correct paths.
     */
    @Test
    @DisplayName("Should verify ApiEndpoint constants have correct values")
    void shouldVerifyApiEndpointConstants() {
        // Verify all constants are non-null and non-empty
        assertNotNull(Constants.ApiEndpoint.API_BASE);
        assertNotNull(Constants.ApiEndpoint.APPLICATIONS);
        assertNotNull(Constants.ApiEndpoint.APPLICATION_BY_ID);
        assertNotNull(Constants.ApiEndpoint.APPLICATION_STATUS);
        assertNotNull(Constants.ApiEndpoint.DOCUMENTS);
        assertNotNull(Constants.ApiEndpoint.DOCUMENT_BY_ID);
        assertNotNull(Constants.ApiEndpoint.DOCUMENTS_BY_APPLICATION);
        assertNotNull(Constants.ApiEndpoint.WEBHOOKS);
        assertNotNull(Constants.ApiEndpoint.WEBHOOK_BY_ID);
        assertNotNull(Constants.ApiEndpoint.WEBHOOK_TEST);
        
        // Verify base path
        assertEquals("/api/v1", Constants.ApiEndpoint.API_BASE);
        
        // Verify that endpoints start with the base path
        assertTrue(Constants.ApiEndpoint.APPLICATIONS.startsWith(Constants.ApiEndpoint.API_BASE));
        assertTrue(Constants.ApiEndpoint.DOCUMENTS.startsWith(Constants.ApiEndpoint.API_BASE));
        assertTrue(Constants.ApiEndpoint.WEBHOOKS.startsWith(Constants.ApiEndpoint.API_BASE));
        
        // Verify that ID-specific endpoints contain the {id} parameter
        assertTrue(Constants.ApiEndpoint.APPLICATION_BY_ID.contains("{id}"));
        assertTrue(Constants.ApiEndpoint.DOCUMENT_BY_ID.contains("{id}"));
        assertTrue(Constants.ApiEndpoint.WEBHOOK_BY_ID.contains("{id}"));
    }
    
    /**
     * Tests for ConfigKey constants.
     * Verifies that configuration key constants are properly defined.
     */
    @Test
    @DisplayName("Should verify ConfigKey constants have correct values")
    void shouldVerifyConfigKeyConstants() {
        // Verify all constants are non-null and non-empty
        // Database configuration
        assertNotNull(Constants.ConfigKey.DB_PRIMARY_URL);
        assertNotNull(Constants.ConfigKey.DB_USERNAME);
        assertNotNull(Constants.ConfigKey.DB_PASSWORD);
        
        // Redis configuration
        assertNotNull(Constants.ConfigKey.REDIS_HOST);
        assertNotNull(Constants.ConfigKey.REDIS_PORT);
        
        // RabbitMQ configuration
        assertNotNull(Constants.ConfigKey.RABBITMQ_HOST);
        assertNotNull(Constants.ConfigKey.RABBITMQ_PORT);
        assertNotNull(Constants.ConfigKey.RABBITMQ_USERNAME);
        assertNotNull(Constants.ConfigKey.RABBITMQ_PASSWORD);
        
        // S3 configuration
        assertNotNull(Constants.ConfigKey.S3_ENDPOINT);
        assertNotNull(Constants.ConfigKey.S3_REGION);
        assertNotNull(Constants.ConfigKey.S3_BUCKET);
        
        // Security configuration
        assertNotNull(Constants.ConfigKey.ENCRYPTION_KEY);
        assertNotNull(Constants.ConfigKey.JWT_PUBLIC_KEY);
        assertNotNull(Constants.ConfigKey.JWT_PRIVATE_KEY);
        
        // Verify that Spring configuration keys follow the Spring naming convention
        assertTrue(Constants.ConfigKey.DB_PRIMARY_URL.startsWith("spring."));
        assertTrue(Constants.ConfigKey.REDIS_HOST.startsWith("spring."));
        assertTrue(Constants.ConfigKey.RABBITMQ_HOST.startsWith("spring."));
    }
}