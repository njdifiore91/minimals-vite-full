package com.dollarfunding.mca.util;

import com.dollarfunding.mca.exception.AuthorizationException;
import com.dollarfunding.mca.exception.BaseException;
import com.dollarfunding.mca.exception.BusinessRuleException;
import com.dollarfunding.mca.exception.DocumentProcessingException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.exception.WebhookDeliveryException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

import javax.servlet.http.HttpServletRequest;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import java.util.concurrent.TimeoutException;

/**
 * Utility class for standardized error handling across the MCA application.
 * Provides methods for error message formatting, error normalization, and error logging.
 * 
 * This class implements the following key features:
 * - Standardized error messages with getErrorMessage utility
 * - Error normalization across different error types
 * - Comprehensive logging with specified log levels (ERROR, WARN, INFO, DEBUG)
 * - Consistent error handling across the application
 * - Secure error messages that don't expose sensitive information
 * - Validation error formatting for form fields
 * - Error categorization (network, auth, validation, etc.)
 * - Retryable error detection
 */
public class ErrorUtil {

    private static final Logger logger = LoggerFactory.getLogger(ErrorUtil.class);
    
    // Patterns for sensitive information that should be redacted from error messages
    private static final Pattern SSN_PATTERN = Pattern.compile("\\d{3}-\\d{2}-\\d{4}");
    private static final Pattern CREDIT_CARD_PATTERN = Pattern.compile("\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}");
    private static final Pattern EIN_PATTERN = Pattern.compile("\\d{2}-\\d{7}");
    private static final Pattern EMAIL_PATTERN = Pattern.compile("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");
    private static final Pattern PHONE_PATTERN = Pattern.compile("\\(\\d{3}\\)\\s*\\d{3}-\\d{4}|\\d{3}-\\d{3}-\\d{4}");
    private static final Pattern ADDRESS_PATTERN = Pattern.compile("\\d+\\s+[A-Za-z0-9\\s,.]+(?:Avenue|Lane|Road|Boulevard|Drive|Street|Ave|Dr|Rd|Blvd|Ln|St)\\.?");
    
    // Network-related error messages
    private static final String NETWORK_ERROR_MESSAGE = "A network error occurred. Please check your connection and try again.";
    private static final String TIMEOUT_ERROR_MESSAGE = "The request timed out. Please try again later.";
    
    // Security-related error messages
    private static final String AUTH_ERROR_MESSAGE = "Authentication failed. Please check your credentials and try again.";
    private static final String FORBIDDEN_ERROR_MESSAGE = "You do not have permission to perform this action.";
    
    // Maximum number of retries for retryable errors
    private static final int MAX_RETRIES = 3;
    
    // Retry backoff parameters
    private static final long INITIAL_BACKOFF_MS = 1000; // 1 second
    private static final double BACKOFF_MULTIPLIER = 2.0;

    /**
     * Private constructor to prevent instantiation of utility class.
     */
    private ErrorUtil() {
        throw new IllegalStateException("Utility class");
    }

    /**
     * Extracts a readable error message from an exception.
     *
     * @param throwable The exception to extract the message from
     * @return A user-friendly error message
     */
    public static String getErrorMessage(Throwable throwable) {
        if (throwable == null) {
            return "An unknown error occurred";
        }

        // Handle custom exceptions
        if (throwable instanceof BaseException) {
            return throwable.getMessage();
        }
        
        // Handle network-related exceptions
        if (throwable instanceof ConnectException || throwable instanceof ResourceAccessException) {
            return NETWORK_ERROR_MESSAGE;
        }
        
        if (throwable instanceof SocketTimeoutException || throwable instanceof TimeoutException) {
            return TIMEOUT_ERROR_MESSAGE;
        }
        
        // Handle Spring Web Client exceptions
        if (throwable instanceof HttpClientErrorException) {
            HttpClientErrorException clientError = (HttpClientErrorException) throwable;
            return String.format("Client error: %s - %s", clientError.getStatusCode(), clientError.getStatusText());
        }
        
        if (throwable instanceof HttpServerErrorException) {
            HttpServerErrorException serverError = (HttpServerErrorException) throwable;
            return String.format("Server error: %s - %s", serverError.getStatusCode(), serverError.getStatusText());
        }

        // For other exceptions, use the message or default to a generic message
        String message = throwable.getMessage();
        return message != null && !message.isEmpty() ? message : "An unexpected error occurred";
    }

