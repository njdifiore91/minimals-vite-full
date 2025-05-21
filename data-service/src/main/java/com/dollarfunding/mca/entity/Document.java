package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;

import javax.persistence.*;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.ArrayList;
import java.util.List;

/**
 * JPA entity class representing document metadata in the database.
 * 
 * This entity maps to the Documents schema and stores metadata about documents
 * uploaded as part of an MCA application. The actual document content is stored
 * in S3-compatible storage with AES-256 encryption, and this entity maintains a reference 
 * to the storage path. It has a Many-to-One relationship with the Application entity.
 * 
 * The document classification is performed by the Document Service with 99% accuracy,
 * and data extraction is performed by the OCR Service using machine learning models.
 */
@Entity
@Table(name = "documents")
public class Document {

    /**
     * Unique identifier for the document
     */
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    /**
     * ID of the application this document belongs to
     */
    @Column(name = "application_id", nullable = false)
    private UUID applicationId;
    
    /**
     * Many-to-One relationship with the Application entity
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "application_id", insertable = false, updatable = false)
    private Application application;

    /**
     * Type of document (e.g., BANK_STATEMENT, TAX_RETURN, etc.)
     */
    @Enumerated(EnumType.STRING)
    @Column(name = "type", nullable = false)
    private DocumentType type;

    /**
     * Path to the document in S3-compatible storage with AES-256 encryption
     * Format: s3://bucket-name/path/to/document
     */
    @Column(name = "storage_path", nullable = false)
    private String storagePath;

    /**
     * Document classification determined by the Document Service
     * This can be more specific than the general document type
     */
    @Column(name = "classification")
    private String classification;

    /**
     * Timestamp when the document was uploaded
     */
    @Column(name = "uploaded_at", nullable = false)
    private LocalDateTime uploadedAt;

    /**
     * JSON string representation of the document metadata
     * Includes OCR extraction results, confidence scores, etc.
     */
    @Column(name = "metadata", columnDefinition = "jsonb")
    private String metadataJson;

    /**
     * In-memory representation of the document metadata
     * Not persisted directly to the database, but converted to/from metadataJson
     */
    @Transient
    private Map<String, Object> metadata;

