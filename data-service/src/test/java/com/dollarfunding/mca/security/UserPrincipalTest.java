package com.dollarfunding.mca.security;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

/**
 * Test class for {@link UserPrincipal} that verifies the correct implementation of the
 * UserDetails interface for Spring Security.
 */
@DisplayName("UserPrincipal Tests")
public class UserPrincipalTest {

    private User testUser;
    private Collection<GrantedAuthority> authorities;
    private UserPrincipal userPrincipal;

    @BeforeEach
    void setUp() {
        // Create test roles
        Role operationsStaffRole = new Role(RoleConstants.ROLE_OPERATIONS_STAFF, 
                                          RoleConstants.OPERATIONS_STAFF_DESCRIPTION);
        
        // Create test user
        testUser = new User("testuser", "password123", "test@example.com", 
                          "Test", "User", true, true, true, true);
        testUser.setId(1L);
        testUser.addRole(operationsStaffRole);
        
        // Create authorities
        authorities = List.of(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
        
        // Create user principal
        userPrincipal = new UserPrincipal(
            testUser.getId(),
            testUser.getUsername(),
            testUser.getPassword(),
            testUser.getEmail(),
            testUser.getFirstName(),
            testUser.getLastName(),
            authorities,
            testUser.isEnabled(),
            testUser.isAccountNonExpired(),
            testUser.isAccountNonLocked(),
            testUser.isCredentialsNonExpired()
        );
    }

    @Nested
    @DisplayName("UserDetails Interface Implementation Tests")
    class UserDetailsInterfaceTests {
        
        @Test
        @DisplayName("getUsername() should return the correct username")
        void getUsernameShouldReturnCorrectUsername() {
            assertEquals("testuser", userPrincipal.getUsername());
        }
        
        @Test
        @DisplayName("getPassword() should return the correct password")
        void getPasswordShouldReturnCorrectPassword() {
            assertEquals("password123", userPrincipal.getPassword());
        }
        
        @Test
        @DisplayName("getAuthorities() should return the correct authorities")
        void getAuthoritiesShouldReturnCorrectAuthorities() {
            Collection<? extends GrantedAuthority> userAuthorities = userPrincipal.getAuthorities();
            
            assertEquals(1, userAuthorities.size());
            assertTrue(userAuthorities.contains(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)));
        }
        
        @Test
        @DisplayName("isEnabled() should return the correct enabled status")
        void isEnabledShouldReturnCorrectStatus() {
            assertTrue(userPrincipal.isEnabled());
            
            // Create disabled user principal
            UserPrincipal disabledPrincipal = new UserPrincipal(
                1L, "testuser", "password", "test@example.com", "Test", "User",
                authorities, false, true, true, true
            );
            
            assertFalse(disabledPrincipal.isEnabled());
        }
    }
    
    @Nested
    @DisplayName("Account Status Methods Tests")
    class AccountStatusMethodsTests {
        
        @Test
        @DisplayName("isAccountNonExpired() should return the correct account expiration status")
        void isAccountNonExpiredShouldReturnCorrectStatus() {
            assertTrue(userPrincipal.isAccountNonExpired());
            
            // Create user principal with expired account
            UserPrincipal expiredPrincipal = new UserPrincipal(
                1L, "testuser", "password", "test@example.com", "Test", "User",
                authorities, true, false, true, true
            );
            
            assertFalse(expiredPrincipal.isAccountNonExpired());
        }
        
        @Test
        @DisplayName("isAccountNonLocked() should return the correct account lock status")
        void isAccountNonLockedShouldReturnCorrectStatus() {
            assertTrue(userPrincipal.isAccountNonLocked());
            
            // Create user principal with locked account
            UserPrincipal lockedPrincipal = new UserPrincipal(
                1L, "testuser", "password", "test@example.com", "Test", "User",
                authorities, true, true, false, true
            );
            
            assertFalse(lockedPrincipal.isAccountNonLocked());
        }
        
        @Test
        @DisplayName("isCredentialsNonExpired() should return the correct credentials expiration status")
        void isCredentialsNonExpiredShouldReturnCorrectStatus() {
            assertTrue(userPrincipal.isCredentialsNonExpired());
            
            // Create user principal with expired credentials
            UserPrincipal expiredCredentialsPrincipal = new UserPrincipal(
                1L, "testuser", "password", "test@example.com", "Test", "User",
                authorities, true, true, true, false
            );
            
            assertFalse(expiredCredentialsPrincipal.isCredentialsNonExpired());
        }
        
