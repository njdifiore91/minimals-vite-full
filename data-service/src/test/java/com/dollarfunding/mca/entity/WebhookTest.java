package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Set;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Unit tests for the {@link Webhook} entity class.
 * <p>
 * These tests verify the JPA mapping, field validation, and security features of the Webhook entity.
 * This includes validation of required fields, proper mapping of enum values for event type,
 * secure storage of webhook secret keys, and timestamp generation.
 * </p>
 * <p>
 * The Webhook entity is used by the notification service to deliver webhook notifications to third-party
 * systems with retry capability. It supports configurable endpoints with JSON payload delivery and
 * implements retry logic for failed webhook deliveries.
 * </p>
 * <p>
 * Key features tested:
 * <ul>
 *   <li>Field validation (required fields, URL format, size constraints)</li>
 *   <li>Enum mapping (EventType)</li>
 *   <li>Secure storage of secret keys</li>
 *   <li>Creation and update timestamp generation</li>
 *   <li>Active flag behavior</li>
 *   <li>Webhook delivery status and retry attempt tracking</li>
 * </ul>
 * </p>
 */
public class WebhookTest {

    private Validator validator;
    private Webhook webhook;

    @BeforeEach
    public void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Create a valid webhook for testing
        webhook = new Webhook(
            "https://api.example.com/webhooks/mca-notifications",
            "secretKey1234567890", // Meets minimum 16 character requirement
            true,
            EventType.APPLICATION_CREATED
        );
    }
    
    /**
     * Helper method to create a webhook with specific values for testing.
     * 
     * @param endpointUrl The URL of the webhook endpoint
     * @param secretKey The secret key for HMAC signing
     * @param active Whether the webhook is active
     * @param eventType The type of event that triggers this webhook
     * @return A new Webhook instance with the specified values
     */
    private Webhook createWebhook(String endpointUrl, String secretKey, Boolean active, EventType eventType) {
        return new Webhook(endpointUrl, secretKey, active, eventType);
    }

    @Test
    @DisplayName("Should create a valid webhook with all required fields")
    public void testCreateValidWebhook() {
        // Validate the webhook
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        // Assert no validation errors
        assertTrue(violations.isEmpty(), "Valid webhook should not have validation errors");
        
        // Assert field values are set correctly
        assertEquals("https://api.example.com/webhooks/mca-notifications", webhook.getEndpointUrl());
        assertEquals("secretKey1234567890", webhook.getSecretKey());
        assertTrue(webhook.getActive());
        assertEquals(EventType.APPLICATION_CREATED, webhook.getEventType());
        assertEquals(3, webhook.getMaxRetryAttempts()); // Default value
        assertEquals(0, webhook.getConsecutiveFailures()); // Default value
        assertNull(webhook.getLastSuccessAt()); // Should be null initially
        assertNull(webhook.getLastFailureAt()); // Should be null initially
    }
    
    @Test
    @DisplayName("Should create webhook with custom retry attempts")
    public void testCreateWebhookWithCustomRetryAttempts() {
        // Create webhook with custom max retry attempts
        webhook.setMaxRetryAttempts(5);
        
        // Validate the webhook
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        // Assert no validation errors
        assertTrue(violations.isEmpty(), "Valid webhook should not have validation errors");
        
        // Assert max retry attempts is set correctly
        assertEquals(5, webhook.getMaxRetryAttempts());
    }

    @Test
    @DisplayName("Should fail validation when endpoint URL is null")
    public void testEndpointUrlNull() {
        webhook.setEndpointUrl(null);
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertEquals(1, violations.size());
        assertEquals("Endpoint URL is required", violations.iterator().next().getMessage());
    }

    @Test
    @DisplayName("Should fail validation when endpoint URL is empty")
    public void testEndpointUrlEmpty() {
        webhook.setEndpointUrl("");
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertEquals(1, violations.size());
        assertEquals("Endpoint URL is required", violations.iterator().next().getMessage());
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "not-a-url",
        "ftp://example.com",
        "example.com",
        "www.example.com"
    })
    @DisplayName("Should fail validation when endpoint URL format is invalid")
    public void testEndpointUrlInvalidFormat(String invalidUrl) {
        webhook.setEndpointUrl(invalidUrl);
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertEquals(1, violations.size());
        assertEquals("Endpoint URL must be a valid URL", violations.iterator().next().getMessage());
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "https://api.example.com/webhooks",
        "http://localhost:8080/webhook-receiver",
        "https://webhook.site/123456789",
        "https://api.example.com/webhooks?token=abc123"
    })
    @DisplayName("Should pass validation with valid endpoint URL formats")
    public void testEndpointUrlValidFormat(String validUrl) {
        webhook.setEndpointUrl(validUrl);
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertTrue(violations.isEmpty(), "Valid URL should not have validation errors");
    }

    @Test
    @DisplayName("Should fail validation when secret key is null")
    public void testSecretKeyNull() {
        webhook.setSecretKey(null);
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertEquals(1, violations.size());
        assertEquals("Secret key is required", violations.iterator().next().getMessage());
    }

    @Test
    @DisplayName("Should fail validation when secret key is too short")
    public void testSecretKeyTooShort() {
        webhook.setSecretKey("short");
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertEquals(1, violations.size());
        assertEquals("Secret key must be at least 16 characters long", violations.iterator().next().getMessage());
    }

    @Test
    @DisplayName("Should fail validation when active flag is null")
    public void testActiveNull() {
        webhook.setActive(null);
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertEquals(1, violations.size());
        assertEquals("Active status is required", violations.iterator().next().getMessage());
    }

    @Test
    @DisplayName("Should fail validation when event type is null")
    public void testEventTypeNull() {
        webhook.setEventType(null);
        
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        
        assertEquals(1, violations.size());
        assertEquals("Event type is required", violations.iterator().next().getMessage());
    }

    @Test
    @DisplayName("Should set creation and update timestamps on persist")
    public void testTimestampGeneration() {
        // Create a new webhook for this test
        Webhook timestampWebhook = createWebhook(
            "https://api.example.com/webhooks/timestamp-test",
            "secretKey1234567890",
            true,
            EventType.APPLICATION_CREATED
        );
        
        // Verify timestamps are null before persistence
        assertNull(timestampWebhook.getCreatedAt(), "CreatedAt should be null before persistence");
        assertNull(timestampWebhook.getUpdatedAt(), "UpdatedAt should be null before persistence");
        
        // Call the onCreate method to simulate JPA @PrePersist
        timestampWebhook.onCreate();
        
        // Verify timestamps are set
        assertNotNull(timestampWebhook.getCreatedAt(), "CreatedAt should be set after persistence");
        assertNotNull(timestampWebhook.getUpdatedAt(), "UpdatedAt should be set after persistence");
        
        // Both timestamps should be the same on creation
        assertEquals(timestampWebhook.getCreatedAt(), timestampWebhook.getUpdatedAt(), 
                    "CreatedAt and UpdatedAt should be the same on creation");
        
        // Store the original timestamps
        LocalDateTime originalCreatedAt = timestampWebhook.getCreatedAt();
        LocalDateTime originalUpdatedAt = timestampWebhook.getUpdatedAt();
        
        // Wait a moment to ensure time difference
        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            // Ignore
        }
        
        // Call the onUpdate method to simulate JPA @PreUpdate
        timestampWebhook.onUpdate();
        
        // Verify createdAt remains unchanged but updatedAt is updated
        assertEquals(originalCreatedAt, timestampWebhook.getCreatedAt(), 
                    "CreatedAt should remain unchanged on update");
        assertNotEquals(originalUpdatedAt, timestampWebhook.getUpdatedAt(), 
                       "UpdatedAt should be updated on update");
        assertTrue(timestampWebhook.getUpdatedAt().isAfter(originalUpdatedAt), 
                  "New UpdatedAt should be after original UpdatedAt");
    }

    @Test
    @DisplayName("Should record successful webhook delivery")
    public void testRecordSuccess() {
        // Set some initial failure state
        webhook.setConsecutiveFailures(2);
        LocalDateTime beforeSuccess = LocalDateTime.now();
        
        // Wait a moment to ensure time difference
        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            // Ignore
        }
        
        // Record a successful delivery
        webhook.recordSuccess();
        
        // Verify the state is updated correctly
        assertEquals(0, webhook.getConsecutiveFailures(), "Consecutive failures should be reset to 0");
        assertNotNull(webhook.getLastSuccessAt(), "Last success timestamp should be set");
        assertTrue(webhook.getLastSuccessAt().isAfter(beforeSuccess), 
                  "Last success timestamp should be after the test started");
    }

    @Test
    @DisplayName("Should record failed webhook delivery and not deactivate when under max retries")
    public void testRecordFailureUnderMaxRetries() {
        // Set max retry attempts
        webhook.setMaxRetryAttempts(3);
        webhook.setConsecutiveFailures(1);
        LocalDateTime beforeFailure = LocalDateTime.now();
        
        // Wait a moment to ensure time difference
        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            // Ignore
        }
        
        // Record a failure
        boolean deactivated = webhook.recordFailure();
        
        // Verify the state is updated correctly
        assertFalse(deactivated, "Webhook should not be deactivated when under max retries");
        assertEquals(2, webhook.getConsecutiveFailures(), "Consecutive failures should be incremented");
        assertNotNull(webhook.getLastFailureAt(), "Last failure timestamp should be set");
        assertTrue(webhook.getLastFailureAt().isAfter(beforeFailure), 
                  "Last failure timestamp should be after the test started");
        assertTrue(webhook.getActive(), "Webhook should still be active");
    }

    @Test
    @DisplayName("Should record failed webhook delivery and deactivate when max retries reached")
    public void testRecordFailureMaxRetriesReached() {
        // Set max retry attempts and consecutive failures to one less
        webhook.setMaxRetryAttempts(3);
        webhook.setConsecutiveFailures(2);
        LocalDateTime beforeFailure = LocalDateTime.now();
        
        // Wait a moment to ensure time difference
        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            // Ignore
        }
        
        // Record a failure that should trigger deactivation
        boolean deactivated = webhook.recordFailure();
        
        // Verify the state is updated correctly
        assertTrue(deactivated, "Webhook should be deactivated when max retries reached");
        assertEquals(3, webhook.getConsecutiveFailures(), "Consecutive failures should be incremented");
        assertNotNull(webhook.getLastFailureAt(), "Last failure timestamp should be set");
        assertTrue(webhook.getLastFailureAt().isAfter(beforeFailure), 
                  "Last failure timestamp should be after the test started");
        assertFalse(webhook.getActive(), "Webhook should be deactivated");
    }

    @Test
    @DisplayName("Should correctly determine if webhook should trigger for event type")
    public void testShouldTriggerFor() {
        // Active webhook should trigger for its event type
        webhook.setActive(true);
        webhook.setEventType(EventType.APPLICATION_CREATED);
        
        assertTrue(webhook.shouldTriggerFor(EventType.APPLICATION_CREATED));
        assertFalse(webhook.shouldTriggerFor(EventType.APPLICATION_UPDATED));
        
        // Inactive webhook should not trigger for any event type
        webhook.setActive(false);
        assertFalse(webhook.shouldTriggerFor(EventType.APPLICATION_CREATED));
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("Should generate sample payload based on event type")
    public void testGenerateSamplePayload(EventType eventType) {
        // Set event type
        webhook.setEventType(eventType);
        
        // Generate sample payload
        Object payload = webhook.generateSamplePayload();
        
        // Verify payload is not null and is a Map
        assertNotNull(payload);
        assertTrue(payload instanceof Map);
        
        @SuppressWarnings("unchecked")
        Map<String, Object> payloadMap = (Map<String, Object>) payload;
        
        // Verify payload contains expected fields
        assertEquals(eventType.name(), payloadMap.get("event_type"));
        assertTrue(payloadMap.containsKey("event_id"));
        assertTrue(payloadMap.containsKey("timestamp"));
        assertTrue(payloadMap.containsKey("data"));
        
        // Verify data structure based on event type
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) payloadMap.get("data");
        
        if (eventType == EventType.APPLICATION_CREATED || 
            eventType == EventType.APPLICATION_UPDATED ||
            eventType == EventType.APPLICATION_APPROVED ||
            eventType == EventType.APPLICATION_REJECTED) {
            // Application events should have application data
            assertTrue(data.containsKey("application_id"));
            assertTrue(data.containsKey("merchant"));
        } else if (eventType == EventType.DOCUMENT_UPLOADED ||
                   eventType == EventType.DOCUMENT_PROCESSED) {
            // Document events should have document data
            assertTrue(data.containsKey("document_id"));
            assertTrue(data.containsKey("application_id"));
            assertTrue(data.containsKey("document_type"));
        }
    }

    @Test
    @DisplayName("Should implement equals and hashCode based on ID")
    public void testEqualsAndHashCode() {
        Webhook webhook1 = createWebhook(
            "https://api.example.com/webhooks/test1",
            "secretKey1234567890",
            true,
            EventType.APPLICATION_CREATED
        );
        webhook1.setId(1L);
        
        Webhook webhook2 = createWebhook(
            "https://api.example.com/webhooks/test2", // Different URL
            "differentSecretKey", // Different secret key
            false, // Different active status
            EventType.APPLICATION_UPDATED // Different event type
        );
        webhook2.setId(1L); // Same ID
        
        Webhook webhook3 = createWebhook(
            "https://api.example.com/webhooks/test1", // Same URL as webhook1
            "secretKey1234567890", // Same secret key as webhook1
            true, // Same active status as webhook1
            EventType.APPLICATION_CREATED // Same event type as webhook1
        );
        webhook3.setId(2L); // Different ID
        
        // Test equals - should be based only on ID
        assertEquals(webhook1, webhook2, "Webhooks with same ID should be equal regardless of other fields");
        assertNotEquals(webhook1, webhook3, "Webhooks with different IDs should not be equal");
        assertNotEquals(webhook1, null, "Webhook should not be equal to null");
        assertNotEquals(webhook1, "not a webhook", "Webhook should not be equal to other types");
        
        // Test hashCode - should be based only on ID
        assertEquals(webhook1.hashCode(), webhook2.hashCode(), 
                    "Webhooks with same ID should have same hashCode");
        assertNotEquals(webhook1.hashCode(), webhook3.hashCode(), 
                       "Webhooks with different IDs should have different hashCode");
    }

    @Test
    @DisplayName("Should implement toString with important fields")
    public void testToString() {
        webhook.setId(1L);
        
        String toString = webhook.toString();
        
        // Verify toString contains important fields
        assertTrue(toString.contains("id=1"));
        assertTrue(toString.contains("endpointUrl='https://api.example.com/webhooks/mca-notifications'"));
        assertTrue(toString.contains("active=true"));
        assertTrue(toString.contains("eventType=APPLICATION_CREATED"));
        assertTrue(toString.contains("consecutiveFailures=0"));
        
        // Verify toString does NOT contain the secret key for security reasons
        assertFalse(toString.contains(webhook.getSecretKey()), 
                   "toString should not expose the secret key");
    }

    @Test
    @DisplayName("Should support description field with size validation")
    public void testDescriptionSizeValidation() {
        // Valid description (under 500 chars)
        webhook.setDescription("This webhook sends notifications to our CRM system when new applications are created.");
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        assertTrue(violations.isEmpty());
        
        // Invalid description (over 500 chars)
        StringBuilder longDescription = new StringBuilder();
        for (int i = 0; i < 51; i++) {
            longDescription.append("This is a very long description that exceeds the maximum allowed size. ");
        }
        webhook.setDescription(longDescription.toString());
        
        violations = validator.validate(webhook);
        assertEquals(1, violations.size());
        assertEquals("Description cannot exceed 500 characters", violations.iterator().next().getMessage());
    }
    
    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("Should test all EventType values with webhook")
    public void testAllEventTypes(EventType eventType) {
        webhook.setEventType(eventType);
        Set<ConstraintViolation<Webhook>> violations = validator.validate(webhook);
        assertTrue(violations.isEmpty(), "Webhook with event type " + eventType + " should be valid");
        
        // Verify event type is correctly stored and retrieved
        assertEquals(eventType, webhook.getEventType());
        
        // Verify shouldTriggerFor works correctly for this event type
        webhook.setActive(true);
        assertTrue(webhook.shouldTriggerFor(eventType));
        
        // Verify other event types don't trigger this webhook
        for (EventType otherType : EventType.values()) {
            if (otherType != eventType) {
                assertFalse(webhook.shouldTriggerFor(otherType));
            }
        }
    }
    
    @Test
    @DisplayName("Should test webhook with different max retry attempts")
    public void testMaxRetryAttempts() {
        // Test with different max retry attempts
        for (int maxRetries = 1; maxRetries <= 5; maxRetries++) {
            // Create a new webhook for each test to avoid state interference
            Webhook testWebhook = createWebhook(
                "https://api.example.com/webhooks/retry-test",
                "secretKey1234567890",
                true,
                EventType.APPLICATION_CREATED
            );
            testWebhook.setMaxRetryAttempts(maxRetries);
            testWebhook.setConsecutiveFailures(0);
            
            // Record failures up to max retries
            for (int i = 0; i < maxRetries - 1; i++) {
                boolean deactivated = testWebhook.recordFailure();
                assertFalse(deactivated, "Webhook should not be deactivated before max retries");
                assertTrue(testWebhook.getActive(), "Webhook should still be active");
                assertEquals(i + 1, testWebhook.getConsecutiveFailures());
                assertNotNull(testWebhook.getLastFailureAt(), "Last failure timestamp should be set");
            }
            
            // Final failure should deactivate the webhook
            boolean deactivated = testWebhook.recordFailure();
            assertTrue(deactivated, "Webhook should be deactivated at max retries");
            assertFalse(testWebhook.getActive(), "Webhook should be inactive");
            assertEquals(maxRetries, testWebhook.getConsecutiveFailures());
        }
    }
}