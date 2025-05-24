package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.dto.ErrorResponseDTO.ValidationError;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link ValidationException} class.
 * 
 * These tests verify that ValidationException properly handles field-level validation errors,
 * correctly formats error messages, and maintains the appropriate HTTP status code (400 Bad Request).
 */
@DisplayName("ValidationException Tests")
class ValidationExceptionTest {

    @Test
    @DisplayName("Should initialize with message and set status code to 400")
    void shouldInitializeWithMessageAndSetStatusCodeTo400() {
        // Arrange & Act
        ValidationException exception = new ValidationException("Validation failed");
        
        // Assert
        assertEquals("Validation failed", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertEquals(400, exception.getStatusCode());
        assertEquals("ERR_400", exception.getErrorCode());
        assertFalse(exception.hasValidationErrors());
        assertEquals(0, exception.getValidationErrorCount());
    }
    
    @Test
    @DisplayName("Should initialize with message and cause")
    void shouldInitializeWithMessageAndCause() {
        // Arrange
        Throwable cause = new IllegalArgumentException("Original error");
        
        // Act
        ValidationException exception = new ValidationException("Validation failed", cause);
        
        // Assert
        assertEquals("Validation failed", exception.getMessage());
        assertEquals(cause, exception.getCause());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertEquals(400, exception.getStatusCode());
        assertFalse(exception.hasValidationErrors());
    }
    
    @Test
    @DisplayName("Should initialize with field and error message")
    void shouldInitializeWithFieldAndErrorMessage() {
        // Arrange & Act
        ValidationException exception = new ValidationException(
                "Validation failed", "email", "Invalid email format");
        
        // Assert
        assertEquals("Validation failed", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(1, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Invalid email format", errors.get(0).getMessage());
        assertNull(errors.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should initialize with field, error message, and rejected value")
    void shouldInitializeWithFieldErrorMessageAndRejectedValue() {
        // Arrange & Act
        String rejectedValue = "not-an-email";
        ValidationException exception = new ValidationException(
                "Validation failed", "email", "Invalid email format", rejectedValue);
        
        // Assert
        assertEquals("Validation failed", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(1, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Invalid email format", errors.get(0).getMessage());
        assertEquals(rejectedValue, errors.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should initialize with a list of validation errors")
    void shouldInitializeWithListOfValidationErrors() {
        // Arrange
        List<ValidationError> validationErrors = new ArrayList<>();
        validationErrors.add(new ValidationError("email", "Invalid email format", "not-an-email"));
        validationErrors.add(new ValidationError("phone", "Invalid phone number", "123"));
        
        // Act
        ValidationException exception = new ValidationException("Multiple validation errors", validationErrors);
        
        // Assert
        assertEquals("Multiple validation errors", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(2, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(2, errors.size());
        
        assertEquals("email", errors.get(0).getField());
        assertEquals("Invalid email format", errors.get(0).getMessage());
        assertEquals("not-an-email", errors.get(0).getRejectedValue());
        
        assertEquals("phone", errors.get(1).getField());
        assertEquals("Invalid phone number", errors.get(1).getMessage());
        assertEquals("123", errors.get(1).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should add validation errors after initialization")
    void shouldAddValidationErrorsAfterInitialization() {
        // Arrange
        ValidationException exception = new ValidationException("Validation failed");
        
        // Act
        exception.addValidationError("email", "Invalid email format")
                .addValidationError("phone", "Invalid phone number", "123");
        
        // Assert
        assertTrue(exception.hasValidationErrors());
        assertEquals(2, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(2, errors.size());
        
        assertEquals("email", errors.get(0).getField());
        assertEquals("Invalid email format", errors.get(0).getMessage());
        assertNull(errors.get(0).getRejectedValue());
        
        assertEquals("phone", errors.get(1).getField());
        assertEquals("Invalid phone number", errors.get(1).getMessage());
        assertEquals("123", errors.get(1).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should create exception for required field")
    void shouldCreateExceptionForRequiredField() {
        // Arrange & Act
        ValidationException exception = ValidationException.requiredField("email");
        
        // Assert
        assertEquals("Required field is missing", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals("email", errors.get(0).getField());
        assertEquals("Field is required and cannot be empty", errors.get(0).getMessage());
    }
    
    @Test
    @DisplayName("Should create exception for invalid format")
    void shouldCreateExceptionForInvalidFormat() {
        // Arrange & Act
        String rejectedValue = "not-an-email";
        ValidationException exception = ValidationException.invalidFormat(
                "email", "user@example.com", rejectedValue);
        
        // Assert
        assertEquals("Invalid field format", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals("email", errors.get(0).getField());
        assertEquals("Field must match format: user@example.com", errors.get(0).getMessage());
        assertEquals(rejectedValue, errors.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should create exception for maximum length exceeded")
    void shouldCreateExceptionForMaxLengthExceeded() {
        // Arrange & Act
        String rejectedValue = "This string is too long";
        ValidationException exception = ValidationException.maxLengthExceeded(
                "name", 10, rejectedValue);
        
        // Assert
        assertEquals("Maximum length exceeded", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals("name", errors.get(0).getField());
        assertEquals("Field must not exceed 10 characters", errors.get(0).getMessage());
        assertEquals(rejectedValue, errors.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should create exception for minimum length not met")
    void shouldCreateExceptionForMinLengthNotMet() {
        // Arrange & Act
        String rejectedValue = "short";
        ValidationException exception = ValidationException.minLengthNotMet(
                "password", 8, rejectedValue);
        
        // Assert
        assertEquals("Minimum length not met", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals("password", errors.get(0).getField());
        assertEquals("Field must be at least 8 characters", errors.get(0).getMessage());
        assertEquals(rejectedValue, errors.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should create exception for maximum value exceeded")
    void shouldCreateExceptionForMaxValueExceeded() {
        // Arrange & Act
        Integer rejectedValue = 150;
        ValidationException exception = ValidationException.maxValueExceeded(
                "age", 100, rejectedValue);
        
        // Assert
        assertEquals("Maximum value exceeded", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals("age", errors.get(0).getField());
        assertEquals("Field must not exceed 100", errors.get(0).getMessage());
        assertEquals(rejectedValue, errors.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should create exception for minimum value not met")
    void shouldCreateExceptionForMinValueNotMet() {
        // Arrange & Act
        Integer rejectedValue = 15;
        ValidationException exception = ValidationException.minValueNotMet(
                "age", 18, rejectedValue);
        
        // Assert
        assertEquals("Minimum value not met", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals("age", errors.get(0).getField());
        assertEquals("Field must be at least 18", errors.get(0).getMessage());
        assertEquals(rejectedValue, errors.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should return unmodifiable list of validation errors")
    void shouldReturnUnmodifiableListOfValidationErrors() {
        // Arrange
        ValidationException exception = new ValidationException("Validation failed");
        exception.addValidationError("email", "Invalid email format");
        
        // Act & Assert
        List<ValidationError> errors = exception.getValidationErrors();
        assertThrows(UnsupportedOperationException.class, () -> errors.add(new ValidationError("test", "test")));
    }
}