        @Test
        @DisplayName("All account status combinations should work correctly")
        void allAccountStatusCombinationsShouldWorkCorrectly() {
            // Test all combinations of account status flags
            UserPrincipal principal1 = new UserPrincipal(
                1L, "user1", "pass1", "email1@example.com", "First1", "Last1",
                authorities, false, false, false, false
            );
            assertFalse(principal1.isEnabled());
            assertFalse(principal1.isAccountNonExpired());
            assertFalse(principal1.isAccountNonLocked());
            assertFalse(principal1.isCredentialsNonExpired());
            
            UserPrincipal principal2 = new UserPrincipal(
                2L, "user2", "pass2", "email2@example.com", "First2", "Last2",
                authorities, true, true, true, true
            );
            assertTrue(principal2.isEnabled());
            assertTrue(principal2.isAccountNonExpired());
            assertTrue(principal2.isAccountNonLocked());
            assertTrue(principal2.isCredentialsNonExpired());
        }
    }
    
    @Nested
    @DisplayName("Authority and Role Checking Methods Tests")
    class AuthorityAndRoleCheckingMethodsTests {
        
        @Test
        @DisplayName("hasAuthority() should return true for authorities the user has")
        void hasAuthorityShouldReturnTrueForAuthoritiesUserHas() {
            assertTrue(userPrincipal.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
            assertFalse(userPrincipal.hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN));
            assertFalse(userPrincipal.hasAuthority("ROLE_NONEXISTENT"));
        }
        
        @Test
        @DisplayName("hasRole() should return true for roles the user has")
        void hasRoleShouldReturnTrueForRolesUserHas() {
            // Test with role prefix
            assertTrue(userPrincipal.hasRole(RoleConstants.ROLE_OPERATIONS_STAFF));
            assertFalse(userPrincipal.hasRole(RoleConstants.ROLE_SYSTEM_ADMIN));
            
            // Test without role prefix
            assertTrue(userPrincipal.hasRole(RoleConstants.OPERATIONS_STAFF));
            assertFalse(userPrincipal.hasRole(RoleConstants.SYSTEM_ADMIN));
        }
        
        @Test
        @DisplayName("isOperationsStaff() should return true for operations staff users")
        void isOperationsStaffShouldReturnTrueForOperationsStaffUsers() {
            assertTrue(userPrincipal.isOperationsStaff());
            
            // Create user principal with system admin role
            UserPrincipal systemAdminPrincipal = new UserPrincipal(
                1L, "admin", "password", "admin@example.com", "Admin", "User",
                List.of(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)),
                true, true, true, true
            );
            
            assertFalse(systemAdminPrincipal.isOperationsStaff());
        }
        
        @Test
        @DisplayName("isSystemAdmin() should return true for system admin users")
        void isSystemAdminShouldReturnTrueForSystemAdminUsers() {
            assertFalse(userPrincipal.isSystemAdmin());
            
            // Create user principal with system admin role
            UserPrincipal systemAdminPrincipal = new UserPrincipal(
                1L, "admin", "password", "admin@example.com", "Admin", "User",
                List.of(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)),
                true, true, true, true
            );
            
