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
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Utility class for standardized error handling in the MCA application.
 * Provides methods for error message formatting, error normalization, and error logging.
 */
public class ErrorUtil {

    private static final Logger logger = LoggerFactory.getLogger(ErrorUtil.class);
    
    // Patterns for sensitive information that should be redacted from error messages
    private static final Pattern CREDIT_CARD_PATTERN = Pattern.compile("\\b(?:\\d[ -]*?){13,16}\\b");
    private static final Pattern SSN_PATTERN = Pattern.compile("\\b\\d{3}[-]?\\d{2}[-]?\\d{4}\\b");
    private static final Pattern EIN_PATTERN = Pattern.compile("\\b\\d{2}[-]?\\d{7}\\b");
    private static final Pattern EMAIL_PATTERN = Pattern.compile("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");
    
    // List of error messages that indicate a retryable error
    private static final List<String> RETRYABLE_ERROR_MESSAGES = List.of(
            "timeout", "timed out", "connection refused", "connection reset",
            "too many requests", "service unavailable", "internal server error",
            "bad gateway", "gateway timeout", "temporarily unavailable"
    );

    /**
     * Private constructor to prevent instantiation of utility class.
     */
    private ErrorUtil() {
        throw new IllegalStateException("Utility class");
    }

    /**
     * Extracts a readable error message from an exception.
     * 
     * @param error The exception to extract the message from
     * @return A human-readable error message
     */
    public static String getErrorMessage(Throwable error) {
        if (error == null) {
            return "Unknown error occurred";
        }
        
        if (error instanceof BaseException) {
            return ((BaseException) error).getMessage();
        }
        
        if (error instanceof HttpClientErrorException) {
            HttpClientErrorException clientError = (HttpClientErrorException) error;
            return String.format("%s: %s", clientError.getStatusCode(), clientError.getStatusText());
        }
        
        if (error instanceof HttpServerErrorException) {
            HttpServerErrorException serverError = (HttpServerErrorException) error;
            return String.format("%s: %s", serverError.getStatusCode(), serverError.getStatusText());
        }
        
        if (error.getCause() != null && error.getMessage() == null) {
            return getErrorMessage(error.getCause());
        }
        
        return error.getMessage() != null ? error.getMessage() : error.getClass().getSimpleName();
    }

    /**
     * Normalizes different error types into a standardized format.
     * 
     * @param error The exception to normalize
     * @return A map containing normalized error information
     */
    public static Map<String, Object> normalizeError(Throwable error) {
        Map<String, Object> normalizedError = new HashMap<>();
        
        normalizedError.put("timestamp", System.currentTimeMillis());
        normalizedError.put("message", sanitizeErrorMessage(getErrorMessage(error)));
        normalizedError.put("type", error.getClass().getSimpleName());
        
        if (error instanceof BaseException) {
            BaseException baseException = (BaseException) error;
            normalizedError.put("code", baseException.getErrorCode());
            normalizedError.put("status", baseException.getHttpStatus().value());
        } else {
            normalizedError.put("code", "INTERNAL_ERROR");
            normalizedError.put("status", HttpStatus.INTERNAL_SERVER_ERROR.value());
        }
        
        if (error instanceof ValidationException) {
            ValidationException validationException = (ValidationException) error;
            normalizedError.put("validationErrors", validationException.getValidationErrors());
        }
        
        return normalizedError;
    }

    /**
     * Logs an error with the appropriate log level based on the error type.
     * 
     * @param error The exception to log
     * @param context Additional context information about where the error occurred
     */
    public static void logError(Throwable error, String context) {
        String errorMessage = String.format("%s: %s", context, getErrorMessage(error));
        
        if (error instanceof ResourceNotFoundException) {
            // Not found errors are expected in some cases, so log as INFO
            logger.info(errorMessage);
        } else if (error instanceof ValidationException || error instanceof BusinessRuleException) {
            // Validation and business rule errors are client errors, log as WARN
            logger.warn(errorMessage);
        } else if (error instanceof AuthorizationException) {
            // Authorization errors could indicate security issues, log as WARN
            logger.warn(errorMessage, error);
        } else {
            // All other errors are unexpected and should be logged as ERROR with stack trace
            logger.error(errorMessage, error);
        }
    }

    /**
     * Creates a standardized API error response entity from an exception.
     * 
     * @param error The exception to convert to an API response
     * @return A ResponseEntity containing the normalized error
     */
    public static ResponseEntity<Map<String, Object>> createApiError(Throwable error) {
        Map<String, Object> errorResponse = normalizeError(error);
        HttpStatus status;
        
        if (error instanceof BaseException) {
            status = ((BaseException) error).getHttpStatus();
        } else if (error instanceof HttpClientErrorException) {
            status = ((HttpClientErrorException) error).getStatusCode();
        } else if (error instanceof HttpServerErrorException) {
            status = ((HttpServerErrorException) error).getStatusCode();
        } else {
            status = HttpStatus.INTERNAL_SERVER_ERROR;
        }
        
        return new ResponseEntity<>(errorResponse, status);
    }

