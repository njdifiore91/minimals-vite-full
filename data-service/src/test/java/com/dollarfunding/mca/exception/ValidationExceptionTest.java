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
 * <p>
 * These tests verify that the ValidationException properly handles validation errors
 * with appropriate HTTP status codes, error messages, and field-level validation details.
 * </p>
 */
public class ValidationExceptionTest {

    @Test
    @DisplayName("Should create ValidationException with message only")
    public void testCreateWithMessageOnly() {
        // Arrange & Act
        String message = "Validation failed";
        ValidationException exception = new ValidationException(message);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode());
        assertFalse(exception.hasValidationErrors());
        assertEquals(0, exception.getValidationErrorCount());
        assertTrue(exception.getValidationErrors().isEmpty());
    }
    
    @Test
    @DisplayName("Should create ValidationException with message and cause")
    public void testCreateWithMessageAndCause() {
        // Arrange & Act
        String message = "Validation failed";
        IllegalArgumentException cause = new IllegalArgumentException("Invalid argument");
        ValidationException exception = new ValidationException(message, cause);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertEquals(cause, exception.getCause());
        assertFalse(exception.hasValidationErrors());
        assertEquals(0, exception.getValidationErrorCount());
        assertTrue(exception.getValidationErrors().isEmpty());
    }
    
    @Test
    @DisplayName("Should create ValidationException with message, field, and error message")
    public void testCreateWithMessageFieldAndErrorMessage() {
        // Arrange & Act
        String message = "Validation failed";
        String field = "email";
        String errorMessage = "Email is invalid";
        ValidationException exception = new ValidationException(message, field, errorMessage);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(1, errors.size());
        assertEquals(field, errors.get(0).getField());
        assertEquals(errorMessage, errors.get(0).getMessage());
    }
    
    @Test
    @DisplayName("Should create ValidationException with message and validation errors list")
    public void testCreateWithMessageAndValidationErrorsList() {
        // Arrange
        String message = "Validation failed";
        List<ValidationError> validationErrors = new ArrayList<>();
        validationErrors.add(new ValidationError("email", "Email is invalid"));
        validationErrors.add(new ValidationError("password", "Password is too short"));
        
        // Act
        ValidationException exception = new ValidationException(message, validationErrors);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(2, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(2, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("password", errors.get(1).getField());
        assertEquals("Password is too short", errors.get(1).getMessage());
    }
    
    @Test
    @DisplayName("Should create ValidationException with error code, message, and validation errors list")
    public void testCreateWithErrorCodeMessageAndValidationErrorsList() {
        // Arrange
        String errorCode = "VAL-001";
        String message = "Validation failed";
        List<ValidationError> validationErrors = new ArrayList<>();
        validationErrors.add(new ValidationError("email", "Email is invalid"));
        validationErrors.add(new ValidationError("password", "Password is too short"));
        
        // Act
        ValidationException exception = new ValidationException(errorCode, message, validationErrors);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(errorCode, exception.getErrorCode());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertTrue(exception.hasValidationErrors());
        assertEquals(2, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(2, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("password", errors.get(1).getField());
        assertEquals("Password is too short", errors.get(1).getMessage());
    }
    
    @Test
    @DisplayName("Should add validation error to existing exception")
    public void testAddValidationError() {
        // Arrange
        ValidationException exception = new ValidationException("Validation failed");
        
        // Act
        exception.addValidationError("email", "Email is invalid");
        
        // Assert
        assertTrue(exception.hasValidationErrors());
        assertEquals(1, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(1, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        
        // Add another validation error
        exception.addValidationError("password", "Password is too short");
        
        // Assert again
        assertTrue(exception.hasValidationErrors());
        assertEquals(2, exception.getValidationErrorCount());
        
        errors = exception.getValidationErrors();
        assertEquals(2, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("password", errors.get(1).getField());
        assertEquals("Password is too short", errors.get(1).getMessage());
    }
    
    @Test
    @DisplayName("Should add multiple validation errors to existing exception")
    public void testAddValidationErrors() {
        // Arrange
        ValidationException exception = new ValidationException("Validation failed");
        List<ValidationError> validationErrors = new ArrayList<>();
        validationErrors.add(new ValidationError("email", "Email is invalid"));
        validationErrors.add(new ValidationError("password", "Password is too short"));
        
        // Act
        exception.addValidationErrors(validationErrors);
        
        // Assert
        assertTrue(exception.hasValidationErrors());
        assertEquals(2, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(2, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("password", errors.get(1).getField());
        assertEquals("Password is too short", errors.get(1).getMessage());
        
        // Add more validation errors
        List<ValidationError> moreErrors = new ArrayList<>();
        moreErrors.add(new ValidationError("name", "Name is required"));
        moreErrors.add(new ValidationError("age", "Age must be positive"));
        exception.addValidationErrors(moreErrors);
        
        // Assert again
        assertTrue(exception.hasValidationErrors());
        assertEquals(4, exception.getValidationErrorCount());
        
        errors = exception.getValidationErrors();
        assertEquals(4, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("password", errors.get(1).getField());
        assertEquals("Password is too short", errors.get(1).getMessage());
        assertEquals("name", errors.get(2).getField());
        assertEquals("Name is required", errors.get(2).getMessage());
        assertEquals("age", errors.get(3).getField());
        assertEquals("Age must be positive", errors.get(3).getMessage());
    }
    
    @Test
    @DisplayName("Should verify validation errors are unmodifiable")
    public void testValidationErrorsAreUnmodifiable() {
        // Arrange
        ValidationException exception = new ValidationException("Validation failed", "email", "Email is invalid");
        
        // Act & Assert
        assertThrows(UnsupportedOperationException.class, () -> {
            exception.getValidationErrors().add(new ValidationError("password", "Password is too short"));
        });
    }
    
    @Test
    @DisplayName("Should verify hasValidationErrors and getValidationErrorCount methods")
    public void testHasValidationErrorsAndGetValidationErrorCount() {
        // Arrange & Act
        ValidationException emptyException = new ValidationException("Validation failed");
        
        // Assert
        assertFalse(emptyException.hasValidationErrors());
        assertEquals(0, emptyException.getValidationErrorCount());
        
        // Arrange & Act
        ValidationException exceptionWithErrors = new ValidationException("Validation failed", "email", "Email is invalid");
        
        // Assert
        assertTrue(exceptionWithErrors.hasValidationErrors());
        assertEquals(1, exceptionWithErrors.getValidationErrorCount());
        
        // Add more errors
        exceptionWithErrors.addValidationError("password", "Password is too short");
        
        // Assert again
        assertTrue(exceptionWithErrors.hasValidationErrors());
        assertEquals(2, exceptionWithErrors.getValidationErrorCount());
    }
    
    @Test
    @DisplayName("Should verify method chaining for addValidationError")
    public void testMethodChainingForAddValidationError() {
        // Arrange
        ValidationException exception = new ValidationException("Validation failed");
        
        // Act
        exception
            .addValidationError("email", "Email is invalid")
            .addValidationError("password", "Password is too short")
            .addValidationError("name", "Name is required");
        
        // Assert
        assertTrue(exception.hasValidationErrors());
        assertEquals(3, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(3, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("password", errors.get(1).getField());
        assertEquals("Password is too short", errors.get(1).getMessage());
        assertEquals("name", errors.get(2).getField());
        assertEquals("Name is required", errors.get(2).getMessage());
    }
    
    @Test
    @DisplayName("Should verify method chaining for addValidationErrors")
    public void testMethodChainingForAddValidationErrors() {
        // Arrange
        ValidationException exception = new ValidationException("Validation failed");
        List<ValidationError> firstBatch = new ArrayList<>();
        firstBatch.add(new ValidationError("email", "Email is invalid"));
        firstBatch.add(new ValidationError("password", "Password is too short"));
        
        List<ValidationError> secondBatch = new ArrayList<>();
        secondBatch.add(new ValidationError("name", "Name is required"));
        secondBatch.add(new ValidationError("age", "Age must be positive"));
        
        // Act
        exception
            .addValidationErrors(firstBatch)
            .addValidationErrors(secondBatch);
        
        // Assert
        assertTrue(exception.hasValidationErrors());
        assertEquals(4, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(4, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("password", errors.get(1).getField());
        assertEquals("Password is too short", errors.get(1).getMessage());
        assertEquals("name", errors.get(2).getField());
        assertEquals("Name is required", errors.get(2).getMessage());
        assertEquals("age", errors.get(3).getField());
        assertEquals("Age must be positive", errors.get(3).getMessage());
    }
    
    @Test
    @DisplayName("Should verify ValidationException with rejected value")
    public void testValidationExceptionWithRejectedValue() {
        // Arrange
        List<ValidationError> validationErrors = new ArrayList<>();
        validationErrors.add(new ValidationError("email", "Email is invalid", "invalid-email"));
        validationErrors.add(new ValidationError("age", "Age must be positive", -5));
        
        // Act
        ValidationException exception = new ValidationException("Validation failed", validationErrors);
        
        // Assert
        assertTrue(exception.hasValidationErrors());
        assertEquals(2, exception.getValidationErrorCount());
        
        List<ValidationError> errors = exception.getValidationErrors();
        assertEquals(2, errors.size());
        assertEquals("email", errors.get(0).getField());
        assertEquals("Email is invalid", errors.get(0).getMessage());
        assertEquals("invalid-email", errors.get(0).getRejectedValue());
        assertEquals("age", errors.get(1).getField());
        assertEquals("Age must be positive", errors.get(1).getMessage());
        assertEquals(-5, errors.get(1).getRejectedValue());
    }
}