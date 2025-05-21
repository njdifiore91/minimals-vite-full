package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Data Transfer Object for document upload and update operations.
 * Defines the structure for incoming document metadata with validation annotations for required fields.
 * This class includes fields for document type, application association, and classification metadata.
 * It serves as the contract for document operations in the REST API.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonIgnoreProperties(ignoreUnknown = true)
public class DocumentRequestDTO {

    /**
     * The ID of the application this document belongs to.
     * Required for all document operations.
     */
    @NotNull(message = "Application ID is required")
    private UUID applicationId;

    /**
     * The type of document being uploaded or updated.
     * Required for document creation.
     */
    @NotNull(message = "Document type is required")
    private DocumentType type;

    /**
     * The classification of the document, if known.
     * Optional for document creation, as it may be determined by the Document Service.
     */
    private String classification;

    /**
     * Additional metadata for the document.
     * Optional for document creation.
     */
    private Map<String, Object> metadata = new HashMap<>();

    /**
     * Confidence scores for document classification and field extraction.
     * Optional for document creation, typically populated by the OCR Service.
     */
    private Map<String, Double> confidenceScores = new HashMap<>();

    /**
     * Original filename of the uploaded document.
     * Optional but recommended for document creation.
     */
    @Size(max = 255, message = "Filename cannot exceed 255 characters")
    private String originalFilename;

    /**
     * Content type of the uploaded document.
     * Optional but recommended for document creation.
     */
    @Size(max = 100, message = "Content type cannot exceed 100 characters")
    private String contentType;

    /**
     * Default constructor for serialization frameworks
     */
    public DocumentRequestDTO() {
    }

    /**
     * Constructor with required fields
     *
     * @param applicationId the ID of the application this document belongs to
     * @param type the type of document
     */
    public DocumentRequestDTO(UUID applicationId, DocumentType type) {
        this.applicationId = applicationId;
        this.type = type;
    }