            assertTrue(systemAdminPrincipal.isSystemAdmin());
        }
        
        @Test
        @DisplayName("User with multiple roles should have all authorities")
        void userWithMultipleRolesShouldHaveAllAuthorities() {
            // Create user principal with multiple roles
            UserPrincipal multiRolePrincipal = new UserPrincipal(
                1L, "multiuser", "password", "multi@example.com", "Multi", "User",
                List.of(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF),
                    new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
                ),
                true, true, true, true
            );
            
            assertTrue(multiRolePrincipal.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
            assertTrue(multiRolePrincipal.hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN));
            assertTrue(multiRolePrincipal.isOperationsStaff());
            assertTrue(multiRolePrincipal.isSystemAdmin());
        }
    }
    
    @Nested
    @DisplayName("Builder Pattern Tests")
    class BuilderPatternTests {
        
        @Test
        @DisplayName("Builder should create UserPrincipal with correct values")
        void builderShouldCreateUserPrincipalWithCorrectValues() {
            UserPrincipal principal = UserPrincipal.builder()
                .id(1L)
                .username("builduser")
                .password("buildpass")
                .email("build@example.com")
                .firstName("Build")
                .lastName("User")
                .authorities(authorities)
                .enabled(true)
                .accountNonExpired(true)
                .accountNonLocked(true)
                .credentialsNonExpired(true)
                .build();
            
            assertEquals(1L, principal.getId());
            assertEquals("builduser", principal.getUsername());
            assertEquals("buildpass", principal.getPassword());
            assertEquals("build@example.com", principal.getEmail());
            assertEquals("Build", principal.getFirstName());
            assertEquals("User", principal.getLastName());
            assertEquals(authorities, principal.getAuthorities());
            assertTrue(principal.isEnabled());
            assertTrue(principal.isAccountNonExpired());
            assertTrue(principal.isAccountNonLocked());
            assertTrue(principal.isCredentialsNonExpired());
        }
        
        @Test
        @DisplayName("Builder should use default values when not specified")
        void builderShouldUseDefaultValuesWhenNotSpecified() {
            UserPrincipal principal = UserPrincipal.builder()
                .id(1L)
                .username("defaultuser")
                .password("defaultpass")
                .email("default@example.com")
                .authorities(authorities)
                .build();
            
            // Default values should be used
            assertTrue(principal.isEnabled());
            assertTrue(principal.isAccountNonExpired());
            assertTrue(principal.isAccountNonLocked());
            assertTrue(principal.isCredentialsNonExpired());
        }
    }
    
    @Nested
    @DisplayName("Spring Security Integration Tests")
    class SpringSecurityIntegrationTests {
        
        @Test
        @DisplayName("create() should create UserPrincipal from User entity")
        void createShouldCreateUserPrincipalFromUserEntity() {
            UserPrincipal principal = UserPrincipal.create(testUser);
            
            assertEquals(testUser.getId(), principal.getId());
            assertEquals(testUser.getUsername(), principal.getUsername());
            assertEquals(testUser.getPassword(), principal.getPassword());
            assertEquals(testUser.getEmail(), principal.getEmail());
            assertEquals(testUser.getFirstName(), principal.getFirstName());
            assertEquals(testUser.getLastName(), principal.getLastName());
            assertTrue(principal.isEnabled());
            assertTrue(principal.isAccountNonExpired());
            assertTrue(principal.isAccountNonLocked());
            assertTrue(principal.isCredentialsNonExpired());
            
            // Check authorities
            Collection<? extends GrantedAuthority> principalAuthorities = principal.getAuthorities();
            assertEquals(1, principalAuthorities.size());
            assertTrue(principalAuthorities.contains(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)));
        }
        
        @Test
        @DisplayName("create() with authorities should create UserPrincipal with specified authorities")
        void createWithAuthoritiesShouldCreateUserPrincipalWithSpecifiedAuthorities() {
            Collection<GrantedAuthority> customAuthorities = List.of(
                new SimpleGrantedAuthority("CUSTOM_AUTHORITY")
            );
            
            UserPrincipal principal = UserPrincipal.create(testUser, customAuthorities);
            
            // Check custom authorities
            Collection<? extends GrantedAuthority> principalAuthorities = principal.getAuthorities();
            assertEquals(1, principalAuthorities.size());
            assertTrue(principalAuthorities.contains(new SimpleGrantedAuthority("CUSTOM_AUTHORITY")));
        }
        
        @Test
        @DisplayName("createOperationsStaffPrincipal() should create UserPrincipal with Operations Staff role")
        void createOperationsStaffPrincipalShouldCreateUserPrincipalWithOperationsStaffRole() {
            UserPrincipal principal = UserPrincipal.createOperationsStaffPrincipal(testUser);
            
            // Check authorities
            Collection<? extends GrantedAuthority> principalAuthorities = principal.getAuthorities();
            assertEquals(1, principalAuthorities.size());
            assertTrue(principalAuthorities.contains(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)));
            assertTrue(principal.isOperationsStaff());
            assertFalse(principal.isSystemAdmin());
        }
        
        @Test
        @DisplayName("createSystemAdminPrincipal() should create UserPrincipal with System Admin role")
        void createSystemAdminPrincipalShouldCreateUserPrincipalWithSystemAdminRole() {
            UserPrincipal principal = UserPrincipal.createSystemAdminPrincipal(testUser);
            
            // Check authorities
            Collection<? extends GrantedAuthority> principalAuthorities = principal.getAuthorities();
            assertEquals(2, principalAuthorities.size());
            assertTrue(principalAuthorities.contains(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)));
            assertTrue(principalAuthorities.contains(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)));
            assertTrue(principal.isOperationsStaff());
            assertTrue(principal.isSystemAdmin());
        }
    }
    
    @Nested
    @DisplayName("Additional Methods Tests")
    class AdditionalMethodsTests {
        
        @Test
        @DisplayName("getId() should return the correct ID")
        void getIdShouldReturnCorrectId() {
            assertEquals(1L, userPrincipal.getId());
        }
        
        @Test
        @DisplayName("getEmail() should return the correct email")
        void getEmailShouldReturnCorrectEmail() {
            assertEquals("test@example.com", userPrincipal.getEmail());
        }
        
        @Test
        @DisplayName("getFirstName() should return the correct first name")
        void getFirstNameShouldReturnCorrectFirstName() {
            assertEquals("Test", userPrincipal.getFirstName());
        }
        
        @Test
        @DisplayName("getLastName() should return the correct last name")
        void getLastNameShouldReturnCorrectLastName() {
            assertEquals("User", userPrincipal.getLastName());
        }
        
        @Test
        @DisplayName("getFullName() should return the correct full name")
        void getFullNameShouldReturnCorrectFullName() {
            assertEquals("Test User", userPrincipal.getFullName());
            
            // Test with null first name
            UserPrincipal principalWithNullFirstName = new UserPrincipal(
                1L, "user", "pass", "email@example.com", null, "LastOnly",
                authorities, true, true, true, true
            );
            assertEquals("LastOnly", principalWithNullFirstName.getFullName());
            
            // Test with null last name
            UserPrincipal principalWithNullLastName = new UserPrincipal(
                1L, "user", "pass", "email@example.com", "FirstOnly", null,
                authorities, true, true, true, true
            );
            assertEquals("FirstOnly", principalWithNullLastName.getFullName());
            
            // Test with null first and last name
            UserPrincipal principalWithNullNames = new UserPrincipal(
                1L, "username", "pass", "email@example.com", null, null,
                authorities, true, true, true, true
            );
            assertEquals("username", principalWithNullNames.getFullName());
        }
        
        @Test
        @DisplayName("equals() should return true for same ID")
        void equalsShouldReturnTrueForSameId() {
            UserPrincipal principal1 = new UserPrincipal(
                1L, "user1", "pass1", "email1@example.com", "First1", "Last1",
                authorities, true, true, true, true
            );
            
            UserPrincipal principal2 = new UserPrincipal(
                1L, "user2", "pass2", "email2@example.com", "First2", "Last2",
                authorities, false, false, false, false
            );
            
            assertEquals(principal1, principal2);
            assertEquals(principal1.hashCode(), principal2.hashCode());
        }
        
        @Test
        @DisplayName("equals() should return false for different ID")
        void equalsShouldReturnFalseForDifferentId() {
            UserPrincipal principal1 = new UserPrincipal(
                1L, "user", "pass", "email@example.com", "First", "Last",
                authorities, true, true, true, true
            );
            
            UserPrincipal principal2 = new UserPrincipal(
                2L, "user", "pass", "email@example.com", "First", "Last",
                authorities, true, true, true, true
            );
            
            assertNotEquals(principal1, principal2);
            assertNotEquals(principal1.hashCode(), principal2.hashCode());
        }
        
        @Test
        @DisplayName("toString() should return a string containing important fields")
        void toStringShouldReturnStringContainingImportantFields() {
            String toString = userPrincipal.toString();
            
            assertTrue(toString.contains("id=1"));
            assertTrue(toString.contains("username='testuser'"));
            assertTrue(toString.contains("email='test@example.com'"));
            assertTrue(toString.contains("enabled=true"));
        }
    }
}