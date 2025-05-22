package com.dollarfunding.mca.security;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link SecurityUtils}.
 */
@ExtendWith(MockitoExtension.class)
public class SecurityUtilsTest {

    @Mock
    private SecurityContext securityContext;

    @Mock
    private Authentication authentication;

    private MockedStatic<SecurityContextHolder> securityContextHolder;

    @BeforeEach
    public void setup() {
        securityContextHolder = Mockito.mockStatic(SecurityContextHolder.class);
        securityContextHolder.when(SecurityContextHolder::getContext).thenReturn(securityContext);
    }

    @AfterEach
    public void tearDown() {
        securityContextHolder.close();
    }

    @Test
    @DisplayName("Should return empty when no authentication is present")
    public void getCurrentUserLogin_NoAuthentication_ReturnsEmpty() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(null);

        // When
        Optional<String> userLogin = SecurityUtils.getCurrentUserLogin();

        // Then
        assertThat(userLogin).isEmpty();
    }

    @Test
    @DisplayName("Should return username when principal is a String")
    public void getCurrentUserLogin_PrincipalIsString_ReturnsUsername() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.getPrincipal()).thenReturn("testuser");

        // When
        Optional<String> userLogin = SecurityUtils.getCurrentUserLogin();

        // Then
        assertThat(userLogin).isPresent();
        assertThat(userLogin.get()).isEqualTo("testuser");
    }

    @Test
    @DisplayName("Should return username when principal is a UserDetails")
    public void getCurrentUserLogin_PrincipalIsUserDetails_ReturnsUsername() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .username("testuser")
                .password("password")
                .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")))
                .build();
        when(authentication.getPrincipal()).thenReturn(userPrincipal);

        // When
        Optional<String> userLogin = SecurityUtils.getCurrentUserLogin();

        // Then
        assertThat(userLogin).isPresent();
        assertThat(userLogin.get()).isEqualTo("testuser");
    }

    @Test
    @DisplayName("Should return empty when principal is an unsupported type")
    public void getCurrentUserLogin_PrincipalIsUnsupportedType_ReturnsEmpty() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.getPrincipal()).thenReturn(new Object());

        // When
        Optional<String> userLogin = SecurityUtils.getCurrentUserLogin();

        // Then
        assertThat(userLogin).isEmpty();
    }

    @Test
    @DisplayName("Should return empty when no authentication is present for user principal")
    public void getCurrentUserPrincipal_NoAuthentication_ReturnsEmpty() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(null);

        // When
        Optional<UserPrincipal> userPrincipal = SecurityUtils.getCurrentUserPrincipal();

        // Then
        assertThat(userPrincipal).isEmpty();
    }

    @Test
    @DisplayName("Should return UserPrincipal when principal is a UserPrincipal")
    public void getCurrentUserPrincipal_PrincipalIsUserPrincipal_ReturnsUserPrincipal() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(1L)
                .username("testuser")
                .password("password")
                .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")))
                .build();
        when(authentication.getPrincipal()).thenReturn(userPrincipal);

        // When
        Optional<UserPrincipal> result = SecurityUtils.getCurrentUserPrincipal();

        // Then
        assertThat(result).isPresent();
        assertThat(result.get()).isEqualTo(userPrincipal);
    }

    @Test
    @DisplayName("Should return empty when principal is not a UserPrincipal")
    public void getCurrentUserPrincipal_PrincipalIsNotUserPrincipal_ReturnsEmpty() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.getPrincipal()).thenReturn("testuser");

        // When
        Optional<UserPrincipal> userPrincipal = SecurityUtils.getCurrentUserPrincipal();

        // Then
        assertThat(userPrincipal).isEmpty();
    }

    @Test
    @DisplayName("Should return empty when no authentication is present for user ID")
    public void getCurrentUserId_NoAuthentication_ReturnsEmpty() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(null);

        // When
        Optional<Long> userId = SecurityUtils.getCurrentUserId();

        // Then
        assertThat(userId).isEmpty();
    }

    @Test
    @DisplayName("Should return user ID when principal is a UserPrincipal")
    public void getCurrentUserId_PrincipalIsUserPrincipal_ReturnsUserId() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(1L)
                .username("testuser")
                .password("password")
                .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")))
                .build();
        when(authentication.getPrincipal()).thenReturn(userPrincipal);

        // When
        Optional<Long> userId = SecurityUtils.getCurrentUserId();

        // Then
        assertThat(userId).isPresent();
        assertThat(userId.get()).isEqualTo(1L);
    }

    @Test
    @DisplayName("Should return false when no authentication is present for hasAuthority")
    public void hasAuthority_NoAuthentication_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(null);

        // When
        boolean hasAuthority = SecurityUtils.hasAuthority("ROLE_USER");

        // Then
        assertThat(hasAuthority).isFalse();
    }

    @Test
    @DisplayName("Should return false when authentication is not authenticated for hasAuthority")
    public void hasAuthority_NotAuthenticated_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(false);

        // When
        boolean hasAuthority = SecurityUtils.hasAuthority("ROLE_USER");

        // Then
        assertThat(hasAuthority).isFalse();
    }

    @Test
    @DisplayName("Should return true when user has the specified authority")
    public void hasAuthority_HasAuthority_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));

        // When
        boolean hasAuthority = SecurityUtils.hasAuthority("ROLE_USER");

        // Then
        assertThat(hasAuthority).isTrue();
    }

    @Test
    @DisplayName("Should return false when user does not have the specified authority")
    public void hasAuthority_DoesNotHaveAuthority_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));

        // When
        boolean hasAuthority = SecurityUtils.hasAuthority("ROLE_ADMIN");

        // Then
        assertThat(hasAuthority).isFalse();
    }

    @Test
    @DisplayName("Should return false when no authentication is present for hasAnyAuthority")
    public void hasAnyAuthority_NoAuthentication_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(null);

        // When
        boolean hasAnyAuthority = SecurityUtils.hasAnyAuthority("ROLE_USER", "ROLE_ADMIN");

        // Then
        assertThat(hasAnyAuthority).isFalse();
    }

    @Test
    @DisplayName("Should return false when authentication is not authenticated for hasAnyAuthority")
    public void hasAnyAuthority_NotAuthenticated_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(false);

        // When
        boolean hasAnyAuthority = SecurityUtils.hasAnyAuthority("ROLE_USER", "ROLE_ADMIN");

        // Then
        assertThat(hasAnyAuthority).isFalse();
    }

    @Test
    @DisplayName("Should return true when user has any of the specified authorities")
    public void hasAnyAuthority_HasOneAuthority_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));

        // When
        boolean hasAnyAuthority = SecurityUtils.hasAnyAuthority("ROLE_USER", "ROLE_ADMIN");

        // Then
        assertThat(hasAnyAuthority).isTrue();
    }

    @Test
    @DisplayName("Should return false when user does not have any of the specified authorities")
    public void hasAnyAuthority_DoesNotHaveAnyAuthority_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));

        // When
        boolean hasAnyAuthority = SecurityUtils.hasAnyAuthority("ROLE_ADMIN", "ROLE_MANAGER");

        // Then
        assertThat(hasAnyAuthority).isFalse();
    }

    @Test
    @DisplayName("Should return true when user has Operations Staff role")
    public void isOperationsStaff_HasRole_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority(SecurityUtils.ROLE_OPERATIONS_STAFF)));

        // When
        boolean isOperationsStaff = SecurityUtils.isOperationsStaff();

        // Then
        assertThat(isOperationsStaff).isTrue();
    }

    @Test
    @DisplayName("Should return false when user does not have Operations Staff role")
    public void isOperationsStaff_DoesNotHaveRole_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));

        // When
        boolean isOperationsStaff = SecurityUtils.isOperationsStaff();

        // Then
        assertThat(isOperationsStaff).isFalse();
    }

    @Test
    @DisplayName("Should return true when user has System Admin role")
    public void isSystemAdmin_HasRole_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority(SecurityUtils.ROLE_SYSTEM_ADMIN)));

        // When
        boolean isSystemAdmin = SecurityUtils.isSystemAdmin();

        // Then
        assertThat(isSystemAdmin).isTrue();
    }

    @Test
    @DisplayName("Should return false when user does not have System Admin role")
    public void isSystemAdmin_DoesNotHaveRole_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));

        // When
        boolean isSystemAdmin = SecurityUtils.isSystemAdmin();

        // Then
        assertThat(isSystemAdmin).isFalse();
    }

    @Test
    @DisplayName("Should return false when no authentication is present for isAuthenticated")
    public void isAuthenticated_NoAuthentication_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(null);

        // When
        boolean isAuthenticated = SecurityUtils.isAuthenticated();

        // Then
        assertThat(isAuthenticated).isFalse();
    }

    @Test
    @DisplayName("Should return false when authentication is not authenticated")
    public void isAuthenticated_NotAuthenticated_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(false);

        // When
        boolean isAuthenticated = SecurityUtils.isAuthenticated();

        // Then
        assertThat(isAuthenticated).isFalse();
    }

    @Test
    @DisplayName("Should return false when principal is anonymousUser")
    public void isAuthenticated_AnonymousUser_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getPrincipal()).thenReturn("anonymousUser");

        // When
        boolean isAuthenticated = SecurityUtils.isAuthenticated();

        // Then
        assertThat(isAuthenticated).isFalse();
    }

    @Test
    @DisplayName("Should return true when user is authenticated and not anonymous")
    public void isAuthenticated_AuthenticatedUser_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getPrincipal()).thenReturn("testuser");

        // When
        boolean isAuthenticated = SecurityUtils.isAuthenticated();

        // Then
        assertThat(isAuthenticated).isTrue();
    }

    @Test
    @DisplayName("Should generate a secure random string of the specified length")
    public void generateSecureRandomString_SpecifiedLength_ReturnsStringOfCorrectLength() {
        // When
        String randomString = SecurityUtils.generateSecureRandomString(16);

        // Then
        assertThat(randomString).isNotNull();
        // Base64 encoding can make the string slightly longer, so we check it's at least the requested length
        assertThat(randomString.length()).isGreaterThanOrEqualTo(16);
    }

    @Test
    @DisplayName("Should generate different secure random strings on multiple calls")
    public void generateSecureRandomString_MultipleCalls_ReturnsDifferentStrings() {
        // When
        String randomString1 = SecurityUtils.generateSecureRandomString(16);
        String randomString2 = SecurityUtils.generateSecureRandomString(16);

        // Then
        assertThat(randomString1).isNotEqualTo(randomString2);
    }

    @Test
    @DisplayName("Should generate a secure token")
    public void generateSecureToken_Called_ReturnsToken() {
        // When
        String token = SecurityUtils.generateSecureToken();

        // Then
        assertThat(token).isNotNull();
        assertThat(token.length()).isGreaterThan(0);
    }

    @Test
    @DisplayName("Should generate different secure tokens on multiple calls")
    public void generateSecureToken_MultipleCalls_ReturnsDifferentTokens() {
        // When
        String token1 = SecurityUtils.generateSecureToken();
        String token2 = SecurityUtils.generateSecureToken();

        // Then
        assertThat(token1).isNotEqualTo(token2);
    }

    @Test
    @DisplayName("Should generate a secure password of the specified length")
    public void generateSecurePassword_SpecifiedLength_ReturnsPasswordOfCorrectLength() {
        // When
        String password = SecurityUtils.generateSecurePassword(12);

        // Then
        assertThat(password).isNotNull();
        assertThat(password.length()).isEqualTo(12);
    }

    @Test
    @DisplayName("Should generate a secure password with at least one uppercase, lowercase, digit, and special character")
    public void generateSecurePassword_Called_ReturnsPasswordWithRequiredCharacters() {
        // When
        String password = SecurityUtils.generateSecurePassword(12);

        // Then
        assertThat(password).isNotNull();
        assertThat(password).matches(".*[A-Z].*"); // At least one uppercase letter
        assertThat(password).matches(".*[a-z].*"); // At least one lowercase letter
        assertThat(password).matches(".*\\d.*"); // At least one digit
        assertThat(password).matches(".*[!@#$%^&*()_\\-+=<>?].*"); // At least one special character
    }

    @Test
    @DisplayName("Should generate different secure passwords on multiple calls")
    public void generateSecurePassword_MultipleCalls_ReturnsDifferentPasswords() {
        // When
        String password1 = SecurityUtils.generateSecurePassword(12);
        String password2 = SecurityUtils.generateSecurePassword(12);

        // Then
        assertThat(password1).isNotEqualTo(password2);
    }

    @Test
    @DisplayName("Should sanitize a sensitive string for logging")
    public void sanitizeForLogging_SensitiveString_ReturnsSanitizedString() {
        // When
        String sanitized = SecurityUtils.sanitizeForLogging("password123");

        // Then
        assertThat(sanitized).isEqualTo("p*******3");
    }

    @Test
    @DisplayName("Should handle null input for sanitizeForLogging")
    public void sanitizeForLogging_NullInput_ReturnsNullPlaceholder() {
        // When
        String sanitized = SecurityUtils.sanitizeForLogging(null);

        // Then
        assertThat(sanitized).isEqualTo("[null]");
    }

    @Test
    @DisplayName("Should handle short strings for sanitizeForLogging")
    public void sanitizeForLogging_ShortString_ReturnsAsterisks() {
        // When
        String sanitized = SecurityUtils.sanitizeForLogging("ab");

        // Then
        assertThat(sanitized).isEqualTo("**");
    }

    @Test
    @DisplayName("Should return true for System Admin when checking application access")
    public void hasApplicationAccess_SystemAdmin_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority(SecurityUtils.ROLE_SYSTEM_ADMIN)));

        // When
        boolean hasAccess = SecurityUtils.hasApplicationAccess(123L);

        // Then
        assertThat(hasAccess).isTrue();
    }

    @Test
    @DisplayName("Should return true for Operations Staff when checking application access")
    public void hasApplicationAccess_OperationsStaff_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority(SecurityUtils.ROLE_OPERATIONS_STAFF)));

        // When
        boolean hasAccess = SecurityUtils.hasApplicationAccess(123L);

        // Then
        assertThat(hasAccess).isTrue();
    }

    @Test
    @DisplayName("Should return false for regular user when checking application access")
    public void hasApplicationAccess_RegularUser_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);
        when(authentication.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));

        // When
        boolean hasAccess = SecurityUtils.hasApplicationAccess(123L);

        // Then
        assertThat(hasAccess).isFalse();
    }

    @Test
    @DisplayName("Should return true when session is valid")
    public void isValidSession_ValidSession_ReturnsTrue() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(true);

        // When
        boolean isValid = SecurityUtils.isValidSession();

        // Then
        assertThat(isValid).isTrue();
    }

    @Test
    @DisplayName("Should return false when no authentication is present for isValidSession")
    public void isValidSession_NoAuthentication_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(null);

        // When
        boolean isValid = SecurityUtils.isValidSession();

        // Then
        assertThat(isValid).isFalse();
    }

    @Test
    @DisplayName("Should return false when authentication is not authenticated for isValidSession")
    public void isValidSession_NotAuthenticated_ReturnsFalse() {
        // Given
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.isAuthenticated()).thenReturn(false);

        // When
        boolean isValid = SecurityUtils.isValidSession();

        // Then
        assertThat(isValid).isFalse();
    }

    @Test
    @DisplayName("Should return client IP address")
    public void getClientIpAddress_Called_ReturnsIpAddress() {
        // When
        String ipAddress = SecurityUtils.getClientIpAddress();

        // Then
        assertThat(ipAddress).isNotNull();
    }
}