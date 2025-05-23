package com.dollarfunding.mca.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

import java.util.Arrays;
import java.util.Collection;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link UserPrincipal} that verifies the correct implementation of the
 * UserDetails interface for Spring Security. It tests the encapsulation of user information
 * including ID, username, password, email, authorities, and account status flags.
 */
@DisplayName("UserPrincipal Tests")
public class UserPrincipalTest {

    private static final Long USER_ID = 1L;
    private static final String USERNAME = "testuser";
    private static final String EMAIL = "test@dollarfunding.com";
    private static final String PASSWORD = "encodedPassword";
    private static final String FIRST_NAME = "Test";
    private static final String LAST_NAME = "User";
    private static final Collection<GrantedAuthority> AUTHORITIES = Arrays.asList(
            new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)
    );

    private UserPrincipal userPrincipal;
    private User user;

    @BeforeEach
    void setUp() {
        // Create a UserPrincipal instance using the builder pattern
        userPrincipal = UserPrincipal.builder()
                .id(USER_ID)
                .username(USERNAME)
                .email(EMAIL)
                .password(PASSWORD)
                .authorities(AUTHORITIES)
                .firstName(FIRST_NAME)
                .lastName(LAST_NAME)
                .enabled(true)
                .accountNonExpired(true)
                .credentialsNonExpired(true)
                .accountNonLocked(true)
                .build();

        // Create a User entity for testing the create() method
        user = new User(USERNAME, PASSWORD, EMAIL, FIRST_NAME, LAST_NAME);
        Role role = new Role();
        role.setName(RoleConstants.ROLE_OPERATIONS_STAFF);
        Set<Role> roles = new HashSet<>();
        roles.add(role);
        user.setRoles(roles);
        user.setId(USER_ID);
        user.setEnabled(true);
        user.setAccountNonExpired(true);
        user.setCredentialsNonExpired(true);
        user.setAccountNonLocked(true);
    }

    @Test
    @DisplayName("Should create UserPrincipal from User entity")
    void shouldCreateFromUserEntity() {
        // When
        UserPrincipal result = UserPrincipal.create(user);

        // Then
        assertEquals(USER_ID, result.getId());
        assertEquals(USERNAME, result.getUsername());
        assertEquals(EMAIL, result.getEmail());
        assertEquals(PASSWORD, result.getPassword());
        assertEquals(FIRST_NAME, result.getFirstName());
        assertEquals(LAST_NAME, result.getLastName());
        assertTrue(result.isEnabled());
        assertTrue(result.isAccountNonExpired());
        assertTrue(result.isCredentialsNonExpired());
        assertTrue(result.isAccountNonLocked());
        assertEquals(1, result.getAuthorities().size());
        assertTrue(result.getAuthorities().stream()
                .anyMatch(a -> a.getAuthority().equals(RoleConstants.ROLE_OPERATIONS_STAFF)));
    }

    @Test
    @DisplayName("Should implement UserDetails interface correctly")
    void shouldImplementUserDetailsInterface() {
        // Then - Testing UserDetails interface methods
        assertEquals(USERNAME, userPrincipal.getUsername());
        assertEquals(PASSWORD, userPrincipal.getPassword());
        assertEquals(AUTHORITIES, userPrincipal.getAuthorities());
        assertTrue(userPrincipal.isEnabled());
        assertTrue(userPrincipal.isAccountNonExpired());
        assertTrue(userPrincipal.isCredentialsNonExpired());
        assertTrue(userPrincipal.isAccountNonLocked());
    }

    @Test
    @DisplayName("Should return correct account status when disabled")
    void shouldReturnCorrectAccountStatusWhenDisabled() {
        // Given
        UserPrincipal disabledUser = UserPrincipal.builder()
                .id(USER_ID)
                .username(USERNAME)
                .email(EMAIL)
                .password(PASSWORD)
                .authorities(AUTHORITIES)
                .enabled(false)
                .accountNonExpired(false)
                .credentialsNonExpired(false)
                .accountNonLocked(false)
                .build();

        // Then
        assertFalse(disabledUser.isEnabled());
        assertFalse(disabledUser.isAccountNonExpired());
        assertFalse(disabledUser.isCredentialsNonExpired());
        assertFalse(disabledUser.isAccountNonLocked());
    }

    @Test
    @DisplayName("Should return additional user information correctly")
    void shouldReturnAdditionalUserInformation() {
        // Then
        assertEquals(USER_ID, userPrincipal.getId());
        assertEquals(EMAIL, userPrincipal.getEmail());
        assertEquals(FIRST_NAME, userPrincipal.getFirstName());
        assertEquals(LAST_NAME, userPrincipal.getLastName());
        assertEquals(FIRST_NAME + " " + LAST_NAME, userPrincipal.getFullName());
    }

    @Test
    @DisplayName("Should handle null first and last name in getFullName")
    void shouldHandleNullFirstAndLastNameInGetFullName() {
        // Given
        UserPrincipal userWithoutNames = UserPrincipal.builder()
                .id(USER_ID)
                .username(USERNAME)
                .email(EMAIL)
                .password(PASSWORD)
                .authorities(AUTHORITIES)
                .build();

        // Then
        assertEquals(USERNAME, userWithoutNames.getFullName());

        // Given
        UserPrincipal userWithFirstNameOnly = UserPrincipal.builder()
                .id(USER_ID)
                .username(USERNAME)
                .email(EMAIL)
                .password(PASSWORD)
                .authorities(AUTHORITIES)
                .firstName(FIRST_NAME)
                .build();

        // Then
        assertEquals(FIRST_NAME, userWithFirstNameOnly.getFullName());

        // Given
        UserPrincipal userWithLastNameOnly = UserPrincipal.builder()
                .id(USER_ID)
                .username(USERNAME)
                .email(EMAIL)
                .password(PASSWORD)
                .authorities(AUTHORITIES)
                .lastName(LAST_NAME)
                .build();

        // Then
        assertEquals(LAST_NAME, userWithLastNameOnly.getFullName());
    }

    @Test
    @DisplayName("Should check authority correctly")
    void shouldCheckAuthorityCorrectly() {
        // Then
        assertTrue(userPrincipal.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
        assertFalse(userPrincipal.hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN));
    }

    @Test
    @DisplayName("Should check role correctly")
    void shouldCheckRoleCorrectly() {
        // Then
        assertTrue(userPrincipal.hasRole(RoleConstants.OPERATIONS_STAFF));
        assertFalse(userPrincipal.hasRole(RoleConstants.SYSTEM_ADMIN));
    }

    @Test
    @DisplayName("Should check specific roles correctly")
    void shouldCheckSpecificRolesCorrectly() {
        // Given
        UserPrincipal adminUser = UserPrincipal.builder()
                .id(2L)
                .username("admin")
                .email("admin@dollarfunding.com")
                .password(PASSWORD)
                .authorities(Arrays.asList(
                        new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
                ))
                .build();

        // Then
        assertTrue(userPrincipal.isOperationsStaff());
        assertFalse(userPrincipal.isSystemAdmin());

        assertTrue(adminUser.isSystemAdmin());
        assertFalse(adminUser.isOperationsStaff());
    }

    @Test
    @DisplayName("Should implement equals and hashCode correctly")
    void shouldImplementEqualsAndHashCodeCorrectly() {
        // Given
        UserPrincipal samePrincipal = UserPrincipal.builder()
                .id(USER_ID)
                .username("different")
                .email("different@dollarfunding.com")
                .password("different")
                .build();

        UserPrincipal differentPrincipal = UserPrincipal.builder()
                .id(2L)
                .username(USERNAME)
                .email(EMAIL)
                .password(PASSWORD)
                .build();

        // Then
        assertEquals(userPrincipal, userPrincipal); // Same instance
        assertEquals(userPrincipal, samePrincipal); // Same ID
        assertNotEquals(userPrincipal, differentPrincipal); // Different ID
        assertNotEquals(userPrincipal, null); // Null comparison
        assertNotEquals(userPrincipal, new Object()); // Different type

        // HashCode should be based on ID
        assertEquals(userPrincipal.hashCode(), samePrincipal.hashCode());
        assertNotEquals(userPrincipal.hashCode(), differentPrincipal.hashCode());
    }

    @Test
    @DisplayName("Should generate toString correctly")
    void shouldGenerateToStringCorrectly() {
        // When
        String toString = userPrincipal.toString();

        // Then
        assertTrue(toString.contains(USER_ID.toString()));
        assertTrue(toString.contains(USERNAME));
        assertTrue(toString.contains(EMAIL));
        assertTrue(toString.contains(FIRST_NAME));
        assertTrue(toString.contains(LAST_NAME));
    }

    @Test
    @DisplayName("Should build UserPrincipal with default values")
    void shouldBuildUserPrincipalWithDefaultValues() {
        // When
        UserPrincipal minimalPrincipal = UserPrincipal.builder()
                .id(USER_ID)
                .username(USERNAME)
                .password(PASSWORD)
                .authorities(AUTHORITIES)
                .build();

        // Then - Default values should be applied
        assertTrue(minimalPrincipal.isEnabled());
        assertTrue(minimalPrincipal.isAccountNonExpired());
        assertTrue(minimalPrincipal.isCredentialsNonExpired());
        assertTrue(minimalPrincipal.isAccountNonLocked());
        assertNull(minimalPrincipal.getEmail());
        assertNull(minimalPrincipal.getFirstName());
        assertNull(minimalPrincipal.getLastName());
    }

    @Test
    @DisplayName("Should build UserPrincipal with all fields")
    void shouldBuildUserPrincipalWithAllFields() {
        // When
        UserPrincipal fullPrincipal = UserPrincipal.builder()
                .id(USER_ID)
                .username(USERNAME)
                .email(EMAIL)
                .password(PASSWORD)
                .authorities(AUTHORITIES)
                .firstName(FIRST_NAME)
                .lastName(LAST_NAME)
                .enabled(true)
                .accountNonExpired(true)
                .credentialsNonExpired(true)
                .accountNonLocked(true)
                .build();

        // Then
        assertEquals(USER_ID, fullPrincipal.getId());
        assertEquals(USERNAME, fullPrincipal.getUsername());
        assertEquals(EMAIL, fullPrincipal.getEmail());
        assertEquals(PASSWORD, fullPrincipal.getPassword());
        assertEquals(AUTHORITIES, fullPrincipal.getAuthorities());
        assertEquals(FIRST_NAME, fullPrincipal.getFirstName());
        assertEquals(LAST_NAME, fullPrincipal.getLastName());
        assertTrue(fullPrincipal.isEnabled());
        assertTrue(fullPrincipal.isAccountNonExpired());
        assertTrue(fullPrincipal.isCredentialsNonExpired());
        assertTrue(fullPrincipal.isAccountNonLocked());
    }
}