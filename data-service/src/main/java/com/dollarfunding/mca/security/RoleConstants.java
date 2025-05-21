package com.dollarfunding.mca.security;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * Constants class that defines the role names used throughout the application for authorization purposes.
 * This class provides a centralized place for role definitions to ensure consistency across the application.
 */
public final class RoleConstants {

    /**
     * Role prefix used by Spring Security for role-based authorization.
     * All role names should be prefixed with this value.
     */
    public static final String ROLE_PREFIX = "ROLE_";

    /**
     * Operations Staff role constant.
     * Operations Staff have permissions to:
     * - Read all application data
     * - Write/update application data
     * - View documents
     * - Process applications
     * - Generate reports
     */
    public static final String ROLE_OPERATIONS_STAFF = "ROLE_OPERATIONS_STAFF";

    /**
     * System Admin role constant.
     * System Admins have permissions to:
     * - Full access to all endpoints
     * - Configure webhooks
     * - Manage users and roles
     * - Access system settings
     * - View audit logs
     * - All permissions of Operations Staff
     */
    public static final String ROLE_SYSTEM_ADMIN = "ROLE_SYSTEM_ADMIN";

    /**
     * Role name without prefix for Operations Staff.
     */
    public static final String OPERATIONS_STAFF = "OPERATIONS_STAFF";

    /**
     * Role name without prefix for System Admin.
     */
    public static final String SYSTEM_ADMIN = "SYSTEM_ADMIN";

    /**
     * Description for Operations Staff role.
     */
    public static final String OPERATIONS_STAFF_DESCRIPTION = 
            "Operations Staff with access to read all data and write application data";

    /**
     * Description for System Admin role.
     */
    public static final String SYSTEM_ADMIN_DESCRIPTION = 
            "System Admin with full access to all endpoints and webhook configuration";

    /**
     * Set of all valid role names with prefix.
     */
    public static final Set<String> ALL_ROLES = new HashSet<>(Arrays.asList(
            ROLE_OPERATIONS_STAFF,
            ROLE_SYSTEM_ADMIN
    ));

    /**
     * Private constructor to prevent instantiation.
     */
    private RoleConstants() {
        // Private constructor to prevent instantiation
    }

    /**
     * Checks if the provided role name is valid.
     *
     * @param roleName the role name to validate
     * @return true if the role name is valid, false otherwise
     */
    public static boolean isValidRole(String roleName) {
        return ALL_ROLES.contains(roleName);
    }

    /**
     * Adds the role prefix to a role name if it doesn't already have it.
     *
     * @param roleName the role name to add the prefix to
     * @return the role name with the prefix
     */
    public static String addRolePrefix(String roleName) {
        if (roleName == null || roleName.isEmpty()) {
            return roleName;
        }
        
        return roleName.startsWith(ROLE_PREFIX) ? roleName : ROLE_PREFIX + roleName;
    }

    /**
     * Removes the role prefix from a role name if it has it.
     *
     * @param roleName the role name to remove the prefix from
     * @return the role name without the prefix
     */
    public static String removeRolePrefix(String roleName) {
        if (roleName == null || roleName.isEmpty()) {
            return roleName;
        }
        
        return roleName.startsWith(ROLE_PREFIX) ? roleName.substring(ROLE_PREFIX.length()) : roleName;
    }

    /**
     * Gets the description for a role name.
     *
     * @param roleName the role name to get the description for
     * @return the description for the role, or null if the role is not recognized
     */
    public static String getRoleDescription(String roleName) {
        String normalizedRole = addRolePrefix(roleName);
        
        if (ROLE_OPERATIONS_STAFF.equals(normalizedRole)) {
            return OPERATIONS_STAFF_DESCRIPTION;
        } else if (ROLE_SYSTEM_ADMIN.equals(normalizedRole)) {
            return SYSTEM_ADMIN_DESCRIPTION;
        }
        
        return null;
    }

    /**
     * Checks if the provided role name is for Operations Staff.
     *
     * @param roleName the role name to check
     * @return true if the role name is for Operations Staff, false otherwise
     */
    public static boolean isOperationsStaffRole(String roleName) {
        return ROLE_OPERATIONS_STAFF.equals(addRolePrefix(roleName));
    }

    /**
     * Checks if the provided role name is for System Admin.
     *
     * @param roleName the role name to check
     * @return true if the role name is for System Admin, false otherwise
     */
    public static boolean isSystemAdminRole(String roleName) {
        return ROLE_SYSTEM_ADMIN.equals(addRolePrefix(roleName));
    }

    /**
     * Creates a new Role entity for Operations Staff.
     *
     * @return a new Role entity for Operations Staff
     */
    public static Role createOperationsStaffRole() {
        return new Role(ROLE_OPERATIONS_STAFF, OPERATIONS_STAFF_DESCRIPTION);
    }

    /**
     * Creates a new Role entity for System Admin.
     *
     * @return a new Role entity for System Admin
     */
    public static Role createSystemAdminRole() {
        return new Role(ROLE_SYSTEM_ADMIN, SYSTEM_ADMIN_DESCRIPTION);
    }
}