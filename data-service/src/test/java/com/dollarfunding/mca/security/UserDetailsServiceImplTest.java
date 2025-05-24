package com.dollarfunding.mca.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cache.CacheManager;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UsernameNotFoundException;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Optional;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * Test class for {@link UserDetailsServiceImpl} that verifies the correct loading of user details
 * from the database for authentication and authorization.
 * 
 * <p>This test ensures that the service correctly retrieves user credentials and authorities
 * from the database for the authentication process.</p>
 */
@ExtendWith(MockitoExtension.class)
public class UserDetailsServiceImplTest {

    @Mock
    private UserRepository userRepository;
    
    @Mock
    private CacheManager cacheManager;
    
    @InjectMocks
    private UserDetailsServiceImpl userDetailsService;
    
    private User testUser;
    private Role operationsStaffRole;
    private Role systemAdminRole;
    
    @BeforeEach
    public void setUp() {
        // Create test roles
        operationsStaffRole = new Role(RoleConstants.ROLE_OPERATIONS_STAFF, "Operations Staff Role");
        systemAdminRole = new Role(RoleConstants.ROLE_SYSTEM_ADMIN, "System Admin Role");
        
        // Create test user
        testUser = new User("testuser", "password123", "test@example.com", "Test", "User");
        testUser.setId(1L);
        testUser.setEnabled(true);
        testUser.setAccountNonExpired(true);
        testUser.setCredentialsNonExpired(true);
        testUser.setAccountNonLocked(true);
        testUser.setCreatedAt(LocalDateTime.now());
        
        // Add roles to user
        Set<Role> roles = new HashSet<>();
        roles.add(operationsStaffRole);
        testUser.setRoles(roles);
    }
    
    @Test
    @DisplayName("Should load user by username successfully")
    public void testLoadUserByUsername_Success() {
        // Arrange
        when(userRepository.findByUsernameOrEmail(anyString(), anyString()))
                .thenReturn(Optional.of(testUser));
        
        // Act
        UserDetails userDetails = userDetailsService.loadUserByUsername("testuser");
        
        // Assert
        assertNotNull(userDetails);
        assertEquals("testuser", userDetails.getUsername());
        assertEquals("password123", userDetails.getPassword());
        assertTrue(userDetails.isEnabled());
        assertTrue(userDetails.isAccountNonExpired());
        assertTrue(userDetails.isCredentialsNonExpired());
        assertTrue(userDetails.isAccountNonLocked());
        
        // Verify authorities
        boolean hasOperationsStaffRole = userDetails.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(authority -> authority.equals(RoleConstants.ROLE_OPERATIONS_STAFF));
        assertTrue(hasOperationsStaffRole);
        
        // Verify repository was called
        verify(userRepository).findByUsernameOrEmail("testuser", "testuser");
        
        // Verify last login was updated
        verify(userRepository).save(any(User.class));
    }
    
    @Test
    @DisplayName("Should load user by email successfully")
    public void testLoadUserByEmail_Success() {
        // Arrange
        when(userRepository.findByUsernameOrEmail(anyString(), anyString()))
                .thenReturn(Optional.of(testUser));
        
        // Act
        UserDetails userDetails = userDetailsService.loadUserByUsername("test@example.com");
        
        // Assert
        assertNotNull(userDetails);
        assertEquals("testuser", userDetails.getUsername());
        
        // Verify repository was called with email
        verify(userRepository).findByUsernameOrEmail("test@example.com", "test@example.com");
    }
    
    @Test
    @DisplayName("Should throw UsernameNotFoundException when user not found")
    public void testLoadUserByUsername_UserNotFound() {
        // Arrange
        when(userRepository.findByUsernameOrEmail(anyString(), anyString()))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        Exception exception = assertThrows(UsernameNotFoundException.class, () -> {
            userDetailsService.loadUserByUsername("nonexistent");
        });
        
        // Verify exception message
        assertTrue(exception.getMessage().contains("nonexistent"));
        
        // Verify repository was called
        verify(userRepository).findByUsernameOrEmail("nonexistent", "nonexistent");
        
        // Verify save was not called
        verify(userRepository, never()).save(any(User.class));
    }
    
    @Test
    @DisplayName("Should load user by ID successfully")
    public void testLoadUserById_Success() {
        // Arrange
        when(userRepository.findById(1L)).thenReturn(Optional.of(testUser));
        
        // Act
        UserDetails userDetails = userDetailsService.loadUserById(1L);
        
        // Assert
        assertNotNull(userDetails);
        assertEquals("testuser", userDetails.getUsername());
        
        // Verify repository was called
        verify(userRepository).findById(1L);
    }
    
