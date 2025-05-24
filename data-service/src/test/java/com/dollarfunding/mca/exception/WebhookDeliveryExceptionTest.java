package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link WebhookDeliveryException} class.
 * <p>
 * These tests verify the behavior of the WebhookDeliveryException class for 500 Internal Server Error
 * webhook delivery failure scenarios. The tests cover constructor variants, message formatting,
 * HTTP status code assignment, and webhook delivery error details retrieval.
 * </p>
 */
@DisplayName("WebhookDeliveryException Tests")
public class WebhookDeliveryExceptionTest {

    private static final String TEST_MESSAGE = "Test webhook delivery exception message";
    private static final String TEST_WEBHOOK_ID = "webhook-123";
    private static final String TEST_ENDPOINT_URL = "https://example.com/webhook";
    private static final Integer TEST_ATTEMPT_COUNT = 3;
    private static final String TEST_RESPONSE_STATUS = "502 Bad Gateway";

    @Test
    @DisplayName("Should create exception with message only")
    void shouldCreateExceptionWithMessageOnly() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(TEST_MESSAGE);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertNull(exception.getWebhookId());
        assertNull(exception.getEndpointUrl());
        assertNull(exception.getAttemptCount());
        assertNull(exception.getResponseStatus());
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message and cause")
    void shouldCreateExceptionWithMessageAndCause() {
        // Given
        Throwable cause = new RuntimeException("Root cause");

        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(TEST_MESSAGE, cause);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertNull(exception.getWebhookId());
        assertNull(exception.getEndpointUrl());
        assertNull(exception.getAttemptCount());
        assertNull(exception.getResponseStatus());
        assertSame(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message and webhook details")
    void shouldCreateExceptionWithMessageAndWebhookDetails() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertNull(exception.getResponseStatus());
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message, webhook details, and response status")
    void shouldCreateExceptionWithMessageWebhookDetailsAndResponseStatus() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertEquals(TEST_RESPONSE_STATUS, exception.getResponseStatus());
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message, cause, webhook details, and response status")
    void shouldCreateExceptionWithMessageCauseWebhookDetailsAndResponseStatus() {
        // Given
        Throwable cause = new RuntimeException("Root cause");

        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, cause, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertEquals(TEST_RESPONSE_STATUS, exception.getResponseStatus());
        assertSame(cause, exception.getCause());
    }
    
    @Test
    @DisplayName("Should format toString with webhook details")
    void shouldFormatToStringWithWebhookDetails() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);
        String toStringResult = exception.toString();
        
        // Then
        assertTrue(toStringResult.contains(TEST_MESSAGE));
        assertTrue(toStringResult.contains("webhookId=" + TEST_WEBHOOK_ID));
        assertTrue(toStringResult.contains("endpointUrl=" + TEST_ENDPOINT_URL));
        assertTrue(toStringResult.contains("attemptCount=" + TEST_ATTEMPT_COUNT));
        assertTrue(toStringResult.contains("responseStatus=" + TEST_RESPONSE_STATUS));
    }
    
    @Test
    @DisplayName("Should format toString with partial webhook details")
    void shouldFormatToStringWithPartialWebhookDetails() {
        // When
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, null, null);
        String toStringResult = exception.toString();
        
