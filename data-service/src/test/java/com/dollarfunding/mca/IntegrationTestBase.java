package com.dollarfunding.mca;

import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserPrincipal;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.List;

/**
 * Abstract base class for integration tests that require a running Spring application context.
 * <p>
 * This class provides common setup for integration testing, including database initialization,
 * cache configuration, and security context setup. It uses @SpringBootTest to load the application
 * context with a realistic configuration while isolating external dependencies through mocks.
 * <p>
 * Features:
 * - Configures test profile to use application-test.yml settings
 * - Sets up transaction management for test isolation
 * - Provides authentication utilities for testing with different user roles
 * - Includes utilities for test data cleanup
 * <p>
 * Usage:
 * Extend this class in your integration test classes and override the setup/teardown methods
 * as needed for specific test requirements.
 */
@SpringBootTest
@ActiveProfiles("test")
@Transactional
public abstract class IntegrationTestBase {

    @Autowired
    protected EntityManager entityManager;

    @Autowired
    protected ObjectMapper objectMapper;

    @Autowired(required = false)
    protected JwtTokenProvider jwtTokenProvider;

    /**
     * Setup method that runs before each test.
     * Clears the security context to ensure tests start with a clean authentication state.
     */
    @BeforeEach
    public void setUp() {
        SecurityContextHolder.clearContext();
    }

    /**
     * Teardown method that runs after each test.
     * Clears the security context and performs any necessary cleanup.
     */
    @AfterEach
    public void tearDown() {
        SecurityContextHolder.clearContext();
        // Additional cleanup can be added here
    }

    /**
     * Flushes and clears the persistence context to ensure all pending changes are synchronized
     * with the database and the entity manager is in a clean state.
     */
    protected void flushAndClear() {
        entityManager.flush();
        entityManager.clear();
    }

    /**
     * Sets up authentication context for an Operations Staff user.
     * This role has read access to all data and write access to application data.
     *
     * @return The authentication object that was set in the security context
     */
    protected Authentication authenticateAsOperationsStaff() {
        return authenticateWithRole(RoleConstants.ROLE_OPERATIONS_STAFF);
    }

    /**
     * Sets up authentication context for a System Admin user.
     * This role has full access to all endpoints and webhook configuration.
     *
     * @return The authentication object that was set in the security context
     */
    protected Authentication authenticateAsSystemAdmin() {
        return authenticateWithRole(RoleConstants.ROLE_SYSTEM_ADMIN);
    }

    /**
     * Sets up authentication context with a specific role.
     *
     * @param role The role to authenticate with
     * @return The authentication object that was set in the security context
     */
    protected Authentication authenticateWithRole(String role) {
        UserPrincipal principal = createUserPrincipal(role);
        Authentication authentication = new UsernamePasswordAuthenticationToken(
                principal,
                null,
                principal.getAuthorities()
        );
        SecurityContextHolder.getContext().setAuthentication(authentication);
        return authentication;
    }

    /**
     * Creates a UserPrincipal with the specified role for testing purposes.
     *
     * @param role The role to assign to the user principal
     * @return A UserPrincipal object with the specified role
     */
    protected UserPrincipal createUserPrincipal(String role) {
        return UserPrincipal.builder()
                .id(1L)
                .username("test-user")
                .email("test@dollarfunding.com")
                .authorities(Collections.singletonList(new SimpleGrantedAuthority(role)))
                .build();
    }

    /**
     * Creates a JWT token for testing purposes with the Operations Staff role.
     *
     * @return A JWT token string
     */
    protected String createOperationsStaffToken() {
        if (jwtTokenProvider == null) {
            throw new IllegalStateException("JwtTokenProvider is not available in the test context");
        }
        return jwtTokenProvider.generateToken(createUserPrincipal(RoleConstants.ROLE_OPERATIONS_STAFF));
    }

    /**
     * Creates a JWT token for testing purposes with the System Admin role.
     *
     * @return A JWT token string
     */
    protected String createSystemAdminToken() {
        if (jwtTokenProvider == null) {
            throw new IllegalStateException("JwtTokenProvider is not available in the test context");
        }
        return jwtTokenProvider.generateToken(createUserPrincipal(RoleConstants.ROLE_SYSTEM_ADMIN));
    }

    /**
     * Creates a JWT token for testing purposes with the specified roles.
     *
     * @param roles The roles to include in the token
     * @return A JWT token string
     */
    protected String createTokenWithRoles(List<String> roles) {
        if (jwtTokenProvider == null) {
            throw new IllegalStateException("JwtTokenProvider is not available in the test context");
        }
        UserPrincipal principal = UserPrincipal.builder()
                .id(1L)
                .username("test-user")
                .email("test@dollarfunding.com")
                .authorities(roles.stream()
                        .map(SimpleGrantedAuthority::new)
                        .toList())
                .build();
        return jwtTokenProvider.generateToken(principal);
    }

    /**
     * Creates an expired JWT token for testing error scenarios.
     *
     * @return An expired JWT token string
     */
    protected String createExpiredToken() {
        if (jwtTokenProvider == null) {
            throw new IllegalStateException("JwtTokenProvider is not available in the test context");
        }
        return jwtTokenProvider.generateTokenWithCustomExpiration(
                createUserPrincipal(RoleConstants.ROLE_OPERATIONS_STAFF),
                -3600 // Expired 1 hour ago
        );
    }
}