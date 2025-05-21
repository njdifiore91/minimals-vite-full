package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Data Transfer Object for returning document metadata to clients.
 * Includes all document fields along with a pre-signed URL for secure document access.
 * This class provides a complete view of a document with appropriate serialization for API responses.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentResponseDTO {

    private UUID id;
    private UUID applicationId;
    private DocumentType type;
    private String storagePath;
    private String classification;
    
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime uploadedAt;
    
    private Map<String, Object> metadata;
    private String presignedUrl;
    private Map<String, Double> confidenceScores;

    /**
     * Default constructor for serialization frameworks
     */
    public DocumentResponseDTO() {
    }

    /**
     * Constructs a DocumentResponseDTO from a Document entity
     * 
     * @param document The Document entity to convert
     */
    public DocumentResponseDTO(Document document) {
        this.id = document.getId();
        this.applicationId = document.getApplicationId();
        this.type = document.getType();
        this.storagePath = document.getStoragePath();
        this.classification = document.getClassification();
        this.uploadedAt = document.getUploadedAt();
        this.metadata = document.getMetadata();
        
        // Extract confidence scores from metadata if available
        if (metadata != null && metadata.containsKey("confidenceScores")) {
            this.confidenceScores = (Map<String, Double>) metadata.get("confidenceScores");
        }
    }

    /**
     * Constructs a DocumentResponseDTO from a Document entity with a pre-signed URL
     * 
     * @param document The Document entity to convert
     * @param presignedUrl The pre-signed URL for secure document access
     */
    public DocumentResponseDTO(Document document, String presignedUrl) {
        this(document);
        this.presignedUrl = presignedUrl;
    }

    /**
     * Constructs a DocumentResponseDTO from a Document entity with a pre-signed URL and confidence scores
     * 
     * @param document The Document entity to convert
     * @param presignedUrl The pre-signed URL for secure document access
     * @param confidenceScores Map of field names to confidence scores
     */
    public DocumentResponseDTO(Document document, String presignedUrl, Map<String, Double> confidenceScores) {
        this(document, presignedUrl);
        this.confidenceScores = confidenceScores;
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
        return metadata;
    }

    /**
     * @param metadata the document metadata to set
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
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
     * @return the pre-signed URL for secure document access
     */
    public String getPresignedUrl() {
        return presignedUrl;
    }

    /**
     * @param presignedUrl the pre-signed URL to set
     */
    public void setPresignedUrl(String presignedUrl) {
        this.presignedUrl = presignedUrl;
    }

    /**
     * @return the confidence scores for document classification and field extraction
     */
    public Map<String, Double> getConfidenceScores() {
        return confidenceScores;
    }

    /**
     * @param confidenceScores the confidence scores to set
     */
    public void setConfidenceScores(Map<String, Double> confidenceScores) {
        this.confidenceScores = confidenceScores;
    }
    
    /**
     * Checks if this document has a specific confidence score
     * 
     * @param fieldName the field name to check
     * @return true if the document has a confidence score for the specified field
     */
    public boolean hasConfidenceScore(String fieldName) {
        return confidenceScores != null && confidenceScores.containsKey(fieldName);
    }
    
    /**
     * Gets the confidence score for a specific field
     * 
     * @param fieldName the field name to get the confidence score for
     * @return the confidence score, or null if not available
     */
    public Double getConfidenceScore(String fieldName) {
        if (confidenceScores == null) {
            return null;
        }
        return confidenceScores.get(fieldName);
    }
    
    /**
     * Checks if this document is of a specific type
     * 
     * @param documentType the document type to check
     * @return true if the document is of the specified type
     */
    public boolean isOfType(DocumentType documentType) {
        return this.type == documentType;
    }
    
    /**
     * Checks if this document has a valid pre-signed URL
     * 
     * @return true if the document has a valid pre-signed URL
     */
    public boolean hasValidPresignedUrl() {
        return presignedUrl != null && !presignedUrl.isEmpty();
    }
    
    /**
     * Checks if this document has metadata
     * 
     * @return true if the document has metadata
     */
    public boolean hasMetadata() {
        return metadata != null && !metadata.isEmpty();
    }
    
    /**
     * Checks if this document is valid for processing
     * 
     * @return true if the document is valid for processing
     */
    public boolean isValidForProcessing() {
        return id != null && 
               applicationId != null && 
               type != null && 
               storagePath != null && !storagePath.isEmpty() &&
               uploadedAt != null;
    }
    
    /**
     * Checks if this document is classified with high confidence
     * 
     * @param confidenceThreshold the minimum confidence threshold (0.0 to 1.0)
     * @return true if the document is classified with confidence above the threshold
     */
    public boolean isClassifiedWithHighConfidence(double confidenceThreshold) {
        if (confidenceScores == null || !confidenceScores.containsKey("classification")) {
            return false;
        }
        Double classificationConfidence = confidenceScores.get("classification");
        return classificationConfidence != null && classificationConfidence >= confidenceThreshold;
    }
    
    /**
     * Gets the age of this document in days
     * 
     * @return the age in days, or -1 if the upload date is not available
     */
    public long getAgeInDays() {
        if (uploadedAt == null) {
            return -1;
        }
        return ChronoUnit.DAYS.between(uploadedAt, LocalDateTime.now());
    }

    /**
     * Converts a list of Document entities to a list of DocumentResponseDTOs
     * 
     * @param documents the list of Document entities to convert
     * @return a list of DocumentResponseDTOs
     */
    public static List<DocumentResponseDTO> fromDocuments(List<Document> documents) {
        if (documents == null) {
            return List.of();
        }
        return documents.stream()
                .map(DocumentResponseDTO::new)
                .collect(Collectors.toList());
    }
    
    /**
     * Converts a list of Document entities to a list of DocumentResponseDTOs with pre-signed URLs
     * 
     * @param documents the list of Document entities to convert
     * @param presignedUrls a map of document IDs to pre-signed URLs
     * @return a list of DocumentResponseDTOs with pre-signed URLs
     */
    public static List<DocumentResponseDTO> fromDocumentsWithUrls(List<Document> documents, Map<UUID, String> presignedUrls) {
        if (documents == null) {
            return List.of();
        }
        return documents.stream()
                .map(doc -> new DocumentResponseDTO(doc, presignedUrls.get(doc.getId())))
                .collect(Collectors.toList());
    }
    
    /**
     * Returns a string representation of this DTO for debugging and logging
     * 
     * @return a string representation of this DTO
     */
    @Override
    public String toString() {
        return "DocumentResponseDTO{" +
                "id=" + id +
                ", applicationId=" + applicationId +
                ", type=" + type +
                ", classification='" + classification + '\'' +
                ", uploadedAt=" + uploadedAt +
                ", hasMetadata=" + hasMetadata() +
                ", hasPresignedUrl=" + hasValidPresignedUrl() +
                ", hasConfidenceScores=" + (confidenceScores != null && !confidenceScores.isEmpty()) +
                '}'; 
    }
    
    /**
     * Compares this DTO with another object for equality
     * 
     * @param o the object to compare with
     * @return true if the objects are equal
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        DocumentResponseDTO that = (DocumentResponseDTO) o;

        return id != null ? id.equals(that.id) : that.id == null;
    }

    /**
     * Returns a hash code for this DTO
     * 
     * @return a hash code value for this object
     */
    @Override
    public int hashCode() {
        return id != null ? id.hashCode() : 0;
    }
    
    /**
     * Builder class for creating DocumentResponseDTO instances
     */
    public static class Builder {
        private Document document;
        private String presignedUrl;
        private Map<String, Double> confidenceScores;

        public Builder(Document document) {
            this.document = document;
        }

        public Builder withPresignedUrl(String presignedUrl) {
            this.presignedUrl = presignedUrl;
            return this;
        }

        public Builder withConfidenceScores(Map<String, Double> confidenceScores) {
            this.confidenceScores = confidenceScores;
            return this;
        }

        public DocumentResponseDTO build() {
            if (confidenceScores != null) {
                return new DocumentResponseDTO(document, presignedUrl, confidenceScores);
            } else if (presignedUrl != null) {
                return new DocumentResponseDTO(document, presignedUrl);
            } else {
                return new DocumentResponseDTO(document);
            }
        }
    }
}