package com.dollarfunding.mca.util;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.List;
import java.util.regex.Pattern;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for the {@link Constants} class that defines application-wide constants
 * for the MCA (Merchant Cash Advance) application.
 * 
 * These tests verify that all constants are properly defined with the correct values and types.
 * This helps maintain the integrity of constant values used throughout the application.
 */
public class ConstantsTest {

    @Nested
    @DisplayName("Application Status Constants Tests")
    class ApplicationStatusTests {
        
        @Test
        @DisplayName("Should define all required application status constants")
        void shouldDefineAllRequiredApplicationStatusConstants() {
            // Verify all required application status constants are defined
            assertNotNull(Constants.ApplicationStatus.NEW);
            assertNotNull(Constants.ApplicationStatus.PROCESSING);
            assertNotNull(Constants.ApplicationStatus.PENDING);
            assertNotNull(Constants.ApplicationStatus.APPROVED);
            assertNotNull(Constants.ApplicationStatus.REJECTED);
            assertNotNull(Constants.ApplicationStatus.COMPLETE);
            assertNotNull(Constants.ApplicationStatus.EXCEPTION);
            assertNotNull(Constants.ApplicationStatus.ERROR);
        }
        
        @Test
        @DisplayName("Should have correct values for application status constants")
        void shouldHaveCorrectValuesForApplicationStatusConstants() {
            // Verify the values of application status constants
            assertEquals("NEW", Constants.ApplicationStatus.NEW);
            assertEquals("PROCESSING", Constants.ApplicationStatus.PROCESSING);
            assertEquals("PENDING", Constants.ApplicationStatus.PENDING);
            assertEquals("APPROVED", Constants.ApplicationStatus.APPROVED);
            assertEquals("REJECTED", Constants.ApplicationStatus.REJECTED);
            assertEquals("COMPLETE", Constants.ApplicationStatus.COMPLETE);
            assertEquals("EXCEPTION", Constants.ApplicationStatus.EXCEPTION);
            assertEquals("ERROR", Constants.ApplicationStatus.ERROR);
        }
        
        @Test
        @DisplayName("Should have unique values for all application status constants")
        void shouldHaveUniqueValuesForAllApplicationStatusConstants() {
            // Collect all application status constants
            List<String> statusValues = Arrays.asList(
                Constants.ApplicationStatus.NEW,
                Constants.ApplicationStatus.PROCESSING,
                Constants.ApplicationStatus.PENDING,
                Constants.ApplicationStatus.APPROVED,
                Constants.ApplicationStatus.REJECTED,
                Constants.ApplicationStatus.COMPLETE,
                Constants.ApplicationStatus.EXCEPTION,
                Constants.ApplicationStatus.ERROR
            );
            
            // Verify that all values are unique
            assertEquals(statusValues.size(), statusValues.stream().distinct().count(),
                    "All application status constants should have unique values");
        }
    }
    
    @Nested
    @DisplayName("Document Type Constants Tests")
    class DocumentTypeTests {
        
        @Test
        @DisplayName("Should define all required document type constants")
        void shouldDefineAllRequiredDocumentTypeConstants() {
            // Verify all required document type constants are defined
            assertNotNull(Constants.DocumentType.LOAN_APPLICATION);
            assertNotNull(Constants.DocumentType.TAX_RETURN);
            assertNotNull(Constants.DocumentType.BANK_STATEMENT);
            assertNotNull(Constants.DocumentType.PAY_STUB);
            assertNotNull(Constants.DocumentType.IDENTITY_DOCUMENT);
            assertNotNull(Constants.DocumentType.OTHER);
        }
        
        @Test
        @DisplayName("Should have correct values for document type constants")
        void shouldHaveCorrectValuesForDocumentTypeConstants() {
            // Verify the values of document type constants
            assertEquals("LOAN_APPLICATION", Constants.DocumentType.LOAN_APPLICATION);
            assertEquals("TAX_RETURN", Constants.DocumentType.TAX_RETURN);
            assertEquals("BANK_STATEMENT", Constants.DocumentType.BANK_STATEMENT);
            assertEquals("PAY_STUB", Constants.DocumentType.PAY_STUB);
            assertEquals("IDENTITY_DOCUMENT", Constants.DocumentType.IDENTITY_DOCUMENT);
            assertEquals("OTHER", Constants.DocumentType.OTHER);
        }
        
        @Test
        @DisplayName("Should have unique values for all document type constants")
        void shouldHaveUniqueValuesForAllDocumentTypeConstants() {
            // Collect all document type constants
            List<String> documentTypeValues = Arrays.asList(
                Constants.DocumentType.LOAN_APPLICATION,
                Constants.DocumentType.TAX_RETURN,
                Constants.DocumentType.BANK_STATEMENT,
                Constants.DocumentType.PAY_STUB,
                Constants.DocumentType.IDENTITY_DOCUMENT,
                Constants.DocumentType.OTHER
            );
            
            // Verify that all values are unique
            assertEquals(documentTypeValues.size(), documentTypeValues.stream().distinct().count(),
                    "All document type constants should have unique values");
        }
    }
    
    @Nested
    @DisplayName("Error Code Constants Tests")
    class ErrorCodeTests {
        
        @Test
        @DisplayName("Should define all required general error code constants")
        void shouldDefineAllRequiredGeneralErrorCodeConstants() {
            // Verify all required general error code constants are defined
            assertNotNull(Constants.ErrorCode.GENERAL_ERROR);
            assertNotNull(Constants.ErrorCode.VALIDATION_ERROR);
            assertNotNull(Constants.ErrorCode.UNAUTHORIZED);
            assertNotNull(Constants.ErrorCode.FORBIDDEN);
            assertNotNull(Constants.ErrorCode.NOT_FOUND);
        }
        
