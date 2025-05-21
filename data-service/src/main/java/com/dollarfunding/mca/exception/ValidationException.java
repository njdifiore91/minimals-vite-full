package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.dto.ErrorResponseDTO.ValidationError;
import org.springframework.http.HttpStatus;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Exception thrown when validation errors occur during request processing.
 * <p>
 * This exception extends BaseException with a default HTTP status code of 400 (Bad Request)
 * and provides support for field-level validation errors. It is used by controllers and services
 * to indicate validation failures in request data, such as missing required fields or invalid formats.
 * </p>
 */
public class ValidationException extends BaseException {

    private final List<ValidationError> validationErrors;

    /**
     * Constructs a new ValidationException with the specified message.
     *
     * @param message the detail message
     */
    public ValidationException(String message) {
        super(message, HttpStatus.BAD_REQUEST);
        this.validationErrors = new ArrayList<>();
    }

    /**
     * Constructs a new ValidationException with the specified message and cause.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     */
    public ValidationException(String message, Throwable cause) {
        super(message, cause, HttpStatus.BAD_REQUEST);
        this.validationErrors = new ArrayList<>();
    }

    /**
     * Constructs a new ValidationException with the specified message and a single validation error.
     *
     * @param message       the detail message
     * @param field         the field name with validation error
     * @param errorMessage  the error message for the field
     */
    public ValidationException(String message, String field, String errorMessage) {
        super(message, HttpStatus.BAD_REQUEST);
        this.validationErrors = new ArrayList<>();
        this.validationErrors.add(new ValidationError(field, errorMessage));
    }

    /**
     * Constructs a new ValidationException with the specified message and a list of validation errors.
     *
     * @param message          the detail message
     * @param validationErrors the list of validation errors
     */
    public ValidationException(String message, List<ValidationError> validationErrors) {
        super(message, HttpStatus.BAD_REQUEST);
        this.validationErrors = new ArrayList<>(validationErrors);
    }

    /**
     * Constructs a new ValidationException with the specified error code, message, and a list of validation errors.
     *
     * @param errorCode        the error code associated with this exception
     * @param message          the detail message
     * @param validationErrors the list of validation errors
     */
    public ValidationException(String errorCode, String message, List<ValidationError> validationErrors) {
        super(errorCode, message, HttpStatus.BAD_REQUEST);
        this.validationErrors = new ArrayList<>(validationErrors);
    }

    /**
     * Returns the list of validation errors associated with this exception.
     *
     * @return an unmodifiable list of validation errors
     */
    public List<ValidationError> getValidationErrors() {
        return Collections.unmodifiableList(validationErrors);
    }

    /**
     * Adds a validation error to the list of validation errors.
     *
     * @param field        the field name with validation error
     * @param errorMessage the error message for the field
     * @return this ValidationException instance for method chaining
     */
    public ValidationException addValidationError(String field, String errorMessage) {
        this.validationErrors.add(new ValidationError(field, errorMessage));
        return this;
    }

    /**
     * Adds multiple validation errors to the list of validation errors.
     *
     * @param errors the list of validation errors to add
     * @return this ValidationException instance for method chaining
     */
    public ValidationException addValidationErrors(List<ValidationError> errors) {
        this.validationErrors.addAll(errors);
        return this;
    }

    /**
     * Returns whether this exception has any validation errors.
     *
     * @return true if this exception has validation errors, false otherwise
     */
    public boolean hasValidationErrors() {
        return !validationErrors.isEmpty();
    }

    /**
     * Returns the number of validation errors associated with this exception.
     *
     * @return the number of validation errors
     */
    public int getValidationErrorCount() {
        return validationErrors.size();
    }
}