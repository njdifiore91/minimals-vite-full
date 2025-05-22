package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.util.Constants;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.BindException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.hamcrest.Matchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultHandlers.print;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit tests for the GlobalExceptionHandler class.
 * <p>
 * These tests verify that the GlobalExceptionHandler properly handles all types of exceptions
 * and converts them to appropriate HTTP responses with consistent error formats.
 * </p>
 */
@ExtendWith(MockitoExtension.class)
public class GlobalExceptionHandlerTest {

    private MockMvc mockMvc;
    
    @Mock
    private HttpServletRequest request;
    
    @InjectMocks
    private GlobalExceptionHandler exceptionHandler;
    
    private ObjectMapper objectMapper;

    @BeforeEach
    public void setup() {
        objectMapper = new ObjectMapper();
        // Configure ObjectMapper to handle LocalDateTime
        objectMapper.findAndRegisterModules();
        
        // Set up MockMvc with the exception handler
        mockMvc = MockMvcBuilders.standaloneSetup(new TestController())
                .setControllerAdvice(exceptionHandler)
                .build();
        
        // Mock common request behavior
        when(request.getRequestURI()).thenReturn("/api/test");
    }

    /**
     * Test controller that throws various exceptions for testing purposes.
     */
    @org.springframework.web.bind.annotation.RestController
    private static class TestController {
        
