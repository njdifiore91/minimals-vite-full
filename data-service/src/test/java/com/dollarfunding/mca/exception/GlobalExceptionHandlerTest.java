package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.util.Constants;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.springframework.beans.TypeMismatchException;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.BindException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.validation.ObjectError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.NoHandlerFoundException;

import javax.validation.ConstraintViolation;
import javax.validation.ConstraintViolationException;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import static org.hamcrest.Matchers.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit tests for {@link GlobalExceptionHandler}.
 * 
 * This test class verifies that the GlobalExceptionHandler properly handles all types of exceptions
 * and converts them to appropriate HTTP responses with consistent error formats.
 */
@DisplayName("GlobalExceptionHandler Tests")
public class GlobalExceptionHandlerTest {

    private MockMvc mockMvc;
    private ObjectMapper objectMapper;
    private GlobalExceptionHandler exceptionHandler;
    
    @Mock
    private WebRequest webRequest;

    /**
     * Test controller that throws various exceptions for testing purposes.
     */
    @RestController
    private static class TestController {
        
        @GetMapping("/test/resource-not-found")
        public void throwResourceNotFoundException() {
            throw new ResourceNotFoundException("application", "123");
        }
        
        @GetMapping("/test/validation-exception")
        public void throwValidationException() {
            ValidationException ex = new ValidationException("Validation failed");
            ex.addValidationError("name", "Name is required");
            ex.addValidationError("email", "Invalid email format", "invalid-email");
            throw ex;
        }
        
        @GetMapping("/test/business-rule-exception")
        public void throwBusinessRuleException() {
            throw new BusinessRuleException("Business rule violated", "RULE-001");
        }
        
        @GetMapping("/test/authorization-exception")
        public void throwAuthorizationException() {
            throw new AuthorizationException("Insufficient permissions", "ADMIN");
        }
        
        @GetMapping("/test/document-processing-exception")
        public void throwDocumentProcessingException() {
            throw new DocumentProcessingException("Error processing document", "DOC-123");
        }
        
        @GetMapping("/test/webhook-delivery-exception")
        public void throwWebhookDeliveryException() {
            throw new WebhookDeliveryException("Error delivering webhook", "WEBHOOK-123");
        }
        
        @GetMapping("/test/illegal-argument-exception")
        public void throwIllegalArgumentException() {
            throw new IllegalArgumentException("Invalid argument provided");
        }
        
        @GetMapping("/test/illegal-state-exception")
        public void throwIllegalStateException() {
            throw new IllegalStateException("Invalid state");
        }
        
        @GetMapping("/test/generic-exception")
        public void throwGenericException() {
            throw new RuntimeException("Unexpected error occurred");
        }
    }

    @BeforeEach
    void setUp() {
        exceptionHandler = new GlobalExceptionHandler();
        mockMvc = MockMvcBuilders.standaloneSetup(new TestController())
                .setControllerAdvice(exceptionHandler)
                .build();
        objectMapper = new ObjectMapper();
        webRequest = mock(WebRequest.class);
        when(webRequest.getDescription(false)).thenReturn("uri=/test");
    }

    @Nested
    @DisplayName("Custom Exception Tests")
    class CustomExceptionTests {
        
