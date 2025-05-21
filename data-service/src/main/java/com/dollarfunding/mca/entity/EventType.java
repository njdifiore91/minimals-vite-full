package com.dollarfunding.mca.entity;

import java.util.Arrays;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Enum representing the possible event types for webhook notifications.
 * <p>
 * This enum defines all supported event types that can trigger webhook notifications
 * in the Merchant Cash Advance (MCA) Application Processing System. Each event type
 * includes a description and can be used to generate appropriate event payloads.
 * </p>
 * <p>
 * The enum is designed to be used with JPA for database persistence and includes
 * methods for validation and conversion between string representations and enum values.
 * </p>
 */
public enum EventType {
    
    /**
     * Triggered when a new application is created in the system.
     */
    APPLICATION_CREATED("Application Created"),
    
    /**
     * Triggered when an existing application is updated with new information.
     */
    APPLICATION_UPDATED("Application Updated"),
    
    /**
     * Triggered when an application is approved by the operations staff.
     */
    APPLICATION_APPROVED("Application Approved"),
    
    /**
     * Triggered when an application is rejected by the operations staff.
     */
    APPLICATION_REJECTED("Application Rejected"),
    
    /**
     * Triggered when a new document is uploaded to an application.
     */
    DOCUMENT_UPLOADED("Document Uploaded"),
    
    /**
     * Triggered when a document has been processed by the OCR service.
     */
    DOCUMENT_PROCESSED("Document Processed");
    
    private final String description;
    
    private static final Map<String, EventType> EVENT_TYPE_MAP = Arrays.stream(EventType.values())
            .collect(Collectors.toMap(EventType::name, Function.identity()));
    
    /**
     * Constructor for EventType enum.
     *
     * @param description Human-readable description of the event type
     */
    EventType(String description) {
        this.description = description;
    }
    
    /**
     * Gets the human-readable description of this event type.
     *
     * @return The description of the event type
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Gets the enum value as a string for JSON serialization.
     *
     * @return The string representation of this enum value
     */
    @JsonValue
    public String getValue() {
        return name();
    }
    
    /**
     * Creates an EventType from its string representation for JSON deserialization.
     *
     * @param value The string representation of the event type
     * @return The corresponding EventType enum value
     * @throws IllegalArgumentException if the value does not match any EventType
     */
    @JsonCreator
    public static EventType fromValue(String value) {
        return Optional.ofNullable(EVENT_TYPE_MAP.get(value))
                .orElseThrow(() -> new IllegalArgumentException("Unknown event type: " + value));
    }
    
    /**
     * Safely converts a string to an EventType without throwing an exception.
     *
     * @param value The string representation of the event type
     * @return An Optional containing the EventType if valid, or empty if invalid
     */
    public static Optional<EventType> fromValueSafe(String value) {
        return Optional.ofNullable(EVENT_TYPE_MAP.get(value));
    }
    
    /**
     * Checks if the given string represents a valid EventType.
     *
     * @param value The string to validate
     * @return true if the string is a valid EventType, false otherwise
     */
    public static boolean isValid(String value) {
        return EVENT_TYPE_MAP.containsKey(value);
    }
    
    /**
     * Determines if this event type is related to application status changes.
     *
     * @return true if this is an application-related event, false otherwise
     */
    public boolean isApplicationEvent() {
        return this == APPLICATION_CREATED || this == APPLICATION_UPDATED || 
               this == APPLICATION_APPROVED || this == APPLICATION_REJECTED;
    }
    
    /**
     * Determines if this event type is related to document operations.
     *
     * @return true if this is a document-related event, false otherwise
     */
    public boolean isDocumentEvent() {
        return this == DOCUMENT_UPLOADED || this == DOCUMENT_PROCESSED;
    }
    
    /**
     * Gets the base payload type for this event type.
     * This is used to determine the structure of the webhook payload.
     *
     * @return The name of the payload type as a string
     */
    public String getPayloadType() {
        if (isApplicationEvent()) {
            return "application";
        } else if (isDocumentEvent()) {
            return "document";
        } else {
            return "generic";
        }
    }
    
    /**
     * Returns a string representation of this EventType.
     *
     * @return A string containing the name and description of this event type
     */
    @Override
    public String toString() {
        return name() + " (" + description + ")";
    }
}