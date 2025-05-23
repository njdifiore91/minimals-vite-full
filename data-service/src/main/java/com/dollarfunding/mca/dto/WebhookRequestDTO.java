package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * Data Transfer Object (DTO) for creating or updating webhook configurations.
 * <p>
 * This class defines the structure for incoming webhook data with validation annotations
 * for required fields. It includes fields for webhook endpoint URL, event types, secret key,
 * and active status. It serves as the contract for webhook configuration operations in the
 * REST API.
 * </p>
 * <p>
 * Used by the REST API for webhook configuration at /api/v1/webhooks, which is restricted
 * to the System Admin role.
 * </p>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WebhookRequestDTO {

    /**
     * The URL of the webhook endpoint where notifications will be sent.
     * Must be a valid HTTPS URL.
     */
    @NotBlank(message = "Endpoint URL is required")
    @Pattern(regexp = "^https://.*", message = "Endpoint URL must use HTTPS protocol")
    @Size(max = 255, message = "Endpoint URL cannot exceed 255 characters")
    @JsonProperty("endpoint_url")
    private String endpointUrl;

    /**
     * Secret key used for HMAC signing of webhook payloads.
     * This provides a way for the webhook receiver to verify the authenticity of the webhook.
     */
    @NotBlank(message = "Secret key is required")
    @Size(min = 32, max = 128, message = "Secret key must be between 32 and 128 characters")
    @JsonProperty("secret_key")
    private String secretKey;

    /**
     * Flag indicating whether this webhook is active and should receive notifications.
     */
    @NotNull(message = "Active status is required")
    @JsonProperty("active")
    private Boolean active;

    /**
     * The type of event that triggers this webhook.
     */
    @NotNull(message = "Event type is required")
    @JsonProperty("event_type")
    private EventType eventType;

    /**
     * The maximum number of retry attempts for failed webhook deliveries.
     * Optional, defaults to 3 if not specified.
     */
    @Min(value = 0, message = "Max retry attempts must be at least 0")
    @Max(value = 10, message = "Max retry attempts cannot exceed 10")
    @JsonProperty("max_retry_attempts")
    private Integer maxRetryAttempts;

    /**
     * The name of the signature header used (e.g., "X-Webhook-Signature").
     * Optional, defaults to "X-Webhook-Signature" if not specified.
     */
    @Size(max = 100, message = "Signature header cannot exceed 100 characters")
    @JsonProperty("signature_header")
    private String signatureHeader;

    /**
     * Default constructor for Jackson deserialization.
     */
    public WebhookRequestDTO() {
    }

    /**
     * Constructor with required fields.
     *
     * @param endpointUrl The URL of the webhook endpoint
     * @param secretKey The secret key for HMAC signing
     * @param active Whether the webhook is active
     * @param eventType The type of event that triggers this webhook
     */
    public WebhookRequestDTO(String endpointUrl, String secretKey, Boolean active, EventType eventType) {
        this.endpointUrl = endpointUrl;
        this.secretKey = secretKey;
        this.active = active;
        this.eventType = eventType;
    }

    /**
     * Constructor with all fields.
     *
     * @param endpointUrl The URL of the webhook endpoint
     * @param secretKey The secret key for HMAC signing
     * @param active Whether the webhook is active
     * @param eventType The type of event that triggers this webhook
     * @param maxRetryAttempts The maximum number of retry attempts for failed webhook deliveries
     * @param signatureHeader The name of the signature header used
     */
    public WebhookRequestDTO(String endpointUrl, String secretKey, Boolean active, EventType eventType,
                             Integer maxRetryAttempts, String signatureHeader) {
        this.endpointUrl = endpointUrl;
        this.secretKey = secretKey;
        this.active = active;
        this.eventType = eventType;
        this.maxRetryAttempts = maxRetryAttempts;
        this.signatureHeader = signatureHeader;
    }

    /**
     * Converts this DTO to a new Webhook entity.
     *
     * @return A new Webhook entity with data from this DTO
     */
    public Webhook toEntity() {
        Webhook webhook = new Webhook(endpointUrl, secretKey, active, eventType);
        
        if (maxRetryAttempts != null) {
            webhook.setMaxRetryAttempts(maxRetryAttempts);
        }
        
        if (signatureHeader != null) {
            webhook.setSignatureHeader(signatureHeader);
        }
        
        return webhook;
    }

    /**
     * Updates an existing Webhook entity with data from this DTO.
     *
     * @param webhook The Webhook entity to update
     * @return The updated Webhook entity
     */
    public Webhook updateEntity(Webhook webhook) {
        if (webhook == null) {
            return toEntity();
        }
        
        webhook.setEndpointUrl(endpointUrl);
        webhook.setSecretKey(secretKey);
        webhook.setActive(active);
        webhook.setEventType(eventType);
        
        if (maxRetryAttempts != null) {
            webhook.setMaxRetryAttempts(maxRetryAttempts);
        }
        
        if (signatureHeader != null) {
            webhook.setSignatureHeader(signatureHeader);
        }
        
        return webhook;
    }

    /**
     * Creates a WebhookRequestDTO from an existing Webhook entity.
     * This is useful for pre-filling forms for webhook updates.
     *
     * @param webhook The Webhook entity to convert
     * @return A new WebhookRequestDTO with data from the Webhook entity
     */
    public static WebhookRequestDTO fromEntity(Webhook webhook) {
        if (webhook == null) {
            return null;
        }
        
        return new WebhookRequestDTO(
            webhook.getEndpointUrl(),
            webhook.getSecretKey(),
            webhook.getActive(),
            webhook.getEventType(),
            webhook.getMaxRetryAttempts(),
            webhook.getSignatureHeader()
        );
    }

    /**
     * Validates that the event type is supported.
     *
     * @return true if the event type is valid, false otherwise
     */
    public boolean isValidEventType() {
        return eventType != null;
    }

    // Getters and Setters

    public String getEndpointUrl() {
        return endpointUrl;
    }

    public void setEndpointUrl(String endpointUrl) {
        this.endpointUrl = endpointUrl;
    }

    public String getSecretKey() {
        return secretKey;
    }

    public void setSecretKey(String secretKey) {
        this.secretKey = secretKey;
    }

    public Boolean getActive() {
        return active;
    }

    public void setActive(Boolean active) {
        this.active = active;
    }

    public EventType getEventType() {
        return eventType;
    }

    public void setEventType(EventType eventType) {
        this.eventType = eventType;
    }

    public Integer getMaxRetryAttempts() {
        return maxRetryAttempts;
    }

    public void setMaxRetryAttempts(Integer maxRetryAttempts) {
        this.maxRetryAttempts = maxRetryAttempts;
    }

    public String getSignatureHeader() {
        return signatureHeader;
    }

    public void setSignatureHeader(String signatureHeader) {
        this.signatureHeader = signatureHeader;
    }

    @Override
    public String toString() {
        return "WebhookRequestDTO{" +
                "endpointUrl='" + endpointUrl + '\'' +
                ", active=" + active +
                ", eventType=" + eventType +
                ", maxRetryAttempts=" + maxRetryAttempts +
                ", signatureHeader='" + signatureHeader + '\'' +
                '}';
    }
}