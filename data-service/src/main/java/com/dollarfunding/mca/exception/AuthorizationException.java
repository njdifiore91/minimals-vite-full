package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.util.Constants;
import org.springframework.http.HttpStatus;

/**
 * Exception thrown when a user attempts to access a resource or perform an action
 * without proper authorization.
 * <p>
 * This exception is used by controllers and services to enforce role-based access control,
 * such as restricting webhook configuration to System Admin role.
 * </p>
 */
public class AuthorizationException extends BaseException {

    private final String requiredRole;
    private final String requiredPermission;
    private final String resource;

    /**
     * Constructs a new AuthorizationException with a default message.
     */
    public AuthorizationException() {
        this("Access denied. You do not have permission to perform this action.");
    }

    /**
     * Constructs a new AuthorizationException with the specified message.
     *
     * @param message the detail message
     */
    public AuthorizationException(String message) {
        super(message, HttpStatus.FORBIDDEN, Constants.ErrorCode.FORBIDDEN);
        this.requiredRole = null;
        this.requiredPermission = null;
        this.resource = null;
    }

    /**
     * Constructs a new AuthorizationException with a message indicating the required role.
     *
     * @param requiredRole the role required to access the resource or perform the action
     */
    public AuthorizationException(String requiredRole, String resource) {
        super(String.format("Access denied. Role '%s' is required to access %s.", requiredRole, resource),
                HttpStatus.FORBIDDEN, Constants.ErrorCode.FORBIDDEN);
        this.requiredRole = requiredRole;
        this.requiredPermission = null;
        this.resource = resource;
    }

    /**
     * Constructs a new AuthorizationException with a message indicating the required permission.
     *
     * @param requiredPermission the permission required to access the resource or perform the action
     * @param resource the resource being accessed
     */
    public AuthorizationException(String requiredRole, String requiredPermission, String resource) {
        super(String.format("Access denied. Role '%s' with permission '%s' is required to access %s.",
                requiredRole, requiredPermission, resource),
                HttpStatus.FORBIDDEN, Constants.ErrorCode.FORBIDDEN);
        this.requiredRole = requiredRole;
        this.requiredPermission = requiredPermission;
        this.resource = resource;
    }

    /**
     * Constructs a new AuthorizationException with the specified message, cause, and required role.
     *
     * @param message the detail message
     * @param cause the cause of this exception
     * @param requiredRole the role required to access the resource or perform the action
     * @param resource the resource being accessed
     */
    public AuthorizationException(String message, Throwable cause, String requiredRole, String resource) {
        super(message, cause, HttpStatus.FORBIDDEN, Constants.ErrorCode.FORBIDDEN);
        this.requiredRole = requiredRole;
        this.requiredPermission = null;
        this.resource = resource;
    }

    /**
     * Returns the role required to access the resource or perform the action.
     *
     * @return the required role, or null if not specified
     */
    public String getRequiredRole() {
        return requiredRole;
    }

    /**
     * Returns the permission required to access the resource or perform the action.
     *
     * @return the required permission, or null if not specified
     */
    public String getRequiredPermission() {
        return requiredPermission;
    }

    /**
     * Returns the resource being accessed.
     *
     * @return the resource, or null if not specified
     */
    public String getResource() {
        return resource;
    }

    /**
     * Creates an AuthorizationException for webhook configuration access.
     * <p>
     * This is a convenience method for creating an exception when a user attempts to
     * access webhook configuration without the System Admin role.
     * </p>
     *
     * @return a new AuthorizationException for webhook configuration access
     */
    public static AuthorizationException forWebhookConfiguration() {
        return new AuthorizationException(
                com.dollarfunding.mca.security.RoleConstants.SYSTEM_ADMIN,
                "webhook configuration");
    }

    /**
     * Creates an AuthorizationException for application data modification.
     * <p>
     * This is a convenience method for creating an exception when a user attempts to
     * modify application data without the Operations Staff or System Admin role.
     * </p>
     *
     * @param applicationId the ID of the application being modified
     * @return a new AuthorizationException for application data modification
     */
    public static AuthorizationException forApplicationModification(String applicationId) {
        return new AuthorizationException(
                com.dollarfunding.mca.security.RoleConstants.OPERATIONS_STAFF,
                String.format("application with ID %s", applicationId));
    }

    /**
     * Creates an AuthorizationException for system configuration access.
     * <p>
     * This is a convenience method for creating an exception when a user attempts to
     * access system configuration without the System Admin role.
     * </p>
     *
     * @return a new AuthorizationException for system configuration access
     */
    public static AuthorizationException forSystemConfiguration() {
        return new AuthorizationException(
                com.dollarfunding.mca.security.RoleConstants.SYSTEM_ADMIN,
                "system configuration");
    }
}