    /**
     * Default constructor required by JPA
     */
    public Document() {
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor with required fields
     * 
     * @param applicationId The ID of the application this document belongs to
     * @param type The type of document
     * @param storagePath The path to the document in S3-compatible storage
     */
    public Document(UUID applicationId, DocumentType type, String storagePath) {
        this.applicationId = applicationId;
        this.type = type;
        this.storagePath = storagePath;
        this.uploadedAt = LocalDateTime.now();
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor with all fields except ID
     * 
     * @param applicationId The ID of the application this document belongs to
     * @param type The type of document
     * @param storagePath The path to the document in S3-compatible storage
     * @param classification The document classification
     * @param uploadedAt The timestamp when the document was uploaded
     * @param metadata The document metadata
     */
    public Document(UUID applicationId, DocumentType type, String storagePath, 
                   String classification, LocalDateTime uploadedAt, Map<String, Object> metadata) {
        this.applicationId = applicationId;
        this.type = type;
        this.storagePath = storagePath;
        this.classification = classification;
        this.uploadedAt = uploadedAt;
        this.metadata = metadata != null ? metadata : new HashMap<>();
    }

    /**
     * @return the document ID
     */
    public UUID getId() {
        return id;
    }

    /**
     * @param id the document ID to set
     */
    public void setId(UUID id) {
        this.id = id;
    }

    /**
     * @return the application ID this document belongs to
     */
    public UUID getApplicationId() {
        return applicationId;
    }

    /**
     * @param applicationId the application ID to set
     */
    public void setApplicationId(UUID applicationId) {
        this.applicationId = applicationId;
    }
    
    /**
     * @return the application this document belongs to
     */
    public Application getApplication() {
        return application;
    }

    /**
     * @param application the application to set
     */
    public void setApplication(Application application) {
        this.application = application;
        if (application != null && application.getId() != null) {
            this.applicationId = application.getId();
        }
    }

    /**
     * @return the document type
     */
    public DocumentType getType() {
        return type;
    }

    /**
     * @param type the document type to set
     */
    public void setType(DocumentType type) {
        this.type = type;
    }

    /**
     * @return the storage path in S3-compatible storage
     */
    public String getStoragePath() {
        return storagePath;
    }

    /**
     * @param storagePath the storage path to set
     */
    public void setStoragePath(String storagePath) {
        this.storagePath = storagePath;
    }

    /**
     * @return the document classification
     */
    public String getClassification() {
        return classification;
    }

    /**
     * @param classification the document classification to set
     */
    public void setClassification(String classification) {
        this.classification = classification;
    }

    /**
     * @return the upload timestamp
     */
    public LocalDateTime getUploadedAt() {
        return uploadedAt;
    }

    /**
     * @param uploadedAt the upload timestamp to set
     */
    public void setUploadedAt(LocalDateTime uploadedAt) {
        this.uploadedAt = uploadedAt;
    }

    /**
     * @return the document metadata
     */
    public Map<String, Object> getMetadata() {
        if (metadata == null && metadataJson != null && !metadataJson.isEmpty()) {
            try {
                metadata = JsonUtil.fromJson(metadataJson, new TypeReference<Map<String, Object>>() {});
            } catch (Exception e) {
                metadata = new HashMap<>();
            }
        }
        return metadata != null ? metadata : new HashMap<>();
    }

    /**
     * @param metadata the document metadata to set
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
        if (metadata != null) {
            try {
                this.metadataJson = JsonUtil.toJson(metadata);
            } catch (Exception e) {
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
            } catch (Exception e) {
                this.metadata = new HashMap<>();
            }
        } else {
            this.metadata = new HashMap<>();
        }
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
        } catch (Exception e) {
            // Log error but continue
        }
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
     * Adds confidence scores to the metadata
     * 
     * @param confidenceScores the confidence scores to add
     */
    public void addConfidenceScores(Map<String, Double> confidenceScores) {
        if (confidenceScores == null || confidenceScores.isEmpty()) {
            return;
        }
        Map<String, Object> metadataMap = getMetadata();
        metadataMap.put("confidenceScores", confidenceScores);
        setMetadata(metadataMap);
    }

    /**
     * Gets the confidence scores from the metadata
     * 
     * @return the confidence scores, or an empty map if not available
     */
    @SuppressWarnings("unchecked")
    public Map<String, Double> getConfidenceScores() {
        Map<String, Object> metadataMap = getMetadata();
        if (metadataMap == null || !metadataMap.containsKey("confidenceScores")) {
            return new HashMap<>();
        }
        return (Map<String, Double>) metadataMap.get("confidenceScores");
    }

    /**
     * Gets the confidence score for a specific field
     * 
     * @param fieldName the field name to get the confidence score for
     * @return the confidence score, or null if not available
     */
    public Double getConfidenceScore(String fieldName) {
        Map<String, Double> scores = getConfidenceScores();
        if (scores.isEmpty()) {
            return null;
        }
        return scores.get(fieldName);
    }

    /**
     * Checks if this document contains personally identifiable information (PII)
     * 
     * @return true if the document contains PII, false otherwise
     */
    public boolean containsPII() {
        return type != null && type.containsPII();
    }

    /**
     * Checks if this document is a financial document
     * 
     * @return true if the document is financial, false otherwise
     */
    public boolean isFinancialDocument() {
        return type != null && type.isFinancialDocument();
    }

    /**
     * Gets the expected OCR confidence threshold for this document type
     * 
     * @return the minimum confidence threshold (0.0-1.0) for OCR extraction
     */
    public double getOcrConfidenceThreshold() {
        return type != null ? type.getOcrConfidenceThreshold() : 0.65;
    }

    /**
     * Checks if this document has been classified with high confidence
     * 
     * @return true if the document has been classified with high confidence
     */
    public boolean isClassifiedWithHighConfidence() {
        Double classificationConfidence = getConfidenceScore("classification");
        return classificationConfidence != null && classificationConfidence >= getOcrConfidenceThreshold();
    }

    /**
     * Gets the S3 bucket name from the storage path
     * 
     * @return the S3 bucket name, or null if the storage path is invalid
     */
    public String getBucketName() {
        if (storagePath == null || !storagePath.startsWith("s3://")) {
            return null;
        }
        String path = storagePath.substring(5); // Remove "s3://"
        int slashIndex = path.indexOf('/');
        if (slashIndex == -1) {
            return path;
        }
        return path.substring(0, slashIndex);
    }

    /**
     * Gets the S3 object key from the storage path
     * 
     * @return the S3 object key, or null if the storage path is invalid
     */
    public String getObjectKey() {
        if (storagePath == null || !storagePath.startsWith("s3://")) {
            return null;
        }
        String path = storagePath.substring(5); // Remove "s3://"
        int slashIndex = path.indexOf('/');
        if (slashIndex == -1) {
            return "";
        }
        return path.substring(slashIndex + 1);
    }

    /**
     * Checks if this document has valid storage information
     * 
     * @return true if the document has valid storage information
     */
    public boolean hasValidStorage() {
        return storagePath != null && !storagePath.isEmpty() && storagePath.startsWith("s3://");
    }

    /**
     * Checks if this document has metadata
     * 
     * @return true if the document has metadata
     */
    public boolean hasMetadata() {
        Map<String, Object> metadataMap = getMetadata();
        return metadataMap != null && !metadataMap.isEmpty();
    }

    /**
     * Checks if this document is valid for processing
     * 
     * @return true if the document is valid for processing
     */
    public boolean isValidForProcessing() {
        return applicationId != null && 
               type != null && 
               storagePath != null && !storagePath.isEmpty() &&
               uploadedAt != null;
    }

    /**
     * Returns a string representation of this entity for debugging and logging
     * 
     * @return a string representation of this entity
     */
    @Override
    public String toString() {
        return "Document{" +
                "id=" + id +
                ", applicationId=" + applicationId +
                ", type=" + type +
                ", classification='" + classification + '\'' +
                ", uploadedAt=" + uploadedAt +
                ", hasMetadata=" + hasMetadata() +
                ", hasValidStorage=" + hasValidStorage() +
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

        Document document = (Document) o;

        return id != null ? id.equals(document.id) : document.id == null;
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
     * Builder class for creating Document instances
     */
    public static class Builder {
        private UUID applicationId;
        private DocumentType type;
        private String storagePath;
        private String classification;
        private LocalDateTime uploadedAt;
        private Map<String, Object> metadata;

        public Builder(UUID applicationId, DocumentType type, String storagePath) {
            this.applicationId = applicationId;
            this.type = type;
            this.storagePath = storagePath;
            this.uploadedAt = LocalDateTime.now();
            this.metadata = new HashMap<>();
        }

        public Builder withClassification(String classification) {
            this.classification = classification;
            return this;
        }

        public Builder withUploadedAt(LocalDateTime uploadedAt) {
            this.uploadedAt = uploadedAt;
            return this;
        }

        public Builder withMetadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Builder addMetadata(String key, Object value) {
            if (this.metadata == null) {
                this.metadata = new HashMap<>();
            }
            this.metadata.put(key, value);
            return this;
        }

        public Builder withConfidenceScores(Map<String, Double> confidenceScores) {
            if (this.metadata == null) {
                this.metadata = new HashMap<>();
            }
            this.metadata.put("confidenceScores", confidenceScores);
            return this;
        }

        public Document build() {
            return new Document(applicationId, type, storagePath, classification, uploadedAt, metadata);
        }
    }
}