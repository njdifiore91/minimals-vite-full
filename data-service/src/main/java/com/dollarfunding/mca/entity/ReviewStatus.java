package com.dollarfunding.mca.entity;

import java.util.Arrays;
import java.util.Optional;

/**
 * Enum representing the possible review status values for an MCA application.
 * This enum is used by the Application entity to represent the current review state of an application.
 * It provides type safety and validation for review status values throughout the application.
 */
public enum ReviewStatus {
    
    /**
     * Application has not been reviewed by operations staff yet.
     */
    NOT_REVIEWED("Not Reviewed", "Application has not been reviewed by operations staff yet."),
    
    /**
     * Application is currently being reviewed by operations staff.
     */
    IN_REVIEW("In Review", "Application is currently being reviewed by operations staff."),
    
    /**
     * Application requires additional information from the merchant before proceeding.
     */
    NEEDS_INFORMATION("Needs Information", "Application requires additional information from the merchant before proceeding."),
    
    /**
     * Application has been reviewed and approved by operations staff.
     */
    APPROVED("Approved", "Application has been reviewed and approved by operations staff."),
    
    /**
     * Application has been reviewed and rejected by operations staff.
     */
    REJECTED("Rejected", "Application has been reviewed and rejected by operations staff.");
    
    private final String displayName;
    private final String description;
    
    /**
     * Constructor for ReviewStatus enum.
     * 
     * @param displayName The human-readable display name for the status
     * @param description A detailed description of what the status means
     */
    ReviewStatus(String displayName, String description) {
        this.displayName = displayName;
        this.description = description;
    }
    
    /**
     * Get the display name of the review status.
     * 
     * @return The human-readable display name
     */
    public String getDisplayName() {
        return displayName;
    }
    
    /**
     * Get the description of the review status.
     * 
     * @return The detailed description
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Find a ReviewStatus by its display name.
     * 
     * @param displayName The display name to search for
     * @return An Optional containing the matching ReviewStatus, or empty if not found
     */
    public static Optional<ReviewStatus> findByDisplayName(String displayName) {
        return Arrays.stream(ReviewStatus.values())
                .filter(status -> status.getDisplayName().equalsIgnoreCase(displayName))
                .findFirst();
    }
    
    /**
     * Validates if a transition from the current status to the target status is allowed.
     * 
     * @param currentStatus The current review status
     * @param targetStatus The target review status to transition to
     * @return true if the transition is valid, false otherwise
     */
    public static boolean isValidTransition(ReviewStatus currentStatus, ReviewStatus targetStatus) {
        // If current status is the same as target status, it's always valid
        if (currentStatus == targetStatus) {
            return true;
        }
        
        // Define valid transitions based on business rules
        switch (currentStatus) {
            case NOT_REVIEWED:
                // From NOT_REVIEWED, can move to IN_REVIEW, APPROVED, or REJECTED
                return targetStatus == IN_REVIEW || targetStatus == APPROVED || targetStatus == REJECTED;
                
            case IN_REVIEW:
                // From IN_REVIEW, can move to NEEDS_INFORMATION, APPROVED, or REJECTED
                return targetStatus == NEEDS_INFORMATION || targetStatus == APPROVED || targetStatus == REJECTED;
                
            case NEEDS_INFORMATION:
                // From NEEDS_INFORMATION, can move back to IN_REVIEW, or to APPROVED or REJECTED
                return targetStatus == IN_REVIEW || targetStatus == APPROVED || targetStatus == REJECTED;
                
            case APPROVED:
                // From APPROVED, can only move to REJECTED (if an error was made)
                return targetStatus == REJECTED;
                
            case REJECTED:
                // From REJECTED, can only move to APPROVED (if an error was made)
                return targetStatus == APPROVED;
                
            default:
                return false;
        }
    }
    
    /**
     * Converts a string representation to a ReviewStatus enum value.
     * 
     * @param status The string representation of the status
     * @return The corresponding ReviewStatus enum value, or NOT_REVIEWED if not found
     */
    public static ReviewStatus fromString(String status) {
        try {
            return ReviewStatus.valueOf(status.toUpperCase());
        } catch (IllegalArgumentException | NullPointerException e) {
            // Default to NOT_REVIEWED if the string doesn't match any enum value
            return NOT_REVIEWED;
        }
    }
    
    /**
     * Checks if the review status is a terminal status (APPROVED or REJECTED).
     * 
     * @return true if the status is terminal, false otherwise
     */
    public boolean isTerminalStatus() {
        return this == APPROVED || this == REJECTED;
    }
    
    /**
     * Checks if the review status requires action from operations staff.
     * 
     * @return true if the status requires action, false otherwise
     */
    public boolean requiresAction() {
        return this == NOT_REVIEWED || this == NEEDS_INFORMATION;
    }
}