package com.dollarfunding.mca.messaging;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Min;
import javax.validation.constraints.Max;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Model class for document processing messages consumed from RabbitMQ.
 * This class defines the structure of messages received from the OCR Service
 * containing extracted document data.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentProcessingMessage {

    /**
     * Enum defining the types of documents that can be processed.
     */
    public enum DocumentType {
        APPLICATION_FORM,
        BANK_STATEMENT,
        TAX_RETURN,
        IDENTITY_DOCUMENT,
        BUSINESS_LICENSE,
        CREDIT_CARD_STATEMENT,
        INVOICE,
        UTILITY_BILL,
        LEASE_AGREEMENT,
        OTHER
    }

    /**
     * Enum defining the processing actions to be taken.
     */
    public enum ProcessingAction {
        CREATE_NEW_APPLICATION,
        UPDATE_EXISTING_APPLICATION,
        APPEND_TO_APPLICATION,
        VERIFICATION_ONLY,
        ARCHIVE_ONLY
    }

    @NotBlank
    @JsonProperty("id")
    private String id;

    @NotBlank
    @JsonProperty("document_id")
    private String documentId;

    @NotNull
    @JsonProperty("document_type")
    private DocumentType documentType;

    @NotBlank
    @JsonProperty("classification")
    private String classification;

    @NotNull
    @Min(0)
    @Max(100)
    @JsonProperty("classification_confidence")
    private Double classificationConfidence;

    @NotNull
    @JsonProperty("processing_action")
    private ProcessingAction processingAction;

    @JsonProperty("application_id")
    private String applicationId;

    @NotNull
    @JsonProperty("timestamp")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime timestamp;

    @JsonProperty("storage_path")
    private String storagePath;

    @NotNull
    @JsonProperty("extracted_fields")
    private Map<String, ExtractedField> extractedFields;

    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    @JsonProperty("processing_metadata")
    private ProcessingMetadata processingMetadata;

    /**
     * Default constructor for serialization frameworks.
     */
    public DocumentProcessingMessage() {
        this.timestamp = LocalDateTime.now();
        this.extractedFields = new HashMap<>();
        this.metadata = new HashMap<>();
    }

    /**
     * Constructor with essential fields.
     *
     * @param id                      Unique identifier for the message
     * @param documentId              Identifier for the document
     * @param documentType            Type of document
     * @param classification          Classification of the document
     * @param classificationConfidence Confidence score for the classification
     * @param processingAction        Action to take for processing
     * @param extractedFields         Map of extracted fields with values and confidence scores
     */
    public DocumentProcessingMessage(String id, String documentId, DocumentType documentType,
                                    String classification, Double classificationConfidence,
                                    ProcessingAction processingAction,
                                    Map<String, ExtractedField> extractedFields) {
        this.id = id;
        this.documentId = documentId;
        this.documentType = documentType;
        this.classification = classification;
        this.classificationConfidence = classificationConfidence;
        this.processingAction = processingAction;
        this.timestamp = LocalDateTime.now();
        this.extractedFields = extractedFields;
        this.metadata = new HashMap<>();
    }

    /**
     * Inner class representing an extracted field with value and confidence score.
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class ExtractedField {
        @NotNull
        @JsonProperty("value")
        private Object value;

        @NotNull
        @Min(0)
        @Max(100)
        @JsonProperty("confidence")
        private Double confidence;

        @JsonProperty("original_text")
        private String originalText;

        @JsonProperty("bounding_box")
        private BoundingBox boundingBox;

        @JsonProperty("alternatives")
        private List<Alternative> alternatives;

        /**
         * Default constructor for serialization frameworks.
         */
        public ExtractedField() {
        }

        /**
         * Constructor with essential fields.
         *
         * @param value      The extracted value
         * @param confidence Confidence score for the extraction
         */
        public ExtractedField(Object value, Double confidence) {
            this.value = value;
            this.confidence = confidence;
        }

        /**
         * Constructor with all fields.
         *
         * @param value        The extracted value
         * @param confidence   Confidence score for the extraction
         * @param originalText The original text from which the value was extracted
         * @param boundingBox  The bounding box of the text in the document
         * @param alternatives Alternative extractions with lower confidence
         */
        public ExtractedField(Object value, Double confidence, String originalText,
                             BoundingBox boundingBox, List<Alternative> alternatives) {
            this.value = value;
            this.confidence = confidence;
            this.originalText = originalText;
            this.boundingBox = boundingBox;
            this.alternatives = alternatives;
        }

        public Object getValue() {
            return value;
        }

        public void setValue(Object value) {
            this.value = value;
        }

        public Double getConfidence() {
            return confidence;
        }

        public void setConfidence(Double confidence) {
            this.confidence = confidence;
        }

        public String getOriginalText() {
            return originalText;
        }

        public void setOriginalText(String originalText) {
            this.originalText = originalText;
        }

        public BoundingBox getBoundingBox() {
            return boundingBox;
        }

        public void setBoundingBox(BoundingBox boundingBox) {
            this.boundingBox = boundingBox;
        }

        public List<Alternative> getAlternatives() {
            return alternatives;
        }

        public void setAlternatives(List<Alternative> alternatives) {
            this.alternatives = alternatives;
        }
    }

    /**
     * Inner class representing an alternative extraction with lower confidence.
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class Alternative {
        @NotNull
        @JsonProperty("value")
        private Object value;

        @NotNull
        @Min(0)
        @Max(100)
        @JsonProperty("confidence")
        private Double confidence;

        /**
         * Default constructor for serialization frameworks.
         */
        public Alternative() {
        }

        /**
         * Constructor with all fields.
         *
         * @param value      The alternative value
         * @param confidence Confidence score for the alternative
         */
        public Alternative(Object value, Double confidence) {
            this.value = value;
            this.confidence = confidence;
        }

        public Object getValue() {
            return value;
        }

        public void setValue(Object value) {
            this.value = value;
        }

        public Double getConfidence() {
            return confidence;
        }

        public void setConfidence(Double confidence) {
            this.confidence = confidence;
        }
    }

    /**
     * Inner class representing a bounding box in the document.
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class BoundingBox {
        @NotNull
        @JsonProperty("x")
        private Integer x;

        @NotNull
        @JsonProperty("y")
        private Integer y;

        @NotNull
        @JsonProperty("width")
        private Integer width;

        @NotNull
        @JsonProperty("height")
        private Integer height;

        @JsonProperty("page")
        private Integer page;

        /**
         * Default constructor for serialization frameworks.
         */
        public BoundingBox() {
        }

        /**
         * Constructor with essential fields.
         *
         * @param x      X-coordinate of the top-left corner
         * @param y      Y-coordinate of the top-left corner
         * @param width  Width of the bounding box
         * @param height Height of the bounding box
         */
        public BoundingBox(Integer x, Integer y, Integer width, Integer height) {
            this.x = x;
            this.y = y;
            this.width = width;
            this.height = height;
        }

        /**
         * Constructor with all fields.
         *
         * @param x      X-coordinate of the top-left corner
         * @param y      Y-coordinate of the top-left corner
         * @param width  Width of the bounding box
         * @param height Height of the bounding box
         * @param page   Page number in the document
         */
        public BoundingBox(Integer x, Integer y, Integer width, Integer height, Integer page) {
            this.x = x;
            this.y = y;
            this.width = width;
            this.height = height;
            this.page = page;
        }

        public Integer getX() {
            return x;
        }

        public void setX(Integer x) {
            this.x = x;
        }

        public Integer getY() {
            return y;
        }

        public void setY(Integer y) {
            this.y = y;
        }

        public Integer getWidth() {
            return width;
        }

        public void setWidth(Integer width) {
            this.width = width;
        }

        public Integer getHeight() {
            return height;
        }

        public void setHeight(Integer height) {
            this.height = height;
        }

        public Integer getPage() {
            return page;
        }

        public void setPage(Integer page) {
            this.page = page;
        }
    }

    /**
     * Inner class representing metadata about the processing of the document.
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class ProcessingMetadata {
        @JsonProperty("processing_time_ms")
        private Long processingTimeMs;

        @JsonProperty("ocr_engine")
        private String ocrEngine;

        @JsonProperty("ocr_engine_version")
        private String ocrEngineVersion;

        @JsonProperty("classification_model")
        private String classificationModel;

        @JsonProperty("classification_model_version")
        private String classificationModelVersion;

        @JsonProperty("processing_node")
        private String processingNode;

        @JsonProperty("retry_count")
        private Integer retryCount;

        @JsonProperty("processing_notes")
        private List<String> processingNotes;

        /**
         * Default constructor for serialization frameworks.
         */
        public ProcessingMetadata() {
        }

        public Long getProcessingTimeMs() {
            return processingTimeMs;
        }

        public void setProcessingTimeMs(Long processingTimeMs) {
            this.processingTimeMs = processingTimeMs;
        }

        public String getOcrEngine() {
            return ocrEngine;
        }

        public void setOcrEngine(String ocrEngine) {
            this.ocrEngine = ocrEngine;
        }

        public String getOcrEngineVersion() {
            return ocrEngineVersion;
        }

        public void setOcrEngineVersion(String ocrEngineVersion) {
            this.ocrEngineVersion = ocrEngineVersion;
        }

        public String getClassificationModel() {
            return classificationModel;
        }

        public void setClassificationModel(String classificationModel) {
            this.classificationModel = classificationModel;
        }

        public String getClassificationModelVersion() {
            return classificationModelVersion;
        }

        public void setClassificationModelVersion(String classificationModelVersion) {
            this.classificationModelVersion = classificationModelVersion;
        }

        public String getProcessingNode() {
            return processingNode;
        }

        public void setProcessingNode(String processingNode) {
            this.processingNode = processingNode;
        }

        public Integer getRetryCount() {
            return retryCount;
        }

        public void setRetryCount(Integer retryCount) {
            this.retryCount = retryCount;
        }

        public List<String> getProcessingNotes() {
            return processingNotes;
        }

        public void setProcessingNotes(List<String> processingNotes) {
            this.processingNotes = processingNotes;
        }
    }

    // Getters and Setters

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getDocumentId() {
        return documentId;
    }

    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    public DocumentType getDocumentType() {
        return documentType;
    }

    public void setDocumentType(DocumentType documentType) {
        this.documentType = documentType;
    }

    public String getClassification() {
        return classification;
    }

    public void setClassification(String classification) {
        this.classification = classification;
    }

    public Double getClassificationConfidence() {
        return classificationConfidence;
    }

    public void setClassificationConfidence(Double classificationConfidence) {
        this.classificationConfidence = classificationConfidence;
    }

    public ProcessingAction getProcessingAction() {
        return processingAction;
    }

    public void setProcessingAction(ProcessingAction processingAction) {
        this.processingAction = processingAction;
    }

    public String getApplicationId() {
        return applicationId;
    }

    public void setApplicationId(String applicationId) {
        this.applicationId = applicationId;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }

    public String getStoragePath() {
        return storagePath;
    }

    public void setStoragePath(String storagePath) {
        this.storagePath = storagePath;
    }

    public Map<String, ExtractedField> getExtractedFields() {
        return extractedFields;
    }

    public void setExtractedFields(Map<String, ExtractedField> extractedFields) {
        this.extractedFields = extractedFields;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    public ProcessingMetadata getProcessingMetadata() {
        return processingMetadata;
    }

    public void setProcessingMetadata(ProcessingMetadata processingMetadata) {
        this.processingMetadata = processingMetadata;
    }

    /**
     * Adds a field to the extractedFields map.
     *
     * @param fieldName The name of the field
     * @param field     The ExtractedField instance
     * @return This DocumentProcessingMessage instance for method chaining
     */
    public DocumentProcessingMessage addExtractedField(String fieldName, ExtractedField field) {
        this.extractedFields.put(fieldName, field);
        return this;
    }

    /**
     * Adds a key-value pair to the metadata map.
     *
     * @param key   The key for the metadata entry
     * @param value The value for the metadata entry
     * @return This DocumentProcessingMessage instance for method chaining
     */
    public DocumentProcessingMessage addMetadata(String key, Object value) {
        this.metadata.put(key, value);
        return this;
    }

    /**
     * Creates a builder for DocumentProcessingMessage.
     *
     * @return A new Builder instance
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder class for creating DocumentProcessingMessage instances.
     */
    public static class Builder {
        private String id;
        private String documentId;
        private DocumentType documentType;
        private String classification;
        private Double classificationConfidence;
        private ProcessingAction processingAction;
        private String applicationId;
        private String storagePath;
        private Map<String, ExtractedField> extractedFields;
        private Map<String, Object> metadata;
        private ProcessingMetadata processingMetadata;

        private Builder() {
            this.extractedFields = new HashMap<>();
            this.metadata = new HashMap<>();
        }

        public Builder id(String id) {
            this.id = id;
            return this;
        }

        public Builder documentId(String documentId) {
            this.documentId = documentId;
            return this;
        }

        public Builder documentType(DocumentType documentType) {
            this.documentType = documentType;
            return this;
        }

        public Builder classification(String classification) {
            this.classification = classification;
            return this;
        }

        public Builder classificationConfidence(Double classificationConfidence) {
            this.classificationConfidence = classificationConfidence;
            return this;
        }

        public Builder processingAction(ProcessingAction processingAction) {
            this.processingAction = processingAction;
            return this;
        }

        public Builder applicationId(String applicationId) {
            this.applicationId = applicationId;
            return this;
        }

        public Builder storagePath(String storagePath) {
            this.storagePath = storagePath;
            return this;
        }

        public Builder extractedFields(Map<String, ExtractedField> extractedFields) {
            this.extractedFields = extractedFields;
            return this;
        }

        public Builder addExtractedField(String fieldName, ExtractedField field) {
            this.extractedFields.put(fieldName, field);
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Builder addMetadata(String key, Object value) {
            this.metadata.put(key, value);
            return this;
        }

        public Builder processingMetadata(ProcessingMetadata processingMetadata) {
            this.processingMetadata = processingMetadata;
            return this;
        }

        public DocumentProcessingMessage build() {
            DocumentProcessingMessage message = new DocumentProcessingMessage();
            message.id = this.id;
            message.documentId = this.documentId;
            message.documentType = this.documentType;
            message.classification = this.classification;
            message.classificationConfidence = this.classificationConfidence;
            message.processingAction = this.processingAction;
            message.applicationId = this.applicationId;
            message.timestamp = LocalDateTime.now();
            message.storagePath = this.storagePath;
            message.extractedFields = this.extractedFields;
            message.metadata = this.metadata;
            message.processingMetadata = this.processingMetadata;
            return message;
        }
    }
}