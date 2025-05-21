package com.dollarfunding.mca.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Utility class for Spring Security.
 * 
 * This class provides helper methods for security-related operations throughout the application,
 * including methods for retrieving the current authenticated user, checking authorities,
 * generating secure random values, and handling security-related conversions.
 */
public final class SecurityUtils {

    private static final Logger logger = LoggerFactory.getLogger(SecurityUtils.class);
    
    // Role constants
    public static final String ROLE_OPERATIONS_STAFF = "ROLE_OPERATIONS_STAFF";
    public static final String ROLE_SYSTEM_ADMIN = "ROLE_SYSTEM_ADMIN";
    
    // JWT constants
    public static final String JWT_ALGORITHM = "RS256";
    public static final long ACCESS_TOKEN_EXPIRATION_MINUTES = 60;
    public static final long REFRESH_TOKEN_EXPIRATION_DAYS = 7;
    
    private static final SecureRandom secureRandom = new SecureRandom();

    private SecurityUtils() {
        // Private constructor to prevent instantiation
    }

    /**
     * Get the login of the current user.
     *
     * @return the login of the current user, or empty if not authenticated
     */
    public static Optional<String> getCurrentUserLogin() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        if (authentication == null) {
            logger.debug("No authentication found in SecurityContext");
            return Optional.empty();
        }
        
        if (authentication.getPrincipal() instanceof String) {
            return Optional.of((String) authentication.getPrincipal());
        }
        
        if (authentication.getPrincipal() instanceof UserDetails) {
            return Optional.of(((UserDetails) authentication.getPrincipal()).getUsername());
        }
        
        if (authentication.getPrincipal() instanceof UserPrincipal) {
            return Optional.of(((UserPrincipal) authentication.getPrincipal()).getUsername());
        }
        
