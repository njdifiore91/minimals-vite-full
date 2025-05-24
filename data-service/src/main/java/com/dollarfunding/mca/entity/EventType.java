package com.dollarfunding.mca.entity;

import java.util.Arrays;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Enum defining the possible event types for webhook notifications.
 * <p>
 * This enum represents the different types of events that can trigger webhook notifications
 * in the Merchant Cash Advance (MCA) Application Processing System. Each event type has a
 * description and is used by the Webhook entity to specify which events trigger webhook
 * notifications.
 * </p>
 */
public enum EventType {
    
    /**
     * Triggered when a new application is created in the system.
     */
    APPLICATION_CREATED("Application Created", "Triggered when a new application is created in the system"),
    
    /**
     * Triggered when an existing application is updated.
     */
    APPLICATION_UPDATED("Application Updated", "Triggered when an existing application is updated"),
    
    /**
     * Triggered when an application is approved.
     */
    APPLICATION_APPROVED("Application Approved", "Triggered when an application is approved"),
    
    /**
     * Triggered when an application is rejected.
     */
    APPLICATION_REJECTED("Application Rejected", "Triggered when an application is rejected"),
    
    /**
     * Triggered when a new document is uploaded to the system.
     */
    DOCUMENT_UPLOADED("Document Uploaded", "Triggered when a new document is uploaded to the system"),
    
    /**
     * Triggered when a document has been processed by the OCR service.
     */
    DOCUMENT_PROCESSED("Document Processed", "Triggered when a document has been processed by the OCR service");
    
    private final String displayName;
    private final String description;
    
    // Cache for efficient lookup by name
    private static final Map<String, EventType> BY_NAME = 
            Arrays.stream(values())
                  .collect(Collectors.toMap(EventType::name, Function.identity()));
    
    /**
     * Constructor for EventType enum.
     *
     * @param displayName The human-readable display name for the event type
     * @param description A detailed description of when this event is triggered
     */
    EventType(String displayName, String description) {
        this.displayName = displayName;
        this.description = description;
    }
    
    /**
     * Gets the display name of the event type.
     *
     * @return The human-readable display name
     */
    public String getDisplayName() {
        return displayName;
    }
    
    /**
     * Gets the description of the event type.
     *
     * @return The detailed description
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Safely converts a string to an EventType.
     *
     * @param name The name of the event type to convert
     * @return An Optional containing the EventType if found, or empty if not found
     */
    public static Optional<EventType> fromString(String name) {
        if (name == null || name.isEmpty()) {
            return Optional.empty();
        }
        return Optional.ofNullable(BY_NAME.get(name.toUpperCase()));
    }
    
    /**
     * Validates if a given string is a valid EventType.
     *
     * @param name The name to validate
     * @return true if the name is a valid EventType, false otherwise
     */
    public static boolean isValid(String name) {
        return fromString(name).isPresent();
    }
    
    /**
     * Generates a sample payload structure for this event type.
     * This can be used for documentation or testing purposes.
     *
     * @return A Map representing the structure of the payload for this event type
     */
    public Map<String, Object> generateSamplePayload() {
        switch (this) {
            case APPLICATION_CREATED:
            case APPLICATION_UPDATED:
            case APPLICATION_APPROVED:
            case APPLICATION_REJECTED:
                return generateApplicationPayload();
            case DOCUMENT_UPLOADED:
            case DOCUMENT_PROCESSED:
                return generateDocumentPayload();
            default:
                throw new IllegalStateException("Unexpected event type: " + this);
        }
    }
    
    /**
     * Generates a sample application event payload.
     *
     * @return A Map representing the structure of an application event payload
     */
    private Map<String, Object> generateApplicationPayload() {
        return Map.of(
            "event_type", this.name(),
            "event_id", "evt_" + System.currentTimeMillis(),
            "timestamp", System.currentTimeMillis(),
            "data", Map.of(
                "application_id", "app_12345",
                "status", this == APPLICATION_APPROVED ? "APPROVED" : 
                         this == APPLICATION_REJECTED ? "REJECTED" : "PENDING",
                "merchant", Map.of(
                    "legal_name", "Example Business LLC",
                    "dba_name", "Example Business",
                    "industry", "Retail"
                )
            )
        );
    }
    
    /**
     * Generates a sample document event payload.
     *
     * @return A Map representing the structure of a document event payload
     */
    private Map<String, Object> generateDocumentPayload() {
        return Map.of(
            "event_type", this.name(),
            "event_id", "evt_" + System.currentTimeMillis(),
            "timestamp", System.currentTimeMillis(),
            "data", Map.of(
                "document_id", "doc_12345",
                "application_id", "app_12345",
                "document_type", "BANK_STATEMENT",
                "status", this == DOCUMENT_PROCESSED ? "PROCESSED" : "UPLOADED",
                "confidence_score", this == DOCUMENT_PROCESSED ? 0.95 : null
            )
        );
    }
    
    /**
     * Returns the event type as a string for use in JSON payloads.
     *
     * @return The name of the event type in lowercase with underscores replaced by dots
     */
    public String toEventString() {
        return name().toLowerCase().replace('_', '.');
    }
    
    @Override
    public String toString() {
        return name();
    }
}