        @org.springframework.web.bind.annotation.GetMapping("/test/resource-not-found")
        public void throwResourceNotFoundException() {
            throw new ResourceNotFoundException("Test resource", "123");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/validation-exception")
        public void throwValidationException() {
            ValidationException ex = new ValidationException("Validation failed");
            ex.addValidationError("field1", "Field 1 is required");
            throw ex;
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/business-rule-exception")
        public void throwBusinessRuleException() {
            throw new BusinessRuleException("Business rule violated", "RULE-001");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/authorization-exception")
        public void throwAuthorizationException() {
            throw new AuthorizationException("Not authorized", "ADMIN");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/document-processing-exception")
        public void throwDocumentProcessingException() {
            throw new DocumentProcessingException("Document processing failed", "DOC-123");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/webhook-delivery-exception")
        public void throwWebhookDeliveryException() {
            throw new WebhookDeliveryException("Webhook delivery failed", "WEBHOOK-123");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/illegal-argument-exception")
        public void throwIllegalArgumentException() {
            throw new IllegalArgumentException("Invalid argument");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/data-integrity-violation-exception")
        public void throwDataIntegrityViolationException() {
            throw new DataIntegrityViolationException("Data integrity violation");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/data-access-exception")
        public void throwDataAccessException() {
            throw new DataAccessException("Database error") {};
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/access-denied-exception")
        public void throwAccessDeniedException() {
            throw new AccessDeniedException("Access denied");
        }
        
        @org.springframework.web.bind.annotation.GetMapping("/test/generic-exception")
        public void throwGenericException() {
            throw new RuntimeException("Unexpected error");
        }
    }

    @Test
    public void testHandleResourceNotFoundException() throws Exception {
        // Arrange
        ResourceNotFoundException ex = new ResourceNotFoundException("Test resource", "123");
        
        // Act & Assert
        ErrorResponseDTO response = exceptionHandler.handleResourceNotFoundException(ex, request);
        
        // Assert
        mockMvc.perform(get("/test/resource-not-found")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(HttpStatus.NOT_FOUND.value()))
                .andExpect(jsonPath("$.errorCode").value(Constants.ErrorCode.NOT_FOUND))
                .andExpect(jsonPath("$.message").isNotEmpty())
                .andExpect(jsonPath("$.timestamp").isNotEmpty())
                .andExpect(jsonPath("$.path").isNotEmpty());
    }

    @Test
    public void testHandleValidationException() throws Exception {
        // Arrange
        ValidationException ex = new ValidationException("Validation failed");
        ex.addValidationError("field1", "Field 1 is required");
        
        // Act & Assert
        mockMvc.perform(get("/test/validation-exception")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(HttpStatus.BAD_REQUEST.value()))
                .andExpect(jsonPath("$.errorCode").value(Constants.ErrorCode.VALIDATION_ERROR))
                .andExpect(jsonPath("$.message").value("Validation error"))
                .andExpect(jsonPath("$.details[0].field").value("field1"))
                .andExpect(jsonPath("$.details[0].message").value("Field 1 is required"))
                .andExpect(jsonPath("$.timestamp").isNotEmpty())
                .andExpect(jsonPath("$.path").isNotEmpty());
    }

    @Test
    public void testHandleBusinessRuleException() throws Exception {
        // Arrange
        BusinessRuleException ex = new BusinessRuleException("Business rule violated", "RULE-001");
        
        // Act & Assert
        mockMvc.perform(get("/test/business-rule-exception")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.status").value(HttpStatus.UNPROCESSABLE_ENTITY.value()))
                .andExpect(jsonPath("$.errorCode").value(ex.getErrorCode()))
                .andExpect(jsonPath("$.message").value("Business rule violation"))
                .andExpect(jsonPath("$.timestamp").isNotEmpty())
                .andExpect(jsonPath("$.path").isNotEmpty());
    }

    @Test
    public void testHandleAuthorizationException() throws Exception {
        // Arrange
        AuthorizationException ex = new AuthorizationException("Not authorized", "ADMIN");
        
        // Act & Assert
        mockMvc.perform(get("/test/authorization-exception")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(HttpStatus.FORBIDDEN.value()))
                .andExpect(jsonPath("$.errorCode").value(ex.getErrorCode()))
                .andExpect(jsonPath("$.message").value("Authorization error"))
                .andExpect(jsonPath("$.timestamp").isNotEmpty())
                .andExpect(jsonPath("$.path").isNotEmpty());
    }

    @Test
    public void testHandleDocumentProcessingException() throws Exception {
        // Arrange
        DocumentProcessingException ex = new DocumentProcessingException("Document processing failed", "DOC-123");
        
        // Act & Assert
        mockMvc.perform(get("/test/document-processing-exception")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.status").value(HttpStatus.INTERNAL_SERVER_ERROR.value()))
                .andExpect(jsonPath("$.errorCode").value(ex.getErrorCode()))
                .andExpect(jsonPath("$.message").value("Document processing error"))
                .andExpect(jsonPath("$.timestamp").isNotEmpty())
                .andExpect(jsonPath("$.path").isNotEmpty());
    }

    @Test
    public void testHandleWebhookDeliveryException() throws Exception {
        // Arrange
        WebhookDeliveryException ex = new WebhookDeliveryException("Webhook delivery failed", "WEBHOOK-123");
        
        // Act & Assert
        mockMvc.perform(get("/test/webhook-delivery-exception")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.status").value(HttpStatus.INTERNAL_SERVER_ERROR.value()))
                .andExpect(jsonPath("$.errorCode").value(ex.getErrorCode()))
                .andExpect(jsonPath("$.message").value("Webhook delivery error"))
                .andExpect(jsonPath("$.timestamp").isNotEmpty())
                .andExpect(jsonPath("$.path").isNotEmpty());
    }

    @Test
    public void testHandleMethodArgumentNotValid() throws Exception {
        // Arrange
        MethodArgumentNotValidException ex = mock(MethodArgumentNotValidException.class);
        BindingResult bindingResult = mock(BindingResult.class);
        when(ex.getBindingResult()).thenReturn(bindingResult);
        when(bindingResult.getFieldErrors()).thenReturn(List.of(
                new FieldError("object", "field1", "Field 1 is invalid"),
                new FieldError("object", "field2", "Field 2 is invalid")
        ));
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleMethodArgumentNotValid(ex, request);
        
        // Assert
        verify(ex, times(1)).getBindingResult();
        verify(bindingResult, times(1)).getFieldErrors();
        
        assert response.getStatus() == HttpStatus.BAD_REQUEST.value();
        assert response.getErrorCode().equals("VALIDATION_ERROR");
        assert response.getMessage().equals("Validation error");
        assert response.getDetails().size() == 2;
        assert response.getDetails().get(0).getField().equals("field1");
        assert response.getDetails().get(0).getMessage().equals("Field 1 is invalid");
        assert response.getDetails().get(1).getField().equals("field2");
        assert response.getDetails().get(1).getMessage().equals("Field 2 is invalid");
    }

    @Test
    public void testHandleBindException() throws Exception {
        // Arrange
        BindException ex = mock(BindException.class);
        BindingResult bindingResult = mock(BindingResult.class);
        when(ex.getBindingResult()).thenReturn(bindingResult);
        when(bindingResult.getFieldErrors()).thenReturn(List.of(
                new FieldError("object", "field1", "Field 1 is invalid")
        ));
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleBindException(ex, request);
        
        // Assert
        verify(ex, times(1)).getBindingResult();
        verify(bindingResult, times(1)).getFieldErrors();
        
        assert response.getStatus() == HttpStatus.BAD_REQUEST.value();
        assert response.getErrorCode().equals("BINDING_ERROR");
        assert response.getMessage().equals("Binding error");
        assert response.getDetails().size() == 1;
        assert response.getDetails().get(0).getField().equals("field1");
        assert response.getDetails().get(0).getMessage().equals("Field 1 is invalid");
    }

    @Test
    public void testHandleConstraintViolation() throws Exception {
        // Arrange
        Set<ConstraintViolation<?>> violations = new HashSet<>();
        ConstraintViolation<?> violation = mock(ConstraintViolation.class);
        violations.add(violation);
        
        when(violation.getPropertyPath()).thenReturn(new TestPropertyPath("object.field1"));
        when(violation.getMessage()).thenReturn("Field 1 is invalid");
        
        ConstraintViolationException ex = new ConstraintViolationException("Constraint violation", violations);
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleConstraintViolation(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.BAD_REQUEST.value();
        assert response.getErrorCode().equals("CONSTRAINT_VIOLATION");
        assert response.getMessage().equals("Constraint violation");
        assert response.getDetails().size() == 1;
        assert response.getDetails().get(0).getField().equals("field1");
        assert response.getDetails().get(0).getMessage().equals("Field 1 is invalid");
    }

    @Test
    public void testHandleMissingServletRequestParameter() throws Exception {
        // Arrange
        MissingServletRequestParameterException ex = new MissingServletRequestParameterException("param1", "String");
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleMissingServletRequestParameter(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.BAD_REQUEST.value();
        assert response.getErrorCode().equals("MISSING_PARAMETER");
        assert response.getMessage().equals("Missing parameter");
        assert response.getDetails().size() == 1;
        assert response.getDetails().get(0).getField().equals("param1");
        assert response.getDetails().get(0).getMessage().equals("Parameter is required");
    }

    @Test
    public void testHandleMethodArgumentTypeMismatch() throws Exception {
        // Arrange
        MethodArgumentTypeMismatchException ex = mock(MethodArgumentTypeMismatchException.class);
        when(ex.getName()).thenReturn("param1");
        when(ex.getRequiredType()).thenReturn((Class)Integer.class);
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleMethodArgumentTypeMismatch(ex, request);
        
        // Assert
        verify(ex, times(1)).getName();
        verify(ex, times(2)).getRequiredType();
        
        assert response.getStatus() == HttpStatus.BAD_REQUEST.value();
        assert response.getErrorCode().equals("TYPE_MISMATCH");
        assert response.getMessage().equals("Type mismatch");
        assert response.getDetails().size() == 1;
        assert response.getDetails().get(0).getField().equals("param1");
        assert response.getDetails().get(0).getMessage().contains("should be of type");
    }

    @Test
    public void testHandleHttpMessageNotReadable() throws Exception {
        // Arrange
        HttpMessageNotReadableException ex = new HttpMessageNotReadableException("Malformed JSON");
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleHttpMessageNotReadable(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.BAD_REQUEST.value();
        assert response.getErrorCode().equals("MALFORMED_JSON");
        assert response.getMessage().equals("Malformed request");
    }

    @Test
    public void testHandleHttpRequestMethodNotSupported() throws Exception {
        // Arrange
        HttpRequestMethodNotSupportedException ex = new HttpRequestMethodNotSupportedException(
                "POST", new String[]{"GET", "PUT"});
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleHttpRequestMethodNotSupported(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.METHOD_NOT_ALLOWED.value();
        assert response.getErrorCode().equals("METHOD_NOT_ALLOWED");
        assert response.getMessage().equals("Method not allowed");
        assert response.getDetails() == null;
    }

    @Test
    public void testHandleHttpMediaTypeNotSupported() throws Exception {
        // Arrange
        HttpMediaTypeNotSupportedException ex = new HttpMediaTypeNotSupportedException("Unsupported media type");
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleHttpMediaTypeNotSupported(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.UNSUPPORTED_MEDIA_TYPE.value();
        assert response.getErrorCode().equals("UNSUPPORTED_MEDIA_TYPE");
        assert response.getMessage().equals("Unsupported media type");
    }

    @Test
    public void testHandleMaxUploadSizeExceeded() throws Exception {
        // Arrange
        MaxUploadSizeExceededException ex = new MaxUploadSizeExceededException(1000L);
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleMaxUploadSizeExceeded(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.PAYLOAD_TOO_LARGE.value();
        assert response.getErrorCode().equals("PAYLOAD_TOO_LARGE");
        assert response.getMessage().equals("File too large");
    }

    @Test
    public void testHandleAccessDeniedException() throws Exception {
        // Arrange
        AccessDeniedException ex = new AccessDeniedException("Access denied");
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleAccessDeniedException(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.FORBIDDEN.value();
        assert response.getErrorCode().equals("ACCESS_DENIED");
        assert response.getMessage().equals("Access denied");
    }

    @Test
    public void testHandleDataIntegrityViolation() throws Exception {
        // Arrange
        DataIntegrityViolationException ex = new DataIntegrityViolationException("Data integrity violation");
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleDataIntegrityViolation(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.CONFLICT.value();
        assert response.getErrorCode().equals("DATA_INTEGRITY_VIOLATION");
        assert response.getMessage().equals("Data integrity violation");
    }

    @Test
    public void testHandleDataAccessException() throws Exception {
        // Arrange
        DataAccessException ex = new DataAccessException("Database error") {};
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleDataAccessException(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.INTERNAL_SERVER_ERROR.value();
        assert response.getErrorCode().equals("DATABASE_ERROR");
        assert response.getMessage().equals("Database error");
    }

    @Test
    public void testHandleIllegalArgument() throws Exception {
        // Arrange
        IllegalArgumentException ex = new IllegalArgumentException("Invalid argument");
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleIllegalArgument(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.BAD_REQUEST.value();
        assert response.getErrorCode().equals("ILLEGAL_ARGUMENT");
        assert response.getMessage().equals("Invalid argument");
    }

    @Test
    public void testHandleAllUncaughtException() throws Exception {
        // Arrange
        Exception ex = new RuntimeException("Unexpected error");
        
        // Act
        ErrorResponseDTO response = exceptionHandler.handleAllUncaughtException(ex, request);
        
        // Assert
        assert response.getStatus() == HttpStatus.INTERNAL_SERVER_ERROR.value();
        assert response.getErrorCode().equals("INTERNAL_SERVER_ERROR");
        assert response.getMessage().equals("Internal server error");
    }

    /**
     * Helper class to mock property path for constraint violation tests.
     */
    private static class TestPropertyPath implements jakarta.validation.Path {
        private final String path;

        public TestPropertyPath(String path) {
            this.path = path;
        }

        @Override
        public String toString() {
            return path;
        }

        @Override
        public java.util.Iterator<Node> iterator() {
            return null;
        }
    }
}