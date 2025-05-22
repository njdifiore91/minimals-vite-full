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
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

import javax.servlet.http.HttpServletRequest;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeoutException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link ErrorUtil} class.
 * 
 * These tests verify that the error handling utilities work correctly, including:
 * - Error message extraction
 * - Error normalization
 * - Error logging
 * - API error response generation
 * - Retry determination
 * - Error message sanitization
 * - Validation error building
 * - Error categorization
 */
@ExtendWith(MockitoExtension.class)
public class ErrorUtilTest {

    @Mock
    private Logger mockLogger;

    @Mock
    private BindingResult mockBindingResult;

    private HttpServletRequest mockRequest;

    @BeforeEach
    void setUp() {
        mockRequest = new MockHttpServletRequest("GET", "/api/applications/123");
    }

    @Test
    @DisplayName("getErrorMessage should extract message from RuntimeException")
    void getErrorMessage_RuntimeException_ReturnsMessage() {
        // Arrange
        RuntimeException exception = new RuntimeException("Test error message");
        
        // Act
        String result = ErrorUtil.getErrorMessage(exception);
        
        // Assert
        assertEquals("Test error message", result);
    }

    @Test
    @DisplayName("getErrorMessage should handle null exception")
    void getErrorMessage_NullException_ReturnsDefaultMessage() {
        // Act
        String result = ErrorUtil.getErrorMessage(null);
        
        // Assert
        assertEquals("An unknown error occurred", result);
    }

    @Test
    @DisplayName("getErrorMessage should handle custom BaseException")
    void getErrorMessage_BaseException_ReturnsMessage() {
        // Arrange
        BaseException exception = mock(BaseException.class);
        when(exception.getMessage()).thenReturn("Custom error message");
        
        // Act
        String result = ErrorUtil.getErrorMessage(exception);
        
        // Assert
        assertEquals("Custom error message", result);
    }

    @Test
    @DisplayName("getErrorMessage should handle network exceptions")
    void getErrorMessage_NetworkException_ReturnsNetworkErrorMessage() {
        // Arrange
        ConnectException exception = new ConnectException("Connection refused");
        
        // Act
        String result = ErrorUtil.getErrorMessage(exception);
        
        // Assert
        assertEquals("A network error occurred. Please check your connection and try again.", result);
    }

    @Test
    @DisplayName("getErrorMessage should handle timeout exceptions")
    void getErrorMessage_TimeoutException_ReturnsTimeoutErrorMessage() {
        // Arrange
        TimeoutException exception = new TimeoutException("Request timed out");
        
        // Act
        String result = ErrorUtil.getErrorMessage(exception);
        
        // Assert
        assertEquals("The request timed out. Please try again later.", result);
    }

    @Test
    @DisplayName("getErrorMessage should handle HttpClientErrorException")
    void getErrorMessage_HttpClientErrorException_ReturnsFormattedMessage() {
        // Arrange
        HttpClientErrorException exception = HttpClientErrorException.create(
            HttpStatus.BAD_REQUEST, "Bad Request", null, null, null);
        
        // Act
        String result = ErrorUtil.getErrorMessage(exception);
        
        // Assert
        assertEquals("Client error: 400 BAD_REQUEST - Bad Request", result);
    }

    @Test
    @DisplayName("getErrorMessage should handle HttpServerErrorException")
    void getErrorMessage_HttpServerErrorException_ReturnsFormattedMessage() {
        // Arrange
        HttpServerErrorException exception = HttpServerErrorException.create(
            HttpStatus.INTERNAL_SERVER_ERROR, "Internal Server Error", null, null, null);
        
        // Act
        String result = ErrorUtil.getErrorMessage(exception);
        
        // Assert
        assertEquals("Server error: 500 INTERNAL_SERVER_ERROR - Internal Server Error", result);
    }

