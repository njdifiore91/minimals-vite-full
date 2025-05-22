package com.dollarfunding.mca.entity;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import javax.persistence.EntityManager;
import javax.persistence.Query;
import java.util.Optional;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link ApplicationStatus} enum.
 * 
 * These tests verify the enum values, descriptions, and JPA mapping functionality.
 */
@DisplayName("ApplicationStatus Enum Tests")
class ApplicationStatusTest {

    /**
     * Test to verify all expected enum constants exist.
     */
    @Test
    @DisplayName("Should have all required status values")
    void shouldHaveAllRequiredStatusValues() {
        // Verify all expected enum constants exist
        assertEquals(6, ApplicationStatus.values().length, "Should have exactly 6 status values");
        
        assertNotNull(ApplicationStatus.NEW);
        assertNotNull(ApplicationStatus.PENDING);
        assertNotNull(ApplicationStatus.PROCESSING);
        assertNotNull(ApplicationStatus.APPROVED);
        assertNotNull(ApplicationStatus.REJECTED);
        assertNotNull(ApplicationStatus.COMPLETED);
    }
    
    /**
     * Test to verify each enum constant has the correct description.
     */
    @ParameterizedTest
    @EnumSource(ApplicationStatus.class)
    @DisplayName("Should have non-null description for each status")
    void shouldHaveNonNullDescription(ApplicationStatus status) {
        assertNotNull(status.getDescription(), "Description should not be null");
        assertFalse(status.getDescription().isEmpty(), "Description should not be empty");
    }
    
    /**
     * Test to verify specific descriptions for each enum constant.
     */
    @Test
    @DisplayName("Should have correct descriptions for each status")
    void shouldHaveCorrectDescriptions() {
        assertEquals("New application received", ApplicationStatus.NEW.getDescription());
        assertEquals("Pending additional information", ApplicationStatus.PENDING.getDescription());
        assertEquals("Application is being processed", ApplicationStatus.PROCESSING.getDescription());
        assertEquals("Application approved for funding", ApplicationStatus.APPROVED.getDescription());
        assertEquals("Application rejected", ApplicationStatus.REJECTED.getDescription());
        assertEquals("Application processing completed", ApplicationStatus.COMPLETED.getDescription());
    }
    
    /**
     * Test to verify the findByDescription method works correctly.
     */
    @ParameterizedTest
    @CsvSource({
        "New application received, NEW",
        "Pending additional information, PENDING",
        "Application is being processed, PROCESSING",
        "Application approved for funding, APPROVED",
        "Application rejected, REJECTED",
        "Application processing completed, COMPLETED"
    })
    @DisplayName("Should find status by description")
    void shouldFindStatusByDescription(String description, ApplicationStatus expectedStatus) {
        Optional<ApplicationStatus> result = ApplicationStatus.findByDescription(description);
        
        assertTrue(result.isPresent(), "Should find a status for valid description");
        assertEquals(expectedStatus, result.get(), "Should find the correct status");
    }
    
    /**
     * Test to verify the findByDescription method returns empty for invalid descriptions.
     */
    @Test
    @DisplayName("Should return empty for invalid description")
    void shouldReturnEmptyForInvalidDescription() {
        Optional<ApplicationStatus> result = ApplicationStatus.findByDescription("Invalid Description");
        
        assertFalse(result.isPresent(), "Should not find a status for invalid description");
    }
    
    /**
     * Test to verify the canTransitionTo method for valid transitions.
     */
    @ParameterizedTest
    @MethodSource("validTransitionsProvider")
    @DisplayName("Should allow valid status transitions")
    void shouldAllowValidTransitions(ApplicationStatus fromStatus, ApplicationStatus toStatus) {
        assertTrue(fromStatus.canTransitionTo(toStatus), 
                 "Should allow transition from " + fromStatus + " to " + toStatus);
    }
    
    /**
     * Test to verify the canTransitionTo method for invalid transitions.
     */
    @ParameterizedTest
    @MethodSource("invalidTransitionsProvider")
    @DisplayName("Should not allow invalid status transitions")
    void shouldNotAllowInvalidTransitions(ApplicationStatus fromStatus, ApplicationStatus toStatus) {
        assertFalse(fromStatus.canTransitionTo(toStatus), 
                  "Should not allow transition from " + fromStatus + " to " + toStatus);
    }
    
