package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.util.Constants;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link ErrorResponseDTO}.
 * 
 * This class tests the error response structure, JSON serialization/deserialization,
 * and builder pattern functionality. It validates error code mapping, message formatting,
 * and field-level validation error handling.
 */
public class ErrorResponseDTOTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    
    @Test
    public void testDefaultConstructor() {
        // When
        ErrorResponseDTO errorResponse = new ErrorResponseDTO();
        
        // Then
        assertNotNull(errorResponse);
        assertNotNull(errorResponse.getTimestamp(), "Timestamp should be initialized");
        assertNull(errorResponse.getMessage(), "Message should be null");
        assertNull(errorResponse.getErrorCode(), "Error code should be null");
        assertNull(errorResponse.getPath(), "Path should be null");
        assertEquals(0, errorResponse.getStatus(), "Status should be 0");
        assertNull(errorResponse.getDetails(), "Details should be null");
    }
    
    @Test
    public void testConstructorWithMessage() {
        // Given
        String errorMessage = "An error occurred";
        
        // When
        ErrorResponseDTO errorResponse = new ErrorResponseDTO(errorMessage);
        
        // Then
        assertNotNull(errorResponse);
        assertEquals(errorMessage, errorResponse.getMessage(), "Message should match");
        assertNotNull(errorResponse.getTimestamp(), "Timestamp should be initialized");
    }
    
    @Test
    public void testConstructorWithMessageAndStatus() {
        // Given
        String errorMessage = "Resource not found";
        int status = HttpStatus.NOT_FOUND.value();
        
        // When
        ErrorResponseDTO errorResponse = new ErrorResponseDTO(errorMessage, status);
        
        // Then
        assertNotNull(errorResponse);
        assertEquals(errorMessage, errorResponse.getMessage(), "Message should match");
        assertEquals(status, errorResponse.getStatus(), "Status should match");
        assertNotNull(errorResponse.getTimestamp(), "Timestamp should be initialized");
    }
    
    @Test
    public void testConstructorWithErrorCodeMessageAndStatus() {
        // Given
        String errorCode = Constants.ErrorCode.NOT_FOUND;
        String errorMessage = "Resource not found";
        int status = HttpStatus.NOT_FOUND.value();
        
        // When
        ErrorResponseDTO errorResponse = new ErrorResponseDTO(errorCode, errorMessage, status);
        
        // Then
        assertNotNull(errorResponse);
        assertEquals(errorCode, errorResponse.getErrorCode(), "Error code should match");
        assertEquals(errorMessage, errorResponse.getMessage(), "Message should match");
        assertEquals(status, errorResponse.getStatus(), "Status should match");
        assertNotNull(errorResponse.getTimestamp(), "Timestamp should be initialized");
    }
    
    @Test
    public void testGettersAndSetters() {
        // Given
        ErrorResponseDTO errorResponse = new ErrorResponseDTO();
        String errorCode = Constants.ErrorCode.VALIDATION_ERROR;
        String message = "Validation failed";
        int status = HttpStatus.BAD_REQUEST.value();
        String path = "/api/v1/applications";
        LocalDateTime timestamp = LocalDateTime.now();
        
        // When
        errorResponse.setErrorCode(errorCode);
        errorResponse.setMessage(message);
        errorResponse.setStatus(status);
        errorResponse.setPath(path);
        errorResponse.setTimestamp(timestamp);
        
        // Then
        assertEquals(errorCode, errorResponse.getErrorCode(), "Error code should match");
        assertEquals(message, errorResponse.getMessage(), "Message should match");
        assertEquals(status, errorResponse.getStatus(), "Status should match");
        assertEquals(path, errorResponse.getPath(), "Path should match");
        assertEquals(timestamp, errorResponse.getTimestamp(), "Timestamp should match");
    }
    
    @Test
    public void testAddValidationError() {
        // Given
        ErrorResponseDTO errorResponse = new ErrorResponseDTO("Validation failed", HttpStatus.BAD_REQUEST.value());
        String field = "email";
        String message = "must be a valid email address";
        Object rejectedValue = "invalid-email";
        
        // When
        errorResponse.addValidationError(field, message, rejectedValue);
        
        // Then
        assertNotNull(errorResponse.getDetails(), "Details should not be null");
        assertEquals(1, errorResponse.getDetails().size(), "Should have one validation error");
        
        ErrorResponseDTO.ValidationError validationError = errorResponse.getDetails().get(0);
        assertEquals(field, validationError.getField(), "Field should match");
        assertEquals(message, validationError.getMessage(), "Message should match");
        assertEquals(rejectedValue, validationError.getRejectedValue(), "Rejected value should match");
    }
    
    @Test
    public void testAddMultipleValidationErrors() {
        // Given
        ErrorResponseDTO errorResponse = new ErrorResponseDTO("Validation failed", HttpStatus.BAD_REQUEST.value());
        
        // When
        errorResponse.addValidationError("email", "must be a valid email address", "invalid-email");
        errorResponse.addValidationError("password", "must be at least 8 characters", "short");
        
        // Then
        assertNotNull(errorResponse.getDetails(), "Details should not be null");
        assertEquals(2, errorResponse.getDetails().size(), "Should have two validation errors");
    }
    
    @Test
    public void testAddValidationErrorWithoutRejectedValue() {
        // Given
        ErrorResponseDTO errorResponse = new ErrorResponseDTO("Validation failed", HttpStatus.BAD_REQUEST.value());
        String field = "email";
        String message = "must not be null";
        
        // When
        errorResponse.addValidationError(field, message);
        
        // Then
        assertNotNull(errorResponse.getDetails(), "Details should not be null");
        assertEquals(1, errorResponse.getDetails().size(), "Should have one validation error");
        
        ErrorResponseDTO.ValidationError validationError = errorResponse.getDetails().get(0);
        assertEquals(field, validationError.getField(), "Field should match");
        assertEquals(message, validationError.getMessage(), "Message should match");
        assertNull(validationError.getRejectedValue(), "Rejected value should be null");
    }
    
    @Test
    public void testBuilderPattern() {
        // Given
        String errorCode = Constants.ErrorCode.VALIDATION_ERROR;
        String message = "Validation failed";
        int status = HttpStatus.BAD_REQUEST.value();
        String path = "/api/v1/applications";
        LocalDateTime timestamp = LocalDateTime.now();
        
        // When
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(errorCode)
                .message(message)
                .status(status)
                .path(path)
                .timestamp(timestamp)
                .addValidationError("email", "must be a valid email address", "invalid-email")
                .build();
        
        // Then
        assertEquals(errorCode, errorResponse.getErrorCode(), "Error code should match");
        assertEquals(message, errorResponse.getMessage(), "Message should match");
        assertEquals(status, errorResponse.getStatus(), "Status should match");
        assertEquals(path, errorResponse.getPath(), "Path should match");
        assertEquals(timestamp, errorResponse.getTimestamp(), "Timestamp should match");
        
        assertNotNull(errorResponse.getDetails(), "Details should not be null");
        assertEquals(1, errorResponse.getDetails().size(), "Should have one validation error");
    }
    
    @Test
    public void testBuilderWithMultipleValidationErrors() {
        // When
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message("Validation failed")
                .status(HttpStatus.BAD_REQUEST.value())
                .path("/api/v1/applications")
                .addValidationError("email", "must be a valid email address", "invalid-email")
                .addValidationError("password", "must be at least 8 characters", "short")
                .build();
        
        // Then
        assertNotNull(errorResponse.getDetails(), "Details should not be null");
        assertEquals(2, errorResponse.getDetails().size(), "Should have two validation errors");
        
        // Verify first validation error
        ErrorResponseDTO.ValidationError firstError = errorResponse.getDetails().get(0);
        assertEquals("email", firstError.getField(), "Field should match");
        assertEquals("must be a valid email address", firstError.getMessage(), "Message should match");
        assertEquals("invalid-email", firstError.getRejectedValue(), "Rejected value should match");
        
        // Verify second validation error
        ErrorResponseDTO.ValidationError secondError = errorResponse.getDetails().get(1);
        assertEquals("password", secondError.getField(), "Field should match");
        assertEquals("must be at least 8 characters", secondError.getMessage(), "Message should match");
        assertEquals("short", secondError.getRejectedValue(), "Rejected value should match");
    }
    
    @Test
    public void testJsonSerialization() throws Exception {
        // Given
        LocalDateTime now = LocalDateTime.now();
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message("Validation failed")
                .status(HttpStatus.BAD_REQUEST.value())
                .path("/api/v1/applications")
                .timestamp(now)
                .addValidationError("email", "must be a valid email address", "invalid-email")
                .build();
        
        // When
        String json = objectMapper.writeValueAsString(errorResponse);
        
        // Then
        assertTrue(json.contains("\"errorCode\":\"" + Constants.ErrorCode.VALIDATION_ERROR + "\""), "JSON should contain error code");
        assertTrue(json.contains("\"message\":\"Validation failed\""), "JSON should contain message");
        assertTrue(json.contains("\"status\":400"), "JSON should contain status");
        assertTrue(json.contains("\"path\":\"/api/v1/applications\""), "JSON should contain path");
        assertTrue(json.contains("\"field\":\"email\""), "JSON should contain validation field");
        assertTrue(json.contains("\"message\":\"must be a valid email address\""), "JSON should contain validation message");
        assertTrue(json.contains("\"rejectedValue\":\"invalid-email\""), "JSON should contain rejected value");
        
        // Verify timestamp format
        String expectedTimestampPattern = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss"));
        assertTrue(json.contains(expectedTimestampPattern.substring(0, 16)), "JSON should contain formatted timestamp");
    }
    
    @Test
    public void testJsonDeserialization() throws Exception {
        // Given
        String json = "{\"errorCode\":\"GEN-002\",\"message\":\"Validation failed\",\"details\":[{\"field\":\"email\",\"message\":\"must be a valid email address\",\"rejectedValue\":\"invalid-email\"}],\"timestamp\":\"2023-05-15T10:30:45.123Z\",\"path\":\"/api/v1/applications\",\"status\":400}";
        
        // When
        ErrorResponseDTO errorResponse = objectMapper.readValue(json, ErrorResponseDTO.class);
        
        // Then
        assertEquals("GEN-002", errorResponse.getErrorCode(), "Error code should match");
        assertEquals("Validation failed", errorResponse.getMessage(), "Message should match");
        assertEquals(400, errorResponse.getStatus(), "Status should match");
        assertEquals("/api/v1/applications", errorResponse.getPath(), "Path should match");
        
        // Verify validation errors
        assertNotNull(errorResponse.getDetails(), "Details should not be null");
        assertEquals(1, errorResponse.getDetails().size(), "Should have one validation error");
        
        ErrorResponseDTO.ValidationError validationError = errorResponse.getDetails().get(0);
        assertEquals("email", validationError.getField(), "Field should match");
        assertEquals("must be a valid email address", validationError.getMessage(), "Message should match");
        assertEquals("invalid-email", validationError.getRejectedValue(), "Rejected value should match");
    }
    
    @Test
    public void testValidationErrorGettersAndSetters() {
        // Given
        ErrorResponseDTO.ValidationError validationError = new ErrorResponseDTO.ValidationError();
        String field = "email";
        String message = "must be a valid email address";
        Object rejectedValue = "invalid-email";
        
        // When
        validationError.setField(field);
        validationError.setMessage(message);
        validationError.setRejectedValue(rejectedValue);
        
        // Then
        assertEquals(field, validationError.getField(), "Field should match");
        assertEquals(message, validationError.getMessage(), "Message should match");
        assertEquals(rejectedValue, validationError.getRejectedValue(), "Rejected value should match");
    }
    
    @Test
    public void testValidationErrorConstructors() {
        // Test constructor with field and message
        ErrorResponseDTO.ValidationError error1 = new ErrorResponseDTO.ValidationError("email", "must be a valid email address");
        assertEquals("email", error1.getField(), "Field should match");
        assertEquals("must be a valid email address", error1.getMessage(), "Message should match");
        assertNull(error1.getRejectedValue(), "Rejected value should be null");
        
        // Test constructor with field, message, and rejected value
        ErrorResponseDTO.ValidationError error2 = new ErrorResponseDTO.ValidationError("email", "must be a valid email address", "invalid-email");
        assertEquals("email", error2.getField(), "Field should match");
        assertEquals("must be a valid email address", error2.getMessage(), "Message should match");
        assertEquals("invalid-email", error2.getRejectedValue(), "Rejected value should match");
    }
    
    @Test
    public void testErrorResponseWithNullDetails() {
        // Given
        ErrorResponseDTO errorResponse = new ErrorResponseDTO("An error occurred", HttpStatus.INTERNAL_SERVER_ERROR.value());
        
        // Then
        assertNull(errorResponse.getDetails(), "Details should be null");
    }
    
    @Test
    public void testSetDetailsDirectly() {
        // Given
        ErrorResponseDTO errorResponse = new ErrorResponseDTO();
        ErrorResponseDTO.ValidationError error1 = new ErrorResponseDTO.ValidationError("email", "must be a valid email address");
        ErrorResponseDTO.ValidationError error2 = new ErrorResponseDTO.ValidationError("password", "must be at least 8 characters");
        List<ErrorResponseDTO.ValidationError> details = List.of(error1, error2);
        
        // When
        errorResponse.setDetails(details);
        
        // Then
        assertNotNull(errorResponse.getDetails(), "Details should not be null");
        assertEquals(2, errorResponse.getDetails().size(), "Should have two validation errors");
        assertEquals("email", errorResponse.getDetails().get(0).getField(), "First error field should match");
        assertEquals("password", errorResponse.getDetails().get(1).getField(), "Second error field should match");
    }
}