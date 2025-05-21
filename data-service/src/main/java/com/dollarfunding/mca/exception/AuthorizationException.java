package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

import java.util.Arrays;

/**
 * Exception thrown when a user attempts to access a resource or perform an action
 * without proper authorization. This exception is used by controllers and services
 * to enforce role-based access control, such as restricting webhook configuration
 * to System Admin role.
 */
public class AuthorizationException extends BaseException {

    private final String requiredRole;
    private final String[] requiredRoles;
    private final String resource;
    private final String action;

    private static final HttpStatus DEFAULT_STATUS = HttpStatus.FORBIDDEN;
    private static final String DEFAULT_ERROR_CODE = "AUTHORIZATION_ERROR";

    /**
     * Constructs a new AuthorizationException with a default message.
     */
    public AuthorizationException() {
        super("You do not have permission to access this resource", DEFAULT_STATUS);
        this.requiredRole = null;
        this.requiredRoles = null;
        this.resource = null;
        this.action = null;
    }

    /**
     * Constructs a new AuthorizationException with the specified message.
     *
     * @param message the detail message
     */
    public AuthorizationException(String message) {
        super(message, DEFAULT_STATUS);
        this.requiredRole = null;
        this.requiredRoles = null;
        this.resource = null;
        this.action = null;
    }

    /**
     * Constructs a new AuthorizationException with the specified required role.
     *
     * @param requiredRole the role required to access the resource
     */
    public AuthorizationException(String requiredRole) {
        super("Access denied. Required role: " + requiredRole, DEFAULT_STATUS);
        this.requiredRole = requiredRole;
        this.requiredRoles = new String[]{requiredRole};
        this.resource = null;
        this.action = null;
    }

    /**
     * Constructs a new AuthorizationException with the specified required roles.
     *
     * @param requiredRoles the roles required to access the resource (any one of these roles is sufficient)
     */
    public AuthorizationException(String[] requiredRoles) {
        super("Access denied. Required roles: " + Arrays.toString(requiredRoles), DEFAULT_STATUS);
        this.requiredRole = null;
        this.requiredRoles = requiredRoles;
        this.resource = null;
        this.action = null;
    }

    /**
     * Constructs a new AuthorizationException with the specified resource and required role.
     *
     * @param resource     the resource being accessed
     * @param requiredRole the role required to access the resource
     */
    public AuthorizationException(String resource, String requiredRole) {
        super("Access denied to resource '" + resource + "'. Required role: " + requiredRole, DEFAULT_STATUS);
        this.requiredRole = requiredRole;
        this.requiredRoles = new String[]{requiredRole};
        this.resource = resource;
        this.action = null;
    }

    /**
     * Constructs a new AuthorizationException with the specified resource and required roles.
     *
     * @param resource      the resource being accessed
     * @param requiredRoles the roles required to access the resource (any one of these roles is sufficient)
     */
    public AuthorizationException(String resource, String[] requiredRoles) {
        super("Access denied to resource '" + resource + "'. Required roles: " + Arrays.toString(requiredRoles), DEFAULT_STATUS);
        this.requiredRole = null;
        this.requiredRoles = requiredRoles;
        this.resource = resource;
        this.action = null;
    }

    /**
     * Constructs a new AuthorizationException with the specified resource, action, and required role.
     *
     * @param resource     the resource being accessed
     * @param action       the action being performed
     * @param requiredRole the role required to perform the action on the resource
     */
    public AuthorizationException(String resource, String action, String requiredRole) {
        super("Access denied to perform '" + action + "' on resource '" + resource + "'. Required role: " + requiredRole, DEFAULT_STATUS);
        this.requiredRole = requiredRole;
        this.requiredRoles = new String[]{requiredRole};
        this.resource = resource;
        this.action = action;
    }

    /**
     * Constructs a new AuthorizationException with the specified resource, action, and required roles.
     *
     * @param resource      the resource being accessed
     * @param action        the action being performed
     * @param requiredRoles the roles required to perform the action on the resource (any one of these roles is sufficient)
     */
    public AuthorizationException(String resource, String action, String[] requiredRoles) {
        super("Access denied to perform '" + action + "' on resource '" + resource + "'. Required roles: " + Arrays.toString(requiredRoles), DEFAULT_STATUS);
        this.requiredRole = null;
        this.requiredRoles = requiredRoles;
        this.resource = resource;
        this.action = action;
    }

    /**
     * Constructs a new AuthorizationException with a custom message and the specified required role.
     *
     * @param message      the detail message
     * @param requiredRole the role required to access the resource
     */
    public AuthorizationException(String message, String requiredRole) {
        super(message, DEFAULT_STATUS);
        this.requiredRole = requiredRole;
        this.requiredRoles = new String[]{requiredRole};
        this.resource = null;
        this.action = null;
    }

    /**
     * Constructs a new AuthorizationException with a custom message and the specified required roles.
     *
     * @param message       the detail message
     * @param requiredRoles the roles required to access the resource (any one of these roles is sufficient)
     */
    public AuthorizationException(String message, String[] requiredRoles) {
        super(message, DEFAULT_STATUS);
        this.requiredRole = null;
        this.requiredRoles = requiredRoles;
        this.resource = null;
        this.action = null;
    }

    /**
     * Returns the required role to access the resource.
     *
     * @return the required role, or null if multiple roles are required or no specific role is set
     */
    public String getRequiredRole() {
        return requiredRole;
    }

    /**
     * Returns the required roles to access the resource.
     *
     * @return the required roles, or null if no specific roles are set
     */
    public String[] getRequiredRoles() {
        return requiredRoles;
    }

    /**
     * Returns the resource being accessed.
     *
     * @return the resource, or null if no specific resource is set
     */
    public String getResource() {
        return resource;
    }

    /**
     * Returns the action being performed.
     *
     * @return the action, or null if no specific action is set
     */
    public String getAction() {
        return action;
    }

    /**
     * Creates an AuthorizationException for webhook configuration access denied.
     *
     * @return a new AuthorizationException for webhook configuration
     */
    public static AuthorizationException forWebhookConfiguration() {
        return new AuthorizationException("webhooks", "configure", "System Admin");
    }

    /**
     * Creates an AuthorizationException for application management access denied.
     *
     * @return a new AuthorizationException for application management
     */
    public static AuthorizationException forApplicationManagement() {
        return new AuthorizationException("applications", "manage", new String[]{"Operations Staff", "System Admin"});
    }

    /**
     * Creates an AuthorizationException for document access denied.
     *
     * @return a new AuthorizationException for document access
     */
    public static AuthorizationException forDocumentAccess() {
        return new AuthorizationException("documents", "view", new String[]{"Operations Staff", "System Admin"});
    }
}