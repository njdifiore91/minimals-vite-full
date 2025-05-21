package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * Model class for document processing messages consumed from RabbitMQ.
 * It defines the structure of messages received from the OCR Service containing extracted document data.
 * This class includes fields for document metadata, extracted field values with confidence scores,
 * and processing instructions.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DocumentProcessingMessage {

    /**
     * Enum defining the possible processing types for document messages.
     */
    public enum ProcessingType {
        NEW_APPLICATION,
        UPDATE_EXISTING,
        SUPPORTING_DOCUMENT
    }

    @JsonProperty("document_id")
    private String documentId;

    @JsonProperty("application_id")
    private String applicationId;

    @JsonProperty("document_type")
    private DocumentType documentType;

    @JsonProperty("classification")
    private String classification;

    @JsonProperty("classification_confidence")
    private Double classificationConfidence;

    @JsonProperty("storage_path")
    private String storagePath;

    @JsonProperty("extracted_data")
    private Map<String, Object> extractedData;

    @JsonProperty("field_confidence_scores")
    private Map<String, Double> fieldConfidenceScores;

    @JsonProperty("processing_type")
    private ProcessingType processingType;

    @JsonProperty("processing_timestamp")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS")
    private LocalDateTime processingTimestamp;

    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * Default constructor for Jackson deserialization.
     */
    public DocumentProcessingMessage() {
    }

    /**
     * Constructor with required fields.
     *
     * @param documentId              The unique identifier of the document
     * @param documentType            The type of document
     * @param extractedData           The data extracted from the document
     * @param processingType          The type of processing to perform
     */
    public DocumentProcessingMessage(String documentId, DocumentType documentType, 
                                    Map<String, Object> extractedData, ProcessingType processingType) {
        this.documentId = documentId;
        this.documentType = documentType;
        this.extractedData = extractedData;
        this.processingType = processingType;
        this.processingTimestamp = LocalDateTime.now();
    }

    /**
     * Gets the document ID.
     *
     * @return The document ID
     */
    public String getDocumentId() {
        return documentId;
    }

    /**
     * Sets the document ID.
     *
     * @param documentId The document ID
     */
    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    /**
     * Gets the application ID.
     *
     * @return The application ID
     */
    public String getApplicationId() {
        return applicationId;
    }

    /**
     * Sets the application ID.
     *
     * @param applicationId The application ID
     */
    public void setApplicationId(String applicationId) {
        this.applicationId = applicationId;
    }

    /**
     * Gets the document type.
     *
     * @return The document type
     */
    public DocumentType getDocumentType() {
        return documentType;
    }

    /**
     * Sets the document type.
     *
     * @param documentType The document type
     */
    public void setDocumentType(DocumentType documentType) {
        this.documentType = documentType;
    }

    /**
     * Gets the document classification.
     *
     * @return The document classification
     */
    public String getClassification() {
        return classification;
    }

    /**
     * Sets the document classification.
     *
     * @param classification The document classification
     */
    public void setClassification(String classification) {
        this.classification = classification;
    }

    /**
     * Gets the classification confidence score.
     *
     * @return The classification confidence score
     */
    public Double getClassificationConfidence() {
        return classificationConfidence;
    }

    /**
     * Sets the classification confidence score.
     *
     * @param classificationConfidence The classification confidence score
     */
    public void setClassificationConfidence(Double classificationConfidence) {
        this.classificationConfidence = classificationConfidence;
    }

    /**
     * Gets the storage path in S3.
     *
     * @return The storage path
     */
    public String getStoragePath() {
        return storagePath;
    }

    /**
     * Sets the storage path in S3.
     *
     * @param storagePath The storage path
     */
    public void setStoragePath(String storagePath) {
        this.storagePath = storagePath;
    }

    /**
     * Gets the extracted data from the document.
     *
     * @return The extracted data
     */
    public Map<String, Object> getExtractedData() {
        return extractedData;
    }

    /**
     * Sets the extracted data from the document.
     *
     * @param extractedData The extracted data
     */
    public void setExtractedData(Map<String, Object> extractedData) {
        this.extractedData = extractedData;
    }

    /**
     * Gets the confidence scores for extracted fields.
     *
     * @return The field confidence scores
     */
    public Map<String, Double> getFieldConfidenceScores() {
        return fieldConfidenceScores;
    }

    /**
     * Sets the confidence scores for extracted fields.
     *
     * @param fieldConfidenceScores The field confidence scores
     */
    public void setFieldConfidenceScores(Map<String, Double> fieldConfidenceScores) {
        this.fieldConfidenceScores = fieldConfidenceScores;
    }

    /**
     * Gets the processing type.
     *
     * @return The processing type
     */
    public ProcessingType getProcessingType() {
        return processingType;
    }

    /**
     * Sets the processing type.
     *
     * @param processingType The processing type
     */
    public void setProcessingType(ProcessingType processingType) {
        this.processingType = processingType;
    }

    /**
     * Gets the processing timestamp.
     *
     * @return The processing timestamp
     */
    public LocalDateTime getProcessingTimestamp() {
        return processingTimestamp;
    }

    /**
     * Sets the processing timestamp.
     *
     * @param processingTimestamp The processing timestamp
     */
    public void setProcessingTimestamp(LocalDateTime processingTimestamp) {
        this.processingTimestamp = processingTimestamp;
    }

    /**
     * Gets the metadata.
     *
     * @return The metadata
     */
    public Map<String, Object> getMetadata() {
        return metadata;
    }

    /**
     * Sets the metadata.
     *
     * @param metadata The metadata
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    @Override
    public String toString() {
        return "DocumentProcessingMessage{" +
                "documentId='" + documentId + '\'' +
                ", applicationId='" + applicationId + '\'' +
                ", documentType=" + documentType +
                ", classification='" + classification + '\'' +
                ", classificationConfidence=" + classificationConfidence +
                ", processingType=" + processingType +
                ", processingTimestamp=" + processingTimestamp +
                '}';
    }
}