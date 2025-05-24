package com.dollarfunding.mca.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.servlet.http.HttpServletRequest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Optional;
import java.util.UUID;

/**
 * Utility class providing helper methods for security-related operations throughout the application.
 * <p>
 * This class centralizes common security operations to ensure consistent implementation across the application.
 * It includes methods for retrieving the current authenticated user, checking authorities, generating secure
 * random values, and handling security-related conversions.
 * </p>
 */
public final class SecurityUtils {

    private static final Logger logger = LoggerFactory.getLogger(SecurityUtils.class);
    
    private static final PasswordEncoder passwordEncoder = new BCryptPasswordEncoder(12);
    private static final SecureRandom secureRandom = new SecureRandom();
    
    /**
     * Private constructor to prevent instantiation.
     */
    private SecurityUtils() {
        // Private constructor to prevent instantiation
    }
    
    /**
     * Gets the current authentication from the security context.
     *
     * @return an Optional containing the current authentication, or empty if not authenticated
     */
    public static Optional<Authentication> getCurrentAuthentication() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated() || 
                authentication instanceof AnonymousAuthenticationToken) {
            return Optional.empty();
        }
        return Optional.of(authentication);
    }
    
    /**
     * Gets the current authenticated user principal from the security context.
     *
     * @return an Optional containing the current user principal, or empty if not authenticated
     */
    public static Optional<UserPrincipal> getCurrentUserPrincipal() {
        return getCurrentAuthentication()
                .map(Authentication::getPrincipal)
                .filter(principal -> principal instanceof UserPrincipal)
                .map(principal -> (UserPrincipal) principal);
    }
    
    /**
     * Gets the current authenticated user's ID from the security context.
     *
     * @return an Optional containing the current user's ID, or empty if not authenticated
     */
    public static Optional<Long> getCurrentUserId() {
        return getCurrentUserPrincipal().map(UserPrincipal::getId);
    }
    
    /**
     * Gets the current authenticated username from the security context.
     *
     * @return an Optional containing the current username, or empty if not authenticated
     */
    public static Optional<String> getCurrentUsername() {
        return getCurrentAuthentication()
                .map(authentication -> {
                    if (authentication.getPrincipal() instanceof UserDetails) {
                        return ((UserDetails) authentication.getPrincipal()).getUsername();
                    } else if (authentication.getPrincipal() instanceof String) {
                        return (String) authentication.getPrincipal();
                    }
                    return null;
                });
    }
    
    /**
     * Checks if the current user has the specified authority.
     *
     * @param authority the authority to check
     * @return true if the current user has the authority, false otherwise
     */
    public static boolean hasAuthority(String authority) {
        return getCurrentAuthentication()
                .map(authentication -> authentication.getAuthorities().stream()
                        .anyMatch(grantedAuthority -> grantedAuthority.getAuthority().equals(authority)))
                .orElse(false);
    }
    
    /**
     * Checks if the current user has the specified role.
     *
     * @param role the role to check (with or without ROLE_ prefix)
     * @return true if the current user has the role, false otherwise
     */
    public static boolean hasRole(String role) {
        String roleWithPrefix = RoleConstants.addRolePrefix(role);
        return hasAuthority(roleWithPrefix);
    }
    
    /**
     * Checks if the current user is an Operations Staff.
     *
     * @return true if the current user is an Operations Staff, false otherwise
     */
    public static boolean isOperationsStaff() {
        return hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF);
    }
    
    /**
     * Checks if the current user is a System Admin.
     *
     * @return true if the current user is a System Admin, false otherwise
     */
    public static boolean isSystemAdmin() {
        return hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN);
    }
    
    /**
     * Checks if the current user has access to the specified resource based on role.
     * <p>
     * System Admins have access to all resources.
     * Operations Staff have access to resources they are explicitly granted.
     * </p>
     *
     * @param requiredRole the role required to access the resource
     * @return true if the current user has access, false otherwise
     */
    public static boolean hasResourceAccess(String requiredRole) {
        // System Admins have access to everything
        if (isSystemAdmin()) {
            return true;
        }
        
        // Check if user has the specific required role
        return hasRole(requiredRole);
    }
    
    /**
     * Generates a secure random password with the specified length.
     *
     * @param length the length of the password to generate
     * @return the generated password
     */
    public static String generateSecurePassword(int length) {
        if (length < 8) {
            throw new IllegalArgumentException("Password length must be at least 8 characters");
        }
        
        // Define character sets for password generation
        String upperChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        String lowerChars = "abcdefghijklmnopqrstuvwxyz";
        String numberChars = "0123456789";
        String specialChars = "!@#$%^&*()_-+=<>?";
        String allChars = upperChars + lowerChars + numberChars + specialChars;
        
        StringBuilder password = new StringBuilder(length);
        
        // Ensure at least one character from each character set
        password.append(upperChars.charAt(secureRandom.nextInt(upperChars.length())));
        password.append(lowerChars.charAt(secureRandom.nextInt(lowerChars.length())));
        password.append(numberChars.charAt(secureRandom.nextInt(numberChars.length())));
        password.append(specialChars.charAt(secureRandom.nextInt(specialChars.length())));
        
        // Fill the rest of the password with random characters
        for (int i = 4; i < length; i++) {
            password.append(allChars.charAt(secureRandom.nextInt(allChars.length())));
        }
        
        // Shuffle the password to avoid predictable patterns
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
     * Encodes a password using BCrypt.
     *
     * @param rawPassword the raw password to encode
     * @return the encoded password
     */
    public static String encodePassword(String rawPassword) {
        return passwordEncoder.encode(rawPassword);
    }
    
    /**
     * Checks if a raw password matches an encoded password.
     *
     * @param rawPassword the raw password to check
     * @param encodedPassword the encoded password to check against
     * @return true if the passwords match, false otherwise
     */
    public static boolean matchesPassword(String rawPassword, String encodedPassword) {
        return passwordEncoder.matches(rawPassword, encodedPassword);
    }
    
    /**
     * Generates a secure random token with the specified byte length, encoded as Base64.
     *
     * @param byteLength the length of the token in bytes
     * @return the generated token encoded as Base64
     */
    public static String generateSecureToken(int byteLength) {
        byte[] tokenBytes = new byte[byteLength];
        secureRandom.nextBytes(tokenBytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(tokenBytes);
    }
    
    /**
     * Generates a secure random UUID.
     *
     * @return the generated UUID as a string
     */
    public static String generateSecureUuid() {
        return UUID.randomUUID().toString();
    }
    
    /**
     * Generates a secure AES key for encryption.
     *
     * @param keySize the key size in bits (128, 192, or 256)
     * @return the generated key encoded as Base64
     * @throws NoSuchAlgorithmException if the AES algorithm is not available
     */
    public static String generateAesKey(int keySize) throws NoSuchAlgorithmException {
        if (keySize != 128 && keySize != 192 && keySize != 256) {
            throw new IllegalArgumentException("Key size must be 128, 192, or 256 bits");
        }
        
        KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
        keyGenerator.init(keySize, secureRandom);
        SecretKey key = keyGenerator.generateKey();
        return Base64.getEncoder().encodeToString(key.getEncoded());
    }
    
    /**
     * Extracts the JWT token from the Authorization header.
     *
     * @param request the HTTP request
     * @return an Optional containing the JWT token, or empty if not found
     */
    public static Optional<String> extractJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return Optional.of(bearerToken.substring(7));
        }
        return Optional.empty();
    }
    
    /**
     * Gets the client IP address from the request.
     *
     * @param request the HTTP request
     * @return the client IP address
     */
    public static String getClientIpAddress(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            // X-Forwarded-For can contain multiple IP addresses in the format: client, proxy1, proxy2, ...
            // We want the client IP address, which is the first one in the list
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
    
    /**
     * Logs a security event with the specified message and user information.
     *
     * @param message the message to log
     * @param request the HTTP request (optional)
     */
    public static void logSecurityEvent(String message, HttpServletRequest request) {
        StringBuilder logMessage = new StringBuilder(message);
        
        // Add user information if available
        getCurrentUsername().ifPresent(username -> 
                logMessage.append(" | User: ").append(username));
        
        // Add request information if available
        if (request != null) {
            logMessage.append(" | IP: ").append(getClientIpAddress(request))
                    .append(" | Method: ").append(request.getMethod())
                    .append(" | URI: ").append(request.getRequestURI());
        }
        
        logger.info("SECURITY EVENT: {}", logMessage);
    }
    
    /**
     * Logs a security violation with the specified message and user information.
     *
     * @param message the message to log
     * @param request the HTTP request (optional)
     */
    public static void logSecurityViolation(String message, HttpServletRequest request) {
        StringBuilder logMessage = new StringBuilder(message);
        
        // Add user information if available
        getCurrentUsername().ifPresent(username -> 
                logMessage.append(" | User: ").append(username));
        
        // Add request information if available
        if (request != null) {
            logMessage.append(" | IP: ").append(getClientIpAddress(request))
                    .append(" | Method: ").append(request.getMethod())
                    .append(" | URI: ").append(request.getRequestURI());
        }
        
        logger.warn("SECURITY VIOLATION: {}", logMessage);
    }
    
    /**
     * Sanitizes a string for logging to prevent log injection attacks.
     *
     * @param input the string to sanitize
     * @return the sanitized string
     */
    public static String sanitizeForLogging(String input) {
        if (input == null) {
            return null;
        }
        // Replace line breaks and control characters that could be used for log injection
        return input.replaceAll("[\r\n\t\f\e\a\b]", " ");
    }
    
    /**
     * Masks sensitive data for logging purposes.
     *
     * @param data the sensitive data to mask
     * @return the masked data
     */
    public static String maskSensitiveData(String data) {
        if (data == null || data.isEmpty()) {
            return data;
        }
        
        int length = data.length();
        if (length <= 4) {
            return "****";
        }
        
        // Show first and last 2 characters, mask the rest
        return data.substring(0, 2) + "*".repeat(length - 4) + data.substring(length - 2);
    }
    
    /**
     * Checks if the current request is from an authenticated user.
     *
     * @return true if the current request is authenticated, false otherwise
     */
    public static boolean isAuthenticated() {
        return getCurrentAuthentication().isPresent();
    }
    
    /**
     * Gets the password encoder used for password hashing.
     *
     * @return the password encoder
     */
    public static PasswordEncoder getPasswordEncoder() {
        return passwordEncoder;
    }
    
    /**
     * Gets the secure random generator used for generating random values.
     *
     * @return the secure random generator
     */
    public static SecureRandom getSecureRandom() {
        return secureRandom;
    }
}