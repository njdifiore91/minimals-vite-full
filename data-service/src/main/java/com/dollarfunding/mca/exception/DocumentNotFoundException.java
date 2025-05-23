package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

/**
 * Exception thrown when a requested document cannot be found in the system.
 * 
 * This exception extends BaseException with a default HTTP status code of 404 (Not Found)
 * and provides constructors for specifying the document identifier. It is used by
 * document-related services to indicate missing documents.
 */
public class DocumentNotFoundException extends BaseException {

    private static final long serialVersionUID = 1L;
    
    /**
     * Constructs a new DocumentNotFoundException with the specified detail message.
     * 
     * @param message The detail message
     */
    public DocumentNotFoundException(String message) {
        super("DOCUMENT_NOT_FOUND", message, HttpStatus.NOT_FOUND.value());
    }
    
    /**
     * Constructs a new DocumentNotFoundException with the specified detail message and cause.
     * 
     * @param message The detail message
     * @param cause The cause of the exception
     */
    public DocumentNotFoundException(String message, Throwable cause) {
        super("DOCUMENT_NOT_FOUND", message, HttpStatus.NOT_FOUND.value(), cause);
    }
    
    /**
     * Constructs a new DocumentNotFoundException with a message indicating the document ID.
     * 
     * @param documentId The ID of the document that was not found
     * @return A new DocumentNotFoundException
     */
    public static DocumentNotFoundException forId(Long documentId) {
        return new DocumentNotFoundException("Document not found with ID: " + documentId);
    }
    
    /**
     * Constructs a new DocumentNotFoundException with a message indicating the application ID.
     * 
     * @param applicationId The ID of the application whose documents were not found
     * @return A new DocumentNotFoundException
     */
    public static DocumentNotFoundException forApplicationId(Long applicationId) {
        return new DocumentNotFoundException("No documents found for application ID: " + applicationId);
    }
    
    /**
     * Constructs a new DocumentNotFoundException with a message indicating the storage path.
     * 
     * @param storagePath The storage path of the document that was not found
     * @return A new DocumentNotFoundException
     */
    public static DocumentNotFoundException forStoragePath(String storagePath) {
        return new DocumentNotFoundException("Document not found at storage path: " + storagePath);
    }
}