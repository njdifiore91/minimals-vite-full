package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

/**
 * Exception thrown when errors occur during document processing operations.
 * This exception is used by document-related services to indicate failures in document
 * storage, retrieval, or classification.
 */
public class DocumentProcessingException extends BaseException {

    private final String documentId;
    private final String processingStage;
    private final String documentType;

    /**
     * Constructs a new DocumentProcessingException with the specified detail message.
     *
     * @param message the detail message
     */
    public DocumentProcessingException(String message) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.documentId = null;
        this.processingStage = null;
        this.documentType = null;
    }

    /**
     * Constructs a new DocumentProcessingException with the specified detail message and document ID.
     *
     * @param message    the detail message
     * @param documentId the ID of the document that failed processing
     */
    public DocumentProcessingException(String message, String documentId) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.documentId = documentId;
        this.processingStage = null;
        this.documentType = null;
    }

    /**
     * Constructs a new DocumentProcessingException with the specified detail message, document ID, and processing stage.
     *
     * @param message         the detail message
     * @param documentId      the ID of the document that failed processing
     * @param processingStage the stage of processing where the failure occurred
     */
    public DocumentProcessingException(String message, String documentId, String processingStage) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.documentId = documentId;
        this.processingStage = processingStage;
        this.documentType = null;
    }

    /**
     * Constructs a new DocumentProcessingException with the specified detail message, document ID, processing stage, and document type.
     *
     * @param message         the detail message
     * @param documentId      the ID of the document that failed processing
     * @param processingStage the stage of processing where the failure occurred
     * @param documentType    the type of document being processed
     */
    public DocumentProcessingException(String message, String documentId, String processingStage, String documentType) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.documentId = documentId;
        this.processingStage = processingStage;
        this.documentType = documentType;
    }

    /**
     * Constructs a new DocumentProcessingException with the specified detail message, cause, document ID, processing stage, and document type.
     *
     * @param message         the detail message
     * @param cause           the cause of the exception
     * @param documentId      the ID of the document that failed processing
     * @param processingStage the stage of processing where the failure occurred
     * @param documentType    the type of document being processed
     */
    public DocumentProcessingException(String message, Throwable cause, String documentId, String processingStage, String documentType) {
        super(message, cause, HttpStatus.INTERNAL_SERVER_ERROR.value());
        this.documentId = documentId;
        this.processingStage = processingStage;
        this.documentType = documentType;
    }

    /**
     * Gets the ID of the document that failed processing.
     *
     * @return the document ID, or null if not specified
     */
    public String getDocumentId() {
        return documentId;
    }

    /**
     * Gets the stage of processing where the failure occurred.
     *
     * @return the processing stage, or null if not specified
     */
    public String getProcessingStage() {
        return processingStage;
    }

    /**
     * Gets the type of document being processed.
     *
     * @return the document type, or null if not specified
     */
    public String getDocumentType() {
        return documentType;
    }

    /**
     * Determines if the document processing can be retried based on the processing stage and error type.
     *
     * @return true if the document processing should be retried, false otherwise
     */
    public boolean isRetriable() {
        // If the processing stage is null, assume it's retriable
        if (processingStage == null) {
            return true;
        }
        
        // Define non-retriable stages
        // For example, if the document is corrupted or has invalid format, it's not retriable
        if (processingStage.equals("VALIDATION") || processingStage.equals("FORMAT_CHECK")) {
            return false;
        }
        
        // Otherwise, it's retriable
        return true;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder("DocumentProcessingException: ");
        sb.append(getMessage());
        
        if (documentId != null) {
            sb.append(", documentId='").append(documentId).append('\'');
        }
        
        if (processingStage != null) {
            sb.append(", processingStage='").append(processingStage).append('\'');
        }
        
        if (documentType != null) {
            sb.append(", documentType='").append(documentType).append('\'');
        }
        
        return sb.toString();
    }
}