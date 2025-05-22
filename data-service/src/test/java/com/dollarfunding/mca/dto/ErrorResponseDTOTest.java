package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link ErrorResponseDTO} that validates the error response structure,
 * JSON serialization/deserialization, and builder pattern functionality.
 * 
 * Tests ensure that the DTO properly formats error information, includes appropriate
 * timestamps and request paths, and handles validation errors with field-level details.
 */
public class ErrorResponseDTOTest {

    private ObjectMapper objectMapper;
    private ErrorResponseDTO errorResponseDTO;
    private static final String ERROR_CODE = "VALIDATION_ERROR";
    private static final String ERROR_MESSAGE = "Validation failed for the request";
    private static final int HTTP_STATUS = 400;
    private static final String REQUEST_PATH = "/api/v1/applications";
    private static final LocalDateTime TIMESTAMP = LocalDateTime.of(2023, 1, 1, 10, 0, 0);

    @BeforeEach
    void setUp() {
        // Configure ObjectMapper with JavaTimeModule for LocalDateTime serialization
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        
        // Create test error response DTO with all required fields
        errorResponseDTO = new ErrorResponseDTO();
        errorResponseDTO.setErrorCode(ERROR_CODE);
        errorResponseDTO.setMessage(ERROR_MESSAGE);
        errorResponseDTO.setStatus(HTTP_STATUS);
        errorResponseDTO.setPath(REQUEST_PATH);
        errorResponseDTO.setTimestamp(TIMESTAMP);
    }

    @Test
    @DisplayName("Should create ErrorResponseDTO with default constructor correctly")
    void shouldCreateWithDefaultConstructor() {
        // Create with default constructor
        ErrorResponseDTO dto = new ErrorResponseDTO();
        
        // Assert timestamp is set automatically
        assertNotNull(dto.getTimestamp());
        assertNull(dto.getErrorCode());
        assertNull(dto.getMessage());
        assertNull(dto.getPath());
        assertEquals(0, dto.getStatus());
        assertNull(dto.getDetails());
    }

    @Test
    @DisplayName("Should create ErrorResponseDTO with message constructor correctly")
    void shouldCreateWithMessageConstructor() {
        // Create with message constructor
        String message = "Test error message";
        ErrorResponseDTO dto = new ErrorResponseDTO(message);
        
        // Assert fields are set correctly
        assertNotNull(dto.getTimestamp());
        assertEquals(message, dto.getMessage());
        assertNull(dto.getErrorCode());
        assertNull(dto.getPath());
        assertEquals(0, dto.getStatus());
        assertNull(dto.getDetails());
    }

    @Test
    @DisplayName("Should create ErrorResponseDTO with message and status constructor correctly")
    void shouldCreateWithMessageAndStatusConstructor() {
        // Create with message and status constructor
        String message = "Test error message";
        int status = 404;
        ErrorResponseDTO dto = new ErrorResponseDTO(message, status);
        
        // Assert fields are set correctly
        assertNotNull(dto.getTimestamp());
        assertEquals(message, dto.getMessage());
        assertEquals(status, dto.getStatus());
        assertNull(dto.getErrorCode());
        assertNull(dto.getPath());
        assertNull(dto.getDetails());
    }

    @Test
    @DisplayName("Should create ErrorResponseDTO with errorCode, message, and status constructor correctly")
    void shouldCreateWithErrorCodeMessageAndStatusConstructor() {
        // Create with errorCode, message, and status constructor
        String errorCode = "NOT_FOUND";
        String message = "Resource not found";
        int status = 404;
        ErrorResponseDTO dto = new ErrorResponseDTO(errorCode, message, status);
        
        // Assert fields are set correctly
        assertNotNull(dto.getTimestamp());
        assertEquals(errorCode, dto.getErrorCode());
        assertEquals(message, dto.getMessage());
        assertEquals(status, dto.getStatus());
        assertNull(dto.getPath());
        assertNull(dto.getDetails());
    }

    @Test
    @DisplayName("Should set and get all fields correctly")
    void shouldSetAndGetAllFieldsCorrectly() {
        // Create empty DTO
        ErrorResponseDTO dto = new ErrorResponseDTO();
        
        // Set all fields
        dto.setErrorCode(ERROR_CODE);
        dto.setMessage(ERROR_MESSAGE);
        dto.setStatus(HTTP_STATUS);
        dto.setPath(REQUEST_PATH);
        dto.setTimestamp(TIMESTAMP);
        
        // Assert all fields are set correctly
        assertEquals(ERROR_CODE, dto.getErrorCode());
        assertEquals(ERROR_MESSAGE, dto.getMessage());
        assertEquals(HTTP_STATUS, dto.getStatus());
        assertEquals(REQUEST_PATH, dto.getPath());
        assertEquals(TIMESTAMP, dto.getTimestamp());
    }