        @Test
        @DisplayName("Should define all required application-specific error code constants")
        void shouldDefineAllRequiredApplicationSpecificErrorCodeConstants() {
            // Verify all required application-specific error code constants are defined
            assertNotNull(Constants.ErrorCode.APPLICATION_NOT_FOUND);
            assertNotNull(Constants.ErrorCode.APPLICATION_INVALID_STATE);
            assertNotNull(Constants.ErrorCode.APPLICATION_PROCESSING_ERROR);
        }
        
        @Test
        @DisplayName("Should define all required document-specific error code constants")
        void shouldDefineAllRequiredDocumentSpecificErrorCodeConstants() {
            // Verify all required document-specific error code constants are defined
            assertNotNull(Constants.ErrorCode.DOCUMENT_NOT_FOUND);
            assertNotNull(Constants.ErrorCode.DOCUMENT_INVALID_TYPE);
            assertNotNull(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR);
            assertNotNull(Constants.ErrorCode.DOCUMENT_STORAGE_ERROR);
        }
        
        @Test
        @DisplayName("Should define all required OCR-specific error code constants")
        void shouldDefineAllRequiredOcrSpecificErrorCodeConstants() {
            // Verify all required OCR-specific error code constants are defined
            assertNotNull(Constants.ErrorCode.OCR_PROCESSING_ERROR);
            assertNotNull(Constants.ErrorCode.OCR_LOW_CONFIDENCE);
        }
        
        @Test
        @DisplayName("Should define all required data-specific error code constants")
        void shouldDefineAllRequiredDataSpecificErrorCodeConstants() {
            // Verify all required data-specific error code constants are defined
            assertNotNull(Constants.ErrorCode.DATA_VALIDATION_ERROR);
            assertNotNull(Constants.ErrorCode.DATA_INTEGRITY_ERROR);
        }
        
        @Test
        @DisplayName("Should define all required messaging-specific error code constants")
        void shouldDefineAllRequiredMessagingSpecificErrorCodeConstants() {
            // Verify all required messaging-specific error code constants are defined
            assertNotNull(Constants.ErrorCode.MESSAGING_PUBLISH_ERROR);
            assertNotNull(Constants.ErrorCode.MESSAGING_CONSUME_ERROR);
        }
        
        @Test
        @DisplayName("Should have correct prefix for general error codes")
        void shouldHaveCorrectPrefixForGeneralErrorCodes() {
            // Verify that general error codes have the correct prefix
            assertTrue(Constants.ErrorCode.GENERAL_ERROR.startsWith("GEN-"));
            assertTrue(Constants.ErrorCode.VALIDATION_ERROR.startsWith("GEN-"));
            assertTrue(Constants.ErrorCode.UNAUTHORIZED.startsWith("GEN-"));
            assertTrue(Constants.ErrorCode.FORBIDDEN.startsWith("GEN-"));
            assertTrue(Constants.ErrorCode.NOT_FOUND.startsWith("GEN-"));
        }
        
        @Test
        @DisplayName("Should have correct prefix for application error codes")
        void shouldHaveCorrectPrefixForApplicationErrorCodes() {
            // Verify that application error codes have the correct prefix
            assertTrue(Constants.ErrorCode.APPLICATION_NOT_FOUND.startsWith("APP-"));
            assertTrue(Constants.ErrorCode.APPLICATION_INVALID_STATE.startsWith("APP-"));
            assertTrue(Constants.ErrorCode.APPLICATION_PROCESSING_ERROR.startsWith("APP-"));
        }
        
        @Test
        @DisplayName("Should have correct prefix for document error codes")
        void shouldHaveCorrectPrefixForDocumentErrorCodes() {
            // Verify that document error codes have the correct prefix
            assertTrue(Constants.ErrorCode.DOCUMENT_NOT_FOUND.startsWith("DOC-"));
            assertTrue(Constants.ErrorCode.DOCUMENT_INVALID_TYPE.startsWith("DOC-"));
            assertTrue(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR.startsWith("DOC-"));
            assertTrue(Constants.ErrorCode.DOCUMENT_STORAGE_ERROR.startsWith("DOC-"));
        }
        
        @Test
        @DisplayName("Should have correct prefix for OCR error codes")
        void shouldHaveCorrectPrefixForOcrErrorCodes() {
            // Verify that OCR error codes have the correct prefix
            assertTrue(Constants.ErrorCode.OCR_PROCESSING_ERROR.startsWith("OCR-"));
            assertTrue(Constants.ErrorCode.OCR_LOW_CONFIDENCE.startsWith("OCR-"));
        }
        
        @Test
        @DisplayName("Should have correct prefix for data error codes")
        void shouldHaveCorrectPrefixForDataErrorCodes() {
            // Verify that data error codes have the correct prefix
            assertTrue(Constants.ErrorCode.DATA_VALIDATION_ERROR.startsWith("DAT-"));
            assertTrue(Constants.ErrorCode.DATA_INTEGRITY_ERROR.startsWith("DAT-"));
        }
        
        @Test
        @DisplayName("Should have correct prefix for messaging error codes")
        void shouldHaveCorrectPrefixForMessagingErrorCodes() {
            // Verify that messaging error codes have the correct prefix
            assertTrue(Constants.ErrorCode.MESSAGING_PUBLISH_ERROR.startsWith("MSG-"));
            assertTrue(Constants.ErrorCode.MESSAGING_CONSUME_ERROR.startsWith("MSG-"));
        }
        
