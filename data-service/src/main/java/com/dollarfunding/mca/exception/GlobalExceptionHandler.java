package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

import java.util.List;
import java.util.Set;

/**
 * Global exception handler that catches and processes all exceptions thrown by the application.
 * <p>
 * This class uses Spring's @ControllerAdvice annotation to intercept exceptions and convert them
 * to appropriate HTTP responses with standardized error formats. It handles custom exceptions
 * as well as standard Java and Spring exceptions, ensuring consistent error handling across
 * the application.
 * </p>
 */
@ControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * Handles all BaseException subclasses with their specific HTTP status codes.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(BaseException.class)
    public ResponseEntity<ErrorResponseDTO> handleBaseException(BaseException ex, HttpServletRequest request) {
        log.error("Base exception occurred: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .status(ex.getHttpStatus().value())
                .code(ex.getErrorCode())
                .message(ex.getMessage())
                .path(request.getRequestURI())
                .timestamp(java.time.LocalDateTime.now())
                .build();
        
        return new ResponseEntity<>(errorResponse, ex.getHttpStatus());
    }

    /**
     * Handles ResourceNotFoundException with 404 Not Found status.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponseDTO> handleResourceNotFoundException(
            ResourceNotFoundException ex, HttpServletRequest request) {
        log.warn("Resource not found: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.NOT_FOUND,
                ex.getErrorCode(),
                ex.getMessage(),
                ex.getMessage(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.NOT_FOUND);
    }

    /**
     * Handles ValidationException with 400 Bad Request status.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response with validation errors
     */
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<ErrorResponseDTO> handleValidationException(
            ValidationException ex, HttpServletRequest request) {
        log.warn("Validation error: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                ex.getErrorCode(),
                "Validation error",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        // Add field-level validation errors if available
        if (ex.getValidationErrors() != null && !ex.getValidationErrors().isEmpty()) {
            ex.getValidationErrors().forEach(error -> 
                errorResponse.addValidationError(error.getField(), error.getMessage())
            );
        }
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles BusinessRuleException with 422 Unprocessable Entity status.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(BusinessRuleException.class)
    public ResponseEntity<ErrorResponseDTO> handleBusinessRuleException(
            BusinessRuleException ex, HttpServletRequest request) {
        log.warn("Business rule violation: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.UNPROCESSABLE_ENTITY,
                ex.getErrorCode(),
                "Business rule violation",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.UNPROCESSABLE_ENTITY);
    }

    /**
     * Handles AuthorizationException with 403 Forbidden status.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(AuthorizationException.class)
    public ResponseEntity<ErrorResponseDTO> handleAuthorizationException(
            AuthorizationException ex, HttpServletRequest request) {
        log.warn("Authorization error: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.FORBIDDEN,
                ex.getErrorCode(),
                "Authorization error",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.FORBIDDEN);
    }

    /**
     * Handles DocumentProcessingException with 500 Internal Server Error status.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(DocumentProcessingException.class)
    public ResponseEntity<ErrorResponseDTO> handleDocumentProcessingException(
            DocumentProcessingException ex, HttpServletRequest request) {
        log.error("Document processing error: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.INTERNAL_SERVER_ERROR,
                ex.getErrorCode(),
                "Document processing error",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Handles WebhookDeliveryException with 500 Internal Server Error status.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(WebhookDeliveryException.class)
    public ResponseEntity<ErrorResponseDTO> handleWebhookDeliveryException(
            WebhookDeliveryException ex, HttpServletRequest request) {
        log.error("Webhook delivery error: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.INTERNAL_SERVER_ERROR,
                ex.getErrorCode(),
                "Webhook delivery error",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Handles Spring's MethodArgumentNotValidException for @Valid annotation validation failures.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response with validation errors
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpServletRequest request) {
        log.warn("Method argument validation failed: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                "VALIDATION_ERROR",
                "Validation error",
                "Method argument validation failed",
                request.getRequestURI()
        );
        
        // Add all field errors to the response
        ex.getBindingResult().getFieldErrors().forEach(fieldError -> 
            errorResponse.addValidationError(fieldError.getField(), fieldError.getDefaultMessage())
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles BindException for form binding validation failures.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response with validation errors
     */
    @ExceptionHandler(BindException.class)
    public ResponseEntity<ErrorResponseDTO> handleBindException(
            BindException ex, HttpServletRequest request) {
        log.warn("Binding error: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                "BINDING_ERROR",
                "Binding error",
                "Form binding failed",
                request.getRequestURI()
        );
        
        // Add all field errors to the response
        List<FieldError> fieldErrors = ex.getBindingResult().getFieldErrors();
        fieldErrors.forEach(fieldError -> 
            errorResponse.addValidationError(fieldError.getField(), fieldError.getDefaultMessage())
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles ConstraintViolationException for bean validation failures.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response with validation errors
     */
    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ErrorResponseDTO> handleConstraintViolation(
            ConstraintViolationException ex, HttpServletRequest request) {
        log.warn("Constraint violation: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                "CONSTRAINT_VIOLATION",
                "Constraint violation",
                "Validation constraint violation",
                request.getRequestURI()
        );
        
        // Add all constraint violations to the response
        Set<ConstraintViolation<?>> violations = ex.getConstraintViolations();
        violations.forEach(violation -> {
            String propertyPath = violation.getPropertyPath().toString();
            String field = propertyPath.substring(propertyPath.lastIndexOf('.') + 1);
            errorResponse.addValidationError(field, violation.getMessage());
        });
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles MissingServletRequestParameterException for missing required request parameters.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ErrorResponseDTO> handleMissingServletRequestParameter(
            MissingServletRequestParameterException ex, HttpServletRequest request) {
        log.warn("Missing request parameter: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                "MISSING_PARAMETER",
                "Missing parameter",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        errorResponse.addValidationError(ex.getParameterName(), "Parameter is required");
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles MethodArgumentTypeMismatchException for type conversion errors in method arguments.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponseDTO> handleMethodArgumentTypeMismatch(
            MethodArgumentTypeMismatchException ex, HttpServletRequest request) {
        log.warn("Method argument type mismatch: {}", ex.getMessage());
        
        String message = String.format(
                "Parameter '%s' should be of type '%s'", 
                ex.getName(), 
                ex.getRequiredType() != null ? ex.getRequiredType().getSimpleName() : "unknown"
        );
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                "TYPE_MISMATCH",
                "Type mismatch",
                message,
                request.getRequestURI()
        );
        
        errorResponse.addValidationError(ex.getName(), message);
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles HttpMessageNotReadableException for malformed request body.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponseDTO> handleHttpMessageNotReadable(
            HttpMessageNotReadableException ex, HttpServletRequest request) {
        log.warn("Message not readable: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                "MALFORMED_JSON",
                "Malformed request",
                "Request body is malformed or invalid JSON",
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles HttpRequestMethodNotSupportedException for unsupported HTTP methods.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ErrorResponseDTO> handleHttpRequestMethodNotSupported(
            HttpRequestMethodNotSupportedException ex, HttpServletRequest request) {
        log.warn("Method not supported: {}", ex.getMessage());
        
        StringBuilder supportedMethods = new StringBuilder();
        if (ex.getSupportedMethods() != null) {
            supportedMethods.append("Supported methods are: ");
            for (String method : ex.getSupportedMethods()) {
                supportedMethods.append(method).append(" ");
            }
        }
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.METHOD_NOT_ALLOWED,
                "METHOD_NOT_ALLOWED",
                "Method not allowed",
                ex.getMessage() + ". " + supportedMethods.toString().trim(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.METHOD_NOT_ALLOWED);
    }

    /**
     * Handles HttpMediaTypeNotSupportedException for unsupported media types.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<ErrorResponseDTO> handleHttpMediaTypeNotSupported(
            HttpMediaTypeNotSupportedException ex, HttpServletRequest request) {
        log.warn("Media type not supported: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.UNSUPPORTED_MEDIA_TYPE,
                "UNSUPPORTED_MEDIA_TYPE",
                "Unsupported media type",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.UNSUPPORTED_MEDIA_TYPE);
    }

    /**
     * Handles MaxUploadSizeExceededException for file upload size limit exceeded.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ErrorResponseDTO> handleMaxUploadSizeExceeded(
            MaxUploadSizeExceededException ex, HttpServletRequest request) {
        log.warn("Max upload size exceeded: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.PAYLOAD_TOO_LARGE,
                "PAYLOAD_TOO_LARGE",
                "File too large",
                "The uploaded file exceeds the maximum allowed size",
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.PAYLOAD_TOO_LARGE);
    }

    /**
     * Handles AccessDeniedException for Spring Security access denied errors.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ErrorResponseDTO> handleAccessDeniedException(
            AccessDeniedException ex, HttpServletRequest request) {
        log.warn("Access denied: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.FORBIDDEN,
                "ACCESS_DENIED",
                "Access denied",
                "You do not have permission to access this resource",
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.FORBIDDEN);
    }

    /**
     * Handles DataIntegrityViolationException for database constraint violations.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<ErrorResponseDTO> handleDataIntegrityViolation(
            DataIntegrityViolationException ex, HttpServletRequest request) {
        log.error("Data integrity violation: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.CONFLICT,
                "DATA_INTEGRITY_VIOLATION",
                "Data integrity violation",
                "The operation would violate data integrity constraints",
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.CONFLICT);
    }

    /**
     * Handles DataAccessException for database access errors.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(DataAccessException.class)
    public ResponseEntity<ErrorResponseDTO> handleDataAccessException(
            DataAccessException ex, HttpServletRequest request) {
        log.error("Database error: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "DATABASE_ERROR",
                "Database error",
                "An error occurred while accessing the database",
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Handles IllegalArgumentException for invalid method arguments.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResponseDTO> handleIllegalArgument(
            IllegalArgumentException ex, HttpServletRequest request) {
        log.warn("Illegal argument: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.BAD_REQUEST,
                "ILLEGAL_ARGUMENT",
                "Invalid argument",
                ex.getMessage(),
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles all other exceptions not specifically handled above.
     *
     * @param ex      The exception that was thrown
     * @param request The current HTTP request
     * @return ResponseEntity containing standardized error response
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponseDTO> handleAllUncaughtException(
            Exception ex, HttpServletRequest request) {
        log.error("Uncaught exception: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.of(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "INTERNAL_SERVER_ERROR",
                "Internal server error",
                "An unexpected error occurred",
                request.getRequestURI()
        );
        
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }
}