    /**
     * Normalizes different error types into a standardized format.
     *
     * @param throwable The exception to normalize
     * @return A map containing normalized error information
     */
    public static Map<String, Object> normalizeError(Throwable throwable) {
        Map<String, Object> errorMap = new HashMap<>();
        errorMap.put("timestamp", System.currentTimeMillis());
        
        if (throwable == null) {
            errorMap.put("error", "Unknown Error");
            errorMap.put("message", "An unknown error occurred");
            errorMap.put("status", HttpStatus.INTERNAL_SERVER_ERROR.value());
            return errorMap;
        }
        
        // Set error type based on exception class
        String errorType = throwable.getClass().getSimpleName();
        errorMap.put("error", errorType);
        
        // Set HTTP status code based on exception type
        HttpStatus status = determineHttpStatus(throwable);
        errorMap.put("status", status.value());
        
        // Set error message (sanitized)
        String message = getErrorMessage(throwable);
        errorMap.put("message", sanitizeErrorMessage(message));
        
        // Add additional details for specific exception types
        if (throwable instanceof ValidationException) {
            ValidationException validationException = (ValidationException) throwable;
            errorMap.put("validationErrors", validationException.getValidationErrors());
        } else if (throwable instanceof BusinessRuleException) {
            BusinessRuleException businessRuleException = (BusinessRuleException) throwable;
            errorMap.put("ruleId", businessRuleException.getRuleId());
        }
        
        return errorMap;
    }

    /**
     * Logs an error with the appropriate log level based on the exception type.
     *
     * @param logger The logger to use
     * @param throwable The exception to log
     * @param message Additional context message
     */
    public static void logError(Logger logger, Throwable throwable, String message) {
        if (logger == null || throwable == null) {
            return;
        }
        
        String logMessage = message != null ? message : "Error occurred";
        
        // Log at ERROR level for server errors and critical issues
        if (isServerError(throwable) || isCriticalError(throwable)) {
            logger.error("{}: {}", logMessage, throwable.getMessage(), throwable);
        }
        // Log at WARN level for client errors and business rule violations
        else if (isClientError(throwable) || throwable instanceof BusinessRuleException) {
            logger.warn("{}: {}", logMessage, throwable.getMessage());
        }
        // Log at INFO level for not found resources and auth issues
        else if (throwable instanceof ResourceNotFoundException || throwable instanceof AuthorizationException) {
            logger.info("{}: {}", logMessage, throwable.getMessage());
        }
        // Default to DEBUG level for all other exceptions
        else {
            logger.debug("{}: {}", logMessage, throwable.getMessage(), throwable);
        }
    }

    /**
     * Creates a standardized API error response object.
     *
     * @param throwable The exception to convert
     * @param path The request path that generated the error
     * @return A map containing the API error response
     */
    public static Map<String, Object> createApiError(Throwable throwable, String path) {
        Map<String, Object> errorResponse = normalizeError(throwable);
        
        // Add request path to the error response
        errorResponse.put("path", path);
        
        // Add trace ID if available
        String traceId = getTraceId();
        if (traceId != null && !traceId.isEmpty()) {
            errorResponse.put("traceId", traceId);
        }
        
        return errorResponse;
    }
    
    /**
     * Creates a standardized API error response object from an HttpServletRequest.
     *
     * @param throwable The exception to convert
     * @param request The HTTP request that generated the error
     * @return A map containing the API error response
     */
    public static Map<String, Object> createApiError(Throwable throwable, HttpServletRequest request) {
        String path = request != null ? request.getRequestURI() : "/unknown";
        Map<String, Object> errorResponse = createApiError(throwable, path);
        
        // Add additional request information if available
        if (request != null) {
            errorResponse.put("method", request.getMethod());
            errorResponse.put("query", request.getQueryString());
        }
        
        return errorResponse;
    }

