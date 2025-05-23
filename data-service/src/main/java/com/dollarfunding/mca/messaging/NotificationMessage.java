package com.dollarfunding.mca.messaging;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Min;
import javax.validation.constraints.Max;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Model class for notification messages published to RabbitMQ.
 * <p>
 * This class defines the structure of messages sent to the Notification Service
 * for delivery to external systems via webhooks or other channels. It includes fields
 * for notification type, recipient information, payload data, and delivery options.
 * </p>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class NotificationMessage {

    /**
     * Enum defining the types of notifications that can be sent.
     */
    public enum NotificationType {
        /**
         * Status update notification for an application
         */
        STATUS_UPDATE,
        
        /**
         * Error notification for an application
         */
        ERROR,
        
        /**
         * Completion notification for an application
         */
        COMPLETION,
        
        /**
         * Document received notification
         */
        DOCUMENT_RECEIVED,
        
        /**
         * Document processed notification
         */
        DOCUMENT_PROCESSED,
        
        /**
         * System notification
         */
        SYSTEM
    }

    /**
     * Enum defining the priority levels for notifications.
     */
    public enum NotificationPriority {
        /**
         * Low priority notification
         */
        LOW,
        
        /**
         * Medium priority notification
         */
        MEDIUM,
        
        /**
         * High priority notification
         */
        HIGH,
        
        /**
         * Critical priority notification
         */
        CRITICAL
    }

    /**
     * Enum defining the types of recipients for notifications.
     */
    public enum RecipientType {
        /**
         * Webhook endpoint recipient
         */
        WEBHOOK,
        
        /**
         * Email recipient
         */
        EMAIL,
        
        /**
         * SMS recipient
         */
        SMS,
        
        /**
         * Push notification recipient
         */
        PUSH
    }

    @NotBlank
    @JsonProperty("id")
    private String id;

    @NotNull
    @JsonProperty("type")
    private NotificationType type;

    @NotNull
    @JsonProperty("priority")
    private NotificationPriority priority;

    @NotNull
    @JsonProperty("timestamp")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime timestamp;

    @NotEmpty
    @JsonProperty("recipients")
    private List<Recipient> recipients;

    @NotNull
    @JsonProperty("payload")
    private Map<String, Object> payload;

    @JsonProperty("delivery_options")
    private DeliveryOptions deliveryOptions;

    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * Default constructor for serialization frameworks.
     */
    public NotificationMessage() {
        this.timestamp = LocalDateTime.now();
        this.recipients = new ArrayList<>();
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
     * @param payload    Payload data for the notification
     */
    public NotificationMessage(String id, NotificationType type, NotificationPriority priority,
                              List<Recipient> recipients, Map<String, Object> payload) {
        this.id = id;
        this.type = type;
        this.priority = priority;
        this.timestamp = LocalDateTime.now();
        this.recipients = recipients;
        this.payload = payload;
        this.metadata = new HashMap<>();
    }

    /**
     * Inner class representing a recipient for a notification.
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class Recipient {
        @NotNull
        @JsonProperty("type")
        private RecipientType type;

        @NotBlank
        @JsonProperty("address")
        private String address;

        @JsonProperty("name")
        private String name;

        @JsonProperty("config")
        private Map<String, Object> config;

        /**
         * Default constructor for serialization frameworks.
         */
        public Recipient() {
            this.config = new HashMap<>();
        }

        /**
         * Constructor with essential fields.
         *
         * @param type    Type of recipient
         * @param address Address of the recipient (e.g., webhook URL, email address)
         */
        public Recipient(RecipientType type, String address) {
            this.type = type;
            this.address = address;
            this.config = new HashMap<>();
        }

        /**
         * Constructor with all fields.
         *
         * @param type    Type of recipient
         * @param address Address of the recipient (e.g., webhook URL, email address)
         * @param name    Name of the recipient
         * @param config  Configuration options for the recipient
         */
        public Recipient(RecipientType type, String address, String name, Map<String, Object> config) {
            this.type = type;
            this.address = address;
            this.name = name;
            this.config = config != null ? config : new HashMap<>();
        }

        public RecipientType getType() {
            return type;
        }

        public void setType(RecipientType type) {
            this.type = type;
        }

        public String getAddress() {
            return address;
        }

        public void setAddress(String address) {
            this.address = address;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public Map<String, Object> getConfig() {
            return config;
        }

        public void setConfig(Map<String, Object> config) {
            this.config = config;
        }

        /**
         * Adds a configuration option for the recipient.
         *
         * @param key   The key for the configuration option
         * @param value The value for the configuration option
         * @return This Recipient instance for method chaining
         */
        public Recipient addConfig(String key, Object value) {
            this.config.put(key, value);
            return this;
        }
    }

    /**
     * Inner class representing delivery options for a notification.
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
         * Constructor with all fields.
         *
         * @param retryCount       Number of retry attempts for failed deliveries
         * @param retryDelayMs     Delay between retry attempts in milliseconds
         * @param expirationMs     Expiration time for the notification in milliseconds
         * @param requireHmac      Whether HMAC signature is required for webhook payloads
         * @param hmacAlgorithm    HMAC algorithm to use for signatures
         * @param deliveryDeadline Deadline for delivery attempts
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

    public NotificationPriority getPriority() {
        return priority;
    }

    public void setPriority(NotificationPriority priority) {
        this.priority = priority;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
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

    public DeliveryOptions getDeliveryOptions() {
        return deliveryOptions;
    }

    public void setDeliveryOptions(DeliveryOptions deliveryOptions) {
        this.deliveryOptions = deliveryOptions;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    /**
     * Adds a recipient to the notification.
     *
     * @param recipient The recipient to add
     * @return This NotificationMessage instance for method chaining
     */
    public NotificationMessage addRecipient(Recipient recipient) {
        this.recipients.add(recipient);
        return this;
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
        private DeliveryOptions deliveryOptions;
        private Map<String, Object> metadata;

        private Builder() {
            this.recipients = new ArrayList<>();
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

        public Builder addRecipient(Recipient recipient) {
            this.recipients.add(recipient);
            return this;
        }

        public Builder addRecipient(RecipientType type, String address) {
            this.recipients.add(new Recipient(type, address));
            return this;
        }

        public Builder addRecipient(RecipientType type, String address, String name, Map<String, Object> config) {
            this.recipients.add(new Recipient(type, address, name, config));
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

        public Builder deliveryOptions(DeliveryOptions deliveryOptions) {
            this.deliveryOptions = deliveryOptions;
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

        public NotificationMessage build() {
            NotificationMessage message = new NotificationMessage();
            message.id = this.id;
            message.type = this.type;
            message.priority = this.priority;
            message.timestamp = LocalDateTime.now();
            message.recipients = this.recipients;
            message.payload = this.payload;
            message.deliveryOptions = this.deliveryOptions;
            message.metadata = this.metadata;
            return message;
        }
    }
}