    @Test
    @DisplayName("Should build ErrorResponseDTO with builder pattern correctly")
    void shouldBuildWithBuilderPatternCorrectly() {
        // Build DTO using builder pattern
        ErrorResponseDTO dto = ErrorResponseDTO.builder()
                .errorCode(ERROR_CODE)
                .message(ERROR_MESSAGE)
                .status(HTTP_STATUS)
                .path(REQUEST_PATH)
                .timestamp(TIMESTAMP)
                .build();
        
        // Assert all fields are set correctly
        assertEquals(ERROR_CODE, dto.getErrorCode());
        assertEquals(ERROR_MESSAGE, dto.getMessage());
        assertEquals(HTTP_STATUS, dto.getStatus());
        assertEquals(REQUEST_PATH, dto.getPath());
        assertEquals(TIMESTAMP, dto.getTimestamp());
    }

    @Test
    @DisplayName("Should build ErrorResponseDTO with validation errors correctly")
    void shouldBuildWithValidationErrorsCorrectly() {
        // Build DTO with validation errors using builder pattern
        ErrorResponseDTO dto = ErrorResponseDTO.builder()
                .errorCode(ERROR_CODE)
                .message(ERROR_MESSAGE)
                .status(HTTP_STATUS)
                .path(REQUEST_PATH)
                .addValidationError("name", "Name is required")
                .addValidationError("email", "Email is invalid", "invalid-email")
                .build();
        
        // Assert validation errors are set correctly
        assertNotNull(dto.getDetails());
        assertEquals(2, dto.getDetails().size());
        
        // Assert first validation error
        ErrorResponseDTO.ValidationError firstError = dto.getDetails().get(0);
        assertEquals("name", firstError.getField());
        assertEquals("Name is required", firstError.getMessage());
        assertNull(firstError.getRejectedValue());
        
        // Assert second validation error
        ErrorResponseDTO.ValidationError secondError = dto.getDetails().get(1);
        assertEquals("email", secondError.getField());
        assertEquals("Email is invalid", secondError.getMessage());
        assertEquals("invalid-email", secondError.getRejectedValue());
    }

    @Test
    @DisplayName("Should add validation errors to existing ErrorResponseDTO correctly")
    void shouldAddValidationErrorsCorrectly() {
        // Add validation errors to existing DTO
        errorResponseDTO.addValidationError("name", "Name is required");
        errorResponseDTO.addValidationError("email", "Email is invalid", "invalid-email");
        
        // Assert validation errors are added correctly
        assertNotNull(errorResponseDTO.getDetails());
        assertEquals(2, errorResponseDTO.getDetails().size());
        
        // Assert first validation error
        ErrorResponseDTO.ValidationError firstError = errorResponseDTO.getDetails().get(0);
        assertEquals("name", firstError.getField());
        assertEquals("Name is required", firstError.getMessage());
        assertNull(firstError.getRejectedValue());
        
        // Assert second validation error
        ErrorResponseDTO.ValidationError secondError = errorResponseDTO.getDetails().get(1);
        assertEquals("email", secondError.getField());
        assertEquals("Email is invalid", secondError.getMessage());
        assertEquals("invalid-email", secondError.getRejectedValue());
    }

    @Test
    @DisplayName("Should serialize ErrorResponseDTO to JSON correctly")
    void shouldSerializeToJsonCorrectly() throws IOException {
        // Add validation errors
        errorResponseDTO.addValidationError("name", "Name is required");
        errorResponseDTO.addValidationError("email", "Email is invalid", "invalid-email");
        
        // Serialize to JSON
        String json = objectMapper.writeValueAsString(errorResponseDTO);
        
        // Assert JSON contains expected fields
        assertTrue(json.contains("\"errorCode\":\"" + ERROR_CODE + "\""));
        assertTrue(json.contains("\"message\":\"" + ERROR_MESSAGE + "\""));
        assertTrue(json.contains("\"status\":" + HTTP_STATUS));
        assertTrue(json.contains("\"path\":\"" + REQUEST_PATH + "\""));
        assertTrue(json.contains("\"timestamp\":\"2023-01-01T10:00:00.000Z\""));
        assertTrue(json.contains("\"details\":"));
        assertTrue(json.contains("\"field\":\"name\""));
        assertTrue(json.contains("\"message\":\"Name is required\""));
        assertTrue(json.contains("\"field\":\"email\""));
        assertTrue(json.contains("\"message\":\"Email is invalid\""));
        assertTrue(json.contains("\"rejectedValue\":\"invalid-email\""));
    }

