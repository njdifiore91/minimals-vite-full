package com.dollarfunding.mca.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Enumerated;
import jakarta.persistence.EnumType;

import java.util.Arrays;
import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Enum representing the possible status values for a Merchant Cash Advance (MCA) application.
 * This enum is used by the Application entity to represent the current state of an application
 * in its lifecycle.
 */
public enum ApplicationStatus {
    
    /**
     * Initial status when an application is first created or received via email.
     * This status indicates that the application has been received but processing has not yet begun.
     */
    NEW("Application has been received but not yet processed"),
    
    /**
     * Application is waiting for additional documents or information.
     * This status indicates that the application cannot proceed until additional information is provided.
     */
    PENDING("Application is waiting for additional documents or information"),
    
    /**
     * Application is currently being processed.
     * This status indicates that the application is actively being reviewed and processed.
     */
    PROCESSING("Application is currently being processed"),
    
    /**
     * Application has been approved.
     * This status indicates that the application has met all requirements and has been approved.
     */
    APPROVED("Application has been approved"),
    
    /**
     * Application has been rejected.
     * This status indicates that the application has been reviewed and does not meet the requirements.
     */
    REJECTED("Application has been rejected"),
    
    /**
     * Application processing has been completed.
     * This status indicates that all processing steps have been completed for this application.
     */
    COMPLETED("Application processing has been completed"),
    
    /**
     * An error occurred during processing.
     * This status indicates that there was a system error during the processing of the application.
     */
    ERROR("An error occurred during application processing"),
    
    /**
     * Application has validation or rule violations.
     * This status indicates that the application has been flagged for review due to rule violations.
     */
    EXCEPTION("Application has been flagged for review due to rule violations");
    
    private final String description;
    
    /**
     * Constructor for ApplicationStatus enum.
     * 
     * @param description A human-readable description of the status
     */
    ApplicationStatus(String description) {
        this.description = description;
    }
    
    /**
     * Get the description of the status.
     * 
     * @return The human-readable description of the status
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Define valid status transitions.
     * This map defines which status values can transition to which other status values.
     */
    private static final Map<ApplicationStatus, Set<ApplicationStatus>> VALID_TRANSITIONS = Map.of(
        NEW, Set.of(PROCESSING, PENDING, ERROR, EXCEPTION),
        PENDING, Set.of(PROCESSING, ERROR, EXCEPTION),
        PROCESSING, Set.of(APPROVED, REJECTED, PENDING, ERROR, EXCEPTION),
        APPROVED, Set.of(COMPLETED, ERROR),
        REJECTED, Set.of(COMPLETED, ERROR),
        EXCEPTION, Set.of(PROCESSING, PENDING, ERROR),
        ERROR, Set.of(PROCESSING, PENDING, EXCEPTION),
        COMPLETED, Collections.emptySet() // Terminal state, no further transitions
    );
    
    /**
     * Check if a transition from the current status to the target status is valid.
     * 
     * @param targetStatus The status to transition to
     * @return true if the transition is valid, false otherwise
     */
    public boolean canTransitionTo(ApplicationStatus targetStatus) {
        return VALID_TRANSITIONS.getOrDefault(this, Collections.emptySet()).contains(targetStatus);
    }
    
    /**
     * Get all possible next statuses that this status can transition to.
     * 
     * @return A set of valid next statuses
     */
    public Set<ApplicationStatus> getValidNextStatuses() {
        return Collections.unmodifiableSet(VALID_TRANSITIONS.getOrDefault(this, Collections.emptySet()));
    }
    
    /**
     * Convert a string to an ApplicationStatus enum value.
     * 
     * @param status The string representation of the status
     * @return The corresponding ApplicationStatus enum value, or null if not found
     */
    public static ApplicationStatus fromString(String status) {
        if (status == null) {
            return null;
        }
        
        try {
            return ApplicationStatus.valueOf(status.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
    
    /**
     * Get all terminal statuses (statuses that represent the end of the application lifecycle).
     * 
     * @return A set of terminal statuses
     */
    public static Set<ApplicationStatus> getTerminalStatuses() {
        return Set.of(COMPLETED, REJECTED);
    }
    
    /**
     * Check if this status is a terminal status.
     * 
     * @return true if this is a terminal status, false otherwise
     */
    public boolean isTerminal() {
        return getTerminalStatuses().contains(this);
    }
    
    /**
     * Get all active statuses (statuses where the application is still being processed).
     * 
     * @return A set of active statuses
     */
    public static Set<ApplicationStatus> getActiveStatuses() {
        return Set.of(NEW, PENDING, PROCESSING, EXCEPTION);
    }
    
    /**
     * Check if this status is an active status.
     * 
     * @return true if this is an active status, false otherwise
     */
    public boolean isActive() {
        return getActiveStatuses().contains(this);
    }
    
    /**
     * Get all error statuses (statuses that indicate an issue with the application).
     * 
     * @return A set of error statuses
     */
    public static Set<ApplicationStatus> getErrorStatuses() {
        return Set.of(ERROR, EXCEPTION);
    }
    
    /**
     * Check if this status is an error status.
     * 
     * @return true if this is an error status, false otherwise
     */
    public boolean isError() {
        return getErrorStatuses().contains(this);
    }
    
    /**
     * Get all statuses that require human intervention.
     * 
     * @return A set of statuses requiring human intervention
     */
    public static Set<ApplicationStatus> getHumanInterventionStatuses() {
        return Set.of(EXCEPTION, ERROR, PENDING);
    }
    
    /**
     * Check if this status requires human intervention.
     * 
     * @return true if this status requires human intervention, false otherwise
     */
    public boolean requiresHumanIntervention() {
        return getHumanInterventionStatuses().contains(this);
    }
    
    /**
     * Get all statuses as a string array.
     * 
     * @return An array of status names as strings
     */
    public static String[] getStatusNames() {
        return Arrays.stream(ApplicationStatus.values())
                .map(Enum::name)
                .toArray(String[]::new);
    }
    
    /**
     * Get all statuses with their descriptions as a map.
     * 
     * @return A map of status names to descriptions
     */
    public static Map<String, String> getStatusDescriptions() {
        return Arrays.stream(ApplicationStatus.values())
                .collect(Collectors.toMap(
                    Enum::name,
                    ApplicationStatus::getDescription
                ));
    }
}