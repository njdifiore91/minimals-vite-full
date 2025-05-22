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
 * Unit tests for the abstract BaseController class that provides common functionality 
 * for all REST controllers in the MCA application.
 * <p>
 * Tests verify global exception handling, standardized response formatting, and utility 
 * methods for consistent API behavior. Includes tests for different exception types, 
 * error response structures, and logging behavior.
 * </p>
 * <p>
 * Uses a concrete implementation of the abstract class to enable testing of its functionality.
 * </p>
 */
@ExtendWith(MockitoExtension.class)
public class BaseControllerTest {

    /**
     * Concrete implementation of the abstract BaseController for testing purposes.
     */
    private static class TestController extends BaseController {
        // No additional implementation needed for testing the base functionality
    }

    private TestController controller;

    @Mock
    private WebRequest webRequest;

    @Mock
    private Logger mockLogger;

    @BeforeEach
    void setUp() {
        controller = new TestController();
        
        // Mock the WebRequest to return a consistent path
        when(webRequest.getDescription(false)).thenReturn("uri=/api/test");
        
        // Use reflection to replace the logger with a mock
        try {
            java.lang.reflect.Field loggerField = BaseController.class.getDeclaredField("logger");
            loggerField.setAccessible(true);
            loggerField.set(controller, mockLogger);
        } catch (Exception e) {
            fail("Failed to set mock logger: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Should create a standard response with data and status")
    void shouldCreateResponseWithDataAndStatus() {
        // Given
        String testData = "Test Data";
        HttpStatus status = HttpStatus.OK;

        // When
        ResponseEntity<String> response = controller.createResponse(testData, status);

        // Then
        assertEquals(status, response.getStatusCode());
        assertEquals(testData, response.getBody());
    }

    @Test
    @DisplayName("Should create a success response with status 200")
    void shouldCreateSuccessResponse() {
        // Given
        String testData = "Test Data";

        // When
        ResponseEntity<String> response = controller.createSuccessResponse(testData);

        // Then
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(testData, response.getBody());
    }

    @Test
    @DisplayName("Should create a created response with status 201")
    void shouldCreateCreatedResponse() {
        // Given
        String testData = "Test Data";

        // When
        ResponseEntity<String> response = controller.createCreatedResponse(testData);

        // Then
        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        assertEquals(testData, response.getBody());
    }

    @Test
    @DisplayName("Should create a page response with pagination metadata")
    void shouldCreatePageResponse() {
        // Given
        List<String> items = Arrays.asList("Item 1", "Item 2", "Item 3");
        Page<String> page = new PageImpl<>(items, PageRequest.of(0, 10), 3);

        // When
        ResponseEntity<PageResponseDTO<String>> response = controller.createPageResponse(page);

        // Then
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(items, response.getBody().getContent());
        assertEquals(3, response.getBody().getMetadata().getTotalElements());
        assertEquals(0, response.getBody().getMetadata().getCurrentPage());
        assertEquals(10, response.getBody().getMetadata().getPageSize());
        assertEquals(1, response.getBody().getMetadata().getTotalPages());
    }

    @Test
    @DisplayName("Should create an error response with message and status")
    void shouldCreateErrorResponse() {
        // Given
        String errorMessage = "Test error message";
        HttpStatus status = HttpStatus.BAD_REQUEST;

        // When
        ResponseEntity<ErrorResponseDTO> response = controller.createErrorResponse(errorMessage, status, webRequest);

        // Then
        assertEquals(status, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(errorMessage, response.getBody().getMessage());
        assertEquals(status.value(), response.getBody().getStatus());
        assertEquals(status.getReasonPhrase(), response.getBody().getError());
        assertEquals("/api/test", response.getBody().getPath());
        assertNotNull(response.getBody().getTimestamp());
    }

    @Test
    @DisplayName("Should validate binding result and throw exception when errors exist")
    void shouldValidateBindingResultAndThrowException() {
        // Given
        BindingResult bindingResult = mock(BindingResult.class);
        FieldError fieldError = new FieldError("testObject", "testField", "Test error message");
        
        when(bindingResult.hasErrors()).thenReturn(true);
        when(bindingResult.getFieldErrors()).thenReturn(Arrays.asList(fieldError));

        // When/Then
        ValidationException exception = assertThrows(ValidationException.class, () -> {
            controller.validateBindingResult(bindingResult);
        });

        // Then
        assertEquals("Validation failed", exception.getMessage());
        Map<String, String> expectedErrors = new HashMap<>();
        expectedErrors.put("testField", "Test error message");
        assertEquals(expectedErrors, exception.getErrors());
    }

    @Test
    @DisplayName("Should not throw exception when binding result has no errors")
    void shouldNotThrowExceptionWhenBindingResultHasNoErrors() {
        // Given
        BindingResult bindingResult = mock(BindingResult.class);
        when(bindingResult.hasErrors()).thenReturn(false);

        // When/Then
        assertDoesNotThrow(() -> {
            controller.validateBindingResult(bindingResult);
        });
    }

    @Test
    @DisplayName("Should log request with method, endpoint, and request body")
    void shouldLogRequestWithBody() {
        // Given
        String method = "POST";
        String endpoint = "/api/test";
        Object requestBody = new Object() {
            @Override
            public String toString() {
                return "TestRequestBody";
            }
        };

        // When
        controller.logRequest(method, endpoint, requestBody);

        // Then
        verify(mockLogger).info("API Request: {} {} with payload: {}", method, endpoint, requestBody);
    }

    @Test
    @DisplayName("Should log request with method and endpoint when body is null")
    void shouldLogRequestWithoutBody() {
        // Given
        String method = "GET";
        String endpoint = "/api/test";

        // When
        controller.logRequest(method, endpoint, null);

        // Then
        verify(mockLogger).info("API Request: {} {}", method, endpoint);
    }

    @Test
    @DisplayName("Should log response with method, endpoint, response body, and status")
    void shouldLogResponse() {
        // Given
        String method = "GET";
        String endpoint = "/api/test";
        Object responseBody = "Test response";
        HttpStatus status = HttpStatus.OK;

        // When
        controller.logResponse(method, endpoint, responseBody, status);

        // Then
        verify(mockLogger).info("API Response: {} {} returned {} with payload: {}", 
                method, endpoint, status.value(), responseBody);
    }

    @Test
    @DisplayName("Should handle ResourceNotFoundException and return 404 response")
    void shouldHandleResourceNotFoundException() {
        // Given
        ResourceNotFoundException exception = new ResourceNotFoundException("Test resource", "123");

        // When
        ResponseEntity<ErrorResponseDTO> response = controller.handleResourceNotFoundException(exception, webRequest);

        // Then
        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Test resource with id 123 not found", response.getBody().getMessage());
        assertEquals(HttpStatus.NOT_FOUND.value(), response.getBody().getStatus());
        verify(mockLogger).warn("Resource not found: {}", exception.getMessage());
    }

    @Test
    @DisplayName("Should handle AuthorizationException and return 403 response")
    void shouldHandleAuthorizationException() {
        // Given
        AuthorizationException exception = new AuthorizationException("webhooks", "configure", "System Admin");

        // When
        ResponseEntity<ErrorResponseDTO> response = controller.handleAuthorizationException(exception, webRequest);

        // Then
        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Access denied to perform 'configure' on resource 'webhooks'. Required role: System Admin", 
                response.getBody().getMessage());
        assertEquals(HttpStatus.FORBIDDEN.value(), response.getBody().getStatus());
        verify(mockLogger).warn("Authorization failure: {}", exception.getMessage());
    }

    @Test
    @DisplayName("Should handle ValidationException and return 400 response with validation errors")
    void shouldHandleValidationException() {
        // Given
        Map<String, String> errors = new HashMap<>();
        errors.put("field1", "Error message 1");
        errors.put("field2", "Error message 2");
        ValidationException exception = new ValidationException("Validation failed", errors);

        // When
        ResponseEntity<ErrorResponseDTO> response = controller.handleValidationException(exception, webRequest);

        // Then
        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Validation failed", response.getBody().getMessage());
        assertEquals(HttpStatus.BAD_REQUEST.value(), response.getBody().getStatus());
        assertEquals(errors, response.getBody().getValidationErrors());
        verify(mockLogger).warn("Validation error: {}", exception.getMessage());
    }

    @Test
    @DisplayName("Should handle MethodArgumentNotValidException and return 400 response with validation errors")
    void shouldHandleMethodArgumentNotValidException() {
        // Given
        MethodArgumentNotValidException exception = mock(MethodArgumentNotValidException.class);
        BindingResult bindingResult = mock(BindingResult.class);
        FieldError fieldError1 = new FieldError("testObject", "field1", "Error message 1");
        FieldError fieldError2 = new FieldError("testObject", "field2", "Error message 2");
        List<FieldError> fieldErrors = Arrays.asList(fieldError1, fieldError2);
        
        when(exception.getBindingResult()).thenReturn(bindingResult);
        when(bindingResult.getFieldErrors()).thenReturn(fieldErrors);
        when(exception.getMessage()).thenReturn("Validation failed");

        // When
        ResponseEntity<ErrorResponseDTO> response = controller.handleMethodArgumentNotValidException(exception, webRequest);

        // Then
        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Validation failed", response.getBody().getMessage());
        assertEquals(HttpStatus.BAD_REQUEST.value(), response.getBody().getStatus());
        
        Map<String, String> expectedErrors = new HashMap<>();
        expectedErrors.put("field1", "Error message 1");
        expectedErrors.put("field2", "Error message 2");
        assertEquals(expectedErrors, response.getBody().getValidationErrors());
        
        verify(mockLogger).warn("Method argument validation error: {}", exception.getMessage());
    }

    @Test
    @DisplayName("Should handle BaseException and return response with status from exception")
    void shouldHandleBaseException() {
        // Given
        BaseException exception = new BaseException("Test error message", HttpStatus.CONFLICT);

        // When
        ResponseEntity<ErrorResponseDTO> response = controller.handleBaseException(exception, webRequest);

        // Then
        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Test error message", response.getBody().getMessage());
        assertEquals(HttpStatus.CONFLICT.value(), response.getBody().getStatus());
        verify(mockLogger).error("Application error: {}", exception.getMessage());
    }

    @Test
    @DisplayName("Should handle generic Exception and return 500 response")
    void shouldHandleGenericException() {
        // Given
        Exception exception = new RuntimeException("Unexpected error");

        // When
        ResponseEntity<ErrorResponseDTO> response = controller.handleGenericException(exception, webRequest);

        // Then
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("An unexpected error occurred. Please try again later.", response.getBody().getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), response.getBody().getStatus());
        
        // Verify that the exception is logged with the stack trace
        ArgumentCaptor<String> messageCaptor = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Object> exceptionCaptor = ArgumentCaptor.forClass(Object.class);
        
        verify(mockLogger).error(messageCaptor.capture(), messageCaptor.capture(), exceptionCaptor.capture());
        assertEquals("Unexpected error: {}", messageCaptor.getAllValues().get(0));
        assertEquals(exception.getMessage(), messageCaptor.getAllValues().get(1));
        assertEquals(exception, exceptionCaptor.getValue());
    }
}