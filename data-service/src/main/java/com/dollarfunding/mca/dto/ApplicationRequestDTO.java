package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.util.HashMap;
import java.util.Map;

/**
 * Data Transfer Object for creating or updating MCA applications.
 * Defines the structure for incoming application data with validation annotations for required fields.
 * This class includes fields for application status, metadata, and review status,
 * with appropriate JSON serialization annotations.
 * It serves as the contract for application creation and update operations in the REST API.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApplicationRequestDTO {

    @NotNull(message = "Application status is required")
    @JsonProperty("status")
    private ApplicationStatus status;

    @JsonProperty("review_status")
    private ReviewStatus reviewStatus;

    @Size(max = 10000, message = "Metadata size exceeds maximum allowed")
    @JsonProperty("metadata")
    private Map<String, Object> metadata = new HashMap<>();

    /**
     * Default constructor
     */
    public ApplicationRequestDTO() {
    }

    /**
     * Constructor with all fields
     *
     * @param status       The application status
     * @param reviewStatus The review status
     * @param metadata     Additional metadata for the application
     */
    public ApplicationRequestDTO(ApplicationStatus status, ReviewStatus reviewStatus, Map<String, Object> metadata) {
        this.status = status;
        this.reviewStatus = reviewStatus;
        this.metadata = metadata != null ? metadata : new HashMap<>();
    }

    /**
     * Converts this DTO to an Application entity
     * Note: This method creates a new entity and does not set id, createdAt, or updatedAt fields
     * which are typically managed by the persistence layer
     *
     * @return A new Application entity with fields populated from this DTO
     */
    public Application toEntity() {
        Application application = new Application();
        application.setStatus(this.status);
        application.setReviewStatus(this.reviewStatus);
        application.setMetadata(this.metadata);
        return application;
    }

    /**
     * Updates an existing Application entity with values from this DTO
     * Note: This method does not update id, createdAt, or updatedAt fields
     * which are typically managed by the persistence layer
     *
     * @param application The Application entity to update
     * @return The updated Application entity
     */
    public Application updateEntity(Application application) {
        if (application == null) {
            return toEntity();
        }

        application.setStatus(this.status);
        
        // Only update review status if it's provided
        if (this.reviewStatus != null) {
            application.setReviewStatus(this.reviewStatus);
        }
        
        // Only update metadata if it's provided
        if (this.metadata != null) {
            application.setMetadata(this.metadata);
        }
        
        return application;
    }

    /**
     * Creates a DTO from an Application entity
     *
     * @param application The Application entity to convert
     * @return A new ApplicationRequestDTO
     */
    public static ApplicationRequestDTO fromEntity(Application application) {
        if (application == null) {
            return null;
        }

        return new ApplicationRequestDTO(
                application.getStatus(),
                application.getReviewStatus(),
                application.getMetadata()
        );
    }

    /**
     * Validates that the application status transition is valid
     * This method can be used to enforce business rules for status transitions
     *
     * @param currentStatus The current application status
     * @return true if the transition is valid, false otherwise
     */
    public boolean isValidStatusTransition(ApplicationStatus currentStatus) {
        // If current status is null (new application), any status is valid
        if (currentStatus == null) {
            return true;
        }

        // Implement business rules for status transitions
        // For example, an application can't go from REJECTED back to PROCESSING
        switch (currentStatus) {
            case NEW:
                // NEW can transition to PENDING or REJECTED
                return this.status == ApplicationStatus.PENDING || 
                       this.status == ApplicationStatus.REJECTED;
                
            case PENDING:
                // PENDING can transition to PROCESSING, REJECTED, or back to NEW
                return this.status == ApplicationStatus.PROCESSING || 
                       this.status == ApplicationStatus.REJECTED || 
                       this.status == ApplicationStatus.NEW;
                
            case PROCESSING:
                // PROCESSING can transition to APPROVED, REJECTED, or back to PENDING
                return this.status == ApplicationStatus.APPROVED || 
                       this.status == ApplicationStatus.REJECTED || 
                       this.status == ApplicationStatus.PENDING;
                
            case APPROVED:
                // APPROVED can transition to COMPLETED or back to PROCESSING
                return this.status == ApplicationStatus.COMPLETED || 
                       this.status == ApplicationStatus.PROCESSING;
                
            case REJECTED:
                // REJECTED is a terminal state, but can go back to NEW if resubmitted
                return this.status == ApplicationStatus.NEW;
                
            case COMPLETED:
                // COMPLETED is a terminal state and cannot transition
                return false;
                
            default:
                return false;
        }
    }

    // Getters and Setters

    public ApplicationStatus getStatus() {
        return status;
    }

    public void setStatus(ApplicationStatus status) {
        this.status = status;
    }

    public ReviewStatus getReviewStatus() {
        return reviewStatus;
    }

    public void setReviewStatus(ReviewStatus reviewStatus) {
        this.reviewStatus = reviewStatus;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata != null ? metadata : new HashMap<>();
    }

    @Override
    public String toString() {
        return "ApplicationRequestDTO{" +
                "status=" + status +
                ", reviewStatus=" + reviewStatus +
                ", metadata=" + metadata +
                '}';
    }
}