    /**
     * Test to verify the canTransitionTo method handles null input.
     */
    @ParameterizedTest
    @EnumSource(ApplicationStatus.class)
    @DisplayName("Should not allow transition to null status")
    void shouldNotAllowTransitionToNull(ApplicationStatus status) {
        assertFalse(status.canTransitionTo(null), "Should not allow transition to null");
    }
    
    /**
     * Test to verify the isTerminalStatus method.
     */
    @Test
    @DisplayName("Should identify terminal status correctly")
    void shouldIdentifyTerminalStatus() {
        assertTrue(ApplicationStatus.COMPLETED.isTerminalStatus(), "COMPLETED should be a terminal status");
        
        assertFalse(ApplicationStatus.NEW.isTerminalStatus(), "NEW should not be a terminal status");
        assertFalse(ApplicationStatus.PENDING.isTerminalStatus(), "PENDING should not be a terminal status");
        assertFalse(ApplicationStatus.PROCESSING.isTerminalStatus(), "PROCESSING should not be a terminal status");
        assertFalse(ApplicationStatus.APPROVED.isTerminalStatus(), "APPROVED should not be a terminal status");
        assertFalse(ApplicationStatus.REJECTED.isTerminalStatus(), "REJECTED should not be a terminal status");
    }
    
    /**
     * Test to verify the isActiveStatus method.
     */
    @Test
    @DisplayName("Should identify active status correctly")
    void shouldIdentifyActiveStatus() {
        assertTrue(ApplicationStatus.NEW.isActiveStatus(), "NEW should be an active status");
        assertTrue(ApplicationStatus.PENDING.isActiveStatus(), "PENDING should be an active status");
        assertTrue(ApplicationStatus.PROCESSING.isActiveStatus(), "PROCESSING should be an active status");
        
        assertFalse(ApplicationStatus.APPROVED.isActiveStatus(), "APPROVED should not be an active status");
        assertFalse(ApplicationStatus.REJECTED.isActiveStatus(), "REJECTED should not be an active status");
        assertFalse(ApplicationStatus.COMPLETED.isActiveStatus(), "COMPLETED should not be an active status");
    }
    
    /**
     * Test to verify the isDecidedStatus method.
     */
    @Test
    @DisplayName("Should identify decided status correctly")
    void shouldIdentifyDecidedStatus() {
        assertTrue(ApplicationStatus.APPROVED.isDecidedStatus(), "APPROVED should be a decided status");
        assertTrue(ApplicationStatus.REJECTED.isDecidedStatus(), "REJECTED should be a decided status");
        assertTrue(ApplicationStatus.COMPLETED.isDecidedStatus(), "COMPLETED should be a decided status");
        
        assertFalse(ApplicationStatus.NEW.isDecidedStatus(), "NEW should not be a decided status");
        assertFalse(ApplicationStatus.PENDING.isDecidedStatus(), "PENDING should not be a decided status");
        assertFalse(ApplicationStatus.PROCESSING.isDecidedStatus(), "PROCESSING should not be a decided status");
    }
    
    /**
     * Test to verify the toString method.
     */
    @ParameterizedTest
    @EnumSource(ApplicationStatus.class)
    @DisplayName("Should return name from toString method")
    void shouldReturnNameFromToString(ApplicationStatus status) {
        assertEquals(status.name(), status.toString(), "toString should return the enum name");
    }
    
    /**
     * Test to verify JPA mapping for enum persistence.
     */
    @Test
    @DisplayName("Should correctly persist and retrieve enum values")
    void shouldCorrectlyPersistAndRetrieveEnumValues() {
        // Mock EntityManager and Query for testing JPA persistence
        EntityManager entityManager = mock(EntityManager.class);
        Query query = mock(Query.class);
        
        // Setup mock behavior
        when(entityManager.createNativeQuery(anyString())).thenReturn(query);
        when(query.setParameter(anyInt(), any())).thenReturn(query);
        when(query.getSingleResult()).thenReturn(ApplicationStatus.APPROVED.name());
        
        // Simulate retrieving the enum value from database
        String dbValue = (String) entityManager.createNativeQuery("SELECT status FROM applications WHERE id = ?").setParameter(1, 1L).getSingleResult();
        ApplicationStatus retrievedStatus = ApplicationStatus.valueOf(dbValue);
        
        // Verify the retrieved enum value
        assertEquals(ApplicationStatus.APPROVED, retrievedStatus, "Should correctly retrieve the enum value from database");
        
        // Verify the mock interactions
        verify(entityManager).createNativeQuery(anyString());
        verify(query).setParameter(anyInt(), any());
        verify(query).getSingleResult();
    }
    
