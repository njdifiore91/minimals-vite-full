package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the BaseException class.
 * These tests verify the core functionality of the BaseException as the foundation
 * of the exception hierarchy in the MCA application.
 */
public class BaseExceptionTest {

    private static final String TEST_ERROR_CODE = "TEST_ERROR_001";
    private static final String TEST_MESSAGE = "Test error message";
    private static final HttpStatus TEST_HTTP_STATUS = HttpStatus.BAD_REQUEST;

    @Test
    @DisplayName("Should create exception with error code, message, and HTTP status")
    void shouldCreateExceptionWithErrorCodeMessageAndHttpStatus() {
        // Arrange & Act
        BaseException exception = new BaseException(TEST_ERROR_CODE, TEST_MESSAGE, TEST_HTTP_STATUS);
        
        // Assert
        assertEquals(TEST_ERROR_CODE, exception.getErrorCode());
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(TEST_HTTP_STATUS, exception.getHttpStatus());
        assertEquals(TEST_HTTP_STATUS.value(), exception.getStatusCode());
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with error code, message, HTTP status, and cause")
    void shouldCreateExceptionWithErrorCodeMessageHttpStatusAndCause() {
        // Arrange
        Throwable cause = new RuntimeException("Original cause");
        
        // Act
        BaseException exception = new BaseException(TEST_ERROR_CODE, TEST_MESSAGE, TEST_HTTP_STATUS, cause);
        
        // Assert
        assertEquals(TEST_ERROR_CODE, exception.getErrorCode());
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(TEST_HTTP_STATUS, exception.getHttpStatus());
        assertEquals(TEST_HTTP_STATUS.value(), exception.getStatusCode());
        assertSame(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message and HTTP status")
    void shouldCreateExceptionWithMessageAndHttpStatus() {
        // Arrange & Act
        BaseException exception = new BaseException(TEST_MESSAGE, TEST_HTTP_STATUS);
        
        // Assert
        assertEquals("ERR_" + TEST_HTTP_STATUS.value(), exception.getErrorCode());
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(TEST_HTTP_STATUS, exception.getHttpStatus());
        assertEquals(TEST_HTTP_STATUS.value(), exception.getStatusCode());
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message, HTTP status, and cause")
    void shouldCreateExceptionWithMessageHttpStatusAndCause() {
        // Arrange
        Throwable cause = new RuntimeException("Original cause");
        
        // Act
        BaseException exception = new BaseException(TEST_MESSAGE, TEST_HTTP_STATUS, cause);
        
        // Assert
        assertEquals("ERR_" + TEST_HTTP_STATUS.value(), exception.getErrorCode());
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(TEST_HTTP_STATUS, exception.getHttpStatus());
        assertEquals(TEST_HTTP_STATUS.value(), exception.getStatusCode());
        assertSame(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should generate error code from HTTP status when not explicitly provided")
    void shouldGenerateErrorCodeFromHttpStatus() {
        // Arrange & Act
        BaseException exception = new BaseException(TEST_MESSAGE, HttpStatus.NOT_FOUND);
        
        // Assert
        assertEquals("ERR_404", exception.getErrorCode());
    }

    @Test
    @DisplayName("Should preserve error code when explicitly provided")
    void shouldPreserveErrorCodeWhenExplicitlyProvided() {
        // Arrange & Act
        BaseException exception = new BaseException("CUSTOM_ERROR", TEST_MESSAGE, HttpStatus.NOT_FOUND);
        
        // Assert
        assertEquals("CUSTOM_ERROR", exception.getErrorCode());
    }

    @Test
    @DisplayName("Should return correct HTTP status code")
    void shouldReturnCorrectHttpStatusCode() {
        // Arrange & Act
        BaseException exception = new BaseException(TEST_MESSAGE, HttpStatus.INTERNAL_SERVER_ERROR);
        
        // Assert
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(500, exception.getStatusCode());
    }

    @Test
    @DisplayName("Should format toString with error code, HTTP status, and message")
    void shouldFormatToStringWithErrorCodeHttpStatusAndMessage() {
        // Arrange
        BaseException exception = new BaseException(TEST_ERROR_CODE, TEST_MESSAGE, TEST_HTTP_STATUS);
        
        // Act
        String result = exception.toString();
        
        // Assert
        assertTrue(result.contains(TEST_ERROR_CODE));
        assertTrue(result.contains(TEST_HTTP_STATUS.toString()));
        assertTrue(result.contains(TEST_MESSAGE));
    }

    @Test
    @DisplayName("Should preserve exception chain for root cause analysis")
    void shouldPreserveExceptionChainForRootCauseAnalysis() {
        // Arrange
        IllegalArgumentException rootCause = new IllegalArgumentException("Invalid argument");
        RuntimeException intermediateException = new RuntimeException("Intermediate exception", rootCause);
        
        // Act
        BaseException exception = new BaseException(TEST_ERROR_CODE, TEST_MESSAGE, TEST_HTTP_STATUS, intermediateException);
        
        // Assert
        assertSame(intermediateException, exception.getCause());
        assertSame(rootCause, exception.getCause().getCause());
        assertEquals("Invalid argument", exception.getCause().getCause().getMessage());
    }

    @Test
    @DisplayName("Should handle null cause gracefully")
    void shouldHandleNullCauseGracefully() {
        // Arrange & Act
        BaseException exception = new BaseException(TEST_ERROR_CODE, TEST_MESSAGE, TEST_HTTP_STATUS, null);
        
        // Assert
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should handle different HTTP status codes correctly")
    void shouldHandleDifferentHttpStatusCodesCorrectly() {
        // Arrange & Act
        BaseException badRequestException = new BaseException("Bad request message", HttpStatus.BAD_REQUEST);
        BaseException notFoundException = new BaseException("Not found message", HttpStatus.NOT_FOUND);
        BaseException serverErrorException = new BaseException("Server error message", HttpStatus.INTERNAL_SERVER_ERROR);
        
        // Assert
        assertEquals(HttpStatus.BAD_REQUEST, badRequestException.getHttpStatus());
        assertEquals(400, badRequestException.getStatusCode());
        assertEquals("ERR_400", badRequestException.getErrorCode());
        
        assertEquals(HttpStatus.NOT_FOUND, notFoundException.getHttpStatus());
        assertEquals(404, notFoundException.getStatusCode());
        assertEquals("ERR_404", notFoundException.getErrorCode());
        
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, serverErrorException.getHttpStatus());
        assertEquals(500, serverErrorException.getStatusCode());
        assertEquals("ERR_500", serverErrorException.getErrorCode());
    }
}