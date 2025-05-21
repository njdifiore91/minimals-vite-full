package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

/**
 * DTO class for creating or updating webhook configurations.
 * This class defines the structure for incoming webhook data with validation annotations for required fields.
 * It serves as the contract for webhook configuration operations in the REST API.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WebhookRequestDTO {

    /**
     * The URL where webhook notifications will be sent.
     * Must be a valid URL starting with http:// or https://
     */
    @NotBlank(message = "Endpoint URL is required")
    @Size(max = 255, message = "Endpoint URL cannot exceed 255 characters")
    @Pattern(regexp = "^(https?://)[a-zA-Z0-9\\-\\._~:/?#\\[\\]@!$&'()*+,;=]+$", 
             message = "Endpoint URL must be a valid URL starting with http:// or https://")
    @JsonProperty("endpoint_url")
    private String endpointUrl;

    /**
     * The type of event that triggers this webhook.
     * Must be a valid event type from the EventType enum.
     */
    @NotBlank(message = "Event type is required")
    @JsonProperty("event_type")
    private String eventType;

    /**
     * The secret key used for HMAC signing of webhook payloads.
     * This is used to verify the authenticity of webhook deliveries.
     */
    @NotBlank(message = "Secret key is required")
    @Size(min = 16, max = 64, message = "Secret key must be between 16 and 64 characters")
    @JsonProperty("secret_key")
    private String secretKey;

    /**
     * Whether the webhook is currently active.
     * Inactive webhooks will not be triggered by events.
     */
    @NotNull(message = "Active status is required")
    @JsonProperty("active")
    private Boolean active;

    /**
     * The name of the signature header used (e.g., "X-Webhook-Signature").
     * This header will contain the HMAC signature in webhook deliveries.
     */
    @JsonProperty("signature_header")
    @Size(max = 100, message = "Signature header name cannot exceed 100 characters")
    private String signatureHeader = "X-Webhook-Signature";

    /**
     * Default constructor.
     */
    public WebhookRequestDTO() {
    }

    /**
     * Constructor with all fields.
     *
     * @param endpointUrl     The endpoint URL
     * @param eventType       The event type
     * @param secretKey       The secret key
     * @param active          Whether the webhook is active
     * @param signatureHeader The signature header name
     */
    public WebhookRequestDTO(String endpointUrl, String eventType, String secretKey, Boolean active, String signatureHeader) {
        this.endpointUrl = endpointUrl;
        this.eventType = eventType;
        this.secretKey = secretKey;
        this.active = active;
        this.signatureHeader = signatureHeader;
    }

    /**
     * @return The endpoint URL
     */
    public String getEndpointUrl() {
        return endpointUrl;
    }

    /**
     * @param endpointUrl The endpoint URL
     */
    public void setEndpointUrl(String endpointUrl) {
        this.endpointUrl = endpointUrl;
    }

    /**
     * @return The event type
     */
    public String getEventType() {
        return eventType;
    }

    /**
     * @param eventType The event type
     */
    public void setEventType(String eventType) {
        this.eventType = eventType;
    }

    /**
     * @return The secret key
     */
    public String getSecretKey() {
        return secretKey;
    }

    /**
     * @param secretKey The secret key
     */
    public void setSecretKey(String secretKey) {
        this.secretKey = secretKey;
    }

    /**
     * @return Whether the webhook is active
     */
    public Boolean getActive() {
        return active;
    }

    /**
     * @param active Whether the webhook is active
     */
    public void setActive(Boolean active) {
        this.active = active;
    }

    /**
     * @return The signature header name
     */
    public String getSignatureHeader() {
        return signatureHeader;
    }

    /**
     * @param signatureHeader The signature header name
     */
    public void setSignatureHeader(String signatureHeader) {
        this.signatureHeader = signatureHeader;
    }

    /**
     * Converts this DTO to a Webhook entity.
     * This method is used when creating a new webhook.
     *
     * @return A new Webhook entity
     * @throws IllegalArgumentException if the event type is invalid
     */
    public Webhook toEntity() {
        Webhook webhook = new Webhook();
        webhook.setEndpointUrl(this.endpointUrl);
        webhook.setSecretKey(this.secretKey);
        webhook.setActive(this.active);
        webhook.setSignatureHeader(this.signatureHeader);
        
        // Convert string event type to enum
        try {
            webhook.setEventType(EventType.valueOf(this.eventType));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid event type: " + this.eventType);
        }
        
        return webhook;
    }

    /**
     * Updates an existing Webhook entity with values from this DTO.
     * This method is used when updating an existing webhook.
     *
     * @param webhook The webhook entity to update
     * @return The updated webhook entity
     * @throws IllegalArgumentException if the event type is invalid
     */
    public Webhook updateEntity(Webhook webhook) {
        if (webhook == null) {
            throw new IllegalArgumentException("Webhook entity cannot be null");
        }
        
        webhook.setEndpointUrl(this.endpointUrl);
        webhook.setSecretKey(this.secretKey);
        webhook.setActive(this.active);
        
        if (this.signatureHeader != null) {
            webhook.setSignatureHeader(this.signatureHeader);
        }
        
        // Convert string event type to enum
        try {
            webhook.setEventType(EventType.valueOf(this.eventType));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid event type: " + this.eventType);
        }
        
        return webhook;
    }

    /**
     * Validates that the event type is a valid enum value.
     *
     * @return true if valid, false otherwise
     */
    public boolean isValidEventType() {
        try {
            EventType.valueOf(this.eventType);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    @Override
    public String toString() {
        return "WebhookRequestDTO{" +
                "endpointUrl='" + endpointUrl + '\'' +
                ", eventType='" + eventType + '\'' +
                ", secretKey='[REDACTED]'" +
                ", active=" + active +
                ", signatureHeader='" + signatureHeader + '\'' +
                '}';
    }
}