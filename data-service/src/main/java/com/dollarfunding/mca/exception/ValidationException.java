package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.dto.ErrorResponseDTO.ValidationError;
import com.dollarfunding.mca.util.Constants;
import org.springframework.http.HttpStatus;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Exception thrown when validation errors occur during request processing.
 * <p>
 * This exception extends BaseException with a default HTTP status code of 400 (Bad Request)
 * and provides support for field-level validation errors. It is used by controllers and
 * services to indicate validation failures in request data, such as missing required fields
 * or invalid formats.
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
     * @param field         the field that failed validation
     * @param errorMessage  the validation error message
     */
    public ValidationException(String message, String field, String errorMessage) {
        super(message, HttpStatus.BAD_REQUEST);
        this.validationErrors = new ArrayList<>();
        this.validationErrors.add(new ValidationError(field, errorMessage));
    }

    /**
     * Constructs a new ValidationException with the specified message and a single validation error
     * including the rejected value.
     *
     * @param message       the detail message
     * @param field         the field that failed validation
     * @param errorMessage  the validation error message
     * @param rejectedValue the value that was rejected
     */
    public ValidationException(String message, String field, String errorMessage, Object rejectedValue) {
        super(message, HttpStatus.BAD_REQUEST);
        this.validationErrors = new ArrayList<>();
        this.validationErrors.add(new ValidationError(field, errorMessage, rejectedValue));
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
     * Adds a validation error to this exception.
     *
     * @param field        the field that failed validation
     * @param errorMessage the validation error message
     * @return this ValidationException instance for method chaining
     */
    public ValidationException addValidationError(String field, String errorMessage) {
        this.validationErrors.add(new ValidationError(field, errorMessage));
        return this;
    }

    /**
     * Adds a validation error with a rejected value to this exception.
     *
     * @param field         the field that failed validation
     * @param errorMessage  the validation error message
     * @param rejectedValue the value that was rejected
     * @return this ValidationException instance for method chaining
     */
    public ValidationException addValidationError(String field, String errorMessage, Object rejectedValue) {
        this.validationErrors.add(new ValidationError(field, errorMessage, rejectedValue));
        return this;
    }

    /**
     * Returns an unmodifiable list of validation errors associated with this exception.
     *
     * @return an unmodifiable list of validation errors
     */
    public List<ValidationError> getValidationErrors() {
        return Collections.unmodifiableList(validationErrors);
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

    /**
     * Creates a new ValidationException for a required field that is missing or empty.
     *
     * @param field the required field that is missing
     * @return a new ValidationException instance
     */
    public static ValidationException requiredField(String field) {
        return new ValidationException(
                "Required field is missing",
                field,
                "Field is required and cannot be empty");
    }

    /**
     * Creates a new ValidationException for an invalid field format.
     *
     * @param field        the field with invalid format
     * @param expectedFormat a description of the expected format
     * @param actualValue  the actual invalid value
     * @return a new ValidationException instance
     */
    public static ValidationException invalidFormat(String field, String expectedFormat, Object actualValue) {
        return new ValidationException(
                "Invalid field format",
                field,
                "Field must match format: " + expectedFormat,
                actualValue);
    }

    /**
     * Creates a new ValidationException for a field that exceeds the maximum allowed length.
     *
     * @param field       the field that exceeds maximum length
     * @param maxLength   the maximum allowed length
     * @param actualValue the actual value that exceeds the maximum length
     * @return a new ValidationException instance
     */
    public static ValidationException maxLengthExceeded(String field, int maxLength, String actualValue) {
        return new ValidationException(
                "Maximum length exceeded",
                field,
                "Field must not exceed " + maxLength + " characters",
                actualValue);
    }

    /**
     * Creates a new ValidationException for a field that is below the minimum allowed length.
     *
     * @param field       the field that is below minimum length
     * @param minLength   the minimum allowed length
     * @param actualValue the actual value that is below the minimum length
     * @return a new ValidationException instance
     */
    public static ValidationException minLengthNotMet(String field, int minLength, String actualValue) {
        return new ValidationException(
                "Minimum length not met",
                field,
                "Field must be at least " + minLength + " characters",
                actualValue);
    }

    /**
     * Creates a new ValidationException for a numeric field that exceeds the maximum allowed value.
     *
     * @param field       the field that exceeds maximum value
     * @param maxValue    the maximum allowed value
     * @param actualValue the actual value that exceeds the maximum
     * @return a new ValidationException instance
     */
    public static ValidationException maxValueExceeded(String field, Number maxValue, Number actualValue) {
        return new ValidationException(
                "Maximum value exceeded",
                field,
                "Field must not exceed " + maxValue,
                actualValue);
    }

    /**
     * Creates a new ValidationException for a numeric field that is below the minimum allowed value.
     *
     * @param field       the field that is below minimum value
     * @param minValue    the minimum allowed value
     * @param actualValue the actual value that is below the minimum
     * @return a new ValidationException instance
     */
    public static ValidationException minValueNotMet(String field, Number minValue, Number actualValue) {
        return new ValidationException(
                "Minimum value not met",
                field,
                "Field must be at least " + minValue,
                actualValue);
    }
}