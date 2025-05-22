package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.Optional;

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
 * - Methods for finding review status by display name
 * - Status transition validation
 * - Terminal status and action required checks
 * - Conversion methods for serialization and deserialization
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
    @DisplayName("Should have non-null display name for each enum constant")
    public void shouldHaveNonNullDisplayName(ReviewStatus reviewStatus) {
        assertNotNull(reviewStatus.getDisplayName(), "Display name should not be null");
        assertFalse(reviewStatus.getDisplayName().isEmpty(), "Display name should not be empty");
    }

    @ParameterizedTest
    @EnumSource(ReviewStatus.class)
    @DisplayName("Should have non-null description for each enum constant")
    public void shouldHaveNonNullDescription(ReviewStatus reviewStatus) {
        assertNotNull(reviewStatus.getDescription(), "Description should not be null");
        assertFalse(reviewStatus.getDescription().isEmpty(), "Description should not be empty");
    }

    @Test
    @DisplayName("Should have correct display names for each enum constant")
    public void shouldHaveCorrectDisplayNames() {
        assertEquals("Not Reviewed", ReviewStatus.NOT_REVIEWED.getDisplayName());
        assertEquals("In Review", ReviewStatus.IN_REVIEW.getDisplayName());
        assertEquals("Needs Information", ReviewStatus.NEEDS_INFORMATION.getDisplayName());
        assertEquals("Approved", ReviewStatus.APPROVED.getDisplayName());
        assertEquals("Rejected", ReviewStatus.REJECTED.getDisplayName());
    }

    @Test
    @DisplayName("Should have correct descriptions for each enum constant")
    public void shouldHaveCorrectDescriptions() {
        assertEquals("Application has not been reviewed by operations staff yet.", 
                ReviewStatus.NOT_REVIEWED.getDescription());
        assertEquals("Application is currently being reviewed by operations staff.", 
                ReviewStatus.IN_REVIEW.getDescription());
        assertEquals("Application requires additional information from the merchant before proceeding.", 
                ReviewStatus.NEEDS_INFORMATION.getDescription());
        assertEquals("Application has been reviewed and approved by operations staff.", 
                ReviewStatus.APPROVED.getDescription());
        assertEquals("Application has been reviewed and rejected by operations staff.", 
                ReviewStatus.REJECTED.getDescription());
    }

    @ParameterizedTest
    @EnumSource(ReviewStatus.class)
    @DisplayName("findByDisplayName() should find enum constant by display name")
    public void findByDisplayName_ShouldFindEnumConstantByDisplayName(ReviewStatus reviewStatus) {
        String displayName = reviewStatus.getDisplayName();
        Optional<ReviewStatus> result = ReviewStatus.findByDisplayName(displayName);
        
        assertTrue(result.isPresent(), "findByDisplayName() should find the enum constant");
        assertEquals(reviewStatus, result.get(), "findByDisplayName() should return the correct enum constant");
    }

    @ParameterizedTest
    @EnumSource(ReviewStatus.class)
    @DisplayName("findByDisplayName() should find enum constant by display name (case-insensitive)")
    public void findByDisplayName_ShouldBeCaseInsensitive(ReviewStatus reviewStatus) {
        String lowerCaseDisplayName = reviewStatus.getDisplayName().toLowerCase();
        Optional<ReviewStatus> result = ReviewStatus.findByDisplayName(lowerCaseDisplayName);
        
        assertTrue(result.isPresent(), "findByDisplayName() should find the enum constant (case-insensitive)");
        assertEquals(reviewStatus, result.get(), "findByDisplayName() should return the correct enum constant");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"Invalid Status", "Unknown"})
    @DisplayName("findByDisplayName() should return empty Optional for invalid display name")
    public void findByDisplayName_ShouldReturnEmptyOptionalForInvalidDisplayName(String invalidDisplayName) {
        Optional<ReviewStatus> result = ReviewStatus.findByDisplayName(invalidDisplayName);
        assertFalse(result.isPresent(), "findByDisplayName() should return an empty Optional for invalid display name");
    }

    @Test
    @DisplayName("isValidTransition() should validate transitions from NOT_REVIEWED status")
    public void isValidTransition_FromNotReviewed() {
        ReviewStatus currentStatus = ReviewStatus.NOT_REVIEWED;
        
        // Valid transitions
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.IN_REVIEW), 
                "Should allow transition from NOT_REVIEWED to IN_REVIEW");
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.APPROVED), 
                "Should allow transition from NOT_REVIEWED to APPROVED");
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.REJECTED), 
                "Should allow transition from NOT_REVIEWED to REJECTED");
        
        // Invalid transitions
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NEEDS_INFORMATION), 
                "Should not allow transition from NOT_REVIEWED to NEEDS_INFORMATION");
        
        // Same status is always valid
        assertTrue(ReviewStatus.isValidTransition(currentStatus, currentStatus), 
                "Should allow transition to the same status");
    }

    @Test
    @DisplayName("isValidTransition() should validate transitions from IN_REVIEW status")
    public void isValidTransition_FromInReview() {
        ReviewStatus currentStatus = ReviewStatus.IN_REVIEW;
        
        // Valid transitions
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NEEDS_INFORMATION), 
                "Should allow transition from IN_REVIEW to NEEDS_INFORMATION");
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.APPROVED), 
                "Should allow transition from IN_REVIEW to APPROVED");
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.REJECTED), 
                "Should allow transition from IN_REVIEW to REJECTED");
        
        // Invalid transitions
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NOT_REVIEWED), 
                "Should not allow transition from IN_REVIEW to NOT_REVIEWED");
        
        // Same status is always valid
        assertTrue(ReviewStatus.isValidTransition(currentStatus, currentStatus), 
                "Should allow transition to the same status");
    }

    @Test
    @DisplayName("isValidTransition() should validate transitions from NEEDS_INFORMATION status")
    public void isValidTransition_FromNeedsInformation() {
        ReviewStatus currentStatus = ReviewStatus.NEEDS_INFORMATION;
        
        // Valid transitions
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.IN_REVIEW), 
                "Should allow transition from NEEDS_INFORMATION to IN_REVIEW");
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.APPROVED), 
                "Should allow transition from NEEDS_INFORMATION to APPROVED");
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.REJECTED), 
                "Should allow transition from NEEDS_INFORMATION to REJECTED");
        
        // Invalid transitions
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NOT_REVIEWED), 
                "Should not allow transition from NEEDS_INFORMATION to NOT_REVIEWED");
        
        // Same status is always valid
        assertTrue(ReviewStatus.isValidTransition(currentStatus, currentStatus), 
                "Should allow transition to the same status");
    }

    @Test
    @DisplayName("isValidTransition() should validate transitions from APPROVED status")
    public void isValidTransition_FromApproved() {
        ReviewStatus currentStatus = ReviewStatus.APPROVED;
        
        // Valid transitions
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.REJECTED), 
                "Should allow transition from APPROVED to REJECTED (error correction)");
        
        // Invalid transitions
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NOT_REVIEWED), 
                "Should not allow transition from APPROVED to NOT_REVIEWED");
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.IN_REVIEW), 
                "Should not allow transition from APPROVED to IN_REVIEW");
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NEEDS_INFORMATION), 
                "Should not allow transition from APPROVED to NEEDS_INFORMATION");
        
        // Same status is always valid
        assertTrue(ReviewStatus.isValidTransition(currentStatus, currentStatus), 
                "Should allow transition to the same status");
    }

    @Test
    @DisplayName("isValidTransition() should validate transitions from REJECTED status")
    public void isValidTransition_FromRejected() {
        ReviewStatus currentStatus = ReviewStatus.REJECTED;
        
        // Valid transitions
        assertTrue(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.APPROVED), 
                "Should allow transition from REJECTED to APPROVED (error correction)");
        
        // Invalid transitions
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NOT_REVIEWED), 
                "Should not allow transition from REJECTED to NOT_REVIEWED");
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.IN_REVIEW), 
                "Should not allow transition from REJECTED to IN_REVIEW");
        assertFalse(ReviewStatus.isValidTransition(currentStatus, ReviewStatus.NEEDS_INFORMATION), 
                "Should not allow transition from REJECTED to NEEDS_INFORMATION");
        
        // Same status is always valid
        assertTrue(ReviewStatus.isValidTransition(currentStatus, currentStatus), 
                "Should allow transition to the same status");
    }

    @Test
    @DisplayName("fromString() should correctly convert string to enum constant")
    public void fromString_ShouldConvertStringToEnumConstant() {
        // Test with enum names
        assertEquals(ReviewStatus.NOT_REVIEWED, ReviewStatus.fromString("NOT_REVIEWED"));
        assertEquals(ReviewStatus.IN_REVIEW, ReviewStatus.fromString("IN_REVIEW"));
        assertEquals(ReviewStatus.NEEDS_INFORMATION, ReviewStatus.fromString("NEEDS_INFORMATION"));
        assertEquals(ReviewStatus.APPROVED, ReviewStatus.fromString("APPROVED"));
        assertEquals(ReviewStatus.REJECTED, ReviewStatus.fromString("REJECTED"));
        
        // Test with lowercase enum names
        assertEquals(ReviewStatus.NOT_REVIEWED, ReviewStatus.fromString("not_reviewed"));
        assertEquals(ReviewStatus.IN_REVIEW, ReviewStatus.fromString("in_review"));
        assertEquals(ReviewStatus.NEEDS_INFORMATION, ReviewStatus.fromString("needs_information"));
        assertEquals(ReviewStatus.APPROVED, ReviewStatus.fromString("approved"));
        assertEquals(ReviewStatus.REJECTED, ReviewStatus.fromString("rejected"));
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_STATUS", "Unknown"})
    @DisplayName("fromString() should return NOT_REVIEWED for invalid string")
    public void fromString_ShouldReturnNotReviewedForInvalidString(String invalidString) {
        assertEquals(ReviewStatus.NOT_REVIEWED, ReviewStatus.fromString(invalidString), 
                "fromString() should return NOT_REVIEWED for invalid string");
    }

    @Test
    @DisplayName("isTerminalStatus() should correctly identify terminal statuses")
    public void isTerminalStatus_ShouldIdentifyTerminalStatuses() {
        assertFalse(ReviewStatus.NOT_REVIEWED.isTerminalStatus(), "NOT_REVIEWED should not be a terminal status");
        assertFalse(ReviewStatus.IN_REVIEW.isTerminalStatus(), "IN_REVIEW should not be a terminal status");
        assertFalse(ReviewStatus.NEEDS_INFORMATION.isTerminalStatus(), "NEEDS_INFORMATION should not be a terminal status");
        
        assertTrue(ReviewStatus.APPROVED.isTerminalStatus(), "APPROVED should be a terminal status");
        assertTrue(ReviewStatus.REJECTED.isTerminalStatus(), "REJECTED should be a terminal status");
    }

    @Test
    @DisplayName("requiresAction() should correctly identify statuses requiring action")
    public void requiresAction_ShouldIdentifyStatusesRequiringAction() {
        assertTrue(ReviewStatus.NOT_REVIEWED.requiresAction(), "NOT_REVIEWED should require action");
        assertFalse(ReviewStatus.IN_REVIEW.requiresAction(), "IN_REVIEW should not require action");
        assertTrue(ReviewStatus.NEEDS_INFORMATION.requiresAction(), "NEEDS_INFORMATION should require action");
        assertFalse(ReviewStatus.APPROVED.requiresAction(), "APPROVED should not require action");
        assertFalse(ReviewStatus.REJECTED.requiresAction(), "REJECTED should not require action");
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
    @DisplayName("All enum display names should be unique")
    public void allEnumDisplayNamesShouldBeUnique() {
        ReviewStatus[] values = ReviewStatus.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(ReviewStatus::getDisplayName)
                .distinct()
                .count(), 
                "All enum constants should have unique display names");
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
}