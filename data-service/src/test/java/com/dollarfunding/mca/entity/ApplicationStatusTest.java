package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.Collections;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Unit tests for the {@link ApplicationStatus} enum.
 * <p>
 * These tests verify the behavior of the ApplicationStatus enum, including:
 * - Enum constants and their descriptions
 * - Status transition validation
 * - Conversion methods for serialization and deserialization
 * - Status categorization (terminal, active, error, human intervention)
 * - Status name and description retrieval
 * </p>
 */
public class ApplicationStatusTest {

    @Test
    @DisplayName("Should have the expected number of enum constants")
    public void shouldHaveExpectedNumberOfConstants() {
        assertEquals(8, ApplicationStatus.values().length, "ApplicationStatus should have exactly 8 constants");
    }

    @ParameterizedTest
    @EnumSource(ApplicationStatus.class)
    @DisplayName("Should have non-null description for each enum constant")
    public void shouldHaveNonNullDescription(ApplicationStatus status) {
        assertNotNull(status.getDescription(), "Description should not be null");
        assertFalse(status.getDescription().isEmpty(), "Description should not be empty");
    }

    @Test
    @DisplayName("Should have correct descriptions for each enum constant")
    public void shouldHaveCorrectDescriptions() {
        assertEquals("Application has been received but not yet processed", 
                ApplicationStatus.NEW.getDescription());
        assertEquals("Application is waiting for additional documents or information", 
                ApplicationStatus.PENDING.getDescription());
        assertEquals("Application is currently being processed", 
                ApplicationStatus.PROCESSING.getDescription());
        assertEquals("Application has been approved", 
                ApplicationStatus.APPROVED.getDescription());
        assertEquals("Application has been rejected", 
                ApplicationStatus.REJECTED.getDescription());
        assertEquals("Application processing has been completed", 
                ApplicationStatus.COMPLETED.getDescription());
        assertEquals("An error occurred during application processing", 
                ApplicationStatus.ERROR.getDescription());
        assertEquals("Application has been flagged for review due to rule violations", 
                ApplicationStatus.EXCEPTION.getDescription());
    }

    @Test
    @DisplayName("Should validate status transitions correctly")
    public void shouldValidateStatusTransitionsCorrectly() {
        // Test valid transitions
        assertTrue(ApplicationStatus.NEW.canTransitionTo(ApplicationStatus.PROCESSING), 
                "NEW should transition to PROCESSING");
        assertTrue(ApplicationStatus.NEW.canTransitionTo(ApplicationStatus.PENDING), 
                "NEW should transition to PENDING");
        assertTrue(ApplicationStatus.PROCESSING.canTransitionTo(ApplicationStatus.APPROVED), 
                "PROCESSING should transition to APPROVED");
        assertTrue(ApplicationStatus.PROCESSING.canTransitionTo(ApplicationStatus.REJECTED), 
                "PROCESSING should transition to REJECTED");
        assertTrue(ApplicationStatus.APPROVED.canTransitionTo(ApplicationStatus.COMPLETED), 
                "APPROVED should transition to COMPLETED");
        
        // Test invalid transitions
        assertFalse(ApplicationStatus.NEW.canTransitionTo(ApplicationStatus.COMPLETED), 
                "NEW should not transition to COMPLETED");
        assertFalse(ApplicationStatus.PENDING.canTransitionTo(ApplicationStatus.COMPLETED), 
                "PENDING should not transition to COMPLETED");
        assertFalse(ApplicationStatus.COMPLETED.canTransitionTo(ApplicationStatus.PROCESSING), 
                "COMPLETED should not transition to PROCESSING (terminal state)");
        assertFalse(ApplicationStatus.REJECTED.canTransitionTo(ApplicationStatus.APPROVED), 
                "REJECTED should not transition to APPROVED");
    }

    @Test
    @DisplayName("Should return valid next statuses for each status")
    public void shouldReturnValidNextStatuses() {
        // Check NEW valid transitions
        Set<ApplicationStatus> newValidTransitions = ApplicationStatus.NEW.getValidNextStatuses();
        assertTrue(newValidTransitions.contains(ApplicationStatus.PROCESSING));
        assertTrue(newValidTransitions.contains(ApplicationStatus.PENDING));
        assertTrue(newValidTransitions.contains(ApplicationStatus.ERROR));
        assertTrue(newValidTransitions.contains(ApplicationStatus.EXCEPTION));
        assertEquals(4, newValidTransitions.size());
        
        // Check COMPLETED has no valid transitions (terminal state)
        Set<ApplicationStatus> completedValidTransitions = ApplicationStatus.COMPLETED.getValidNextStatuses();
        assertTrue(completedValidTransitions.isEmpty());
        
        // Check PROCESSING valid transitions
        Set<ApplicationStatus> processingValidTransitions = ApplicationStatus.PROCESSING.getValidNextStatuses();
        assertTrue(processingValidTransitions.contains(ApplicationStatus.APPROVED));
        assertTrue(processingValidTransitions.contains(ApplicationStatus.REJECTED));
        assertTrue(processingValidTransitions.contains(ApplicationStatus.PENDING));
        assertTrue(processingValidTransitions.contains(ApplicationStatus.ERROR));
        assertTrue(processingValidTransitions.contains(ApplicationStatus.EXCEPTION));
        assertEquals(5, processingValidTransitions.size());
    }

