package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link ResourceNotFoundException} class.
 * <p>
 * These tests verify that the ResourceNotFoundException properly handles resource not found scenarios
 * with appropriate HTTP status codes, error messages, and resource identification details.
 * </p>
 */
public class ResourceNotFoundExceptionTest {

    @Test
    @DisplayName("Should create ResourceNotFoundException with resource type and identifier")
    public void testCreateWithResourceTypeAndIdentifier() {
        // Arrange & Act
        String resourceType = "Application";
        String resourceId = "APP123";
        ResourceNotFoundException exception = new ResourceNotFoundException(resourceType, resourceId);
        
        // Assert
        assertEquals(String.format("%s with id %s not found", resourceType, resourceId), exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(HttpStatus.NOT_FOUND.value(), exception.getStatusCode());
        assertEquals(resourceType, exception.getResourceType());
        assertEquals(resourceId, exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should create ResourceNotFoundException with resource type, identifier, and cause")
    public void testCreateWithResourceTypeIdentifierAndCause() {
        // Arrange & Act
        String resourceType = "Document";
        String resourceId = "DOC456";
        IllegalArgumentException cause = new IllegalArgumentException("Invalid document ID format");
        ResourceNotFoundException exception = new ResourceNotFoundException(resourceType, resourceId, cause);
        
        // Assert
        assertEquals(String.format("%s with id %s not found", resourceType, resourceId), exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(cause, exception.getCause());
        assertEquals(resourceType, exception.getResourceType());
        assertEquals(resourceId, exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should create ResourceNotFoundException with custom message")
    public void testCreateWithCustomMessage() {
        // Arrange & Act
        String message = "Custom resource not found message";
        ResourceNotFoundException exception = new ResourceNotFoundException(message);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Resource", exception.getResourceType());
        assertEquals("unknown", exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should create ResourceNotFoundException with custom message and cause")
    public void testCreateWithCustomMessageAndCause() {
        // Arrange & Act
        String message = "Custom resource not found message with cause";
        IllegalStateException cause = new IllegalStateException("Database connection error");
        ResourceNotFoundException exception = new ResourceNotFoundException(message, cause);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(cause, exception.getCause());
        assertEquals("Resource", exception.getResourceType());
        assertEquals("unknown", exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should create ResourceNotFoundException for application not found")
    public void testApplicationNotFound() {
        // Arrange & Act
        String applicationId = "APP789";
        ResourceNotFoundException exception = ResourceNotFoundException.applicationNotFound(applicationId);
        
        // Assert
        assertEquals(String.format("%s with id %s not found", "Application", applicationId), exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Application", exception.getResourceType());
        assertEquals(applicationId, exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should create ResourceNotFoundException for document not found")
    public void testDocumentNotFound() {
        // Arrange & Act
        String documentId = "DOC789";
        ResourceNotFoundException exception = ResourceNotFoundException.documentNotFound(documentId);
        
        // Assert
        assertEquals(String.format("%s with id %s not found", "Document", documentId), exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Document", exception.getResourceType());
        assertEquals(documentId, exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should create ResourceNotFoundException for merchant not found")
    public void testMerchantNotFound() {
        // Arrange & Act
        String merchantId = "MERCH123";
        ResourceNotFoundException exception = ResourceNotFoundException.merchantNotFound(merchantId);
        
        // Assert
        assertEquals(String.format("%s with id %s not found", "Merchant", merchantId), exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Merchant", exception.getResourceType());
        assertEquals(merchantId, exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should create ResourceNotFoundException for webhook not found")
    public void testWebhookNotFound() {
        // Arrange & Act
        String webhookId = "WEBHOOK456";
        ResourceNotFoundException exception = ResourceNotFoundException.webhookNotFound(webhookId);
        
        // Assert
        assertEquals(String.format("%s with id %s not found", "Webhook", webhookId), exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals("Webhook", exception.getResourceType());
        assertEquals(webhookId, exception.getResourceId());
    }
    
    @Test
    @DisplayName("Should verify error code is set to NOT_FOUND")
    public void testErrorCodeIsSetToNotFound() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException("Application", "APP123");
        
        // Assert
        assertEquals("NOT_FOUND", exception.getErrorCode());
    }
    
    @Test
    @DisplayName("Should verify status code is set to 404")
    public void testStatusCodeIsSetTo404() {
        // Arrange & Act
        ResourceNotFoundException exception = new ResourceNotFoundException("Application", "APP123");
        
        // Assert
        assertEquals(404, exception.getStatusCode());
    }
    
    @Test
    @DisplayName("Should verify message formatting with different resource types and identifiers")
    public void testMessageFormattingWithDifferentResourceTypesAndIdentifiers() {
        // Arrange & Act - Test with various resource types and identifiers
        ResourceNotFoundException exception1 = new ResourceNotFoundException("User", "USR001");
        ResourceNotFoundException exception2 = new ResourceNotFoundException("Product", "PRD123");
        ResourceNotFoundException exception3 = new ResourceNotFoundException("Order", "ORD-XYZ-789");
        
        // Assert
        assertEquals("User with id USR001 not found", exception1.getMessage());
        assertEquals("Product with id PRD123 not found", exception2.getMessage());
        assertEquals("Order with id ORD-XYZ-789 not found", exception3.getMessage());
    }
    
    @Test
    @DisplayName("Should verify resource type and identifier getters")
    public void testResourceTypeAndIdentifierGetters() {
        // Arrange & Act
        String resourceType = "CustomResource";
        String resourceId = "CUSTOM-ID-123";
        ResourceNotFoundException exception = new ResourceNotFoundException(resourceType, resourceId);
        
        // Assert
        assertEquals(resourceType, exception.getResourceType());
        assertEquals(resourceId, exception.getResourceId());
    }
}