    @Test
    @DisplayName("Should deserialize JSON to ErrorResponseDTO correctly")
    void shouldDeserializeFromJsonCorrectly() throws IOException {
        // Add validation errors
        errorResponseDTO.addValidationError("name", "Name is required");
        errorResponseDTO.addValidationError("email", "Email is invalid", "invalid-email");
        
        // Serialize to JSON and then deserialize back
        String json = objectMapper.writeValueAsString(errorResponseDTO);
        ErrorResponseDTO deserializedDTO = objectMapper.readValue(json, ErrorResponseDTO.class);
        
        // Assert deserialized DTO matches original
        assertEquals(ERROR_CODE, deserializedDTO.getErrorCode());
        assertEquals(ERROR_MESSAGE, deserializedDTO.getMessage());
        assertEquals(HTTP_STATUS, deserializedDTO.getStatus());
        assertEquals(REQUEST_PATH, deserializedDTO.getPath());
        assertEquals(TIMESTAMP, deserializedDTO.getTimestamp());
        
        // Assert validation errors
        assertNotNull(deserializedDTO.getDetails());
        assertEquals(2, deserializedDTO.getDetails().size());
        
        // Assert first validation error
        ErrorResponseDTO.ValidationError firstError = deserializedDTO.getDetails().get(0);
        assertEquals("name", firstError.getField());
        assertEquals("Name is required", firstError.getMessage());
        assertNull(firstError.getRejectedValue());
        
        // Assert second validation error
        ErrorResponseDTO.ValidationError secondError = deserializedDTO.getDetails().get(1);
        assertEquals("email", secondError.getField());
        assertEquals("Email is invalid", secondError.getMessage());
        assertEquals("invalid-email", secondError.getRejectedValue());
    }

    @Test
    @DisplayName("Should handle null fields in JSON serialization correctly")
    void shouldHandleNullFieldsInJsonSerializationCorrectly() throws IOException {
        // Create DTO with only required fields
        ErrorResponseDTO dto = new ErrorResponseDTO();
        dto.setMessage(ERROR_MESSAGE);
        
        // Serialize to JSON
        String json = objectMapper.writeValueAsString(dto);
        
        // Assert JSON contains only non-null fields
        assertTrue(json.contains("\"message\":\"" + ERROR_MESSAGE + "\""));
        assertTrue(json.contains("\"timestamp\":"));
        assertFalse(json.contains("\"errorCode\":"));
        assertFalse(json.contains("\"path\":"));
        assertFalse(json.contains("\"details\":"));
    }

    @Test
    @DisplayName("Should create ValidationError with field and message constructor correctly")
    void shouldCreateValidationErrorWithFieldAndMessageConstructorCorrectly() {
        // Create ValidationError with field and message
        String field = "name";
        String message = "Name is required";
        ErrorResponseDTO.ValidationError validationError = new ErrorResponseDTO.ValidationError(field, message);
        
        // Assert fields are set correctly
        assertEquals(field, validationError.getField());
        assertEquals(message, validationError.getMessage());
        assertNull(validationError.getRejectedValue());
    }

    @Test
    @DisplayName("Should create ValidationError with field, message, and rejectedValue constructor correctly")
    void shouldCreateValidationErrorWithFieldMessageAndRejectedValueConstructorCorrectly() {
        // Create ValidationError with field, message, and rejectedValue
        String field = "email";
        String message = "Email is invalid";
        String rejectedValue = "invalid-email";
        ErrorResponseDTO.ValidationError validationError = 
                new ErrorResponseDTO.ValidationError(field, message, rejectedValue);
        
        // Assert fields are set correctly
        assertEquals(field, validationError.getField());
        assertEquals(message, validationError.getMessage());
        assertEquals(rejectedValue, validationError.getRejectedValue());
    }

    @Test
    @DisplayName("Should set and get ValidationError fields correctly")
    void shouldSetAndGetValidationErrorFieldsCorrectly() {
        // Create empty ValidationError
        ErrorResponseDTO.ValidationError validationError = new ErrorResponseDTO.ValidationError();
        
        // Set fields
        String field = "name";
        String message = "Name is required";
        String rejectedValue = "invalid-name";
        validationError.setField(field);
        validationError.setMessage(message);
        validationError.setRejectedValue(rejectedValue);
        
        // Assert fields are set correctly
        assertEquals(field, validationError.getField());
        assertEquals(message, validationError.getMessage());
        assertEquals(rejectedValue, validationError.getRejectedValue());
    }

    @Test
    @DisplayName("Should handle HTTP status codes correctly")
    void shouldHandleHttpStatusCodesCorrectly() {
        // Create DTOs with different status codes
        ErrorResponseDTO badRequestDTO = new ErrorResponseDTO("Bad Request", 400);
        ErrorResponseDTO notFoundDTO = new ErrorResponseDTO("Not Found", 404);
        ErrorResponseDTO serverErrorDTO = new ErrorResponseDTO("Server Error", 500);
        
        // Assert status codes are set correctly
        assertEquals(400, badRequestDTO.getStatus());
        assertEquals(404, notFoundDTO.getStatus());
        assertEquals(500, serverErrorDTO.getStatus());
    }

    @Test
    @DisplayName("Should handle method chaining with addValidationError correctly")
    void shouldHandleMethodChainingWithAddValidationErrorCorrectly() {
        // Use method chaining with addValidationError
        ErrorResponseDTO dto = new ErrorResponseDTO()
                .addValidationError("field1", "Error 1")
                .addValidationError("field2", "Error 2", "invalid-value");
        
        // Assert validation errors are added correctly
        List<ErrorResponseDTO.ValidationError> details = dto.getDetails();
        assertNotNull(details);
        assertEquals(2, details.size());
        assertEquals("field1", details.get(0).getField());
        assertEquals("field2", details.get(1).getField());
    }
}