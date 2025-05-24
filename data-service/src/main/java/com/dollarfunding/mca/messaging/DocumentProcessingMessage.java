package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * Model class for document processing messages consumed from RabbitMQ.
 * 
 * This class defines the structure of messages received from the OCR Service containing
 * extracted document data. It includes fields for document metadata, extracted field values
 * with confidence scores, and processing instructions.
 * 
 * The Data Service consumes these messages from the RabbitMQ queue, processes the extracted
 * document data, and updates the application state accordingly.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentProcessingMessage {

    /**
     * Unique identifier for the message.
     */
    @NotBlank(message = "Message ID is required")
    @Pattern(regexp = "^[a-zA-Z0-9\\-]+$", message = "Message ID must contain only alphanumeric characters and hyphens")
    @JsonProperty("message_id")
    private String messageId;

    /**
     * ID of the document being processed.
     */
    @NotBlank(message = "Document ID is required")
    @Pattern(regexp = "^[a-zA-Z0-9\\-]+$", message = "Document ID must contain only alphanumeric characters and hyphens")
    @JsonProperty("document_id")
    private String documentId;

    /**
     * Type of document (application_form, tax_return, etc.).
     */
    @NotNull(message = "Document type is required")
    @JsonProperty("document_type")
    private DocumentType documentType;

    /**
     * ID of the application this document belongs to.
     * May be null for documents not yet associated with an application.
     */
    @Pattern(regexp = "^[a-zA-Z0-9\\-]+$", message = "Application ID must contain only alphanumeric characters and hyphens")
    @JsonProperty("application_id")
    private String applicationId;

    /**
     * S3 storage path for the document.
     */
    @NotBlank(message = "Storage path is required")
    @Size(max = 1024, message = "Storage path cannot exceed 1024 characters")
    @JsonProperty("storage_path")
    private String storagePath;

    /**
     * MIME type of the document.
     */
    @NotBlank(message = "Content type is required")
    @Size(max = 255, message = "Content type cannot exceed 255 characters")
    @JsonProperty("content_type")
    private String contentType;

    /**
     * ISO 8601 timestamp when the message was created.
     */
    @NotNull(message = "Timestamp is required")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSSXXX")
    @JsonProperty("timestamp")
    private LocalDateTime timestamp;

    /**
     * Service that published the message (typically "ocr-service").
     */
    @NotBlank(message = "Source service is required")
    @Size(max = 255, message = "Source service cannot exceed 255 characters")
    @JsonProperty("source_service")
    private String sourceService;

    /**
     * Processing status of the document.
     */
    @NotBlank(message = "Status is required")
    @Pattern(regexp = "^(received|processing|completed|failed|pending_verification)$", 
             message = "Status must be one of: received, processing, completed, failed, pending_verification")
    @JsonProperty("status")
    private String status;

    /**
     * Additional document metadata.
     * This may include classification confidence, page count, etc.
     */
    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * OCR extraction results.
     * This contains the structured data extracted from the document.
     * The structure varies based on document type.
     */
    @JsonProperty("extraction_results")
    private Map<String, Object> extractionResults;

    /**
     * Confidence scores for extracted fields.
     * Maps field names to confidence scores (0.0-1.0).
     */
    @JsonProperty("confidence_scores")
    private Map<String, Float> confidenceScores;

    /**
     * Error information if processing failed.
     */
    @JsonProperty("error")
    private Map<String, Object> error;

    /**
     * Processing time in milliseconds.
     */
    @JsonProperty("processing_time_ms")
    private Float processingTimeMs;

    /**
     * Whether human verification is required.
     */
    @JsonProperty("requires_verification")
    private Boolean requiresVerification;

    /**
     * Fields requiring verification.
     * List of field names that have low confidence scores and require human verification.
     */
    @JsonProperty("verification_fields")
    private List<String> verificationFields;

    /**
     * Checks if this message indicates a new application should be created.
     * 
     * @return true if this document should create a new application, false otherwise
     */
    public boolean isNewApplication() {
        // If this is a loan application document and no application ID is provided,
        // it should create a new application
        return DocumentType.LOAN_APPLICATION.equals(documentType) && 
               (applicationId == null || applicationId.isEmpty());
    }

    /**
     * Checks if this message requires human verification.
     * 
     * @return true if human verification is required, false otherwise
     */
    public boolean requiresHumanVerification() {
        return Boolean.TRUE.equals(requiresVerification) || 
               "pending_verification".equals(status);
    }

    /**
     * Gets the average confidence score across all extracted fields.
     * 
     * @return the average confidence score, or null if no confidence scores are available
     */
    public Float getAverageConfidenceScore() {
        if (confidenceScores == null || confidenceScores.isEmpty()) {
            return null;
        }
        
        return (float) confidenceScores.values().stream()
                .mapToDouble(Float::doubleValue)
                .average()
                .orElse(0.0);
    }

    /**
     * Gets the lowest confidence score among all extracted fields.
     * 
     * @return the lowest confidence score, or null if no confidence scores are available
     */
    public Float getLowestConfidenceScore() {
        if (confidenceScores == null || confidenceScores.isEmpty()) {
            return null;
        }
        
        return confidenceScores.values().stream()
                .min(Float::compare)
                .orElse(null);
    }

    /**
     * Checks if the document has been successfully processed.
     * 
     * @return true if processing is complete, false otherwise
     */
    public boolean isProcessingComplete() {
        return "completed".equals(status);
    }

    /**
     * Checks if the document processing has failed.
     * 
     * @return true if processing failed, false otherwise
     */
    public boolean isProcessingFailed() {
        return "failed".equals(status);
    }

    /**
     * Gets a specific field value from the extraction results.
     * 
     * @param fieldName the name of the field to retrieve
     * @return the field value, or null if not found
     */
    @SuppressWarnings("unchecked")
    public Object getFieldValue(String fieldName) {
        if (extractionResults == null) {
            return null;
        }
        
        // Handle nested field paths (e.g., "applicant.name")
        String[] pathParts = fieldName.split("\\.");
        Map<String, Object> currentMap = extractionResults;
        
        for (int i = 0; i < pathParts.length - 1; i++) {
            Object value = currentMap.get(pathParts[i]);
            if (!(value instanceof Map)) {
                return null;
            }
            currentMap = (Map<String, Object>) value;
        }
        
        return currentMap.get(pathParts[pathParts.length - 1]);
    }

    /**
     * Gets the confidence score for a specific field.
     * 
     * @param fieldName the name of the field
     * @return the confidence score, or null if not found
     */
    public Float getFieldConfidence(String fieldName) {
        if (confidenceScores == null) {
            return null;
        }
        return confidenceScores.get(fieldName);
    }
}