        @Test
        @DisplayName("Should have unique values for all error code constants")
        void shouldHaveUniqueValuesForAllErrorCodeConstants() {
            // Collect all error code constants
            List<String> errorCodeValues = Arrays.asList(
                Constants.ErrorCode.GENERAL_ERROR,
                Constants.ErrorCode.VALIDATION_ERROR,
                Constants.ErrorCode.UNAUTHORIZED,
                Constants.ErrorCode.FORBIDDEN,
                Constants.ErrorCode.NOT_FOUND,
                Constants.ErrorCode.APPLICATION_NOT_FOUND,
                Constants.ErrorCode.APPLICATION_INVALID_STATE,
                Constants.ErrorCode.APPLICATION_PROCESSING_ERROR,
                Constants.ErrorCode.DOCUMENT_NOT_FOUND,
                Constants.ErrorCode.DOCUMENT_INVALID_TYPE,
                Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR,
                Constants.ErrorCode.DOCUMENT_STORAGE_ERROR,
                Constants.ErrorCode.OCR_PROCESSING_ERROR,
                Constants.ErrorCode.OCR_LOW_CONFIDENCE,
                Constants.ErrorCode.DATA_VALIDATION_ERROR,
                Constants.ErrorCode.DATA_INTEGRITY_ERROR,
                Constants.ErrorCode.MESSAGING_PUBLISH_ERROR,
                Constants.ErrorCode.MESSAGING_CONSUME_ERROR
            );
            
            // Verify that all values are unique
            assertEquals(errorCodeValues.size(), errorCodeValues.stream().distinct().count(),
                    "All error code constants should have unique values");
        }
    }
    
    @Nested
    @DisplayName("Validation Regex Constants Tests")
    class ValidationRegexTests {
        
        @Test
        @DisplayName("Should define all required basic validation regex constants")
        void shouldDefineAllRequiredBasicValidationRegexConstants() {
            // Verify all required basic validation regex constants are defined
            assertNotNull(Constants.ValidationRegex.EMAIL);
            assertNotNull(Constants.ValidationRegex.PHONE);
        }
        
        @Test
        @DisplayName("Should define all required business identifier validation regex constants")
        void shouldDefineAllRequiredBusinessIdentifierValidationRegexConstants() {
            // Verify all required business identifier validation regex constants are defined
            assertNotNull(Constants.ValidationRegex.EIN);
            assertNotNull(Constants.ValidationRegex.SSN);
        }
        
        @Test
        @DisplayName("Should define all required financial validation regex constants")
        void shouldDefineAllRequiredFinancialValidationRegexConstants() {
            // Verify all required financial validation regex constants are defined
            assertNotNull(Constants.ValidationRegex.CURRENCY);
            assertNotNull(Constants.ValidationRegex.PERCENTAGE);
        }
        
