package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

/**
 * Exception thrown when errors occur during document storage operations.
 * 
 * This exception extends BaseException with a default HTTP status code of 500 (Internal Server Error)
 * and provides details about the document storage operation that failed. It is used by
 * document-related services to indicate failures in document upload, retrieval, or deletion.
 */
public class DocumentStorageException extends BaseException {

    private static final long serialVersionUID = 1L;
    
    /**
     * Constructs a new DocumentStorageException with the specified detail message.
     * 
     * @param message The detail message
     */
    public DocumentStorageException(String message) {
        super("DOCUMENT_STORAGE_ERROR", message, HttpStatus.INTERNAL_SERVER_ERROR.value());
    }
    
    /**
     * Constructs a new DocumentStorageException with the specified detail message and cause.
     * 
     * @param message The detail message
     * @param cause The cause of the exception
     */
    public DocumentStorageException(String message, Throwable cause) {
        super("DOCUMENT_STORAGE_ERROR", message, HttpStatus.INTERNAL_SERVER_ERROR.value(), cause);
    }
    
    /**
     * Constructs a new DocumentStorageException for upload failures.
     * 
     * @param documentName The name of the document that failed to upload
     * @param cause The cause of the failure
     * @return A new DocumentStorageException
     */
    public static DocumentStorageException uploadFailure(String documentName, Throwable cause) {
        return new DocumentStorageException("Failed to upload document: " + documentName, cause);
    }
    
    /**
     * Constructs a new DocumentStorageException for retrieval failures.
     * 
     * @param documentId The ID of the document that failed to retrieve
     * @param cause The cause of the failure
     * @return A new DocumentStorageException
     */
    public static DocumentStorageException retrievalFailure(Long documentId, Throwable cause) {
        return new DocumentStorageException("Failed to retrieve document with ID: " + documentId, cause);
    }
    
    /**
     * Constructs a new DocumentStorageException for deletion failures.
     * 
     * @param documentId The ID of the document that failed to delete
     * @param cause The cause of the failure
     * @return A new DocumentStorageException
     */
    public static DocumentStorageException deletionFailure(Long documentId, Throwable cause) {
        return new DocumentStorageException("Failed to delete document with ID: " + documentId, cause);
    }
    
    /**
     * Constructs a new DocumentStorageException for URL generation failures.
     * 
     * @param documentId The ID of the document for which URL generation failed
     * @param cause The cause of the failure
     * @return A new DocumentStorageException
     */
    public static DocumentStorageException urlGenerationFailure(Long documentId, Throwable cause) {
        return new DocumentStorageException("Failed to generate secure URL for document with ID: " + documentId, cause);
    }
}