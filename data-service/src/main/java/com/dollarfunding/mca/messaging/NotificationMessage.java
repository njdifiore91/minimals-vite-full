package com.dollarfunding.mca.messaging;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Model class for notification messages published to RabbitMQ.
 * This class defines the structure of messages sent to the Notification Service
 * for delivery to external systems via webhooks or other channels.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class NotificationMessage {

    /**
     * Enum defining the types of notifications that can be sent.
     */
    public enum NotificationType {
        STATUS_UPDATE,
        ERROR,
        COMPLETION
    }

    /**
     * Enum defining the priority levels for notifications.
     */
    public enum NotificationPriority {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    /**
     * Enum defining the channels through which notifications can be delivered.
     */
    public enum NotificationChannel {
        WEBHOOK,
        EMAIL,
        SMS,
        PUSH
    }

    @NotNull
    @JsonProperty("id")
    private String id;

    @NotNull
    @JsonProperty("type")
    private NotificationType type;

    @NotNull
    @JsonProperty("timestamp")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime timestamp;

    @NotNull
    @JsonProperty("priority")
    private NotificationPriority priority;

    @NotEmpty
    @JsonProperty("recipients")
    private List<Recipient> recipients;

    @NotNull
    @JsonProperty("payload")
    private Map<String, Object> payload;

    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    @JsonProperty("delivery_options")
    private DeliveryOptions deliveryOptions;

    /**
     * Default constructor for serialization frameworks.
     */
    public NotificationMessage() {
        this.timestamp = LocalDateTime.now();
        this.payload = new HashMap<>();
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor with essential fields.
     *
     * @param id         Unique identifier for the notification
     * @param type       Type of notification
     * @param priority   Priority level of the notification
     * @param recipients List of recipients for the notification
     * @param payload    Data payload of the notification
     */
    public NotificationMessage(String id, NotificationType type, NotificationPriority priority,
                              List<Recipient> recipients, Map<String, Object> payload) {
        this.id = id;
        this.type = type;
        this.timestamp = LocalDateTime.now();
        this.priority = priority;
        this.recipients = recipients;
        this.payload = payload;
        this.metadata = new HashMap<>();
    }

    /**
     * Inner class representing a notification recipient.
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class Recipient {
        @NotNull
        @JsonProperty("channel")
        private NotificationChannel channel;

        @NotBlank
        @JsonProperty("destination")
        private String destination;

        @JsonProperty("name")
        private String name;

        @JsonProperty("properties")
        private Map<String, Object> properties;

        /**
         * Default constructor for serialization frameworks.
         */
        public Recipient() {
            this.properties = new HashMap<>();
        }

        /**
         * Constructor with essential fields.
         *
         * @param channel     Channel for notification delivery
         * @param destination Destination address (webhook URL, email, phone number, etc.)
         */
        public Recipient(NotificationChannel channel, String destination) {
            this.channel = channel;
            this.destination = destination;
            this.properties = new HashMap<>();
        }

        /**
         * Constructor with all fields.
         *
         * @param channel     Channel for notification delivery
         * @param destination Destination address (webhook URL, email, phone number, etc.)
         * @param name        Name of the recipient
         * @param properties  Additional properties for the recipient
         */
        public Recipient(NotificationChannel channel, String destination, String name, Map<String, Object> properties) {
            this.channel = channel;
            this.destination = destination;
            this.name = name;
            this.properties = properties;
        }

        public NotificationChannel getChannel() {
            return channel;
        }

        public void setChannel(NotificationChannel channel) {
            this.channel = channel;
        }

        public String getDestination() {
            return destination;
        }

        public void setDestination(String destination) {
            this.destination = destination;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public Map<String, Object> getProperties() {
            return properties;
        }

        public void setProperties(Map<String, Object> properties) {
            this.properties = properties;
        }
    }

    /**
     * Inner class representing delivery options for notifications.
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class DeliveryOptions {
        @JsonProperty("retry_count")
        private Integer retryCount;

        @JsonProperty("retry_delay_ms")
        private Long retryDelayMs;

        @JsonProperty("expiration_ms")
        private Long expirationMs;

        @JsonProperty("require_hmac")
        private Boolean requireHmac;

        @JsonProperty("hmac_algorithm")
        private String hmacAlgorithm;

        @JsonProperty("delivery_deadline")
        @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
        private LocalDateTime deliveryDeadline;

        /**
         * Default constructor for serialization frameworks.
         */
        public DeliveryOptions() {
        }

        /**
         * Constructor with retry options.
         *
         * @param retryCount   Number of retry attempts
         * @param retryDelayMs Delay between retry attempts in milliseconds
         */
        public DeliveryOptions(Integer retryCount, Long retryDelayMs) {
            this.retryCount = retryCount;
            this.retryDelayMs = retryDelayMs;
        }

        /**
         * Constructor with all fields.
         *
         * @param retryCount      Number of retry attempts
         * @param retryDelayMs    Delay between retry attempts in milliseconds
         * @param expirationMs    Expiration time for the notification in milliseconds
         * @param requireHmac     Whether HMAC signature is required
         * @param hmacAlgorithm   Algorithm to use for HMAC signature
         * @param deliveryDeadline Deadline for delivery of the notification
         */
        public DeliveryOptions(Integer retryCount, Long retryDelayMs, Long expirationMs,
                              Boolean requireHmac, String hmacAlgorithm, LocalDateTime deliveryDeadline) {
            this.retryCount = retryCount;
            this.retryDelayMs = retryDelayMs;
            this.expirationMs = expirationMs;
            this.requireHmac = requireHmac;
            this.hmacAlgorithm = hmacAlgorithm;
            this.deliveryDeadline = deliveryDeadline;
        }

        public Integer getRetryCount() {
            return retryCount;
        }

        public void setRetryCount(Integer retryCount) {
            this.retryCount = retryCount;
        }

        public Long getRetryDelayMs() {
            return retryDelayMs;
        }

        public void setRetryDelayMs(Long retryDelayMs) {
            this.retryDelayMs = retryDelayMs;
        }

        public Long getExpirationMs() {
            return expirationMs;
        }

        public void setExpirationMs(Long expirationMs) {
            this.expirationMs = expirationMs;
        }

        public Boolean getRequireHmac() {
            return requireHmac;
        }

        public void setRequireHmac(Boolean requireHmac) {
            this.requireHmac = requireHmac;
        }

        public String getHmacAlgorithm() {
            return hmacAlgorithm;
        }

        public void setHmacAlgorithm(String hmacAlgorithm) {
            this.hmacAlgorithm = hmacAlgorithm;
        }

        public LocalDateTime getDeliveryDeadline() {
            return deliveryDeadline;
        }

        public void setDeliveryDeadline(LocalDateTime deliveryDeadline) {
            this.deliveryDeadline = deliveryDeadline;
        }
    }

    // Getters and Setters

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public NotificationType getType() {
        return type;
    }

    public void setType(NotificationType type) {
        this.type = type;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }

    public NotificationPriority getPriority() {
        return priority;
    }

    public void setPriority(NotificationPriority priority) {
        this.priority = priority;
    }

    public List<Recipient> getRecipients() {
        return recipients;
    }

    public void setRecipients(List<Recipient> recipients) {
        this.recipients = recipients;
    }

    public Map<String, Object> getPayload() {
        return payload;
    }

    public void setPayload(Map<String, Object> payload) {
        this.payload = payload;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    public DeliveryOptions getDeliveryOptions() {
        return deliveryOptions;
    }

    public void setDeliveryOptions(DeliveryOptions deliveryOptions) {
        this.deliveryOptions = deliveryOptions;
    }

    /**
     * Adds a key-value pair to the payload map.
     *
     * @param key   The key for the payload entry
     * @param value The value for the payload entry
     * @return This NotificationMessage instance for method chaining
     */
    public NotificationMessage addPayload(String key, Object value) {
        this.payload.put(key, value);
        return this;
    }

    /**
     * Adds a key-value pair to the metadata map.
     *
     * @param key   The key for the metadata entry
     * @param value The value for the metadata entry
     * @return This NotificationMessage instance for method chaining
     */
    public NotificationMessage addMetadata(String key, Object value) {
        this.metadata.put(key, value);
        return this;
    }

    /**
     * Creates a builder for NotificationMessage.
     *
     * @return A new Builder instance
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder class for creating NotificationMessage instances.
     */
    public static class Builder {
        private String id;
        private NotificationType type;
        private NotificationPriority priority;
        private List<Recipient> recipients;
        private Map<String, Object> payload;
        private Map<String, Object> metadata;
        private DeliveryOptions deliveryOptions;

        private Builder() {
            this.payload = new HashMap<>();
            this.metadata = new HashMap<>();
        }

        public Builder id(String id) {
            this.id = id;
            return this;
        }

        public Builder type(NotificationType type) {
            this.type = type;
            return this;
        }

        public Builder priority(NotificationPriority priority) {
            this.priority = priority;
            return this;
        }

        public Builder recipients(List<Recipient> recipients) {
            this.recipients = recipients;
            return this;
        }

        public Builder payload(Map<String, Object> payload) {
            this.payload = payload;
            return this;
        }

        public Builder addPayload(String key, Object value) {
            this.payload.put(key, value);
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Builder addMetadata(String key, Object value) {
            this.metadata.put(key, value);
            return this;
        }

        public Builder deliveryOptions(DeliveryOptions deliveryOptions) {
            this.deliveryOptions = deliveryOptions;
            return this;
        }

        public NotificationMessage build() {
            NotificationMessage message = new NotificationMessage();
            message.id = this.id;
            message.type = this.type;
            message.timestamp = LocalDateTime.now();
            message.priority = this.priority;
            message.recipients = this.recipients;
            message.payload = this.payload;
            message.metadata = this.metadata;
            message.deliveryOptions = this.deliveryOptions;
            return message;
        }
    }
}