package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.exception.BaseException;
import com.dollarfunding.mca.util.Constants;
import org.springframework.http.HttpStatus;

/**
 * Custom exception for messaging-related errors in the MCA application.
 * <p>
 * This exception is thrown when errors occur during RabbitMQ operations such as
 * connection issues, message serialization/deserialization errors, and delivery failures.
 * It includes fields for error type, retry information, and root cause details to facilitate
 * troubleshooting and recovery strategies.
 * </p>
 */
public class MessagingException extends BaseException {

    /**
     * Enum defining the types of messaging errors that can occur.
     */
    public enum ErrorType {
        /**
         * Connection-related errors (e.g., connection refused, authentication failure)
         */
        CONNECTION,
        
        /**
         * Message serialization or deserialization errors
         */
        SERIALIZATION,
        
        /**
         * Message delivery failures
         */
        DELIVERY,
        
        /**
         * Channel-related errors
         */
        CHANNEL,
        
        /**
         * Queue-related errors
         */
        QUEUE,
        
        /**
         * Exchange-related errors
         */
        EXCHANGE,
        
        /**
         * Other messaging errors
         */
        OTHER
    }

    private final ErrorType errorType;
    private final Integer retryAttempt;
    private final Long backoffPeriod;
    private final String queueOrExchange;

    /**
     * Constructs a new MessagingException with the specified message, error type, and HTTP status.
     *
     * @param message    the detail message
     * @param errorType  the type of messaging error
     * @param httpStatus the HTTP status code to be returned to the client
     */
    public MessagingException(String message, ErrorType errorType, HttpStatus httpStatus) {
        this(message, errorType, httpStatus, null, null, null, null);
    }

    /**
     * Constructs a new MessagingException with the specified message, error type, cause, and HTTP status.
     *
     * @param message    the detail message
     * @param errorType  the type of messaging error
     * @param cause      the cause of this exception
     * @param httpStatus the HTTP status code to be returned to the client
     */
    public MessagingException(String message, ErrorType errorType, Throwable cause, HttpStatus httpStatus) {
        this(message, errorType, httpStatus, cause, null, null, null);
    }

    /**
     * Constructs a new MessagingException with the specified message, error type, HTTP status,
     * retry attempt, and backoff period.
     *
     * @param message       the detail message
     * @param errorType     the type of messaging error
     * @param httpStatus    the HTTP status code to be returned to the client
     * @param retryAttempt  the current retry attempt number (null if not applicable)
     * @param backoffPeriod the backoff period in milliseconds before the next retry (null if not applicable)
     */
    public MessagingException(String message, ErrorType errorType, HttpStatus httpStatus,
                             Integer retryAttempt, Long backoffPeriod) {
        this(message, errorType, httpStatus, null, retryAttempt, backoffPeriod, null);
    }

    /**
     * Constructs a new MessagingException with all parameters.
     *
     * @param message        the detail message
     * @param errorType      the type of messaging error
     * @param httpStatus     the HTTP status code to be returned to the client
     * @param cause          the cause of this exception
     * @param retryAttempt   the current retry attempt number (null if not applicable)
     * @param backoffPeriod  the backoff period in milliseconds before the next retry (null if not applicable)
     * @param queueOrExchange the name of the queue or exchange involved (null if not applicable)
     */
    public MessagingException(String message, ErrorType errorType, HttpStatus httpStatus,
                             Throwable cause, Integer retryAttempt, Long backoffPeriod,
                             String queueOrExchange) {
        super(message, cause, httpStatus, determineErrorCode(errorType));
        this.errorType = errorType;
        this.retryAttempt = retryAttempt;
        this.backoffPeriod = backoffPeriod;
        this.queueOrExchange = queueOrExchange;
    }

    /**
     * Returns the type of messaging error.
     *
     * @return the error type
     */
    public ErrorType getErrorType() {
        return errorType;
    }

    /**
     * Returns the current retry attempt number.
     *
     * @return the retry attempt number, or null if not applicable
     */
    public Integer getRetryAttempt() {
        return retryAttempt;
    }

    /**
     * Returns the backoff period in milliseconds before the next retry.
     *
     * @return the backoff period in milliseconds, or null if not applicable
     */
    public Long getBackoffPeriod() {
        return backoffPeriod;
    }

    /**
     * Returns the name of the queue or exchange involved in the error.
     *
     * @return the queue or exchange name, or null if not applicable
     */
    public String getQueueOrExchange() {
        return queueOrExchange;
    }

