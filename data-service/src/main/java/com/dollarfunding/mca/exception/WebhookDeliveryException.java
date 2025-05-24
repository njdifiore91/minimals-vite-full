package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

/**
 * Exception thrown when errors occur during webhook notification delivery.
 * <p>
 * This exception provides details about the webhook endpoint and delivery attempt,
 * and is used by the notification service to indicate failures in webhook delivery,
 * such as connection timeouts or invalid responses.
 * </p>
 * <p>
 * It extends BaseException with a default HTTP status code of 500 (Internal Server Error).
 * </p>
 */
public class WebhookDeliveryException extends BaseException {

    private final String webhookId;
    private final String endpointUrl;
    private final Integer attemptCount;
    private final String responseStatus;

    /**
     * Constructs a new WebhookDeliveryException with the specified message.
     *
     * @param message the detail message
     */
    public WebhookDeliveryException(String message) {
        this(message, null, null, null, null);
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified message and cause.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     */
    public WebhookDeliveryException(String message, Throwable cause) {
        this(message, cause, null, null, null, null);
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified message and webhook details.
     *
     * @param message      the detail message
     * @param webhookId    the identifier of the webhook configuration
     * @param endpointUrl  the URL of the webhook endpoint
     * @param attemptCount the number of delivery attempts made
     */
    public WebhookDeliveryException(String message, String webhookId, String endpointUrl, Integer attemptCount) {
        this(message, webhookId, endpointUrl, attemptCount, null);
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified message, webhook details, and response status.
     *
     * @param message        the detail message
     * @param webhookId      the identifier of the webhook configuration
     * @param endpointUrl    the URL of the webhook endpoint
     * @param attemptCount   the number of delivery attempts made
     * @param responseStatus the HTTP status received from the webhook endpoint
     */
    public WebhookDeliveryException(String message, String webhookId, String endpointUrl, 
                                   Integer attemptCount, String responseStatus) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR);
        this.webhookId = webhookId;
        this.endpointUrl = endpointUrl;
        this.attemptCount = attemptCount;
        this.responseStatus = responseStatus;
    }

    /**
     * Constructs a new WebhookDeliveryException with the specified message, cause, webhook details, and response status.
     *
     * @param message        the detail message
     * @param cause          the cause of this exception
     * @param webhookId      the identifier of the webhook configuration
     * @param endpointUrl    the URL of the webhook endpoint
     * @param attemptCount   the number of delivery attempts made
     * @param responseStatus the HTTP status received from the webhook endpoint
     */
    public WebhookDeliveryException(String message, Throwable cause, String webhookId, 
                                   String endpointUrl, Integer attemptCount, String responseStatus) {
        super(message, cause, HttpStatus.INTERNAL_SERVER_ERROR);
        this.webhookId = webhookId;
        this.endpointUrl = endpointUrl;
        this.attemptCount = attemptCount;
        this.responseStatus = responseStatus;
    }

    /**
     * Returns the identifier of the webhook configuration.
     *
     * @return the webhook identifier
     */
    public String getWebhookId() {
        return webhookId;
    }

    /**
     * Returns the URL of the webhook endpoint.
     *
     * @return the endpoint URL
     */
    public String getEndpointUrl() {
        return endpointUrl;
    }

    /**
     * Returns the number of delivery attempts made.
     *
     * @return the attempt count
     */
    public Integer getAttemptCount() {
        return attemptCount;
    }

    /**
     * Returns the HTTP status received from the webhook endpoint.
     *
     * @return the response status
     */
    public String getResponseStatus() {
        return responseStatus;
    }

    /**
     * Returns a string representation of this exception including webhook details.
     *
     * @return a string representation of this exception
     */
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder(super.toString());
        
        if (webhookId != null) {
            sb.append(", webhookId=").append(webhookId);
        }
        
        if (endpointUrl != null) {
            sb.append(", endpointUrl=").append(endpointUrl);
        }
        
        if (attemptCount != null) {
            sb.append(", attemptCount=").append(attemptCount);
        }
        
        if (responseStatus != null) {
            sb.append(", responseStatus=").append(responseStatus);
        }
        
        return sb.toString();
    }

    /**
     * Creates a new WebhookDeliveryException for connection timeout scenarios.
     *
     * @param webhookId    the identifier of the webhook configuration
     * @param endpointUrl  the URL of the webhook endpoint
     * @param attemptCount the number of delivery attempts made
     * @return a new WebhookDeliveryException
     */
    public static WebhookDeliveryException connectionTimeout(String webhookId, String endpointUrl, Integer attemptCount) {
        return new WebhookDeliveryException(
            "Webhook delivery timed out after " + attemptCount + " attempts",
            webhookId,
            endpointUrl,
            attemptCount,
            "TIMEOUT"
        );
    }

    /**
     * Creates a new WebhookDeliveryException for invalid response scenarios.
     *
     * @param webhookId      the identifier of the webhook configuration
     * @param endpointUrl    the URL of the webhook endpoint
     * @param attemptCount   the number of delivery attempts made
     * @param responseStatus the HTTP status received from the webhook endpoint
     * @return a new WebhookDeliveryException
     */
    public static WebhookDeliveryException invalidResponse(String webhookId, String endpointUrl, 
                                                         Integer attemptCount, String responseStatus) {
        return new WebhookDeliveryException(
            "Webhook endpoint returned invalid response: " + responseStatus,
            webhookId,
            endpointUrl,
            attemptCount,
            responseStatus
        );
    }

    /**
     * Creates a new WebhookDeliveryException for max retry exceeded scenarios.
     *
     * @param webhookId    the identifier of the webhook configuration
     * @param endpointUrl  the URL of the webhook endpoint
     * @param attemptCount the number of delivery attempts made
     * @return a new WebhookDeliveryException
     */
    public static WebhookDeliveryException maxRetryExceeded(String webhookId, String endpointUrl, Integer attemptCount) {
        return new WebhookDeliveryException(
            "Webhook delivery failed after maximum retry attempts: " + attemptCount,
            webhookId,
            endpointUrl,
            attemptCount,
            "MAX_RETRY_EXCEEDED"
        );
    }
}