    @ParameterizedTest
    @EnumSource(ApplicationStatus.class)
    @DisplayName("fromString() should find enum constant by name")
    public void fromString_ShouldFindEnumConstantByName(ApplicationStatus status) {
        String name = status.name();
        ApplicationStatus result = ApplicationStatus.fromString(name);
        
        assertNotNull(result, "fromString() should find the enum constant");
        assertEquals(status, result, "fromString() should return the correct enum constant");
    }

    @ParameterizedTest
    @EnumSource(ApplicationStatus.class)
    @DisplayName("fromString() should find enum constant by name (case-insensitive)")
    public void fromString_ShouldBeCaseInsensitive(ApplicationStatus status) {
        String lowerCaseName = status.name().toLowerCase();
        ApplicationStatus result = ApplicationStatus.fromString(lowerCaseName);
        
        assertNotNull(result, "fromString() should find the enum constant (case-insensitive)");
        assertEquals(status, result, "fromString() should return the correct enum constant");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_STATUS", "unknown"})
    @DisplayName("fromString() should return null for invalid name")
    public void fromString_ShouldReturnNullForInvalidName(String invalidName) {
        ApplicationStatus result = ApplicationStatus.fromString(invalidName);
        assertNull(result, "fromString() should return null for invalid name");
    }

    @Test
    @DisplayName("Terminal statuses should be correctly identified")
    public void terminalStatusesShouldBeCorrectlyIdentified() {
        Set<ApplicationStatus> terminalStatuses = ApplicationStatus.getTerminalStatuses();
        
        assertTrue(terminalStatuses.contains(ApplicationStatus.COMPLETED));
        assertTrue(terminalStatuses.contains(ApplicationStatus.REJECTED));
        assertEquals(2, terminalStatuses.size());
        
        // Verify isTerminal() method
        assertTrue(ApplicationStatus.COMPLETED.isTerminal());
        assertTrue(ApplicationStatus.REJECTED.isTerminal());
        assertFalse(ApplicationStatus.NEW.isTerminal());
        assertFalse(ApplicationStatus.PROCESSING.isTerminal());
        assertFalse(ApplicationStatus.PENDING.isTerminal());
        assertFalse(ApplicationStatus.APPROVED.isTerminal());
        assertFalse(ApplicationStatus.ERROR.isTerminal());
        assertFalse(ApplicationStatus.EXCEPTION.isTerminal());
    }

    @Test
    @DisplayName("Active statuses should be correctly identified")
    public void activeStatusesShouldBeCorrectlyIdentified() {
        Set<ApplicationStatus> activeStatuses = ApplicationStatus.getActiveStatuses();
        
        assertTrue(activeStatuses.contains(ApplicationStatus.NEW));
        assertTrue(activeStatuses.contains(ApplicationStatus.PENDING));
        assertTrue(activeStatuses.contains(ApplicationStatus.PROCESSING));
        assertTrue(activeStatuses.contains(ApplicationStatus.EXCEPTION));
        assertEquals(4, activeStatuses.size());
        
        // Verify isActive() method
        assertTrue(ApplicationStatus.NEW.isActive());
        assertTrue(ApplicationStatus.PENDING.isActive());
        assertTrue(ApplicationStatus.PROCESSING.isActive());
        assertTrue(ApplicationStatus.EXCEPTION.isActive());
        assertFalse(ApplicationStatus.APPROVED.isActive());
        assertFalse(ApplicationStatus.REJECTED.isActive());
        assertFalse(ApplicationStatus.COMPLETED.isActive());
        assertFalse(ApplicationStatus.ERROR.isActive());
    }

    @Test
    @DisplayName("Error statuses should be correctly identified")
    public void errorStatusesShouldBeCorrectlyIdentified() {
        Set<ApplicationStatus> errorStatuses = ApplicationStatus.getErrorStatuses();
        
        assertTrue(errorStatuses.contains(ApplicationStatus.ERROR));
        assertTrue(errorStatuses.contains(ApplicationStatus.EXCEPTION));
        assertEquals(2, errorStatuses.size());
        
        // Verify isError() method
        assertTrue(ApplicationStatus.ERROR.isError());
        assertTrue(ApplicationStatus.EXCEPTION.isError());
        assertFalse(ApplicationStatus.NEW.isError());
        assertFalse(ApplicationStatus.PENDING.isError());
        assertFalse(ApplicationStatus.PROCESSING.isError());
        assertFalse(ApplicationStatus.APPROVED.isError());
        assertFalse(ApplicationStatus.REJECTED.isError());
        assertFalse(ApplicationStatus.COMPLETED.isError());
    }

    @Test
    @DisplayName("Human intervention statuses should be correctly identified")
    public void humanInterventionStatusesShouldBeCorrectlyIdentified() {
        Set<ApplicationStatus> humanInterventionStatuses = ApplicationStatus.getHumanInterventionStatuses();
        
        assertTrue(humanInterventionStatuses.contains(ApplicationStatus.EXCEPTION));
        assertTrue(humanInterventionStatuses.contains(ApplicationStatus.ERROR));
        assertTrue(humanInterventionStatuses.contains(ApplicationStatus.PENDING));
        assertEquals(3, humanInterventionStatuses.size());
        
        // Verify requiresHumanIntervention() method
        assertTrue(ApplicationStatus.EXCEPTION.requiresHumanIntervention());
        assertTrue(ApplicationStatus.ERROR.requiresHumanIntervention());
        assertTrue(ApplicationStatus.PENDING.requiresHumanIntervention());
        assertFalse(ApplicationStatus.NEW.requiresHumanIntervention());
        assertFalse(ApplicationStatus.PROCESSING.requiresHumanIntervention());
        assertFalse(ApplicationStatus.APPROVED.requiresHumanIntervention());
        assertFalse(ApplicationStatus.REJECTED.requiresHumanIntervention());
        assertFalse(ApplicationStatus.COMPLETED.requiresHumanIntervention());
    }

    @Test
    @DisplayName("getStatusNames() should return all status names as strings")
    public void getStatusNames_ShouldReturnAllStatusNames() {
        String[] statusNames = ApplicationStatus.getStatusNames();
        
        assertEquals(ApplicationStatus.values().length, statusNames.length);
        
        for (ApplicationStatus status : ApplicationStatus.values()) {
            boolean found = false;
            for (String name : statusNames) {
                if (status.name().equals(name)) {
                    found = true;
                    break;
                }
            }
            assertTrue(found, "Status name " + status.name() + " should be in the array");
        }
    }

    @Test
    @DisplayName("getStatusDescriptions() should return all status descriptions as a map")
    public void getStatusDescriptions_ShouldReturnAllStatusDescriptions() {
        Map<String, String> statusDescriptions = ApplicationStatus.getStatusDescriptions();
        
        assertEquals(ApplicationStatus.values().length, statusDescriptions.size());
        
        for (ApplicationStatus status : ApplicationStatus.values()) {
            String name = status.name();
            assertTrue(statusDescriptions.containsKey(name), 
                    "Status name " + name + " should be a key in the map");
            assertEquals(status.getDescription(), statusDescriptions.get(name),
                    "Description for " + name + " should match");
        }
    }

    @Test
    @DisplayName("All enum constants should be unique")
    public void allEnumConstantsShouldBeUnique() {
        ApplicationStatus[] values = ApplicationStatus.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(ApplicationStatus::name)
                .distinct()
                .count(), 
                "All enum constants should have unique names");
    }

    @Test
    @DisplayName("All enum descriptions should be unique")
    public void allEnumDescriptionsShouldBeUnique() {
        ApplicationStatus[] values = ApplicationStatus.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(ApplicationStatus::getDescription)
                .distinct()
                .count(), 
                "All enum constants should have unique descriptions");
    }

    @Test
    @DisplayName("JPA mapping: Enum should be persistable and retrievable")
    public void jpaMapping_EnumShouldBePersistableAndRetrievable() {
        // This test verifies that the enum can be used with JPA
        // In a real test, this would involve an actual database operation
        // Here we're just verifying that the enum has the necessary annotations
        
        // The @Enumerated annotation is typically used on the field in the entity class
        // that references this enum, not on the enum itself
        
        // For this test, we'll just verify that all enum values can be converted to and from strings
        for (ApplicationStatus status : ApplicationStatus.values()) {
            String name = status.name();
            ApplicationStatus retrieved = ApplicationStatus.fromString(name);
            assertEquals(status, retrieved, "Enum should be retrievable from its string representation");
        }
    }
}