package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.exception.AuthorizationException;
import com.dollarfunding.mca.exception.BaseException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.context.request.WebRequest;

import javax.validation.Valid;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Abstract base controller class that provides common functionality for all REST controllers
 * in the MCA application. It includes global exception handling, standardized response formatting,
 * and utility methods for consistent API behavior.
 * 
 * This controller serves as the foundation for all other controllers, ensuring uniform error handling,
 * logging, and response structures across the API surface.
 */
public abstract class BaseController {

    protected final Logger logger = LoggerFactory.getLogger(getClass());

    /**
     * Creates a standardized success response with the provided data and HTTP status.
     *
     * @param data   The response data to be returned
     * @param status The HTTP status code for the response
     * @param <T>    The type of the response data
     * @return A ResponseEntity with the provided data and status
     */
    protected <T> ResponseEntity<T> createResponse(T data, HttpStatus status) {
        return new ResponseEntity<>(data, status);
    }

    /**
     * Creates a standardized success response with the provided data and HTTP status OK (200).
     *
     * @param data The response data to be returned
     * @param <T>  The type of the response data
     * @return A ResponseEntity with the provided data and status OK
     */
    protected <T> ResponseEntity<T> createSuccessResponse(T data) {
        return createResponse(data, HttpStatus.OK);
    }

    /**
     * Creates a standardized success response for created resources with HTTP status CREATED (201).
     *
     * @param data The response data to be returned
     * @param <T>  The type of the response data
     * @return A ResponseEntity with the provided data and status CREATED
     */
    protected <T> ResponseEntity<T> createCreatedResponse(T data) {
        return createResponse(data, HttpStatus.CREATED);
    }

    /**
     * Creates a standardized paginated response with the provided Page object and HTTP status OK (200).
     *
     * @param page The Spring Page object containing the paginated data
     * @param <T>  The type of the response data
     * @return A ResponseEntity with a PageResponseDTO and status OK
     */
    protected <T> ResponseEntity<PageResponseDTO<T>> createPageResponse(Page<T> page) {
        PageResponseDTO<T> pageResponse = new PageResponseDTO<>(page);
        return createSuccessResponse(pageResponse);
    }

    /**
     * Creates a standardized error response with the provided error message and HTTP status.
     *
     * @param message The error message
     * @param status  The HTTP status code for the response
     * @param request The web request that triggered the error
     * @return A ResponseEntity with an ErrorResponseDTO and the provided status
     */
    protected ResponseEntity<ErrorResponseDTO> createErrorResponse(String message, HttpStatus status, WebRequest request) {
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .status(status.value())
                .error(status.getReasonPhrase())
                .message(message)
                .path(request.getDescription(false).substring(4)) // Remove "uri=" prefix
                .build();
        return new ResponseEntity<>(errorResponse, status);
    }

    /**
     * Validates the binding result and throws a ValidationException if there are errors.
     * This method should be called after @Valid annotations are processed.
     *
     * @param bindingResult The binding result from validation
     * @throws ValidationException If there are validation errors
     */
    protected void validateBindingResult(BindingResult bindingResult) {
        if (bindingResult.hasErrors()) {
            Map<String, String> errors = new HashMap<>();
            bindingResult.getFieldErrors().forEach(error -> 
                errors.put(error.getField(), error.getDefaultMessage()));
            throw new ValidationException("Validation failed", errors);
        }
    }

    /**
     * Logs the API request with appropriate level and details.
     *
     * @param method      The HTTP method (GET, POST, etc.)
     * @param endpoint    The API endpoint
     * @param requestBody The request body (optional)
     */
    protected void logRequest(String method, String endpoint, Object requestBody) {
        if (requestBody != null) {
            logger.info("API Request: {} {} with payload: {}", method, endpoint, requestBody);
        } else {
            logger.info("API Request: {} {}", method, endpoint);
        }
    }

    /**
     * Logs the API response with appropriate level and details.
     *
     * @param method       The HTTP method (GET, POST, etc.)
     * @param endpoint     The API endpoint
     * @param responseBody The response body
     * @param status       The HTTP status code
     */
    protected void logResponse(String method, String endpoint, Object responseBody, HttpStatus status) {
        logger.info("API Response: {} {} returned {} with payload: {}", 
                method, endpoint, status.value(), responseBody);
    }

