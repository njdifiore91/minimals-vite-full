package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;

import javax.persistence.*;
import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * JPA entity class representing an MCA application in the database.
 * 
 * This entity maps to the Applications schema and serves as the core data structure
 * for tracking merchant cash advance applications throughout their lifecycle.
 * It includes bidirectional relationships with Document and MerchantDetails entities.
 * 
 * The application processing system is designed to process applications in under 5 minutes
 * from receipt to completion and maintain 99% data extraction accuracy through AI and
 * machine learning.
 */
@Entity
@Table(name = "applications")
public class Application {

    /**
     * Unique identifier for the application
     */
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    /**
     * Current status of the application in its lifecycle
     */
    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    private ApplicationStatus status;

    /**
     * Current review status of the application
     */
    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(name = "review_status", nullable = false)
    private ReviewStatus reviewStatus;

    /**
     * JSON string representation of the application metadata
     * Includes processing details, confidence scores, etc.
     */
    @Column(name = "metadata", columnDefinition = "jsonb")
    private String metadataJson;

    /**
     * In-memory representation of the application metadata
     * Not persisted directly to the database, but converted to/from metadataJson
     */
    @Transient
    private Map<String, Object> metadata;

    /**
     * Timestamp when the application was created
     */
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /**
     * Timestamp when the application was last updated
     */
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    /**
     * One-to-Many relationship with Document entity
     * An application can have multiple documents
     */
    @OneToMany(mappedBy = "application", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Document> documents;

    /**
     * One-to-One relationship with MerchantDetails entity
     * An application has exactly one merchant details record
     */
    @OneToOne(mappedBy = "application", cascade = CascadeType.ALL, orphanRemoval = true)
    private MerchantDetails merchantDetails;

    /**
     * Default constructor required by JPA
     */
    public Application() {
        this.metadata = new HashMap<>();
        this.documents = new ArrayList<>();
        this.status = ApplicationStatus.NEW;
        this.reviewStatus = ReviewStatus.NOT_REVIEWED;
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Constructor with required fields
     */
    public Application(ApplicationStatus status, ReviewStatus reviewStatus) {
        this();
        this.status = status;
        this.reviewStatus = reviewStatus;
    }

    /**
     * Constructor with all fields except ID and relationships
     */
    public Application(ApplicationStatus status, ReviewStatus reviewStatus, 
                      Map<String, Object> metadata, LocalDateTime createdAt, 
                      LocalDateTime updatedAt) {
        this.status = status;
        this.reviewStatus = reviewStatus;
        this.metadata = metadata != null ? metadata : new HashMap<>();
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.documents = new ArrayList<>();
        
        // Convert metadata map to JSON string
        if (metadata != null) {
            try {
                this.metadataJson = JsonUtil.toJson(metadata);
            } catch (JsonUtil.JsonConversionException e) {
                this.metadataJson = "{}";
            }
        } else {
            this.metadataJson = "{}";
        }
    }

    /**
     * @return the application ID
     */
    public UUID getId() {
        return id;
    }

    /**
     * @param id the application ID to set
     */
    public void setId(UUID id) {
        this.id = id;
    }

    /**
     * @return the application status
     */
    public ApplicationStatus getStatus() {
        return status;
    }

    /**
     * @param status the application status to set
     */
    public void setStatus(ApplicationStatus status) {
        this.status = status;
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Updates the application status if the transition is valid
     * 
     * @param newStatus the new status to transition to
     * @return true if the status was updated, false if the transition is invalid
     */
    public boolean updateStatus(ApplicationStatus newStatus) {
        if (this.status.canTransitionTo(newStatus)) {
            this.status = newStatus;
            this.updatedAt = LocalDateTime.now();
            return true;
        }
        return false;
    }

    /**
     * @return the review status
     */
    public ReviewStatus getReviewStatus() {
        return reviewStatus;
    }

    /**
     * @param reviewStatus the review status to set
     */
    public void setReviewStatus(ReviewStatus reviewStatus) {
        this.reviewStatus = reviewStatus;
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Updates the review status if the transition is valid
     * 
     * @param newReviewStatus the new review status to transition to
     * @return true if the review status was updated, false if the transition is invalid
     */
    public boolean updateReviewStatus(ReviewStatus newReviewStatus) {
        if (ReviewStatus.isValidTransition(this.reviewStatus, newReviewStatus)) {
            this.reviewStatus = newReviewStatus;
            this.updatedAt = LocalDateTime.now();
            return true;
        }
        return false;
    }

    /**
     * @return the application metadata
     */
    public Map<String, Object> getMetadata() {
        if (metadata == null && metadataJson != null && !metadataJson.isEmpty()) {
            try {
                metadata = JsonUtil.fromJson(metadataJson, new TypeReference<Map<String, Object>>() {});
            } catch (JsonUtil.JsonConversionException e) {
                metadata = new HashMap<>();
            }
        }
        return metadata != null ? metadata : new HashMap<>();
    }

    /**
     * @param metadata the application metadata to set
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
        if (metadata != null) {
            try {
                this.metadataJson = JsonUtil.toJson(metadata);
            } catch (JsonUtil.JsonConversionException e) {
                this.metadataJson = "{}";
            }
        } else {
            this.metadataJson = "{}";
        }
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Gets the JSON string representation of the metadata
     * 
     * @return the metadata JSON string
     */
    public String getMetadataJson() {
        return metadataJson;
    }

    /**
     * Sets the metadata from a JSON string
     * 
     * @param metadataJson the metadata JSON string to set
     */
    public void setMetadataJson(String metadataJson) {
        this.metadataJson = metadataJson;
        if (metadataJson != null && !metadataJson.isEmpty()) {
            try {
                this.metadata = JsonUtil.fromJson(metadataJson, new TypeReference<Map<String, Object>>() {});
            } catch (JsonUtil.JsonConversionException e) {
                this.metadata = new HashMap<>();
            }
        } else {
            this.metadata = new HashMap<>();
        }
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Adds a metadata key-value pair
     * 
     * @param key the metadata key
     * @param value the metadata value
     */
    public void addMetadata(String key, Object value) {
        if (metadata == null) {
            metadata = new HashMap<>();
        }
        metadata.put(key, value);
        try {
            this.metadataJson = JsonUtil.toJson(metadata);
        } catch (JsonUtil.JsonConversionException e) {
            // Log error but continue
        }
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Gets a specific metadata value
     * 
     * @param key the metadata key
     * @param <T> the expected type of the metadata value
     * @return the metadata value, or null if not available
     */
    @SuppressWarnings("unchecked")
    public <T> T getMetadataValue(String key) {
        Map<String, Object> metadataMap = getMetadata();
        if (metadataMap == null) {
            return null;
        }
        return (T) metadataMap.get(key);
    }

    /**
     * @return the creation timestamp
     */
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    /**
     * @param createdAt the creation timestamp to set
     */
    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    /**
     * @return the update timestamp
     */
    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    /**
     * @param updatedAt the update timestamp to set
     */
    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    /**
     * @return the list of documents associated with this application
     */
    public List<Document> getDocuments() {
        return documents;
    }

    /**
     * @param documents the list of documents to set
     */
    public void setDocuments(List<Document> documents) {
        this.documents = documents;
        if (documents != null) {
            for (Document document : documents) {
                document.setApplication(this);
            }
        }
    }

    /**
     * Adds a document to this application
     * 
     * @param document the document to add
     */
    public void addDocument(Document document) {
        if (documents == null) {
            documents = new ArrayList<>();
        }
        documents.add(document);
        document.setApplication(this);
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Removes a document from this application
     * 
     * @param document the document to remove
     */
    public void removeDocument(Document document) {
        if (documents != null) {
            documents.remove(document);
            document.setApplication(null);
            this.updatedAt = LocalDateTime.now();
        }
    }

    /**
     * @return the merchant details associated with this application
     */
    public MerchantDetails getMerchantDetails() {
        return merchantDetails;
    }

    /**
     * @param merchantDetails the merchant details to set
     */
    public void setMerchantDetails(MerchantDetails merchantDetails) {
        this.merchantDetails = merchantDetails;
        if (merchantDetails != null) {
            merchantDetails.setApplication(this);
        }
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Checks if this application has been completed
     * 
     * @return true if the application status is COMPLETED
     */
    public boolean isCompleted() {
        return status == ApplicationStatus.COMPLETED;
    }

    /**
     * Checks if this application is in an active state
     * 
     * @return true if the application is in an active state
     */
    public boolean isActive() {
        return status.isActiveStatus();
    }

    /**
     * Checks if this application has been decided upon
     * 
     * @return true if the application has been decided upon
     */
    public boolean isDecided() {
        return status.isDecidedStatus();
    }

    /**
     * Checks if this application requires review
     * 
     * @return true if the application requires review
     */
    public boolean requiresReview() {
        return reviewStatus.requiresAction();
    }

    /**
     * Checks if this application has all required documents
     * 
     * @return true if the application has all required documents
     */
    public boolean hasAllRequiredDocuments() {
        // Check if we have at least one document of each required type
        boolean hasIdentification = false;
        boolean hasFinancial = false;
        boolean hasBusinessVerification = false;
        
        if (documents != null) {
            for (Document document : documents) {
                DocumentType type = document.getType();
                if (type == DocumentType.ID_VERIFICATION) {
                    hasIdentification = true;
                } else if (type == DocumentType.BANK_STATEMENT || type == DocumentType.TAX_RETURN) {
                    hasFinancial = true;
                } else if (type == DocumentType.BUSINESS_LICENSE || type == DocumentType.INVOICE) {
                    hasBusinessVerification = true;
                }
            }
        }
        
        return hasIdentification && hasFinancial && hasBusinessVerification;
    }

    /**
     * Calculates the processing time of this application in minutes
     * 
     * @return the processing time in minutes, or -1 if the application is not completed
     */
    public long getProcessingTimeMinutes() {
        if (!isCompleted() || createdAt == null || updatedAt == null) {
            return -1;
        }
        return java.time.Duration.between(createdAt, updatedAt).toMinutes();
    }

    /**
     * Checks if this application was processed within the target time (5 minutes)
     * 
     * @return true if the application was processed within the target time
     */
    public boolean isProcessedWithinTargetTime() {
        long processingTime = getProcessingTimeMinutes();
        return processingTime >= 0 && processingTime <= 5;
    }

    /**
     * Returns a string representation of this entity for debugging and logging
     * 
     * @return a string representation of this entity
     */
    @Override
    public String toString() {
        return "Application{" +
                "id=" + id +
                ", status=" + status +
                ", reviewStatus=" + reviewStatus +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                ", documentsCount=" + (documents != null ? documents.size() : 0) +
                ", hasMerchantDetails=" + (merchantDetails != null) +
                "}";
    }

    /**
     * Compares this entity with another object for equality
     * 
     * @param o the object to compare with
     * @return true if the objects are equal
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        Application that = (Application) o;

        return id != null ? id.equals(that.id) : that.id == null;
    }

    /**
     * Returns a hash code for this entity
     * 
     * @return a hash code value for this object
     */
    @Override
    public int hashCode() {
        return id != null ? id.hashCode() : 0;
    }

    /**
     * Builder class for creating Application instances
     */
    public static class Builder {
        private ApplicationStatus status = ApplicationStatus.NEW;
        private ReviewStatus reviewStatus = ReviewStatus.NOT_REVIEWED;
        private Map<String, Object> metadata = new HashMap<>();
        private LocalDateTime createdAt = LocalDateTime.now();
        private LocalDateTime updatedAt = LocalDateTime.now();

        public Builder withStatus(ApplicationStatus status) {
            this.status = status;
            return this;
        }

        public Builder withReviewStatus(ReviewStatus reviewStatus) {
            this.reviewStatus = reviewStatus;
            return this;
        }

        public Builder withMetadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Builder addMetadata(String key, Object value) {
            this.metadata.put(key, value);
            return this;
        }

        public Builder withCreatedAt(LocalDateTime createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        public Builder withUpdatedAt(LocalDateTime updatedAt) {
            this.updatedAt = updatedAt;
            return this;
        }

        public Application build() {
            return new Application(status, reviewStatus, metadata, createdAt, updatedAt);
        }
    }
}