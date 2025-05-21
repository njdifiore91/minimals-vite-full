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
     * @param errorCode   the error code associated with this exception
     * @param message     the detail message
     * @param httpStatus  the HTTP status code to be returned to the client
     */
    public BaseException(String errorCode, String message, HttpStatus httpStatus) {
        super(message);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
    }

    /**
     * Constructs a new BaseException with the specified error code, message, cause, and HTTP status.
     *
     * @param errorCode   the error code associated with this exception
     * @param message     the detail message
     * @param cause       the cause of this exception
     * @param httpStatus  the HTTP status code to be returned to the client
     */
    public BaseException(String errorCode, String message, Throwable cause, HttpStatus httpStatus) {
        super(message, cause);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
    }

    /**
     * Constructs a new BaseException with the specified message and HTTP status.
     * The error code will be derived from the exception class name.
     *
     * @param message     the detail message
     * @param httpStatus  the HTTP status code to be returned to the client
     */
    public BaseException(String message, HttpStatus httpStatus) {
        super(message);
        this.errorCode = this.getClass().getSimpleName();
        this.httpStatus = httpStatus;
    }

    /**
     * Constructs a new BaseException with the specified message, cause, and HTTP status.
     * The error code will be derived from the exception class name.
     *
     * @param message     the detail message
     * @param cause       the cause of this exception
     * @param httpStatus  the HTTP status code to be returned to the client
     */
    public BaseException(String message, Throwable cause, HttpStatus httpStatus) {
        super(message, cause);
        this.errorCode = this.getClass().getSimpleName();
        this.httpStatus = httpStatus;
    }

    /**
     * Returns the error code associated with this exception.
     *
     * @return the error code
     */
    public String getErrorCode() {
        return errorCode;
    }

    /**
     * Returns the HTTP status code to be returned to the client.
     *
     * @return the HTTP status code
     */
    public HttpStatus getHttpStatus() {
        return httpStatus;
    }
}