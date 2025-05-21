package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;

/**
 * DTO class for returning webhook configuration data to clients.
 * This class provides a complete view of webhook configuration while masking
 * sensitive information like secret keys.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WebhookResponseDTO {

    /**
     * Unique identifier for the webhook.
     */
    @JsonProperty("id")
    private Long id;

    /**
     * The URL where webhook notifications will be sent.
     */
    @JsonProperty("endpoint_url")
    private String endpointUrl;

    /**
     * The type of event that triggers this webhook.
     */
    @JsonProperty("event_type")
    private String eventType;

    /**
     * Whether the webhook is currently active.
     */
    @JsonProperty("active")
    private boolean active;

    /**
     * Masked version of the secret key used for HMAC signing.
     */
    @JsonProperty("secret_key_masked")
    private String secretKeyMasked;

    /**
     * Timestamp when the webhook was created.
     */
    @JsonProperty("created_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime createdAt;

    /**
     * Timestamp when the webhook was last updated.
     */
    @JsonProperty("updated_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime updatedAt;

    /**
     * Timestamp when the webhook was last delivered.
     */
    @JsonProperty("last_delivery_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime lastDeliveryAt;

    /**
     * Whether the last delivery was successful.
     */
    @JsonProperty("last_delivery_success")
    private Boolean lastDeliverySuccess;

    /**
     * HTTP status code from the last delivery attempt.
     */
    @JsonProperty("last_delivery_status_code")
    private Integer lastDeliveryStatusCode;

    /**
     * Error message from the last delivery attempt, if any.
     */
    @JsonProperty("last_delivery_error")
    private String lastDeliveryError;

    /**
     * Total number of successful deliveries.
     */
    @JsonProperty("successful_deliveries_count")
    private Long successfulDeliveriesCount;

    /**
     * Total number of failed deliveries.
     */
    @JsonProperty("failed_deliveries_count")
    private Long failedDeliveriesCount;

    /**
     * The name of the signature header used (e.g., "X-Webhook-Signature").
     */
    @JsonProperty("signature_header")
    private String signatureHeader;

    /**
     * Default constructor.
     */
    public WebhookResponseDTO() {
    }

    /**
     * Constructor with all fields.
     *
     * @param id                     The webhook ID
     * @param endpointUrl            The endpoint URL
     * @param eventType              The event type
     * @param active                 Whether the webhook is active
     * @param secretKeyMasked        The masked secret key
     * @param createdAt              The creation timestamp
     * @param updatedAt              The last update timestamp
     * @param lastDeliveryAt         The last delivery timestamp
     * @param lastDeliverySuccess    Whether the last delivery was successful
     * @param lastDeliveryStatusCode The HTTP status code from the last delivery
     * @param lastDeliveryError      The error message from the last delivery
     * @param successfulDeliveriesCount Total successful deliveries
     * @param failedDeliveriesCount  Total failed deliveries
     * @param signatureHeader        The signature header name
     */
    public WebhookResponseDTO(Long id, String endpointUrl, String eventType, boolean active,
                             String secretKeyMasked, LocalDateTime createdAt, LocalDateTime updatedAt,
                             LocalDateTime lastDeliveryAt, Boolean lastDeliverySuccess,
                             Integer lastDeliveryStatusCode, String lastDeliveryError,
                             Long successfulDeliveriesCount, Long failedDeliveriesCount,
                             String signatureHeader) {
        this.id = id;
        this.endpointUrl = endpointUrl;
        this.eventType = eventType;
        this.active = active;
        this.secretKeyMasked = secretKeyMasked;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.lastDeliveryAt = lastDeliveryAt;
        this.lastDeliverySuccess = lastDeliverySuccess;
        this.lastDeliveryStatusCode = lastDeliveryStatusCode;
        this.lastDeliveryError = lastDeliveryError;
        this.successfulDeliveriesCount = successfulDeliveriesCount;
        this.failedDeliveriesCount = failedDeliveriesCount;
        this.signatureHeader = signatureHeader;
    }

    /**
     * Converts a Webhook entity to a WebhookResponseDTO.
     *
     * @param webhook The webhook entity
     * @return A new WebhookResponseDTO instance
     */
    public static WebhookResponseDTO fromEntity(Webhook webhook) {
        if (webhook == null) {
            return null;
        }

        // Mask the secret key (show only first 4 characters followed by asterisks)
        String secretKey = webhook.getSecretKey();
        String maskedKey = null;
        if (secretKey != null && !secretKey.isEmpty()) {
            int visibleChars = Math.min(4, secretKey.length());
            maskedKey = secretKey.substring(0, visibleChars) + "*".repeat(Math.max(0, 8 - visibleChars));
        }

        return new Builder()
                .id(webhook.getId())
                .endpointUrl(webhook.getEndpointUrl())
                .eventType(webhook.getEventType() != null ? webhook.getEventType().name() : null)
                .active(webhook.isActive())
                .secretKeyMasked(maskedKey)
                .createdAt(webhook.getCreatedAt())
                .updatedAt(webhook.getUpdatedAt())
                .lastDeliveryAt(webhook.getLastDeliveryAt())
                .lastDeliverySuccess(webhook.getLastDeliverySuccess())
                .lastDeliveryStatusCode(webhook.getLastDeliveryStatusCode())
                .lastDeliveryError(webhook.getLastDeliveryError())
                .successfulDeliveriesCount(webhook.getSuccessfulDeliveriesCount())
                .failedDeliveriesCount(webhook.getFailedDeliveriesCount())
                .signatureHeader(webhook.getSignatureHeader())
                .build();
    }

    /**
     * @return The webhook ID
     */
    public Long getId() {
        return id;
    }

    /**
     * @param id The webhook ID
     */
    public void setId(Long id) {
        this.id = id;
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
     * @return Whether the webhook is active
     */
    public boolean isActive() {
        return active;
    }

    /**
     * @param active Whether the webhook is active
     */
    public void setActive(boolean active) {
        this.active = active;
    }

    /**
     * @return The masked secret key
     */
    public String getSecretKeyMasked() {
        return secretKeyMasked;
    }

    /**
     * @param secretKeyMasked The masked secret key
     */
    public void setSecretKeyMasked(String secretKeyMasked) {
        this.secretKeyMasked = secretKeyMasked;
    }

    /**
     * @return The creation timestamp
     */
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    /**
     * @param createdAt The creation timestamp
     */
    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    /**
     * @return The last update timestamp
     */
    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    /**
     * @param updatedAt The last update timestamp
     */
    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    /**
     * @return The last delivery timestamp
     */
    public LocalDateTime getLastDeliveryAt() {
        return lastDeliveryAt;
    }

    /**
     * @param lastDeliveryAt The last delivery timestamp
     */
    public void setLastDeliveryAt(LocalDateTime lastDeliveryAt) {
        this.lastDeliveryAt = lastDeliveryAt;
    }

    /**
     * @return Whether the last delivery was successful
     */
    public Boolean getLastDeliverySuccess() {
        return lastDeliverySuccess;
    }

    /**
     * @param lastDeliverySuccess Whether the last delivery was successful
     */
    public void setLastDeliverySuccess(Boolean lastDeliverySuccess) {
        this.lastDeliverySuccess = lastDeliverySuccess;
    }

    /**
     * @return The HTTP status code from the last delivery
     */
    public Integer getLastDeliveryStatusCode() {
        return lastDeliveryStatusCode;
    }

    /**
     * @param lastDeliveryStatusCode The HTTP status code from the last delivery
     */
    public void setLastDeliveryStatusCode(Integer lastDeliveryStatusCode) {
        this.lastDeliveryStatusCode = lastDeliveryStatusCode;
    }

    /**
     * @return The error message from the last delivery
     */
    public String getLastDeliveryError() {
        return lastDeliveryError;
    }

    /**
     * @param lastDeliveryError The error message from the last delivery
     */
    public void setLastDeliveryError(String lastDeliveryError) {
        this.lastDeliveryError = lastDeliveryError;
    }

    /**
     * @return Total successful deliveries
     */
    public Long getSuccessfulDeliveriesCount() {
        return successfulDeliveriesCount;
    }

    /**
     * @param successfulDeliveriesCount Total successful deliveries
     */
    public void setSuccessfulDeliveriesCount(Long successfulDeliveriesCount) {
        this.successfulDeliveriesCount = successfulDeliveriesCount;
    }

    /**
     * @return Total failed deliveries
     */
    public Long getFailedDeliveriesCount() {
        return failedDeliveriesCount;
    }

    /**
     * @param failedDeliveriesCount Total failed deliveries
     */
    public void setFailedDeliveriesCount(Long failedDeliveriesCount) {
        this.failedDeliveriesCount = failedDeliveriesCount;
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
     * Builder class for creating WebhookResponseDTO instances.
     */
    public static class Builder {
        private Long id;
        private String endpointUrl;
        private String eventType;
        private boolean active;
        private String secretKeyMasked;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private LocalDateTime lastDeliveryAt;
        private Boolean lastDeliverySuccess;
        private Integer lastDeliveryStatusCode;
        private String lastDeliveryError;
        private Long successfulDeliveriesCount;
        private Long failedDeliveriesCount;
        private String signatureHeader;

        /**
         * Default constructor.
         */
        public Builder() {
        }

        /**
         * @param id The webhook ID
         * @return The builder instance
         */
        public Builder id(Long id) {
            this.id = id;
            return this;
        }

        /**
         * @param endpointUrl The endpoint URL
         * @return The builder instance
         */
        public Builder endpointUrl(String endpointUrl) {
            this.endpointUrl = endpointUrl;
            return this;
        }

        /**
         * @param eventType The event type
         * @return The builder instance
         */
        public Builder eventType(String eventType) {
            this.eventType = eventType;
            return this;
        }

        /**
         * @param active Whether the webhook is active
         * @return The builder instance
         */
        public Builder active(boolean active) {
            this.active = active;
            return this;
        }

        /**
         * @param secretKeyMasked The masked secret key
         * @return The builder instance
         */
        public Builder secretKeyMasked(String secretKeyMasked) {
            this.secretKeyMasked = secretKeyMasked;
            return this;
        }

        /**
         * @param createdAt The creation timestamp
         * @return The builder instance
         */
        public Builder createdAt(LocalDateTime createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        /**
         * @param updatedAt The last update timestamp
         * @return The builder instance
         */
        public Builder updatedAt(LocalDateTime updatedAt) {
            this.updatedAt = updatedAt;
            return this;
        }

        /**
         * @param lastDeliveryAt The last delivery timestamp
         * @return The builder instance
         */
        public Builder lastDeliveryAt(LocalDateTime lastDeliveryAt) {
            this.lastDeliveryAt = lastDeliveryAt;
            return this;
        }

        /**
         * @param lastDeliverySuccess Whether the last delivery was successful
         * @return The builder instance
         */
        public Builder lastDeliverySuccess(Boolean lastDeliverySuccess) {
            this.lastDeliverySuccess = lastDeliverySuccess;
            return this;
        }

        /**
         * @param lastDeliveryStatusCode The HTTP status code from the last delivery
         * @return The builder instance
         */
        public Builder lastDeliveryStatusCode(Integer lastDeliveryStatusCode) {
            this.lastDeliveryStatusCode = lastDeliveryStatusCode;
            return this;
        }

        /**
         * @param lastDeliveryError The error message from the last delivery
         * @return The builder instance
         */
        public Builder lastDeliveryError(String lastDeliveryError) {
            this.lastDeliveryError = lastDeliveryError;
            return this;
        }

        /**
         * @param successfulDeliveriesCount Total successful deliveries
         * @return The builder instance
         */
        public Builder successfulDeliveriesCount(Long successfulDeliveriesCount) {
            this.successfulDeliveriesCount = successfulDeliveriesCount;
            return this;
        }

        /**
         * @param failedDeliveriesCount Total failed deliveries
         * @return The builder instance
         */
        public Builder failedDeliveriesCount(Long failedDeliveriesCount) {
            this.failedDeliveriesCount = failedDeliveriesCount;
            return this;
        }

        /**
         * @param signatureHeader The signature header name
         * @return The builder instance
         */
        public Builder signatureHeader(String signatureHeader) {
            this.signatureHeader = signatureHeader;
            return this;
        }

        /**
         * Builds a new WebhookResponseDTO instance.
         *
         * @return A new WebhookResponseDTO instance
         */
        public WebhookResponseDTO build() {
            WebhookResponseDTO dto = new WebhookResponseDTO();
            dto.id = this.id;
            dto.endpointUrl = this.endpointUrl;
            dto.eventType = this.eventType;
            dto.active = this.active;
            dto.secretKeyMasked = this.secretKeyMasked;
            dto.createdAt = this.createdAt;
            dto.updatedAt = this.updatedAt;
            dto.lastDeliveryAt = this.lastDeliveryAt;
            dto.lastDeliverySuccess = this.lastDeliverySuccess;
            dto.lastDeliveryStatusCode = this.lastDeliveryStatusCode;
            dto.lastDeliveryError = this.lastDeliveryError;
            dto.successfulDeliveriesCount = this.successfulDeliveriesCount;
            dto.failedDeliveriesCount = this.failedDeliveriesCount;
            dto.signatureHeader = this.signatureHeader;
            return dto;
        }
    }

    /**
     * Creates a new builder instance.
     *
     * @return A new builder instance
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Creates a list response from a list of webhook entities.
     *
     * @param webhooks The list of webhook entities
     * @return A list of WebhookResponseDTO instances
     */
    public static java.util.List<WebhookResponseDTO> fromEntities(java.util.List<Webhook> webhooks) {
        if (webhooks == null) {
            return java.util.Collections.emptyList();
        }
        return webhooks.stream()
                .map(WebhookResponseDTO::fromEntity)
                .collect(java.util.stream.Collectors.toList());
    }
}