        // Then
        assertTrue(toStringResult.contains(TEST_MESSAGE));
        assertTrue(toStringResult.contains("webhookId=" + TEST_WEBHOOK_ID));
        assertTrue(toStringResult.contains("endpointUrl=" + TEST_ENDPOINT_URL));
        assertFalse(toStringResult.contains("attemptCount="));
        assertFalse(toStringResult.contains("responseStatus="));
    }
    
    @Test
    @DisplayName("Should create connection timeout exception with factory method")
    void shouldCreateConnectionTimeoutExceptionWithFactoryMethod() {
        // When
        WebhookDeliveryException exception = WebhookDeliveryException.connectionTimeout(
                TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT);
        
        // Then
        assertTrue(exception.getMessage().contains("timed out"));
        assertTrue(exception.getMessage().contains(TEST_ATTEMPT_COUNT.toString()));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertEquals("TIMEOUT", exception.getResponseStatus());
    }
    
    @Test
    @DisplayName("Should create invalid response exception with factory method")
    void shouldCreateInvalidResponseExceptionWithFactoryMethod() {
        // When
        WebhookDeliveryException exception = WebhookDeliveryException.invalidResponse(
                TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);
        
        // Then
        assertTrue(exception.getMessage().contains("invalid response"));
        assertTrue(exception.getMessage().contains(TEST_RESPONSE_STATUS));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertEquals(TEST_RESPONSE_STATUS, exception.getResponseStatus());
    }
    
    @Test
    @DisplayName("Should create max retry exceeded exception with factory method")
    void shouldCreateMaxRetryExceededExceptionWithFactoryMethod() {
        // When
        WebhookDeliveryException exception = WebhookDeliveryException.maxRetryExceeded(
                TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT);
        
        // Then
        assertTrue(exception.getMessage().contains("maximum retry attempts"));
        assertTrue(exception.getMessage().contains(TEST_ATTEMPT_COUNT.toString()));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertEquals("MAX_RETRY_EXCEEDED", exception.getResponseStatus());
    }
    
    @Test
    @DisplayName("Should provide consistent error details through getters")
    void shouldProvideConsistentErrorDetailsThroughGetters() {
        // Given
        WebhookDeliveryException exception = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);
        
        // When/Then - Verify consistency across multiple calls
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId());
        assertEquals(TEST_WEBHOOK_ID, exception.getWebhookId()); // Second call should return same value
        
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl());
        assertEquals(TEST_ENDPOINT_URL, exception.getEndpointUrl()); // Second call should return same value
        
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount());
        assertEquals(TEST_ATTEMPT_COUNT, exception.getAttemptCount()); // Second call should return same value
        
        assertEquals(TEST_RESPONSE_STATUS, exception.getResponseStatus());
        assertEquals(TEST_RESPONSE_STATUS, exception.getResponseStatus()); // Second call should return same value
    }
    
    @Test
    @DisplayName("Should always set HTTP status code to 500 Internal Server Error")
    void shouldAlwaysSetHttpStatusCodeTo500InternalServerError() {
        // Create exceptions with different constructors
        WebhookDeliveryException exception1 = new WebhookDeliveryException(TEST_MESSAGE);
        WebhookDeliveryException exception2 = new WebhookDeliveryException(TEST_MESSAGE, new RuntimeException());
        WebhookDeliveryException exception3 = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT);
        WebhookDeliveryException exception4 = new WebhookDeliveryException(
                TEST_MESSAGE, TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);
        WebhookDeliveryException exception5 = new WebhookDeliveryException(
                TEST_MESSAGE, new RuntimeException(), TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, 
                TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);
        WebhookDeliveryException exception6 = WebhookDeliveryException.connectionTimeout(
                TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT);
        WebhookDeliveryException exception7 = WebhookDeliveryException.invalidResponse(
                TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT, TEST_RESPONSE_STATUS);
        WebhookDeliveryException exception8 = WebhookDeliveryException.maxRetryExceeded(
                TEST_WEBHOOK_ID, TEST_ENDPOINT_URL, TEST_ATTEMPT_COUNT);
        
        // Then - All should have 500 Internal Server Error status
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception1.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception2.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception3.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception4.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception5.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception6.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception7.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception8.getHttpStatus());
        
        assertEquals(500, exception1.getStatusCode());
        assertEquals(500, exception2.getStatusCode());
        assertEquals(500, exception3.getStatusCode());
        assertEquals(500, exception4.getStatusCode());
        assertEquals(500, exception5.getStatusCode());
        assertEquals(500, exception6.getStatusCode());
        assertEquals(500, exception7.getStatusCode());
        assertEquals(500, exception8.getStatusCode());
    }