        @Test
        @DisplayName("Should handle ResourceNotFoundException with 404 status")
        void shouldHandleResourceNotFoundException() throws Exception {
            mockMvc.perform(get("/test/resource-not-found"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.status", is(404)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.NOT_FOUND)))
                    .andExpect(jsonPath("$.message", containsString("application")))
                    .andExpect(jsonPath("$.message", containsString("123")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
        
        @Test
        @DisplayName("Should handle ValidationException with 400 status and validation details")
        void shouldHandleValidationException() throws Exception {
            mockMvc.perform(get("/test/validation-exception"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.status", is(400)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.VALIDATION_ERROR)))
                    .andExpect(jsonPath("$.message", is("Validation failed")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()))
                    .andExpect(jsonPath("$.details", hasSize(2)))
                    .andExpect(jsonPath("$.details[0].field", isOneOf("name", "email")))
                    .andExpect(jsonPath("$.details[1].field", isOneOf("name", "email")));
        }
        
        @Test
        @DisplayName("Should handle BusinessRuleException with 422 status")
        void shouldHandleBusinessRuleException() throws Exception {
            mockMvc.perform(get("/test/business-rule-exception"))
                    .andExpect(status().isUnprocessableEntity())
                    .andExpect(jsonPath("$.status", is(422)))
                    .andExpect(jsonPath("$.errorCode", is("RULE-001")))
                    .andExpect(jsonPath("$.message", is("Business rule violated")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
        
        @Test
        @DisplayName("Should handle AuthorizationException with 403 status")
        void shouldHandleAuthorizationException() throws Exception {
            mockMvc.perform(get("/test/authorization-exception"))
                    .andExpect(status().isForbidden())
                    .andExpect(jsonPath("$.status", is(403)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.FORBIDDEN)))
                    .andExpect(jsonPath("$.message", containsString("Insufficient permissions")))
                    .andExpect(jsonPath("$.message", containsString("ADMIN")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
        
        @Test
        @DisplayName("Should handle DocumentProcessingException with 500 status")
        void shouldHandleDocumentProcessingException() throws Exception {
            mockMvc.perform(get("/test/document-processing-exception"))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.status", is(500)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.DOCUMENT_PROCESSING_ERROR)))
                    .andExpect(jsonPath("$.message", containsString("Error processing document")))
                    .andExpect(jsonPath("$.message", containsString("DOC-123")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
        
        @Test
        @DisplayName("Should handle WebhookDeliveryException with 500 status")
        void shouldHandleWebhookDeliveryException() throws Exception {
            mockMvc.perform(get("/test/webhook-delivery-exception"))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.status", is(500)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.MESSAGING_PUBLISH_ERROR)))
                    .andExpect(jsonPath("$.message", containsString("Error delivering webhook")))
                    .andExpect(jsonPath("$.message", containsString("WEBHOOK-123")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
    }
    
    @Nested
    @DisplayName("Standard Java Exception Tests")
    class StandardJavaExceptionTests {
        
        @Test
        @DisplayName("Should handle IllegalArgumentException with 400 status")
        void shouldHandleIllegalArgumentException() throws Exception {
            mockMvc.perform(get("/test/illegal-argument-exception"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.status", is(400)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.VALIDATION_ERROR)))
                    .andExpect(jsonPath("$.message", is("Invalid argument provided")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
        
        @Test
        @DisplayName("Should handle IllegalStateException with 400 status")
        void shouldHandleIllegalStateException() throws Exception {
            mockMvc.perform(get("/test/illegal-state-exception"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.status", is(400)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.VALIDATION_ERROR)))
                    .andExpect(jsonPath("$.message", is("Invalid state")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
        
        @Test
        @DisplayName("Should handle generic exceptions with 500 status")
        void shouldHandleGenericException() throws Exception {
            mockMvc.perform(get("/test/generic-exception"))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.status", is(500)))
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.GENERAL_ERROR)))
                    .andExpect(jsonPath("$.message", is("An unexpected error occurred")))
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(jsonPath("$.path", notNullValue()));
        }
    }
    
    @Nested
    @DisplayName("Spring Framework Exception Tests")
    class SpringFrameworkExceptionTests {
        
        @Test
        @DisplayName("Should handle MethodArgumentNotValidException with 400 status and validation details")
        void shouldHandleMethodArgumentNotValidException() throws Exception {
            // Mock MethodArgumentNotValidException
            MethodParameter parameter = mock(MethodParameter.class);
            BindingResult bindingResult = mock(BindingResult.class);
            FieldError fieldError1 = new FieldError("testObject", "field1", "rejected1", false, null, null, "Field 1 error");
            FieldError fieldError2 = new FieldError("testObject", "field2", "rejected2", false, null, null, "Field 2 error");
            ObjectError globalError = new ObjectError("testObject", "Global error");
            
            when(bindingResult.getFieldErrors()).thenReturn(Arrays.asList(fieldError1, fieldError2));
            when(bindingResult.getGlobalErrors()).thenReturn(Collections.singletonList(globalError));
            
            MethodArgumentNotValidException ex = new MethodArgumentNotValidException(parameter, bindingResult);
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.BAD_REQUEST;
            
            Object response = exceptionHandler.handleMethodArgumentNotValid(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 400;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().equals("Validation failed");
            assert errorResponse.getDetails().size() == 3;
        }
        
        @Test
        @DisplayName("Should handle BindException with 400 status and validation details")
        void shouldHandleBindException() throws Exception {
            // Mock BindException
            BindingResult bindingResult = mock(BindingResult.class);
            FieldError fieldError = new FieldError("testObject", "field1", "rejected1", false, null, null, "Field 1 error");
            ObjectError globalError = new ObjectError("testObject", "Global error");
            
            when(bindingResult.getFieldErrors()).thenReturn(Collections.singletonList(fieldError));
            when(bindingResult.getGlobalErrors()).thenReturn(Collections.singletonList(globalError));
            
            BindException ex = new BindException(bindingResult);
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.BAD_REQUEST;
            
            Object response = exceptionHandler.handleBindException(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 400;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().equals("Binding failed");
            assert errorResponse.getDetails().size() == 2;
        }
        
        @Test
        @DisplayName("Should handle MissingServletRequestParameterException with 400 status")
        void shouldHandleMissingServletRequestParameterException() throws Exception {
            // Mock MissingServletRequestParameterException
            MissingServletRequestParameterException ex = new MissingServletRequestParameterException("testParam", "String");
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.BAD_REQUEST;
            
            Object response = exceptionHandler.handleMissingServletRequestParameter(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 400;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().contains("testParam");
            assert errorResponse.getMessage().contains("String");
            assert errorResponse.getDetails().size() == 1;
            assert errorResponse.getDetails().get(0).getField().equals("testParam");
        }
        
        @Test
        @DisplayName("Should handle TypeMismatchException with 400 status")
        void shouldHandleTypeMismatchException() throws Exception {
            // Mock TypeMismatchException
            TypeMismatchException ex = new TypeMismatchException("123", Integer.class);
            ex.setValue("abc");
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.BAD_REQUEST;
            
            Object response = exceptionHandler.handleTypeMismatch(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 400;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().contains("abc");
            assert errorResponse.getMessage().contains("Integer");
        }
        
        @Test
        @DisplayName("Should handle HttpMessageNotReadableException with 400 status")
        void shouldHandleHttpMessageNotReadableException() throws Exception {
            // Mock HttpMessageNotReadableException
            HttpMessageNotReadableException ex = new HttpMessageNotReadableException("Malformed JSON request");
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.BAD_REQUEST;
            
            Object response = exceptionHandler.handleHttpMessageNotReadable(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 400;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().equals("Malformed JSON request");
        }
        
        @Test
        @DisplayName("Should handle HttpRequestMethodNotSupportedException with 405 status")
        void shouldHandleHttpRequestMethodNotSupportedException() throws Exception {
            // Mock HttpRequestMethodNotSupportedException
            HttpRequestMethodNotSupportedException ex = new HttpRequestMethodNotSupportedException(
                    "POST", Arrays.asList("GET", "PUT"));
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.METHOD_NOT_ALLOWED;
            
            Object response = exceptionHandler.handleHttpRequestMethodNotSupported(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 405;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().contains("POST");
            assert errorResponse.getMessage().contains("GET");
            assert errorResponse.getMessage().contains("PUT");
        }
        
        @Test
        @DisplayName("Should handle HttpMediaTypeNotSupportedException with 415 status")
        void shouldHandleHttpMediaTypeNotSupportedException() throws Exception {
            // Mock HttpMediaTypeNotSupportedException
            HttpMediaTypeNotSupportedException ex = new HttpMediaTypeNotSupportedException(
                    MediaType.APPLICATION_XML, Arrays.asList(MediaType.APPLICATION_JSON));
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.UNSUPPORTED_MEDIA_TYPE;
            
            Object response = exceptionHandler.handleHttpMediaTypeNotSupported(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 415;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().contains("application/xml");
            assert errorResponse.getMessage().contains("application/json");
        }
        
        @Test
        @DisplayName("Should handle NoHandlerFoundException with 404 status")
        void shouldHandleNoHandlerFoundException() throws Exception {
            // Mock NoHandlerFoundException
            NoHandlerFoundException ex = new NoHandlerFoundException("GET", "/unknown-path", new HttpHeaders());
            
            // Process the exception directly
            HttpHeaders headers = new HttpHeaders();
            HttpStatus status = HttpStatus.NOT_FOUND;
            
            Object response = exceptionHandler.handleNoHandlerFoundException(ex, headers, status, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 404;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.NOT_FOUND);
            assert errorResponse.getMessage().contains("GET");
            assert errorResponse.getMessage().contains("/unknown-path");
        }
    }
    
    @Nested
    @DisplayName("Other Exception Tests")
    class OtherExceptionTests {
        
        @Test
        @DisplayName("Should handle ConstraintViolationException with 400 status and validation details")
        void shouldHandleConstraintViolationException() throws Exception {
            // Mock ConstraintViolationException
            Set<ConstraintViolation<?>> violations = new HashSet<>();
            ConstraintViolation<?> violation1 = mock(ConstraintViolation.class);
            ConstraintViolation<?> violation2 = mock(ConstraintViolation.class);
            
            when(violation1.getPropertyPath()).thenReturn(new TestPropertyPath("field1"));
            when(violation1.getMessage()).thenReturn("Field 1 error");
            when(violation1.getInvalidValue()).thenReturn("invalid1");
            
            when(violation2.getPropertyPath()).thenReturn(new TestPropertyPath("field2"));
            when(violation2.getMessage()).thenReturn("Field 2 error");
            when(violation2.getInvalidValue()).thenReturn("invalid2");
            
            violations.add(violation1);
            violations.add(violation2);
            
            ConstraintViolationException ex = new ConstraintViolationException("Constraint violations", violations);
            
            // Process the exception directly
            Object response = exceptionHandler.handleConstraintViolation(ex, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 400;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().equals("Validation failed");
            assert errorResponse.getDetails().size() == 2;
        }
        
        @Test
        @DisplayName("Should handle MethodArgumentTypeMismatchException with 400 status")
        void shouldHandleMethodArgumentTypeMismatchException() throws Exception {
            // Mock MethodArgumentTypeMismatchException
            MethodArgumentTypeMismatchException ex = mock(MethodArgumentTypeMismatchException.class);
            when(ex.getName()).thenReturn("testParam");
            when(ex.getValue()).thenReturn("abc");
            when(ex.getRequiredType()).thenReturn((Class) Integer.class);
            when(ex.getMessage()).thenReturn("Failed to convert value of type 'java.lang.String' to required type 'java.lang.Integer'");
            
            // Process the exception directly
            Object response = exceptionHandler.handleMethodArgumentTypeMismatch(ex, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 400;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().contains("testParam");
            assert errorResponse.getMessage().contains("Integer");
            assert errorResponse.getDetails().size() == 1;
            assert errorResponse.getDetails().get(0).getField().equals("testParam");
        }
        
        @Test
        @DisplayName("Should handle MaxUploadSizeExceededException with 413 status")
        void shouldHandleMaxUploadSizeExceededException() throws Exception {
            // Mock MaxUploadSizeExceededException
            MaxUploadSizeExceededException ex = new MaxUploadSizeExceededException(1000000L);
            
            // Process the exception directly
            Object response = exceptionHandler.handleMaxUploadSizeExceeded(ex, webRequest);
            
            // Verify response
            ErrorResponseDTO errorResponse = (ErrorResponseDTO) response;
            assert errorResponse.getStatus() == 413;
            assert errorResponse.getErrorCode().equals(Constants.ErrorCode.VALIDATION_ERROR);
            assert errorResponse.getMessage().contains("File size exceeds");
        }
    }
    
    @Nested
    @DisplayName("Error Response Format Tests")
    class ErrorResponseFormatTests {
        
        @Test
        @DisplayName("Should include timestamp in ISO format")
        void shouldIncludeTimestampInIsoFormat() throws Exception {
            mockMvc.perform(get("/test/resource-not-found"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.timestamp", notNullValue()))
                    .andExpect(result -> {
                        String response = result.getResponse().getContentAsString();
                        ErrorResponseDTO errorResponse = objectMapper.readValue(response, ErrorResponseDTO.class);
                        LocalDateTime timestamp = errorResponse.getTimestamp();
                        assert timestamp != null;
                        assert timestamp.getYear() > 2020; // Basic validation that it's a recent timestamp
                    });
        }
        
        @Test
        @DisplayName("Should include request path in error response")
        void shouldIncludeRequestPath() throws Exception {
            mockMvc.perform(get("/test/resource-not-found"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.path", is("/test/resource-not-found")));
        }
        
        @Test
        @DisplayName("Should include HTTP status code in error response")
        void shouldIncludeHttpStatusCode() throws Exception {
            mockMvc.perform(get("/test/resource-not-found"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.status", is(404)));
        }
        
        @Test
        @DisplayName("Should include error code in error response")
        void shouldIncludeErrorCode() throws Exception {
            mockMvc.perform(get("/test/resource-not-found"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.errorCode", is(Constants.ErrorCode.NOT_FOUND)));
        }
        
        @Test
        @DisplayName("Should include error message in error response")
        void shouldIncludeErrorMessage() throws Exception {
            mockMvc.perform(get("/test/resource-not-found"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.message", notNullValue()));
        }
        
        @Test
        @DisplayName("Should include validation details for validation errors")
        void shouldIncludeValidationDetails() throws Exception {
            mockMvc.perform(get("/test/validation-exception"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.details", hasSize(2)))
                    .andExpect(jsonPath("$.details[0].field", notNullValue()))
                    .andExpect(jsonPath("$.details[0].message", notNullValue()));
        }
    }
    
    /**
     * Simple implementation of PropertyPath for testing ConstraintViolationException.
     */
    private static class TestPropertyPath implements javax.validation.Path {
        private final String path;
        
        public TestPropertyPath(String path) {
            this.path = path;
        }
        
        @Override
        public java.util.Iterator<Node> iterator() {
            return Collections.emptyIterator();
        }
        
        @Override
        public String toString() {
            return path;
        }
    }
}