package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.http.HttpStatus;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * DTO class for standardized error responses.
 * <p>
 * This class defines a consistent structure for error information including error code,
 * message, details, timestamp, and path. It is used by the global exception handler
 * to provide uniform error responses across all API endpoints.
 * </p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponseDTO {

    /**
     * HTTP status code of the error response
     */
    private int status;

    /**
     * Application-specific error code
     */
    private String code;

    /**
     * Human-readable error message
     */
    private String message;

    /**
     * Detailed error description
     */
    private String details;

    /**
     * Request path that generated the error
     */
    private String path;

    /**
     * Timestamp when the error occurred
     */
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime timestamp;

    /**
     * List of field-level validation errors
     */
    @Builder.Default
    private List<ValidationError> errors = new ArrayList<>();

    /**
     * Static factory method to create an error response from an HTTP status
     *
     * @param status  HTTP status code
     * @param message Error message
     * @param path    Request path
     * @return ErrorResponseDTO instance
     */
    public static ErrorResponseDTO of(HttpStatus status, String message, String path) {
        return ErrorResponseDTO.builder()
                .status(status.value())
                .code(status.name())
                .message(message)
                .path(path)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * Static factory method to create an error response with details
     *
     * @param status  HTTP status code
     * @param message Error message
     * @param details Detailed error description
     * @param path    Request path
     * @return ErrorResponseDTO instance
     */
    public static ErrorResponseDTO of(HttpStatus status, String message, String details, String path) {
        return ErrorResponseDTO.builder()
                .status(status.value())
                .code(status.name())
                .message(message)
                .details(details)
                .path(path)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * Static factory method to create an error response with a custom error code
     *
     * @param status  HTTP status code
     * @param code    Custom error code
     * @param message Error message
     * @param details Detailed error description
     * @param path    Request path
     * @return ErrorResponseDTO instance
     */
    public static ErrorResponseDTO of(HttpStatus status, String code, String message, String details, String path) {
        return ErrorResponseDTO.builder()
                .status(status.value())
                .code(code)
                .message(message)
                .details(details)
                .path(path)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * Add a validation error to the error response
     *
     * @param field   Field name with validation error
     * @param message Error message for the field
     * @return This ErrorResponseDTO instance for method chaining
     */
    public ErrorResponseDTO addValidationError(String field, String message) {
        if (this.errors == null) {
            this.errors = new ArrayList<>();
        }
        this.errors.add(new ValidationError(field, message));
        return this;
    }

    /**
     * Add multiple validation errors to the error response
     *
     * @param validationErrors List of validation errors to add
     * @return This ErrorResponseDTO instance for method chaining
     */
    public ErrorResponseDTO addValidationErrors(List<ValidationError> validationErrors) {
        if (this.errors == null) {
            this.errors = new ArrayList<>();
        }
        this.errors.addAll(validationErrors);
        return this;
    }

    /**
     * Inner class representing a field-level validation error
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ValidationError {
        /**
         * Field name with validation error
         */
        private String field;

        /**
         * Error message for the field
         */
        private String message;
    }
}