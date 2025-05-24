package com.dollarfunding.mca.entity;

import java.time.LocalDateTime;
import java.util.Objects;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.EnumType;
import javax.persistence.Enumerated;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.PrePersist;
import javax.persistence.PreUpdate;
import javax.persistence.Table;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

/**
 * Entity class representing webhook configuration in the database.
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
     * Must be a valid URL starting with http:// or https://
     */
    @NotBlank(message = "Endpoint URL is required")
    @Pattern(regexp = "^(https?://)[\\w.-]+(?:\\.[\\w.-]+)+[\\w\\-._~:/?#[\\]@!$&'()*+,;=.]+$", 
             message = "Endpoint URL must be a valid URL")
    @Column(name = "endpoint_url", nullable = false)
    private String endpointUrl;

    /**
     * Secret key used for signing webhook payloads with HMAC-SHA256.
     * This provides a way for webhook recipients to verify the authenticity of the webhook.
     */
    @NotBlank(message = "Secret key is required")
    @Size(min = 16, message = "Secret key must be at least 16 characters long")
    @Column(name = "secret_key", nullable = false)
    private String secretKey;

    /**
     * Indicates whether this webhook is currently active and should receive notifications.
     */
    @NotNull(message = "Active status is required")
    @Column(name = "active", nullable = false)
    private Boolean active;

    /**
     * The type of event that triggers this webhook notification.
     */
    @NotNull(message = "Event type is required")
    @Enumerated(EnumType.STRING)
    @Column(name = "event_type", nullable = false)
    private EventType eventType;

    /**
     * Maximum number of retry attempts for failed webhook deliveries.
     */
    @Column(name = "max_retry_attempts", nullable = false)
    private Integer maxRetryAttempts = 3;

    /**
     * Current number of consecutive failed delivery attempts.
     */
    @Column(name = "consecutive_failures", nullable = false)
    private Integer consecutiveFailures = 0;

    /**
     * Timestamp of the last successful webhook delivery.
     */
    @Column(name = "last_success_at")
    private LocalDateTime lastSuccessAt;

    /**
     * Timestamp of the last failed webhook delivery.
     */
    @Column(name = "last_failure_at")
    private LocalDateTime lastFailureAt;

    /**
     * Description of the webhook for administrative purposes.
     */
    @Column(name = "description")
    @Size(max = 500, message = "Description cannot exceed 500 characters")
    private String description;

    /**
     * Timestamp when this webhook configuration was created.
     */
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /**
     * Timestamp when this webhook configuration was last updated.
     */
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    /**
     * Automatically sets the creation and update timestamps before persisting.
     */
    @PrePersist
    protected void onCreate() {
        LocalDateTime now = LocalDateTime.now();
        this.createdAt = now;
        this.updatedAt = now;
    }

    /**
     * Automatically updates the update timestamp before updating.
     */
    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Default constructor required by JPA.
     */
    public Webhook() {
    }

    /**
     * Constructor with required fields.
     *
     * @param endpointUrl The URL of the webhook endpoint
     * @param secretKey   The secret key for HMAC signing
     * @param active      Whether the webhook is active
     * @param eventType   The type of event that triggers this webhook
     */
    public Webhook(String endpointUrl, String secretKey, Boolean active, EventType eventType) {
        this.endpointUrl = endpointUrl;
        this.secretKey = secretKey;
        this.active = active;
        this.eventType = eventType;
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

    public Integer getConsecutiveFailures() {
        return consecutiveFailures;
    }

    public void setConsecutiveFailures(Integer consecutiveFailures) {
        this.consecutiveFailures = consecutiveFailures;
    }

    public LocalDateTime getLastSuccessAt() {
        return lastSuccessAt;
    }

    public void setLastSuccessAt(LocalDateTime lastSuccessAt) {
        this.lastSuccessAt = lastSuccessAt;
    }

    public LocalDateTime getLastFailureAt() {
        return lastFailureAt;
    }

    public void setLastFailureAt(LocalDateTime lastFailureAt) {
        this.lastFailureAt = lastFailureAt;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    /**
     * Records a successful webhook delivery.
     * Updates the lastSuccessAt timestamp and resets the consecutive failures counter.
     */
    public void recordSuccess() {
        this.lastSuccessAt = LocalDateTime.now();
        this.consecutiveFailures = 0;
    }

    /**
     * Records a failed webhook delivery.
     * Updates the lastFailureAt timestamp and increments the consecutive failures counter.
     * If the consecutive failures exceed the maximum retry attempts, the webhook is deactivated.
     *
     * @return true if the webhook should be deactivated due to too many failures, false otherwise
     */
    public boolean recordFailure() {
        this.lastFailureAt = LocalDateTime.now();
        this.consecutiveFailures++;
        
        if (this.consecutiveFailures >= this.maxRetryAttempts) {
            this.active = false;
            return true;
        }
        return false;
    }

    /**
     * Checks if this webhook should be triggered for the given event type.
     *
     * @param eventType The event type to check
     * @return true if this webhook should be triggered, false otherwise
     */
    public boolean shouldTriggerFor(EventType eventType) {
        return this.active && this.eventType == eventType;
    }

    /**
     * Generates a payload for this webhook based on the event type.
     *
     * @return A sample payload for this webhook's event type
     */
    public Object generateSamplePayload() {
        return this.eventType.generateSamplePayload();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Webhook webhook = (Webhook) o;
        return Objects.equals(id, webhook.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "Webhook{" +
                "id=" + id +
                ", endpointUrl='" + endpointUrl + '\'' +
                ", active=" + active +
                ", eventType=" + eventType +
                ", consecutiveFailures=" + consecutiveFailures +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}