package com.dollarfunding.mca.dto;

import java.time.LocalDateTime;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Data Transfer Object (DTO) for returning webhook configuration data to clients.
 * <p>
 * This class provides a complete view of webhook configuration while masking sensitive
 * information like secret keys. It includes all webhook fields with appropriate serialization
 * for API responses and delivery status information.
 * </p>
 * <p>
 * Used by the REST API for webhook configuration at /api/v1/webhooks, which is restricted
 * to the System Admin role.
 * </p>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WebhookResponseDTO {

    @JsonProperty("id")
    private Long id;

    @JsonProperty("endpoint_url")
    private String endpointUrl;

    @JsonProperty("event_type")
    private EventType eventType;

    @JsonProperty("active")
    private Boolean active;

    @JsonProperty("max_retry_attempts")
    private Integer maxRetryAttempts;

    @JsonProperty("last_delivery_status")
    private String lastDeliveryStatus;

    @JsonProperty("last_delivery_attempt")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS")
    private LocalDateTime lastDeliveryAttempt;

    @JsonProperty("failed_attempts")
    private Integer failedAttempts;

    @JsonProperty("last_delivery_success")
    private Boolean lastDeliverySuccess;

    @JsonProperty("last_delivery_status_code")
    private Integer lastDeliveryStatusCode;

    @JsonProperty("last_delivery_error")
    private String lastDeliveryError;

    @JsonProperty("successful_deliveries_count")
    private Long successfulDeliveriesCount;

    @JsonProperty("failed_deliveries_count")
    private Long failedDeliveriesCount;

    @JsonProperty("signature_header")
    private String signatureHeader;

    @JsonProperty("created_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS")
    private LocalDateTime createdAt;

    @JsonProperty("updated_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS")
    private LocalDateTime updatedAt;

    /**
     * Masked secret key for display purposes. Only shows the first and last 4 characters
     * with asterisks in between for security.
     */
    @JsonProperty("masked_secret_key")
    private String maskedSecretKey;

    /**
     * Default constructor for Jackson deserialization.
     */
    public WebhookResponseDTO() {
    }

    /**
     * Creates a WebhookResponseDTO from a Webhook entity.
     *
     * @param webhook The Webhook entity to convert
     * @return A new WebhookResponseDTO with data from the Webhook entity
     */
    public static WebhookResponseDTO fromEntity(Webhook webhook) {
        if (webhook == null) {
            return null;
        }

        WebhookResponseDTO dto = new WebhookResponseDTO();
        dto.setId(webhook.getId());
        dto.setEndpointUrl(webhook.getEndpointUrl());
        dto.setEventType(webhook.getEventType());
        dto.setActive(webhook.getActive());
        dto.setMaxRetryAttempts(webhook.getMaxRetryAttempts());
        dto.setLastDeliveryStatus(webhook.getLastDeliveryStatus());
        dto.setLastDeliveryAttempt(webhook.getLastDeliveryAttempt());
        dto.setFailedAttempts(webhook.getFailedAttempts());
        dto.setLastDeliverySuccess(webhook.getLastDeliverySuccess());
        dto.setLastDeliveryStatusCode(webhook.getLastDeliveryStatusCode());
        dto.setLastDeliveryError(webhook.getLastDeliveryError());
        dto.setSuccessfulDeliveriesCount(webhook.getSuccessfulDeliveriesCount());
        dto.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount());
        dto.setSignatureHeader(webhook.getSignatureHeader());
        dto.setCreatedAt(webhook.getCreatedAt());
        dto.setUpdatedAt(webhook.getUpdatedAt());
        
        // Mask the secret key for security
        dto.setMaskedSecretKey(maskSecretKey(webhook.getSecretKey()));
        
        return dto;
    }

    /**
     * Masks a secret key for display purposes, showing only the first and last 4 characters
     * with asterisks in between.
     *
     * @param secretKey The secret key to mask
     * @return The masked secret key, or null if the input is null
     */
    private static String maskSecretKey(String secretKey) {
        if (secretKey == null) {
            return null;
        }
        
        int length = secretKey.length();
        if (length <= 8) {
            // If the key is too short, mask all but the first and last character
            return length > 2 ? 
                   secretKey.charAt(0) + "*****" + secretKey.charAt(length - 1) : 
                   "*****";
        }
        
        // Show first 4 and last 4 characters, mask the rest
        String firstFour = secretKey.substring(0, 4);
        String lastFour = secretKey.substring(length - 4);
        return firstFour + "*".repeat(Math.min(length - 8, 10)) + lastFour;
    }

    /**
     * Gets the delivery status summary as a human-readable string.
     *
     * @return A string summarizing the webhook delivery status
     */
    @JsonProperty("delivery_status_summary")
    public String getDeliveryStatusSummary() {
        if (lastDeliveryAttempt == null) {
            return "Never triggered";
        }
        
        if (Boolean.TRUE.equals(lastDeliverySuccess)) {
            return "Last delivery successful at " + lastDeliveryAttempt;
        }
        
        if (failedAttempts != null && failedAttempts > 0) {
            return "Failed delivery (" + failedAttempts + " attempts) - Last attempt at " + lastDeliveryAttempt;
        }
        
        return lastDeliveryStatus != null ? lastDeliveryStatus : "Unknown status";
    }

    /**
     * Gets the webhook health status based on delivery history.
     *
     * @return A string representing the webhook health: "healthy", "warning", or "error"
     */
    @JsonProperty("health_status")
    public String getHealthStatus() {
        if (lastDeliveryAttempt == null) {
            return "unknown";
        }
        
        if (Boolean.TRUE.equals(lastDeliverySuccess)) {
            return "healthy";
        }
        
        if (failedAttempts != null && failedAttempts > 0 && maxRetryAttempts != null) {
            return failedAttempts >= maxRetryAttempts ? "error" : "warning";
        }
        
        return "unknown";
    }

    // Getters and Setters

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getEndpointUrl() {
        return endpointUrl;
    }

    public void setEndpointUrl(String endpointUrl) {
        this.endpointUrl = endpointUrl;
    }

    public EventType getEventType() {
        return eventType;
    }

    public void setEventType(EventType eventType) {
        this.eventType = eventType;
    }

    public Boolean getActive() {
        return active;
    }

    public void setActive(Boolean active) {
        this.active = active;
    }

    public Integer getMaxRetryAttempts() {
        return maxRetryAttempts;
    }

    public void setMaxRetryAttempts(Integer maxRetryAttempts) {
        this.maxRetryAttempts = maxRetryAttempts;
    }

    public String getLastDeliveryStatus() {
        return lastDeliveryStatus;
    }

    public void setLastDeliveryStatus(String lastDeliveryStatus) {
        this.lastDeliveryStatus = lastDeliveryStatus;
    }

    public LocalDateTime getLastDeliveryAttempt() {
        return lastDeliveryAttempt;
    }

    public void setLastDeliveryAttempt(LocalDateTime lastDeliveryAttempt) {
        this.lastDeliveryAttempt = lastDeliveryAttempt;
    }

    public Integer getFailedAttempts() {
        return failedAttempts;
    }

    public void setFailedAttempts(Integer failedAttempts) {
        this.failedAttempts = failedAttempts;
    }

    public Boolean getLastDeliverySuccess() {
        return lastDeliverySuccess;
    }

    public void setLastDeliverySuccess(Boolean lastDeliverySuccess) {
        this.lastDeliverySuccess = lastDeliverySuccess;
    }

    public Integer getLastDeliveryStatusCode() {
        return lastDeliveryStatusCode;
    }

    public void setLastDeliveryStatusCode(Integer lastDeliveryStatusCode) {
        this.lastDeliveryStatusCode = lastDeliveryStatusCode;
    }

    public String getLastDeliveryError() {
        return lastDeliveryError;
    }

    public void setLastDeliveryError(String lastDeliveryError) {
        this.lastDeliveryError = lastDeliveryError;
    }

    public Long getSuccessfulDeliveriesCount() {
        return successfulDeliveriesCount;
    }

    public void setSuccessfulDeliveriesCount(Long successfulDeliveriesCount) {
        this.successfulDeliveriesCount = successfulDeliveriesCount;
    }

    public Long getFailedDeliveriesCount() {
        return failedDeliveriesCount;
    }

    public void setFailedDeliveriesCount(Long failedDeliveriesCount) {
        this.failedDeliveriesCount = failedDeliveriesCount;
    }

    public String getSignatureHeader() {
        return signatureHeader;
    }

    public void setSignatureHeader(String signatureHeader) {
        this.signatureHeader = signatureHeader;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public String getMaskedSecretKey() {
        return maskedSecretKey;
    }

    public void setMaskedSecretKey(String maskedSecretKey) {
        this.maskedSecretKey = maskedSecretKey;
    }

    @Override
    public String toString() {
        return "WebhookResponseDTO{" +
                "id=" + id +
                ", endpointUrl='" + endpointUrl + '\'' +
                ", eventType=" + eventType +
                ", active=" + active +
                ", maxRetryAttempts=" + maxRetryAttempts +
                ", lastDeliveryStatus='" + lastDeliveryStatus + '\'' +
                ", lastDeliveryAttempt=" + lastDeliveryAttempt +
                ", failedAttempts=" + failedAttempts +
                ", lastDeliverySuccess=" + lastDeliverySuccess +
                ", lastDeliveryStatusCode=" + lastDeliveryStatusCode +
                ", successfulDeliveriesCount=" + successfulDeliveriesCount +
                ", failedDeliveriesCount=" + failedDeliveriesCount +
                ", signatureHeader='" + signatureHeader + '\'' +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                ", maskedSecretKey='" + maskedSecretKey + '\'' +
                '}';
    }
}