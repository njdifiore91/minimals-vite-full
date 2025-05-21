package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

/**
 * Exception thrown when errors occur during webhook notification delivery.
 * This exception is used by the notification service to indicate failures in webhook delivery,
 * such as connection timeouts or invalid responses.
 */
public class WebhookDeliveryException extends BaseException {

    private final String webhookId;
    private final String endpoint;
    private final Integer attemptCount;

    /**
     * Constructs a new WebhookDeliveryException with the specified detail message.
     *
     * @param message the detail message
     */
    public WebhookDeliveryException(String message) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.webhookId = null;
        this.endpoint = null;
        this.attemptCount = null;
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified detail message and webhook ID.
     *
     * @param message   the detail message
     * @param webhookId the ID of the webhook that failed to deliver
     */
    public WebhookDeliveryException(String message, String webhookId) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.webhookId = webhookId;
        this.endpoint = null;
        this.attemptCount = null;
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified detail message, webhook ID, and endpoint.
     *
     * @param message   the detail message
     * @param webhookId the ID of the webhook that failed to deliver
     * @param endpoint  the endpoint URL that failed to receive the webhook
     */
    public WebhookDeliveryException(String message, String webhookId, String endpoint) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.webhookId = webhookId;
        this.endpoint = endpoint;
        this.attemptCount = null;
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified detail message, webhook ID, endpoint, and attempt count.
     *
     * @param message      the detail message
     * @param webhookId    the ID of the webhook that failed to deliver
     * @param endpoint     the endpoint URL that failed to receive the webhook
     * @param attemptCount the number of delivery attempts made so far
     */
    public WebhookDeliveryException(String message, String webhookId, String endpoint, Integer attemptCount) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.webhookId = webhookId;
        this.endpoint = endpoint;
        this.attemptCount = attemptCount;
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified detail message, cause, webhook ID, endpoint, and attempt count.
     *
     * @param message      the detail message
     * @param cause        the cause of the exception
     * @param webhookId    the ID of the webhook that failed to deliver
     * @param endpoint     the endpoint URL that failed to receive the webhook
     * @param attemptCount the number of delivery attempts made so far
     */
    public WebhookDeliveryException(String message, Throwable cause, String webhookId, String endpoint, Integer attemptCount) {
        super(message, cause, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.webhookId = webhookId;
        this.endpoint = endpoint;
        this.attemptCount = attemptCount;
    }

    /**
     * Gets the ID of the webhook that failed to deliver.
     *
     * @return the webhook ID, or null if not specified
     */
    public String getWebhookId() {
        return webhookId;
    }

    /**
     * Gets the endpoint URL that failed to receive the webhook.
     *
     * @return the endpoint URL, or null if not specified
     */
    public String getEndpoint() {
        return endpoint;
    }

    /**
     * Gets the number of delivery attempts made so far.
     *
     * @return the attempt count, or null if not specified
     */
    public Integer getAttemptCount() {
        return attemptCount;
    }

    /**
     * Determines if this is a retriable exception based on the attempt count and error type.
     * 
     * @param maxAttempts the maximum number of retry attempts allowed
     * @return true if the webhook delivery should be retried, false otherwise
     */
    public boolean isRetriable(int maxAttempts) {
        // If no attempt count is specified, assume it's retriable
        if (attemptCount == null) {
            return true;
        }
        
        // If we've reached the maximum number of attempts, don't retry
        if (attemptCount >= maxAttempts) {
            return false;
        }
        
        // Otherwise, it's retriable
        return true;
    }

    /**
     * Creates a new WebhookDeliveryException for the next retry attempt.
     *
     * @return a new WebhookDeliveryException with an incremented attempt count
     */
    public WebhookDeliveryException forNextAttempt() {
        int nextAttempt = (attemptCount == null) ? 1 : attemptCount + 1;
        return new WebhookDeliveryException(
                getMessage(),
                getCause(),
                webhookId,
                endpoint,
                nextAttempt
        );
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder("WebhookDeliveryException: ");
        sb.append(getMessage());
        
        if (webhookId != null) {
            sb.append(", webhookId='").append(webhookId).append('\'');
        }
        
        if (endpoint != null) {
            sb.append(", endpoint='").append(endpoint).append('\'');
        }
        
        if (attemptCount != null) {
            sb.append(", attemptCount=").append(attemptCount);
        }
        
        return sb.toString();
    }
}