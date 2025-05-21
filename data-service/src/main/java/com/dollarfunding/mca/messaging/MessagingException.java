package com.dollarfunding.mca.messaging;

/**
 * Custom exception class for messaging-related errors in the MCA application.
 * It extends RuntimeException and provides specialized handling for RabbitMQ connection issues,
 * message serialization/deserialization errors, and delivery failures.
 */
public class MessagingException extends RuntimeException {

    /**
     * Enum defining the possible error types for messaging exceptions.
     */
    public enum ErrorType {
        CONNECTION_ERROR,
        SERIALIZATION_ERROR,
        DESERIALIZATION_ERROR,
        DELIVERY_ERROR,
        VALIDATION_ERROR,
        PROCESSING_ERROR
    }

    private final ErrorType errorType;
    private final boolean retryable;
    private final Integer retryCount;
    private final Integer maxRetries;

    /**
     * Constructor with error message and type.
     *
     * @param message   The error message
     * @param errorType The type of error
     */
    public MessagingException(String message, ErrorType errorType) {
        super(message);
        this.errorType = errorType;
        this.retryable = isRetryableErrorType(errorType);
        this.retryCount = null;
        this.maxRetries = null;
    }

    /**
     * Constructor with error message, cause, and type.
     *
     * @param message   The error message
     * @param cause     The cause of the error
     * @param errorType The type of error
     */
    public MessagingException(String message, Throwable cause, ErrorType errorType) {
        super(message, cause);
        this.errorType = errorType;
        this.retryable = isRetryableErrorType(errorType);
        this.retryCount = null;
        this.maxRetries = null;
    }

    /**
     * Constructor with error message, type, and retry information.
     *
     * @param message    The error message
     * @param errorType  The type of error
     * @param retryable  Whether the error is retryable
     * @param retryCount The current retry count
     * @param maxRetries The maximum number of retries
     */
    public MessagingException(String message, ErrorType errorType, boolean retryable, Integer retryCount, Integer maxRetries) {
        super(message);
        this.errorType = errorType;
        this.retryable = retryable;
        this.retryCount = retryCount;
        this.maxRetries = maxRetries;
    }

    /**
     * Constructor with error message, cause, type, and retry information.
     *
     * @param message    The error message
     * @param cause      The cause of the error
     * @param errorType  The type of error
     * @param retryable  Whether the error is retryable
     * @param retryCount The current retry count
     * @param maxRetries The maximum number of retries
     */
    public MessagingException(String message, Throwable cause, ErrorType errorType, boolean retryable, Integer retryCount, Integer maxRetries) {
        super(message, cause);
        this.errorType = errorType;
        this.retryable = retryable;
        this.retryCount = retryCount;
        this.maxRetries = maxRetries;
    }

    /**
     * Gets the error type.
     *
     * @return The error type
     */
    public ErrorType getErrorType() {
        return errorType;
    }

    /**
     * Checks if the error is retryable.
     *
     * @return true if the error is retryable, false otherwise
     */
    public boolean isRetryable() {
        return retryable;
    }

    /**
     * Gets the current retry count.
     *
     * @return The retry count, or null if not applicable
     */
    public Integer getRetryCount() {
        return retryCount;
    }

    /**
     * Gets the maximum number of retries.
     *
     * @return The maximum retries, or null if not applicable
     */
    public Integer getMaxRetries() {
        return maxRetries;
    }

    /**
     * Checks if the error has exceeded the maximum number of retries.
     *
     * @return true if retries are exhausted, false otherwise or if not applicable
     */
    public boolean isRetriesExhausted() {
        return retryCount != null && maxRetries != null && retryCount >= maxRetries;
    }

    /**
     * Determines if an error type is retryable by default.
     *
     * @param errorType The error type to check
     * @return true if the error type is retryable by default, false otherwise
     */
    private boolean isRetryableErrorType(ErrorType errorType) {
        switch (errorType) {
            case CONNECTION_ERROR:
            case DELIVERY_ERROR:
                return true;
            case SERIALIZATION_ERROR:
            case DESERIALIZATION_ERROR:
            case VALIDATION_ERROR:
                return false;
            case PROCESSING_ERROR:
                return true;
            default:
                return false;
        }
    }

    /**
     * Creates a connection error exception.
     *
     * @param message The error message
     * @param cause   The cause of the error
     * @return A new MessagingException for connection errors
     */
    public static MessagingException connectionError(String message, Throwable cause) {
        return new MessagingException(message, cause, ErrorType.CONNECTION_ERROR);
    }

    /**
     * Creates a serialization error exception.
     *
     * @param message The error message
     * @param cause   The cause of the error
     * @return A new MessagingException for serialization errors
     */
    public static MessagingException serializationError(String message, Throwable cause) {
        return new MessagingException(message, cause, ErrorType.SERIALIZATION_ERROR);
    }

    /**
     * Creates a deserialization error exception.
     *
     * @param message The error message
     * @param cause   The cause of the error
     * @return A new MessagingException for deserialization errors
     */
    public static MessagingException deserializationError(String message, Throwable cause) {
        return new MessagingException(message, cause, ErrorType.DESERIALIZATION_ERROR);
    }

    /**
     * Creates a delivery error exception.
     *
     * @param message    The error message
     * @param cause      The cause of the error
     * @param retryCount The current retry count
     * @param maxRetries The maximum number of retries
     * @return A new MessagingException for delivery errors
     */
    public static MessagingException deliveryError(String message, Throwable cause, Integer retryCount, Integer maxRetries) {
        return new MessagingException(message, cause, ErrorType.DELIVERY_ERROR, true, retryCount, maxRetries);
    }

    /**
     * Creates a validation error exception.
     *
     * @param message The error message
     * @return A new MessagingException for validation errors
     */
    public static MessagingException validationError(String message) {
        return new MessagingException(message, ErrorType.VALIDATION_ERROR);
    }

    /**
     * Creates a processing error exception.
     *
     * @param message    The error message
     * @param cause      The cause of the error
     * @param retryCount The current retry count
     * @param maxRetries The maximum number of retries
     * @return A new MessagingException for processing errors
     */
    public static MessagingException processingError(String message, Throwable cause, Integer retryCount, Integer maxRetries) {
        return new MessagingException(message, cause, ErrorType.PROCESSING_ERROR, true, retryCount, maxRetries);
    }
}