package com.dollarfunding.mca.util;

import com.dollarfunding.mca.exception.AuthorizationException;
import com.dollarfunding.mca.exception.BaseException;
import com.dollarfunding.mca.exception.BusinessRuleException;
import com.dollarfunding.mca.exception.DocumentProcessingException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.exception.WebhookDeliveryException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.slf4j.Logger;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link ErrorUtil} class.
 * 
 * Tests verify error message extraction, error normalization, error logging,
 * API error response generation, retry determination, error message sanitization,
 * validation error building, and error categorization.
 */
@DisplayName("ErrorUtil Tests")
class ErrorUtilTest {

    /**
     * Tests for the getErrorMessage method.
     */
    @Nested
    @DisplayName("getErrorMessage() Tests")
    class GetErrorMessageTests {
        
        @Test
        @DisplayName("Should extract message from RuntimeException")
        void shouldExtractMessageFromRuntimeException() {
            // Arrange
            String errorMessage = "Test error message";
            RuntimeException exception = new RuntimeException(errorMessage);
            
            // Act
            String result = ErrorUtil.getErrorMessage(exception);
            
            // Assert
            assertEquals(errorMessage, result, "Should extract the correct message from RuntimeException");
        }
        
        @Test
        @DisplayName("Should extract message from BaseException")
        void shouldExtractMessageFromBaseException() {
            // Arrange
            String errorMessage = "Business rule violated";
            BaseException exception = new BusinessRuleException("RULE_VIOLATED", errorMessage);
            
            // Act
            String result = ErrorUtil.getErrorMessage(exception);
            
            // Assert
            assertEquals(errorMessage, result, "Should extract the correct message from BaseException");
        }
        
        @Test
        @DisplayName("Should extract message from HttpClientErrorException")
        void shouldExtractMessageFromHttpClientErrorException() {
            // Arrange
            HttpClientErrorException exception = HttpClientErrorException.create(
                    HttpStatus.BAD_REQUEST, "Bad Request", null, null, null);
            
            // Act
            String result = ErrorUtil.getErrorMessage(exception);
            
            // Assert
            assertEquals("400 BAD_REQUEST: Bad Request", result, 
                    "Should format message with status code and text");
        }
        
        @Test
        @DisplayName("Should extract message from HttpServerErrorException")
        void shouldExtractMessageFromHttpServerErrorException() {
            // Arrange
            HttpServerErrorException exception = HttpServerErrorException.create(
                    HttpStatus.INTERNAL_SERVER_ERROR, "Internal Server Error", null, null, null);
            
            // Act
            String result = ErrorUtil.getErrorMessage(exception);
            
            // Assert
            assertEquals("500 INTERNAL_SERVER_ERROR: Internal Server Error", result, 
                    "Should format message with status code and text");
        }
        
        @Test
        @DisplayName("Should extract message from nested cause when parent message is null")
        void shouldExtractMessageFromNestedCause() {
            // Arrange
            String causeMessage = "Root cause message";
            Exception cause = new IllegalArgumentException(causeMessage);
            Exception wrapper = new Exception(null, cause);
            
            // Act
            String result = ErrorUtil.getErrorMessage(wrapper);
            
            // Assert
            assertEquals(causeMessage, result, "Should extract message from the cause");
        }
        
        @Test
        @DisplayName("Should return class name when message is null")
        void shouldReturnClassNameWhenMessageIsNull() {
            // Arrange
            Exception exception = new NullPointerException();
            
            // Act
            String result = ErrorUtil.getErrorMessage(exception);
            
            // Assert
            assertEquals("NullPointerException", result, "Should return the exception class name");
        }
        
        @Test
        @DisplayName("Should handle null exception")
        void shouldHandleNullException() {
            // Act
            String result = ErrorUtil.getErrorMessage(null);
            
            // Assert
            assertEquals("Unknown error occurred", result, "Should return unknown error message");
        }
    }
    
    /**
     * Tests for the normalizeError method.
     */
    @Nested
    @DisplayName("normalizeError() Tests")
    class NormalizeErrorTests {
        
