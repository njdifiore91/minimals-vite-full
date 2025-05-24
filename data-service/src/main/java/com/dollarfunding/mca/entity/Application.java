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
 * for tracking merchant cash advance applications throughout their lifecycle. It includes
 * bidirectional relationships with Document and MerchantDetails entities.
 * 
 * The Data Service uses this entity to manage application data, processing logic, and
 * database interactions. Applications are processed in under 5 minutes from receipt to
 * completion with 99% data extraction accuracy through AI and machine learning.
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
    @NotNull
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    /**
     * Timestamp when the application was last updated
     */
    @NotNull
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    /**
     * Current review status of the application
     */
    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(name = "review_status", nullable = false)
    private ReviewStatus reviewStatus;

    /**
     * One-to-Many relationship with Document entity
     * An application can have multiple documents
     */
    @OneToMany(mappedBy = "application", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Document> documents;

    /**
     * One-to-One relationship with MerchantDetails entity
     * An application has one merchant details record
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
     * 
     * @param status The initial status of the application
     */
    public Application(ApplicationStatus status) {
        this();
        this.status = status != null ? status : ApplicationStatus.NEW;
    }

    /**
     * Constructor with all fields except ID and relationships
     * 
     * @param status The status of the application
     * @param metadata The application metadata
     * @param createdAt The timestamp when the application was created
     * @param updatedAt The timestamp when the application was last updated
     * @param reviewStatus The review status of the application
     */
    public Application(ApplicationStatus status, Map<String, Object> metadata,
                      LocalDateTime createdAt, LocalDateTime updatedAt, ReviewStatus reviewStatus) {
        this.documents = new ArrayList<>();
        this.status = status != null ? status : ApplicationStatus.NEW;
        this.metadata = metadata != null ? metadata : new HashMap<>();
        this.createdAt = createdAt != null ? createdAt : LocalDateTime.now();
        this.updatedAt = updatedAt != null ? updatedAt : LocalDateTime.now();
        this.reviewStatus = reviewStatus != null ? reviewStatus : ReviewStatus.NOT_REVIEWED;
        
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
     * @return the current status of the application
     */
    public ApplicationStatus getStatus() {
        return status;
    }

    /**
     * @param status the status to set
     */
    public void setStatus(ApplicationStatus status) {
        if (status == null) {
            throw new IllegalArgumentException("Status cannot be null");
        }
        
        // Check if the status transition is valid
        if (this.status != null && !this.status.canTransitionTo(status)) {
            throw new IllegalStateException(
                "Invalid status transition from " + this.status + " to " + status);
        }
        
        this.status = status;
        this.updatedAt = LocalDateTime.now();
        
        // Add status change to metadata
        addMetadata("statusHistory", getStatusHistory());
        addMetadata("lastStatusChange", LocalDateTime.now().toString());
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
    }

    /**
     * @return the timestamp when the application was created
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
     * @return the timestamp when the application was last updated
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
     * @return the current review status of the application
     */
    public ReviewStatus getReviewStatus() {
        return reviewStatus;
    }

    /**
     * @param reviewStatus the review status to set
     */
    public void setReviewStatus(ReviewStatus reviewStatus) {
        if (reviewStatus == null) {
            throw new IllegalArgumentException("Review status cannot be null");
        }
        
        // Check if the review status transition is valid
        if (this.reviewStatus != null && !this.reviewStatus.canTransitionTo(reviewStatus)) {
            throw new IllegalStateException(
                "Invalid review status transition from " + this.reviewStatus + " to " + reviewStatus);
        }
        
        this.reviewStatus = reviewStatus;
        this.updatedAt = LocalDateTime.now();
        
        // Add review status change to metadata
        addMetadata("reviewStatusHistory", getReviewStatusHistory());
        addMetadata("lastReviewStatusChange", LocalDateTime.now().toString());
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
    }

    /**
     * Adds a document to this application
     * 
     * @param document the document to add
     */
    public void addDocument(Document document) {
        if (document == null) {
            return;
        }
        
        if (this.documents == null) {
            this.documents = new ArrayList<>();
        }
        
        this.documents.add(document);
        document.setApplication(this);
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Removes a document from this application
     * 
     * @param document the document to remove
     */
    public void removeDocument(Document document) {
        if (document == null || this.documents == null) {
            return;
        }
        
        this.documents.remove(document);
        document.setApplication(null);
        this.updatedAt = LocalDateTime.now();
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
     * Gets the status history of this application from metadata
     * 
     * @return the status history as a list, or an empty list if not available
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getStatusHistory() {
        List<Map<String, Object>> history = getMetadataValue("statusHistory");
        if (history == null) {
            history = new ArrayList<>();
        }
        
        // Add current status to history if it's not already there or has changed
        if (history.isEmpty() || !history.get(history.size() - 1).get("status").equals(status.name())) {
            Map<String, Object> entry = new HashMap<>();
            entry.put("status", status.name());
            entry.put("timestamp", LocalDateTime.now().toString());
            history.add(entry);
        }
        
        return history;
    }

    /**
     * Gets the review status history of this application from metadata
     * 
     * @return the review status history as a list, or an empty list if not available
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getReviewStatusHistory() {
        List<Map<String, Object>> history = getMetadataValue("reviewStatusHistory");
        if (history == null) {
            history = new ArrayList<>();
        }
        
        // Add current review status to history if it's not already there or has changed
        if (history.isEmpty() || !history.get(history.size() - 1).get("status").equals(reviewStatus.name())) {
            Map<String, Object> entry = new HashMap<>();
            entry.put("status", reviewStatus.name());
            entry.put("timestamp", LocalDateTime.now().toString());
            history.add(entry);
        }
        
        return history;
    }

    /**
     * Gets the processing time of this application in milliseconds
     * 
     * @return the processing time, or 0 if the application is not completed
     */
    public long getProcessingTimeMillis() {
        if (status != ApplicationStatus.COMPLETED) {
            return 0;
        }
        
        LocalDateTime completedAt = updatedAt;
        return java.time.Duration.between(createdAt, completedAt).toMillis();
    }

    /**
     * Checks if this application meets the 5-minute processing time requirement
     * 
     * @return true if the application was processed in under 5 minutes, false otherwise
     */
    public boolean meetsProcessingTimeRequirement() {
        if (status != ApplicationStatus.COMPLETED) {
            return false;
        }
        
        // 5 minutes = 300,000 milliseconds
        return getProcessingTimeMillis() < 300000;
    }

    /**
     * Gets the number of documents associated with this application
     * 
     * @return the number of documents
     */
    public int getDocumentCount() {
        return documents != null ? documents.size() : 0;
    }

    /**
     * Checks if this application has merchant details
     * 
     * @return true if the application has merchant details, false otherwise
     */
    public boolean hasMerchantDetails() {
        return merchantDetails != null;
    }

    /**
     * Checks if this application is in a terminal state
     * 
     * @return true if the application is in a terminal state, false otherwise
     */
    public boolean isTerminal() {
        return status != null && status.isTerminal();
    }

    /**
     * Checks if this application requires human intervention
     * 
     * @return true if the application requires human intervention, false otherwise
     */
    public boolean requiresHumanIntervention() {
        return status != null && status.requiresHumanIntervention();
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
                ", documentCount=" + getDocumentCount() +
                ", hasMerchantDetails=" + hasMerchantDetails() +
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
        private Map<String, Object> metadata = new HashMap<>();
        private LocalDateTime createdAt = LocalDateTime.now();
        private LocalDateTime updatedAt = LocalDateTime.now();
        private ReviewStatus reviewStatus = ReviewStatus.NOT_REVIEWED;

        public Builder() {
        }

        public Builder withStatus(ApplicationStatus status) {
            this.status = status;
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

        public Builder withReviewStatus(ReviewStatus reviewStatus) {
            this.reviewStatus = reviewStatus;
            return this;
        }

        public Application build() {
            return new Application(status, metadata, createdAt, updatedAt, reviewStatus);
        }
    }
}