    @Test
    @DisplayName("Should throw UsernameNotFoundException when user ID not found")
    public void testLoadUserById_UserNotFound() {
        // Arrange
        when(userRepository.findById(999L)).thenReturn(Optional.empty());
        
        // Act & Assert
        Exception exception = assertThrows(UsernameNotFoundException.class, () -> {
            userDetailsService.loadUserById(999L);
        });
        
        // Verify exception message
        assertTrue(exception.getMessage().contains("999"));
        
        // Verify repository was called
        verify(userRepository).findById(999L);
    }
    
    @Test
    @DisplayName("Should map user authorities correctly")
    public void testUserAuthoritiesMapping() {
        // Arrange - Add System Admin role to test user
        testUser.addRole(systemAdminRole);
        when(userRepository.findByUsernameOrEmail(anyString(), anyString()))
                .thenReturn(Optional.of(testUser));
        
        // Act
        UserDetails userDetails = userDetailsService.loadUserByUsername("testuser");
        
        // Assert - User should have both roles
        assertEquals(2, userDetails.getAuthorities().size());
        
        boolean hasOperationsStaffRole = userDetails.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(authority -> authority.equals(RoleConstants.ROLE_OPERATIONS_STAFF));
        
        boolean hasSystemAdminRole = userDetails.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(authority -> authority.equals(RoleConstants.ROLE_SYSTEM_ADMIN));
        
        assertTrue(hasOperationsStaffRole);
        assertTrue(hasSystemAdminRole);
    }
    
    @Test
    @DisplayName("Should update last login timestamp")
    public void testUpdateLastLogin() {
        // Arrange
        LocalDateTime beforeUpdate = testUser.getLastLoginAt();
        
        // Act
        userDetailsService.updateLastLogin(testUser);
        
        // Assert
        assertNotNull(testUser.getLastLoginAt());
        if (beforeUpdate != null) {
            assertTrue(testUser.getLastLoginAt().isAfter(beforeUpdate) || 
                    testUser.getLastLoginAt().isEqual(beforeUpdate));
        }
        
        // Verify repository was called
        verify(userRepository).save(testUser);
    }
    
    @Test
    @DisplayName("Should handle exception during last login update")
    public void testUpdateLastLogin_Exception() {
        // Arrange
        doThrow(new RuntimeException("Database error")).when(userRepository).save(any(User.class));
        
        // Act - Should not throw exception
        assertDoesNotThrow(() -> userDetailsService.updateLastLogin(testUser));
        
        // Verify repository was called
        verify(userRepository).save(testUser);
    }
    
    @Test
    @DisplayName("Should check if user exists by username or email")
    public void testExistsByUsernameOrEmail() {
        // Arrange
        when(userRepository.existsByUsername("testuser")).thenReturn(true);
        when(userRepository.existsByEmail("test@example.com")).thenReturn(true);
        when(userRepository.existsByUsername("nonexistent")).thenReturn(false);
        when(userRepository.existsByEmail("nonexistent")).thenReturn(false);
        
        // Act & Assert
        assertTrue(userDetailsService.existsByUsernameOrEmail("testuser"));
        assertTrue(userDetailsService.existsByUsernameOrEmail("test@example.com"));
        assertFalse(userDetailsService.existsByUsernameOrEmail("nonexistent"));
        
        // Verify repository was called
        verify(userRepository).existsByUsername("testuser");
        verify(userRepository).existsByEmail("test@example.com");
        verify(userRepository).existsByUsername("nonexistent");
        verify(userRepository).existsByEmail("nonexistent");
    }
    
    @Test
    @DisplayName("Should check if user has specific role")
    public void testHasRole() {
        // Arrange
        when(userRepository.findByUsernameOrEmail("testuser", "testuser"))
                .thenReturn(Optional.of(testUser));
        
        // Act & Assert
        assertTrue(userDetailsService.hasRole("testuser", RoleConstants.OPERATIONS_STAFF));
        assertFalse(userDetailsService.hasRole("testuser", RoleConstants.SYSTEM_ADMIN));
        
        // Verify repository was called
        verify(userRepository, times(2)).findByUsernameOrEmail("testuser", "testuser");
    }
    
