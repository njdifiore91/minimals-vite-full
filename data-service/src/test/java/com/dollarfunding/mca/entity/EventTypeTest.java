package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Unit tests for the {@link EventType} enum.
 * <p>
 * These tests verify the behavior of the EventType enum, including:
 * - Enum constants and their descriptions
 * - Conversion methods for serialization and deserialization
 * - Validation methods
 * - Event categorization methods
 * - Payload type determination
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
    @DisplayName("Should have non-null description for each enum constant")
    public void shouldHaveNonNullDescription(EventType eventType) {
        assertNotNull(eventType.getDescription(), "Description should not be null");
        assertFalse(eventType.getDescription().isEmpty(), "Description should not be empty");
    }

    @Test
    @DisplayName("Should have correct descriptions for each enum constant")
    public void shouldHaveCorrectDescriptions() {
        assertEquals("Application Created", EventType.APPLICATION_CREATED.getDescription());
        assertEquals("Application Updated", EventType.APPLICATION_UPDATED.getDescription());
        assertEquals("Application Approved", EventType.APPLICATION_APPROVED.getDescription());
        assertEquals("Application Rejected", EventType.APPLICATION_REJECTED.getDescription());
        assertEquals("Document Uploaded", EventType.DOCUMENT_UPLOADED.getDescription());
        assertEquals("Document Processed", EventType.DOCUMENT_PROCESSED.getDescription());
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("getValue() should return the enum name for JSON serialization")
    public void getValue_ShouldReturnEnumName(EventType eventType) {
        assertEquals(eventType.name(), eventType.getValue(), 
                "getValue() should return the enum name for JSON serialization");
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("fromValue() should correctly deserialize from string")
    public void fromValue_ShouldDeserializeCorrectly(EventType eventType) {
        String value = eventType.name();
        EventType result = EventType.fromValue(value);
        assertEquals(eventType, result, "fromValue() should return the correct enum constant");
    }

    @Test
    @DisplayName("fromValue() should throw IllegalArgumentException for invalid value")
    public void fromValue_ShouldThrowExceptionForInvalidValue() {
        assertThrows(IllegalArgumentException.class, () -> EventType.fromValue("INVALID_EVENT_TYPE"),
                "fromValue() should throw IllegalArgumentException for invalid value");
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("fromValueSafe() should correctly deserialize from string")
    public void fromValueSafe_ShouldDeserializeCorrectly(EventType eventType) {
        String value = eventType.name();
        var result = EventType.fromValueSafe(value);
        assertTrue(result.isPresent(), "fromValueSafe() should return a non-empty Optional for valid value");
        assertEquals(eventType, result.get(), "fromValueSafe() should return the correct enum constant");
    }

    @Test
    @DisplayName("fromValueSafe() should return empty Optional for invalid value")
    public void fromValueSafe_ShouldReturnEmptyOptionalForInvalidValue() {
        var result = EventType.fromValueSafe("INVALID_EVENT_TYPE");
        assertFalse(result.isPresent(), "fromValueSafe() should return an empty Optional for invalid value");
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("isValid() should return true for valid enum names")
    public void isValid_ShouldReturnTrueForValidNames(EventType eventType) {
        String value = eventType.name();
        assertTrue(EventType.isValid(value), "isValid() should return true for valid enum names");
    }

    @Test
    @DisplayName("isValid() should return false for invalid enum names")
    public void isValid_ShouldReturnFalseForInvalidNames() {
        assertFalse(EventType.isValid("INVALID_EVENT_TYPE"), 
                "isValid() should return false for invalid enum names");
        assertFalse(EventType.isValid(null), 
                "isValid() should return false for null value");
        assertFalse(EventType.isValid(""), 
                "isValid() should return false for empty string");
    }

    @Test
    @DisplayName("isApplicationEvent() should correctly identify application events")
    public void isApplicationEvent_ShouldIdentifyApplicationEvents() {
        assertTrue(EventType.APPLICATION_CREATED.isApplicationEvent());
        assertTrue(EventType.APPLICATION_UPDATED.isApplicationEvent());
        assertTrue(EventType.APPLICATION_APPROVED.isApplicationEvent());
        assertTrue(EventType.APPLICATION_REJECTED.isApplicationEvent());
        assertFalse(EventType.DOCUMENT_UPLOADED.isApplicationEvent());
        assertFalse(EventType.DOCUMENT_PROCESSED.isApplicationEvent());
    }

    @Test
    @DisplayName("isDocumentEvent() should correctly identify document events")
    public void isDocumentEvent_ShouldIdentifyDocumentEvents() {
        assertFalse(EventType.APPLICATION_CREATED.isDocumentEvent());
        assertFalse(EventType.APPLICATION_UPDATED.isDocumentEvent());
        assertFalse(EventType.APPLICATION_APPROVED.isDocumentEvent());
        assertFalse(EventType.APPLICATION_REJECTED.isDocumentEvent());
        assertTrue(EventType.DOCUMENT_UPLOADED.isDocumentEvent());
        assertTrue(EventType.DOCUMENT_PROCESSED.isDocumentEvent());
    }

    @Test
    @DisplayName("getPayloadType() should return correct payload type for each event")
    public void getPayloadType_ShouldReturnCorrectType() {
        // Application events should return "application" payload type
        assertEquals("application", EventType.APPLICATION_CREATED.getPayloadType());
        assertEquals("application", EventType.APPLICATION_UPDATED.getPayloadType());
        assertEquals("application", EventType.APPLICATION_APPROVED.getPayloadType());
        assertEquals("application", EventType.APPLICATION_REJECTED.getPayloadType());
        
        // Document events should return "document" payload type
        assertEquals("document", EventType.DOCUMENT_UPLOADED.getPayloadType());
        assertEquals("document", EventType.DOCUMENT_PROCESSED.getPayloadType());
    }

    @ParameterizedTest
    @EnumSource(EventType.class)
    @DisplayName("toString() should include name and description")
    public void toString_ShouldIncludeNameAndDescription(EventType eventType) {
        String result = eventType.toString();
        assertTrue(result.contains(eventType.name()), 
                "toString() should include the enum name");
        assertTrue(result.contains(eventType.getDescription()), 
                "toString() should include the description");
        assertTrue(result.contains("(") && result.contains(")"), 
                "toString() should format with parentheses");
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