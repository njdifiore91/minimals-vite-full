package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.util.Constants;
import org.springframework.http.HttpStatus;

/**
 * Exception thrown when errors occur during document processing operations.
 * <p>
 * This exception is used by document-related services to indicate failures in document
 * storage, retrieval, or classification. It extends BaseException with a default HTTP
 * status code of 500 (Internal Server Error) and provides details about the document
 * and processing stage.
 * </p>
 */
public class DocumentProcessingException extends BaseException {

    private final Long documentId;
    private final String processingStage;

    /**
     * Constructs a new DocumentProcessingException with the specified message.
     *
     * @param message the detail message
     */
    public DocumentProcessingException(String message) {
        this(message, null, null);
    }

    /**
     * Constructs a new DocumentProcessingException with the specified message and cause.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     */
    public DocumentProcessingException(String message, Throwable cause) {
        this(message, cause, null, null);
    }

    /**
     * Constructs a new DocumentProcessingException with the specified message and document ID.
     *
     * @param message    the detail message
     * @param documentId the ID of the document that failed processing
     */
    public DocumentProcessingException(String message, Long documentId) {
        this(message, documentId, null);
    }

    /**
     * Constructs a new DocumentProcessingException with the specified message, document ID, and processing stage.
     *
     * @param message         the detail message
     * @param documentId      the ID of the document that failed processing
     * @param processingStage the stage of processing where the failure occurred
     */
    public DocumentProcessingException(String message, Long documentId, String processingStage) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR, Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR);
        this.documentId = documentId;
        this.processingStage = processingStage;
    }

    /**
     * Constructs a new DocumentProcessingException with the specified message, cause, document ID, and processing stage.
     *
     * @param message         the detail message
     * @param cause           the cause of this exception
     * @param documentId      the ID of the document that failed processing
     * @param processingStage the stage of processing where the failure occurred
     */
    public DocumentProcessingException(String message, Throwable cause, Long documentId, String processingStage) {
        super(message, cause, HttpStatus.INTERNAL_SERVER_ERROR, Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR);
        this.documentId = documentId;
        this.processingStage = processingStage;
    }

    /**
     * Returns the ID of the document that failed processing.
     *
     * @return the document ID, or null if not available
     */
    public Long getDocumentId() {
        return documentId;
    }

    /**
     * Returns the stage of processing where the failure occurred.
     *
     * @return the processing stage, or null if not available
     */
    public String getProcessingStage() {
        return processingStage;
    }

    /**
     * Creates a new DocumentProcessingException for a storage error.
     *
     * @param message    the detail message
     * @param documentId the ID of the document
     * @param cause      the cause of this exception
     * @return a new DocumentProcessingException
     */
    public static DocumentProcessingException storageError(String message, Long documentId, Throwable cause) {
        return new DocumentProcessingException(message, cause, documentId, "storage");
    }

    /**
     * Creates a new DocumentProcessingException for a retrieval error.
     *
     * @param message    the detail message
     * @param documentId the ID of the document
     * @param cause      the cause of this exception
     * @return a new DocumentProcessingException
     */
    public static DocumentProcessingException retrievalError(String message, Long documentId, Throwable cause) {
        return new DocumentProcessingException(message, cause, documentId, "retrieval");
    }

    /**
     * Creates a new DocumentProcessingException for a classification error.
     *
     * @param message    the detail message
     * @param documentId the ID of the document
     * @param cause      the cause of this exception
     * @return a new DocumentProcessingException
     */
    public static DocumentProcessingException classificationError(String message, Long documentId, Throwable cause) {
        return new DocumentProcessingException(message, cause, documentId, "classification");
    }

    /**
     * Creates a new DocumentProcessingException for an OCR extraction error.
     *
     * @param message    the detail message
     * @param documentId the ID of the document
     * @param cause      the cause of this exception
     * @return a new DocumentProcessingException
     */
    public static DocumentProcessingException ocrExtractionError(String message, Long documentId, Throwable cause) {
        return new DocumentProcessingException(message, cause, documentId, "ocr_extraction");
    }

    /**
     * Creates a new DocumentProcessingException for a validation error.
     *
     * @param message    the detail message
     * @param documentId the ID of the document
     * @param cause      the cause of this exception
     * @return a new DocumentProcessingException
     */
    public static DocumentProcessingException validationError(String message, Long documentId, Throwable cause) {
        return new DocumentProcessingException(message, cause, documentId, "validation");
    }
}