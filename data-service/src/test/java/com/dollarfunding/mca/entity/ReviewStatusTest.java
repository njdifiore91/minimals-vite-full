package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.Set;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Unit tests for the {@link ReviewStatus} enum.
 * <p>
 * These tests verify the behavior of the ReviewStatus enum, including:
 * - Enum constants and their descriptions
 * - Status transition validation methods
 * - Conversion methods for string representations
 * - Terminal state identification
 * </p>
 */
public class ReviewStatusTest {

    @Test
    @DisplayName("Should have the expected number of enum constants")
    public void shouldHaveExpectedNumberOfConstants() {
        assertEquals(5, ReviewStatus.values().length, "ReviewStatus should have exactly 5 constants");
    }

    @ParameterizedTest
    @EnumSource(ReviewStatus.class)
    @DisplayName("Should have non-null description for each enum constant")
    public void shouldHaveNonNullDescription(ReviewStatus reviewStatus) {
        assertNotNull(reviewStatus.getDescription(), "Description should not be null");
        assertFalse(reviewStatus.getDescription().isEmpty(), "Description should not be empty");
    }

    @Test
    @DisplayName("Should have correct descriptions for each enum constant")
    public void shouldHaveCorrectDescriptions() {
        assertEquals("Application has not been reviewed", ReviewStatus.NOT_REVIEWED.getDescription());
        assertEquals("Application is currently under review", ReviewStatus.IN_REVIEW.getDescription());
        assertEquals("Additional information required from merchant", ReviewStatus.NEEDS_INFORMATION.getDescription());
        assertEquals("Application approved for funding", ReviewStatus.APPROVED.getDescription());
        assertEquals("Application rejected", ReviewStatus.REJECTED.getDescription());
    }

    @Test
    @DisplayName("NOT_REVIEWED should allow transitions to IN_REVIEW and REJECTED")
    public void notReviewed_ShouldAllowTransitionsToInReviewAndRejected() {
        ReviewStatus status = ReviewStatus.NOT_REVIEWED;
        
        // Valid transitions
        assertTrue(status.canTransitionTo(ReviewStatus.IN_REVIEW), 
                "NOT_REVIEWED should transition to IN_REVIEW");
        assertTrue(status.canTransitionTo(ReviewStatus.REJECTED), 
                "NOT_REVIEWED should transition to REJECTED");
        
        // Invalid transitions
        assertFalse(status.canTransitionTo(ReviewStatus.NEEDS_INFORMATION), 
                "NOT_REVIEWED should not transition to NEEDS_INFORMATION");
        assertFalse(status.canTransitionTo(ReviewStatus.APPROVED), 
                "NOT_REVIEWED should not transition to APPROVED");
        
        // Self-transition is allowed
        assertTrue(status.canTransitionTo(ReviewStatus.NOT_REVIEWED), 
                "Self-transition should be allowed");
    }

    @Test
    @DisplayName("IN_REVIEW should allow transitions to NEEDS_INFORMATION, APPROVED, and REJECTED")
    public void inReview_ShouldAllowTransitionsToNeedsInfoApprovedAndRejected() {
        ReviewStatus status = ReviewStatus.IN_REVIEW;
        
        // Valid transitions
        assertTrue(status.canTransitionTo(ReviewStatus.NEEDS_INFORMATION), 
                "IN_REVIEW should transition to NEEDS_INFORMATION");
        assertTrue(status.canTransitionTo(ReviewStatus.APPROVED), 
                "IN_REVIEW should transition to APPROVED");
        assertTrue(status.canTransitionTo(ReviewStatus.REJECTED), 
                "IN_REVIEW should transition to REJECTED");
        
        // Invalid transitions
        assertFalse(status.canTransitionTo(ReviewStatus.NOT_REVIEWED), 
                "IN_REVIEW should not transition to NOT_REVIEWED");
        
        // Self-transition is allowed
        assertTrue(status.canTransitionTo(ReviewStatus.IN_REVIEW), 
                "Self-transition should be allowed");
    }

    @Test
    @DisplayName("NEEDS_INFORMATION should allow transitions to IN_REVIEW, APPROVED, and REJECTED")
    public void needsInformation_ShouldAllowTransitionsToInReviewApprovedAndRejected() {
        ReviewStatus status = ReviewStatus.NEEDS_INFORMATION;
        
        // Valid transitions
        assertTrue(status.canTransitionTo(ReviewStatus.IN_REVIEW), 
                "NEEDS_INFORMATION should transition to IN_REVIEW");
        assertTrue(status.canTransitionTo(ReviewStatus.APPROVED), 
                "NEEDS_INFORMATION should transition to APPROVED");
        assertTrue(status.canTransitionTo(ReviewStatus.REJECTED), 
                "NEEDS_INFORMATION should transition to REJECTED");
        
        // Invalid transitions
        assertFalse(status.canTransitionTo(ReviewStatus.NOT_REVIEWED), 
                "NEEDS_INFORMATION should not transition to NOT_REVIEWED");
        
        // Self-transition is allowed
        assertTrue(status.canTransitionTo(ReviewStatus.NEEDS_INFORMATION), 
                "Self-transition should be allowed");
    }