    /**
     * Determines if an error is retryable (i.e., the operation should be retried).
     *
     * @param throwable The exception to check
     * @return true if the operation should be retried, false otherwise
     */
    public static boolean isRetryableError(Throwable throwable) {
        if (throwable == null) {
            return false;
        }
        
        // Network-related errors are typically retryable
        if (throwable instanceof ConnectException ||
            throwable instanceof SocketTimeoutException ||
            throwable instanceof TimeoutException ||
            throwable instanceof ResourceAccessException) {
            return true;
        }
        
        // Server errors (5xx) are potentially retryable
        if (throwable instanceof HttpServerErrorException) {
            HttpServerErrorException serverError = (HttpServerErrorException) throwable;
            return serverError.getStatusCode().is5xxServerError();
        }
        
        // Webhook delivery exceptions may be retryable
        if (throwable instanceof WebhookDeliveryException) {
            return true;
        }
        
        // Document processing exceptions may be retryable depending on the cause
        if (throwable instanceof DocumentProcessingException) {
            DocumentProcessingException docException = (DocumentProcessingException) throwable;
            return docException.isRetryable();
        }
        
        // All other exceptions are not retryable
        return false;
    }

    /**
     * Sanitizes error messages to remove sensitive information.
     *
     * @param message The error message to sanitize
     * @return The sanitized error message
     */
    public static String sanitizeErrorMessage(String message) {
        if (message == null || message.isEmpty()) {
            return message;
        }
        
        // Redact SSNs
        message = SSN_PATTERN.matcher(message).replaceAll("XXX-XX-XXXX");
        
        // Redact credit card numbers
        message = CREDIT_CARD_PATTERN.matcher(message).replaceAll("XXXX-XXXX-XXXX-XXXX");
        
        // Redact EINs
        message = EIN_PATTERN.matcher(message).replaceAll("XX-XXXXXXX");
        
        // Redact email addresses
        message = EMAIL_PATTERN.matcher(message).replaceAll("[EMAIL REDACTED]");
        
        // Redact phone numbers
        message = PHONE_PATTERN.matcher(message).replaceAll("[PHONE REDACTED]");
        
        // Redact addresses
        message = ADDRESS_PATTERN.matcher(message).replaceAll("[ADDRESS REDACTED]");
        
        return message;
    }

    /**
     * Builds a validation error map from Spring's BindingResult.
     *
     * @param bindingResult The binding result containing validation errors
     * @return A map of field names to error messages
     */
    public static Map<String, String> buildValidationError(BindingResult bindingResult) {
        Map<String, String> errors = new HashMap<>();
        
        if (bindingResult != null && bindingResult.hasErrors()) {
            List<FieldError> fieldErrors = bindingResult.getFieldErrors();
            
            for (FieldError fieldError : fieldErrors) {
                String fieldName = fieldError.getField();
                String errorMessage = fieldError.getDefaultMessage();
                errors.put(fieldName, errorMessage);
            }
        }
        
        return errors;
    }

    /**
     * Determines if an exception represents a network error.
     *
     * @param throwable The exception to check
     * @return true if it's a network error, false otherwise
     */
    public static boolean isNetworkError(Throwable throwable) {
        return throwable instanceof ConnectException ||
               throwable instanceof SocketTimeoutException ||
               throwable instanceof TimeoutException ||
               throwable instanceof ResourceAccessException;
    }

    /**
     * Determines if an exception represents an authentication error.
     *
     * @param throwable The exception to check
     * @return true if it's an authentication error, false otherwise
     */
    public static boolean isAuthError(Throwable throwable) {
        if (throwable instanceof HttpClientErrorException) {
            HttpClientErrorException clientError = (HttpClientErrorException) throwable;
            return clientError.getStatusCode() == HttpStatus.UNAUTHORIZED;
        }
        
        // Check for auth-related messages in the exception
        if (throwable != null && throwable.getMessage() != null) {
            String message = throwable.getMessage().toLowerCase();
            return message.contains("unauthorized") || 
                   message.contains("authentication") || 
                   message.contains("unauthenticated") || 
                   message.contains("not logged in") ||
                   message.contains("invalid token") ||
                   message.contains("expired token");
        }
        
        return false;
    }

    /**
     * Determines if an exception represents an authorization error.
     *
     * @param throwable The exception to check
     * @return true if it's an authorization error, false otherwise
     */
    public static boolean isAuthorizationError(Throwable throwable) {
        if (throwable instanceof AuthorizationException) {
            return true;
        }
        
        if (throwable instanceof HttpClientErrorException) {
            HttpClientErrorException clientError = (HttpClientErrorException) throwable;
            return clientError.getStatusCode() == HttpStatus.FORBIDDEN;
        }
        
        return false;
    }

