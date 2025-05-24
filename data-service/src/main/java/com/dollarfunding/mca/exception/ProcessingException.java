package com.dollarfunding.mca.exception;

import java.util.Map;
import java.util.UUID;

/**
 * Exception thrown when an error occurs during application processing.
 * This exception includes details about the processing context, such as
 * the document and application involved, to aid in troubleshooting and recovery.
 */
public class ProcessingException extends RuntimeException {

    private final UUID documentId;
    private final UUID applicationId;
    private final String errorCode;
    private final Map<String, Object> metadata;

    /**
     * Creates a new ProcessingException with the specified message.
     *
     * @param message The error message
     */
    public ProcessingException(String message) {
        super(message);
        this.documentId = null;
        this.applicationId = null;
        this.errorCode = "PROCESSING_ERROR";
        this.metadata = null;
    }

    /**
     * Creates a new ProcessingException with the specified message and cause.
     *
     * @param message The error message
     * @param cause The cause of the exception
     */
    public ProcessingException(String message, Throwable cause) {
        super(message, cause);
        this.documentId = null;
        this.applicationId = null;
        this.errorCode = "PROCESSING_ERROR";
        this.metadata = null;
    }

    /**
     * Creates a new ProcessingException with the specified message, error code, and context.
     *
     * @param message The error message
     * @param errorCode A specific error code for this exception
     * @param documentId The ID of the document being processed when the error occurred
     * @param applicationId The ID of the application being processed when the error occurred
     * @param metadata Additional metadata about the processing context
     */
    public ProcessingException(String message, String errorCode, UUID documentId, UUID applicationId, Map<String, Object> metadata) {
        super(message);
        this.documentId = documentId;
        this.applicationId = applicationId;
        this.errorCode = errorCode != null ? errorCode : "PROCESSING_ERROR";
        this.metadata = metadata;
    }

    /**
     * Creates a new ProcessingException with the specified message, cause, error code, and context.
     *
     * @param message The error message
     * @param cause The cause of the exception
     * @param errorCode A specific error code for this exception
     * @param documentId The ID of the document being processed when the error occurred
     * @param applicationId The ID of the application being processed when the error occurred
     * @param metadata Additional metadata about the processing context
     */
    public ProcessingException(String message, Throwable cause, String errorCode, UUID documentId, UUID applicationId, Map<String, Object> metadata) {
        super(message, cause);
        this.documentId = documentId;
        this.applicationId = applicationId;
        this.errorCode = errorCode != null ? errorCode : "PROCESSING_ERROR";
        this.metadata = metadata;
    }

    /**
     * Gets the ID of the document being processed when the error occurred.
     *
     * @return The document ID, or null if not available
     */
    public UUID getDocumentId() {
        return documentId;
    }

    /**
     * Gets the ID of the application being processed when the error occurred.
     *
     * @return The application ID, or null if not available
     */
    public UUID getApplicationId() {
        return applicationId;
    }

    /**
     * Gets the error code for this exception.
     *
     * @return The error code
     */
    public String getErrorCode() {
        return errorCode;
    }

    /**
     * Gets the metadata about the processing context.
     *
     * @return The metadata, or null if not available
     */
    public Map<String, Object> getMetadata() {
        return metadata;
    }

    /**
     * Creates a string representation of this exception, including context information.
     *
     * @return A string representation of this exception
     */
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder("ProcessingException: ");
        sb.append(getMessage());
        sb.append(" [errorCode=").append(errorCode).append("]")
          .append(" [documentId=").append(documentId).append("]")
          .append(" [applicationId=").append(applicationId).append("]")
          .append(" [metadata=").append(metadata).append("]")
          .append(" [cause=").append(getCause()).append("]");
        return sb.toString();
    }
}