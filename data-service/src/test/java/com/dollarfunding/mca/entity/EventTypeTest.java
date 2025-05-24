package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.Map;
import java.util.Optional;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Unit tests for the {@link EventType} enum.
 * <p>
 * These tests verify the behavior of the EventType enum, including:
 * - Enum constants and their display names and descriptions
 * - Methods for finding event types by name
 * - Conversion methods for serialization and deserialization
 * - Sample payload generation for different event types
 * </p>
 */
public class EventTypeTest {

    @Test
    @DisplayName("Should have the expected number of enum constants")
    public void shouldHaveExpectedNumberOfConstants() {
        assertEquals(6, EventType.values().length, "EventType should have exactly 6 constants");
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("Should have non-null display name for each enum constant")
    public void shouldHaveNonNullDisplayName(EventType eventType) {
        assertNotNull(eventType.getDisplayName(), "Display name should not be null");
        assertFalse(eventType.getDisplayName().isEmpty(), "Display name should not be empty");
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("Should have non-null description for each enum constant")
    public void shouldHaveNonNullDescription(EventType eventType) {
        assertNotNull(eventType.getDescription(), "Description should not be null");
        assertFalse(eventType.getDescription().isEmpty(), "Description should not be empty");
    }

    @Test
    @DisplayName("Should have correct display names for each enum constant")
    public void shouldHaveCorrectDisplayNames() {
        assertEquals("Application Created", EventType.APPLICATION_CREATED.getDisplayName());
        assertEquals("Application Updated", EventType.APPLICATION_UPDATED.getDisplayName());
        assertEquals("Application Approved", EventType.APPLICATION_APPROVED.getDisplayName());
        assertEquals("Application Rejected", EventType.APPLICATION_REJECTED.getDisplayName());
        assertEquals("Document Uploaded", EventType.DOCUMENT_UPLOADED.getDisplayName());
        assertEquals("Document Processed", EventType.DOCUMENT_PROCESSED.getDisplayName());
    }

    @Test
    @DisplayName("Should have correct descriptions for each enum constant")
    public void shouldHaveCorrectDescriptions() {
        assertEquals("Triggered when a new application is created in the system", 
                EventType.APPLICATION_CREATED.getDescription());
        assertEquals("Triggered when an existing application is updated", 
                EventType.APPLICATION_UPDATED.getDescription());
        assertEquals("Triggered when an application is approved", 
                EventType.APPLICATION_APPROVED.getDescription());
        assertEquals("Triggered when an application is rejected", 
                EventType.APPLICATION_REJECTED.getDescription());
        assertEquals("Triggered when a new document is uploaded to the system", 
                EventType.DOCUMENT_UPLOADED.getDescription());
        assertEquals("Triggered when a document has been processed by the OCR service", 
                EventType.DOCUMENT_PROCESSED.getDescription());
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("fromString() should find enum constant by name")
    public void fromString_ShouldFindEnumConstantByName(EventType eventType) {
        String name = eventType.name();
        Optional<EventType> result = EventType.fromString(name);
        
        assertTrue(result.isPresent(), "fromString() should find the enum constant");
        assertEquals(eventType, result.get(), "fromString() should return the correct enum constant");
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("fromString() should find enum constant by name (case-insensitive)")
    public void fromString_ShouldBeCaseInsensitive(EventType eventType) {
        String lowerCaseName = eventType.name().toLowerCase();
        Optional<EventType> result = EventType.fromString(lowerCaseName);
        
        assertTrue(result.isPresent(), "fromString() should find the enum constant (case-insensitive)");
        assertEquals(eventType, result.get(), "fromString() should return the correct enum constant");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_EVENT_TYPE", "unknown"})
    @DisplayName("fromString() should return empty Optional for invalid name")
    public void fromString_ShouldReturnEmptyOptionalForInvalidName(String invalidName) {
        Optional<EventType> result = EventType.fromString(invalidName);
        assertFalse(result.isPresent(), "fromString() should return an empty Optional for invalid name");
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("isValid() should return true for valid event type names")
    public void isValid_ShouldReturnTrueForValidNames(EventType eventType) {
        String name = eventType.name();
        assertTrue(EventType.isValid(name), "isValid() should return true for valid event type name");
        
        // Test case-insensitivity
        String lowerCaseName = name.toLowerCase();
        assertTrue(EventType.isValid(lowerCaseName), "isValid() should be case-insensitive");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_EVENT_TYPE", "unknown"})
    @DisplayName("isValid() should return false for invalid event type names")
    public void isValid_ShouldReturnFalseForInvalidNames(String invalidName) {
        assertFalse(EventType.isValid(invalidName), "isValid() should return false for invalid event type name");
    }

    @Test
    @DisplayName("toEventString() should convert enum name to lowercase with dots")
    public void toEventString_ShouldConvertEnumNameToLowercaseWithDots() {
        assertEquals("application.created", EventType.APPLICATION_CREATED.toEventString());
        assertEquals("application.updated", EventType.APPLICATION_UPDATED.toEventString());
        assertEquals("application.approved", EventType.APPLICATION_APPROVED.toEventString());
        assertEquals("application.rejected", EventType.APPLICATION_REJECTED.toEventString());
        assertEquals("document.uploaded", EventType.DOCUMENT_UPLOADED.toEventString());
        assertEquals("document.processed", EventType.DOCUMENT_PROCESSED.toEventString());
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("toString() should return the enum name")
    public void toString_ShouldReturnEnumName(EventType eventType) {
        assertEquals(eventType.name(), eventType.toString(), 
                "toString() should return the enum name");
    }

    @Test
    @DisplayName("generateSamplePayload() should return non-null payload for all event types")
    public void generateSamplePayload_ShouldReturnNonNullPayload() {
        for (EventType eventType : EventType.values()) {
            Map<String, Object> payload = eventType.generateSamplePayload();
            assertNotNull(payload, "Sample payload should not be null");
            assertFalse(payload.isEmpty(), "Sample payload should not be empty");
        }
    }

    @Test
    @DisplayName("Application event payloads should have correct structure")
    public void applicationEventPayloads_ShouldHaveCorrectStructure() {
        EventType[] applicationEvents = {
            EventType.APPLICATION_CREATED,
            EventType.APPLICATION_UPDATED,
            EventType.APPLICATION_APPROVED,
            EventType.APPLICATION_REJECTED
        };
        
        for (EventType eventType : applicationEvents) {
            Map<String, Object> payload = eventType.generateSamplePayload();
            
            // Check top-level fields
            assertTrue(payload.containsKey("event_type"), "Payload should contain event_type");
            assertTrue(payload.containsKey("event_id"), "Payload should contain event_id");
            assertTrue(payload.containsKey("timestamp"), "Payload should contain timestamp");
            assertTrue(payload.containsKey("data"), "Payload should contain data");
            
            // Check event_type value
            assertEquals(eventType.name(), payload.get("event_type"), 
                    "event_type should match the enum name");
            
            // Check data structure
            @SuppressWarnings("unchecked")
            Map<String, Object> data = (Map<String, Object>) payload.get("data");
            assertTrue(data.containsKey("application_id"), "Data should contain application_id");
            assertTrue(data.containsKey("status"), "Data should contain status");
            assertTrue(data.containsKey("merchant"), "Data should contain merchant");
            
            // Check merchant structure
            @SuppressWarnings("unchecked")
            Map<String, Object> merchant = (Map<String, Object>) data.get("merchant");
            assertTrue(merchant.containsKey("legal_name"), "Merchant should contain legal_name");
            assertTrue(merchant.containsKey("dba_name"), "Merchant should contain dba_name");
            assertTrue(merchant.containsKey("industry"), "Merchant should contain industry");
        }
    }

    @Test
    @DisplayName("Document event payloads should have correct structure")
    public void documentEventPayloads_ShouldHaveCorrectStructure() {
        EventType[] documentEvents = {
            EventType.DOCUMENT_UPLOADED,
            EventType.DOCUMENT_PROCESSED
        };
        
        for (EventType eventType : documentEvents) {
            Map<String, Object> payload = eventType.generateSamplePayload();
            
            // Check top-level fields
            assertTrue(payload.containsKey("event_type"), "Payload should contain event_type");
            assertTrue(payload.containsKey("event_id"), "Payload should contain event_id");
            assertTrue(payload.containsKey("timestamp"), "Payload should contain timestamp");
            assertTrue(payload.containsKey("data"), "Payload should contain data");
            
            // Check event_type value
            assertEquals(eventType.name(), payload.get("event_type"), 
                    "event_type should match the enum name");
            
            // Check data structure
            @SuppressWarnings("unchecked")
            Map<String, Object> data = (Map<String, Object>) payload.get("data");
            assertTrue(data.containsKey("document_id"), "Data should contain document_id");
            assertTrue(data.containsKey("application_id"), "Data should contain application_id");
            assertTrue(data.containsKey("document_type"), "Data should contain document_type");
            assertTrue(data.containsKey("status"), "Data should contain status");
            
            // Check confidence_score for DOCUMENT_PROCESSED
            if (eventType == EventType.DOCUMENT_PROCESSED) {
                assertTrue(data.containsKey("confidence_score"), 
                        "DOCUMENT_PROCESSED should contain confidence_score");
                assertNotNull(data.get("confidence_score"), 
                        "confidence_score should not be null for DOCUMENT_PROCESSED");
            } else {
                assertEquals(null, data.get("confidence_score"), 
                        "confidence_score should be null for DOCUMENT_UPLOADED");
            }
        }
    }

    @Test
    @DisplayName("All enum constants should be unique")
    public void allEnumConstantsShouldBeUnique() {
        EventType[] values = EventType.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(EventType::name)
                .distinct()
                .count(), 
                "All enum constants should have unique names");
    }

    @Test
    @DisplayName("All enum display names should be unique")
    public void allEnumDisplayNamesShouldBeUnique() {
        EventType[] values = EventType.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(EventType::getDisplayName)
                .distinct()
                .count(), 
                "All enum constants should have unique display names");
    }

    @Test
    @DisplayName("All enum descriptions should be unique")
    public void allEnumDescriptionsShouldBeUnique() {
        EventType[] values = EventType.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(EventType::getDescription)
                .distinct()
                .count(), 
                "All enum constants should have unique descriptions");
    }
}