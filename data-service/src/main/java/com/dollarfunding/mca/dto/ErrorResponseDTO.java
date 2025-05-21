package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Data Transfer Object for standardized error responses across all API endpoints.
 * This class provides a consistent structure for error information including
 * error code, message, details, timestamp, and path.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponseDTO {

    private String errorCode;
    private String message;
    private List<ValidationError> details;
    
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime timestamp;
    
    private String path;
    private int status;

    /**
     * Default constructor
     */
    public ErrorResponseDTO() {
        this.timestamp = LocalDateTime.now();
    }

    /**
     * Constructor with error message
     * 
     * @param message Error message
     */
    public ErrorResponseDTO(String message) {
        this();
        this.message = message;
    }

    /**
     * Constructor with error message and status code
     * 
     * @param message Error message
     * @param status HTTP status code
     */
    public ErrorResponseDTO(String message, int status) {
        this(message);
        this.status = status;
    }

    /**
     * Constructor with error code, message, and status
     * 
     * @param errorCode Error code
     * @param message Error message
     * @param status HTTP status code
     */
    public ErrorResponseDTO(String errorCode, String message, int status) {
        this(message, status);
        this.errorCode = errorCode;
    }

    /**
     * Nested class for validation error details
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class ValidationError {
        private String field;
        private String message;
        private Object rejectedValue;

        public ValidationError() {
        }

        public ValidationError(String field, String message) {
            this.field = field;
            this.message = message;
        }

        public ValidationError(String field, String message, Object rejectedValue) {
            this.field = field;
            this.message = message;
            this.rejectedValue = rejectedValue;
        }

        public String getField() {
            return field;
        }

        public void setField(String field) {
            this.field = field;
        }

        public String getMessage() {
            return message;
        }

        public void setMessage(String message) {
            this.message = message;
        }

        public Object getRejectedValue() {
            return rejectedValue;
        }

        public void setRejectedValue(Object rejectedValue) {
            this.rejectedValue = rejectedValue;
        }
    }

    /**
     * Add a validation error to the details list
     * 
     * @param field Field name with error
     * @param message Error message
     * @param rejectedValue The value that was rejected
     * @return This ErrorResponseDTO instance for method chaining
     */
    public ErrorResponseDTO addValidationError(String field, String message, Object rejectedValue) {
        if (details == null) {
            details = new ArrayList<>();
        }
        details.add(new ValidationError(field, message, rejectedValue));
        return this;
    }

    /**
     * Add a validation error to the details list
     * 
     * @param field Field name with error
     * @param message Error message
     * @return This ErrorResponseDTO instance for method chaining
     */
    public ErrorResponseDTO addValidationError(String field, String message) {
        if (details == null) {
            details = new ArrayList<>();
        }
        details.add(new ValidationError(field, message));
        return this;
    }

    /**
     * Builder class for creating ErrorResponseDTO instances
     */
    public static class Builder {
        private String errorCode;
        private String message;
        private List<ValidationError> details;
        private LocalDateTime timestamp;
        private String path;
        private int status;

        public Builder() {
            this.timestamp = LocalDateTime.now();
        }

        public Builder errorCode(String errorCode) {
            this.errorCode = errorCode;
            return this;
        }

        public Builder message(String message) {
            this.message = message;
            return this;
        }

        public Builder status(int status) {
            this.status = status;
            return this;
        }

        public Builder path(String path) {
            this.path = path;
            return this;
        }

        public Builder timestamp(LocalDateTime timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public Builder addValidationError(String field, String message) {
            if (details == null) {
                details = new ArrayList<>();
            }
            details.add(new ValidationError(field, message));
            return this;
        }

        public Builder addValidationError(String field, String message, Object rejectedValue) {
            if (details == null) {
                details = new ArrayList<>();
            }
            details.add(new ValidationError(field, message, rejectedValue));
            return this;
        }

        public ErrorResponseDTO build() {
            ErrorResponseDTO errorResponse = new ErrorResponseDTO();
            errorResponse.errorCode = this.errorCode;
            errorResponse.message = this.message;
            errorResponse.details = this.details;
            errorResponse.timestamp = this.timestamp;
            errorResponse.path = this.path;
            errorResponse.status = this.status;
            return errorResponse;
        }
    }

    /**
     * Create a new builder instance
     * 
     * @return A new Builder instance
     */
    public static Builder builder() {
        return new Builder();
    }

    // Getters and Setters

    public String getErrorCode() {
        return errorCode;
    }

    public void setErrorCode(String errorCode) {
        this.errorCode = errorCode;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public List<ValidationError> getDetails() {
        return details;
    }

    public void setDetails(List<ValidationError> details) {
        this.details = details;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public int getStatus() {
        return status;
    }

    public void setStatus(int status) {
        this.status = status;
    }
}