        @Test
        @DisplayName("Should normalize BaseException with correct fields")
        void shouldNormalizeBaseException() {
            // Arrange
            String errorCode = "BUSINESS_RULE_VIOLATED";
            String errorMessage = "Business rule violated";
            BusinessRuleException exception = new BusinessRuleException(errorCode, errorMessage);
            
            // Act
            Map<String, Object> result = ErrorUtil.normalizeError(exception);
            
            // Assert
            assertNotNull(result, "Result should not be null");
            assertEquals(errorMessage, result.get("message"), "Message should match");
            assertEquals(errorCode, result.get("code"), "Error code should match");
            assertEquals(HttpStatus.UNPROCESSABLE_ENTITY.value(), result.get("status"), "Status should match");
            assertEquals("BusinessRuleException", result.get("type"), "Type should match");
            assertNotNull(result.get("timestamp"), "Timestamp should be present");
        }
        
        @Test
        @DisplayName("Should normalize RuntimeException with default values")
        void shouldNormalizeRuntimeException() {
            // Arrange
            String errorMessage = "Runtime error";
            RuntimeException exception = new RuntimeException(errorMessage);
            
            // Act
            Map<String, Object> result = ErrorUtil.normalizeError(exception);
            
            // Assert
            assertNotNull(result, "Result should not be null");
            assertEquals(errorMessage, result.get("message"), "Message should match");
            assertEquals("INTERNAL_ERROR", result.get("code"), "Default error code should be used");
            assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), result.get("status"), 
                    "Default status should be used");
            assertEquals("RuntimeException", result.get("type"), "Type should match");
            assertNotNull(result.get("timestamp"), "Timestamp should be present");
        }
        
        @Test
        @DisplayName("Should include validation errors for ValidationException")
        void shouldIncludeValidationErrors() {
            // Arrange
            Map<String, String> validationErrors = Map.of(
                    "field1", "Field 1 is required",
                    "field2", "Field 2 must be a valid email"
            );
            ValidationException exception = new ValidationException("Validation failed", validationErrors);
            
            // Act
            Map<String, Object> result = ErrorUtil.normalizeError(exception);
            
            // Assert
            assertNotNull(result, "Result should not be null");
            assertEquals("Validation failed", result.get("message"), "Message should match");
            assertEquals(validationErrors, result.get("validationErrors"), "Validation errors should be included");
        }
        
        @Test
        @DisplayName("Should sanitize error messages in normalized error")
        void shouldSanitizeErrorMessages() {
            // Arrange
            String errorWithSensitiveInfo = "Error processing credit card 4111-1111-1111-1111";
            RuntimeException exception = new RuntimeException(errorWithSensitiveInfo);
            
            // Act
            Map<String, Object> result = ErrorUtil.normalizeError(exception);
            
            // Assert
            assertNotNull(result, "Result should not be null");
            assertEquals("Error processing credit card [REDACTED_CC]", result.get("message"), 
                    "Message should be sanitized");
        }
    }
    
    /**
     * Tests for the logError method.
     */
    @Nested
    @DisplayName("logError() Tests")
    class LogErrorTests {
        
        private Logger mockLogger;
        private MockedStatic<org.slf4j.LoggerFactory> mockedLoggerFactory;
        
        @BeforeEach
        void setUp() {
            mockLogger = mock(Logger.class);
            mockedLoggerFactory = mockStatic(org.slf4j.LoggerFactory.class);
            mockedLoggerFactory.when(() -> org.slf4j.LoggerFactory.getLogger(ErrorUtil.class))
                    .thenReturn(mockLogger);
        }
        
        @Test
        @DisplayName("Should log ResourceNotFoundException at INFO level")
        void shouldLogResourceNotFoundAtInfoLevel() {
            // Arrange
            ResourceNotFoundException exception = new ResourceNotFoundException("application", "123");
            String context = "Retrieving application";
            
            // Act
            ErrorUtil.logError(exception, context);
            
            // Assert
            verify(mockLogger).info("Retrieving application: Application with ID 123 not found");
            verify(mockLogger, never()).warn(anyString());
            verify(mockLogger, never()).error(anyString(), any(Throwable.class));
        }
        
        @Test
        @DisplayName("Should log ValidationException at WARN level")
        void shouldLogValidationExceptionAtWarnLevel() {
            // Arrange
            ValidationException exception = new ValidationException("Validation failed");
            String context = "Processing request";
            
            // Act
            ErrorUtil.logError(exception, context);
            
            // Assert
            verify(mockLogger).warn("Processing request: Validation failed");
            verify(mockLogger, never()).info(anyString());
            verify(mockLogger, never()).error(anyString(), any(Throwable.class));
        }
        
        @Test
        @DisplayName("Should log BusinessRuleException at WARN level")
        void shouldLogBusinessRuleExceptionAtWarnLevel() {
            // Arrange
            BusinessRuleException exception = new BusinessRuleException("RULE_VIOLATED", "Business rule violated");
            String context = "Processing application";
            
            // Act
            ErrorUtil.logError(exception, context);
            
            // Assert
            verify(mockLogger).warn("Processing application: Business rule violated");
            verify(mockLogger, never()).info(anyString());
            verify(mockLogger, never()).error(anyString(), any(Throwable.class));
        }
        
        @Test
        @DisplayName("Should log AuthorizationException at WARN level with stack trace")
        void shouldLogAuthorizationExceptionAtWarnLevelWithStackTrace() {
            // Arrange
            AuthorizationException exception = new AuthorizationException("Insufficient permissions");
            String context = "Accessing resource";
            
            // Act
            ErrorUtil.logError(exception, context);
            
            // Assert
            verify(mockLogger).warn("Accessing resource: Insufficient permissions", exception);
            verify(mockLogger, never()).info(anyString());
            verify(mockLogger, never()).error(anyString(), any(Throwable.class));
        }
        
        @Test
        @DisplayName("Should log other exceptions at ERROR level with stack trace")
        void shouldLogOtherExceptionsAtErrorLevelWithStackTrace() {
            // Arrange
            RuntimeException exception = new RuntimeException("Unexpected error");
            String context = "Processing request";
            
            // Act
            ErrorUtil.logError(exception, context);
            
            // Assert
            verify(mockLogger).error("Processing request: Unexpected error", exception);
            verify(mockLogger, never()).info(anyString());
            verify(mockLogger, never()).warn(anyString());
            verify(mockLogger, never()).warn(anyString(), any(Throwable.class));
        }
    }
    
    /**
     * Tests for the createApiError method.
     */
    @Nested
    @DisplayName("createApiError() Tests")
    class CreateApiErrorTests {
        
        @Test
        @DisplayName("Should create API error response with correct status for BaseException")
        void shouldCreateApiErrorResponseForBaseException() {
            // Arrange
            ValidationException exception = new ValidationException("Validation failed");
            
            // Act
            ResponseEntity<Map<String, Object>> response = ErrorUtil.createApiError(exception);
            
            // Assert
            assertNotNull(response, "Response should not be null");
            assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode(), "Status code should match");
            assertNotNull(response.getBody(), "Response body should not be null");
            assertEquals("Validation failed", response.getBody().get("message"), "Message should match");
        }
        
        @Test
        @DisplayName("Should create API error response with correct status for HttpClientErrorException")
        void shouldCreateApiErrorResponseForHttpClientErrorException() {
            // Arrange
            HttpClientErrorException exception = HttpClientErrorException.create(
                    HttpStatus.UNAUTHORIZED, "Unauthorized", null, null, null);
            
            // Act
            ResponseEntity<Map<String, Object>> response = ErrorUtil.createApiError(exception);
            
            // Assert
            assertNotNull(response, "Response should not be null");
            assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode(), "Status code should match");
            assertNotNull(response.getBody(), "Response body should not be null");
            assertEquals("401 UNAUTHORIZED: Unauthorized", response.getBody().get("message"), 
                    "Message should match");
        }
        
        @Test
        @DisplayName("Should create API error response with correct status for HttpServerErrorException")
        void shouldCreateApiErrorResponseForHttpServerErrorException() {
            // Arrange
            HttpServerErrorException exception = HttpServerErrorException.create(
                    HttpStatus.SERVICE_UNAVAILABLE, "Service Unavailable", null, null, null);
            
            // Act
            ResponseEntity<Map<String, Object>> response = ErrorUtil.createApiError(exception);
            
            // Assert
            assertNotNull(response, "Response should not be null");
            assertEquals(HttpStatus.SERVICE_UNAVAILABLE, response.getStatusCode(), "Status code should match");
            assertNotNull(response.getBody(), "Response body should not be null");
            assertEquals("503 SERVICE_UNAVAILABLE: Service Unavailable", response.getBody().get("message"), 
                    "Message should match");
        }
        
        @Test
        @DisplayName("Should create API error response with 500 status for other exceptions")
        void shouldCreateApiErrorResponseForOtherExceptions() {
            // Arrange
            RuntimeException exception = new RuntimeException("Unexpected error");
            
            // Act
            ResponseEntity<Map<String, Object>> response = ErrorUtil.createApiError(exception);
            
            // Assert
            assertNotNull(response, "Response should not be null");
            assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode(), "Status code should match");
            assertNotNull(response.getBody(), "Response body should not be null");
            assertEquals("Unexpected error", response.getBody().get("message"), "Message should match");
        }
    }
    
    /**
     * Tests for the isRetryableError method.
     */
    @Nested
    @DisplayName("isRetryableError() Tests")
    class IsRetryableErrorTests {
        
        @Test
        @DisplayName("Should identify ConnectException as retryable")
        void shouldIdentifyConnectExceptionAsRetryable() {
            // Arrange
            ConnectException exception = new ConnectException("Connection refused");
            
            // Act
            boolean result = ErrorUtil.isRetryableError(exception);
            
            // Assert
            assertTrue(result, "ConnectException should be identified as retryable");
        }
        
        @Test
        @DisplayName("Should identify SocketTimeoutException as retryable")
        void shouldIdentifySocketTimeoutExceptionAsRetryable() {
            // Arrange
            SocketTimeoutException exception = new SocketTimeoutException("Read timed out");
            
            // Act
            boolean result = ErrorUtil.isRetryableError(exception);
            
            // Assert
            assertTrue(result, "SocketTimeoutException should be identified as retryable");
        }
        
        @Test
        @DisplayName("Should identify ResourceAccessException as retryable")
        void shouldIdentifyResourceAccessExceptionAsRetryable() {
            // Arrange
            ResourceAccessException exception = new ResourceAccessException("I/O error");
            
            // Act
            boolean result = ErrorUtil.isRetryableError(exception);
            
            // Assert
            assertTrue(result, "ResourceAccessException should be identified as retryable");
        }
        
        @Test
        @DisplayName("Should identify certain HTTP status codes as retryable")
        void shouldIdentifyCertainHttpStatusCodesAsRetryable() {
            // Arrange
            HttpServerErrorException serviceUnavailable = HttpServerErrorException.create(
                    HttpStatus.SERVICE_UNAVAILABLE, "Service Unavailable", null, null, null);
            HttpServerErrorException gatewayTimeout = HttpServerErrorException.create(
                    HttpStatus.GATEWAY_TIMEOUT, "Gateway Timeout", null, null, null);
            HttpServerErrorException tooManyRequests = HttpServerErrorException.create(
                    HttpStatus.TOO_MANY_REQUESTS, "Too Many Requests", null, null, null);
            HttpServerErrorException internalServerError = HttpServerErrorException.create(
                    HttpStatus.INTERNAL_SERVER_ERROR, "Internal Server Error", null, null, null);
            
            // Act & Assert
            assertTrue(ErrorUtil.isRetryableError(serviceUnavailable), 
                    "SERVICE_UNAVAILABLE should be retryable");
            assertTrue(ErrorUtil.isRetryableError(gatewayTimeout), 
                    "GATEWAY_TIMEOUT should be retryable");
            assertTrue(ErrorUtil.isRetryableError(tooManyRequests), 
                    "TOO_MANY_REQUESTS should be retryable");
            assertTrue(ErrorUtil.isRetryableError(internalServerError), 
                    "INTERNAL_SERVER_ERROR should be retryable");
        }
        
        @Test
        @DisplayName("Should identify errors with retryable message patterns")
        void shouldIdentifyErrorsWithRetryableMessagePatterns() {
            // Arrange
            Exception timeoutException = new Exception("Operation timed out");
            Exception connectionRefusedException = new Exception("Connection refused by host");
            Exception unavailableException = new Exception("Service temporarily unavailable");
            
            // Act & Assert
            assertTrue(ErrorUtil.isRetryableError(timeoutException), 
                    "Exception with 'timed out' message should be retryable");
            assertTrue(ErrorUtil.isRetryableError(connectionRefusedException), 
                    "Exception with 'connection refused' message should be retryable");
            assertTrue(ErrorUtil.isRetryableError(unavailableException), 
                    "Exception with 'temporarily unavailable' message should be retryable");
        }
        
        @Test
        @DisplayName("Should identify retryable errors in nested causes")
        void shouldIdentifyRetryableErrorsInNestedCauses() {
            // Arrange
            ConnectException cause = new ConnectException("Connection refused");
            Exception wrapper = new Exception("Wrapped error", cause);
            
            // Act
            boolean result = ErrorUtil.isRetryableError(wrapper);
            
            // Assert
            assertTrue(result, "Exception with retryable cause should be identified as retryable");
        }
        
        @Test
        @DisplayName("Should identify non-retryable errors")
        void shouldIdentifyNonRetryableErrors() {
            // Arrange
            ValidationException validationException = new ValidationException("Validation failed");
            ResourceNotFoundException notFoundException = new ResourceNotFoundException("application", "123");
            BusinessRuleException businessRuleException = new BusinessRuleException("RULE_VIOLATED", "Rule violated");
            
            // Act & Assert
            assertFalse(ErrorUtil.isRetryableError(validationException), 
                    "ValidationException should not be retryable");
            assertFalse(ErrorUtil.isRetryableError(notFoundException), 
                    "ResourceNotFoundException should not be retryable");
            assertFalse(ErrorUtil.isRetryableError(businessRuleException), 
                    "BusinessRuleException should not be retryable");
        }
        
        @Test
        @DisplayName("Should handle null error")
        void shouldHandleNullError() {
            // Act
            boolean result = ErrorUtil.isRetryableError(null);
            
            // Assert
            assertFalse(result, "Null error should not be identified as retryable");
        }
    }
    
    /**
     * Tests for the sanitizeErrorMessage method.
     */
    @Nested
    @DisplayName("sanitizeErrorMessage() Tests")
    class SanitizeErrorMessageTests {
        
        @Test
        @DisplayName("Should sanitize credit card numbers")
        void shouldSanitizeCreditCardNumbers() {
            // Arrange
            String messageWithCreditCard = "Error processing payment with card 4111-1111-1111-1111";
            String messageWithMultipleCards = "Cards 4111111111111111 and 5555555555554444 are invalid";
            
            // Act
            String sanitized1 = ErrorUtil.sanitizeErrorMessage(messageWithCreditCard);
            String sanitized2 = ErrorUtil.sanitizeErrorMessage(messageWithMultipleCards);
            
            // Assert
            assertEquals("Error processing payment with card [REDACTED_CC]", sanitized1, 
                    "Credit card number should be redacted");
            assertEquals("Cards [REDACTED_CC] and [REDACTED_CC] are invalid", sanitized2, 
                    "Multiple credit card numbers should be redacted");
        }
        
        @Test
        @DisplayName("Should sanitize Social Security Numbers")
        void shouldSanitizeSSNs() {
            // Arrange
            String messageWithSSN = "Error processing SSN 123-45-6789";
            String messageWithMultipleSSNs = "SSNs 123456789 and 987-65-4321 are invalid";
            
            // Act
            String sanitized1 = ErrorUtil.sanitizeErrorMessage(messageWithSSN);
            String sanitized2 = ErrorUtil.sanitizeErrorMessage(messageWithMultipleSSNs);
            
            // Assert
            assertEquals("Error processing SSN [REDACTED_SSN]", sanitized1, 
                    "SSN should be redacted");
            assertEquals("SSNs [REDACTED_SSN] and [REDACTED_SSN] are invalid", sanitized2, 
                    "Multiple SSNs should be redacted");
        }
        
        @Test
        @DisplayName("Should sanitize Employer Identification Numbers")
        void shouldSanitizeEINs() {
            // Arrange
            String messageWithEIN = "Error processing EIN 12-3456789";
            String messageWithMultipleEINs = "EINs 123456789 and 98-7654321 are invalid";
            
            // Act
            String sanitized1 = ErrorUtil.sanitizeErrorMessage(messageWithEIN);
            String sanitized2 = ErrorUtil.sanitizeErrorMessage(messageWithMultipleEINs);
            
            // Assert
            assertEquals("Error processing EIN [REDACTED_EIN]", sanitized1, 
                    "EIN should be redacted");
            assertEquals("EINs [REDACTED_EIN] and [REDACTED_EIN] are invalid", sanitized2, 
                    "Multiple EINs should be redacted");
        }
        
        @Test
        @DisplayName("Should sanitize email addresses")
        void shouldSanitizeEmails() {
            // Arrange
            String messageWithEmail = "Error sending email to user@example.com";
            String messageWithMultipleEmails = "Emails admin@example.com and support@example.org are invalid";
            
            // Act
            String sanitized1 = ErrorUtil.sanitizeErrorMessage(messageWithEmail);
            String sanitized2 = ErrorUtil.sanitizeErrorMessage(messageWithMultipleEmails);
            
            // Assert
            assertEquals("Error sending email to [REDACTED_EMAIL]", sanitized1, 
                    "Email should be redacted");
            assertEquals("Emails [REDACTED_EMAIL] and [REDACTED_EMAIL] are invalid", sanitized2, 
                    "Multiple emails should be redacted");
        }
        
        @Test
        @DisplayName("Should handle null message")
        void shouldHandleNullMessage() {
            // Act
            String result = ErrorUtil.sanitizeErrorMessage(null);
            
            // Assert
            assertEquals("", result, "Null message should return empty string");
        }
        
        @Test
        @DisplayName("Should not modify messages without sensitive information")
        void shouldNotModifyMessagesWithoutSensitiveInformation() {
            // Arrange
            String message = "General error occurred during processing";
            
            // Act
            String result = ErrorUtil.sanitizeErrorMessage(message);
            
            // Assert
            assertEquals(message, result, "Message without sensitive info should not be modified");
        }
    }
    
    /**
     * Tests for the buildValidationError method.
     */
    @Nested
    @DisplayName("buildValidationError() Tests")
    class BuildValidationErrorTests {
        
        @Test
        @DisplayName("Should build validation error map from BindingResult")
        void shouldBuildValidationErrorMap() {
            // Arrange
            BindingResult bindingResult = mock(BindingResult.class);
            List<FieldError> fieldErrors = new ArrayList<>();
            fieldErrors.add(new FieldError("object", "field1", "Field 1 is required"));
            fieldErrors.add(new FieldError("object", "field2", "Field 2 must be a valid email"));
            when(bindingResult.getFieldErrors()).thenReturn(fieldErrors);
            
            // Act
            Map<String, String> result = ErrorUtil.buildValidationError(bindingResult);
            
            // Assert
            assertNotNull(result, "Result should not be null");
            assertEquals(2, result.size(), "Result should contain 2 entries");
            assertEquals("Field 1 is required", result.get("field1"), "Error message for field1 should match");
            assertEquals("Field 2 must be a valid email", result.get("field2"), 
                    "Error message for field2 should match");
        }
        
        @Test
        @DisplayName("Should handle empty BindingResult")
        void shouldHandleEmptyBindingResult() {
            // Arrange
            BindingResult bindingResult = mock(BindingResult.class);
            when(bindingResult.getFieldErrors()).thenReturn(new ArrayList<>());
            
            // Act
            Map<String, String> result = ErrorUtil.buildValidationError(bindingResult);
            
            // Assert
            assertNotNull(result, "Result should not be null");
            assertTrue(result.isEmpty(), "Result should be empty");
        }
    }
    
    /**
     * Tests for the error categorization methods.
     */
    @Nested
    @DisplayName("Error Categorization Tests")
    class ErrorCategorizationTests {
        
        @Test
        @DisplayName("Should identify network errors correctly")
        void shouldIdentifyNetworkErrors() {
            // Arrange
            ConnectException connectException = new ConnectException("Connection refused");
            SocketTimeoutException timeoutException = new SocketTimeoutException("Read timed out");
            ResourceAccessException resourceException = new ResourceAccessException("I/O error");
            RuntimeException runtimeException = new RuntimeException("General error");
            
            // Act & Assert
            assertTrue(ErrorUtil.isNetworkError(connectException), 
                    "ConnectException should be identified as network error");
            assertTrue(ErrorUtil.isNetworkError(timeoutException), 
                    "SocketTimeoutException should be identified as network error");
            assertTrue(ErrorUtil.isNetworkError(resourceException), 
                    "ResourceAccessException should be identified as network error");
            assertFalse(ErrorUtil.isNetworkError(runtimeException), 
                    "RuntimeException should not be identified as network error");
        }
        
        @Test
        @DisplayName("Should identify authentication/authorization errors correctly")
        void shouldIdentifyAuthErrors() {
            // Arrange
            AuthorizationException authException = new AuthorizationException("Insufficient permissions");
            HttpClientErrorException unauthorizedException = HttpClientErrorException.create(
                    HttpStatus.UNAUTHORIZED, "Unauthorized", null, null, null);
            HttpClientErrorException forbiddenException = HttpClientErrorException.create(
                    HttpStatus.FORBIDDEN, "Forbidden", null, null, null);
            RuntimeException runtimeException = new RuntimeException("General error");
            
            // Act & Assert
            assertTrue(ErrorUtil.isAuthError(authException), 
                    "AuthorizationException should be identified as auth error");
            assertTrue(ErrorUtil.isAuthError(unauthorizedException), 
                    "UNAUTHORIZED exception should be identified as auth error");
            assertTrue(ErrorUtil.isAuthError(forbiddenException), 
                    "FORBIDDEN exception should be identified as auth error");
            assertFalse(ErrorUtil.isAuthError(runtimeException), 
                    "RuntimeException should not be identified as auth error");
        }
        
        @Test
        @DisplayName("Should identify validation errors correctly")
        void shouldIdentifyValidationErrors() {
            // Arrange
            ValidationException validationException = new ValidationException("Validation failed");
            HttpClientErrorException badRequestException = HttpClientErrorException.create(
                    HttpStatus.BAD_REQUEST, "Bad Request", null, null, null);
            RuntimeException runtimeException = new RuntimeException("General error");
            
            // Act & Assert
            assertTrue(ErrorUtil.isValidationError(validationException), 
                    "ValidationException should be identified as validation error");
            assertTrue(ErrorUtil.isValidationError(badRequestException), 
                    "BAD_REQUEST exception should be identified as validation error");
            assertFalse(ErrorUtil.isValidationError(runtimeException), 
                    "RuntimeException should not be identified as validation error");
        }
        
        @Test
        @DisplayName("Should identify business rule errors correctly")
        void shouldIdentifyBusinessRuleErrors() {
            // Arrange
            BusinessRuleException businessRuleException = new BusinessRuleException(
                    "RULE_VIOLATED", "Business rule violated");
            HttpClientErrorException unprocessableEntityException = HttpClientErrorException.create(
                    HttpStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", null, null, null);
            RuntimeException runtimeException = new RuntimeException("General error");
            
            // Act & Assert
            assertTrue(ErrorUtil.isBusinessRuleError(businessRuleException), 
                    "BusinessRuleException should be identified as business rule error");
            assertTrue(ErrorUtil.isBusinessRuleError(unprocessableEntityException), 
                    "UNPROCESSABLE_ENTITY exception should be identified as business rule error");
            assertFalse(ErrorUtil.isBusinessRuleError(runtimeException), 
                    "RuntimeException should not be identified as business rule error");
        }
        
        @Test
        @DisplayName("Should identify document errors correctly")
        void shouldIdentifyDocumentErrors() {
            // Arrange
            DocumentProcessingException documentException = new DocumentProcessingException(
                    "DOC_PROCESSING_ERROR", "Error processing document");
            RuntimeException runtimeException = new RuntimeException("General error");
            
            // Act & Assert
            assertTrue(ErrorUtil.isDocumentError(documentException), 
                    "DocumentProcessingException should be identified as document error");
            assertFalse(ErrorUtil.isDocumentError(runtimeException), 
                    "RuntimeException should not be identified as document error");
        }
        
        @Test
        @DisplayName("Should identify webhook errors correctly")
        void shouldIdentifyWebhookErrors() {
            // Arrange
            WebhookDeliveryException webhookException = new WebhookDeliveryException(
                    "WEBHOOK_DELIVERY_ERROR", "Error delivering webhook");
            RuntimeException runtimeException = new RuntimeException("General error");
            
            // Act & Assert
            assertTrue(ErrorUtil.isWebhookError(webhookException), 
                    "WebhookDeliveryException should be identified as webhook error");
            assertFalse(ErrorUtil.isWebhookError(runtimeException), 
                    "RuntimeException should not be identified as webhook error");
        }
    }
}