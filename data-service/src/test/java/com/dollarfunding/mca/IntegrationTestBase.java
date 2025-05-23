package com.dollarfunding.mca;

import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserPrincipal;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.transaction.annotation.Transactional;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
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
 * - Transaction management for test isolation
 * - Authentication utilities for testing with different user roles
 * - Test data cleanup to prevent test interference
 * <p>
 * Usage:
 * Extend this class in your integration test classes and override the setup and cleanup methods
 * as needed for specific test requirements.
 */
@ExtendWith(SpringExtension.class)
@SpringBootTest
@ActiveProfiles("test")
@Transactional
public abstract class IntegrationTestBase {

    @Autowired
    private DataSource dataSource;

    @Autowired(required = false)
    private JwtTokenProvider jwtTokenProvider;

    /**
     * Setup method that runs before each test.
     * <p>
     * This method initializes the test environment, including database setup and security context.
     * Override this method in subclasses to add additional setup logic, but always call super.setUp().
     */
    @BeforeEach
    public void setUp() throws Exception {
        // Clear security context before each test
        SecurityContextHolder.clearContext();
        
        // Initialize database if needed
        initializeDatabase();
    }

    /**
     * Cleanup method that runs after each test.
     * <p>
     * This method cleans up the test environment, including security context and any test data.
     * Override this method in subclasses to add additional cleanup logic, but always call super.tearDown().
     */
    @AfterEach
    public void tearDown() {
        // Clear security context after each test
        SecurityContextHolder.clearContext();
        
        // Clean up any test data
        cleanupTestData();
    }

    /**
     * Initializes the database for testing.
     * <p>
     * This method can be overridden in subclasses to perform specific database initialization.
     */
    protected void initializeDatabase() throws SQLException {
        // Default implementation does nothing
        // Subclasses can override to initialize specific test data
    }

    /**
     * Cleans up test data after each test.
     * <p>
     * This method can be overridden in subclasses to perform specific test data cleanup.
     */
    protected void cleanupTestData() {
        // Default implementation does nothing
        // Subclasses can override to clean up specific test data
    }

    /**
     * Sets up authentication context for an Operations Staff user.
     * <p>
     * This method creates a UserPrincipal with Operations Staff role and sets it in the SecurityContext.
     * Use this method to test endpoints that require Operations Staff permissions.
     *
     * @param userId The user ID to use for authentication (defaults to "test-ops-user" if null)
     * @return The Authentication object that was set in the SecurityContext
     */
    protected Authentication authenticateAsOperationsStaff(String userId) {
        String id = userId != null ? userId : "test-ops-user";
        return authenticateWithRoles(id, Collections.singletonList(RoleConstants.ROLE_OPERATIONS_STAFF));
    }

    /**
     * Sets up authentication context for a System Admin user.
     * <p>
     * This method creates a UserPrincipal with System Admin role and sets it in the SecurityContext.
     * Use this method to test endpoints that require System Admin permissions.
     *
     * @param userId The user ID to use for authentication (defaults to "test-admin-user" if null)
     * @return The Authentication object that was set in the SecurityContext
     */
    protected Authentication authenticateAsSystemAdmin(String userId) {
        String id = userId != null ? userId : "test-admin-user";
        return authenticateWithRoles(id, Collections.singletonList(RoleConstants.ROLE_SYSTEM_ADMIN));
    }

    /**
     * Sets up authentication context with custom roles.
     * <p>
     * This method creates a UserPrincipal with the specified roles and sets it in the SecurityContext.
     * Use this method to test endpoints with custom role combinations.
     *
     * @param userId The user ID to use for authentication
     * @param roles  The list of roles to assign to the user
     * @return The Authentication object that was set in the SecurityContext
     */
    protected Authentication authenticateWithRoles(String userId, List<String> roles) {
        UserPrincipal principal = createUserPrincipal(userId, roles);
        Authentication authentication = new UsernamePasswordAuthenticationToken(
                principal, null, principal.getAuthorities());
        SecurityContextHolder.getContext().setAuthentication(authentication);
        return authentication;
    }

    /**
     * Creates a UserPrincipal with the specified user ID and roles.
     * <p>
     * This method creates a UserPrincipal object that can be used for authentication in tests.
     * It converts role strings to SimpleGrantedAuthority objects as required by Spring Security.
     *
     * @param userId The user ID to use for the principal
     * @param roles  The list of roles to assign to the user
     * @return A UserPrincipal object with the specified user ID and roles
     */
    private UserPrincipal createUserPrincipal(String userId, List<String> roles) {
        List<SimpleGrantedAuthority> authorities = roles.stream()
                .map(role -> new SimpleGrantedAuthority(role))
                .toList();

        return UserPrincipal.builder()
                .id(userId)
                .username("test-user-" + userId)
                .email("test-" + userId + "@example.com")
                .authorities(authorities)
                .build();
    }

    /**
     * Gets a database connection for direct database operations.
     * <p>
     * This method provides a connection to the test database for operations that need to bypass
     * the ORM layer. The connection is automatically closed after the test.
     *
     * @return A Connection object for database operations
     * @throws SQLException If a database access error occurs
     */
    protected Connection getConnection() throws SQLException {
        return dataSource.getConnection();
    }

    /**
     * Generates a JWT token for the current authenticated user.
     * <p>
     * This method creates a JWT token that can be used for testing API endpoints that require
     * JWT authentication. It uses the JwtTokenProvider to generate the token.
     *
     * @return A JWT token string for the current authenticated user
     * @throws IllegalStateException If no user is authenticated or JwtTokenProvider is not available
     */
    protected String generateJwtToken() {
        if (jwtTokenProvider == null) {
            throw new IllegalStateException("JwtTokenProvider is not available in the test context");
        }

        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null) {
            throw new IllegalStateException("No authentication found in SecurityContext");
        }

        return jwtTokenProvider.generateToken(authentication);
    }
}