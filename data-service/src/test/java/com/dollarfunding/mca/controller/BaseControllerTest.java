package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.exception.AuthorizationException;
import com.dollarfunding.mca.exception.BaseException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.context.request.WebRequest;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the abstract BaseController class.
 * 
 * These tests verify the functionality of the BaseController by using a concrete
 * implementation of the abstract class. The tests cover global exception handling,
 * standardized response formatting, and utility methods for consistent API behavior.
 */
@ExtendWith(MockitoExtension.class)
public class BaseControllerTest {

    /**
     * Concrete implementation of BaseController for testing purposes.
     */
    private static class TestController extends BaseController {
        // No additional implementation needed for testing
    }

    private TestController controller;

    @Mock
    private WebRequest webRequest;

    @Mock
    private BindingResult bindingResult;

    @Mock
    private Logger mockLogger;

    @BeforeEach
    void setUp() {
        controller = new TestController();
        // Mock the logger to test logging behavior
        try {
            // Use reflection to set the logger field in BaseController
            java.lang.reflect.Field loggerField = BaseController.class.getDeclaredField("logger");
            loggerField.setAccessible(true);
            loggerField.set(controller, mockLogger);
        } catch (Exception e) {
            fail("Failed to set mock logger: " + e.getMessage());
        }

        // Mock the WebRequest to return a consistent path
        when(webRequest.getDescription(false)).thenReturn("uri=/api/v1/test");
    }

    @Test
    @DisplayName("Should create a success response with HTTP status 200")
    void testCreateSuccessResponse() {
        // Arrange
        String testData = "Test Data";

        // Act
        ResponseEntity<String> response = controller.createSuccessResponse(testData);

        // Assert
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(testData, response.getBody());
    }

    @Test
    @DisplayName("Should create a created response with HTTP status 201")
    void testCreateCreatedResponse() {
        // Arrange
        String testData = "Created Resource";

        // Act
        ResponseEntity<String> response = controller.createCreatedResponse(testData);

        // Assert
        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        assertEquals(testData, response.getBody());
    }

    @Test
    @DisplayName("Should create a custom response with specified HTTP status")
    void testCreateResponse() {
        // Arrange
        String testData = "Custom Response";
        HttpStatus customStatus = HttpStatus.ACCEPTED;

        // Act
        ResponseEntity<String> response = controller.createResponse(testData, customStatus);

        // Assert
        assertEquals(customStatus, response.getStatusCode());
        assertEquals(testData, response.getBody());
    }

    @Test
    @DisplayName("Should create a paginated response with metadata and links")
    void testCreatePageResponse() {
        // Arrange
        List<String> items = Arrays.asList("Item 1", "Item 2", "Item 3");
        Page<String> page = new PageImpl<>(items, PageRequest.of(0, 10), 3);

        // Act
        ResponseEntity<PageResponseDTO<String>> response = controller.createPageResponse(page);

        // Assert
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(items, response.getBody().getContent());
        assertEquals(3, response.getBody().getMetadata().getTotalElements());
        assertEquals(0, response.getBody().getMetadata().getCurrentPage());
        assertEquals(1, response.getBody().getMetadata().getTotalPages());
        assertEquals(10, response.getBody().getMetadata().getPageSize());
    }