    /**
     * Determines the appropriate error code based on the error type.
     *
     * @param errorType the type of messaging error
     * @return the appropriate error code
     */
    private static String determineErrorCode(ErrorType errorType) {
        if (errorType == null) {
            return Constants.ErrorCode.MESSAGING_PUBLISH_ERROR;
        }

        switch (errorType) {
            case CONNECTION:
            case CHANNEL:
            case QUEUE:
            case EXCHANGE:
                return Constants.ErrorCode.MESSAGING_PUBLISH_ERROR;
            case SERIALIZATION:
            case DELIVERY:
            case OTHER:
            default:
                return Constants.ErrorCode.MESSAGING_CONSUME_ERROR;
        }
    }

    /**
     * Creates a new MessagingException for connection errors.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     * @return a new MessagingException for connection errors
     */
    public static MessagingException connectionError(String message, Throwable cause) {
        return new MessagingException(
            message,
            ErrorType.CONNECTION,
            cause,
            HttpStatus.INTERNAL_SERVER_ERROR
        );
    }

    /**
     * Creates a new MessagingException for connection errors with retry information.
     *
     * @param message       the detail message
     * @param cause         the cause of this exception
     * @param retryAttempt  the current retry attempt number
     * @param backoffPeriod the backoff period in milliseconds before the next retry
     * @return a new MessagingException for connection errors with retry information
     */
    public static MessagingException connectionError(String message, Throwable cause,
                                                   Integer retryAttempt, Long backoffPeriod) {
        return new MessagingException(
            message,
            ErrorType.CONNECTION,
            HttpStatus.INTERNAL_SERVER_ERROR,
            cause,
            retryAttempt,
            backoffPeriod,
            null
        );
    }

    /**
     * Creates a new MessagingException for serialization errors.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     * @return a new MessagingException for serialization errors
     */
    public static MessagingException serializationError(String message, Throwable cause) {
        return new MessagingException(
            message,
            ErrorType.SERIALIZATION,
            cause,
            HttpStatus.INTERNAL_SERVER_ERROR
        );
    }

    /**
     * Creates a new MessagingException for delivery errors.
     *
     * @param message        the detail message
     * @param cause          the cause of this exception
     * @param queueOrExchange the name of the queue or exchange involved
     * @return a new MessagingException for delivery errors
     */
    public static MessagingException deliveryError(String message, Throwable cause, String queueOrExchange) {
        return new MessagingException(
            message,
            ErrorType.DELIVERY,
            HttpStatus.INTERNAL_SERVER_ERROR,
            cause,
            null,
            null,
            queueOrExchange
        );
    }

    /**
     * Creates a new MessagingException for delivery errors with retry information.
     *
     * @param message        the detail message
     * @param cause          the cause of this exception
     * @param retryAttempt   the current retry attempt number
     * @param backoffPeriod  the backoff period in milliseconds before the next retry
     * @param queueOrExchange the name of the queue or exchange involved
     * @return a new MessagingException for delivery errors with retry information
     */
    public static MessagingException deliveryError(String message, Throwable cause,
                                                 Integer retryAttempt, Long backoffPeriod,
                                                 String queueOrExchange) {
        return new MessagingException(
            message,
            ErrorType.DELIVERY,
            HttpStatus.INTERNAL_SERVER_ERROR,
            cause,
            retryAttempt,
            backoffPeriod,
            queueOrExchange
        );
    }

    /**
     * Creates a new MessagingException for channel errors.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     * @return a new MessagingException for channel errors
     */
    public static MessagingException channelError(String message, Throwable cause) {
        return new MessagingException(
            message,
            ErrorType.CHANNEL,
            cause,
            HttpStatus.INTERNAL_SERVER_ERROR
        );
    }

    /**
     * Creates a new MessagingException for queue errors.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     * @param queue   the name of the queue involved
     * @return a new MessagingException for queue errors
     */
    public static MessagingException queueError(String message, Throwable cause, String queue) {
        return new MessagingException(
            message,
            ErrorType.QUEUE,
            HttpStatus.INTERNAL_SERVER_ERROR,
            cause,
            null,
            null,
            queue
        );
    }

    /**
     * Creates a new MessagingException for exchange errors.
     *
     * @param message  the detail message
     * @param cause    the cause of this exception
     * @param exchange the name of the exchange involved
     * @return a new MessagingException for exchange errors
     */
    public static MessagingException exchangeError(String message, Throwable cause, String exchange) {
        return new MessagingException(
            message,
            ErrorType.EXCHANGE,
            HttpStatus.INTERNAL_SERVER_ERROR,
            cause,
            null,
            null,
            exchange
        );
    }
}