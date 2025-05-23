package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.util.Constants;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link DocumentProcessingException} class.
 * 
 * These tests verify that the DocumentProcessingException properly handles document processing
 * failures with appropriate HTTP status codes, error messages, and contextual information about
 * the document processing stage that failed.
 */
@DisplayName("Document Processing Exception Tests")
class DocumentProcessingExceptionTest {

    private static final String ERROR_MESSAGE = "Failed to process document";
    private static final Long DOCUMENT_ID = 123L;
    private static final String PROCESSING_STAGE = "classification";

    @Test
    @DisplayName("Should create exception with message only")
    void shouldCreateExceptionWithMessageOnly() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(ERROR_MESSAGE);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertNull(exception.getDocumentId());
        assertNull(exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create exception with message and cause")
    void shouldCreateExceptionWithMessageAndCause() {
        // Given
        Throwable cause = new RuntimeException("Root cause");
        
        // When
        DocumentProcessingException exception = new DocumentProcessingException(ERROR_MESSAGE, cause);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertSame(cause, exception.getCause());
        assertNull(exception.getDocumentId());
        assertNull(exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create exception with message and document ID")
    void shouldCreateExceptionWithMessageAndDocumentId() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(ERROR_MESSAGE, DOCUMENT_ID);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertNull(exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create exception with message, document ID, and processing stage")
    void shouldCreateExceptionWithMessageDocumentIdAndProcessingStage() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(
                ERROR_MESSAGE, DOCUMENT_ID, PROCESSING_STAGE);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertEquals(PROCESSING_STAGE, exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create exception with message, cause, document ID, and processing stage")
    void shouldCreateExceptionWithAllParameters() {
        // Given
        Throwable cause = new RuntimeException("Root cause");
        
        // When
        DocumentProcessingException exception = new DocumentProcessingException(
                ERROR_MESSAGE, cause, DOCUMENT_ID, PROCESSING_STAGE);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertSame(cause, exception.getCause());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertEquals(PROCESSING_STAGE, exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create storage error exception")
    void shouldCreateStorageErrorException() {
        // Given
        Throwable cause = new RuntimeException("Storage failure");
        
        // When
        DocumentProcessingException exception = DocumentProcessingException.storageError(
                ERROR_MESSAGE, DOCUMENT_ID, cause);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertSame(cause, exception.getCause());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertEquals("storage", exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create retrieval error exception")
    void shouldCreateRetrievalErrorException() {
        // Given
        Throwable cause = new RuntimeException("Retrieval failure");
        
        // When
        DocumentProcessingException exception = DocumentProcessingException.retrievalError(
                ERROR_MESSAGE, DOCUMENT_ID, cause);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertSame(cause, exception.getCause());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertEquals("retrieval", exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create classification error exception")
    void shouldCreateClassificationErrorException() {
        // Given
        Throwable cause = new RuntimeException("Classification failure");
        
        // When
        DocumentProcessingException exception = DocumentProcessingException.classificationError(
                ERROR_MESSAGE, DOCUMENT_ID, cause);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertSame(cause, exception.getCause());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertEquals("classification", exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create OCR extraction error exception")
    void shouldCreateOcrExtractionErrorException() {
        // Given
        Throwable cause = new RuntimeException("OCR extraction failure");
        
        // When
        DocumentProcessingException exception = DocumentProcessingException.ocrExtractionError(
                ERROR_MESSAGE, DOCUMENT_ID, cause);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertSame(cause, exception.getCause());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertEquals("ocr_extraction", exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should create validation error exception")
    void shouldCreateValidationErrorException() {
        // Given
        Throwable cause = new RuntimeException("Validation failure");
        
        // When
        DocumentProcessingException exception = DocumentProcessingException.validationError(
                ERROR_MESSAGE, DOCUMENT_ID, cause);
        
        // Then
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertSame(cause, exception.getCause());
        assertEquals(DOCUMENT_ID, exception.getDocumentId());
        assertEquals("validation", exception.getProcessingStage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should verify HTTP status code is 500 Internal Server Error")
    void shouldVerifyHttpStatusCodeIs500() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(ERROR_MESSAGE);
        
        // Then
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(500, exception.getStatusCode());
    }

    @Test
    @DisplayName("Should format message with document ID and processing stage")
    void shouldFormatMessageWithDocumentIdAndProcessingStage() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(
                ERROR_MESSAGE, DOCUMENT_ID, PROCESSING_STAGE);
        
        // Then
        String expectedToString = String.format("BaseException{errorCode='%s', httpStatus=%s, message='%s'}",
                Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR, HttpStatus.INTERNAL_SERVER_ERROR, ERROR_MESSAGE);
        assertEquals(expectedToString, exception.toString());
    }
}