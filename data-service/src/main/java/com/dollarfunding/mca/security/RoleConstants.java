package com.dollarfunding.mca.security;

import java.util.Arrays;
import java.util.List;

/**
 * Constants class that defines the role names used throughout the application for authorization purposes.
 * This class provides a centralized place for role definitions to ensure consistency across the application.
 * 
 * <p>The MCA Application Processing System implements two specific roles:</p>
 * <ul>
 *   <li>Operations Staff: Read all data, write application data</li>
 *   <li>System Admin: Full access to all endpoints and webhook configuration</li>
 * </ul>
 */
public final class RoleConstants {

    /**
     * Prefix used by Spring Security for role-based authorization.
     * This prefix is automatically added by Spring Security when checking authorities.
     */
    public static final String ROLE_PREFIX = "ROLE_";

    /**
     * Operations Staff role constant.
     * <p>Permissions:</p>
     * <ul>
     *   <li>Read access to all application data</li>
     *   <li>Write access to application data</li>
     *   <li>Cannot configure webhooks or system settings</li>
     * </ul>
     */
    public static final String ROLE_OPERATIONS_STAFF = ROLE_PREFIX + "OPERATIONS_STAFF";
    
    /**
     * System Admin role constant.
     * <p>Permissions:</p>
     * <ul>
     *   <li>Full access to all endpoints</li>
     *   <li>Full access to webhook configuration</li>
     *   <li>Access to system settings and configurations</li>
     *   <li>User management capabilities</li>
     * </ul>
     */
    public static final String ROLE_SYSTEM_ADMIN = ROLE_PREFIX + "SYSTEM_ADMIN";
    
    /**
     * Operations Staff role name without the ROLE_ prefix.
     * This constant is used for frontend integration where the ROLE_ prefix is not needed.
     */
    public static final String OPERATIONS_STAFF = "OPERATIONS_STAFF";
    
    /**
     * System Admin role name without the ROLE_ prefix.
     * This constant is used for frontend integration where the ROLE_ prefix is not needed.
     */
    public static final String SYSTEM_ADMIN = "SYSTEM_ADMIN";
    
    /**
     * List of all valid roles in the system without the ROLE_ prefix.
     * This list is used for role validation.
     */
    public static final List<String> VALID_ROLES = Arrays.asList(
            OPERATIONS_STAFF,
            SYSTEM_ADMIN
    );
    
    /**
     * List of all valid roles in the system with the ROLE_ prefix.
     * This list is used for Spring Security authorization checks.
     */
    public static final List<String> VALID_SPRING_ROLES = Arrays.asList(
            ROLE_OPERATIONS_STAFF,
            ROLE_SYSTEM_ADMIN
    );
    
    /**
     * Private constructor to prevent instantiation of this utility class.
     */
    private RoleConstants() {
        throw new IllegalStateException("Utility class");
    }
    
    /**
     * Validates if the provided role is a valid role in the system.
     * 
     * @param role The role to validate (without ROLE_ prefix)
     * @return true if the role is valid, false otherwise
     */
    public static boolean isValidRole(String role) {
        return role != null && VALID_ROLES.contains(role.toUpperCase());
    }
    
    /**
     * Converts a role name to its Spring Security format by adding the ROLE_ prefix if not present.
     * 
     * @param role The role name to convert
     * @return The role name with ROLE_ prefix
     */
    public static String toSpringRole(String role) {
        if (role == null) {
            return null;
        }
        
        String upperRole = role.toUpperCase();
        if (upperRole.startsWith(ROLE_PREFIX)) {
            return upperRole;
        }
        
        return ROLE_PREFIX + upperRole;
    }
    
    /**
     * Converts a Spring Security role (with ROLE_ prefix) to a simple role name.
     * 
     * @param springRole The Spring Security role name
     * @return The role name without ROLE_ prefix, or the original string if prefix is not present
     */
    public static String fromSpringRole(String springRole) {
        if (springRole == null) {
            return null;
        }
        
        if (springRole.startsWith(ROLE_PREFIX)) {
            return springRole.substring(ROLE_PREFIX.length());
        }
        
        return springRole;
    }
}