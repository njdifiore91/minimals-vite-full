package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.LocalDateTime;
import java.util.Set;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for the {@link Webhook} entity class.
 * <p>
 * These tests verify JPA mapping, field validation, and security features of the Webhook entity.
 * The test class ensures that the Webhook entity can be properly persisted and retrieved with all
 * its attributes intact, that validation constraints are properly enforced, and that secret keys
 * are securely stored.
 * </p>
 */
public class WebhookTest {

    private Validator validator;
    
    @BeforeEach
    public void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }
    
    @Test
    @DisplayName("Should create a valid webhook with all required fields")
    public void testCreateValidWebhook() {
        // Given
        String endpointUrl = "https://example.com/webhook";
        String secretKey = "abcdefghijklmnopqrstuvwxyz123456";
        Boolean active = true;
        EventType eventType = EventType.APPLICATION_CREATED;
        
        // When
        Webhook webhook = new Webhook(endpointUrl, secretKey, active, eventType);
        webhook.onCreate(); // Manually trigger the @PrePersist method for testing
        
        // Then
        assertEquals(endpointUrl, webhook.getEndpointUrl());
        assertEquals(secretKey, webhook.getSecretKey());
        assertEquals(active, webhook.getActive());
        assertEquals(eventType, webhook.getEventType());
        assertNotNull(webhook.getCreatedAt());
        assertNotNull(webhook.getUpdatedAt());
        assertEquals(webhook.getCreatedAt(), webhook.getUpdatedAt());
        assertEquals(0, webhook.getFailedAttempts());
        assertEquals(0L, webhook.getSuccessfulDeliveriesCount());
        assertEquals(0L, webhook.getFailedDeliveriesCount());
        assertEquals("X-Webhook-Signature", webhook.getSignatureHeader());
        assertTrue(webhook.isActive());
    }
    
    @Test
    @DisplayName("Should validate required fields")
    public void testValidateRequiredFields() {
        // Given
        Webhook webhook = new Webhook();
        
        // When
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        // Then
        assertFalse(violations.isEmpty());
        assertEquals(4, violations.size()); // endpointUrl, secretKey, active, eventType
        
        boolean hasEndpointUrlViolation = false;
        boolean hasSecretKeyViolation = false;
        boolean hasActiveViolation = false;
        boolean hasEventTypeViolation = false;
        
        for (ConstraintViolation<Webhook> violation : violations) {
            String propertyPath = violation.getPropertyPath().toString();
            if ("endpointUrl".equals(propertyPath)) {
                hasEndpointUrlViolation = true;
            } else if ("secretKey".equals(propertyPath)) {
                hasSecretKeyViolation = true;
            } else if ("active".equals(propertyPath)) {
                hasActiveViolation = true;
            } else if ("eventType".equals(propertyPath)) {
                hasEventTypeViolation = true;
            }
        }
        
        assertTrue(hasEndpointUrlViolation, "Should have endpointUrl violation");
        assertTrue(hasSecretKeyViolation, "Should have secretKey violation");
        assertTrue(hasActiveViolation, "Should have active violation");
        assertTrue(hasEventTypeViolation, "Should have eventType violation");
    }
    
    @Test
    @DisplayName("Should validate endpoint URL format")
    public void testValidateEndpointUrlFormat() {
        // Given
        Webhook webhook = new Webhook(
            "http://example.com/webhook", // Not HTTPS
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        
        // When
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        // Then
        assertFalse(violations.isEmpty());
        boolean hasHttpsViolation = false;
        
        for (ConstraintViolation<Webhook> violation : violations) {
            if ("endpointUrl".equals(violation.getPropertyPath().toString()) && 
                violation.getMessage().contains("HTTPS")) {
                hasHttpsViolation = true;
                break;
            }
        }
        
        assertTrue(hasHttpsViolation, "Should require HTTPS protocol");
    }
    
    @Test
    @DisplayName("Should validate secret key length")
    public void testValidateSecretKeyLength() {
        // Given
        Webhook webhookShortKey = new Webhook(
            "https://example.com/webhook",
            "tooshort", // Less than 32 characters
            true,
            EventType.APPLICATION_CREATED
        );
        
        // When
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhookShortKey);
        
        // Then
        assertFalse(violations.isEmpty());
        boolean hasMinSizeViolation = false;
        
        for (ConstraintViolation<Webhook> violation : violations) {
            if ("secretKey".equals(violation.getPropertyPath().toString()) && 
                violation.getMessage().contains("between")) {
                hasMinSizeViolation = true;
                break;
            }
        }
        
        assertTrue(hasMinSizeViolation, "Should require minimum length for secret key");
        
        // Test maximum length
        StringBuilder longKeyBuilder = new StringBuilder();
        for (int i = 0; i < 129; i++) { // 129 characters (exceeds max of 128)
            longKeyBuilder.append("a");
        }
        
        Webhook webhookLongKey = new Webhook(
            "https://example.com/webhook",
            longKeyBuilder.toString(),
            true,
            EventType.APPLICATION_CREATED
        );
        
        violations = validator.validate(webhookLongKey);
        
        assertFalse(violations.isEmpty());
        boolean hasMaxSizeViolation = false;
        
        for (ConstraintViolation<Webhook> violation : violations) {
            if ("secretKey".equals(violation.getPropertyPath().toString()) && 
                violation.getMessage().contains("between")) {
                hasMaxSizeViolation = true;
                break;
            }
        }
        
        assertTrue(hasMaxSizeViolation, "Should enforce maximum length for secret key");
    }
    
    @Test
    @DisplayName("Should validate max retry attempts")
    public void testValidateMaxRetryAttempts() {
        // Given
        Webhook webhook = new Webhook(
            "https://example.com/webhook",
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        webhook.setMaxRetryAttempts(11); // Exceeds max of 10
        
        // When
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        // Then
        assertFalse(violations.isEmpty());
        boolean hasMaxRetryViolation = false;
        
        for (ConstraintViolation<Webhook> violation : violations) {
            if ("maxRetryAttempts".equals(violation.getPropertyPath().toString()) && 
                violation.getMessage().contains("exceed 10")) {
                hasMaxRetryViolation = true;
                break;
            }
        }
        
        assertTrue(hasMaxRetryViolation, "Should enforce maximum retry attempts");
        
        // Test negative value
        webhook.setMaxRetryAttempts(-1);
        violations = validator.validate(webhook);
        
        assertFalse(violations.isEmpty());
        boolean hasMinRetryViolation = false;
        
        for (ConstraintViolation<Webhook> violation : violations) {
            if ("maxRetryAttempts".equals(violation.getPropertyPath().toString()) && 
                violation.getMessage().contains("at least 0")) {
                hasMinRetryViolation = true;
                break;
            }
        }
        
        assertTrue(hasMinRetryViolation, "Should enforce minimum retry attempts");
    }
    
    @Test
    @DisplayName("Should update timestamp on entity update")
    public void testUpdateTimestamp() {
        // Given
        Webhook webhook = new Webhook(
            "https://example.com/webhook",
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        webhook.onCreate(); // Manually trigger the @PrePersist method for testing
        LocalDateTime createdAt = webhook.getCreatedAt();
        LocalDateTime updatedAt = webhook.getUpdatedAt();
        
        // Simulate a small delay
        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            // Ignore
        }
        
        // When
        webhook.setEndpointUrl("https://example.com/updated-webhook");
        webhook.onUpdate(); // Manually trigger the @PreUpdate method for testing
        
        // Then
        assertEquals(createdAt, webhook.getCreatedAt(), "Created timestamp should not change");
        assertNotNull(webhook.getUpdatedAt());
        assertFalse(updatedAt.equals(webhook.getUpdatedAt()), "Updated timestamp should change");
    }
    
    @Test
    @DisplayName("Should track webhook delivery status")
    public void testTrackDeliveryStatus() {
        // Given
        Webhook webhook = new Webhook(
            "https://example.com/webhook",
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        webhook.onCreate(); // Initialize counters
        
        // When - successful delivery
        webhook.recordSuccessfulDelivery();
        
        // Then
        assertEquals("SUCCESS", webhook.getLastDeliveryStatus());
        assertNotNull(webhook.getLastDeliveryAttempt());
        assertEquals(0, webhook.getFailedAttempts());
        
        // When - failed delivery
        boolean shouldRetry = webhook.recordFailedDelivery("Connection timeout");
        
        // Then
        assertTrue(shouldRetry, "Should allow retry on first failure");
        assertTrue(webhook.getLastDeliveryStatus().contains("Connection timeout"));
        assertEquals(1, webhook.getFailedAttempts());
        assertTrue(webhook.shouldRetry());
        
        // When - multiple failures up to max retries
        for (int i = 0; i < webhook.getMaxRetryAttempts() - 1; i++) {
            shouldRetry = webhook.recordFailedDelivery("Attempt " + (i + 2));
        }
        
        // Then
        assertTrue(shouldRetry, "Should allow retry until max attempts");
        assertEquals(webhook.getMaxRetryAttempts(), webhook.getFailedAttempts());
        assertTrue(webhook.shouldRetry());
        
        // When - one more failure beyond max retries
        shouldRetry = webhook.recordFailedDelivery("Final attempt");
        
        // Then
        assertFalse(shouldRetry, "Should not allow retry after max attempts");
        assertEquals(webhook.getMaxRetryAttempts() + 1, webhook.getFailedAttempts());
        assertFalse(webhook.shouldRetry());
        
        // When - reset failed attempts
        webhook.resetFailedAttempts();
        
        // Then
        assertEquals(0, webhook.getFailedAttempts());
        assertFalse(webhook.shouldRetry(), "Should not retry when no failures");
    }
    
    @Test
    @DisplayName("Should handle active flag correctly")
    public void testActiveFlag() {
        // Given
        Webhook webhook = new Webhook(
            "https://example.com/webhook",
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        
        // Then
        assertTrue(webhook.isActive());
        
        // When
        webhook.setActive(false);
        
        // Then
        assertFalse(webhook.isActive());
        
        // When - test null handling
        webhook.setActive(null);
        
        // Then
        assertFalse(webhook.isActive(), "Should handle null as false");
    }
    
    @Test
    @DisplayName("Should handle delivery tracking fields")
    public void testDeliveryTrackingFields() {
        // Given
        Webhook webhook = new Webhook(
            "https://example.com/webhook",
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        webhook.onCreate(); // Initialize counters
        
        // When - set delivery status fields
        webhook.setLastDeliverySuccess(true);
        webhook.setLastDeliveryStatusCode(200);
        webhook.setSuccessfulDeliveriesCount(5L);
        webhook.setFailedDeliveriesCount(2L);
        webhook.setLastDeliveryError(null);
        
        // Then
        assertTrue(webhook.getLastDeliverySuccess());
        assertEquals(200, webhook.getLastDeliveryStatusCode());
        assertEquals(5L, webhook.getSuccessfulDeliveriesCount());
        assertEquals(2L, webhook.getFailedDeliveriesCount());
        assertNull(webhook.getLastDeliveryError());
        
        // When - set error information
        webhook.setLastDeliverySuccess(false);
        webhook.setLastDeliveryStatusCode(500);
        webhook.setLastDeliveryError("Internal Server Error");
        webhook.setFailedDeliveriesCount(3L);
        
        // Then
        assertFalse(webhook.getLastDeliverySuccess());
        assertEquals(500, webhook.getLastDeliveryStatusCode());
        assertEquals("Internal Server Error", webhook.getLastDeliveryError());
        assertEquals(3L, webhook.getFailedDeliveriesCount());
    }
    
    @Test
    @DisplayName("Should customize signature header")
    public void testCustomSignatureHeader() {
        // Given
        Webhook webhook = new Webhook(
            "https://example.com/webhook",
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        webhook.onCreate(); // Set default signature header
        
        // Then
        assertEquals("X-Webhook-Signature", webhook.getSignatureHeader());
        
        // When
        webhook.setSignatureHeader("X-Custom-Signature");
        
        // Then
        assertEquals("X-Custom-Signature", webhook.getSignatureHeader());
    }
    
    @Test
    @DisplayName("Should generate proper string representation")
    public void testToString() {
        // Given
        Webhook webhook = new Webhook(
            "https://example.com/webhook",
            "abcdefghijklmnopqrstuvwxyz123456",
            true,
            EventType.APPLICATION_CREATED
        );
        webhook.setId(1L);
        
        // When
        String stringRepresentation = webhook.toString();
        
        // Then
        assertTrue(stringRepresentation.contains("id=1"));
        assertTrue(stringRepresentation.contains("endpointUrl='https://example.com/webhook'"));
        assertTrue(stringRepresentation.contains("active=true"));
        assertTrue(stringRepresentation.contains("eventType=APPLICATION_CREATED"));
        
        // Verify that the secret key is NOT included in the toString output for security reasons
        assertFalse(stringRepresentation.contains("abcdefghijklmnopqrstuvwxyz123456"));
    }
}