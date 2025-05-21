package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.exception.BaseException;
import org.springframework.http.HttpStatus;

/**
 * Custom exception class for messaging-related errors in the MCA application.
 * Provides specialized handling for RabbitMQ connection issues, message 
 * serialization/deserialization errors, and delivery failures.
 */
public class MessagingException extends BaseException {

    /**
     * Enum defining the types of messaging errors that can occur.
     */
    public enum ErrorType {
        CONNECTION,      // RabbitMQ connection issues
        SERIALIZATION,   // Message serialization/deserialization errors
        DELIVERY,        // Message delivery failures
        CONFIGURATION,   // Configuration-related errors
        AUTHENTICATION,  // TLS/certificate authentication errors
        UNKNOWN          // Unclassified errors
    }

    private final ErrorType errorType;
    private final RetryInfo retryInfo;

    /**
     * Class to hold retry-related information for recovery strategies.
     */
    public static class RetryInfo {
        private final int attemptCount;
        private final long lastAttemptTimestamp;
        private final long nextAttemptTimestamp;
        private final long backoffPeriodMs;

        /**
         * Constructs a new RetryInfo instance.
         *
         * @param attemptCount Number of retry attempts made so far
         * @param lastAttemptTimestamp Timestamp of the last retry attempt
         * @param nextAttemptTimestamp Timestamp for the next retry attempt
         * @param backoffPeriodMs Current backoff period in milliseconds
         */
        public RetryInfo(int attemptCount, long lastAttemptTimestamp, long nextAttemptTimestamp, long backoffPeriodMs) {
            this.attemptCount = attemptCount;
            this.lastAttemptTimestamp = lastAttemptTimestamp;
            this.nextAttemptTimestamp = nextAttemptTimestamp;
            this.backoffPeriodMs = backoffPeriodMs;
        }

        /**
         * Creates a new RetryInfo instance for the first attempt.
         *
         * @param initialBackoffMs Initial backoff period in milliseconds
         * @return A new RetryInfo instance
         */
        public static RetryInfo forFirstAttempt(long initialBackoffMs) {
            long now = System.currentTimeMillis();
            return new RetryInfo(0, 0, now, initialBackoffMs);
        }

        /**
         * Creates a new RetryInfo instance for the next attempt with exponential backoff.
         *
         * @param factor Multiplier for exponential backoff calculation
         * @return A new RetryInfo instance with updated values
         */
        public RetryInfo forNextAttempt(double factor) {
            long now = System.currentTimeMillis();
            long newBackoff = Math.min(
                    (long) (this.backoffPeriodMs * factor),
                    30_000 // Maximum backoff of 30 seconds
            );
            return new RetryInfo(
                    this.attemptCount + 1,
                    now,
                    now + newBackoff,
                    newBackoff
            );
        }

        /**
         * @return Number of retry attempts made so far
         */
        public int getAttemptCount() {
            return attemptCount;
        }

        /**
         * @return Timestamp of the last retry attempt
         */
        public long getLastAttemptTimestamp() {
            return lastAttemptTimestamp;
        }

        /**
         * @return Timestamp for the next retry attempt
         */
        public long getNextAttemptTimestamp() {
            return nextAttemptTimestamp;
        }

        /**
         * @return Current backoff period in milliseconds
         */
        public long getBackoffPeriodMs() {
            return backoffPeriodMs;
        }

        /**
         * @return Whether the next retry attempt is due based on current time
         */
        public boolean isRetryDue() {
            return System.currentTimeMillis() >= nextAttemptTimestamp;
        }

        @Override
        public String toString() {
            return String.format(
                    "RetryInfo{attempts=%d, lastAttempt=%d, nextAttempt=%d, backoffMs=%d}",
                    attemptCount, lastAttemptTimestamp, nextAttemptTimestamp, backoffPeriodMs
            );
        }
    }

    /**
     * Constructs a new MessagingException with the specified error type, message, and cause.
     *
     * @param errorType The type of messaging error
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @param retryInfo Information about retry attempts
     */
    public MessagingException(ErrorType errorType, String message, Throwable cause, RetryInfo retryInfo) {
        super("MESSAGING_" + errorType.name(), message, HttpStatus.INTERNAL_SERVER_ERROR, cause);
        this.errorType = errorType;
        this.retryInfo = retryInfo;
    }