    @Test
    @DisplayName("Should check if user is Operations Staff")
    public void testIsOperationsStaff() {
        // Arrange
        when(userRepository.findByUsernameOrEmail("testuser", "testuser"))
                .thenReturn(Optional.of(testUser));
        
        // Act & Assert
        assertTrue(userDetailsService.isOperationsStaff("testuser"));
        
        // Verify repository was called
        verify(userRepository).findByUsernameOrEmail("testuser", "testuser");
    }
    
    @Test
    @DisplayName("Should check if user is System Admin")
    public void testIsSystemAdmin() {
        // Arrange
        when(userRepository.findByUsernameOrEmail("testuser", "testuser"))
                .thenReturn(Optional.of(testUser));
        
        // Act & Assert
        assertFalse(userDetailsService.isSystemAdmin("testuser"));
        
        // Add System Admin role and test again
        testUser.addRole(systemAdminRole);
        assertTrue(userDetailsService.isSystemAdmin("testuser"));
        
        // Verify repository was called twice
        verify(userRepository, times(2)).findByUsernameOrEmail("testuser", "testuser");
    }
    
    @Test
    @DisplayName("Should cache user details when loading by username")
    public void testCacheUserDetailsByUsername() {
        // This test verifies that caching works as expected
        // We need to use a spy to verify the actual repository calls
        UserDetailsServiceImpl serviceSpy = spy(userDetailsService);
        
        // Arrange
        when(userRepository.findByUsernameOrEmail("testuser", "testuser"))
                .thenReturn(Optional.of(testUser));
        
        // Act - Call twice
        UserDetails firstCall = serviceSpy.loadUserByUsername("testuser");
        UserDetails secondCall = serviceSpy.loadUserByUsername("testuser");
        
        // Assert
        assertNotNull(firstCall);
        assertNotNull(secondCall);
        assertEquals(firstCall.getUsername(), secondCall.getUsername());
        
        // Verify repository was called only once (due to caching)
        verify(userRepository, times(1)).findByUsernameOrEmail("testuser", "testuser");
    }
    
    @Test
    @DisplayName("Should cache user details when loading by ID")
    public void testCacheUserDetailsById() {
        // This test verifies that caching works as expected
        // We need to use a spy to verify the actual repository calls
        UserDetailsServiceImpl serviceSpy = spy(userDetailsService);
        
        // Arrange
        when(userRepository.findById(1L)).thenReturn(Optional.of(testUser));
        
        // Act - Call twice
        UserDetails firstCall = serviceSpy.loadUserById(1L);
        UserDetails secondCall = serviceSpy.loadUserById(1L);
        
        // Assert
        assertNotNull(firstCall);
        assertNotNull(secondCall);
        assertEquals(firstCall.getUsername(), secondCall.getUsername());
        
        // Verify repository was called only once (due to caching)
        verify(userRepository, times(1)).findById(1L);
    }
    
    @Test
    @DisplayName("Should integrate with Spring Security authentication manager")
    public void testIntegrationWithSpringSecurityAuthenticationManager() {
        // Arrange
        when(userRepository.findByUsernameOrEmail("testuser", "testuser"))
                .thenReturn(Optional.of(testUser));
        
        // Act
        UserDetails userDetails = userDetailsService.loadUserByUsername("testuser");
        
        // Assert - Verify UserDetails implementation is compatible with Spring Security
        assertTrue(userDetails instanceof UserPrincipal);
        UserPrincipal principal = (UserPrincipal) userDetails;
        
        // Check core UserDetails contract
        assertEquals("testuser", principal.getUsername());
        assertEquals("password123", principal.getPassword());
        assertTrue(principal.isEnabled());
        assertTrue(principal.isAccountNonExpired());
        assertTrue(principal.isCredentialsNonExpired());
        assertTrue(principal.isAccountNonLocked());
        
        // Check authorities
        assertTrue(principal.getAuthorities().contains(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)));
        
        // Check additional UserPrincipal methods
        assertEquals(1L, principal.getId());
        assertEquals("test@example.com", principal.getEmail());
        assertEquals("Test", principal.getFirstName());
        assertEquals("User", principal.getLastName());
        assertEquals("Test User", principal.getFullName());
        
        // Check role-specific methods
        assertTrue(principal.hasRole(RoleConstants.OPERATIONS_STAFF));
        assertFalse(principal.hasRole(RoleConstants.SYSTEM_ADMIN));
        assertTrue(principal.isOperationsStaff());
        assertFalse(principal.isSystemAdmin());
    }
}