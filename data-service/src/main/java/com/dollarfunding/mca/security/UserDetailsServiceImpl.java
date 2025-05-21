package com.dollarfunding.mca.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Implementation of Spring Security's UserDetailsService interface that loads user details
 * from the database for authentication and authorization.
 * 
 * This class is critical for the authentication process as it retrieves user credentials
 * and authorities from the database and converts them to UserPrincipal objects that
 * Spring Security can use for authentication and authorization.
 * 
 * It integrates with the Minimal UI Kit's JWT authentication system and supports
 * the two specific roles defined in the requirements: Operations Staff and System Admin.
 */
@Service
@CacheConfig(cacheNames = "userDetails")
public class UserDetailsServiceImpl implements UserDetailsService {

    private static final Logger logger = LoggerFactory.getLogger(UserDetailsServiceImpl.class);

    private final UserRepository userRepository;

    /**
     * Constructor with required dependencies.
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
     * This method is called by Spring Security during the authentication process.
     * 
     * The result is cached to improve performance for subsequent authentication requests
     * with the same username.
     *
     * @param username the username to load
     * @return a UserDetails object containing the user's credentials and authorities
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(key = "#username", unless = "#result == null")
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        logger.debug("Loading user by username: {}", username);
        
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> {
                    logger.warn("User not found with username: {}", username);
                    return new UsernameNotFoundException("User not found with username: " + username);
                });
        
        logger.debug("User found: {}", user.getUsername());
        
        // Update last login timestamp
        user.updateLastLogin();
        
        return UserPrincipal.create(user);
    }

    /**
     * Loads a user by ID from the database and converts it to a UserPrincipal object.
     * 
     * This method can be used when the user ID is available but not the username.
     * 
     * The result is cached to improve performance for subsequent requests with the same ID.
     *
     * @param id the user ID to load
     * @return a UserDetails object containing the user's credentials and authorities
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Transactional(readOnly = true)
    @Cacheable(key = "'id_' + #id", unless = "#result == null")
    public UserDetails loadUserById(Long id) throws UsernameNotFoundException {
        logger.debug("Loading user by ID: {}", id);
        
        User user = userRepository.findById(id)
                .orElseThrow(() -> {
                    logger.warn("User not found with ID: {}", id);
                    return new UsernameNotFoundException("User not found with ID: " + id);
                });
        
        logger.debug("User found: {}", user.getUsername());
        
        return UserPrincipal.create(user);
    }

    /**
     * Loads a user by email from the database and converts it to a UserPrincipal object.
     * 
     * This method can be used when the email is available but not the username.
     * 
     * The result is cached to improve performance for subsequent requests with the same email.
     *
     * @param email the email to load
     * @return a UserDetails object containing the user's credentials and authorities
     * @throws UsernameNotFoundException if the user is not found in the database
     */
    @Transactional(readOnly = true)
    @Cacheable(key = "'email_' + #email", unless = "#result == null")
    public UserDetails loadUserByEmail(String email) throws UsernameNotFoundException {
        logger.debug("Loading user by email: {}", email);
        
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> {
                    logger.warn("User not found with email: {}", email);
                    return new UsernameNotFoundException("User not found with email: " + email);
                });
        
        logger.debug("User found: {}", user.getUsername());
        
        return UserPrincipal.create(user);
    }
}