    @Test
    @DisplayName("APPROVED should only allow transition to REJECTED")
    public void approved_ShouldOnlyAllowTransitionToRejected() {
        ReviewStatus status = ReviewStatus.APPROVED;
        
        // Valid transitions
        assertTrue(status.canTransitionTo(ReviewStatus.REJECTED), 
                "APPROVED should transition to REJECTED");
        
        // Invalid transitions
        assertFalse(status.canTransitionTo(ReviewStatus.NOT_REVIEWED), 
                "APPROVED should not transition to NOT_REVIEWED");
        assertFalse(status.canTransitionTo(ReviewStatus.IN_REVIEW), 
                "APPROVED should not transition to IN_REVIEW");
        assertFalse(status.canTransitionTo(ReviewStatus.NEEDS_INFORMATION), 
                "APPROVED should not transition to NEEDS_INFORMATION");
        
        // Self-transition is allowed
        assertTrue(status.canTransitionTo(ReviewStatus.APPROVED), 
                "Self-transition should be allowed");
    }

    @Test
    @DisplayName("REJECTED should not allow transitions to any other status")
    public void rejected_ShouldNotAllowTransitionsToAnyOtherStatus() {
        ReviewStatus status = ReviewStatus.REJECTED;
        
        // Invalid transitions
        assertFalse(status.canTransitionTo(ReviewStatus.NOT_REVIEWED), 
                "REJECTED should not transition to NOT_REVIEWED");
        assertFalse(status.canTransitionTo(ReviewStatus.IN_REVIEW), 
                "REJECTED should not transition to IN_REVIEW");
        assertFalse(status.canTransitionTo(ReviewStatus.NEEDS_INFORMATION), 
                "REJECTED should not transition to NEEDS_INFORMATION");
        assertFalse(status.canTransitionTo(ReviewStatus.APPROVED), 
                "REJECTED should not transition to APPROVED");
        
        // Self-transition is allowed
        assertTrue(status.canTransitionTo(ReviewStatus.REJECTED), 
                "Self-transition should be allowed");
    }

    @Test
    @DisplayName("canTransitionTo() should return false for null target status")
    public void canTransitionTo_ShouldReturnFalseForNullTargetStatus() {
        for (ReviewStatus status : ReviewStatus.values()) {
            assertFalse(status.canTransitionTo(null), 
                    "canTransitionTo() should return false for null target status");
        }
    }

    @ParameterizedTest
    @EnumSource(ReviewStatus.class)
    @DisplayName("getValidTransitions() should return non-null set")
    public void getValidTransitions_ShouldReturnNonNullSet(ReviewStatus status) {
        Set<ReviewStatus> validTransitions = status.getValidTransitions();
        assertNotNull(validTransitions, "getValidTransitions() should return non-null set");
    }

    @Test
    @DisplayName("getValidTransitions() should return correct transitions for each status")
    public void getValidTransitions_ShouldReturnCorrectTransitions() {
        // NOT_REVIEWED -> IN_REVIEW, REJECTED
        Set<ReviewStatus> notReviewedTransitions = ReviewStatus.NOT_REVIEWED.getValidTransitions();
        assertEquals(2, notReviewedTransitions.size(), "NOT_REVIEWED should have 2 valid transitions");
        assertTrue(notReviewedTransitions.contains(ReviewStatus.IN_REVIEW), 
                "NOT_REVIEWED should transition to IN_REVIEW");
        assertTrue(notReviewedTransitions.contains(ReviewStatus.REJECTED), 
                "NOT_REVIEWED should transition to REJECTED");
        
        // IN_REVIEW -> NEEDS_INFORMATION, APPROVED, REJECTED
        Set<ReviewStatus> inReviewTransitions = ReviewStatus.IN_REVIEW.getValidTransitions();
        assertEquals(3, inReviewTransitions.size(), "IN_REVIEW should have 3 valid transitions");
        assertTrue(inReviewTransitions.contains(ReviewStatus.NEEDS_INFORMATION), 
                "IN_REVIEW should transition to NEEDS_INFORMATION");
        assertTrue(inReviewTransitions.contains(ReviewStatus.APPROVED), 
                "IN_REVIEW should transition to APPROVED");
        assertTrue(inReviewTransitions.contains(ReviewStatus.REJECTED), 
                "IN_REVIEW should transition to REJECTED");
        
        // NEEDS_INFORMATION -> IN_REVIEW, APPROVED, REJECTED
        Set<ReviewStatus> needsInfoTransitions = ReviewStatus.NEEDS_INFORMATION.getValidTransitions();
        assertEquals(3, needsInfoTransitions.size(), "NEEDS_INFORMATION should have 3 valid transitions");
        assertTrue(needsInfoTransitions.contains(ReviewStatus.IN_REVIEW), 
                "NEEDS_INFORMATION should transition to IN_REVIEW");
        assertTrue(needsInfoTransitions.contains(ReviewStatus.APPROVED), 
                "NEEDS_INFORMATION should transition to APPROVED");
        assertTrue(needsInfoTransitions.contains(ReviewStatus.REJECTED), 
                "NEEDS_INFORMATION should transition to REJECTED");
        
        // APPROVED -> REJECTED
        Set<ReviewStatus> approvedTransitions = ReviewStatus.APPROVED.getValidTransitions();
        assertEquals(1, approvedTransitions.size(), "APPROVED should have 1 valid transition");
        assertTrue(approvedTransitions.contains(ReviewStatus.REJECTED), 
                "APPROVED should transition to REJECTED");
        
        // REJECTED -> (none)
        Set<ReviewStatus> rejectedTransitions = ReviewStatus.REJECTED.getValidTransitions();
        assertTrue(rejectedTransitions.isEmpty(), "REJECTED should have no valid transitions");
    }

