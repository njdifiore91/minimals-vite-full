package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link DocumentProcessingException} class.
 * 
 * These tests verify the behavior of the DocumentProcessingException for document processing failure scenarios,
 * ensuring proper initialization, message formatting, and HTTP status code assignment.
 */
@DisplayName("DocumentProcessingException Tests")
class DocumentProcessingExceptionTest {

    private static final String TEST_MESSAGE = "Failed to process document";
    private static final String TEST_DOCUMENT_ID = "doc-123";
    private static final String TEST_PROCESSING_STAGE = "OCR_EXTRACTION";
    private static final String TEST_DOCUMENT_TYPE = "BANK_STATEMENT";

    @Test
    @DisplayName("Should create exception with message only")
    void shouldCreateExceptionWithMessageOnly() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(TEST_MESSAGE);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertNull(exception.getDocumentId());
        assertNull(exception.getProcessingStage());
        assertNull(exception.getDocumentType());
    }

    @Test
    @DisplayName("Should create exception with message and document ID")
    void shouldCreateExceptionWithMessageAndDocumentId() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(TEST_MESSAGE, TEST_DOCUMENT_ID);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_DOCUMENT_ID, exception.getDocumentId());
        assertNull(exception.getProcessingStage());
        assertNull(exception.getDocumentType());
    }

    @Test
    @DisplayName("Should create exception with message, document ID, and processing stage")
    void shouldCreateExceptionWithMessageDocumentIdAndProcessingStage() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, TEST_PROCESSING_STAGE);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_DOCUMENT_ID, exception.getDocumentId());
        assertEquals(TEST_PROCESSING_STAGE, exception.getProcessingStage());
        assertNull(exception.getDocumentType());
    }

    @Test
    @DisplayName("Should create exception with message, document ID, processing stage, and document type")
    void shouldCreateExceptionWithAllFields() {
        // When
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, TEST_PROCESSING_STAGE, TEST_DOCUMENT_TYPE);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_DOCUMENT_ID, exception.getDocumentId());
        assertEquals(TEST_PROCESSING_STAGE, exception.getProcessingStage());
        assertEquals(TEST_DOCUMENT_TYPE, exception.getDocumentType());
    }

    @Test
    @DisplayName("Should create exception with cause and all fields")
    void shouldCreateExceptionWithCauseAndAllFields() {
        // Given
        Throwable cause = new RuntimeException("File not found");
        
        // When
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, cause, TEST_DOCUMENT_ID, TEST_PROCESSING_STAGE, TEST_DOCUMENT_TYPE);
        
        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(TEST_DOCUMENT_ID, exception.getDocumentId());
        assertEquals(TEST_PROCESSING_STAGE, exception.getProcessingStage());
        assertEquals(TEST_DOCUMENT_TYPE, exception.getDocumentType());
        assertEquals(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should format toString with all fields")
    void shouldFormatToStringWithAllFields() {
        // Given
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, TEST_PROCESSING_STAGE, TEST_DOCUMENT_TYPE);
        
        // When
        String result = exception.toString();
        
        // Then
        assertTrue(result.contains(TEST_MESSAGE));
        assertTrue(result.contains(TEST_DOCUMENT_ID));
        assertTrue(result.contains(TEST_PROCESSING_STAGE));
        assertTrue(result.contains(TEST_DOCUMENT_TYPE));
    }

    @Test
    @DisplayName("Should format toString with partial fields")
    void shouldFormatToStringWithPartialFields() {
        // Given
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID);
        
        // When
        String result = exception.toString();
        
        // Then
        assertTrue(result.contains(TEST_MESSAGE));
        assertTrue(result.contains(TEST_DOCUMENT_ID));
        assertFalse(result.contains(TEST_PROCESSING_STAGE));
        assertFalse(result.contains(TEST_DOCUMENT_TYPE));
    }

    @Test
    @DisplayName("Should determine non-retriable for VALIDATION stage")
    void shouldDetermineNonRetriableForValidationStage() {
        // Given
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, "VALIDATION");
        
        // Then
        assertFalse(exception.isRetriable(), "Should not be retriable for VALIDATION stage");
    }

    @Test
    @DisplayName("Should determine non-retriable for FORMAT_CHECK stage")
    void shouldDetermineNonRetriableForFormatCheckStage() {
        // Given
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, "FORMAT_CHECK");
        
        // Then
        assertFalse(exception.isRetriable(), "Should not be retriable for FORMAT_CHECK stage");
    }

    @Test
    @DisplayName("Should determine retriable for other processing stages")
    void shouldDetermineRetriableForOtherStages() {
        // Given
        DocumentProcessingException ocrException = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, "OCR_EXTRACTION");
        
        DocumentProcessingException classificationException = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, "CLASSIFICATION");
        
        DocumentProcessingException storageException = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID, "STORAGE");
        
        // Then
        assertTrue(ocrException.isRetriable(), "Should be retriable for OCR_EXTRACTION stage");
        assertTrue(classificationException.isRetriable(), "Should be retriable for CLASSIFICATION stage");
        assertTrue(storageException.isRetriable(), "Should be retriable for STORAGE stage");
    }

    @Test
    @DisplayName("Should determine retriable when processing stage is null")
    void shouldDetermineRetriableWhenProcessingStageIsNull() {
        // Given
        DocumentProcessingException exception = new DocumentProcessingException(
                TEST_MESSAGE, TEST_DOCUMENT_ID);
        
        // Then
        assertTrue(exception.isRetriable(), "Should be retriable when processing stage is null");
    }

    @Test
    @DisplayName("Should have INTERNAL_SERVER_ERROR status code")
    void shouldHaveInternalServerErrorStatusCode() {
        // Given
        DocumentProcessingException exception = new DocumentProcessingException(TEST_MESSAGE);
        
        // Then
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
    }
}