    /**
     * Constructor with all fields
     *
     * @param applicationId the ID of the application this document belongs to
     * @param type the type of document
     * @param classification the classification of the document
     * @param metadata additional metadata for the document
     * @param confidenceScores confidence scores for document classification and field extraction
     * @param originalFilename original filename of the uploaded document
     * @param contentType content type of the uploaded document
     */
    public DocumentRequestDTO(UUID applicationId, DocumentType type, String classification,
                             Map<String, Object> metadata, Map<String, Double> confidenceScores,
                             String originalFilename, String contentType) {
        this.applicationId = applicationId;
        this.type = type;
        this.classification = classification;
        this.metadata = metadata != null ? metadata : new HashMap<>();
        this.confidenceScores = confidenceScores != null ? confidenceScores : new HashMap<>();
        this.originalFilename = originalFilename;
        this.contentType = contentType;
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
     * Adds a metadata entry to the document
     *
     * @param key the metadata key
     * @param value the metadata value
     * @return this DTO for method chaining
     */
    public DocumentRequestDTO addMetadata(String key, Object value) {
        if (this.metadata == null) {
            this.metadata = new HashMap<>();
        }
        this.metadata.put(key, value);
        return this;
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
        this.confidenceScores = confidenceScores != null ? confidenceScores : new HashMap<>();
    }

    /**
     * Adds a confidence score for a specific field
     *
     * @param fieldName the field name
     * @param confidenceScore the confidence score (0.0 to 1.0)
     * @return this DTO for method chaining
     */
    public DocumentRequestDTO addConfidenceScore(String fieldName, Double confidenceScore) {
        if (this.confidenceScores == null) {
            this.confidenceScores = new HashMap<>();
        }
        this.confidenceScores.put(fieldName, confidenceScore);
        return this;
    }

    /**
     * @return the original filename of the uploaded document
     */
    public String getOriginalFilename() {
        return originalFilename;
    }

    /**
     * @param originalFilename the original filename to set
     */
    public void setOriginalFilename(String originalFilename) {
        this.originalFilename = originalFilename;
    }

    /**
     * @return the content type of the uploaded document
     */
    public String getContentType() {
        return contentType;
    }

    /**
     * @param contentType the content type to set
     */
    public void setContentType(String contentType) {
        this.contentType = contentType;
    }

    /**
     * Validates if this DTO has all required fields for document creation
     *
     * @return true if the DTO has all required fields for document creation
     */
    public boolean isValidForCreation() {
        return applicationId != null && type != null;
    }

    /**
     * Validates if this DTO has all required fields for document update
     *
     * @param documentId the ID of the document being updated
     * @return true if the DTO has all required fields for document update
     */
    public boolean isValidForUpdate(UUID documentId) {
        return documentId != null && applicationId != null;
    }

    /**
     * Creates a copy of this DTO with additional metadata
     *
     * @param additionalMetadata additional metadata to add
     * @return a new DTO with combined metadata
     */
    public DocumentRequestDTO withAdditionalMetadata(Map<String, Object> additionalMetadata) {
        if (additionalMetadata == null || additionalMetadata.isEmpty()) {
            return this;
        }

        Map<String, Object> combinedMetadata = new HashMap<>(this.metadata);
        combinedMetadata.putAll(additionalMetadata);

        return new DocumentRequestDTO(
                this.applicationId,
                this.type,
                this.classification,
                combinedMetadata,
                this.confidenceScores,
                this.originalFilename,
                this.contentType
        );
    }

    /**
     * Creates a copy of this DTO with additional confidence scores
     *
     * @param additionalScores additional confidence scores to add
     * @return a new DTO with combined confidence scores
     */
    public DocumentRequestDTO withAdditionalConfidenceScores(Map<String, Double> additionalScores) {
        if (additionalScores == null || additionalScores.isEmpty()) {
            return this;
        }

        Map<String, Double> combinedScores = new HashMap<>(this.confidenceScores);
        combinedScores.putAll(additionalScores);

        return new DocumentRequestDTO(
                this.applicationId,
                this.type,
                this.classification,
                this.metadata,
                combinedScores,
                this.originalFilename,
                this.contentType
        );
    }

    /**
     * Returns a string representation of this DTO for debugging and logging
     *
     * @return a string representation of this DTO
     */
    @Override
    public String toString() {
        return "DocumentRequestDTO{" +
                "applicationId=" + applicationId +
                ", type=" + type +
                ", classification='" + classification + '\'' +
                ", hasMetadata=" + (metadata != null && !metadata.isEmpty()) +
                ", hasConfidenceScores=" + (confidenceScores != null && !confidenceScores.isEmpty()) +
                ", originalFilename='" + originalFilename + '\'' +
                ", contentType='" + contentType + '\'' +
                '}';
    }

    /**
     * Builder class for creating DocumentRequestDTO instances
     */
    public static class Builder {
        private UUID applicationId;
        private DocumentType type;
        private String classification;
        private Map<String, Object> metadata = new HashMap<>();
        private Map<String, Double> confidenceScores = new HashMap<>();
        private String originalFilename;
        private String contentType;

        public Builder(UUID applicationId, DocumentType type) {
            this.applicationId = applicationId;
            this.type = type;
        }

        public Builder withClassification(String classification) {
            this.classification = classification;
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

        public Builder withConfidenceScores(Map<String, Double> confidenceScores) {
            this.confidenceScores = confidenceScores;
            return this;
        }

        public Builder addConfidenceScore(String fieldName, Double confidenceScore) {
            this.confidenceScores.put(fieldName, confidenceScore);
            return this;
        }

        public Builder withOriginalFilename(String originalFilename) {
            this.originalFilename = originalFilename;
            return this;
        }

        public Builder withContentType(String contentType) {
            this.contentType = contentType;
            return this;
        }

        public DocumentRequestDTO build() {
            return new DocumentRequestDTO(
                    applicationId,
                    type,
                    classification,
                    metadata,
                    confidenceScores,
                    originalFilename,
                    contentType
            );
        }
    }
}