        @Test
        @DisplayName("Should define all required address validation regex constants")
        void shouldDefineAllRequiredAddressValidationRegexConstants() {
            // Verify all required address validation regex constants are defined
            assertNotNull(Constants.ValidationRegex.ZIP_CODE);
            assertNotNull(Constants.ValidationRegex.STATE_CODE);
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for email")
        void shouldHaveValidRegexPatternForEmail() {
            // Verify that the email regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.EMAIL);
            
            // Valid email addresses
            assertTrue(pattern.matcher("test@example.com").matches());
            assertTrue(pattern.matcher("user.name@domain.co.uk").matches());
            assertTrue(pattern.matcher("user-name@domain.com").matches());
            
            // Invalid email addresses
            assertFalse(pattern.matcher("test@").matches());
            assertFalse(pattern.matcher("@example.com").matches());
            assertFalse(pattern.matcher("test@example").matches());
            assertFalse(pattern.matcher("test.example.com").matches());
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for phone number")
        void shouldHaveValidRegexPatternForPhoneNumber() {
            // Verify that the phone regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.PHONE);
            
            // Valid phone numbers (E.164 format)
            assertTrue(pattern.matcher("+12025550179").matches());
            assertTrue(pattern.matcher("+442071234567").matches());
            assertTrue(pattern.matcher("+61491570156").matches());
            
            // Invalid phone numbers
            assertFalse(pattern.matcher("12025550179").matches()); // Missing + prefix
            assertFalse(pattern.matcher("+").matches()); // Just a plus sign
            assertFalse(pattern.matcher("+0123").matches()); // Starts with 0
            assertFalse(pattern.matcher("+123abc4567").matches()); // Contains non-digits
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for EIN")
        void shouldHaveValidRegexPatternForEin() {
            // Verify that the EIN regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.EIN);
            
            // Valid EINs
            assertTrue(pattern.matcher("12-3456789").matches());
            assertTrue(pattern.matcher("98-7654321").matches());
            
            // Invalid EINs
            assertFalse(pattern.matcher("123-456789").matches()); // Wrong format
            assertFalse(pattern.matcher("12-345678").matches()); // Too short
            assertFalse(pattern.matcher("12-34567890").matches()); // Too long
            assertFalse(pattern.matcher("AB-1234567").matches()); // Contains letters
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for SSN")
        void shouldHaveValidRegexPatternForSsn() {
            // Verify that the SSN regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.SSN);
            
            // Valid SSNs
            assertTrue(pattern.matcher("123-45-6789").matches());
            assertTrue(pattern.matcher("987-65-4321").matches());
            
            // Invalid SSNs
            assertFalse(pattern.matcher("1234-56-789").matches()); // Wrong format
            assertFalse(pattern.matcher("123-456-789").matches()); // Wrong format
            assertFalse(pattern.matcher("12-34-5678").matches()); // Wrong format
            assertFalse(pattern.matcher("123-45-678").matches()); // Too short
            assertFalse(pattern.matcher("123-45-67890").matches()); // Too long
            assertFalse(pattern.matcher("AAA-BB-CCCC").matches()); // Contains letters
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for currency")
        void shouldHaveValidRegexPatternForCurrency() {
            // Verify that the currency regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.CURRENCY);
            
            // Valid currency values
            assertTrue(pattern.matcher("$100").matches());
            assertTrue(pattern.matcher("$100.00").matches());
            assertTrue(pattern.matcher("$1,000").matches());
            assertTrue(pattern.matcher("$1,000.00").matches());
            assertTrue(pattern.matcher("$1,000,000.00").matches());
            assertTrue(pattern.matcher("100").matches());
            assertTrue(pattern.matcher("100.00").matches());
            assertTrue(pattern.matcher("1,000").matches());
            assertTrue(pattern.matcher("1,000.00").matches());
            
            // Invalid currency values
            assertFalse(pattern.matcher("$").matches()); // Just a dollar sign
            assertFalse(pattern.matcher("$100.0").matches()); // One decimal place
            assertFalse(pattern.matcher("$100.000").matches()); // Three decimal places
            assertFalse(pattern.matcher("$1,00.00").matches()); // Incorrect comma placement
            assertFalse(pattern.matcher("$1,000,00.00").matches()); // Incorrect comma placement
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for percentage")
        void shouldHaveValidRegexPatternForPercentage() {
            // Verify that the percentage regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.PERCENTAGE);
            
            // Valid percentage values
            assertTrue(pattern.matcher("10%").matches());
            assertTrue(pattern.matcher("10.5%").matches());
            assertTrue(pattern.matcher("10.50%").matches());
            assertTrue(pattern.matcher("100%").matches());
            assertTrue(pattern.matcher("0%").matches());
            
            // Invalid percentage values
            assertFalse(pattern.matcher("%").matches()); // Just a percent sign
            assertFalse(pattern.matcher("10").matches()); // Missing percent sign
            assertFalse(pattern.matcher("10.%").matches()); // Decimal point with no digits after
            assertFalse(pattern.matcher("10.500%").matches()); // More than two decimal places
            assertFalse(pattern.matcher("10,%").matches()); // Contains a comma
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for ZIP code")
        void shouldHaveValidRegexPatternForZipCode() {
            // Verify that the ZIP code regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.ZIP_CODE);
            
            // Valid ZIP codes
            assertTrue(pattern.matcher("12345").matches());
            assertTrue(pattern.matcher("12345-6789").matches());
            
            // Invalid ZIP codes
            assertFalse(pattern.matcher("1234").matches()); // Too short
            assertFalse(pattern.matcher("123456").matches()); // Too long for 5-digit format
            assertFalse(pattern.matcher("12345-678").matches()); // Too short for 9-digit format
            assertFalse(pattern.matcher("12345-67890").matches()); // Too long for 9-digit format
            assertFalse(pattern.matcher("ABCDE").matches()); // Contains letters
            assertFalse(pattern.matcher("12345-ABCD").matches()); // Contains letters
        }
        
        @Test
        @DisplayName("Should have valid regex pattern for state code")
        void shouldHaveValidRegexPatternForStateCode() {
            // Verify that the state code regex pattern is valid and works correctly
            Pattern pattern = Pattern.compile(Constants.ValidationRegex.STATE_CODE);
            
            // Valid state codes
            assertTrue(pattern.matcher("CA").matches());
            assertTrue(pattern.matcher("NY").matches());
            assertTrue(pattern.matcher("TX").matches());
            
            // Invalid state codes
            assertFalse(pattern.matcher("C").matches()); // Too short
            assertFalse(pattern.matcher("CAL").matches()); // Too long
            assertFalse(pattern.matcher("Ca").matches()); // Contains lowercase
            assertFalse(pattern.matcher("12").matches()); // Contains digits
            assertFalse(pattern.matcher("C@").matches()); // Contains special characters
        }
    }
    
    @Nested
    @DisplayName("Cache TTL Constants Tests")
    class CacheTTLTests {
        
        @Test
        @DisplayName("Should define all required cache TTL constants")
        void shouldDefineAllRequiredCacheTTLConstants() {
            // Verify all required cache TTL constants are defined
            assertTrue(Constants.CacheTTL.APPLICATION_DATA > 0);
            assertTrue(Constants.CacheTTL.USER_SESSION > 0);
            assertTrue(Constants.CacheTTL.METADATA > 0);
            assertTrue(Constants.CacheTTL.CONFIGURATION > 0);
        }
        
        @Test
        @DisplayName("Should have correct value for application data cache TTL (15 minutes)")
        void shouldHaveCorrectValueForApplicationDataCacheTTL() {
            // Verify that the application data cache TTL is set to 15 minutes (in seconds)
            assertEquals(15 * 60, Constants.CacheTTL.APPLICATION_DATA);
        }
        
        @Test
        @DisplayName("Should have correct value for user session cache TTL (24 hours)")
        void shouldHaveCorrectValueForUserSessionCacheTTL() {
            // Verify that the user session cache TTL is set to 24 hours (in seconds)
            assertEquals(24 * 60 * 60, Constants.CacheTTL.USER_SESSION);
        }
        
        @Test
        @DisplayName("Should have correct value for metadata cache TTL (30 minutes)")
        void shouldHaveCorrectValueForMetadataCacheTTL() {
            // Verify that the metadata cache TTL is set to 30 minutes (in seconds)
            assertEquals(30 * 60, Constants.CacheTTL.METADATA);
        }
        
        @Test
        @DisplayName("Should have correct value for configuration cache TTL (1 hour)")
        void shouldHaveCorrectValueForConfigurationCacheTTL() {
            // Verify that the configuration cache TTL is set to 1 hour (in seconds)
            assertEquals(60 * 60, Constants.CacheTTL.CONFIGURATION);
        }
    }
    
    @Nested
    @DisplayName("Queue Name Constants Tests")
    class QueueNameTests {
        
        @Test
        @DisplayName("Should define all required exchange name constants")
        void shouldDefineAllRequiredExchangeNameConstants() {
            // Verify all required exchange name constants are defined
            assertNotNull(Constants.QueueName.DOCUMENTS_EXCHANGE);
        }
        
        @Test
        @DisplayName("Should define all required queue name constants")
        void shouldDefineAllRequiredQueueNameConstants() {
            // Verify all required queue name constants are defined
            assertNotNull(Constants.QueueName.DOCUMENT_PROCESSING);
            assertNotNull(Constants.QueueName.DATA_EXTRACTION);
            assertNotNull(Constants.QueueName.NOTIFICATION);
        }
        
        @Test
        @DisplayName("Should define all required routing key constants")
        void shouldDefineAllRequiredRoutingKeyConstants() {
            // Verify all required routing key constants are defined
            assertNotNull(Constants.QueueName.DOCUMENT_NEW);
            assertNotNull(Constants.QueueName.OCR_REQUEST);
            assertNotNull(Constants.QueueName.DATA_PROCESSING);
        }
        
        @Test
        @DisplayName("Should have correct value for documents exchange name")
        void shouldHaveCorrectValueForDocumentsExchangeName() {
            // Verify that the documents exchange name is correct
            assertEquals("mca.documents", Constants.QueueName.DOCUMENTS_EXCHANGE);
        }
        
        @Test
        @DisplayName("Should have correct values for queue names")
        void shouldHaveCorrectValuesForQueueNames() {
            // Verify that the queue names are correct
            assertEquals("document-processing", Constants.QueueName.DOCUMENT_PROCESSING);
            assertEquals("data-extraction", Constants.QueueName.DATA_EXTRACTION);
            assertEquals("notification", Constants.QueueName.NOTIFICATION);
        }
        
        @Test
        @DisplayName("Should have correct values for routing keys")
        void shouldHaveCorrectValuesForRoutingKeys() {
            // Verify that the routing keys are correct
            assertEquals("document.new", Constants.QueueName.DOCUMENT_NEW);
            assertEquals("ocr.request", Constants.QueueName.OCR_REQUEST);
            assertEquals("data.processing", Constants.QueueName.DATA_PROCESSING);
        }
        
        @Test
        @DisplayName("Should have unique values for all queue-related constants")
        void shouldHaveUniqueValuesForAllQueueRelatedConstants() {
            // Collect all queue-related constants
            List<String> queueValues = Arrays.asList(
                Constants.QueueName.DOCUMENTS_EXCHANGE,
                Constants.QueueName.DOCUMENT_PROCESSING,
                Constants.QueueName.DATA_EXTRACTION,
                Constants.QueueName.NOTIFICATION,
                Constants.QueueName.DOCUMENT_NEW,
                Constants.QueueName.OCR_REQUEST,
                Constants.QueueName.DATA_PROCESSING
            );
            
            // Verify that all values are unique
            assertEquals(queueValues.size(), queueValues.stream().distinct().count(),
                    "All queue-related constants should have unique values");
        }
    }
    
    @Nested
    @DisplayName("Security Constants Tests")
    class SecurityConstantsTests {
        
        @Test
        @DisplayName("Should define all required encryption algorithm constants")
        void shouldDefineAllRequiredEncryptionAlgorithmConstants() {
            // Verify all required encryption algorithm constants are defined
            assertNotNull(Constants.SecurityConstants.ENCRYPTION_ALGORITHM);
            assertTrue(Constants.SecurityConstants.AES_KEY_SIZE > 0);
            assertTrue(Constants.SecurityConstants.GCM_IV_LENGTH > 0);
            assertTrue(Constants.SecurityConstants.GCM_TAG_LENGTH > 0);
        }
        
        @Test
        @DisplayName("Should define all required JWT authentication constants")
        void shouldDefineAllRequiredJwtAuthenticationConstants() {
            // Verify all required JWT authentication constants are defined
            assertNotNull(Constants.SecurityConstants.JWT_ALGORITHM);
            assertTrue(Constants.SecurityConstants.JWT_EXPIRY > 0);
            assertTrue(Constants.SecurityConstants.REFRESH_TOKEN_EXPIRY > 0);
        }
        
        @Test
        @DisplayName("Should define PII field names that require encryption")
        void shouldDefinePiiFieldNamesThatRequireEncryption() {
            // Verify that PII field names are defined
            assertNotNull(Constants.SecurityConstants.PII_FIELDS);
            assertTrue(Constants.SecurityConstants.PII_FIELDS.length > 0);
        }
        
        @Test
        @DisplayName("Should have correct value for encryption algorithm")
        void shouldHaveCorrectValueForEncryptionAlgorithm() {
            // Verify that the encryption algorithm is correct
            assertEquals("AES/GCM/NoPadding", Constants.SecurityConstants.ENCRYPTION_ALGORITHM);
        }
        
        @Test
        @DisplayName("Should have correct value for AES key size (256 bits)")
        void shouldHaveCorrectValueForAesKeySize() {
            // Verify that the AES key size is 256 bits
            assertEquals(256, Constants.SecurityConstants.AES_KEY_SIZE);
        }
        
        @Test
        @DisplayName("Should have correct value for GCM IV length (12 bytes)")
        void shouldHaveCorrectValueForGcmIvLength() {
            // Verify that the GCM IV length is 12 bytes
            assertEquals(12, Constants.SecurityConstants.GCM_IV_LENGTH);
        }
        
        @Test
        @DisplayName("Should have correct value for GCM tag length (16 bytes)")
        void shouldHaveCorrectValueForGcmTagLength() {
            // Verify that the GCM tag length is 16 bytes
            assertEquals(16, Constants.SecurityConstants.GCM_TAG_LENGTH);
        }
        
        @Test
        @DisplayName("Should have correct value for JWT algorithm (RS256)")
        void shouldHaveCorrectValueForJwtAlgorithm() {
            // Verify that the JWT algorithm is RS256
            assertEquals("RS256", Constants.SecurityConstants.JWT_ALGORITHM);
        }
        
        @Test
        @DisplayName("Should have correct value for JWT expiry (60 minutes)")
        void shouldHaveCorrectValueForJwtExpiry() {
            // Verify that the JWT expiry is 60 minutes
            assertEquals(60, Constants.SecurityConstants.JWT_EXPIRY);
        }
        
        @Test
        @DisplayName("Should have correct value for refresh token expiry (7 days in minutes)")
        void shouldHaveCorrectValueForRefreshTokenExpiry() {
            // Verify that the refresh token expiry is 7 days in minutes
            assertEquals(7 * 24 * 60, Constants.SecurityConstants.REFRESH_TOKEN_EXPIRY);
        }
        
        @Test
        @DisplayName("Should include essential PII fields that require encryption")
        void shouldIncludeEssentialPiiFieldsThatRequireEncryption() {
            // Verify that essential PII fields are included
            List<String> piiFields = Arrays.asList(Constants.SecurityConstants.PII_FIELDS);
            assertTrue(piiFields.contains("ssn"));
            assertTrue(piiFields.contains("ein"));
            assertTrue(piiFields.contains("driverLicense"));
            assertTrue(piiFields.contains("passportNumber"));
            assertTrue(piiFields.contains("bankAccountNumber"));
        }
    }
    
    @Nested
    @DisplayName("Business Rule Constants Tests")
    class BusinessRuleTests {
        
        @Test
        @DisplayName("Should define all required processing time constants")
        void shouldDefineAllRequiredProcessingTimeConstants() {
            // Verify all required processing time constants are defined
            assertTrue(Constants.BusinessRule.MAX_PROCESSING_TIME > 0);
        }
        
        @Test
        @DisplayName("Should define all required automation rate constants")
        void shouldDefineAllRequiredAutomationRateConstants() {
            // Verify all required automation rate constants are defined
            assertTrue(Constants.BusinessRule.AUTOMATION_RATE_TARGET > 0);
        }
        
        @Test
        @DisplayName("Should define all required data extraction accuracy constants")
        void shouldDefineAllRequiredDataExtractionAccuracyConstants() {
            // Verify all required data extraction accuracy constants are defined
            assertTrue(Constants.BusinessRule.DATA_EXTRACTION_ACCURACY > 0);
        }
        
        @Test
        @DisplayName("Should define all required OCR confidence threshold constants")
        void shouldDefineAllRequiredOcrConfidenceThresholdConstants() {
            // Verify all required OCR confidence threshold constants are defined
            assertTrue(Constants.BusinessRule.OCR_HIGH_CONFIDENCE > 0);
            assertTrue(Constants.BusinessRule.OCR_LOW_CONFIDENCE > 0);
        }
        
        @Test
        @DisplayName("Should define all required document classification confidence threshold constants")
        void shouldDefineAllRequiredDocumentClassificationConfidenceThresholdConstants() {
            // Verify all required document classification confidence threshold constants are defined
            assertTrue(Constants.BusinessRule.CLASSIFICATION_CONFIDENCE > 0);
        }
        
        @Test
        @DisplayName("Should have correct value for maximum processing time (5 minutes)")
        void shouldHaveCorrectValueForMaximumProcessingTime() {
            // Verify that the maximum processing time is 5 minutes
            assertEquals(5, Constants.BusinessRule.MAX_PROCESSING_TIME);
        }
        
        @Test
        @DisplayName("Should have correct value for automation rate target (93%)")
        void shouldHaveCorrectValueForAutomationRateTarget() {
            // Verify that the automation rate target is 93%
            assertEquals(0.93, Constants.BusinessRule.AUTOMATION_RATE_TARGET, 0.001);
        }
        
        @Test
        @DisplayName("Should have correct value for data extraction accuracy (99%)")
        void shouldHaveCorrectValueForDataExtractionAccuracy() {
            // Verify that the data extraction accuracy is 99%
            assertEquals(0.99, Constants.BusinessRule.DATA_EXTRACTION_ACCURACY, 0.001);
        }
        
        @Test
        @DisplayName("Should have correct value for OCR high confidence threshold (75%)")
        void shouldHaveCorrectValueForOcrHighConfidenceThreshold() {
            // Verify that the OCR high confidence threshold is 75%
            assertEquals(0.75, Constants.BusinessRule.OCR_HIGH_CONFIDENCE, 0.001);
        }
        
        @Test
        @DisplayName("Should have correct value for OCR low confidence threshold (50%)")
        void shouldHaveCorrectValueForOcrLowConfidenceThreshold() {
            // Verify that the OCR low confidence threshold is 50%
            assertEquals(0.50, Constants.BusinessRule.OCR_LOW_CONFIDENCE, 0.001);
        }
        
        @Test
        @DisplayName("Should have correct value for document classification confidence threshold (75%)")
        void shouldHaveCorrectValueForDocumentClassificationConfidenceThreshold() {
            // Verify that the document classification confidence threshold is 75%
            assertEquals(0.75, Constants.BusinessRule.CLASSIFICATION_CONFIDENCE, 0.001);
        }
        
        @Test
        @DisplayName("Should have OCR high confidence threshold greater than low confidence threshold")
        void shouldHaveOcrHighConfidenceThresholdGreaterThanLowConfidenceThreshold() {
            // Verify that the OCR high confidence threshold is greater than the low confidence threshold
            assertTrue(Constants.BusinessRule.OCR_HIGH_CONFIDENCE > Constants.BusinessRule.OCR_LOW_CONFIDENCE);
        }
    }
    
    @Nested
    @DisplayName("API Endpoint Constants Tests")
    class ApiEndpointTests {
        
        @Test
        @DisplayName("Should define API base path constant")
        void shouldDefineApiBasePathConstant() {
            // Verify that the API base path constant is defined
            assertNotNull(Constants.ApiEndpoint.API_BASE);
        }
        
        @Test
        @DisplayName("Should define all required application endpoint constants")
        void shouldDefineAllRequiredApplicationEndpointConstants() {
            // Verify all required application endpoint constants are defined
            assertNotNull(Constants.ApiEndpoint.APPLICATIONS);
            assertNotNull(Constants.ApiEndpoint.APPLICATION_BY_ID);
            assertNotNull(Constants.ApiEndpoint.APPLICATION_STATUS);
        }
        
        @Test
        @DisplayName("Should define all required document endpoint constants")
        void shouldDefineAllRequiredDocumentEndpointConstants() {
            // Verify all required document endpoint constants are defined
            assertNotNull(Constants.ApiEndpoint.DOCUMENTS);
            assertNotNull(Constants.ApiEndpoint.DOCUMENT_BY_ID);
            assertNotNull(Constants.ApiEndpoint.DOCUMENTS_BY_APPLICATION);
        }
        
        @Test
        @DisplayName("Should define all required webhook endpoint constants")
        void shouldDefineAllRequiredWebhookEndpointConstants() {
            // Verify all required webhook endpoint constants are defined
            assertNotNull(Constants.ApiEndpoint.WEBHOOKS);
            assertNotNull(Constants.ApiEndpoint.WEBHOOK_BY_ID);
            assertNotNull(Constants.ApiEndpoint.WEBHOOK_TEST);
        }
        
        @Test
        @DisplayName("Should have correct value for API base path")
        void shouldHaveCorrectValueForApiBasePath() {
            // Verify that the API base path is correct
            assertEquals("/api/v1", Constants.ApiEndpoint.API_BASE);
        }
        
        @Test
        @DisplayName("Should have correct values for application endpoints")
        void shouldHaveCorrectValuesForApplicationEndpoints() {
            // Verify that the application endpoints are correct
            assertEquals("/api/v1/applications", Constants.ApiEndpoint.APPLICATIONS);
            assertEquals("/api/v1/applications/{id}", Constants.ApiEndpoint.APPLICATION_BY_ID);
            assertEquals("/api/v1/applications/{id}/status", Constants.ApiEndpoint.APPLICATION_STATUS);
        }
        
        @Test
        @DisplayName("Should have correct values for document endpoints")
        void shouldHaveCorrectValuesForDocumentEndpoints() {
            // Verify that the document endpoints are correct
            assertEquals("/api/v1/documents", Constants.ApiEndpoint.DOCUMENTS);
            assertEquals("/api/v1/documents/{id}", Constants.ApiEndpoint.DOCUMENT_BY_ID);
            assertEquals("/api/v1/applications/{id}/documents", Constants.ApiEndpoint.DOCUMENTS_BY_APPLICATION);
        }
        
        @Test
        @DisplayName("Should have correct values for webhook endpoints")
        void shouldHaveCorrectValuesForWebhookEndpoints() {
            // Verify that the webhook endpoints are correct
            assertEquals("/api/v1/webhooks", Constants.ApiEndpoint.WEBHOOKS);
            assertEquals("/api/v1/webhooks/{id}", Constants.ApiEndpoint.WEBHOOK_BY_ID);
            assertEquals("/api/v1/webhooks/{id}/test", Constants.ApiEndpoint.WEBHOOK_TEST);
        }
        
        @Test
        @DisplayName("Should have application endpoints that start with API base path")
        void shouldHaveApplicationEndpointsThatStartWithApiBasePath() {
            // Verify that all application endpoints start with the API base path
            assertTrue(Constants.ApiEndpoint.APPLICATIONS.startsWith(Constants.ApiEndpoint.API_BASE));
            assertTrue(Constants.ApiEndpoint.APPLICATION_BY_ID.startsWith(Constants.ApiEndpoint.API_BASE));
            assertTrue(Constants.ApiEndpoint.APPLICATION_STATUS.startsWith(Constants.ApiEndpoint.API_BASE));
        }
        
        @Test
        @DisplayName("Should have document endpoints that start with API base path")
        void shouldHaveDocumentEndpointsThatStartWithApiBasePath() {
            // Verify that all document endpoints start with the API base path
            assertTrue(Constants.ApiEndpoint.DOCUMENTS.startsWith(Constants.ApiEndpoint.API_BASE));
            assertTrue(Constants.ApiEndpoint.DOCUMENT_BY_ID.startsWith(Constants.ApiEndpoint.API_BASE));
            assertTrue(Constants.ApiEndpoint.DOCUMENTS_BY_APPLICATION.startsWith(Constants.ApiEndpoint.API_BASE));
        }
        
        @Test
        @DisplayName("Should have webhook endpoints that start with API base path")
        void shouldHaveWebhookEndpointsThatStartWithApiBasePath() {
            // Verify that all webhook endpoints start with the API base path
            assertTrue(Constants.ApiEndpoint.WEBHOOKS.startsWith(Constants.ApiEndpoint.API_BASE));
            assertTrue(Constants.ApiEndpoint.WEBHOOK_BY_ID.startsWith(Constants.ApiEndpoint.API_BASE));
            assertTrue(Constants.ApiEndpoint.WEBHOOK_TEST.startsWith(Constants.ApiEndpoint.API_BASE));
        }
    }
    
    @Nested
    @DisplayName("Config Key Constants Tests")
    class ConfigKeyTests {
        
        @Test
        @DisplayName("Should define all required database configuration constants")
        void shouldDefineAllRequiredDatabaseConfigurationConstants() {
            // Verify all required database configuration constants are defined
            assertNotNull(Constants.ConfigKey.DB_PRIMARY_URL);
            assertNotNull(Constants.ConfigKey.DB_USERNAME);
            assertNotNull(Constants.ConfigKey.DB_PASSWORD);
        }
        
        @Test
        @DisplayName("Should define all required Redis configuration constants")
        void shouldDefineAllRequiredRedisConfigurationConstants() {
            // Verify all required Redis configuration constants are defined
            assertNotNull(Constants.ConfigKey.REDIS_HOST);
            assertNotNull(Constants.ConfigKey.REDIS_PORT);
        }
        
        @Test
        @DisplayName("Should define all required RabbitMQ configuration constants")
        void shouldDefineAllRequiredRabbitMQConfigurationConstants() {
            // Verify all required RabbitMQ configuration constants are defined
            assertNotNull(Constants.ConfigKey.RABBITMQ_HOST);
            assertNotNull(Constants.ConfigKey.RABBITMQ_PORT);
            assertNotNull(Constants.ConfigKey.RABBITMQ_USERNAME);
            assertNotNull(Constants.ConfigKey.RABBITMQ_PASSWORD);
        }
        
        @Test
        @DisplayName("Should define all required S3 configuration constants")
        void shouldDefineAllRequiredS3ConfigurationConstants() {
            // Verify all required S3 configuration constants are defined
            assertNotNull(Constants.ConfigKey.S3_ENDPOINT);
            assertNotNull(Constants.ConfigKey.S3_REGION);
            assertNotNull(Constants.ConfigKey.S3_BUCKET);
        }
        
        @Test
        @DisplayName("Should define all required security configuration constants")
        void shouldDefineAllRequiredSecurityConfigurationConstants() {
            // Verify all required security configuration constants are defined
            assertNotNull(Constants.ConfigKey.ENCRYPTION_KEY);
            assertNotNull(Constants.ConfigKey.JWT_PUBLIC_KEY);
            assertNotNull(Constants.ConfigKey.JWT_PRIVATE_KEY);
        }
        
        @Test
        @DisplayName("Should have correct values for database configuration constants")
        void shouldHaveCorrectValuesForDatabaseConfigurationConstants() {
            // Verify that the database configuration constants are correct
            assertEquals("spring.datasource.url", Constants.ConfigKey.DB_PRIMARY_URL);
            assertEquals("spring.datasource.username", Constants.ConfigKey.DB_USERNAME);
            assertEquals("spring.datasource.password", Constants.ConfigKey.DB_PASSWORD);
        }
        
        @Test
        @DisplayName("Should have correct values for Redis configuration constants")
        void shouldHaveCorrectValuesForRedisConfigurationConstants() {
            // Verify that the Redis configuration constants are correct
            assertEquals("spring.redis.host", Constants.ConfigKey.REDIS_HOST);
            assertEquals("spring.redis.port", Constants.ConfigKey.REDIS_PORT);
        }
        
        @Test
        @DisplayName("Should have correct values for RabbitMQ configuration constants")
        void shouldHaveCorrectValuesForRabbitMQConfigurationConstants() {
            // Verify that the RabbitMQ configuration constants are correct
            assertEquals("spring.rabbitmq.host", Constants.ConfigKey.RABBITMQ_HOST);
            assertEquals("spring.rabbitmq.port", Constants.ConfigKey.RABBITMQ_PORT);
            assertEquals("spring.rabbitmq.username", Constants.ConfigKey.RABBITMQ_USERNAME);
            assertEquals("spring.rabbitmq.password", Constants.ConfigKey.RABBITMQ_PASSWORD);
        }
        
        @Test
        @DisplayName("Should have correct values for S3 configuration constants")
        void shouldHaveCorrectValuesForS3ConfigurationConstants() {
            // Verify that the S3 configuration constants are correct
            assertEquals("aws.s3.endpoint", Constants.ConfigKey.S3_ENDPOINT);
            assertEquals("aws.s3.region", Constants.ConfigKey.S3_REGION);
            assertEquals("aws.s3.bucket", Constants.ConfigKey.S3_BUCKET);
        }
        
        @Test
        @DisplayName("Should have correct values for security configuration constants")
        void shouldHaveCorrectValuesForSecurityConfigurationConstants() {
            // Verify that the security configuration constants are correct
            assertEquals("security.encryption.key", Constants.ConfigKey.ENCRYPTION_KEY);
            assertEquals("security.jwt.public-key", Constants.ConfigKey.JWT_PUBLIC_KEY);
            assertEquals("security.jwt.private-key", Constants.ConfigKey.JWT_PRIVATE_KEY);
        }
        
        @Test
        @DisplayName("Should have unique values for all configuration key constants")
        void shouldHaveUniqueValuesForAllConfigurationKeyConstants() {
            // Collect all configuration key constants
            List<String> configKeyValues = Arrays.asList(
                Constants.ConfigKey.DB_PRIMARY_URL,
                Constants.ConfigKey.DB_USERNAME,
                Constants.ConfigKey.DB_PASSWORD,
                Constants.ConfigKey.REDIS_HOST,
                Constants.ConfigKey.REDIS_PORT,
                Constants.ConfigKey.RABBITMQ_HOST,
                Constants.ConfigKey.RABBITMQ_PORT,
                Constants.ConfigKey.RABBITMQ_USERNAME,
                Constants.ConfigKey.RABBITMQ_PASSWORD,
                Constants.ConfigKey.S3_ENDPOINT,
                Constants.ConfigKey.S3_REGION,
                Constants.ConfigKey.S3_BUCKET,
                Constants.ConfigKey.ENCRYPTION_KEY,
                Constants.ConfigKey.JWT_PUBLIC_KEY,
                Constants.ConfigKey.JWT_PRIVATE_KEY
            );
            
            // Verify that all values are unique
            assertEquals(configKeyValues.size(), configKeyValues.stream().distinct().count(),
                    "All configuration key constants should have unique values");
        }
    }
}