package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.util.Constants;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link AuthorizationException} class.
 * <p>
 * These tests verify the behavior of the AuthorizationException class for 403 Forbidden
 * authorization failure scenarios. The tests cover constructor variants, message formatting,
 * HTTP status code assignment, and error detail retrieval methods.
 * </p>
 */
@DisplayName("AuthorizationException Tests")
public class AuthorizationExceptionTest {

    private static final String TEST_MESSAGE = "Test authorization exception message";
    private static final String TEST_ROLE = "SYSTEM_ADMIN";
    private static final String TEST_PERMISSION = "MANAGE_WEBHOOKS";
    private static final String TEST_RESOURCE = "webhook configuration";

    @Test
    @DisplayName("Should create exception with default message")
    void shouldCreateExceptionWithDefaultMessage() {
        // When
        AuthorizationException exception = new AuthorizationException();

        // Then
        assertEquals("Access denied. You do not have permission to perform this action.", exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertNull(exception.getRequiredRole());
        assertNull(exception.getRequiredPermission());
        assertNull(exception.getResource());
    }

    @Test
    @DisplayName("Should create exception with custom message")
    void shouldCreateExceptionWithCustomMessage() {
        // When
        AuthorizationException exception = new AuthorizationException(TEST_MESSAGE);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertNull(exception.getRequiredRole());
        assertNull(exception.getRequiredPermission());
        assertNull(exception.getResource());
    }

    @Test
    @DisplayName("Should create exception with required role and resource")
    void shouldCreateExceptionWithRequiredRoleAndResource() {
        // When
        AuthorizationException exception = new AuthorizationException(TEST_ROLE, TEST_RESOURCE);

        // Then
        assertEquals(String.format("Access denied. Role '%s' is required to access %s.", 
                TEST_ROLE, TEST_RESOURCE), exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertEquals(TEST_ROLE, exception.getRequiredRole());
        assertNull(exception.getRequiredPermission());
        assertEquals(TEST_RESOURCE, exception.getResource());
    }

    @Test
    @DisplayName("Should create exception with required role, permission and resource")
    void shouldCreateExceptionWithRequiredRolePermissionAndResource() {
        // When
        AuthorizationException exception = new AuthorizationException(TEST_ROLE, TEST_PERMISSION, TEST_RESOURCE);

        // Then
        assertEquals(String.format("Access denied. Role '%s' with permission '%s' is required to access %s.",
                TEST_ROLE, TEST_PERMISSION, TEST_RESOURCE), exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertEquals(TEST_ROLE, exception.getRequiredRole());
        assertEquals(TEST_PERMISSION, exception.getRequiredPermission());
        assertEquals(TEST_RESOURCE, exception.getResource());
    }

    @Test
    @DisplayName("Should create exception with message, cause, required role and resource")
    void shouldCreateExceptionWithMessageCauseRequiredRoleAndResource() {
        // Given
        Throwable cause = new RuntimeException("Root cause");

        // When
        AuthorizationException exception = new AuthorizationException(TEST_MESSAGE, cause, TEST_ROLE, TEST_RESOURCE);

        // Then
        assertEquals(TEST_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertEquals(TEST_ROLE, exception.getRequiredRole());
        assertNull(exception.getRequiredPermission());
        assertEquals(TEST_RESOURCE, exception.getResource());
        assertSame(cause, exception.getCause());
    }

    @Test
    @DisplayName("Should create exception for webhook configuration access")
    void shouldCreateExceptionForWebhookConfigurationAccess() {
        // When
        AuthorizationException exception = AuthorizationException.forWebhookConfiguration();

        // Then
        assertEquals(String.format("Access denied. Role '%s' is required to access %s.",
                RoleConstants.SYSTEM_ADMIN, "webhook configuration"), exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertEquals(RoleConstants.SYSTEM_ADMIN, exception.getRequiredRole());
        assertNull(exception.getRequiredPermission());
        assertEquals("webhook configuration", exception.getResource());
    }

    @Test
    @DisplayName("Should create exception for application modification")
    void shouldCreateExceptionForApplicationModification() {
        // Given
        String applicationId = "APP123";

        // When
        AuthorizationException exception = AuthorizationException.forApplicationModification(applicationId);

        // Then
        assertEquals(String.format("Access denied. Role '%s' is required to access %s.",
                RoleConstants.OPERATIONS_STAFF, String.format("application with ID %s", applicationId)), 
                exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertEquals(RoleConstants.OPERATIONS_STAFF, exception.getRequiredRole());
        assertNull(exception.getRequiredPermission());
        assertEquals(String.format("application with ID %s", applicationId), exception.getResource());
    }

    @Test
    @DisplayName("Should create exception for system configuration access")
    void shouldCreateExceptionForSystemConfigurationAccess() {
        // When
        AuthorizationException exception = AuthorizationException.forSystemConfiguration();

        // Then
        assertEquals(String.format("Access denied. Role '%s' is required to access %s.",
                RoleConstants.SYSTEM_ADMIN, "system configuration"), exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
        assertEquals(RoleConstants.SYSTEM_ADMIN, exception.getRequiredRole());
        assertNull(exception.getRequiredPermission());
        assertEquals("system configuration", exception.getResource());
    }

    @Test
    @DisplayName("Should provide consistent error details through getters")
    void shouldProvideConsistentErrorDetailsThroughGetters() {
        // Given
        AuthorizationException exception = new AuthorizationException(TEST_ROLE, TEST_PERMISSION, TEST_RESOURCE);

        // When/Then - Verify consistency across multiple calls
        assertEquals(TEST_ROLE, exception.getRequiredRole());
        assertEquals(TEST_ROLE, exception.getRequiredRole()); // Second call should return same value

        assertEquals(TEST_PERMISSION, exception.getRequiredPermission());
        assertEquals(TEST_PERMISSION, exception.getRequiredPermission()); // Second call should return same value

        assertEquals(TEST_RESOURCE, exception.getResource());
        assertEquals(TEST_RESOURCE, exception.getResource()); // Second call should return same value
    }

    @Test
    @DisplayName("Should always set HTTP status to FORBIDDEN")
    void shouldAlwaysSetHttpStatusToForbidden() {
        // Test all constructor variants
        AuthorizationException exception1 = new AuthorizationException();
        assertEquals(HttpStatus.FORBIDDEN, exception1.getHttpStatus());

        AuthorizationException exception2 = new AuthorizationException(TEST_MESSAGE);
        assertEquals(HttpStatus.FORBIDDEN, exception2.getHttpStatus());

        AuthorizationException exception3 = new AuthorizationException(TEST_ROLE, TEST_RESOURCE);
        assertEquals(HttpStatus.FORBIDDEN, exception3.getHttpStatus());

        AuthorizationException exception4 = new AuthorizationException(TEST_ROLE, TEST_PERMISSION, TEST_RESOURCE);
        assertEquals(HttpStatus.FORBIDDEN, exception4.getHttpStatus());

        Throwable cause = new RuntimeException("Root cause");
        AuthorizationException exception5 = new AuthorizationException(TEST_MESSAGE, cause, TEST_ROLE, TEST_RESOURCE);
        assertEquals(HttpStatus.FORBIDDEN, exception5.getHttpStatus());

        AuthorizationException exception6 = AuthorizationException.forWebhookConfiguration();
        assertEquals(HttpStatus.FORBIDDEN, exception6.getHttpStatus());

        AuthorizationException exception7 = AuthorizationException.forApplicationModification("APP123");
        assertEquals(HttpStatus.FORBIDDEN, exception7.getHttpStatus());

        AuthorizationException exception8 = AuthorizationException.forSystemConfiguration();
        assertEquals(HttpStatus.FORBIDDEN, exception8.getHttpStatus());
    }
}