package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;

import javax.persistence.*;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * JPA entity class representing document metadata in the database.
 * 
 * This entity maps to the Documents schema and stores metadata about documents uploaded
 * as part of an MCA application. The actual document content is stored in S3-compatible
 * storage with AES-256 encryption, while this entity maintains references and metadata.
 * 
 * It maintains a Many-to-One relationship with the Application entity and uses JPA
 * annotations for ORM mapping. The Document Service classifies documents into categories
 * with 99% accuracy, and the OCR Service extracts data from these documents using
 * machine learning models.
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
    @NotNull
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
    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(name = "type", nullable = false)
    private DocumentType type;

    /**
     * Path to the document in S3-compatible storage
     * Format: bucket/path/to/document.pdf
     */
    @NotNull
    @Size(max = 1024)
    @Column(name = "storage_path", nullable = false)
    private String storagePath;

    /**
     * Classification result from document processing
     */
    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(name = "classification", nullable = false)
    private DocumentClassification classification;

    /**
     * Timestamp when the document was uploaded
     */
    @NotNull
    @Column(name = "uploaded_at", nullable = false)
    private LocalDateTime uploadedAt;

    /**
     * JSON string representation of the document metadata
     * Includes OCR confidence scores, extracted fields, etc.
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
        this.classification = DocumentClassification.UNCLASSIFIED;
        this.uploadedAt = LocalDateTime.now();
    }

    /**
     * Constructor with required fields
     * 
     * @param applicationId The ID of the application this document belongs to
     * @param type The type of document
     * @param storagePath The path to the document in S3-compatible storage
     */
    public Document(UUID applicationId, DocumentType type, String storagePath) {
        this();
        this.applicationId = applicationId;
        this.type = type;
        this.storagePath = storagePath;
    }

    /**
     * Constructor with all fields except ID
     * 
     * @param applicationId The ID of the application this document belongs to
     * @param type The type of document
     * @param storagePath The path to the document in S3-compatible storage
     * @param classification The classification result from document processing
     * @param uploadedAt The timestamp when the document was uploaded
     * @param metadata The document metadata
     */
    public Document(UUID applicationId, DocumentType type, String storagePath,
                   DocumentClassification classification, LocalDateTime uploadedAt,
                   Map<String, Object> metadata) {
        this.applicationId = applicationId;
        this.type = type;
        this.storagePath = storagePath;
        this.classification = classification != null ? classification : DocumentClassification.UNCLASSIFIED;
        this.uploadedAt = uploadedAt != null ? uploadedAt : LocalDateTime.now();
        this.metadata = metadata != null ? metadata : new HashMap<>();
        
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
     * @return the type of document
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
     * @return the path to the document in S3-compatible storage
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
     * @return the classification result from document processing
     */
    public DocumentClassification getClassification() {
        return classification;
    }

    /**
     * @param classification the classification to set
     */
    public void setClassification(DocumentClassification classification) {
        this.classification = classification != null ? classification : DocumentClassification.UNCLASSIFIED;
    }

    /**
     * @return the timestamp when the document was uploaded
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
            } catch (JsonUtil.JsonConversionException e) {
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
     * Gets the confidence score for this document's classification
     * 
     * @return the confidence score, or 0.0 if not available
     */
    public double getConfidenceScore() {
        Double score = getMetadataValue("confidenceScore");
        return score != null ? score : 0.0;
    }

    /**
     * Sets the confidence score for this document's classification
     * 
     * @param score the confidence score to set
     */
    public void setConfidenceScore(double score) {
        addMetadata("confidenceScore", score);
        // Update classification based on confidence score
        this.classification = DocumentClassification.fromConfidenceScore(score);
    }

    /**
     * Gets the file name of the document from the storage path
     * 
     * @return the file name, or the full path if parsing fails
     */
    public String getFileName() {
        if (storagePath == null || storagePath.isEmpty()) {
            return "";
        }
        
        int lastSlashIndex = storagePath.lastIndexOf('/');
        if (lastSlashIndex >= 0 && lastSlashIndex < storagePath.length() - 1) {
            return storagePath.substring(lastSlashIndex + 1);
        }
        
        return storagePath;
    }

    /**
     * Gets the file extension of the document
     * 
     * @return the file extension, or an empty string if not available
     */
    public String getFileExtension() {
        String fileName = getFileName();
        int lastDotIndex = fileName.lastIndexOf('.');
        
        if (lastDotIndex > 0 && lastDotIndex < fileName.length() - 1) {
            return fileName.substring(lastDotIndex + 1).toLowerCase();
        }
        
        return "";
    }

    /**
     * Gets the MIME type of the document based on its file extension
     * 
     * @return the MIME type, or "application/octet-stream" if not determinable
     */
    public String getMimeType() {
        String extension = getFileExtension();
        
        switch (extension) {
            case "pdf":
                return "application/pdf";
            case "jpg":
            case "jpeg":
                return "image/jpeg";
            case "png":
                return "image/png";
            case "tiff":
            case "tif":
                return "image/tiff";
            case "doc":
                return "application/msword";
            case "docx":
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "xls":
                return "application/vnd.ms-excel";
            case "xlsx":
                return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            default:
                return "application/octet-stream";
        }
    }

    /**
     * Checks if this document requires manual review based on its classification
     * 
     * @return true if the document requires manual review
     */
    public boolean requiresManualReview() {
        return classification != null && classification.requiresManualReview();
    }

    /**
     * Checks if this document is acceptable for processing based on its classification
     * 
     * @return true if the document is acceptable for processing
     */
    public boolean isAcceptable() {
        return classification != null && classification.isAcceptable();
    }

    /**
     * Gets the S3 bucket name from the storage path
     * 
     * @return the bucket name, or an empty string if parsing fails
     */
    public String getBucketName() {
        if (storagePath == null || storagePath.isEmpty()) {
            return "";
        }
        
        int firstSlashIndex = storagePath.indexOf('/');
        if (firstSlashIndex > 0) {
            return storagePath.substring(0, firstSlashIndex);
        }
        
        return "";
    }

    /**
     * Gets the S3 object key from the storage path
     * 
     * @return the object key, or the full path if parsing fails
     */
    public String getObjectKey() {
        if (storagePath == null || storagePath.isEmpty()) {
            return "";
        }
        
        int firstSlashIndex = storagePath.indexOf('/');
        if (firstSlashIndex > 0 && firstSlashIndex < storagePath.length() - 1) {
            return storagePath.substring(firstSlashIndex + 1);
        }
        
        return storagePath;
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
                ", fileName=" + getFileName() +
                ", classification=" + classification +
                ", uploadedAt=" + uploadedAt +
                ", confidenceScore=" + getConfidenceScore() +
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
        private DocumentClassification classification = DocumentClassification.UNCLASSIFIED;
        private LocalDateTime uploadedAt = LocalDateTime.now();
        private Map<String, Object> metadata = new HashMap<>();

        public Builder(UUID applicationId, DocumentType type, String storagePath) {
            this.applicationId = applicationId;
            this.type = type;
            this.storagePath = storagePath;
        }

        public Builder withClassification(DocumentClassification classification) {
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
            this.metadata.put(key, value);
            return this;
        }

        public Builder withConfidenceScore(double score) {
            this.metadata.put("confidenceScore", score);
            this.classification = DocumentClassification.fromConfidenceScore(score);
            return this;
        }

        public Document build() {
            return new Document(applicationId, type, storagePath, classification, uploadedAt, metadata);
        }
    }
}