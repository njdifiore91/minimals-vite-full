package com.dollarfunding.mca.entity;

import java.util.Arrays;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Enum representing the possible status values for a Merchant Cash Advance (MCA) application.
 * This enum is used by the Application entity to represent the current state of an application
 * in its lifecycle.
 */
public enum ApplicationStatus {
    
    /**
     * Initial state for newly created applications.
     * Applications in this state have been received but not yet started processing.
     */
    NEW("New application received"),
    
    /**
     * Application is waiting for processing or additional information.
     * Applications in this state are waiting for additional documents or information
     * before processing can continue.
     */
    PENDING("Pending additional information"),
    
    /**
     * Application is currently being processed.
     * Applications in this state are actively being evaluated by the system or staff.
     */
    PROCESSING("Application is being processed"),
    
    /**
     * Application has been approved.
     * Applications in this state have met all criteria and been approved for funding.
     */
    APPROVED("Application approved for funding"),
    
    /**
     * Application has been rejected.
     * Applications in this state have been evaluated and determined not to meet criteria.
     */
    REJECTED("Application rejected"),
    
    /**
     * Application processing has been completed.
     * Applications in this state have completed the entire lifecycle (approved and funded,
     * or rejected and closed).
     */
    COMPLETED("Application processing completed");
    
    private final String description;
    
    /**
     * Static map for efficient lookup of enum values by description.
     */
    private static final Map<String, ApplicationStatus> BY_DESCRIPTION = 
            Arrays.stream(values())
                  .collect(Collectors.toMap(ApplicationStatus::getDescription, Function.identity()));
    
    /**
     * Constructor for ApplicationStatus enum.
     * 
     * @param description Human-readable description of the status
     */
    ApplicationStatus(String description) {
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
     * Find an ApplicationStatus by its description.
     * 
     * @param description The description to search for
     * @return Optional containing the matching ApplicationStatus, or empty if not found
     */
    public static Optional<ApplicationStatus> findByDescription(String description) {
        return Optional.ofNullable(BY_DESCRIPTION.get(description));
    }
    
    /**
     * Checks if a transition from the current status to the target status is valid.
     * Implements business rules for allowed status transitions.
     * 
     * @param targetStatus The status to transition to
     * @return true if the transition is valid, false otherwise
     */
    public boolean canTransitionTo(ApplicationStatus targetStatus) {
        if (targetStatus == null) {
            return false;
        }
        
        switch (this) {
            case NEW:
                // New applications can move to pending, processing, rejected
                return targetStatus == PENDING || targetStatus == PROCESSING || targetStatus == REJECTED;
                
            case PENDING:
                // Pending applications can move to processing, rejected
                return targetStatus == PROCESSING || targetStatus == REJECTED;
                
            case PROCESSING:
                // Processing applications can move to approved, rejected, pending (if more info needed)
                return targetStatus == APPROVED || targetStatus == REJECTED || targetStatus == PENDING;
                
            case APPROVED:
                // Approved applications can only move to completed
                return targetStatus == COMPLETED;
                
            case REJECTED:
                // Rejected applications can only move to completed
                return targetStatus == COMPLETED;
                
            case COMPLETED:
                // Completed applications cannot transition to any other status
                return false;
                
            default:
                return false;
        }
    }
    
    /**
     * Checks if this status is considered a terminal status.
     * Terminal statuses are those that represent the end of the application lifecycle.
     * 
     * @return true if this is a terminal status, false otherwise
     */
    public boolean isTerminalStatus() {
        return this == COMPLETED;
    }
    
    /**
     * Checks if this status is considered an active status.
     * Active statuses are those where the application is still being processed.
     * 
     * @return true if this is an active status, false otherwise
     */
    public boolean isActiveStatus() {
        return this == NEW || this == PENDING || this == PROCESSING;
    }
    
    /**
     * Checks if this status indicates the application has been decided upon.
     * Decided statuses are those where a final decision has been made.
     * 
     * @return true if this is a decided status, false otherwise
     */
    public boolean isDecidedStatus() {
        return this == APPROVED || this == REJECTED || this == COMPLETED;
    }
    
    /**
     * Returns a string representation of this status.
     * 
     * @return The name of the enum constant
     */
    @Override
    public String toString() {
        return name();
    }
}