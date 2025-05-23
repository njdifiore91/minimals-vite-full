package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.util.Constants;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link ResourceNotFoundException} class.
 * 
 * These tests verify that ResourceNotFoundException properly handles 404 Not Found scenarios,
 * correctly formats error messages with resource type and identifier information, and
 * provides appropriate static factory methods for common resource types.
 */
@DisplayName("ResourceNotFoundException Tests")
class ResourceNotFoundExceptionTest {

    private static final String TEST_MESSAGE = "Resource not found";
    private static final String TEST_RESOURCE_TYPE = "TestResource";
    private static final String TEST_RESOURCE_ID = "test-123";

    @Test
    @DisplayName("Should initialize with message and set status code to 404")
    void shouldInitializeWithMessageAndSetStatusCodeTo404() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(TEST_MESSAGE);
        
        // Assert
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(404, exception.getStatusCode());
        assertEquals("unknown", exception.getResourceType());
        assertEquals("unknown", exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should initialize with message and cause")
    void shouldInitializeWithMessageAndCause() {
        // Arrange
        Throwable cause = new IllegalArgumentException("Original error");
        
        // Act
        ResourceNotFoundException exception = new ResourceNotFoundException(TEST_MESSAGE, cause);
        
        // Assert
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(cause, exception.getCause());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(404, exception.getStatusCode());
        assertEquals("unknown", exception.getResourceType());
        assertEquals("unknown", exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should initialize with resource type and identifier")
    void shouldInitializeWithResourceTypeAndIdentifier() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                TEST_RESOURCE_TYPE, TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", TEST_RESOURCE_TYPE, TEST_RESOURCE_ID), 
                exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(404, exception.getStatusCode());
        assertEquals(TEST_RESOURCE_TYPE, exception.getResourceType());
        assertEquals(TEST_RESOURCE_ID, exception.getResourceId());
        assertEquals(Constants.ErrorCode.NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should initialize with resource type, identifier, and cause")
    void shouldInitializeWithResourceTypeIdentifierAndCause() {
        // Arrange
        Throwable cause = new IllegalArgumentException("Original error");
        
        // Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                TEST_RESOURCE_TYPE, TEST_RESOURCE_ID, cause);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", TEST_RESOURCE_TYPE, TEST_RESOURCE_ID), 
                exception.getMessage());
        assertEquals(cause, exception.getCause());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(404, exception.getStatusCode());
        assertEquals(TEST_RESOURCE_TYPE, exception.getResourceType());
        assertEquals(TEST_RESOURCE_ID, exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should determine correct error code for Application resource type")
    void shouldDetermineCorrectErrorCodeForApplicationResourceType() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                "Application", TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(Constants.ErrorCode.APPLICATION_NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should determine correct error code for Document resource type")
    void shouldDetermineCorrectErrorCodeForDocumentResourceType() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                "Document", TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(Constants.ErrorCode.DOCUMENT_NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should determine correct error code for unknown resource type")
    void shouldDetermineCorrectErrorCodeForUnknownResourceType() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                "UnknownType", TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(Constants.ErrorCode.NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should determine correct error code for null resource type")
    void shouldDetermineCorrectErrorCodeForNullResourceType() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                null, TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(Constants.ErrorCode.NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should create exception for application not found")
    void shouldCreateExceptionForApplicationNotFound() {
        // Arrange & Act
        ResourceNotFoundException exception = ResourceNotFoundException.applicationNotFound(TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", "Application", TEST_RESOURCE_ID), 
                exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Application", exception.getResourceType());
        assertEquals(TEST_RESOURCE_ID, exception.getResourceId());
        assertEquals(Constants.ErrorCode.APPLICATION_NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should create exception for document not found")
    void shouldCreateExceptionForDocumentNotFound() {
        // Arrange & Act
        ResourceNotFoundException exception = ResourceNotFoundException.documentNotFound(TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", "Document", TEST_RESOURCE_ID), 
                exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Document", exception.getResourceType());
        assertEquals(TEST_RESOURCE_ID, exception.getResourceId());
        assertEquals(Constants.ErrorCode.DOCUMENT_NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should create exception for merchant not found")
    void shouldCreateExceptionForMerchantNotFound() {
        // Arrange & Act
        ResourceNotFoundException exception = ResourceNotFoundException.merchantNotFound(TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", "Merchant", TEST_RESOURCE_ID), 
                exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Merchant", exception.getResourceType());
        assertEquals(TEST_RESOURCE_ID, exception.getResourceId());
        assertEquals(Constants.ErrorCode.NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should create exception for webhook not found")
    void shouldCreateExceptionForWebhookNotFound() {
        // Arrange & Act
        ResourceNotFoundException exception = ResourceNotFoundException.webhookNotFound(TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", "Webhook", TEST_RESOURCE_ID), 
                exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Webhook", exception.getResourceType());
        assertEquals(TEST_RESOURCE_ID, exception.getResourceId());
        assertEquals(Constants.ErrorCode.NOT_FOUND, exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should format message with resource type and identifier")
    void shouldFormatMessageWithResourceTypeAndIdentifier() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                TEST_RESOURCE_TYPE, TEST_RESOURCE_ID);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", TEST_RESOURCE_TYPE, TEST_RESOURCE_ID), 
                exception.getMessage());
    }
    
    @Test
    @DisplayName("Should handle null resource identifier")
    void shouldHandleNullResourceIdentifier() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException(
                TEST_RESOURCE_TYPE, null);
        
        // Assert
        assertEquals(String.format("%s with id '%s' not found", TEST_RESOURCE_TYPE, "null"), 
                exception.getMessage());
        assertEquals(TEST_RESOURCE_TYPE, exception.getResourceType());
        assertNull(exception.getResourceId());
    }
}