    @Test
    @DisplayName("normalizeError should create standardized error map")
    void normalizeError_Exception_ReturnsStandardizedMap() {
        // Arrange
        RuntimeException exception = new RuntimeException("Test error message");
        
        // Act
        Map<String, Object> result = ErrorUtil.normalizeError(exception);
        
        // Assert
        assertNotNull(result);
        assertEquals("RuntimeException", result.get("error"));
        assertEquals("Test error message", result.get("message"));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), result.get("status"));
        assertNotNull(result.get("timestamp"));
    }

    @Test
    @DisplayName("normalizeError should handle null exception")
    void normalizeError_NullException_ReturnsDefaultMap() {
        // Act
        Map<String, Object> result = ErrorUtil.normalizeError(null);
        
        // Assert
        assertNotNull(result);
        assertEquals("Unknown Error", result.get("error"));
        assertEquals("An unknown error occurred", result.get("message"));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), result.get("status"));
        assertNotNull(result.get("timestamp"));
    }

    @Test
    @DisplayName("normalizeError should include validation errors for ValidationException")
    void normalizeError_ValidationException_IncludesValidationErrors() {
        // Arrange
        Map<String, String> validationErrors = Map.of(
            "name", "Name is required",
            "email", "Invalid email format"
        );
        ValidationException exception = mock(ValidationException.class);
        when(exception.getMessage()).thenReturn("Validation failed");
        when(exception.getValidationErrors()).thenReturn(validationErrors);
        when(exception.getStatusCode()).thenReturn(HttpStatus.BAD_REQUEST);
        
        // Act
        Map<String, Object> result = ErrorUtil.normalizeError(exception);
        
        // Assert
        assertNotNull(result);
        assertEquals("ValidationException", result.get("error"));
        assertEquals("Validation failed", result.get("message"));
        assertEquals(HttpStatus.BAD_REQUEST.value(), result.get("status"));
        assertEquals(validationErrors, result.get("validationErrors"));
    }

    @Test
    @DisplayName("normalizeError should include rule ID for BusinessRuleException")
    void normalizeError_BusinessRuleException_IncludesRuleId() {
        // Arrange
        BusinessRuleException exception = mock(BusinessRuleException.class);
        when(exception.getMessage()).thenReturn("Business rule violation");
        when(exception.getRuleId()).thenReturn("RULE_001");
        when(exception.getStatusCode()).thenReturn(HttpStatus.UNPROCESSABLE_ENTITY);
        
        // Act
        Map<String, Object> result = ErrorUtil.normalizeError(exception);
        
        // Assert
        assertNotNull(result);
        assertEquals("BusinessRuleException", result.get("error"));
        assertEquals("Business rule violation", result.get("message"));
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY.value(), result.get("status"));
        assertEquals("RULE_001", result.get("ruleId"));
    }

    @Test
    @DisplayName("logError should log at ERROR level for server errors")
    void logError_ServerError_LogsAtErrorLevel() {
        // Arrange
        HttpServerErrorException exception = HttpServerErrorException.create(
            HttpStatus.INTERNAL_SERVER_ERROR, "Internal Server Error", null, null, null);
        
        // Act
        ErrorUtil.logError(mockLogger, exception, "Server error occurred");
        
        // Assert
        verify(mockLogger).error(eq("Server error occurred: {}"), eq("Internal Server Error"), eq(exception));
        verifyNoMoreInteractions(mockLogger);
    }

    @Test
    @DisplayName("logError should log at WARN level for client errors")
    void logError_ClientError_LogsAtWarnLevel() {
        // Arrange
        HttpClientErrorException exception = HttpClientErrorException.create(
            HttpStatus.BAD_REQUEST, "Bad Request", null, null, null);
        
        // Act
        ErrorUtil.logError(mockLogger, exception, "Client error occurred");
        
        // Assert
        verify(mockLogger).warn(eq("Client error occurred: {}"), eq("Client error: 400 BAD_REQUEST - Bad Request"));
        verifyNoMoreInteractions(mockLogger);
    }

    @Test
    @DisplayName("logError should log at INFO level for not found resources")
    void logError_ResourceNotFound_LogsAtInfoLevel() {
        // Arrange
        ResourceNotFoundException exception = mock(ResourceNotFoundException.class);
        when(exception.getMessage()).thenReturn("Resource not found");
        
        // Act
        ErrorUtil.logError(mockLogger, exception, "Resource not found");
        
        // Assert
        verify(mockLogger).info(eq("Resource not found: {}"), eq("Resource not found"));
        verifyNoMoreInteractions(mockLogger);
    }

    @Test
    @DisplayName("logError should log at INFO level for authorization issues")
    void logError_AuthorizationException_LogsAtInfoLevel() {
        // Arrange
        AuthorizationException exception = mock(AuthorizationException.class);
        when(exception.getMessage()).thenReturn("Not authorized");
        
        // Act
        ErrorUtil.logError(mockLogger, exception, "Authorization error");
        
        // Assert
        verify(mockLogger).info(eq("Authorization error: {}"), eq("Not authorized"));
        verifyNoMoreInteractions(mockLogger);
    }

    @Test
    @DisplayName("logError should log at DEBUG level for other exceptions")
    void logError_OtherException_LogsAtDebugLevel() {
        // Arrange
        RuntimeException exception = new RuntimeException("Generic error");
        
        // Act
        ErrorUtil.logError(mockLogger, exception, "Generic error occurred");
        
        // Assert
        verify(mockLogger).debug(eq("Generic error occurred: {}"), eq("Generic error"), eq(exception));
        verifyNoMoreInteractions(mockLogger);
    }

    @Test
    @DisplayName("logError should handle null logger")
    void logError_NullLogger_DoesNotThrowException() {
        // Arrange
        RuntimeException exception = new RuntimeException("Test error");
        
        // Act & Assert - should not throw exception
        assertDoesNotThrow(() -> ErrorUtil.logError(null, exception, "Test message"));
    }

    @Test
    @DisplayName("logError should handle null exception")
    void logError_NullException_DoesNotThrowException() {
        // Act & Assert - should not throw exception
        assertDoesNotThrow(() -> ErrorUtil.logError(mockLogger, null, "Test message"));
        verifyNoInteractions(mockLogger);
    }

    @Test
    @DisplayName("createApiError should create standardized API error response")
    void createApiError_Exception_ReturnsApiErrorResponse() {
        // Arrange
        RuntimeException exception = new RuntimeException("API error");
        String path = "/api/applications/123";
        
        // Act
        Map<String, Object> result = ErrorUtil.createApiError(exception, path);
        
        // Assert
        assertNotNull(result);
        assertEquals("RuntimeException", result.get("error"));
        assertEquals("API error", result.get("message"));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), result.get("status"));
        assertEquals(path, result.get("path"));
        assertNotNull(result.get("timestamp"));
    }

    @Test
    @DisplayName("createApiError with HttpServletRequest should include request details")
    void createApiError_WithRequest_IncludesRequestDetails() {
        // Arrange
        RuntimeException exception = new RuntimeException("API error");
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/applications");
        request.setQueryString("type=business");
        
        // Act
        Map<String, Object> result = ErrorUtil.createApiError(exception, request);
        
        // Assert
        assertNotNull(result);
        assertEquals("/api/applications", result.get("path"));
        assertEquals("POST", result.get("method"));
        assertEquals("type=business", result.get("query"));
    }

    @Test
    @DisplayName("isRetryableError should identify network errors as retryable")
    void isRetryableError_NetworkError_ReturnsTrue() {
        // Arrange
        ConnectException exception = new ConnectException("Connection refused");
        
        // Act
        boolean result = ErrorUtil.isRetryableError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isRetryableError should identify timeout errors as retryable")
    void isRetryableError_TimeoutError_ReturnsTrue() {
        // Arrange
        SocketTimeoutException exception = new SocketTimeoutException("Socket timeout");
        
        // Act
        boolean result = ErrorUtil.isRetryableError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isRetryableError should identify server errors as retryable")
    void isRetryableError_ServerError_ReturnsTrue() {
        // Arrange
        HttpServerErrorException exception = HttpServerErrorException.create(
            HttpStatus.INTERNAL_SERVER_ERROR, "Internal Server Error", null, null, null);
        
        // Act
        boolean result = ErrorUtil.isRetryableError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isRetryableError should identify webhook delivery errors as retryable")
    void isRetryableError_WebhookDeliveryError_ReturnsTrue() {
        // Arrange
        WebhookDeliveryException exception = mock(WebhookDeliveryException.class);
        
        // Act
        boolean result = ErrorUtil.isRetryableError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isRetryableError should identify retryable document processing errors")
    void isRetryableError_RetryableDocumentProcessingError_ReturnsTrue() {
        // Arrange
        DocumentProcessingException exception = mock(DocumentProcessingException.class);
        when(exception.isRetryable()).thenReturn(true);
        
        // Act
        boolean result = ErrorUtil.isRetryableError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isRetryableError should identify non-retryable document processing errors")
    void isRetryableError_NonRetryableDocumentProcessingError_ReturnsFalse() {
        // Arrange
        DocumentProcessingException exception = mock(DocumentProcessingException.class);
        when(exception.isRetryable()).thenReturn(false);
        
        // Act
        boolean result = ErrorUtil.isRetryableError(exception);
        
        // Assert
        assertFalse(result);
    }

    @Test
    @DisplayName("isRetryableError should identify client errors as non-retryable")
    void isRetryableError_ClientError_ReturnsFalse() {
        // Arrange
        HttpClientErrorException exception = HttpClientErrorException.create(
            HttpStatus.BAD_REQUEST, "Bad Request", null, null, null);
        
        // Act
        boolean result = ErrorUtil.isRetryableError(exception);
        
        // Assert
        assertFalse(result);
    }

    @Test
    @DisplayName("isRetryableError should handle null exception")
    void isRetryableError_NullException_ReturnsFalse() {
        // Act
        boolean result = ErrorUtil.isRetryableError(null);
        
        // Assert
        assertFalse(result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should redact SSNs")
    void sanitizeErrorMessage_ContainsSsn_RedactsSsn() {
        // Arrange
        String message = "Error processing SSN: 123-45-6789";
        
        // Act
        String result = ErrorUtil.sanitizeErrorMessage(message);
        
        // Assert
        assertEquals("Error processing SSN: XXX-XX-XXXX", result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should redact credit card numbers")
    void sanitizeErrorMessage_ContainsCreditCard_RedactsCreditCard() {
        // Arrange
        String message = "Error processing credit card: 4111-1111-1111-1111";
        
        // Act
        String result = ErrorUtil.sanitizeErrorMessage(message);
        
        // Assert
        assertEquals("Error processing credit card: XXXX-XXXX-XXXX-XXXX", result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should redact EINs")
    void sanitizeErrorMessage_ContainsEin_RedactsEin() {
        // Arrange
        String message = "Error processing EIN: 12-3456789";
        
        // Act
        String result = ErrorUtil.sanitizeErrorMessage(message);
        
        // Assert
        assertEquals("Error processing EIN: XX-XXXXXXX", result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should redact email addresses")
    void sanitizeErrorMessage_ContainsEmail_RedactsEmail() {
        // Arrange
        String message = "Error sending email to: user@example.com";
        
        // Act
        String result = ErrorUtil.sanitizeErrorMessage(message);
        
        // Assert
        assertEquals("Error sending email to: [EMAIL REDACTED]", result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should redact phone numbers")
    void sanitizeErrorMessage_ContainsPhone_RedactsPhone() {
        // Arrange
        String message = "Error sending SMS to: (123) 456-7890";
        
        // Act
        String result = ErrorUtil.sanitizeErrorMessage(message);
        
        // Assert
        assertEquals("Error sending SMS to: [PHONE REDACTED]", result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should redact addresses")
    void sanitizeErrorMessage_ContainsAddress_RedactsAddress() {
        // Arrange
        String message = "Error processing address: 123 Main Street";
        
        // Act
        String result = ErrorUtil.sanitizeErrorMessage(message);
        
        // Assert
        assertEquals("Error processing address: [ADDRESS REDACTED]", result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should handle null message")
    void sanitizeErrorMessage_NullMessage_ReturnsNull() {
        // Act
        String result = ErrorUtil.sanitizeErrorMessage(null);
        
        // Assert
        assertNull(result);
    }

    @Test
    @DisplayName("sanitizeErrorMessage should handle empty message")
    void sanitizeErrorMessage_EmptyMessage_ReturnsEmptyString() {
        // Act
        String result = ErrorUtil.sanitizeErrorMessage("");
        
        // Assert
        assertEquals("", result);
    }

    @Test
    @DisplayName("buildValidationError should create map from binding result")
    void buildValidationError_BindingResult_ReturnsErrorMap() {
        // Arrange
        List<FieldError> fieldErrors = new ArrayList<>();
        fieldErrors.add(new FieldError("application", "name", "Name is required"));
        fieldErrors.add(new FieldError("application", "email", "Invalid email format"));
        
        when(mockBindingResult.hasErrors()).thenReturn(true);
        when(mockBindingResult.getFieldErrors()).thenReturn(fieldErrors);
        
        // Act
        Map<String, String> result = ErrorUtil.buildValidationError(mockBindingResult);
        
        // Assert
        assertNotNull(result);
        assertEquals(2, result.size());
        assertEquals("Name is required", result.get("name"));
        assertEquals("Invalid email format", result.get("email"));
    }

    @Test
    @DisplayName("buildValidationError should handle binding result with no errors")
    void buildValidationError_NoErrors_ReturnsEmptyMap() {
        // Arrange
        when(mockBindingResult.hasErrors()).thenReturn(false);
        
        // Act
        Map<String, String> result = ErrorUtil.buildValidationError(mockBindingResult);
        
        // Assert
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("buildValidationError should handle null binding result")
    void buildValidationError_NullBindingResult_ReturnsEmptyMap() {
        // Act
        Map<String, String> result = ErrorUtil.buildValidationError(null);
        
        // Assert
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("isNetworkError should identify ConnectException as network error")
    void isNetworkError_ConnectException_ReturnsTrue() {
        // Arrange
        ConnectException exception = new ConnectException("Connection refused");
        
        // Act
        boolean result = ErrorUtil.isNetworkError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isNetworkError should identify SocketTimeoutException as network error")
    void isNetworkError_SocketTimeoutException_ReturnsTrue() {
        // Arrange
        SocketTimeoutException exception = new SocketTimeoutException("Socket timeout");
        
        // Act
        boolean result = ErrorUtil.isNetworkError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isNetworkError should identify ResourceAccessException as network error")
    void isNetworkError_ResourceAccessException_ReturnsTrue() {
        // Arrange
        ResourceAccessException exception = new ResourceAccessException("Resource access error");
        
        // Act
        boolean result = ErrorUtil.isNetworkError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isNetworkError should not identify other exceptions as network errors")
    void isNetworkError_OtherException_ReturnsFalse() {
        // Arrange
        RuntimeException exception = new RuntimeException("Generic error");
        
        // Act
        boolean result = ErrorUtil.isNetworkError(exception);
        
        // Assert
        assertFalse(result);
    }

    @Test
    @DisplayName("isAuthError should identify HttpClientErrorException with 401 status as auth error")
    void isAuthError_UnauthorizedException_ReturnsTrue() {
        // Arrange
        HttpClientErrorException exception = HttpClientErrorException.create(
            HttpStatus.UNAUTHORIZED, "Unauthorized", null, null, null);
        
        // Act
        boolean result = ErrorUtil.isAuthError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isAuthError should identify exceptions with auth-related messages")
    void isAuthError_AuthRelatedMessage_ReturnsTrue() {
        // Arrange
        RuntimeException exception = new RuntimeException("Authentication failed: Invalid token");
        
        // Act
        boolean result = ErrorUtil.isAuthError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isAuthError should not identify other exceptions as auth errors")
    void isAuthError_OtherException_ReturnsFalse() {
        // Arrange
        RuntimeException exception = new RuntimeException("Generic error");
        
        // Act
        boolean result = ErrorUtil.isAuthError(exception);
        
        // Assert
        assertFalse(result);
    }

    @Test
    @DisplayName("isAuthorizationError should identify AuthorizationException as authorization error")
    void isAuthorizationError_AuthorizationException_ReturnsTrue() {
        // Arrange
        AuthorizationException exception = mock(AuthorizationException.class);
        
        // Act
        boolean result = ErrorUtil.isAuthorizationError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isAuthorizationError should identify HttpClientErrorException with 403 status as authorization error")
    void isAuthorizationError_ForbiddenException_ReturnsTrue() {
        // Arrange
        HttpClientErrorException exception = HttpClientErrorException.create(
            HttpStatus.FORBIDDEN, "Forbidden", null, null, null);
        
        // Act
        boolean result = ErrorUtil.isAuthorizationError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isAuthorizationError should not identify other exceptions as authorization errors")
    void isAuthorizationError_OtherException_ReturnsFalse() {
        // Arrange
        RuntimeException exception = new RuntimeException("Generic error");
        
        // Act
        boolean result = ErrorUtil.isAuthorizationError(exception);
        
        // Assert
        assertFalse(result);
    }

    @Test
    @DisplayName("isValidationError should identify ValidationException as validation error")
    void isValidationError_ValidationException_ReturnsTrue() {
        // Arrange
        ValidationException exception = mock(ValidationException.class);
        
        // Act
        boolean result = ErrorUtil.isValidationError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isValidationError should identify BindException as validation error")
    void isValidationError_BindException_ReturnsTrue() {
        // Arrange
        org.springframework.validation.BindException exception = mock(org.springframework.validation.BindException.class);
        
        // Act
        boolean result = ErrorUtil.isValidationError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isValidationError should identify MethodArgumentNotValidException as validation error")
    void isValidationError_MethodArgumentNotValidException_ReturnsTrue() {
        // Arrange
        org.springframework.web.bind.MethodArgumentNotValidException exception = 
            mock(org.springframework.web.bind.MethodArgumentNotValidException.class);
        
        // Act
        boolean result = ErrorUtil.isValidationError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isValidationError should identify HttpClientErrorException with 400 status as validation error")
    void isValidationError_BadRequestException_ReturnsTrue() {
        // Arrange
        HttpClientErrorException exception = HttpClientErrorException.create(
            HttpStatus.BAD_REQUEST, "Bad Request", null, null, null);
        
        // Act
        boolean result = ErrorUtil.isValidationError(exception);
        
        // Assert
        assertTrue(result);
    }

    @Test
    @DisplayName("isValidationError should not identify other exceptions as validation errors")
    void isValidationError_OtherException_ReturnsFalse() {
        // Arrange
        RuntimeException exception = new RuntimeException("Generic error");
        
        // Act
        boolean result = ErrorUtil.isValidationError(exception);
        
        // Assert
        assertFalse(result);
    }

    @Test
    @DisplayName("calculateRetryDelay should return initial backoff for first attempt")
    void calculateRetryDelay_FirstAttempt_ReturnsInitialBackoff() {
        // Act
        long result = ErrorUtil.calculateRetryDelay(1);
        
        // Assert
        assertEquals(1000, result);
    }

    @Test
    @DisplayName("calculateRetryDelay should increase delay for subsequent attempts")
    void calculateRetryDelay_SubsequentAttempts_ReturnsIncreasedDelay() {
        // Act
        long result1 = ErrorUtil.calculateRetryDelay(1);
        long result2 = ErrorUtil.calculateRetryDelay(2);
        long result3 = ErrorUtil.calculateRetryDelay(3);
        
        // Assert
        assertTrue(result2 > result1);
        assertTrue(result3 > result2);
    }

    @Test
    @DisplayName("calculateRetryDelay should handle invalid attempt number")
    void calculateRetryDelay_InvalidAttempt_ReturnsInitialBackoff() {
        // Act
        long result = ErrorUtil.calculateRetryDelay(0);
        
        // Assert
        assertEquals(1000, result);
    }

    @Test
    @DisplayName("calculateRetryDelay should cap delay at 30 seconds")
    void calculateRetryDelay_LargeAttemptNumber_CapsAt30Seconds() {
        // Act
        long result = ErrorUtil.calculateRetryDelay(10);
        
        // Assert
        assertTrue(result <= 30000);
    }
}