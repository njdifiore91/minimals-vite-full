package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.util.Constants;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link BaseException} class.
 * <p>
 * These tests verify the core functionality of the BaseException class as the foundation
 * of the exception hierarchy in the MCA application. The tests cover constructor variants,
 * error code assignment, HTTP status code mapping, message formatting, and exception chaining.
 * </p>
 */
@DisplayName("BaseException Tests")
public class BaseExceptionTest {

    private static final String TEST_MESSAGE = "Test exception message";
    private static final String CUSTOM_ERROR_CODE = "CUSTOM-001";

    @Test
    @DisplayName("Should create exception with message and HTTP status")
    void shouldCreateExceptionWithMessageAndHttpStatus() {
        // When
        BaseException exception = new BaseException(TEST_MESSAGE, HttpStatus.BAD_REQUEST);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode());
        assertEquals(Constants.ErrorCode.VALIDATION_ERROR, exception.getErrorCode());
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message, cause, and HTTP status")
    void shouldCreateExceptionWithMessageCauseAndHttpStatus() {
        // Given
        Throwable cause = new RuntimeException("Root cause");

        // When
        BaseException exception = new BaseException(TEST_MESSAGE, cause, HttpStatus.INTERNAL_SERVER_ERROR);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, exception.getHttpStatus());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), exception.getStatusCode());
        assertEquals(Constants.ErrorCode.GENERAL_ERROR, exception.getErrorCode());
        assertSame(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message, HTTP status, and error code")
    void shouldCreateExceptionWithMessageHttpStatusAndErrorCode() {
        // When
        BaseException exception = new BaseException(TEST_MESSAGE, HttpStatus.NOT_FOUND, CUSTOM_ERROR_CODE);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.NOT_FOUND, exception.getHttpStatus());
        assertEquals(HttpStatus.NOT_FOUND.value(), exception.getStatusCode());
        assertEquals(CUSTOM_ERROR_CODE, exception.getErrorCode());
        assertNull(exception.getCause());
    }

    @Test
    @DisplayName("Should create exception with message, cause, HTTP status, and error code")
    void shouldCreateExceptionWithMessageCauseHttpStatusAndErrorCode() {
        // Given
        Throwable cause = new RuntimeException("Root cause");

        // When
        BaseException exception = new BaseException(TEST_MESSAGE, cause, HttpStatus.FORBIDDEN, CUSTOM_ERROR_CODE);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode());
        assertEquals(CUSTOM_ERROR_CODE, exception.getErrorCode());
        assertSame(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should use default error code when null is provided")
    void shouldUseDefaultErrorCodeWhenNullIsProvided() {
        // When
        BaseException exception = new BaseException(TEST_MESSAGE, HttpStatus.UNAUTHORIZED, null);

        // Then
        assertEquals(Constants.ErrorCode.UNAUTHORIZED, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should map HTTP status codes to appropriate error codes")
    void shouldMapHttpStatusCodesToAppropriateErrorCodes() {
        // Test all HTTP status code mappings
        BaseException badRequestException = new BaseException(TEST_MESSAGE, HttpStatus.BAD_REQUEST);
        assertEquals(Constants.ErrorCode.VALIDATION_ERROR, badRequestException.getErrorCode());

        BaseException unauthorizedException = new BaseException(TEST_MESSAGE, HttpStatus.UNAUTHORIZED);
        assertEquals(Constants.ErrorCode.UNAUTHORIZED, unauthorizedException.getErrorCode());

        BaseException forbiddenException = new BaseException(TEST_MESSAGE, HttpStatus.FORBIDDEN);
        assertEquals(Constants.ErrorCode.FORBIDDEN, forbiddenException.getErrorCode());

        BaseException notFoundException = new BaseException(TEST_MESSAGE, HttpStatus.NOT_FOUND);
        assertEquals(Constants.ErrorCode.NOT_FOUND, notFoundException.getErrorCode());

        BaseException unprocessableEntityException = new BaseException(TEST_MESSAGE, HttpStatus.UNPROCESSABLE_ENTITY);
        assertEquals(Constants.ErrorCode.DATA_VALIDATION_ERROR, unprocessableEntityException.getErrorCode());

        BaseException internalServerErrorException = new BaseException(TEST_MESSAGE, HttpStatus.INTERNAL_SERVER_ERROR);
        assertEquals(Constants.ErrorCode.GENERAL_ERROR, internalServerErrorException.getErrorCode());

        // Test a non-mapped status code
        BaseException serviceUnavailableException = new BaseException(TEST_MESSAGE, HttpStatus.SERVICE_UNAVAILABLE);
        assertEquals(Constants.ErrorCode.GENERAL_ERROR, serviceUnavailableException.getErrorCode());
    }

    @Test
    @DisplayName("Should handle null HTTP status by using general error code")
    void shouldHandleNullHttpStatusByUsingGeneralErrorCode() {
        // When - Using reflection to access private constructor for test purposes
        BaseException exception = new BaseException(TEST_MESSAGE, null, CUSTOM_ERROR_CODE);

        // Then
        assertNull(exception.getHttpStatus());
        assertEquals(0, exception.getStatusCode()); // Default value when HttpStatus is null
        assertEquals(CUSTOM_ERROR_CODE, exception.getErrorCode());
    }

    @Test
    @DisplayName("Should properly chain exceptions for root cause analysis")
    void shouldProperlyChainExceptionsForRootCauseAnalysis() {
        // Given
        IllegalArgumentException rootCause = new IllegalArgumentException("Invalid argument");
        RuntimeException intermediateException = new RuntimeException("Intermediate exception", rootCause);

        // When
        BaseException exception = new BaseException(TEST_MESSAGE, intermediateException, HttpStatus.BAD_REQUEST);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertSame(intermediateException, exception.getCause());
        assertSame(rootCause, exception.getCause().getCause());
        assertEquals("Invalid argument", rootCause.getMessage());
    }

    @Test
    @DisplayName("Should provide consistent error details through getters")
    void shouldProvideConsistentErrorDetailsThroughGetters() {
        // Given
        BaseException exception = new BaseException(TEST_MESSAGE, HttpStatus.BAD_REQUEST, CUSTOM_ERROR_CODE);

        // When/Then - Verify consistency across multiple calls
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(TEST_MESSAGE, exception.getMessage()); // Second call should return same value

        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getHttpStatus()); // Second call should return same value

        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode());
        assertEquals(HttpStatus.BAD_REQUEST.value(), exception.getStatusCode()); // Second call should return same value

        assertEquals(CUSTOM_ERROR_CODE, exception.getErrorCode());
        assertEquals(CUSTOM_ERROR_CODE, exception.getErrorCode()); // Second call should return same value
    }
}