    /**
     * Determines if an exception represents a validation error.
     *
     * @param throwable The exception to check
     * @return true if it's a validation error, false otherwise
     */
    public static boolean isValidationError(Throwable throwable) {
        return throwable instanceof ValidationException ||
               throwable instanceof org.springframework.validation.BindException ||
               throwable instanceof org.springframework.web.bind.MethodArgumentNotValidException ||
               (throwable instanceof HttpClientErrorException && 
                ((HttpClientErrorException) throwable).getStatusCode() == HttpStatus.BAD_REQUEST);
    }
    
    /**
     * Calculates the retry delay using exponential backoff.
     *
     * @param attempt The current retry attempt (1-based)
     * @return The delay in milliseconds before the next retry
     */
    public static long calculateRetryDelay(int attempt) {
        if (attempt <= 0) {
            return INITIAL_BACKOFF_MS;
        }
        
        // Calculate exponential backoff with jitter
        double exponentialDelay = INITIAL_BACKOFF_MS * Math.pow(BACKOFF_MULTIPLIER, attempt - 1);
        
        // Add random jitter (±20%)
        double jitterFactor = 0.8 + (Math.random() * 0.4); // 0.8 to 1.2
        long delay = (long) (exponentialDelay * jitterFactor);
        
        // Cap at 30 seconds
        return Math.min(delay, 30000);
    }

    /**
     * Determines if an exception represents a server error.
     *
     * @param throwable The exception to check
     * @return true if it's a server error, false otherwise
     */
    private static boolean isServerError(Throwable throwable) {
        if (throwable instanceof HttpServerErrorException) {
            return true;
        }
        
        if (throwable instanceof BaseException) {
            BaseException baseException = (BaseException) throwable;
            return baseException.getStatusCode().is5xxServerError();
        }
        
        return false;
    }

    /**
     * Determines if an exception represents a client error.
     *
     * @param throwable The exception to check
     * @return true if it's a client error, false otherwise
     */
    private static boolean isClientError(Throwable throwable) {
        if (throwable instanceof HttpClientErrorException) {
            return true;
        }
        
        if (throwable instanceof BaseException) {
            BaseException baseException = (BaseException) throwable;
            return baseException.getStatusCode().is4xxClientError();
        }
        
        return false;
    }

    /**
     * Determines if an exception represents a critical error that requires immediate attention.
     *
     * @param throwable The exception to check
     * @return true if it's a critical error, false otherwise
     */
    private static boolean isCriticalError(Throwable throwable) {
        // Consider document processing errors as critical
        if (throwable instanceof DocumentProcessingException) {
            return true;
        }
        
        // Consider webhook delivery errors as critical
        if (throwable instanceof WebhookDeliveryException) {
            return true;
        }
        
        return false;
    }

    /**
     * Determines the appropriate HTTP status code for an exception.
     *
     * @param throwable The exception to check
     * @return The appropriate HTTP status code
     */
    private static HttpStatus determineHttpStatus(Throwable throwable) {
        if (throwable instanceof BaseException) {
            BaseException baseException = (BaseException) throwable;
            return baseException.getStatusCode();
        }
        
        if (throwable instanceof HttpClientErrorException) {
            HttpClientErrorException clientError = (HttpClientErrorException) throwable;
            return clientError.getStatusCode();
        }
        
        if (throwable instanceof HttpServerErrorException) {
            HttpServerErrorException serverError = (HttpServerErrorException) throwable;
            return serverError.getStatusCode();
        }
        
        if (isNetworkError(throwable)) {
            return HttpStatus.SERVICE_UNAVAILABLE;
        }
        
        // Default to internal server error
        return HttpStatus.INTERNAL_SERVER_ERROR;
    }

    /**
     * Gets the current trace ID from the logging context, if available.
     *
     * @return The trace ID or null if not available
     */
    private static String getTraceId() {
        // This implementation would depend on the specific tracing solution used
        // For example, with Spring Cloud Sleuth or OpenTelemetry
        try {
            // For Spring Cloud Sleuth
            org.springframework.cloud.sleuth.Span currentSpan = 
                org.springframework.cloud.sleuth.Tracer.currentSpan();
            if (currentSpan != null) {
                return currentSpan.context().traceId();
            }
            // If Sleuth is not available, try MDC (used by many logging frameworks)
            return org.slf4j.MDC.get("traceId");
        } catch (Exception e) {
            // If tracing is not configured, return null
            return null;
        }
    }
}