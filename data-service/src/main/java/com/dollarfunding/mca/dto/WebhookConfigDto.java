package com.dollarfunding.mca.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Data Transfer Object for webhook configuration.
 * <p>
 * This class represents the webhook configuration data that is transferred between
 * the client and the server. It includes validation annotations to ensure the data
 * is valid before processing.
 * </p>
 */
public class WebhookConfigDto {

    private Long id;

    @NotBlank(message = "Webhook URL is required")
    @Pattern(regexp = "^https://.*", message = "Webhook URL must use HTTPS")
    @Size(max = 255, message = "Webhook URL cannot exceed 255 characters")
    private String url;

    @NotEmpty(message = "At least one event must be specified")
    private List<String> events;

    private String description;

    private boolean active = true;

    private String secretKey;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    /**
     * Default constructor.
     */
    public WebhookConfigDto() {
    }

    /**
     * Constructor with all fields.
     *
     * @param id          The webhook configuration ID
     * @param url         The webhook URL
     * @param events      The list of events to trigger the webhook
     * @param description The webhook description
     * @param active      Whether the webhook is active
     * @param secretKey   The secret key for HMAC signature verification
     * @param createdAt   The creation timestamp
     * @param updatedAt   The last update timestamp
     */
    public WebhookConfigDto(Long id, String url, List<String> events, String description,
                           boolean active, String secretKey, LocalDateTime createdAt,
                           LocalDateTime updatedAt) {
        this.id = id;
        this.url = url;
        this.events = events;
        this.description = description;
        this.active = active;
        this.secretKey = secretKey;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    /**
     * Gets the webhook configuration ID.
     *
     * @return The webhook configuration ID
     */
    public Long getId() {
        return id;
    }

    /**
     * Sets the webhook configuration ID.
     *
     * @param id The webhook configuration ID
     */
    public void setId(Long id) {
        this.id = id;
    }

    /**
     * Gets the webhook URL.
     *
     * @return The webhook URL
     */
    public String getUrl() {
        return url;
    }

    /**
     * Sets the webhook URL.
     *
     * @param url The webhook URL
     */
    public void setUrl(String url) {
        this.url = url;
    }

    /**
     * Gets the list of events to trigger the webhook.
     *
     * @return The list of events
     */
    public List<String> getEvents() {
        return events;
    }

    /**
     * Sets the list of events to trigger the webhook.
     *
     * @param events The list of events
     */
    public void setEvents(List<String> events) {
        this.events = events;
    }

    /**
     * Gets the webhook description.
     *
     * @return The webhook description
     */
    public String getDescription() {
        return description;
    }

    /**
     * Sets the webhook description.
     *
     * @param description The webhook description
     */
    public void setDescription(String description) {
        this.description = description;
    }

    /**
     * Checks if the webhook is active.
     *
     * @return true if the webhook is active, false otherwise
     */
    public boolean isActive() {
        return active;
    }

    /**
     * Sets whether the webhook is active.
     *
     * @param active true if the webhook is active, false otherwise
     */
    public void setActive(boolean active) {
        this.active = active;
    }

    /**
     * Gets the secret key for HMAC signature verification.
     *
     * @return The secret key
     */
    public String getSecretKey() {
        return secretKey;
    }

    /**
     * Sets the secret key for HMAC signature verification.
     *
     * @param secretKey The secret key
     */
    public void setSecretKey(String secretKey) {
        this.secretKey = secretKey;
    }

    /**
     * Gets the creation timestamp.
     *
     * @return The creation timestamp
     */
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    /**
     * Sets the creation timestamp.
     *
     * @param createdAt The creation timestamp
     */
    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    /**
     * Gets the last update timestamp.
     *
     * @return The last update timestamp
     */
    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    /**
     * Sets the last update timestamp.
     *
     * @param updatedAt The last update timestamp
     */
    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public String toString() {
        return "WebhookConfigDto{" +
                "id=" + id +
                ", url='" + url + '\'' +
                ", events=" + events +
                ", description='" + description + '\'' +
                ", active=" + active +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}