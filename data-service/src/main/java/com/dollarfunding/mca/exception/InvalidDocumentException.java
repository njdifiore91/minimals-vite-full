package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

/**
 * Exception thrown when a document is invalid or does not meet the required criteria.
 * 
 * This exception extends BaseException with a default HTTP status code of 400 (Bad Request)
 * and provides details about the validation failure. It is used by document-related services
 * to indicate issues with document content, format, or metadata.
 */
public class InvalidDocumentException extends BaseException {

    private static final long serialVersionUID = 1L;
    
    /**
     * Constructs a new InvalidDocumentException with the specified detail message.
     * 
     * @param message The detail message
     */
    public InvalidDocumentException(String message) {
        super("INVALID_DOCUMENT", message, HttpStatus.BAD_REQUEST.value());
    }
    
    /**
     * Constructs a new InvalidDocumentException with the specified detail message and cause.
     * 
     * @param message The detail message
     * @param cause The cause of the exception
     */
    public InvalidDocumentException(String message, Throwable cause) {
        super("INVALID_DOCUMENT", message, HttpStatus.BAD_REQUEST.value(), cause);
    }
    
    /**
     * Constructs a new InvalidDocumentException for empty document content.
     * 
     * @return A new InvalidDocumentException
     */
    public static InvalidDocumentException emptyContent() {
        return new InvalidDocumentException("Document content is empty or null");
    }
    
    /**
     * Constructs a new InvalidDocumentException for invalid document format.
     * 
     * @param format The invalid format
     * @return A new InvalidDocumentException
     */
    public static InvalidDocumentException invalidFormat(String format) {
        return new InvalidDocumentException("Invalid document format: " + format);
    }
    
    /**
     * Constructs a new InvalidDocumentException for invalid document type.
     * 
     * @param type The invalid type
     * @return A new InvalidDocumentException
     */
    public static InvalidDocumentException invalidType(String type) {
        return new InvalidDocumentException("Invalid document type: " + type);
    }
    
    /**
     * Constructs a new InvalidDocumentException for invalid document metadata.
     * 
     * @param reason The reason for the metadata invalidity
     * @return A new InvalidDocumentException
     */
    public static InvalidDocumentException invalidMetadata(String reason) {
        return new InvalidDocumentException("Invalid document metadata: " + reason);
    }
    
    /**
     * Constructs a new InvalidDocumentException for document size exceeding the limit.
     * 
     * @param size The actual size
     * @param maxSize The maximum allowed size
     * @return A new InvalidDocumentException
     */
    public static InvalidDocumentException sizeExceeded(long size, long maxSize) {
        return new InvalidDocumentException("Document size exceeds the maximum allowed size: " + 
                size + " > " + maxSize);
    }
}