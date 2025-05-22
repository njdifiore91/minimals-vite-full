package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link AuthorizationException} class.
 * 
 * These tests verify that the AuthorizationException properly handles 403 Forbidden
 * authorization failure scenarios, including constructor variants with required role
 * or permission details, message formatting, and HTTP status code assignment.
 */
@DisplayName("Authorization Exception Tests")
public class AuthorizationExceptionTest {

    @Test
    @DisplayName("Default constructor should set default message and 403 status")
    void defaultConstructorShouldSetDefaultMessageAnd403Status() {
        // When
        AuthorizationException exception = new AuthorizationException();
        
        // Then
        assertEquals("You do not have permission to access this resource", exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(403, exception.getStatusCode());
        assertNull(exception.getRequiredRole());
        assertNull(exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Constructor with message should set custom message and 403 status")
    void constructorWithMessageShouldSetCustomMessageAnd403Status() {
        // Given
        String customMessage = "Custom authorization error message";
        
        // When
        AuthorizationException exception = new AuthorizationException(customMessage);
        
        // Then
        assertEquals(customMessage, exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(403, exception.getStatusCode());
        assertNull(exception.getRequiredRole());
        assertNull(exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Constructor with required role should format message correctly")
    void constructorWithRequiredRoleShouldFormatMessageCorrectly() {
        // Given
        String role = "System Admin";
        
        // When
        AuthorizationException exception = new AuthorizationException(role);
        
        // Then
        assertEquals("Access denied. Required role: " + role, exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(role, exception.getRequiredRole());
        assertArrayEquals(new String[]{role}, exception.getRequiredRoles());
        assertNull(exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Constructor with required roles array should format message correctly")
    void constructorWithRequiredRolesArrayShouldFormatMessageCorrectly() {
        // Given
        String[] roles = {"Operations Staff", "System Admin"};
        
        // When
        AuthorizationException exception = new AuthorizationException(roles);
        
        // Then
        assertEquals("Access denied. Required roles: [Operations Staff, System Admin]", exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertNull(exception.getRequiredRole());
        assertArrayEquals(roles, exception.getRequiredRoles());
        assertNull(exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Constructor with resource and role should format message correctly")
    void constructorWithResourceAndRoleShouldFormatMessageCorrectly() {
        // Given
        String resource = "webhooks";
        String role = "System Admin";
        
        // When
        AuthorizationException exception = new AuthorizationException(resource, role);
        
        // Then
        assertEquals("Access denied to resource 'webhooks'. Required role: System Admin", exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(role, exception.getRequiredRole());
        assertArrayEquals(new String[]{role}, exception.getRequiredRoles());
        assertEquals(resource, exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Constructor with resource and roles array should format message correctly")
    void constructorWithResourceAndRolesArrayShouldFormatMessageCorrectly() {
        // Given
        String resource = "applications";
        String[] roles = {"Operations Staff", "System Admin"};
        
        // When
        AuthorizationException exception = new AuthorizationException(resource, roles);
        
        // Then
        assertEquals("Access denied to resource 'applications'. Required roles: [Operations Staff, System Admin]", 
                exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertNull(exception.getRequiredRole());
        assertArrayEquals(roles, exception.getRequiredRoles());
        assertEquals(resource, exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Constructor with resource, action and role should format message correctly")
    void constructorWithResourceActionAndRoleShouldFormatMessageCorrectly() {
        // Given
        String resource = "webhooks";
        String action = "configure";
        String role = "System Admin";
        
        // When
        AuthorizationException exception = new AuthorizationException(resource, action, role);
        
        // Then
        assertEquals("Access denied to perform 'configure' on resource 'webhooks'. Required role: System Admin", 
                exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(role, exception.getRequiredRole());
        assertArrayEquals(new String[]{role}, exception.getRequiredRoles());
        assertEquals(resource, exception.getResource());
        assertEquals(action, exception.getAction());
    }

    @Test
    @DisplayName("Constructor with resource, action and roles array should format message correctly")
    void constructorWithResourceActionAndRolesArrayShouldFormatMessageCorrectly() {
        // Given
        String resource = "documents";
        String action = "view";
        String[] roles = {"Operations Staff", "System Admin"};
        
        // When
        AuthorizationException exception = new AuthorizationException(resource, action, roles);
        
        // Then
        assertEquals("Access denied to perform 'view' on resource 'documents'. Required roles: [Operations Staff, System Admin]", 
                exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertNull(exception.getRequiredRole());
        assertArrayEquals(roles, exception.getRequiredRoles());
        assertEquals(resource, exception.getResource());
        assertEquals(action, exception.getAction());
    }

    @Test
    @DisplayName("Constructor with custom message and role should set both correctly")
    void constructorWithCustomMessageAndRoleShouldSetBothCorrectly() {
        // Given
        String message = "You need admin privileges for this operation";
        String role = "System Admin";
        
        // When
        AuthorizationException exception = new AuthorizationException(message, role);
        
        // Then
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals(role, exception.getRequiredRole());
        assertArrayEquals(new String[]{role}, exception.getRequiredRoles());
        assertNull(exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Constructor with custom message and roles array should set both correctly")
    void constructorWithCustomMessageAndRolesArrayShouldSetBothCorrectly() {
        // Given
        String message = "You need operations or admin privileges for this operation";
        String[] roles = {"Operations Staff", "System Admin"};
        
        // When
        AuthorizationException exception = new AuthorizationException(message, roles);
        
        // Then
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertNull(exception.getRequiredRole());
        assertArrayEquals(roles, exception.getRequiredRoles());
        assertNull(exception.getResource());
        assertNull(exception.getAction());
    }

    @Test
    @DisplayName("Factory method for webhook configuration should create correct exception")
    void factoryMethodForWebhookConfigurationShouldCreateCorrectException() {
        // When
        AuthorizationException exception = AuthorizationException.forWebhookConfiguration();
        
        // Then
        assertEquals("Access denied to perform 'configure' on resource 'webhooks'. Required role: System Admin", 
                exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertEquals("System Admin", exception.getRequiredRole());
        assertEquals("webhooks", exception.getResource());
        assertEquals("configure", exception.getAction());
    }

    @Test
    @DisplayName("Factory method for application management should create correct exception")
    void factoryMethodForApplicationManagementShouldCreateCorrectException() {
        // When
        AuthorizationException exception = AuthorizationException.forApplicationManagement();
        
        // Then
        assertEquals("Access denied to perform 'manage' on resource 'applications'. Required roles: [Operations Staff, System Admin]", 
                exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertNull(exception.getRequiredRole());
        assertArrayEquals(new String[]{"Operations Staff", "System Admin"}, exception.getRequiredRoles());
        assertEquals("applications", exception.getResource());
        assertEquals("manage", exception.getAction());
    }

    @Test
    @DisplayName("Factory method for document access should create correct exception")
    void factoryMethodForDocumentAccessShouldCreateCorrectException() {
        // When
        AuthorizationException exception = AuthorizationException.forDocumentAccess();
        
        // Then
        assertEquals("Access denied to perform 'view' on resource 'documents'. Required roles: [Operations Staff, System Admin]", 
                exception.getMessage());
        assertEquals(HttpStatus.FORBIDDEN, exception.getHttpStatus());
        assertNull(exception.getRequiredRole());
        assertArrayEquals(new String[]{"Operations Staff", "System Admin"}, exception.getRequiredRoles());
        assertEquals("documents", exception.getResource());
        assertEquals("view", exception.getAction());
    }

    @Test
    @DisplayName("Error code should be set to FORBIDDEN")
    void errorCodeShouldBeSetToForbidden() {
        // When
        AuthorizationException exception = new AuthorizationException();
        
        // Then
        assertEquals(Constants.ErrorCode.FORBIDDEN, exception.getErrorCode());
    }
}