        logger.debug("Authentication principal is not a recognized type: {}", 
                authentication.getPrincipal().getClass().getName());
        return Optional.empty();
    }

    /**
     * Get the current user principal.
     *
     * @return the UserPrincipal object of the current user, or empty if not authenticated
     */
    public static Optional<UserPrincipal> getCurrentUserPrincipal() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        if (authentication == null) {
            logger.debug("No authentication found in SecurityContext");
            return Optional.empty();
        }
        
        if (authentication.getPrincipal() instanceof UserPrincipal) {
            return Optional.of((UserPrincipal) authentication.getPrincipal());
        }
        
        logger.debug("Authentication principal is not a UserPrincipal: {}", 
                authentication.getPrincipal().getClass().getName());
        return Optional.empty();
    }

    /**
     * Get the current user ID.
     *
     * @return the ID of the current user, or empty if not authenticated
     */
    public static Optional<Long> getCurrentUserId() {
        return getCurrentUserPrincipal().map(UserPrincipal::getId);
    }

    /**
     * Check if the current user has the specified authority.
     *
     * @param authority the authority to check
     * @return true if the current user has the authority, false otherwise
     */
    public static boolean hasAuthority(String authority) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        if (authentication == null || !authentication.isAuthenticated()) {
            logger.debug("No authenticated user found when checking authority: {}", authority);
            return false;
        }
        
        return authentication.getAuthorities().stream()
                .anyMatch(grantedAuthority -> grantedAuthority.getAuthority().equals(authority));
    }

    /**
     * Check if the current user has any of the specified authorities.
     *
     * @param authorities the authorities to check
     * @return true if the current user has any of the authorities, false otherwise
     */
    public static boolean hasAnyAuthority(String... authorities) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        if (authentication == null || !authentication.isAuthenticated()) {
            logger.debug("No authenticated user found when checking authorities");
            return false;
        }
        
        Set<String> userAuthorities = authentication.getAuthorities().stream()
                .map(grantedAuthority -> grantedAuthority.getAuthority())
                .collect(Collectors.toSet());
        
        for (String authority : authorities) {
            if (userAuthorities.contains(authority)) {
                return true;
            }
        }
        
        return false;
    }

    /**
     * Check if the current user has the Operations Staff role.
     *
     * @return true if the current user has the Operations Staff role, false otherwise
     */
    public static boolean isOperationsStaff() {
        return hasAuthority(ROLE_OPERATIONS_STAFF);
    }

    /**
     * Check if the current user has the System Admin role.
     *
     * @return true if the current user has the System Admin role, false otherwise
     */
    public static boolean isSystemAdmin() {
        return hasAuthority(ROLE_SYSTEM_ADMIN);
    }

    /**
     * Check if the current user is authenticated.
     *
     * @return true if the current user is authenticated, false otherwise
     */
    public static boolean isAuthenticated() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        return authentication != null && authentication.isAuthenticated() && 
                !(authentication.getPrincipal() instanceof String && "anonymousUser".equals(authentication.getPrincipal()));
    }

    /**
     * Generate a secure random string of the specified length.
     *
     * @param length the length of the random string
     * @return the generated random string
     */
    public static String generateSecureRandomString(int length) {
        byte[] randomBytes = new byte[length];
        secureRandom.nextBytes(randomBytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);
    }

    /**
     * Generate a secure random token for use in security-sensitive operations.
     *
     * @return a secure random token
     */
    public static String generateSecureToken() {
        return generateSecureRandomString(32);
    }

    /**
     * Generate a secure random password of the specified length.
     *
     * @param length the length of the password
     * @return the generated password
     */
    public static String generateSecurePassword(int length) {
        // Define character sets for password generation
        String upperChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        String lowerChars = "abcdefghijklmnopqrstuvwxyz";
        String numericChars = "0123456789";
        String specialChars = "!@#$%^&*()_-+=<>?";
        String allChars = upperChars + lowerChars + numericChars + specialChars;
        
        // Ensure minimum requirements
        StringBuilder password = new StringBuilder();
        password.append(upperChars.charAt(secureRandom.nextInt(upperChars.length())));
        password.append(lowerChars.charAt(secureRandom.nextInt(lowerChars.length())));
        password.append(numericChars.charAt(secureRandom.nextInt(numericChars.length())));
        password.append(specialChars.charAt(secureRandom.nextInt(specialChars.length())));
        
        // Fill the rest with random characters
        for (int i = 4; i < length; i++) {
            password.append(allChars.charAt(secureRandom.nextInt(allChars.length())));
        }
        
        // Shuffle the password
        char[] passwordArray = password.toString().toCharArray();
        for (int i = 0; i < passwordArray.length; i++) {
            int randomIndex = secureRandom.nextInt(passwordArray.length);
            char temp = passwordArray[i];
            passwordArray[i] = passwordArray[randomIndex];
            passwordArray[randomIndex] = temp;
        }
        
        return new String(passwordArray);
    }

    /**
     * Log a security audit event.
     *
     * @param action the security action being performed
     * @param details additional details about the action
     */
    public static void logSecurityAudit(String action, String details) {
        String userLogin = getCurrentUserLogin().orElse("anonymous");
        logger.info("SECURITY AUDIT: User '{}' performed action '{}' - {}", userLogin, action, details);
    }

    /**
     * Log a security violation event.
     *
     * @param violation the security violation that occurred
     * @param details additional details about the violation
     */
    public static void logSecurityViolation(String violation, String details) {
        String userLogin = getCurrentUserLogin().orElse("anonymous");
        logger.warn("SECURITY VIOLATION: User '{}' triggered violation '{}' - {}", userLogin, violation, details);
    }

    /**
     * Sanitize a potentially sensitive string for logging purposes.
     * This method replaces all characters with asterisks except for the first and last characters.
     *
     * @param sensitive the sensitive string to sanitize
     * @return the sanitized string, or "[null]" if the input is null
     */
    public static String sanitizeForLogging(String sensitive) {
        if (sensitive == null) {
            return "[null]";
        }
        
        if (sensitive.length() <= 2) {
            return "**";
        }
        
        char firstChar = sensitive.charAt(0);
        char lastChar = sensitive.charAt(sensitive.length() - 1);
        StringBuilder sanitized = new StringBuilder();
        sanitized.append(firstChar);
        
        for (int i = 1; i < sensitive.length() - 1; i++) {
            sanitized.append('*');
        }
        
        sanitized.append(lastChar);
        return sanitized.toString();
    }

    /**
     * Check if the current request is coming from an authenticated user with a valid session.
     * This is useful for protecting against session fixation attacks.
     *
     * @return true if the current session is valid, false otherwise
     */
    public static boolean isValidSession() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        if (authentication == null || !authentication.isAuthenticated()) {
            return false;
        }
        
        // Additional session validation logic can be added here
        return true;
    }

    /**
     * Validate that a given user has access to a specific application ID.
     * This is used for enforcing data access controls.
     *
     * @param applicationId the ID of the application to check access for
     * @return true if the current user has access to the application, false otherwise
     */
    public static boolean hasApplicationAccess(Long applicationId) {
        // System admins have access to all applications
        if (isSystemAdmin()) {
            return true;
        }
        
        // Operations staff have access to all applications
        if (isOperationsStaff()) {
            return true;
        }
        
        // Additional access control logic can be implemented here
        // For example, checking if the application belongs to the current user
        
        return false;
    }

    /**
     * Get the client IP address from the current request context.
     * This is useful for logging and security monitoring.
     *
     * @return the client IP address, or "unknown" if not available
     */
    public static String getClientIpAddress() {
        // In a real implementation, this would extract the IP from the request
        // Since we don't have direct access to the request here, this is a placeholder
        return "unknown";
    }
}