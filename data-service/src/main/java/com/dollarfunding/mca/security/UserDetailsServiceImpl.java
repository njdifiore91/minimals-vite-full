package com.dollarfunding.mca.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Implementation of Spring Security's UserDetailsService that loads user details from the database
 * for authentication and authorization. This service is critical for the authentication process as it
 * retrieves user credentials and authorities from the database and converts them to UserPrincipal objects
 * that Spring Security can use.
 * 
 * <p>This implementation integrates with the Minimal UI Kit's JWT authentication system and supports
 * the two specific roles required by the MCA Application Processing System: Operations Staff and System Admin.</p>
 */
@Service
public class UserDetailsServiceImpl implements UserDetailsService {

    private static final Logger logger = LoggerFactory.getLogger(UserDetailsServiceImpl.class);

    private final UserRepository userRepository;

    /**
     * Constructor-based dependency injection for UserRepository.
     * 
     * @param userRepository the repository for accessing user data
     */
    @Autowired
    public UserDetailsServiceImpl(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * Loads a user by username from the database and converts it to a UserPrincipal object
     * that Spring Security can use for authentication and authorization.
     * 
     * <p>This method is called by Spring Security during the authentication process.</p>
     * 
     * @param usernameOrEmail the username or email of the user to load
     * @return a UserDetails object containing the user's credentials and authorities
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(value = "userDetails", key = "#usernameOrEmail", unless = "#result == null")
    public UserDetails loadUserByUsername(String usernameOrEmail) throws UsernameNotFoundException {
        logger.debug("Loading user by username or email: {}", usernameOrEmail);
        
        // Try to find the user by username or email
        User user = userRepository.findByUsernameOrEmail(usernameOrEmail, usernameOrEmail)
                .orElseThrow(() -> {
                    logger.error("User not found with username or email: {}", usernameOrEmail);
                    return new UsernameNotFoundException("User not found with username or email: " + usernameOrEmail);
                });
        
        logger.debug("User found: {}", user.getUsername());
        
        // Update last login timestamp
        updateLastLogin(user);
        
        // Convert User entity to UserPrincipal
        return UserPrincipal.create(user);
    }
    
    /**
     * Updates the last login timestamp for a user.
     * This method is called after successful authentication.
     * 
     * @param user the user to update
     */
    @Transactional
    public void updateLastLogin(User user) {
        try {
            user.setLastLoginAt(java.time.LocalDateTime.now());
            userRepository.save(user);
            logger.debug("Updated last login timestamp for user: {}", user.getUsername());
        } catch (Exception e) {
            // Log the error but don't fail the authentication process
            logger.warn("Failed to update last login timestamp for user: {}", user.getUsername(), e);
        }
    }
    
    /**
     * Loads a user by ID from the database and converts it to a UserPrincipal object.
     * This method is useful for token-based authentication where the user ID is extracted from the token.
     * 
     * @param id the ID of the user to load
     * @return a UserDetails object containing the user's credentials and authorities
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Transactional(readOnly = true)
    @Cacheable(value = "userDetailsById", key = "#id", unless = "#result == null")
    public UserDetails loadUserById(Long id) throws UsernameNotFoundException {
        logger.debug("Loading user by ID: {}", id);
        
        User user = userRepository.findById(id)
                .orElseThrow(() -> {
                    logger.error("User not found with ID: {}", id);
                    return new UsernameNotFoundException("User not found with ID: " + id);
                });
        
        logger.debug("User found by ID: {}", user.getUsername());
        
        return UserPrincipal.create(user);
    }
    
    /**
     * Checks if a user exists with the given username or email.
     * This method is useful for registration and password reset functionality.
     * 
     * @param usernameOrEmail the username or email to check
     * @return true if a user exists with the given username or email, false otherwise
     */
    @Transactional(readOnly = true)
    public boolean existsByUsernameOrEmail(String usernameOrEmail) {
        return userRepository.existsByUsername(usernameOrEmail) || 
               userRepository.existsByEmail(usernameOrEmail);
    }
    
    /**
     * Checks if a user with the given username or email has the specified role.
     * This method is useful for role-based authorization checks.
     * 
     * @param usernameOrEmail the username or email of the user to check
     * @param roleName the role name to check (without ROLE_ prefix)
     * @return true if the user has the specified role, false otherwise
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Transactional(readOnly = true)
    public boolean hasRole(String usernameOrEmail, String roleName) throws UsernameNotFoundException {
        User user = userRepository.findByUsernameOrEmail(usernameOrEmail, usernameOrEmail)
                .orElseThrow(() -> new UsernameNotFoundException("User not found with username or email: " + usernameOrEmail));
        
        return user.hasRole(roleName);
    }
    
    /**
     * Checks if a user with the given username or email is an Operations Staff.
     * 
     * @param usernameOrEmail the username or email of the user to check
     * @return true if the user is an Operations Staff, false otherwise
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Transactional(readOnly = true)
    public boolean isOperationsStaff(String usernameOrEmail) throws UsernameNotFoundException {
        return hasRole(usernameOrEmail, RoleConstants.OPERATIONS_STAFF);
    }
    
    /**
     * Checks if a user with the given username or email is a System Admin.
     * 
     * @param usernameOrEmail the username or email of the user to check
     * @return true if the user is a System Admin, false otherwise
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Transactional(readOnly = true)
    public boolean isSystemAdmin(String usernameOrEmail) throws UsernameNotFoundException {
        return hasRole(usernameOrEmail, RoleConstants.SYSTEM_ADMIN);
    }
}