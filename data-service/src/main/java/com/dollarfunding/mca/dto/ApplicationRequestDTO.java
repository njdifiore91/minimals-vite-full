package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Data Transfer Object for creating or updating MCA applications.
 * This class defines the structure for incoming application data with
 * validation annotations for required fields. It serves as the contract
 * for application creation and update operations in the REST API.
 * <p>
 * Fields include application status, metadata, and review status with
 * appropriate JSON serialization annotations.
 * </p>
 *
 * @author MCA Application Team
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApplicationRequestDTO {

    /**
     * Current status of the application in its lifecycle.
     * This field is required and must be a valid ApplicationStatus value.
     */
    @NotNull(message = "Application status is required")
    @JsonProperty("status")
    private String status;

    /**
     * Current review status of the application.
     * This field is required and must be a valid ReviewStatus value.
     */
    @NotNull(message = "Review status is required")
    @JsonProperty("review_status")
    private String reviewStatus;

    /**
     * Application metadata including processing details, confidence scores, etc.
     * This field is optional and will be stored as a JSON object in the database.
     */
    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * Converts this DTO to an Application entity.
     * This method handles the conversion of all fields, including proper
     * parsing of status enums and metadata formatting.
     *
     * @return A new Application entity with data from this DTO
     * @throws IllegalArgumentException if status or reviewStatus is invalid
     */
    public Application toEntity() {
        // Parse status enum
        ApplicationStatus applicationStatus;
        try {
            applicationStatus = ApplicationStatus.valueOf(this.status);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid application status: " + this.status);
        }

        // Parse review status enum
        ReviewStatus appReviewStatus;
        try {
            appReviewStatus = ReviewStatus.valueOf(this.reviewStatus);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid review status: " + this.reviewStatus);
        }

        // Create and return the entity
        return new Application.Builder()
                .withStatus(applicationStatus)
                .withReviewStatus(appReviewStatus)
                .withMetadata(this.metadata != null ? this.metadata : new HashMap<>())
                .withCreatedAt(LocalDateTime.now())
                .withUpdatedAt(LocalDateTime.now())
                .build();
    }

    /**
     * Updates an existing Application entity with data from this DTO.
     * This method updates status, review status, and metadata fields in the entity
     * with values from this DTO, preserving the entity's ID, creation timestamp,
     * and relationships.
     *
     * @param entity The existing Application entity to update
     * @return The updated Application entity
     * @throws IllegalArgumentException if entity is null or status/reviewStatus is invalid
     */
    public Application updateEntity(Application entity) {
        if (entity == null) {
            throw new IllegalArgumentException("Entity cannot be null");
        }

        // Update status if provided
        if (this.status != null) {
            try {
                ApplicationStatus applicationStatus = ApplicationStatus.valueOf(this.status);
                // Check if the status transition is valid
                if (!entity.getStatus().canTransitionTo(applicationStatus)) {
                    throw new IllegalArgumentException(
                            "Invalid status transition from " + entity.getStatus() + " to " + applicationStatus);
                }
                entity.setStatus(applicationStatus);
            } catch (IllegalArgumentException e) {
                if (e.getMessage().contains("Invalid status transition")) {
                    throw e;
                }
                throw new IllegalArgumentException("Invalid application status: " + this.status);
            }
        }

        // Update review status if provided
        if (this.reviewStatus != null) {
            try {
                ReviewStatus appReviewStatus = ReviewStatus.valueOf(this.reviewStatus);
                // Check if the review status transition is valid
                if (!ReviewStatus.isValidTransition(entity.getReviewStatus(), appReviewStatus)) {
                    throw new IllegalArgumentException(
                            "Invalid review status transition from " + entity.getReviewStatus() + " to " + appReviewStatus);
                }
                entity.setReviewStatus(appReviewStatus);
            } catch (IllegalArgumentException e) {
                if (e.getMessage().contains("Invalid review status transition")) {
                    throw e;
                }
                throw new IllegalArgumentException("Invalid review status: " + this.reviewStatus);
            }
        }

        // Update metadata if provided
        if (this.metadata != null) {
            entity.setMetadata(this.metadata);
        }

        // Update the timestamp
        entity.setUpdatedAt(LocalDateTime.now());

        return entity;
    }

    /**
     * Creates a new ApplicationRequestDTO from an Application entity.
     * This method extracts status, review status, and metadata from the entity.
     *
     * @param application The Application entity
     * @return A new ApplicationRequestDTO with data from the entity
     */
    public static ApplicationRequestDTO fromEntity(Application application) {
        if (application == null) {
            return null;
        }

        return ApplicationRequestDTO.builder()
                .status(application.getStatus().name())
                .reviewStatus(application.getReviewStatus().name())
                .metadata(application.getMetadata())
                .build();
    }

    /**
     * Validates that the status value is a valid ApplicationStatus enum value.
     *
     * @return true if valid, false otherwise
     */
    public boolean isValidStatus() {
        if (this.status == null) {
            return false;
        }
        try {
            ApplicationStatus.valueOf(this.status);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    /**
     * Validates that the review status value is a valid ReviewStatus enum value.
     *
     * @return true if valid, false otherwise
     */
    public boolean isValidReviewStatus() {
        if (this.reviewStatus == null) {
            return false;
        }
        try {
            ReviewStatus.valueOf(this.reviewStatus);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    /**
     * Gets a specific metadata value.
     *
     * @param key the metadata key
     * @param <T> the expected type of the metadata value
     * @return the metadata value, or null if not available
     */
    @SuppressWarnings("unchecked")
    public <T> T getMetadataValue(String key) {
        if (metadata == null) {
            return null;
        }
        return (T) metadata.get(key);
    }

    /**
     * Adds a metadata key-value pair.
     *
     * @param key   the metadata key
     * @param value the metadata value
     */
    public void addMetadata(String key, Object value) {
        if (metadata == null) {
            metadata = new HashMap<>();
        }
        metadata.put(key, value);
    }
}