    @Test
    @DisplayName("Should create an error response with specified message and status")
    void testCreateErrorResponse() {
        // Arrange
        String errorMessage = "Test error message";
        HttpStatus errorStatus = HttpStatus.BAD_REQUEST;

        // Act
        ResponseEntity<ErrorResponseDTO> response = controller.createErrorResponse(
                errorMessage, errorStatus, webRequest);

        // Assert
        assertEquals(errorStatus, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(errorMessage, response.getBody().getMessage());
        assertEquals(errorStatus.value(), response.getBody().getStatus());
        assertEquals(errorStatus.getReasonPhrase(), response.getBody().getError());
        assertEquals("/api/v1/test", response.getBody().getPath());
        assertNotNull(response.getBody().getTimestamp());
    }

    @Test
    @DisplayName("Should handle ResourceNotFoundException with 404 status")
    void testHandleResourceNotFoundException() {
        // Arrange
        String errorMessage = "Resource not found";
        ResourceNotFoundException ex = new ResourceNotFoundException(errorMessage);

        // Act
        ResponseEntity<ErrorResponseDTO> response = controller.handleResourceNotFoundException(ex, webRequest);

        // Assert
        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertEquals(errorMessage, response.getBody().getMessage());
        assertEquals(HttpStatus.NOT_FOUND.value(), response.getBody().getStatus());
        
        // Verify logging
        verify(mockLogger).warn(contains("Resource not found"), eq(errorMessage));
    }

    @Test
    @DisplayName("Should handle AuthorizationException with 403 status")
    void testHandleAuthorizationException() {
        // Arrange
        String errorMessage = "Access denied";
        AuthorizationException ex = new AuthorizationException(errorMessage);

        // Act
        ResponseEntity<ErrorResponseDTO> response = controller.handleAuthorizationException(ex, webRequest);

        // Assert
        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        assertEquals(errorMessage, response.getBody().getMessage());
        assertEquals(HttpStatus.FORBIDDEN.value(), response.getBody().getStatus());
        
        // Verify logging
        verify(mockLogger).warn(contains("Authorization failure"), eq(errorMessage));
    }

    @Test
    @DisplayName("Should handle ValidationException with 400 status and validation errors")
    void testHandleValidationException() {
        // Arrange
        String errorMessage = "Validation failed";
        Map<String, String> errors = new HashMap<>();
        errors.put("field1", "Field 1 is required");
        errors.put("field2", "Field 2 must be a valid email");
        ValidationException ex = new ValidationException(errorMessage, errors);

        // Act
        ResponseEntity<ErrorResponseDTO> response = controller.handleValidationException(ex, webRequest);

        // Assert
        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals(errorMessage, response.getBody().getMessage());
        assertEquals(HttpStatus.BAD_REQUEST.value(), response.getBody().getStatus());
        assertEquals(errors, response.getBody().getValidationErrors());
        
        // Verify logging
        verify(mockLogger).warn(contains("Validation error"), eq(errorMessage));
    }

    @Test
    @DisplayName("Should handle MethodArgumentNotValidException with 400 status and field errors")
    void testHandleMethodArgumentNotValidException() {
        // Arrange
        MethodArgumentNotValidException ex = mock(MethodArgumentNotValidException.class);
        BindingResult bindingResult = mock(BindingResult.class);
        when(ex.getBindingResult()).thenReturn(bindingResult);
        
        List<FieldError> fieldErrors = Arrays.asList(
            new FieldError("testObject", "field1", "Field 1 is required"),
            new FieldError("testObject", "field2", "Field 2 must be a valid email")
        );
        when(bindingResult.getFieldErrors()).thenReturn(fieldErrors);

        // Act
        ResponseEntity<ErrorResponseDTO> response = controller.handleMethodArgumentNotValidException(ex, webRequest);

        // Assert
        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals("Validation failed", response.getBody().getMessage());
        assertEquals(HttpStatus.BAD_REQUEST.value(), response.getBody().getStatus());
        
        Map<String, String> expectedErrors = new HashMap<>();
        expectedErrors.put("field1", "Field 1 is required");
        expectedErrors.put("field2", "Field 2 must be a valid email");
        assertEquals(expectedErrors, response.getBody().getValidationErrors());
        
        // Verify logging
        verify(mockLogger).warn(contains("Method argument validation error"), anyString());
    }

    @Test
    @DisplayName("Should handle BaseException with custom status code")
    void testHandleBaseException() {
        // Arrange
        String errorMessage = "Custom error";
        int statusCode = HttpStatus.CONFLICT.value();
        BaseException ex = new BaseException(errorMessage, statusCode);

        // Act
        ResponseEntity<ErrorResponseDTO> response = controller.handleBaseException(ex, webRequest);

        // Assert
        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals(errorMessage, response.getBody().getMessage());
        assertEquals(statusCode, response.getBody().getStatus());
        
        // Verify logging
        verify(mockLogger).error(contains("Application error"), eq(errorMessage));
    }

    @Test
    @DisplayName("Should handle generic Exception with 500 status")
    void testHandleGenericException() {
        // Arrange
        String errorMessage = "Unexpected error";
        Exception ex = new RuntimeException(errorMessage);

        // Act
        ResponseEntity<ErrorResponseDTO> response = controller.handleGenericException(ex, webRequest);

        // Assert
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertEquals("An unexpected error occurred. Please try again later.", response.getBody().getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), response.getBody().getStatus());
        
        // Verify logging
        verify(mockLogger).error(contains("Unexpected error"), eq(errorMessage), eq(ex));
    }

