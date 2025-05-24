package com.dollarfunding.mca.entity;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Enum representing the possible review statuses for a Merchant Cash Advance application.
 * This enum is used by the Application entity to track the current review state.
 */
public enum ReviewStatus {
    
    /**
     * Application has not been reviewed yet. This is the initial state for new applications.
     */
    NOT_REVIEWED("Application has not been reviewed"),
    
    /**
     * Application is currently being reviewed by operations staff.
     */
    IN_REVIEW("Application is currently under review"),
    
    /**
     * Application requires additional information from the merchant.
     */
    NEEDS_INFORMATION("Additional information required from merchant"),
    
    /**
     * Application has been approved for funding.
     */
    APPROVED("Application approved for funding"),
    
    /**
     * Application has been rejected and will not be funded.
     */
    REJECTED("Application rejected");
    
    private final String description;
    
    // Define valid status transitions
    private static final Map<ReviewStatus, Set<ReviewStatus>> VALID_TRANSITIONS;
    
    static {
        Map<ReviewStatus, Set<ReviewStatus>> transitions = new HashMap<>();
        
        // From NOT_REVIEWED, can transition to IN_REVIEW or REJECTED
        transitions.put(NOT_REVIEWED, new HashSet<>(Arrays.asList(IN_REVIEW, REJECTED)));
        
        // From IN_REVIEW, can transition to NEEDS_INFORMATION, APPROVED, or REJECTED
        transitions.put(IN_REVIEW, new HashSet<>(Arrays.asList(NEEDS_INFORMATION, APPROVED, REJECTED)));
        
        // From NEEDS_INFORMATION, can transition to IN_REVIEW, APPROVED, or REJECTED
        transitions.put(NEEDS_INFORMATION, new HashSet<>(Arrays.asList(IN_REVIEW, APPROVED, REJECTED)));
        
        // From APPROVED, can only transition to REJECTED (e.g., if fraud is detected later)
        transitions.put(APPROVED, new HashSet<>(Collections.singletonList(REJECTED)));
        
        // From REJECTED, no valid transitions (terminal state)
        transitions.put(REJECTED, new HashSet<>());
        
        VALID_TRANSITIONS = Collections.unmodifiableMap(transitions);
    }
    
    /**
     * Constructor for ReviewStatus enum.
     * 
     * @param description A human-readable description of the status
     */
    ReviewStatus(String description) {
        this.description = description;
    }
    
    /**
     * Get the human-readable description of this status.
     * 
     * @return The description string
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Check if a transition from the current status to the target status is valid.
     * 
     * @param targetStatus The status to transition to
     * @return true if the transition is valid, false otherwise
     */
    public boolean canTransitionTo(ReviewStatus targetStatus) {
        if (targetStatus == null) {
            return false;
        }
        
        // Allow transition to the same status (no change)
        if (this == targetStatus) {
            return true;
        }
        
        // Check if the transition is in the valid transitions map
        Set<ReviewStatus> validTargets = VALID_TRANSITIONS.get(this);
        return validTargets != null && validTargets.contains(targetStatus);
    }
    
    /**
     * Get all valid status transitions from the current status.
     * 
     * @return A set of valid target statuses
     */
    public Set<ReviewStatus> getValidTransitions() {
        Set<ReviewStatus> validTargets = VALID_TRANSITIONS.get(this);
        return validTargets != null ? Collections.unmodifiableSet(validTargets) : Collections.emptySet();
    }
    
    /**
     * Check if this status is a terminal state (no further transitions possible).
     * 
     * @return true if this is a terminal state, false otherwise
     */
    public boolean isTerminalState() {
        Set<ReviewStatus> validTargets = VALID_TRANSITIONS.get(this);
        return validTargets == null || validTargets.isEmpty();
    }
    
    /**
     * Parse a string representation of a review status.
     * 
     * @param status The string representation of the status
     * @return The corresponding ReviewStatus enum value, or null if not found
     */
    public static ReviewStatus fromString(String status) {
        if (status == null || status.trim().isEmpty()) {
            return null;
        }
        
        try {
            return ReviewStatus.valueOf(status.trim().toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}