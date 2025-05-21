package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.util.Constants;
import org.springframework.http.HttpStatus;

/**
 * Base exception class that all custom exceptions in the MCA application extend.
 * <p>
 * This class provides common functionality such as error code, message, and HTTP status code.
 * It serves as the foundation for the exception hierarchy, ensuring consistent error handling
 * and response formatting across the application.
 * </p>
 */
public class BaseException extends RuntimeException {

    private final String errorCode;
    private final HttpStatus httpStatus;

    /**
     * Constructs a new BaseException with the specified message and HTTP status.
     *
     * @param message    the detail message
     * @param httpStatus the HTTP status code to be returned to the client
     */
    public BaseException(String message, HttpStatus httpStatus) {
        this(message, httpStatus, null);
    }

    /**
     * Constructs a new BaseException with the specified message, cause, and HTTP status.
     *
     * @param message    the detail message
     * @param cause      the cause of this exception
     * @param httpStatus the HTTP status code to be returned to the client
     */
    public BaseException(String message, Throwable cause, HttpStatus httpStatus) {
        this(message, cause, httpStatus, determineErrorCode(httpStatus));
    }

    /**
     * Constructs a new BaseException with the specified message, HTTP status, and error code.
     *
     * @param message    the detail message
     * @param httpStatus the HTTP status code to be returned to the client
     * @param errorCode  the application-specific error code
     */
    public BaseException(String message, HttpStatus httpStatus, String errorCode) {
        super(message);
        this.httpStatus = httpStatus;
        this.errorCode = errorCode != null ? errorCode : determineErrorCode(httpStatus);
    }

    /**
     * Constructs a new BaseException with the specified message, cause, HTTP status, and error code.
     *
     * @param message    the detail message
     * @param cause      the cause of this exception
     * @param httpStatus the HTTP status code to be returned to the client
     * @param errorCode  the application-specific error code
     */
    public BaseException(String message, Throwable cause, HttpStatus httpStatus, String errorCode) {
        super(message, cause);
        this.httpStatus = httpStatus;
        this.errorCode = errorCode != null ? errorCode : determineErrorCode(httpStatus);
    }

    /**
     * Returns the HTTP status code associated with this exception.
     *
     * @return the HTTP status code
     */
    public HttpStatus getHttpStatus() {
        return httpStatus;
    }

    /**
     * Returns the application-specific error code associated with this exception.
     *
     * @return the error code
     */
    public String getErrorCode() {
        return errorCode;
    }

    /**
     * Returns the HTTP status code value associated with this exception.
     *
     * @return the HTTP status code value
     */
    public int getStatusCode() {
        return httpStatus.value();
    }

    /**
     * Determines an appropriate error code based on the HTTP status code.
     *
     * @param httpStatus the HTTP status code
     * @return an appropriate error code
     */
    private static String determineErrorCode(HttpStatus httpStatus) {
        if (httpStatus == null) {
            return Constants.ErrorCode.GENERAL_ERROR;
        }

        switch (httpStatus) {
            case BAD_REQUEST:
                return Constants.ErrorCode.VALIDATION_ERROR;
            case UNAUTHORIZED:
                return Constants.ErrorCode.UNAUTHORIZED;
            case FORBIDDEN:
                return Constants.ErrorCode.FORBIDDEN;
            case NOT_FOUND:
                return Constants.ErrorCode.NOT_FOUND;
            case UNPROCESSABLE_ENTITY:
                return Constants.ErrorCode.DATA_VALIDATION_ERROR;
            case INTERNAL_SERVER_ERROR:
            default:
                return Constants.ErrorCode.GENERAL_ERROR;
        }
    }
}