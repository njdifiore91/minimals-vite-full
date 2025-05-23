package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Data Transfer Object for document upload and update operations.
 * 
 * This class defines the structure for incoming document metadata with validation
 * annotations for required fields. It includes fields for document type, application
 * association, and classification metadata. It serves as the contract for document
 * operations in the REST API.
 * 
 * Used for both document creation and update operations, with appropriate validation
 * rules for each field. For updates, only the fields that are provided will be updated.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentRequestDTO {

    /**
     * The ID of the application this document belongs to.
     * Required for document creation.
     */
    @NotNull(message = "Application ID is required")
    @JsonProperty("application_id")
    private UUID applicationId;

    /**
     * The type of document being uploaded.
     * Required for document creation.
     */
    @NotNull(message = "Document type is required")
    private DocumentType type;

    /**
     * Optional document classification.
     * If not provided, will be determined by the Document Service.
     */
    private String classification;

    /**
     * Optional metadata for the document.
     * Can include any additional information about the document.
     */
    @JsonInclude(JsonInclude.Include.NON_EMPTY)
    private Map<String, Object> metadata;

    /**
     * Original filename of the uploaded document.
     * Used for reference and display purposes.
     */
    @Size(max = 255, message = "Filename cannot exceed 255 characters")
    private String filename;

    /**
     * Content type of the document (e.g., application/pdf, image/jpeg).
     * Used for proper handling and display of the document.
     */
    @Pattern(regexp = "^[a-zA-Z0-9/\\-+.]+$", message = "Invalid content type format")
    @JsonProperty("content_type")
    private String contentType;

    /**
     * Flag indicating if the document contains personally identifiable information (PII).
     * Used for applying appropriate security measures.
     */
    @JsonProperty("contains_pii")
    private Boolean containsPii;

    /**
     * Flag indicating if the document is a financial document.
     * Used for applying appropriate processing rules.
     */
    @JsonProperty("is_financial")
    private Boolean isFinancial;

    /**
     * Base64-encoded content of the document for direct API uploads.
     * Not used when uploading via multipart form data.
     */
    @JsonProperty("content")
    private String base64Content;

    /**
     * Confidence score for document classification (0.0-1.0).
     * Used when classification is provided by the client.
     */
    @JsonProperty("classification_confidence")
    private Double classificationConfidence;

    /**
     * Default constructor
     */
    public DocumentRequestDTO() {
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor with required fields
     * 
     * @param applicationId The ID of the application this document belongs to
     * @param type The type of document
     */
    public DocumentRequestDTO(UUID applicationId, DocumentType type) {
        this.applicationId = applicationId;
        this.type = type;
        this.metadata = new HashMap<>();
    }

    /**
     * @return the application ID
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
     * @return the original filename
     */
    public String getFilename() {
        return filename;
    }

    /**
     * @param filename the original filename to set
     */
    public void setFilename(String filename) {
        this.filename = filename;
    }

    /**
     * @return the content type
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
     * @return whether the document contains PII
     */
    public Boolean getContainsPii() {
        return containsPii;
    }

    /**
     * @param containsPii whether the document contains PII
     */
    public void setContainsPii(Boolean containsPii) {
        this.containsPii = containsPii;
    }

    /**
     * @return whether the document is financial
     */
    public Boolean getIsFinancial() {
        return isFinancial;
    }

    /**
     * @param isFinancial whether the document is financial
     */
    public void setIsFinancial(Boolean isFinancial) {
        this.isFinancial = isFinancial;
    }

    /**
     * @return the base64-encoded content
     */
    public String getBase64Content() {
        return base64Content;
    }

    /**
     * @param base64Content the base64-encoded content to set
     */
    public void setBase64Content(String base64Content) {
        this.base64Content = base64Content;
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
     * Adds a metadata key-value pair
     * 
     * @param key the metadata key
     * @param value the metadata value
     */
    public void addMetadata(String key, Object value) {
        if (this.metadata == null) {
            this.metadata = new HashMap<>();
        }
        this.metadata.put(key, value);
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
        if (this.metadata == null) {
            return null;
        }
        return (T) this.metadata.get(key);
    }

    /**
     * Checks if the document has metadata
     * 
     * @return true if the document has metadata
     */
    @JsonIgnore
    public boolean hasMetadata() {
        return this.metadata != null && !this.metadata.isEmpty();
    }

    /**
     * Checks if the document has base64 content
     * 
     * @return true if the document has base64 content
     */
    @JsonIgnore
    public boolean hasBase64Content() {
        return this.base64Content != null && !this.base64Content.isEmpty();
    }

    /**
     * Checks if this request contains the minimum required fields for document creation
     * 
     * @return true if the request is valid for document creation
     */
    @JsonIgnore
    public boolean isValidForCreation() {
        return this.applicationId != null && this.type != null;
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
        if (this.metadata == null) {
            this.metadata = new HashMap<>();
        }
        this.metadata.put("confidenceScores", confidenceScores);
    }

    /**
     * Gets the confidence scores from the metadata
     * 
     * @return the confidence scores, or an empty map if not available
     */
    @SuppressWarnings("unchecked")
    @JsonIgnore
    public Map<String, Double> getConfidenceScores() {
        if (this.metadata == null || !this.metadata.containsKey("confidenceScores")) {
            return new HashMap<>();
        }
        return (Map<String, Double>) this.metadata.get("confidenceScores");
    }

    /**
     * Builder class for creating DocumentRequestDTO instances
     */
    public static class Builder {
        private UUID applicationId;
        private DocumentType type;
        private String classification;
        private Map<String, Object> metadata = new HashMap<>();
        private String filename;
        private String contentType;
        private Boolean containsPii;
        private Boolean isFinancial;
        private String base64Content;
        private Double classificationConfidence;

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

        public Builder withFilename(String filename) {
            this.filename = filename;
            return this;
        }

        public Builder withContentType(String contentType) {
            this.contentType = contentType;
            return this;
        }

        public Builder withContainsPii(Boolean containsPii) {
            this.containsPii = containsPii;
            return this;
        }

        public Builder withIsFinancial(Boolean isFinancial) {
            this.isFinancial = isFinancial;
            return this;
        }

        public Builder withBase64Content(String base64Content) {
            this.base64Content = base64Content;
            return this;
        }

        public Builder withClassificationConfidence(Double classificationConfidence) {
            this.classificationConfidence = classificationConfidence;
            return this;
        }

        public Builder addMetadata(String key, Object value) {
            this.metadata.put(key, value);
            return this;
        }

        public Builder addConfidenceScores(Map<String, Double> confidenceScores) {
            if (confidenceScores != null && !confidenceScores.isEmpty()) {
                this.metadata.put("confidenceScores", confidenceScores);
            }
            return this;
        }

        public DocumentRequestDTO build() {
            DocumentRequestDTO dto = new DocumentRequestDTO();
            dto.setApplicationId(applicationId);
            dto.setType(type);
            dto.setClassification(classification);
            dto.setMetadata(metadata);
            dto.setFilename(filename);
            dto.setContentType(contentType);
            dto.setContainsPii(containsPii);
            dto.setIsFinancial(isFinancial);
            dto.setBase64Content(base64Content);
            dto.setClassificationConfidence(classificationConfidence);
            return dto;
        }
    }
}