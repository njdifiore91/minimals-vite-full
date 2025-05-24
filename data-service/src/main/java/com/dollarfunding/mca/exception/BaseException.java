package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

/**
 * Base exception class that all custom exceptions in the MCA application extend.
 * It provides common functionality such as error code, message, and HTTP status code.
 * This class serves as the foundation for the exception hierarchy, ensuring consistent
 * error handling and response formatting across the application.
 */
public class BaseException extends RuntimeException {

    private final String errorCode;
    private final HttpStatus httpStatus;

    /**
     * Constructs a new BaseException with the specified error code, message, and HTTP status.
     *
     * @param errorCode   The error code that uniquely identifies this error type
     * @param message     The detailed error message
     * @param httpStatus  The HTTP status code to be returned to the client
     */
    public BaseException(String errorCode, String message, HttpStatus httpStatus) {
        super(message);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
    }

    /**
     * Constructs a new BaseException with the specified error code, message, HTTP status,
     * and cause.
     *
     * @param errorCode   The error code that uniquely identifies this error type
     * @param message     The detailed error message
     * @param httpStatus  The HTTP status code to be returned to the client
     * @param cause       The cause of this exception
     */
    public BaseException(String errorCode, String message, HttpStatus httpStatus, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
    }

    /**
     * Constructs a new BaseException with the specified message and HTTP status.
     * The error code will be derived from the HTTP status.
     *
     * @param message     The detailed error message
     * @param httpStatus  The HTTP status code to be returned to the client
     */
    public BaseException(String message, HttpStatus httpStatus) {
        super(message);
        this.errorCode = "ERR_" + httpStatus.value();
        this.httpStatus = httpStatus;
    }

    /**
     * Constructs a new BaseException with the specified message, HTTP status, and cause.
     * The error code will be derived from the HTTP status.
     *
     * @param message     The detailed error message
     * @param httpStatus  The HTTP status code to be returned to the client
     * @param cause       The cause of this exception
     */
    public BaseException(String message, HttpStatus httpStatus, Throwable cause) {
        super(message, cause);
        this.errorCode = "ERR_" + httpStatus.value();
        this.httpStatus = httpStatus;
    }

    /**
     * Returns the error code associated with this exception.
     *
     * @return The error code
     */
    public String getErrorCode() {
        return errorCode;
    }

    /**
     * Returns the HTTP status code associated with this exception.
     *
     * @return The HTTP status code
     */
    public HttpStatus getHttpStatus() {
        return httpStatus;
    }

    /**
     * Returns the numeric HTTP status code associated with this exception.
     *
     * @return The numeric HTTP status code
     */
    public int getStatusCode() {
        return httpStatus.value();
    }

    /**
     * Returns a string representation of this exception, including the error code,
     * HTTP status, and message.
     *
     * @return A string representation of this exception
     */
    @Override
    public String toString() {
        return String.format("BaseException{errorCode='%s', httpStatus=%s, message='%s'}",
                errorCode, httpStatus, getMessage());
    }
}