    @Test
    @DisplayName("Should validate binding result without errors")
    void testValidateBindingResultWithoutErrors() {
        // Arrange
        when(bindingResult.hasErrors()).thenReturn(false);

        // Act & Assert - should not throw exception
        assertDoesNotThrow(() -> controller.validateBindingResult(bindingResult));
    }

    @Test
    @DisplayName("Should throw ValidationException when binding result has errors")
    void testValidateBindingResultWithErrors() {
        // Arrange
        when(bindingResult.hasErrors()).thenReturn(true);
        
        List<FieldError> fieldErrors = Arrays.asList(
            new FieldError("testObject", "field1", "Field 1 is required"),
            new FieldError("testObject", "field2", "Field 2 must be a valid email")
        );
        when(bindingResult.getFieldErrors()).thenReturn(fieldErrors);

        // Act & Assert
        ValidationException exception = assertThrows(ValidationException.class, 
                () -> controller.validateBindingResult(bindingResult));
        
        assertEquals("Validation failed", exception.getMessage());
        Map<String, String> expectedErrors = new HashMap<>();
        expectedErrors.put("field1", "Field 1 is required");
        expectedErrors.put("field2", "Field 2 must be a valid email");
        assertEquals(expectedErrors, exception.getErrors());
    }

    @Test
    @DisplayName("Should log request with payload")
    void testLogRequestWithPayload() {
        // Arrange
        String method = "POST";
        String endpoint = "/api/v1/test";
        Object payload = new TestPayload("test", 123);

        // Act
        controller.logRequest(method, endpoint, payload);

        // Assert
        verify(mockLogger).info(eq("API Request: {} {} with payload: {}"), eq(method), eq(endpoint), eq(payload));
    }

    @Test
    @DisplayName("Should log request without payload")
    void testLogRequestWithoutPayload() {
        // Arrange
        String method = "GET";
        String endpoint = "/api/v1/test";

        // Act
        controller.logRequest(method, endpoint, null);

        // Assert
        verify(mockLogger).info(eq("API Request: {} {}"), eq(method), eq(endpoint));
    }

    @Test
    @DisplayName("Should log response")
    void testLogResponse() {
        // Arrange
        String method = "GET";
        String endpoint = "/api/v1/test";
        Object responseBody = new TestPayload("response", 456);
        HttpStatus status = HttpStatus.OK;

        // Act
        controller.logResponse(method, endpoint, responseBody, status);

        // Assert
        verify(mockLogger).info(
                eq("API Response: {} {} returned {} with payload: {}"), 
                eq(method), 
                eq(endpoint), 
                eq(status.value()), 
                eq(responseBody));
    }

    /**
     * Simple test payload class for logging tests.
     */
    private static class TestPayload {
        private final String name;
        private final int value;

        public TestPayload(String name, int value) {
            this.name = name;
            this.value = value;
        }

        @Override
        public String toString() {
            return "TestPayload{name='" + name + "', value=" + value + '}';
        }
    }
}