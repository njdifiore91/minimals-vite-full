package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Data Transfer Object (DTO) representing a document processing message received from RabbitMQ.
 * 
 * This class encapsulates the data extracted from documents by the OCR Service and sent to
 * the Data Service for processing. It includes document metadata, extracted field data,
 * and confidence scores for the extraction process.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DocumentProcessingMessage {

    /**
     * Unique identifier for the document being processed
     */
    @NotNull
    @JsonProperty("document_id")
    private UUID documentId;

    /**
     * Identifier for the application this document belongs to, if known
     * May be null for new documents that haven't been associated with an application yet
     */
    @JsonProperty("application_id")
    private UUID applicationId;

    /**
     * Type of document (e.g., BANK_STATEMENT, TAX_RETURN, etc.)
     */
    @NotNull
    @JsonProperty("document_type")
    private String documentType;

    /**
     * More specific classification of the document determined by the Document Service
     */
    @JsonProperty("classification")
    private String classification;

    /**
     * Path to the document in S3-compatible storage
     */
    @NotNull
    @JsonProperty("storage_path")
    private String storagePath;

    /**
     * Path to the extracted data JSON file in S3-compatible storage
     */
    @JsonProperty("extracted_data_path")
    private String extractedDataPath;

    /**
     * Map containing the extracted data from the document
     * Keys are field names, values are the extracted values
     */
    @JsonProperty("extracted_data")
    private Map<String, Object> extractedData;

    /**
     * Map containing confidence scores for each extracted field
     * Keys are field names, values are confidence scores (0.0-1.0)
     */
    @JsonProperty("confidence_scores")
    private Map<String, Double> confidenceScores;

    /**
     * Timestamp when the document was processed by the OCR Service
     */
    @NotNull
    @JsonProperty("processed_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS")
    private LocalDateTime processedAt;

    /**
     * Additional metadata about the document and processing
     */
    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * Default constructor required for Jackson deserialization
     */
    public DocumentProcessingMessage() {
        this.extractedData = new HashMap<>();
        this.confidenceScores = new HashMap<>();
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor with required fields
     * 
     * @param documentId Unique identifier for the document
     * @param documentType Type of document
     * @param storagePath Path to the document in S3-compatible storage
     * @param processedAt Timestamp when the document was processed
     */
    public DocumentProcessingMessage(UUID documentId, String documentType, String storagePath, LocalDateTime processedAt) {
        this();
        this.documentId = documentId;
        this.documentType = documentType;
        this.storagePath = storagePath;
        this.processedAt = processedAt;
    }

    /**
     * @return the document ID
     */
    public UUID getDocumentId() {
        return documentId;
    }

    /**
     * @param documentId the document ID to set
     */
    public void setDocumentId(UUID documentId) {
        this.documentId = documentId;
    }

    /**
     * @return the application ID, may be null
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
    public String getDocumentType() {
        return documentType;
    }

    /**
     * @param documentType the document type to set
     */
    public void setDocumentType(String documentType) {
        this.documentType = documentType;
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
     * @return the storage path
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
     * @return the extracted data path
     */
    public String getExtractedDataPath() {
        return extractedDataPath;
    }

    /**
     * @param extractedDataPath the extracted data path to set
     */
    public void setExtractedDataPath(String extractedDataPath) {
        this.extractedDataPath = extractedDataPath;
    }

    /**
     * @return the extracted data map
     */
    public Map<String, Object> getExtractedData() {
        return extractedData;
    }

    /**
     * @param extractedData the extracted data map to set
     */
    public void setExtractedData(Map<String, Object> extractedData) {
        this.extractedData = extractedData != null ? extractedData : new HashMap<>();
    }

    /**
     * @return the confidence scores map
     */
    public Map<String, Double> getConfidenceScores() {
        return confidenceScores;
    }

    /**
     * @param confidenceScores the confidence scores map to set
     */
    public void setConfidenceScores(Map<String, Double> confidenceScores) {
        this.confidenceScores = confidenceScores != null ? confidenceScores : new HashMap<>();
    }

    /**
     * @return the processed timestamp
     */
    public LocalDateTime getProcessedAt() {
        return processedAt;
    }

    /**
     * @param processedAt the processed timestamp to set
     */
    public void setProcessedAt(LocalDateTime processedAt) {
        this.processedAt = processedAt;
    }

    /**
     * @return the metadata map
     */
    public Map<String, Object> getMetadata() {
        return metadata;
    }

    /**
     * @param metadata the metadata map to set
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata != null ? metadata : new HashMap<>();
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
     * Gets the average confidence score across all extracted fields
     * 
     * @return the average confidence score, or 0.0 if no scores are available
     */
    public double getAverageConfidenceScore() {
        if (confidenceScores == null || confidenceScores.isEmpty()) {
            return 0.0;
        }
        return confidenceScores.values().stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(0.0);
    }

    /**
     * Checks if this message contains a document with high confidence extraction
     * 
     * @param threshold the confidence threshold to check against (0.0-1.0)
     * @return true if the average confidence score is at or above the threshold
     */
    public boolean hasHighConfidence(double threshold) {
        return getAverageConfidenceScore() >= threshold;
    }

    /**
     * Checks if this message contains all required fields
     * 
     * @return true if all required fields are present
     */
    public boolean isValid() {
        return documentId != null && 
               documentType != null && !documentType.isEmpty() &&
               storagePath != null && !storagePath.isEmpty() &&
               processedAt != null;
    }

    /**
     * Returns a string representation of this message for debugging and logging
     * 
     * @return a string representation of this message
     */
    @Override
    public String toString() {
        return "DocumentProcessingMessage{" +
                "documentId=" + documentId +
                ", applicationId=" + applicationId +
                ", documentType='" + documentType + '\'' +
                ", classification='" + classification + '\'' +
                ", processedAt=" + processedAt +
                ", extractedDataFields=" + (extractedData != null ? extractedData.size() : 0) +
                ", avgConfidence=" + String.format("%.2f", getAverageConfidenceScore()) +
                "}";
    }

    /**
     * Builder class for creating DocumentProcessingMessage instances
     */
    public static class Builder {
        private UUID documentId;
        private UUID applicationId;
        private String documentType;
        private String classification;
        private String storagePath;
        private String extractedDataPath;
        private Map<String, Object> extractedData = new HashMap<>();
        private Map<String, Double> confidenceScores = new HashMap<>();
        private LocalDateTime processedAt;
        private Map<String, Object> metadata = new HashMap<>();

        public Builder withDocumentId(UUID documentId) {
            this.documentId = documentId;
            return this;
        }

        public Builder withApplicationId(UUID applicationId) {
            this.applicationId = applicationId;
            return this;
        }

        public Builder withDocumentType(String documentType) {
            this.documentType = documentType;
            return this;
        }

        public Builder withClassification(String classification) {
            this.classification = classification;
            return this;
        }

        public Builder withStoragePath(String storagePath) {
            this.storagePath = storagePath;
            return this;
        }

        public Builder withExtractedDataPath(String extractedDataPath) {
            this.extractedDataPath = extractedDataPath;
            return this;
        }

        public Builder withExtractedData(Map<String, Object> extractedData) {
            this.extractedData = extractedData;
            return this;
        }

        public Builder withConfidenceScores(Map<String, Double> confidenceScores) {
            this.confidenceScores = confidenceScores;
            return this;
        }

        public Builder withProcessedAt(LocalDateTime processedAt) {
            this.processedAt = processedAt;
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

        public DocumentProcessingMessage build() {
            DocumentProcessingMessage message = new DocumentProcessingMessage(documentId, documentType, storagePath, processedAt);
            message.setApplicationId(applicationId);
            message.setClassification(classification);
            message.setExtractedDataPath(extractedDataPath);
            message.setExtractedData(extractedData);
            message.setConfidenceScores(confidenceScores);
            message.setMetadata(metadata);
            return message;
        }
    }
}