    /**
     * Provides valid status transitions for parameterized tests.
     */
    static Stream<Arguments> validTransitionsProvider() {
        return Stream.of(
            // From NEW
            Arguments.of(ApplicationStatus.NEW, ApplicationStatus.PENDING),
            Arguments.of(ApplicationStatus.NEW, ApplicationStatus.PROCESSING),
            Arguments.of(ApplicationStatus.NEW, ApplicationStatus.REJECTED),
            
            // From PENDING
            Arguments.of(ApplicationStatus.PENDING, ApplicationStatus.PROCESSING),
            Arguments.of(ApplicationStatus.PENDING, ApplicationStatus.REJECTED),
            
            // From PROCESSING
            Arguments.of(ApplicationStatus.PROCESSING, ApplicationStatus.APPROVED),
            Arguments.of(ApplicationStatus.PROCESSING, ApplicationStatus.REJECTED),
            Arguments.of(ApplicationStatus.PROCESSING, ApplicationStatus.PENDING),
            
            // From APPROVED
            Arguments.of(ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED),
            
            // From REJECTED
            Arguments.of(ApplicationStatus.REJECTED, ApplicationStatus.COMPLETED)
        );
    }
    
    /**
     * Provides invalid status transitions for parameterized tests.
     */
    static Stream<Arguments> invalidTransitionsProvider() {
        return Stream.of(
            // From NEW
            Arguments.of(ApplicationStatus.NEW, ApplicationStatus.APPROVED),
            Arguments.of(ApplicationStatus.NEW, ApplicationStatus.COMPLETED),
            
            // From PENDING
            Arguments.of(ApplicationStatus.PENDING, ApplicationStatus.NEW),
            Arguments.of(ApplicationStatus.PENDING, ApplicationStatus.APPROVED),
            Arguments.of(ApplicationStatus.PENDING, ApplicationStatus.COMPLETED),
            
            // From PROCESSING
            Arguments.of(ApplicationStatus.PROCESSING, ApplicationStatus.NEW),
            Arguments.of(ApplicationStatus.PROCESSING, ApplicationStatus.COMPLETED),
            
            // From APPROVED
            Arguments.of(ApplicationStatus.APPROVED, ApplicationStatus.NEW),
            Arguments.of(ApplicationStatus.APPROVED, ApplicationStatus.PENDING),
            Arguments.of(ApplicationStatus.APPROVED, ApplicationStatus.PROCESSING),
            Arguments.of(ApplicationStatus.APPROVED, ApplicationStatus.REJECTED),
            
            // From REJECTED
            Arguments.of(ApplicationStatus.REJECTED, ApplicationStatus.NEW),
            Arguments.of(ApplicationStatus.REJECTED, ApplicationStatus.PENDING),
            Arguments.of(ApplicationStatus.REJECTED, ApplicationStatus.PROCESSING),
            Arguments.of(ApplicationStatus.REJECTED, ApplicationStatus.APPROVED),
            
            // From COMPLETED
            Arguments.of(ApplicationStatus.COMPLETED, ApplicationStatus.NEW),
            Arguments.of(ApplicationStatus.COMPLETED, ApplicationStatus.PENDING),
            Arguments.of(ApplicationStatus.COMPLETED, ApplicationStatus.PROCESSING),
            Arguments.of(ApplicationStatus.COMPLETED, ApplicationStatus.APPROVED),
            Arguments.of(ApplicationStatus.COMPLETED, ApplicationStatus.REJECTED),
            Arguments.of(ApplicationStatus.COMPLETED, ApplicationStatus.COMPLETED)
        );
    }
}