package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link WebhookDeliveryException} class.
 * 
 * These tests verify the behavior of the WebhookDeliveryException for webhook delivery failure scenarios,
 * ensuring proper initialization, message formatting, and HTTP status code assignment.
 */
@DisplayName("WebhookDeliveryException Tests")
class WebhookDeliveryExceptionTest {

    private static final String TEST_MESSAGE = "Failed to deliver webhook notification";
    private static final String TEST_WEBHOOK_ID = "webhook-123";
    private static final String TEST_ENDPOINT = "https://example.com/webhook";
    private static final Integer TEST_ATTEMPT_COUNT = 3;

    @Test
    @DisplayName("Should create exception with message only")
    void shouldCreateExceptionWithMessageOnly() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(TEST_MESSAGE);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertNull(exception.getWebhookId());
        assertNull(exception.getEndpoint());
        assertNull(exception.getAttemptCount());
    }

    @Test
    @DisplayName("Should create exception with message and webhook ID")
    void shouldCreateExceptionWithMessageAndWebhookId() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(TEST_MESSAGE, TEST_WEBHOOK_ID);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertNull(exception.getEndpoint());
        assertNull(exception.getAttemptCount());
    }

    @Test
    @DisplayName("Should create exception with message, webhook ID, and endpoint")
    void shouldCreateExceptionWithMessageWebhookIdAndEndpoint() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT, exception.getEndpoint());
        assertNull(exception.getAttemptCount());
    }

    @Test
    @DisplayName("Should create exception with message, webhook ID, endpoint, and attempt count")
    void shouldCreateExceptionWithAllFields() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT, TEST_ATTEMPT_COUNT);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT, exception.getEndpoint());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
    }

    @Test
    @DisplayName("Should create exception with cause and all fields")
    void shouldCreateExceptionWithCauseAndAllFields() {
        // Given
        Throwable cause = new RuntimeException("Connection timeout");
        
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, cause, TEST_WEBHOOK_ID, TEST_ENDPOINT, TEST_ATTEMPT_COUNT);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT, exception.getEndpoint());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertEquals(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should format toString with all fields")
    void shouldFormatToStringWithAllFields() {
        // Given
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT, TEST_ATTEMPT_COUNT);
        
        // When
        String result = exception.toString();
        
        // Then
        assertTrue(result.contains(TEST_MESSAGE));
        assertTrue(result.contains(TEST_WEBHOOK_ID));
        assertTrue(result.contains(TEST_ENDPOINT));
        assertTrue(result.contains(TEST_ATTEMPT_COUNT.toString()));
    }

    @Test
    @DisplayName("Should determine retriability based on attempt count")
    void shouldDetermineRetriabilityBasedOnAttemptCount() {
        // Given
        WebhookDeliveryException retriableException = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT, 2);
        
        WebhookDeliveryException nonRetriableException = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT, 5);
        
        WebhookDeliveryException nullAttemptException = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT);
        
        // Then
        assertTrue(retriableException.isRetriable(5), "Should be retriable when attempts < max");
        assertFalse(nonRetriableException.isRetriable(5), "Should not be retriable when attempts >= max");
        assertTrue(nullAttemptException.isRetriable(5), "Should be retriable when attempt count is null");
    }

    @Test
    @DisplayName("Should create exception for next attempt with incremented count")
    void shouldCreateExceptionForNextAttemptWithIncrementedCount() {
        // Given
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT, 2);
        
        // When
        WebhookDeliveryException nextAttemptException = exception.forNextAttempt();
        
        // Then
        assertEquals(TEST_MESSAGE, nextAttemptException.getMessage());
        assertEquals(TEST_WEBHOOK_ID, nextAttemptException.getWebhookId());
        assertEquals(TEST_ENDPOINT, nextAttemptException.getEndpoint());
        assertEquals(3, nextAttemptException.getAttemptCount());
    }

    @Test
    @DisplayName("Should create exception for next attempt with count of 1 when original is null")
    void shouldCreateExceptionForNextAttemptWithCountOfOneWhenOriginalIsNull() {
        // Given
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT);
        
        // When
        WebhookDeliveryException nextAttemptException = exception.forNextAttempt();
        
        // Then
        assertEquals(TEST_MESSAGE, nextAttemptException.getMessage());
        assertEquals(TEST_WEBHOOK_ID, nextAttemptException.getWebhookId());
        assertEquals(TEST_ENDPOINT, nextAttemptException.getEndpoint());
        assertEquals(1, nextAttemptException.getAttemptCount());
    }
}