    /**
     * Exception handler for ResourceNotFoundException.
     * Returns a 404 Not Found response with details about the missing resource.
     *
     * @param ex      The exception that was thrown
     * @param request The web request that triggered the exception
     * @return A ResponseEntity with an ErrorResponseDTO and status NOT_FOUND
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponseDTO> handleResourceNotFoundException(
            ResourceNotFoundException ex, WebRequest request) {
        logger.warn("Resource not found: {}", ex.getMessage());
        return createErrorResponse(ex.getMessage(), HttpStatus.NOT_FOUND, request);
    }

    /**
     * Exception handler for AuthorizationException.
     * Returns a 403 Forbidden response with details about the authorization failure.
     *
     * @param ex      The exception that was thrown
     * @param request The web request that triggered the exception
     * @return A ResponseEntity with an ErrorResponseDTO and status FORBIDDEN
     */
    @ExceptionHandler(AuthorizationException.class)
    public ResponseEntity<ErrorResponseDTO> handleAuthorizationException(
            AuthorizationException ex, WebRequest request) {
        logger.warn("Authorization failure: {}", ex.getMessage());
        return createErrorResponse(ex.getMessage(), HttpStatus.FORBIDDEN, request);
    }

    /**
     * Exception handler for ValidationException.
     * Returns a 400 Bad Request response with details about the validation errors.
     *
     * @param ex      The exception that was thrown
     * @param request The web request that triggered the exception
     * @return A ResponseEntity with an ErrorResponseDTO and status BAD_REQUEST
     */
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<ErrorResponseDTO> handleValidationException(
            ValidationException ex, WebRequest request) {
        logger.warn("Validation error: {}", ex.getMessage());
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .status(HttpStatus.BAD_REQUEST.value())
                .error(HttpStatus.BAD_REQUEST.getReasonPhrase())
                .message(ex.getMessage())
                .path(request.getDescription(false).substring(4))
                .validationErrors(ex.getErrors())
                .build();
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Exception handler for MethodArgumentNotValidException.
     * Returns a 400 Bad Request response with details about the validation errors.
     *
     * @param ex      The exception that was thrown
     * @param request The web request that triggered the exception
     * @return A ResponseEntity with an ErrorResponseDTO and status BAD_REQUEST
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleMethodArgumentNotValidException(
            MethodArgumentNotValidException ex, WebRequest request) {
        logger.warn("Method argument validation error: {}", ex.getMessage());
        Map<String, String> errors = new HashMap<>();
        List<FieldError> fieldErrors = ex.getBindingResult().getFieldErrors();
        
        fieldErrors.forEach(error -> 
            errors.put(error.getField(), error.getDefaultMessage()));
        
        ErrorResponseDTO errorResponse = ErrorResponseDTO.builder()
                .status(HttpStatus.BAD_REQUEST.value())
                .error(HttpStatus.BAD_REQUEST.getReasonPhrase())
                .message("Validation failed")
                .path(request.getDescription(false).substring(4))
                .validationErrors(errors)
                .build();
        
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Exception handler for BaseException.
     * Returns a response with the HTTP status specified in the exception.
     *
     * @param ex      The exception that was thrown
     * @param request The web request that triggered the exception
     * @return A ResponseEntity with an ErrorResponseDTO and the status from the exception
     */
    @ExceptionHandler(BaseException.class)
    public ResponseEntity<ErrorResponseDTO> handleBaseException(
            BaseException ex, WebRequest request) {
        logger.error("Application error: {}", ex.getMessage());
        HttpStatus status = HttpStatus.valueOf(ex.getStatusCode());
        return createErrorResponse(ex.getMessage(), status, request);
    }

    /**
     * Exception handler for all other exceptions.
     * Returns a 500 Internal Server Error response.
     *
     * @param ex      The exception that was thrown
     * @param request The web request that triggered the exception
     * @return A ResponseEntity with an ErrorResponseDTO and status INTERNAL_SERVER_ERROR
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponseDTO> handleGenericException(
            Exception ex, WebRequest request) {
        logger.error("Unexpected error: {}", ex.getMessage(), ex);
        return createErrorResponse(
                "An unexpected error occurred. Please try again later.",
                HttpStatus.INTERNAL_SERVER_ERROR,
                request);
    }
}