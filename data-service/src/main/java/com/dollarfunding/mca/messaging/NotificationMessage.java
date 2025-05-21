package com.dollarfunding.mca.messaging;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Model class for notification messages published to RabbitMQ.
 * It defines the structure of messages sent to the Notification Service
 * for delivery to external systems via webhooks or other channels.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class NotificationMessage {

    /**
     * Notification type enumeration.
     */
    public enum Type {
        STATUS_UPDATE,
        ERROR,
        COMPLETION,
        DOCUMENT_RECEIVED,
        DOCUMENT_PROCESSED,
        APPLICATION_CREATED,
        APPLICATION_UPDATED,
        APPLICATION_APPROVED,
        APPLICATION_REJECTED
    }

    /**
     * Notification priority enumeration.
     */
    public enum Priority {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    /**
     * Recipient type enumeration.
     */
    public enum RecipientType {
        WEBHOOK,
        EMAIL,
        SMS,
        PUSH
    }

    @NotNull
    @JsonProperty("notification_id")
    private String notificationId;

    @NotNull
    @JsonProperty("type")
    private Type type;

    @NotNull
    @JsonProperty("priority")
    private Priority priority;

    @NotNull
    @JsonProperty("timestamp")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSSZ")
    private LocalDateTime timestamp;

    @NotNull
    @JsonProperty("recipient")
    private Recipient recipient;

    @NotNull
    @JsonProperty("payload")
    private Map<String, Object> payload;

    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * Recipient information for the notification.
     */
    public static class Recipient {
        @NotNull
        @JsonProperty("type")
        private RecipientType type;

        @NotBlank
        @JsonProperty("destination")
        private String destination;

        @JsonProperty("properties")
        private Map<String, Object> properties;

        public Recipient() {
            this.properties = new HashMap<>();
        }

        public Recipient(RecipientType type, String destination) {
            this.type = type;
            this.destination = destination;
            this.properties = new HashMap<>();
        }

        public RecipientType getType() {
            return type;
        }

        public void setType(RecipientType type) {
            this.type = type;
        }

        public String getDestination() {
            return destination;
        }

        public void setDestination(String destination) {
            this.destination = destination;
        }

        public Map<String, Object> getProperties() {
            return properties;
        }

        public void setProperties(Map<String, Object> properties) {
            this.properties = properties;
        }

        public void addProperty(String key, Object value) {
            this.properties.put(key, value);
        }
    }

    /**
     * Default constructor.
     */
    public NotificationMessage() {
        this.timestamp = LocalDateTime.now();
        this.payload = new HashMap<>();
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor with essential fields.
     *
     * @param notificationId Unique identifier for the notification
     * @param type Type of notification
     * @param priority Priority level of the notification
     * @param recipient Recipient information
     */
    public NotificationMessage(String notificationId, Type type, Priority priority, Recipient recipient) {
        this.notificationId = notificationId;
        this.type = type;
        this.priority = priority;
        this.recipient = recipient;
        this.timestamp = LocalDateTime.now();
        this.payload = new HashMap<>();
        this.metadata = new HashMap<>();
    }

    /**
     * @return Unique identifier for the notification
     */
    public String getNotificationId() {
        return notificationId;
    }

    /**
     * @param notificationId Unique identifier for the notification
     */
    public void setNotificationId(String notificationId) {
        this.notificationId = notificationId;
    }

    /**
     * @return Type of notification
     */
    public Type getType() {
        return type;
    }

    /**
     * @param type Type of notification
     */
    public void setType(Type type) {
        this.type = type;
    }

    /**
     * @return Priority level of the notification
     */
    public Priority getPriority() {
        return priority;
    }

    /**
     * @param priority Priority level of the notification
     */
    public void setPriority(Priority priority) {
        this.priority = priority;
    }

    /**
     * @return Timestamp when the notification was created
     */
    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    /**
     * @param timestamp Timestamp when the notification was created
     */
    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }

    /**
     * @return Recipient information
     */
    public Recipient getRecipient() {
        return recipient;
    }

    /**
     * @param recipient Recipient information
     */
    public void setRecipient(Recipient recipient) {
        this.recipient = recipient;
    }

    /**
     * @return Payload data for the notification
     */
    public Map<String, Object> getPayload() {
        return payload;
    }

    /**
     * @param payload Payload data for the notification
     */
    public void setPayload(Map<String, Object> payload) {
        this.payload = payload;
    }

    /**
     * Add a key-value pair to the payload.
     *
     * @param key Key for the payload entry
     * @param value Value for the payload entry
     */
    public void addPayload(String key, Object value) {
        this.payload.put(key, value);
    }

    /**
     * @return Metadata for the notification
     */
    public Map<String, Object> getMetadata() {
        return metadata;
    }

    /**
     * @param metadata Metadata for the notification
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    /**
     * Add a key-value pair to the metadata.
     *
     * @param key Key for the metadata entry
     * @param value Value for the metadata entry
     */
    public void addMetadata(String key, Object value) {
        this.metadata.put(key, value);
    }

    /**
     * Creates a builder for the NotificationMessage.
     *
     * @return A new builder instance
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder class for creating NotificationMessage instances.
     */
    public static class Builder {
        private String notificationId;
        private Type type;
        private Priority priority = Priority.MEDIUM; // Default priority
        private Recipient recipient;
        private Map<String, Object> payload = new HashMap<>();
        private Map<String, Object> metadata = new HashMap<>();

        /**
         * @param notificationId Unique identifier for the notification
         * @return The builder instance
         */
        public Builder notificationId(String notificationId) {
            this.notificationId = notificationId;
            return this;
        }

        /**
         * @param type Type of notification
         * @return The builder instance
         */
        public Builder type(Type type) {
            this.type = type;
            return this;
        }

        /**
         * @param priority Priority level of the notification
         * @return The builder instance
         */
        public Builder priority(Priority priority) {
            this.priority = priority;
            return this;
        }

        /**
         * @param recipient Recipient information
         * @return The builder instance
         */
        public Builder recipient(Recipient recipient) {
            this.recipient = recipient;
            return this;
        }

        /**
         * @param type Recipient type
         * @param destination Recipient destination
         * @return The builder instance
         */
        public Builder recipient(RecipientType type, String destination) {
            this.recipient = new Recipient(type, destination);
            return this;
        }

        /**
         * @param payload Payload data for the notification
         * @return The builder instance
         */
        public Builder payload(Map<String, Object> payload) {
            this.payload = payload;
            return this;
        }

        /**
         * Add a key-value pair to the payload.
         *
         * @param key Key for the payload entry
         * @param value Value for the payload entry
         * @return The builder instance
         */
        public Builder addPayload(String key, Object value) {
            this.payload.put(key, value);
            return this;
        }

        /**
         * @param metadata Metadata for the notification
         * @return The builder instance
         */
        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        /**
         * Add a key-value pair to the metadata.
         *
         * @param key Key for the metadata entry
         * @param value Value for the metadata entry
         * @return The builder instance
         */
        public Builder addMetadata(String key, Object value) {
            this.metadata.put(key, value);
            return this;
        }

        /**
         * Builds the NotificationMessage instance.
         *
         * @return A new NotificationMessage instance
         */
        public NotificationMessage build() {
            NotificationMessage message = new NotificationMessage();
            message.setNotificationId(notificationId);
            message.setType(type);
            message.setPriority(priority);
            message.setRecipient(recipient);
            message.setPayload(payload);
            message.setMetadata(metadata);
            message.setTimestamp(LocalDateTime.now());
            return message;
        }
    }
}