package com.dollarfunding.mca.security;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.time.LocalDateTime;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UsernameNotFoundException;

/**
 * Test class for {@link UserDetailsServiceImpl} that verifies the correct loading of user details
 * from the database for authentication and authorization.
 * 
 * These tests ensure that the service correctly retrieves user credentials and authorities
 * from the database for the authentication process, handles exceptions appropriately, and
 * properly maps user authorities.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("UserDetailsServiceImpl Tests")
public class UserDetailsServiceImplTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserDetailsServiceImpl userDetailsService;

    @Captor
    private ArgumentCaptor<User> userCaptor;

    private User operationsStaffUser;
    private User systemAdminUser;
    private User regularUser;

    @BeforeEach
    void setUp() {
        // Create roles
        Role operationsStaffRole = Role.createOperationsStaffRole();
        Role systemAdminRole = Role.createSystemAdminRole();
        
        // Create operations staff user
        operationsStaffUser = new User("ops_user", "password123", "ops@dollarfunding.com", 
                                    "Operations", "User", true, true, true, true);
        operationsStaffUser.setId(1L);
        operationsStaffUser.addRole(operationsStaffRole);
        
        // Create system admin user
        systemAdminUser = new User("admin_user", "password456", "admin@dollarfunding.com", 
                                 "Admin", "User", true, true, true, true);
        systemAdminUser.setId(2L);
        systemAdminUser.addRole(systemAdminRole);
        
        // Create regular user with no roles
        regularUser = new User("regular_user", "password789", "user@dollarfunding.com", 
                             "Regular", "User", true, true, true, true);
        regularUser.setId(3L);
    }

    @Nested
    @DisplayName("Loading User By Username Tests")
    class LoadingUserByUsernameTests {
        
        @Test
        @DisplayName("loadUserByUsername() should return UserDetails when user exists")
        void loadUserByUsernameShouldReturnUserDetailsWhenUserExists() {
            // Arrange
            when(userRepository.findByUsername("ops_user")).thenReturn(Optional.of(operationsStaffUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserByUsername("ops_user");
            
            // Assert
            assertNotNull(userDetails);
            assertEquals("ops_user", userDetails.getUsername());
            assertEquals("password123", userDetails.getPassword());
            assertTrue(userDetails.isEnabled());
            assertTrue(userDetails.getAuthorities().stream()
                    .anyMatch(a -> a.getAuthority().equals(RoleConstants.ROLE_OPERATIONS_STAFF)));
            
            // Verify that the user's last login timestamp was updated
            verify(userRepository).findByUsername("ops_user");
        }
        
        @Test
        @DisplayName("loadUserByUsername() should throw UsernameNotFoundException when user does not exist")
        void loadUserByUsernameShouldThrowUsernameNotFoundExceptionWhenUserDoesNotExist() {
            // Arrange
            when(userRepository.findByUsername("non_existent_user")).thenReturn(Optional.empty());
            
            // Act & Assert
            Exception exception = assertThrows(UsernameNotFoundException.class, () -> {
                userDetailsService.loadUserByUsername("non_existent_user");
            });
            
            // Verify the exception message
            assertEquals("User not found with username: non_existent_user", exception.getMessage());
            verify(userRepository).findByUsername("non_existent_user");
        }
        
        @Test
        @DisplayName("loadUserByUsername() should update last login timestamp")
        void loadUserByUsernameShouldUpdateLastLoginTimestamp() {
            // Arrange
            LocalDateTime beforeLogin = LocalDateTime.now().minusSeconds(1);
            when(userRepository.findByUsername("ops_user")).thenReturn(Optional.of(operationsStaffUser));
            
            // Act
            userDetailsService.loadUserByUsername("ops_user");
            
            // Assert
            verify(userRepository).findByUsername("ops_user");
            assertNotNull(operationsStaffUser.getLastLoginAt());
            assertTrue(operationsStaffUser.getLastLoginAt().isAfter(beforeLogin));
        }
    }
    
    @Nested
    @DisplayName("Loading User By ID Tests")
    class LoadingUserByIdTests {
        
        @Test
        @DisplayName("loadUserById() should return UserDetails when user exists")
        void loadUserByIdShouldReturnUserDetailsWhenUserExists() {
            // Arrange
            when(userRepository.findById(2L)).thenReturn(Optional.of(systemAdminUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserById(2L);
            
            // Assert
            assertNotNull(userDetails);
            assertEquals("admin_user", userDetails.getUsername());
            assertEquals("password456", userDetails.getPassword());
            assertTrue(userDetails.isEnabled());
            assertTrue(userDetails.getAuthorities().stream()
                    .anyMatch(a -> a.getAuthority().equals(RoleConstants.ROLE_SYSTEM_ADMIN)));
            
            verify(userRepository).findById(2L);
        }
        
        @Test
        @DisplayName("loadUserById() should throw UsernameNotFoundException when user does not exist")
        void loadUserByIdShouldThrowUsernameNotFoundExceptionWhenUserDoesNotExist() {
            // Arrange
            when(userRepository.findById(999L)).thenReturn(Optional.empty());
            
            // Act & Assert
            Exception exception = assertThrows(UsernameNotFoundException.class, () -> {
                userDetailsService.loadUserById(999L);
            });
            
            // Verify the exception message
            assertEquals("User not found with ID: 999", exception.getMessage());
            verify(userRepository).findById(999L);
        }
    }
    
    @Nested
    @DisplayName("Loading User By Email Tests")
    class LoadingUserByEmailTests {
        
        @Test
        @DisplayName("loadUserByEmail() should return UserDetails when user exists")
        void loadUserByEmailShouldReturnUserDetailsWhenUserExists() {
            // Arrange
            when(userRepository.findByEmail("user@dollarfunding.com")).thenReturn(Optional.of(regularUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserByEmail("user@dollarfunding.com");
            
            // Assert
            assertNotNull(userDetails);
            assertEquals("regular_user", userDetails.getUsername());
            assertEquals("password789", userDetails.getPassword());
            assertTrue(userDetails.isEnabled());
            
            verify(userRepository).findByEmail("user@dollarfunding.com");
        }
        
        @Test
        @DisplayName("loadUserByEmail() should throw UsernameNotFoundException when user does not exist")
        void loadUserByEmailShouldThrowUsernameNotFoundExceptionWhenUserDoesNotExist() {
            // Arrange
            when(userRepository.findByEmail("non_existent@dollarfunding.com")).thenReturn(Optional.empty());
            
            // Act & Assert
            Exception exception = assertThrows(UsernameNotFoundException.class, () -> {
                userDetailsService.loadUserByEmail("non_existent@dollarfunding.com");
            });
            
            // Verify the exception message
            assertEquals("User not found with email: non_existent@dollarfunding.com", exception.getMessage());
            verify(userRepository).findByEmail("non_existent@dollarfunding.com");
        }
    }
    
    @Nested
    @DisplayName("User Authorities Mapping Tests")
    class UserAuthoritiesMappingTests {
        
        @Test
        @DisplayName("User with Operations Staff role should have correct authorities")
        void userWithOperationsStaffRoleShouldHaveCorrectAuthorities() {
            // Arrange
            when(userRepository.findByUsername("ops_user")).thenReturn(Optional.of(operationsStaffUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserByUsername("ops_user");
            
            // Assert
            assertTrue(userDetails instanceof UserPrincipal);
            UserPrincipal userPrincipal = (UserPrincipal) userDetails;
            
            assertTrue(userPrincipal.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
            assertFalse(userPrincipal.hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN));
            assertTrue(userPrincipal.isOperationsStaff());
            assertFalse(userPrincipal.isSystemAdmin());
            
            verify(userRepository).findByUsername("ops_user");
        }
        
        @Test
        @DisplayName("User with System Admin role should have correct authorities")
        void userWithSystemAdminRoleShouldHaveCorrectAuthorities() {
            // Arrange
            when(userRepository.findByUsername("admin_user")).thenReturn(Optional.of(systemAdminUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserByUsername("admin_user");
            
            // Assert
            assertTrue(userDetails instanceof UserPrincipal);
            UserPrincipal userPrincipal = (UserPrincipal) userDetails;
            
            assertTrue(userPrincipal.hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN));
            assertFalse(userPrincipal.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
            assertTrue(userPrincipal.isSystemAdmin());
            assertFalse(userPrincipal.isOperationsStaff());
            
            verify(userRepository).findByUsername("admin_user");
        }
        
        @Test
        @DisplayName("User with no roles should have no authorities")
        void userWithNoRolesShouldHaveNoAuthorities() {
            // Arrange
            when(userRepository.findByUsername("regular_user")).thenReturn(Optional.of(regularUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserByUsername("regular_user");
            
            // Assert
            assertTrue(userDetails instanceof UserPrincipal);
            UserPrincipal userPrincipal = (UserPrincipal) userDetails;
            
            assertFalse(userPrincipal.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
            assertFalse(userPrincipal.hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN));
            assertFalse(userPrincipal.isOperationsStaff());
            assertFalse(userPrincipal.isSystemAdmin());
            assertTrue(userPrincipal.getAuthorities().isEmpty());
            
            verify(userRepository).findByUsername("regular_user");
        }
    }
    
    @Nested
    @DisplayName("Caching Tests")
    class CachingTests {
        
        @Test
        @DisplayName("loadUserByUsername() should have Cacheable annotation with correct parameters")
        void loadUserByUsernameShouldHaveCacheableAnnotationWithCorrectParameters() throws NoSuchMethodException {
            // Get the loadUserByUsername method
            java.lang.reflect.Method method = UserDetailsServiceImpl.class.getMethod("loadUserByUsername", String.class);
            
            // Check if the method has the Cacheable annotation
            assertTrue(method.isAnnotationPresent(org.springframework.cache.annotation.Cacheable.class));
            
            // Get the Cacheable annotation
            org.springframework.cache.annotation.Cacheable cacheable = 
                method.getAnnotation(org.springframework.cache.annotation.Cacheable.class);
            
            // Check the annotation parameters
            assertEquals("#username", cacheable.key());
            assertEquals("#result == null", cacheable.unless());
        }
        
        @Test
        @DisplayName("loadUserById() should have Cacheable annotation with correct parameters")
        void loadUserByIdShouldHaveCacheableAnnotationWithCorrectParameters() throws NoSuchMethodException {
            // Get the loadUserById method
            java.lang.reflect.Method method = UserDetailsServiceImpl.class.getMethod("loadUserById", Long.class);
            
            // Check if the method has the Cacheable annotation
            assertTrue(method.isAnnotationPresent(org.springframework.cache.annotation.Cacheable.class));
            
            // Get the Cacheable annotation
            org.springframework.cache.annotation.Cacheable cacheable = 
                method.getAnnotation(org.springframework.cache.annotation.Cacheable.class);
            
            // Check the annotation parameters
            assertEquals("'id_' + #id", cacheable.key());
            assertEquals("#result == null", cacheable.unless());
        }
        
        @Test
        @DisplayName("loadUserByEmail() should have Cacheable annotation with correct parameters")
        void loadUserByEmailShouldHaveCacheableAnnotationWithCorrectParameters() throws NoSuchMethodException {
            // Get the loadUserByEmail method
            java.lang.reflect.Method method = UserDetailsServiceImpl.class.getMethod("loadUserByEmail", String.class);
            
            // Check if the method has the Cacheable annotation
            assertTrue(method.isAnnotationPresent(org.springframework.cache.annotation.Cacheable.class));
            
            // Get the Cacheable annotation
            org.springframework.cache.annotation.Cacheable cacheable = 
                method.getAnnotation(org.springframework.cache.annotation.Cacheable.class);
            
            // Check the annotation parameters
            assertEquals("'email_' + #email", cacheable.key());
            assertEquals("#result == null", cacheable.unless());
        }
        
        @Test
        @DisplayName("UserDetailsServiceImpl class should have CacheConfig annotation")
        void userDetailsServiceImplClassShouldHaveCacheConfigAnnotation() {
            // Check if the class has the CacheConfig annotation
            assertTrue(UserDetailsServiceImpl.class.isAnnotationPresent(org.springframework.cache.annotation.CacheConfig.class));
            
            // Get the CacheConfig annotation
            org.springframework.cache.annotation.CacheConfig cacheConfig = 
                UserDetailsServiceImpl.class.getAnnotation(org.springframework.cache.annotation.CacheConfig.class);
            
            // Check the annotation parameters
            assertArrayEquals(new String[]{"userDetails"}, cacheConfig.cacheNames());
        }
    }
    
    @Nested
    @DisplayName("Last Login Timestamp Tests")
    class LastLoginTimestampTests {
        
        @Test
        @DisplayName("loadUserByUsername() should update last login timestamp")
        void loadUserByUsernameShouldUpdateLastLoginTimestamp() {
            // Arrange
            when(userRepository.findByUsername("ops_user")).thenReturn(Optional.of(operationsStaffUser));
            
            // Act
            userDetailsService.loadUserByUsername("ops_user");
            
            // Assert
            assertNotNull(operationsStaffUser.getLastLoginAt());
            
            // Verify that the user's last login timestamp was updated
            verify(userRepository).findByUsername("ops_user");
        }
        
        @Test
        @DisplayName("loadUserById() should update last login timestamp")
        void loadUserByIdShouldUpdateLastLoginTimestamp() {
            // Arrange
            when(userRepository.findById(2L)).thenReturn(Optional.of(systemAdminUser));
            
            // Act
            userDetailsService.loadUserById(2L);
            
            // Assert
            assertNotNull(systemAdminUser.getLastLoginAt());
            
            // Verify that the user's last login timestamp was updated
            verify(userRepository).findById(2L);
        }
        
        @Test
        @DisplayName("loadUserByEmail() should update last login timestamp")
        void loadUserByEmailShouldUpdateLastLoginTimestamp() {
            // Arrange
            when(userRepository.findByEmail("user@dollarfunding.com")).thenReturn(Optional.of(regularUser));
            
            // Act
            userDetailsService.loadUserByEmail("user@dollarfunding.com");
            
            // Assert
            assertNotNull(regularUser.getLastLoginAt());
            
            // Verify that the user's last login timestamp was updated
            verify(userRepository).findByEmail("user@dollarfunding.com");
        }
    }
    
    @Nested
    @DisplayName("Integration with Spring Security Authentication Manager Tests")
    class IntegrationWithSpringSecurityAuthenticationManagerTests {
        
        @Test
        @DisplayName("UserPrincipal created by loadUserByUsername() should have correct user details")
        void userPrincipalCreatedByLoadUserByUsernameShouldHaveCorrectUserDetails() {
            // Arrange
            when(userRepository.findByUsername("ops_user")).thenReturn(Optional.of(operationsStaffUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserByUsername("ops_user");
            
            // Assert
            assertTrue(userDetails instanceof UserPrincipal);
            UserPrincipal userPrincipal = (UserPrincipal) userDetails;
            
            assertEquals(operationsStaffUser.getId(), userPrincipal.getId());
            assertEquals(operationsStaffUser.getUsername(), userPrincipal.getUsername());
            assertEquals(operationsStaffUser.getPassword(), userPrincipal.getPassword());
            assertEquals(operationsStaffUser.getEmail(), userPrincipal.getEmail());
            assertEquals(operationsStaffUser.getFirstName(), userPrincipal.getFirstName());
            assertEquals(operationsStaffUser.getLastName(), userPrincipal.getLastName());
            assertEquals(operationsStaffUser.isEnabled(), userPrincipal.isEnabled());
            assertEquals(operationsStaffUser.isAccountNonExpired(), userPrincipal.isAccountNonExpired());
            assertEquals(operationsStaffUser.isAccountNonLocked(), userPrincipal.isAccountNonLocked());
            assertEquals(operationsStaffUser.isCredentialsNonExpired(), userPrincipal.isCredentialsNonExpired());
            
            verify(userRepository).findByUsername("ops_user");
        }
        
        @Test
        @DisplayName("UserPrincipal created by loadUserById() should have correct user details")
        void userPrincipalCreatedByLoadUserByIdShouldHaveCorrectUserDetails() {
            // Arrange
            when(userRepository.findById(2L)).thenReturn(Optional.of(systemAdminUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserById(2L);
            
            // Assert
            assertTrue(userDetails instanceof UserPrincipal);
            UserPrincipal userPrincipal = (UserPrincipal) userDetails;
            
            assertEquals(systemAdminUser.getId(), userPrincipal.getId());
            assertEquals(systemAdminUser.getUsername(), userPrincipal.getUsername());
            assertEquals(systemAdminUser.getPassword(), userPrincipal.getPassword());
            assertEquals(systemAdminUser.getEmail(), userPrincipal.getEmail());
            assertEquals(systemAdminUser.getFirstName(), userPrincipal.getFirstName());
            assertEquals(systemAdminUser.getLastName(), userPrincipal.getLastName());
            assertEquals(systemAdminUser.isEnabled(), userPrincipal.isEnabled());
            assertEquals(systemAdminUser.isAccountNonExpired(), userPrincipal.isAccountNonExpired());
            assertEquals(systemAdminUser.isAccountNonLocked(), userPrincipal.isAccountNonLocked());
            assertEquals(systemAdminUser.isCredentialsNonExpired(), userPrincipal.isCredentialsNonExpired());
            
            verify(userRepository).findById(2L);
        }
        
        @Test
        @DisplayName("UserPrincipal created by loadUserByEmail() should have correct user details")
        void userPrincipalCreatedByLoadUserByEmailShouldHaveCorrectUserDetails() {
            // Arrange
            when(userRepository.findByEmail("user@dollarfunding.com")).thenReturn(Optional.of(regularUser));
            
            // Act
            UserDetails userDetails = userDetailsService.loadUserByEmail("user@dollarfunding.com");
            
            // Assert
            assertTrue(userDetails instanceof UserPrincipal);
            UserPrincipal userPrincipal = (UserPrincipal) userDetails;
            
            assertEquals(regularUser.getId(), userPrincipal.getId());
            assertEquals(regularUser.getUsername(), userPrincipal.getUsername());
            assertEquals(regularUser.getPassword(), userPrincipal.getPassword());
            assertEquals(regularUser.getEmail(), userPrincipal.getEmail());
            assertEquals(regularUser.getFirstName(), userPrincipal.getFirstName());
            assertEquals(regularUser.getLastName(), userPrincipal.getLastName());
            assertEquals(regularUser.isEnabled(), userPrincipal.isEnabled());
            assertEquals(regularUser.isAccountNonExpired(), userPrincipal.isAccountNonExpired());
            assertEquals(regularUser.isAccountNonLocked(), userPrincipal.isAccountNonLocked());
            assertEquals(regularUser.isCredentialsNonExpired(), userPrincipal.isCredentialsNonExpired());
            
            verify(userRepository).findByEmail("user@dollarfunding.com");
        }
    }
}