    /**
     * Determines if an error is retryable (i.e., the operation might succeed if retried).
     * 
     * @param error The exception to check
     * @return true if the error is retryable, false otherwise
     */
    public static boolean isRetryableError(Throwable error) {
        if (error == null) {
            return false;
        }
        
        // Network-related exceptions are generally retryable
        if (error instanceof ConnectException || 
            error instanceof SocketTimeoutException || 
            error instanceof ResourceAccessException) {
            return true;
        }
        
        // Check for HTTP status codes that indicate retryable errors
        if (error instanceof HttpServerErrorException) {
            HttpStatus status = ((HttpServerErrorException) error).getStatusCode();
            return status == HttpStatus.SERVICE_UNAVAILABLE || 
                   status == HttpStatus.GATEWAY_TIMEOUT || 
                   status == HttpStatus.TOO_MANY_REQUESTS || 
                   status == HttpStatus.INTERNAL_SERVER_ERROR;
        }
        
        // Check error message for retryable patterns
        String message = getErrorMessage(error).toLowerCase();
        for (String retryablePattern : RETRYABLE_ERROR_MESSAGES) {
            if (message.contains(retryablePattern)) {
                return true;
            }
        }
        
        // Check if cause is retryable
        return error.getCause() != null && isRetryableError(error.getCause());
    }

    /**
     * Sanitizes an error message by removing sensitive information.
     * 
     * @param message The error message to sanitize
     * @return The sanitized error message
     */
    public static String sanitizeErrorMessage(String message) {
        if (message == null) {
            return "";
        }
        
        // Replace credit card numbers with [REDACTED_CC]
        String sanitized = CREDIT_CARD_PATTERN.matcher(message).replaceAll("[REDACTED_CC]");
        
        // Replace SSNs with [REDACTED_SSN]
        sanitized = SSN_PATTERN.matcher(sanitized).replaceAll("[REDACTED_SSN]");
        
        // Replace EINs with [REDACTED_EIN]
        sanitized = EIN_PATTERN.matcher(sanitized).replaceAll("[REDACTED_EIN]");
        
        // Replace email addresses with [REDACTED_EMAIL]
        sanitized = EMAIL_PATTERN.matcher(sanitized).replaceAll("[REDACTED_EMAIL]");
        
        return sanitized;
    }

    /**
     * Builds a validation error map from Spring's BindingResult.
     * 
     * @param bindingResult The binding result containing validation errors
     * @return A map of field names to error messages
     */
    public static Map<String, String> buildValidationError(BindingResult bindingResult) {
        Map<String, String> errors = new HashMap<>();
        
        for (FieldError error : bindingResult.getFieldErrors()) {
            errors.put(error.getField(), error.getDefaultMessage());
        }
        
        return errors;
    }

    /**
     * Checks if an error is a network-related error.
     * 
     * @param error The exception to check
     * @return true if the error is network-related, false otherwise
     */
    public static boolean isNetworkError(Throwable error) {
        return error instanceof ConnectException || 
               error instanceof SocketTimeoutException || 
               error instanceof ResourceAccessException;
    }

    /**
     * Checks if an error is an authentication or authorization error.
     * 
     * @param error The exception to check
     * @return true if the error is auth-related, false otherwise
     */
    public static boolean isAuthError(Throwable error) {
        if (error instanceof AuthorizationException) {
            return true;
        }
        
        if (error instanceof HttpClientErrorException) {
            HttpStatus status = ((HttpClientErrorException) error).getStatusCode();
            return status == HttpStatus.UNAUTHORIZED || status == HttpStatus.FORBIDDEN;
        }
        
        return false;
    }

    /**
     * Checks if an error is a validation error.
     * 
     * @param error The exception to check
     * @return true if the error is validation-related, false otherwise
     */
    public static boolean isValidationError(Throwable error) {
        if (error instanceof ValidationException) {
            return true;
        }
        
        if (error instanceof HttpClientErrorException) {
            HttpStatus status = ((HttpClientErrorException) error).getStatusCode();
            return status == HttpStatus.BAD_REQUEST;
        }
        
        return false;
    }

    /**
     * Checks if an error is a business rule violation.
     * 
     * @param error The exception to check
     * @return true if the error is a business rule violation, false otherwise
     */
    public static boolean isBusinessRuleError(Throwable error) {
        if (error instanceof BusinessRuleException) {
            return true;
        }
        
        if (error instanceof HttpClientErrorException) {
            HttpStatus status = ((HttpClientErrorException) error).getStatusCode();
            return status == HttpStatus.UNPROCESSABLE_ENTITY;
        }
        
        return false;
    }

    /**
     * Checks if an error is a document processing error.
     * 
     * @param error The exception to check
     * @return true if the error is document-related, false otherwise
     */
    public static boolean isDocumentError(Throwable error) {
        return error instanceof DocumentProcessingException;
    }

    /**
     * Checks if an error is a webhook delivery error.
     * 
     * @param error The exception to check
     * @return true if the error is webhook-related, false otherwise
     */
    public static boolean isWebhookError(Throwable error) {
        return error instanceof WebhookDeliveryException;
    }
}