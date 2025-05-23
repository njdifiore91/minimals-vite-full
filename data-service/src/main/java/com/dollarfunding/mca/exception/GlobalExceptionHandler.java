package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.util.Constants;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.TypeMismatchException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.validation.ObjectError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.context.request.ServletWebRequest;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import javax.validation.ConstraintViolation;
import javax.validation.ConstraintViolationException;
import java.util.ArrayList;
import java.util.List;

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
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * Handle all custom exceptions that extend BaseException.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with appropriate status and error details
     */
    @ExceptionHandler(BaseException.class)
    public ResponseEntity<Object> handleBaseException(BaseException ex, WebRequest request) {
        log.error("Base exception occurred: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(ex.getErrorCode())
                .message(ex.getMessage())
                .status(ex.getStatusCode())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.valueOf(ex.getStatusCode()));
    }

    /**
     * Handle ResourceNotFoundException specifically for more detailed logging.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 404 status and error details
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Object> handleResourceNotFoundException(ResourceNotFoundException ex, WebRequest request) {
        log.warn("Resource not found: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(ex.getErrorCode())
                .message(ex.getMessage())
                .status(ex.getStatusCode())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.NOT_FOUND);
    }

    /**
     * Handle ValidationException specifically to include validation error details.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 400 status and validation error details
     */
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<Object> handleValidationException(ValidationException ex, WebRequest request) {
        log.warn("Validation exception: {}", ex.getMessage());
        
        ErrorResponseDTO.Builder builder = ErrorResponseDTO.builder()
                .errorCode(ex.getErrorCode())
                .message(ex.getMessage())
                .status(ex.getStatusCode())
                .path(getRequestPath(request));
        
        // Add validation error details if available
        if (ex.getValidationErrors() != null) {
            ex.getValidationErrors().forEach(error -> 
                builder.addValidationError(error.getField(), error.getMessage(), error.getRejectedValue()));
        }
        
        return new ResponseEntity<>(builder.build(), HttpStatus.BAD_REQUEST);
    }

    /**
     * Handle BusinessRuleException specifically for business rule violations.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 422 status and error details
     */
    @ExceptionHandler(BusinessRuleException.class)
    public ResponseEntity<Object> handleBusinessRuleException(BusinessRuleException ex, WebRequest request) {
        log.warn("Business rule violation: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(ex.getErrorCode())
                .message(ex.getMessage())
                .status(ex.getStatusCode())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.UNPROCESSABLE_ENTITY);
    }

    /**
     * Handle AuthorizationException specifically for authorization failures.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 403 status and error details
     */
    @ExceptionHandler(AuthorizationException.class)
    public ResponseEntity<Object> handleAuthorizationException(AuthorizationException ex, WebRequest request) {
        log.warn("Authorization failure: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(ex.getErrorCode())
                .message(ex.getMessage())
                .status(ex.getStatusCode())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.FORBIDDEN);
    }

    /**
     * Handle DocumentProcessingException specifically for document processing errors.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 500 status and error details
     */
    @ExceptionHandler(DocumentProcessingException.class)
    public ResponseEntity<Object> handleDocumentProcessingException(DocumentProcessingException ex, WebRequest request) {
        log.error("Document processing error: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(ex.getErrorCode())
                .message(ex.getMessage())
                .status(ex.getStatusCode())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Handle WebhookDeliveryException specifically for webhook delivery errors.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 500 status and error details
     */
    @ExceptionHandler(WebhookDeliveryException.class)
    public ResponseEntity<Object> handleWebhookDeliveryException(WebhookDeliveryException ex, WebRequest request) {
        log.error("Webhook delivery error: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(ex.getErrorCode())
                .message(ex.getMessage())
                .status(ex.getStatusCode())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Handle constraint violation exceptions from Bean Validation API.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 400 status and validation error details
     */
    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<Object> handleConstraintViolation(ConstraintViolationException ex, WebRequest request) {
        log.warn("Constraint violation: {}", ex.getMessage());
        
        List<String> errors = new ArrayList<>();
        ErrorResponseDTO.Builder builder = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message("Validation failed")
                .status(HttpStatus.BAD_REQUEST.value())
                .path(getRequestPath(request));
        
        for (ConstraintViolation<?> violation : ex.getConstraintViolations()) {
            String propertyPath = violation.getPropertyPath().toString();
            String field = propertyPath.contains(".") ? 
                    propertyPath.substring(propertyPath.lastIndexOf(".") + 1) : propertyPath;
            
            builder.addValidationError(field, violation.getMessage(), violation.getInvalidValue());
            errors.add(field + ": " + violation.getMessage());
        }
        
        log.debug("Constraint violations: {}", String.join(", ", errors));
        return new ResponseEntity<>(builder.build(), HttpStatus.BAD_REQUEST);
    }

    /**
     * Handle method argument type mismatch exceptions.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 400 status and error details
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<Object> handleMethodArgumentTypeMismatch(MethodArgumentTypeMismatchException ex, WebRequest request) {
        log.warn("Method argument type mismatch: {}", ex.getMessage());
        
        String message = String.format(
                "Parameter '%s' should be of type '%s'", 
                ex.getName(), 
                ex.getRequiredType() != null ? ex.getRequiredType().getSimpleName() : "unknown");
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message(message)
                .status(HttpStatus.BAD_REQUEST.value())
                .path(getRequestPath(request))
                .addValidationError(ex.getName(), message, ex.getValue())
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handle max upload size exceeded exceptions.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 413 status and error details
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<Object> handleMaxUploadSizeExceeded(MaxUploadSizeExceededException ex, WebRequest request) {
        log.warn("Max upload size exceeded: {}", ex.getMessage());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message("File size exceeds the maximum allowed limit")
                .status(HttpStatus.PAYLOAD_TOO_LARGE.value())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.PAYLOAD_TOO_LARGE);
    }

    /**
     * Handle standard Java exceptions.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 400 status and error details
     */
    @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
    public ResponseEntity<Object> handleBadRequest(RuntimeException ex, WebRequest request) {
        log.warn("Bad request: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message(ex.getMessage())
                .status(HttpStatus.BAD_REQUEST.value())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handle all other exceptions not specifically handled above.
     *
     * @param ex      the exception to handle
     * @param request the current request
     * @return a ResponseEntity with 500 status and error details
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Object> handleAllUncaughtException(Exception ex, WebRequest request) {
        log.error("Uncaught exception: {}", ex.getMessage(), ex);
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.GENERAL_ERROR)
                .message("An unexpected error occurred")
                .status(HttpStatus.INTERNAL_SERVER_ERROR.value())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Override to handle method argument not valid exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 400 status and validation error details
     */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("Method argument validation failed: {}", ex.getMessage());
        
        List<String> errors = new ArrayList<>();
        ErrorResponseDTO.Builder builder = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message("Validation failed")
                .status(status.value())
                .path(getRequestPath(request));
        
        // Process field errors
        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            builder.addValidationError(error.getField(), error.getDefaultMessage(), error.getRejectedValue());
            errors.add(error.getField() + ": " + error.getDefaultMessage());
        }
        
        // Process global errors
        for (ObjectError error : ex.getBindingResult().getGlobalErrors()) {
            builder.addValidationError(error.getObjectName(), error.getDefaultMessage());
            errors.add(error.getObjectName() + ": " + error.getDefaultMessage());
        }
        
        log.debug("Validation errors: {}", String.join(", ", errors));
        return new ResponseEntity<>(builder.build(), headers, status);
    }

    /**
     * Override to handle missing servlet request parameter exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 400 status and error details
     */
    @Override
    protected ResponseEntity<Object> handleMissingServletRequestParameter(
            MissingServletRequestParameterException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("Missing request parameter: {}", ex.getMessage());
        
        String message = String.format("Parameter '%s' of type '%s' is required", 
                ex.getParameterName(), ex.getParameterType());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message(message)
                .status(status.value())
                .path(getRequestPath(request))
                .addValidationError(ex.getParameterName(), message)
                .build();
        
        return new ResponseEntity<>(errorResponse, headers, status);
    }

    /**
     * Override to handle bind exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 400 status and validation error details
     */
    @Override
    protected ResponseEntity<Object> handleBindException(
            BindException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("Bind exception: {}", ex.getMessage());
        
        List<String> errors = new ArrayList<>();
        ErrorResponseDTO.Builder builder = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message("Binding failed")
                .status(status.value())
                .path(getRequestPath(request));
        
        // Process field errors
        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            builder.addValidationError(error.getField(), error.getDefaultMessage(), error.getRejectedValue());
            errors.add(error.getField() + ": " + error.getDefaultMessage());
        }
        
        // Process global errors
        for (ObjectError error : ex.getBindingResult().getGlobalErrors()) {
            builder.addValidationError(error.getObjectName(), error.getDefaultMessage());
            errors.add(error.getObjectName() + ": " + error.getDefaultMessage());
        }
        
        log.debug("Binding errors: {}", String.join(", ", errors));
        return new ResponseEntity<>(builder.build(), headers, status);
    }

    /**
     * Override to handle type mismatch exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 400 status and error details
     */
    @Override
    protected ResponseEntity<Object> handleTypeMismatch(
            TypeMismatchException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("Type mismatch: {}", ex.getMessage());
        
        String message = String.format(
                "Value '%s' for property '%s' should be of type '%s'", 
                ex.getValue(), 
                ex.getPropertyName(), 
                ex.getRequiredType() != null ? ex.getRequiredType().getSimpleName() : "unknown");
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message(message)
                .status(status.value())
                .path(getRequestPath(request))
                .addValidationError(ex.getPropertyName(), message, ex.getValue())
                .build();
        
        return new ResponseEntity<>(errorResponse, headers, status);
    }

    /**
     * Override to handle HTTP message not readable exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 400 status and error details
     */
    @Override
    protected ResponseEntity<Object> handleHttpMessageNotReadable(
            HttpMessageNotReadableException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("Message not readable: {}", ex.getMessage());
        
        String message = "Malformed JSON request";
        Throwable cause = ex.getCause();
        if (cause != null) {
            message = cause.getMessage();
        }
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message(message)
                .status(status.value())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, headers, status);
    }

    /**
     * Override to handle HTTP request method not supported exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 405 status and error details
     */
    @Override
    protected ResponseEntity<Object> handleHttpRequestMethodNotSupported(
            HttpRequestMethodNotSupportedException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("Method not supported: {}", ex.getMessage());
        
        StringBuilder builder = new StringBuilder();
        builder.append(ex.getMethod());
        builder.append(" method is not supported for this request. Supported methods are ");
        
        if (ex.getSupportedHttpMethods() != null) {
            ex.getSupportedHttpMethods().forEach(method -> builder.append(method).append(", "));
            // Remove trailing comma and space
            if (builder.length() > 2) {
                builder.setLength(builder.length() - 2);
            }
        }
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message(builder.toString())
                .status(status.value())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, headers, status);
    }

    /**
     * Override to handle HTTP media type not supported exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 415 status and error details
     */
    @Override
    protected ResponseEntity<Object> handleHttpMediaTypeNotSupported(
            HttpMediaTypeNotSupportedException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("Media type not supported: {}", ex.getMessage());
        
        StringBuilder builder = new StringBuilder();
        builder.append(ex.getContentType());
        builder.append(" media type is not supported. Supported media types are ");
        
        if (ex.getSupportedMediaTypes() != null) {
            ex.getSupportedMediaTypes().forEach(mediaType -> builder.append(mediaType).append(", "));
            // Remove trailing comma and space
            if (builder.length() > 2) {
                builder.setLength(builder.length() - 2);
            }
        }
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.VALIDATION_ERROR)
                .message(builder.toString())
                .status(status.value())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, headers, status);
    }

    /**
     * Override to handle no handler found exceptions.
     *
     * @param ex      the exception to handle
     * @param headers the headers to be written to the response
     * @param status  the selected response status
     * @param request the current request
     * @return a ResponseEntity with 404 status and error details
     */
    @Override
    protected ResponseEntity<Object> handleNoHandlerFoundException(
            NoHandlerFoundException ex,
            HttpHeaders headers,
            HttpStatus status,
            WebRequest request) {
        
        log.warn("No handler found: {}", ex.getMessage());
        
        String message = String.format("No handler found for %s %s", ex.getHttpMethod(), ex.getRequestURL());
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .errorCode(Constants.ErrorCode.NOT_FOUND)
                .message(message)
                .status(status.value())
                .path(getRequestPath(request))
                .build();
        
        return new ResponseEntity<>(errorResponse, headers, status);
    }

    /**
     * Extract the request path from the WebRequest.
     *
     * @param request the current request
     * @return the request path or "unknown" if not available
     */
    private String getRequestPath(WebRequest request) {
        if (request instanceof ServletWebRequest) {
            return ((ServletWebRequest) request).getRequest().getRequestURI();
        }
        return "unknown";
    }
}