    @Test
    @DisplayName("isTerminalState() should return true only for REJECTED")
    public void isTerminalState_ShouldReturnTrueOnlyForRejected() {
        assertTrue(ReviewStatus.REJECTED.isTerminalState(), 
                "REJECTED should be a terminal state");
        
        assertFalse(ReviewStatus.NOT_REVIEWED.isTerminalState(), 
                "NOT_REVIEWED should not be a terminal state");
        assertFalse(ReviewStatus.IN_REVIEW.isTerminalState(), 
                "IN_REVIEW should not be a terminal state");
        assertFalse(ReviewStatus.NEEDS_INFORMATION.isTerminalState(), 
                "NEEDS_INFORMATION should not be a terminal state");
        assertFalse(ReviewStatus.APPROVED.isTerminalState(), 
                "APPROVED should not be a terminal state");
    }

    @ParameterizedTest
    @EnumSource(ReviewStatus.class)
    @DisplayName("fromString() should find enum constant by name")
    public void fromString_ShouldFindEnumConstantByName(ReviewStatus reviewStatus) {
        String name = reviewStatus.name();
        assertEquals(reviewStatus, ReviewStatus.fromString(name), 
                "fromString() should return the correct enum constant");
    }

    @ParameterizedTest
    @EnumSource(ReviewStatus.class)
    @DisplayName("fromString() should find enum constant by name (case-insensitive)")
    public void fromString_ShouldBeCaseInsensitive(ReviewStatus reviewStatus) {
        String lowerCaseName = reviewStatus.name().toLowerCase();
        assertEquals(reviewStatus, ReviewStatus.fromString(lowerCaseName), 
                "fromString() should be case-insensitive");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_STATUS", "unknown", "pending"})
    @DisplayName("fromString() should return null for invalid name")
    public void fromString_ShouldReturnNullForInvalidName(String invalidName) {
        assertNull(ReviewStatus.fromString(invalidName), 
                "fromString() should return null for invalid name");
    }

    @Test
    @DisplayName("All enum constants should be unique")
    public void allEnumConstantsShouldBeUnique() {
        ReviewStatus[] values = ReviewStatus.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(ReviewStatus::name)
                .distinct()
                .count(), 
                "All enum constants should have unique names");
    }

    @Test
    @DisplayName("All enum descriptions should be unique")
    public void allEnumDescriptionsShouldBeUnique() {
        ReviewStatus[] values = ReviewStatus.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(ReviewStatus::getDescription)
                .distinct()
                .count(), 
                "All enum constants should have unique descriptions");
    }

    @Test
    @DisplayName("JPA mapping should work with ReviewStatus enum")
    public void jpaMappingShouldWorkWithReviewStatusEnum() {
        // This test simulates how JPA would store and retrieve the enum
        // In a real application, this would be tested with an actual database
        
        for (ReviewStatus status : ReviewStatus.values()) {
            // Simulate storing the enum as a string in the database
            String dbValue = status.name();
            
            // Simulate retrieving the enum from the database string
            ReviewStatus retrievedStatus = ReviewStatus.valueOf(dbValue);
            
            // Verify the retrieved enum matches the original
            assertEquals(status, retrievedStatus, 
                    "JPA mapping should preserve the enum value");
            assertEquals(status.getDescription(), retrievedStatus.getDescription(), 
                    "JPA mapping should preserve the description");
        }
    }
}