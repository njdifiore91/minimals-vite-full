package com.dollarfunding.mca.entity;

import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * Entity representing a webhook configuration for notification delivery.
 * <p>
 * This entity stores information about external webhook endpoints for notification delivery,
 * including the endpoint URL, secret key for HMAC signing, active status, and event type.
 * It is used by the notification service to deliver webhook notifications to third-party
 * systems with retry capability.
 * </p>
 */
@Entity
@Table(name = "webhooks")
public class Webhook {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * The URL of the webhook endpoint where notifications will be sent.
     * Must be a valid HTTPS URL.
     */
    @NotBlank(message = "Endpoint URL is required")
    @Pattern(regexp = "^https://.*", message = "Endpoint URL must use HTTPS protocol")
    @Size(max = 255, message = "Endpoint URL cannot exceed 255 characters")
    @Column(name = "endpoint_url", nullable = false)
    private String endpointUrl;

    /**
     * Secret key used for HMAC signing of webhook payloads.
     * This provides a way for the webhook receiver to verify the authenticity of the webhook.
     */
    @NotBlank(message = "Secret key is required")
    @Size(min = 32, max = 128, message = "Secret key must be between 32 and 128 characters")
    @Column(name = "secret_key", nullable = false)
    private String secretKey;

    /**
     * Flag indicating whether this webhook is active and should receive notifications.
     */
    @NotNull(message = "Active status is required")
    @Column(name = "active", nullable = false)
    private Boolean active;

    /**
     * The type of event that triggers this webhook.
     */
    @NotNull(message = "Event type is required")
    @Enumerated(EnumType.STRING)
    @Column(name = "event_type", nullable = false)
    private EventType eventType;

    /**
     * The maximum number of retry attempts for failed webhook deliveries.
     */
    @Min(value = 0, message = "Max retry attempts must be at least 0")
    @Max(value = 10, message = "Max retry attempts cannot exceed 10")
    @Column(name = "max_retry_attempts", nullable = false)
    private Integer maxRetryAttempts = 3;

    /**
     * The current status of the webhook delivery.
     * This is used to track whether the last delivery attempt was successful.
     */
    @Column(name = "last_delivery_status")
    private String lastDeliveryStatus;

    /**
     * The timestamp of the last delivery attempt.
     */
    @Column(name = "last_delivery_attempt")
    private LocalDateTime lastDeliveryAttempt;

    /**
     * The number of consecutive failed delivery attempts.
     */
    @Min(value = 0, message = "Failed attempts must be at least 0")
    @Column(name = "failed_attempts", nullable = false)
    private Integer failedAttempts = 0;

    /**
     * Whether the last delivery was successful.
     */
    @Column(name = "last_delivery_success")
    private Boolean lastDeliverySuccess;

    /**
     * The HTTP status code from the last delivery attempt.
     */
    @Column(name = "last_delivery_status_code")
    private Integer lastDeliveryStatusCode;

    /**
     * The error message from the last delivery attempt, if any.
     */
    @Column(name = "last_delivery_error")
    private String lastDeliveryError;

    /**
     * Total number of successful deliveries.
     */
    @Column(name = "successful_deliveries_count")
    private Long successfulDeliveriesCount = 0L;

    /**
     * Total number of failed deliveries.
     */
    @Column(name = "failed_deliveries_count")
    private Long failedDeliveriesCount = 0L;

    /**
     * The name of the signature header used (e.g., "X-Webhook-Signature").
     */
    @Column(name = "signature_header")
    private String signatureHeader = "X-Webhook-Signature";

    /**
     * The timestamp when this webhook was created.
     */
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /**
     * The timestamp when this webhook was last updated.
     */
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    /**
     * Default constructor required by JPA.
     */
    public Webhook() {
    }

    /**
     * Constructor with required fields.
     *
     * @param endpointUrl The URL of the webhook endpoint
     * @param secretKey The secret key for HMAC signing
     * @param active Whether the webhook is active
     * @param eventType The type of event that triggers this webhook
     */
    public Webhook(String endpointUrl, String secretKey, Boolean active, EventType eventType) {
        this.endpointUrl = endpointUrl;
        this.secretKey = secretKey;
        this.active = active;
        this.eventType = eventType;
    }

    /**
     * Sets the creation and update timestamps before persisting.
     */
    @PrePersist
    protected void onCreate() {
        LocalDateTime now = LocalDateTime.now();
        this.createdAt = now;
        this.updatedAt = now;
        if (this.successfulDeliveriesCount == null) {
            this.successfulDeliveriesCount = 0L;
        }
        if (this.failedDeliveriesCount == null) {
            this.failedDeliveriesCount = 0L;
        }
        if (this.signatureHeader == null) {
            this.signatureHeader = "X-Webhook-Signature";
        }
    }

    /**
     * Updates the update timestamp before updating.
     */
    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Records a successful delivery attempt.
     */
    public void recordSuccessfulDelivery() {
        this.lastDeliveryStatus = "SUCCESS";
        this.lastDeliveryAttempt = LocalDateTime.now();
        this.failedAttempts = 0;
    }

    /**
     * Records a failed delivery attempt.
     *
     * @param errorMessage The error message from the failed delivery
     * @return true if max retry attempts has not been reached, false otherwise
     */
    public boolean recordFailedDelivery(String errorMessage) {
        this.lastDeliveryStatus = "FAILED: " + errorMessage;
        this.lastDeliveryAttempt = LocalDateTime.now();
        this.failedAttempts++;
        return this.failedAttempts <= this.maxRetryAttempts;
    }

    /**
     * Checks if this webhook should be retried after a failed delivery.
     *
     * @return true if the webhook should be retried, false otherwise
     */
    public boolean shouldRetry() {
        return this.active && this.failedAttempts > 0 && this.failedAttempts <= this.maxRetryAttempts;
    }

    /**
     * Resets the failed attempts counter.
     */
    public void resetFailedAttempts() {
        this.failedAttempts = 0;
    }

    /**
     * Checks if the webhook is active.
     *
     * @return true if the webhook is active, false otherwise
     */
    public boolean isActive() {
        return Boolean.TRUE.equals(this.active);
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

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    @Override
    public String toString() {
        return "Webhook{" +
                "id=" + id +
                ", endpointUrl='" + endpointUrl + '\'' +
                ", active=" + active +
                ", eventType=" + eventType +
                ", maxRetryAttempts=" + maxRetryAttempts +
                ", failedAttempts=" + failedAttempts +
                ", lastDeliveryStatus='" + lastDeliveryStatus + '\'' +
                ", lastDeliveryAttempt=" + lastDeliveryAttempt +
                ", lastDeliverySuccess=" + lastDeliverySuccess +
                ", lastDeliveryStatusCode=" + lastDeliveryStatusCode +
                ", successfulDeliveriesCount=" + successfulDeliveriesCount +
                ", failedDeliveriesCount=" + failedDeliveriesCount +
                ", signatureHeader='" + signatureHeader + '\'' +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}