    /**
     * Constructs a new MessagingException with the specified error type and message.
     *
     * @param errorType The type of messaging error
     * @param message Detailed error message
     * @param retryInfo Information about retry attempts
     */
    public MessagingException(ErrorType errorType, String message, RetryInfo retryInfo) {
        this(errorType, message, null, retryInfo);
    }

    /**
     * Constructs a new MessagingException with the specified error type, message, and cause.
     * Creates a new RetryInfo for the first attempt.
     *
     * @param errorType The type of messaging error
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @param initialBackoffMs Initial backoff period in milliseconds
     */
    public MessagingException(ErrorType errorType, String message, Throwable cause, long initialBackoffMs) {
        this(errorType, message, cause, RetryInfo.forFirstAttempt(initialBackoffMs));
    }

    /**
     * Constructs a new MessagingException with the specified error type and message.
     * Creates a new RetryInfo for the first attempt.
     *
     * @param errorType The type of messaging error
     * @param message Detailed error message
     * @param initialBackoffMs Initial backoff period in milliseconds
     */
    public MessagingException(ErrorType errorType, String message, long initialBackoffMs) {
        this(errorType, message, null, RetryInfo.forFirstAttempt(initialBackoffMs));
    }

    /**
     * @return The type of messaging error
     */
    public ErrorType getErrorType() {
        return errorType;
    }

    /**
     * @return Information about retry attempts
     */
    public RetryInfo getRetryInfo() {
        return retryInfo;
    }

    /**
     * Creates a new MessagingException for the next retry attempt with updated retry information.
     *
     * @param backoffFactor Multiplier for exponential backoff calculation
     * @return A new MessagingException with updated retry information
     */
    public MessagingException forNextAttempt(double backoffFactor) {
        return new MessagingException(
                this.errorType,
                this.getMessage(),
                this.getCause(),
                this.retryInfo.forNextAttempt(backoffFactor)
        );
    }

    /**
     * Factory method for creating a connection error exception.
     *
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @return A new MessagingException for connection errors
     */
    public static MessagingException connectionError(String message, Throwable cause) {
        return new MessagingException(ErrorType.CONNECTION, message, cause, 1000); // 1 second initial backoff
    }

    /**
     * Factory method for creating a serialization error exception.
     *
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @return A new MessagingException for serialization errors
     */
    public static MessagingException serializationError(String message, Throwable cause) {
        return new MessagingException(ErrorType.SERIALIZATION, message, cause, 500); // 0.5 second initial backoff
    }

    /**
     * Factory method for creating a delivery error exception.
     *
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @return A new MessagingException for delivery errors
     */
    public static MessagingException deliveryError(String message, Throwable cause) {
        return new MessagingException(ErrorType.DELIVERY, message, cause, 2000); // 2 second initial backoff
    }

    /**
     * Factory method for creating a configuration error exception.
     *
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @return A new MessagingException for configuration errors
     */
    public static MessagingException configurationError(String message, Throwable cause) {
        return new MessagingException(ErrorType.CONFIGURATION, message, cause, 5000); // 5 second initial backoff
    }

    /**
     * Factory method for creating an authentication error exception.
     *
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @return A new MessagingException for authentication errors
     */
    public static MessagingException authenticationError(String message, Throwable cause) {
        return new MessagingException(ErrorType.AUTHENTICATION, message, cause, 3000); // 3 second initial backoff
    }

    /**
     * Factory method for creating an unknown error exception.
     *
     * @param message Detailed error message
     * @param cause The underlying cause of the exception
     * @return A new MessagingException for unknown errors
     */
    public static MessagingException unknownError(String message, Throwable cause) {
        return new MessagingException(ErrorType.UNKNOWN, message, cause, 1000); // 1 second initial backoff
    }

    @Override
    public String toString() {
        return String.format(
                "MessagingException{errorType=%s, message='%s', retryInfo=%s}",
                errorType, getMessage(), retryInfo
        );
    }
}