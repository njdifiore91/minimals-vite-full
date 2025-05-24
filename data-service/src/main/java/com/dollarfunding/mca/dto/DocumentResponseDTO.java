package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * DTO class for returning document metadata to clients.
 * 
 * This class includes all document fields (id, application_id, type, storage_path, 
 * classification, uploaded_at, metadata) along with a pre-signed URL for secure 
 * document access. It provides a complete view of a document with appropriate 
 * serialization for API responses.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentResponseDTO {

    /**
     * Unique identifier for the document
     */
    @JsonProperty("id")
    private UUID id;

    /**
     * ID of the application this document belongs to
     */
    @JsonProperty("application_id")
    private UUID applicationId;

    /**
     * Type of document (e.g., BANK_STATEMENT, TAX_RETURN, etc.)
     */
    @JsonProperty("type")
    private String type;

    /**
     * Path to the document in S3-compatible storage
     * This is not exposed directly to clients for security reasons
     */
    @JsonProperty("storage_path")
    private String storagePath;

    /**
     * Document classification determined by the Document Service
     */
    @JsonProperty("classification")
    private String classification;

    /**
     * Timestamp when the document was uploaded
     */
    @JsonProperty("uploaded_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime uploadedAt;

    /**
     * Document metadata including OCR extraction results, confidence scores, etc.
     */
    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * Pre-signed URL for secure document access
     * This URL is time-limited and provides temporary access to the document
     */
    @JsonProperty("download_url")
    private String downloadUrl;

    /**
     * Expiration time for the pre-signed URL
     */
    @JsonProperty("url_expires_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime urlExpiresAt;

    /**
     * Classification confidence score (0.0-1.0)
     */
    @JsonProperty("classification_confidence")
    private Double classificationConfidence;

    /**
     * Default constructor
     */
    public DocumentResponseDTO() {
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor from Document entity
     * 
     * @param document The Document entity to convert
     * @param downloadUrl The pre-signed URL for document access
     * @param urlExpiresAt The expiration time for the pre-signed URL
     */
    public DocumentResponseDTO(Document document, String downloadUrl, LocalDateTime urlExpiresAt) {
        this.id = document.getId();
        this.applicationId = document.getApplicationId();
        this.type = document.getType() != null ? document.getType().name() : null;
        this.storagePath = document.getStoragePath();
        this.classification = document.getClassification();
        this.uploadedAt = document.getUploadedAt();
        this.metadata = document.getMetadata();
        this.downloadUrl = downloadUrl;
        this.urlExpiresAt = urlExpiresAt;
        
        // Extract classification confidence from metadata if available
        this.classificationConfidence = document.getConfidenceScore("classification");
    }

    /**
     * Static factory method to create a DTO from a Document entity
     * 
     * @param document The Document entity to convert
     * @param downloadUrl The pre-signed URL for document access
     * @param urlExpiresAt The expiration time for the pre-signed URL
     * @return A new DocumentResponseDTO instance
     */
    public static DocumentResponseDTO fromEntity(Document document, String downloadUrl, LocalDateTime urlExpiresAt) {
        if (document == null) {
            return null;
        }
        return new DocumentResponseDTO(document, downloadUrl, urlExpiresAt);
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
     * @return the document type as a string
     */
    public String getType() {
        return type;
    }

    /**
     * @param type the document type to set
     */
    public void setType(String type) {
        this.type = type;
    }

    /**
     * @param type the document type to set as enum
     */
    public void setType(DocumentType type) {
        this.type = type != null ? type.name() : null;
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
        return metadata;
    }

    /**
     * @param metadata the document metadata to set
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata != null ? metadata : new HashMap<>();
    }

    /**
     * @return the pre-signed URL for document access
     */
    public String getDownloadUrl() {
        return downloadUrl;
    }

    /**
     * @param downloadUrl the pre-signed URL to set
     */
    public void setDownloadUrl(String downloadUrl) {
        this.downloadUrl = downloadUrl;
    }

    /**
     * @return the expiration time for the pre-signed URL
     */
    public LocalDateTime getUrlExpiresAt() {
        return urlExpiresAt;
    }

    /**
     * @param urlExpiresAt the URL expiration time to set
     */
    public void setUrlExpiresAt(LocalDateTime urlExpiresAt) {
        this.urlExpiresAt = urlExpiresAt;
    }

    /**
     * @return the classification confidence score
     */
    public Double getClassificationConfidence() {
        return classificationConfidence;
    }

    /**
     * @param classificationConfidence the classification confidence score to set
     */
    public void setClassificationConfidence(Double classificationConfidence) {
        this.classificationConfidence = classificationConfidence;
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
        if (metadata == null) {
            return null;
        }
        return (T) metadata.get(key);
    }

    /**
     * Gets the confidence scores from the metadata
     * 
     * @return the confidence scores, or an empty map if not available
     */
    @SuppressWarnings("unchecked")
    public Map<String, Double> getConfidenceScores() {
        if (metadata == null || !metadata.containsKey("confidenceScores")) {
            return new HashMap<>();
        }
        return (Map<String, Double>) metadata.get("confidenceScores");
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
     * Checks if the document has a valid download URL
     * 
     * @return true if the document has a valid download URL
     */
    public boolean hasValidDownloadUrl() {
        return downloadUrl != null && !downloadUrl.isEmpty() && urlExpiresAt != null && 
               urlExpiresAt.isAfter(LocalDateTime.now());
    }

    /**
     * Checks if the document has high classification confidence
     * 
     * @return true if the document has high classification confidence
     */
    public boolean hasHighClassificationConfidence() {
        return classificationConfidence != null && classificationConfidence >= 0.9;
    }

    /**
     * Checks if the document has medium classification confidence
     * 
     * @return true if the document has medium classification confidence
     */
    public boolean hasMediumClassificationConfidence() {
        return classificationConfidence != null && 
               classificationConfidence >= 0.7 && 
               classificationConfidence < 0.9;
    }

    /**
     * Checks if the document has low classification confidence
     * 
     * @return true if the document has low classification confidence
     */
    public boolean hasLowClassificationConfidence() {
        return classificationConfidence != null && classificationConfidence < 0.7;
    }

    /**
     * Builder class for creating DocumentResponseDTO instances
     */
    public static class Builder {
        private UUID id;
        private UUID applicationId;
        private String type;
        private String storagePath;
        private String classification;
        private LocalDateTime uploadedAt;
        private Map<String, Object> metadata;
        private String downloadUrl;
        private LocalDateTime urlExpiresAt;
        private Double classificationConfidence;

        public Builder() {
            this.metadata = new HashMap<>();
        }

        public Builder(Document document) {
            this.id = document.getId();
            this.applicationId = document.getApplicationId();
            this.type = document.getType() != null ? document.getType().name() : null;
            this.storagePath = document.getStoragePath();
            this.classification = document.getClassification();
            this.uploadedAt = document.getUploadedAt();
            this.metadata = document.getMetadata();
            this.classificationConfidence = document.getConfidenceScore("classification");
        }

        public Builder withId(UUID id) {
            this.id = id;
            return this;
        }

        public Builder withApplicationId(UUID applicationId) {
            this.applicationId = applicationId;
            return this;
        }

        public Builder withType(String type) {
            this.type = type;
            return this;
        }

        public Builder withType(DocumentType type) {
            this.type = type != null ? type.name() : null;
            return this;
        }

        public Builder withStoragePath(String storagePath) {
            this.storagePath = storagePath;
            return this;
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

        public Builder withDownloadUrl(String downloadUrl) {
            this.downloadUrl = downloadUrl;
            return this;
        }

        public Builder withUrlExpiresAt(LocalDateTime urlExpiresAt) {
            this.urlExpiresAt = urlExpiresAt;
            return this;
        }

        public Builder withClassificationConfidence(Double classificationConfidence) {
            this.classificationConfidence = classificationConfidence;
            return this;
        }

        public DocumentResponseDTO build() {
            DocumentResponseDTO dto = new DocumentResponseDTO();
            dto.setId(id);
            dto.setApplicationId(applicationId);
            dto.setType(type);
            dto.setStoragePath(storagePath);
            dto.setClassification(classification);
            dto.setUploadedAt(uploadedAt);
            dto.setMetadata(metadata);
            dto.setDownloadUrl(downloadUrl);
            dto.setUrlExpiresAt(urlExpiresAt);
            dto.setClassificationConfidence(classificationConfidence);
            return dto;
        }
    }
}