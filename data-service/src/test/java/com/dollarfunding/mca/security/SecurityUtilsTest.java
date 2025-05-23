package com.dollarfunding.mca.security;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.TestingAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import javax.servlet.http.HttpServletRequest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * Test class for {@link SecurityUtils} that verifies the correct implementation of security-related utility methods.
 * It tests retrieving the current authenticated user, checking authorities, generating secure random values,
 * and handling security-related conversions.
 */
@ExtendWith(MockitoExtension.class)
public class SecurityUtilsTest {

    @Mock
    private SecurityContext securityContext;
    
    @Mock
    private Authentication authentication;
    
    @Mock
    private HttpServletRequest request;
    
    @Mock
    private Logger mockLogger;
    
    private UserPrincipal userPrincipal;
    
    @BeforeEach
    void setUp() {
        // Create a test UserPrincipal with both roles
        List<SimpleGrantedAuthority> authorities = Arrays.asList(
                new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF),
                new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
        );
        
        userPrincipal = UserPrincipal.builder()
                .id(1L)
                .username("testuser")
                .email("test@dollarfunding.com")
                .password("encodedPassword")
                .authorities(authorities)
                .firstName("Test")
                .lastName("User")
                .build();
    }
    
    @AfterEach
    void tearDown() {
        // Clear the security context after each test
        SecurityContextHolder.clearContext();
    }
    
    @Nested
    @DisplayName("Authentication Tests")
    class AuthenticationTests {
        
        @Test
        @DisplayName("getCurrentAuthentication should return empty when not authenticated")
        void getCurrentAuthenticationShouldReturnEmptyWhenNotAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(null);
            
            // Execute
            Optional<Authentication> result = SecurityUtils.getCurrentAuthentication();
            
            // Verify
            assertFalse(result.isPresent());
        }
        
        @Test
        @DisplayName("getCurrentAuthentication should return empty for anonymous authentication")
        void getCurrentAuthenticationShouldReturnEmptyForAnonymousAuthentication() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            AnonymousAuthenticationToken anonymousToken = new AnonymousAuthenticationToken(
                    "key", "anonymousUser", Collections.singletonList(new SimpleGrantedAuthority("ROLE_ANONYMOUS")));
            when(securityContext.getAuthentication()).thenReturn(anonymousToken);
            
            // Execute
            Optional<Authentication> result = SecurityUtils.getCurrentAuthentication();
            
            // Verify
            assertFalse(result.isPresent());
        }
        
        @Test
        @DisplayName("getCurrentAuthentication should return authentication when authenticated")
        void getCurrentAuthenticationShouldReturnAuthenticationWhenAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            
            // Execute
            Optional<Authentication> result = SecurityUtils.getCurrentAuthentication();
            
            // Verify
            assertTrue(result.isPresent());
            assertEquals(authentication, result.get());
        }
        
        @Test
        @DisplayName("getCurrentUserPrincipal should return empty when not authenticated")
        void getCurrentUserPrincipalShouldReturnEmptyWhenNotAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(null);
            
            // Execute
            Optional<UserPrincipal> result = SecurityUtils.getCurrentUserPrincipal();
            
            // Verify
            assertFalse(result.isPresent());
        }
        
        @Test
        @DisplayName("getCurrentUserPrincipal should return user principal when authenticated")
        void getCurrentUserPrincipalShouldReturnUserPrincipalWhenAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getPrincipal()).thenReturn(userPrincipal);
            
            // Execute
            Optional<UserPrincipal> result = SecurityUtils.getCurrentUserPrincipal();
            
            // Verify
            assertTrue(result.isPresent());
            assertEquals(userPrincipal, result.get());
        }
        
        @Test
        @DisplayName("getCurrentUserId should return empty when not authenticated")
        void getCurrentUserIdShouldReturnEmptyWhenNotAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(null);
            
            // Execute
            Optional<Long> result = SecurityUtils.getCurrentUserId();
            
            // Verify
            assertFalse(result.isPresent());
        }
        
        @Test
        @DisplayName("getCurrentUserId should return user ID when authenticated")
        void getCurrentUserIdShouldReturnUserIdWhenAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getPrincipal()).thenReturn(userPrincipal);
            
            // Execute
            Optional<Long> result = SecurityUtils.getCurrentUserId();
            
            // Verify
            assertTrue(result.isPresent());
            assertEquals(1L, result.get());
        }
        
        @Test
        @DisplayName("getCurrentUsername should return empty when not authenticated")
        void getCurrentUsernameShouldReturnEmptyWhenNotAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(null);
            
            // Execute
            Optional<String> result = SecurityUtils.getCurrentUsername();
            
            // Verify
            assertFalse(result.isPresent());
        }
        
        @Test
        @DisplayName("getCurrentUsername should return username from UserDetails when authenticated")
        void getCurrentUsernameShouldReturnUsernameFromUserDetailsWhenAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getPrincipal()).thenReturn(userPrincipal);
            
            // Execute
            Optional<String> result = SecurityUtils.getCurrentUsername();
            
            // Verify
            assertTrue(result.isPresent());
            assertEquals("testuser", result.get());
        }
        
        @Test
        @DisplayName("getCurrentUsername should return username from String principal when authenticated")
        void getCurrentUsernameShouldReturnUsernameFromStringPrincipalWhenAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getPrincipal()).thenReturn("stringUsername");
            
            // Execute
            Optional<String> result = SecurityUtils.getCurrentUsername();
            
            // Verify
            assertTrue(result.isPresent());
            assertEquals("stringUsername", result.get());
        }
        
        @Test
        @DisplayName("isAuthenticated should return false when not authenticated")
        void isAuthenticatedShouldReturnFalseWhenNotAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(null);
            
            // Execute & Verify
            assertFalse(SecurityUtils.isAuthenticated());
        }
        
        @Test
        @DisplayName("isAuthenticated should return true when authenticated")
        void isAuthenticatedShouldReturnTrueWhenAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            
            // Execute & Verify
            assertTrue(SecurityUtils.isAuthenticated());
        }
    }
    
    @Nested
    @DisplayName("Authorization Tests")
    class AuthorizationTests {
        
        @Test
        @DisplayName("hasAuthority should return false when not authenticated")
        void hasAuthorityShouldReturnFalseWhenNotAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(null);
            
            // Execute & Verify
            assertFalse(SecurityUtils.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
        }
        
        @Test
        @DisplayName("hasAuthority should return true when user has the authority")
        void hasAuthorityShouldReturnTrueWhenUserHasAuthority() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Arrays.asList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF),
                    new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
            ));
            
            // Execute & Verify
            assertTrue(SecurityUtils.hasAuthority(RoleConstants.ROLE_OPERATIONS_STAFF));
        }
        
        @Test
        @DisplayName("hasAuthority should return false when user doesn't have the authority")
        void hasAuthorityShouldReturnFalseWhenUserDoesNotHaveAuthority() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Collections.singletonList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)
            ));
            
            // Execute & Verify
            assertFalse(SecurityUtils.hasAuthority("ROLE_UNKNOWN"));
        }
        
        @Test
        @DisplayName("hasRole should return false when not authenticated")
        void hasRoleShouldReturnFalseWhenNotAuthenticated() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(null);
            
            // Execute & Verify
            assertFalse(SecurityUtils.hasRole(RoleConstants.OPERATIONS_STAFF));
        }
        
        @Test
        @DisplayName("hasRole should return true when user has the role")
        void hasRoleShouldReturnTrueWhenUserHasRole() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Arrays.asList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF),
                    new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
            ));
            
            // Execute & Verify
            assertTrue(SecurityUtils.hasRole(RoleConstants.OPERATIONS_STAFF));
        }
        
        @Test
        @DisplayName("hasRole should handle role with or without prefix")
        void hasRoleShouldHandleRoleWithOrWithoutPrefix() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Arrays.asList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF),
                    new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
            ));
            
            // Execute & Verify - with prefix
            assertTrue(SecurityUtils.hasRole(RoleConstants.ROLE_OPERATIONS_STAFF));
            
            // Execute & Verify - without prefix
            assertTrue(SecurityUtils.hasRole(RoleConstants.OPERATIONS_STAFF));
        }
        
        @Test
        @DisplayName("isOperationsStaff should return true when user has Operations Staff role")
        void isOperationsStaffShouldReturnTrueWhenUserHasOperationsStaffRole() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Collections.singletonList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)
            ));
            
            // Execute & Verify
            assertTrue(SecurityUtils.isOperationsStaff());
        }
        
        @Test
        @DisplayName("isOperationsStaff should return false when user doesn't have Operations Staff role")
        void isOperationsStaffShouldReturnFalseWhenUserDoesNotHaveOperationsStaffRole() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Collections.singletonList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
            ));
            
            // Execute & Verify
            assertFalse(SecurityUtils.isOperationsStaff());
        }
        
        @Test
        @DisplayName("isSystemAdmin should return true when user has System Admin role")
        void isSystemAdminShouldReturnTrueWhenUserHasSystemAdminRole() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Collections.singletonList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
            ));
            
            // Execute & Verify
            assertTrue(SecurityUtils.isSystemAdmin());
        }
        
        @Test
        @DisplayName("isSystemAdmin should return false when user doesn't have System Admin role")
        void isSystemAdminShouldReturnFalseWhenUserDoesNotHaveSystemAdminRole() {
            // Setup
            SecurityContextHolder.setContext(securityContext);
            when(securityContext.getAuthentication()).thenReturn(authentication);
            when(authentication.isAuthenticated()).thenReturn(true);
            when(authentication.getAuthorities()).thenReturn(Collections.singletonList(
                    new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)
            ));
            
            // Execute & Verify
            assertFalse(SecurityUtils.isSystemAdmin());
        }
        
        @Test
        @DisplayName("hasResourceAccess should return true for System Admin regardless of required role")
        void hasResourceAccessShouldReturnTrueForSystemAdminRegardlessOfRequiredRole() {
            // Setup - mock static method isSystemAdmin
            try (MockedStatic<SecurityUtils> mockedSecurityUtils = mockStatic(SecurityUtils.class)) {
                mockedSecurityUtils.when(SecurityUtils::isSystemAdmin).thenReturn(true);
                mockedSecurityUtils.when(() -> SecurityUtils.hasResourceAccess(anyString()))
                        .thenCallRealMethod();
                
                // Execute & Verify
                assertTrue(SecurityUtils.hasResourceAccess("ANY_ROLE"));
            }
        }
        
        @Test
        @DisplayName("hasResourceAccess should check specific role when not System Admin")
        void hasResourceAccessShouldCheckSpecificRoleWhenNotSystemAdmin() {
            // Setup - mock static methods
            try (MockedStatic<SecurityUtils> mockedSecurityUtils = mockStatic(SecurityUtils.class)) {
                mockedSecurityUtils.when(SecurityUtils::isSystemAdmin).thenReturn(false);
                mockedSecurityUtils.when(() -> SecurityUtils.hasRole("REQUIRED_ROLE")).thenReturn(true);
                mockedSecurityUtils.when(() -> SecurityUtils.hasResourceAccess("REQUIRED_ROLE"))
                        .thenCallRealMethod();
                
                // Execute & Verify
                assertTrue(SecurityUtils.hasResourceAccess("REQUIRED_ROLE"));
            }
        }
    }
    
    @Nested
    @DisplayName("Password and Token Generation Tests")
    class PasswordAndTokenGenerationTests {
        
        @Test
        @DisplayName("generateSecurePassword should throw exception for length less than 8")
        void generateSecurePasswordShouldThrowExceptionForLengthLessThan8() {
            // Execute & Verify
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class,
                    () -> SecurityUtils.generateSecurePassword(7));
            assertEquals("Password length must be at least 8 characters", exception.getMessage());
        }
        
        @ParameterizedTest
        @ValueSource(ints = {8, 12, 16, 20})
        @DisplayName("generateSecurePassword should generate password with correct length")
        void generateSecurePasswordShouldGeneratePasswordWithCorrectLength(int length) {
            // Execute
            String password = SecurityUtils.generateSecurePassword(length);
            
            // Verify
            assertEquals(length, password.length());
        }
        
        @Test
        @DisplayName("generateSecurePassword should include required character types")
        void generateSecurePasswordShouldIncludeRequiredCharacterTypes() {
            // Execute
            String password = SecurityUtils.generateSecurePassword(12);
            
            // Verify
            assertTrue(Pattern.compile("[A-Z]").matcher(password).find(), "Password should contain uppercase letters");
            assertTrue(Pattern.compile("[a-z]").matcher(password).find(), "Password should contain lowercase letters");
            assertTrue(Pattern.compile("[0-9]").matcher(password).find(), "Password should contain numbers");
            assertTrue(Pattern.compile("[!@#$%^&*()_\-+=<>?]").matcher(password).find(), "Password should contain special characters");
        }
        
        @Test
        @DisplayName("encodePassword should use BCrypt encoder")
        void encodePasswordShouldUseBCryptEncoder() {
            // Execute
            String encoded = SecurityUtils.encodePassword("password");
            
            // Verify
            assertTrue(encoded.startsWith("$2a$"), "Encoded password should use BCrypt format");
        }
        
        @Test
        @DisplayName("matchesPassword should return true for matching passwords")
        void matchesPasswordShouldReturnTrueForMatchingPasswords() {
            // Setup
            String rawPassword = "testPassword";
            String encodedPassword = SecurityUtils.encodePassword(rawPassword);
            
            // Execute & Verify
            assertTrue(SecurityUtils.matchesPassword(rawPassword, encodedPassword));
        }
        
        @Test
        @DisplayName("matchesPassword should return false for non-matching passwords")
        void matchesPasswordShouldReturnFalseForNonMatchingPasswords() {
            // Setup
            String rawPassword = "testPassword";
            String wrongPassword = "wrongPassword";
            String encodedPassword = SecurityUtils.encodePassword(rawPassword);
            
            // Execute & Verify
            assertFalse(SecurityUtils.matchesPassword(wrongPassword, encodedPassword));
        }
        
        @Test
        @DisplayName("generateSecureToken should generate token with correct length")
        void generateSecureTokenShouldGenerateTokenWithCorrectLength() {
            // Execute
            String token = SecurityUtils.generateSecureToken(32);
            
            // Verify - Base64 encoding will make the string longer than the byte length
            byte[] decodedToken = Base64.getUrlDecoder().decode(token);
            assertEquals(32, decodedToken.length);
        }
        
        @Test
        @DisplayName("generateSecureUuid should generate valid UUID")
        void generateSecureUuidShouldGenerateValidUuid() {
            // Execute
            String uuid = SecurityUtils.generateSecureUuid();
            
            // Verify
            assertDoesNotThrow(() -> UUID.fromString(uuid));
        }
        
        @Test
        @DisplayName("generateAesKey should throw exception for invalid key size")
        void generateAesKeyShouldThrowExceptionForInvalidKeySize() {
            // Execute & Verify
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class,
                    () -> SecurityUtils.generateAesKey(64));
            assertEquals("Key size must be 128, 192, or 256 bits", exception.getMessage());
        }
        
        @ParameterizedTest
        @ValueSource(ints = {128, 192, 256})
        @DisplayName("generateAesKey should generate key with correct size")
        void generateAesKeyShouldGenerateKeyWithCorrectSize(int keySize) throws NoSuchAlgorithmException {
            // Execute
            String encodedKey = SecurityUtils.generateAesKey(keySize);
            
            // Verify
            byte[] keyBytes = Base64.getDecoder().decode(encodedKey);
            SecretKey secretKey = new SecretKeySpec(keyBytes, "AES");
            assertEquals(keySize / 8, secretKey.getEncoded().length);
        }
    }
    
    @Nested
    @DisplayName("HTTP Request Tests")
    class HttpRequestTests {
        
        @Test
        @DisplayName("extractJwtFromRequest should return empty when Authorization header is missing")
        void extractJwtFromRequestShouldReturnEmptyWhenAuthorizationHeaderIsMissing() {
            // Setup
            when(request.getHeader("Authorization")).thenReturn(null);
            
            // Execute
            Optional<String> result = SecurityUtils.extractJwtFromRequest(request);
            
            // Verify
            assertFalse(result.isPresent());
        }
        
        @Test
        @DisplayName("extractJwtFromRequest should return empty when Authorization header doesn't start with Bearer")
        void extractJwtFromRequestShouldReturnEmptyWhenAuthorizationHeaderDoesntStartWithBearer() {
            // Setup
            when(request.getHeader("Authorization")).thenReturn("Basic dXNlcjpwYXNzd29yZA==");
            
            // Execute
            Optional<String> result = SecurityUtils.extractJwtFromRequest(request);
            
            // Verify
            assertFalse(result.isPresent());
        }
        
        @Test
        @DisplayName("extractJwtFromRequest should return token when Authorization header is valid")
        void extractJwtFromRequestShouldReturnTokenWhenAuthorizationHeaderIsValid() {
            // Setup
            String token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U";
            when(request.getHeader("Authorization")).thenReturn("Bearer " + token);
            
            // Execute
            Optional<String> result = SecurityUtils.extractJwtFromRequest(request);
            
            // Verify
            assertTrue(result.isPresent());
            assertEquals(token, result.get());
        }
        
        @Test
        @DisplayName("getClientIpAddress should return X-Forwarded-For header when present")
        void getClientIpAddressShouldReturnXForwardedForHeaderWhenPresent() {
            // Setup
            when(request.getHeader("X-Forwarded-For")).thenReturn("192.168.1.1, 10.0.0.1");
            
            // Execute
            String result = SecurityUtils.getClientIpAddress(request);
            
            // Verify
            assertEquals("192.168.1.1", result);
        }
        
        @Test
        @DisplayName("getClientIpAddress should return remote address when X-Forwarded-For is not present")
        void getClientIpAddressShouldReturnRemoteAddressWhenXForwardedForIsNotPresent() {
            // Setup
            when(request.getHeader("X-Forwarded-For")).thenReturn(null);
            when(request.getRemoteAddr()).thenReturn("192.168.1.2");
            
            // Execute
            String result = SecurityUtils.getClientIpAddress(request);
            
            // Verify
            assertEquals("192.168.1.2", result);
        }
    }
    
    @Nested
    @DisplayName("Logging and Security Event Tests")
    class LoggingAndSecurityEventTests {
        
        @Test
        @DisplayName("logSecurityEvent should log message with user information when authenticated")
        void logSecurityEventShouldLogMessageWithUserInformationWhenAuthenticated() {
            // Setup - mock static methods
            try (MockedStatic<SecurityUtils> mockedSecurityUtils = mockStatic(SecurityUtils.class)) {
                mockedSecurityUtils.when(() -> SecurityUtils.getCurrentUsername())
                        .thenReturn(Optional.of("testuser"));
                mockedSecurityUtils.when(() -> SecurityUtils.getClientIpAddress(request))
                        .thenReturn("192.168.1.1");
                
                // Need to call the real method for logSecurityEvent
                mockedSecurityUtils.when(() -> SecurityUtils.logSecurityEvent(anyString(), any(HttpServletRequest.class)))
                        .thenCallRealMethod();
                
                // Mock the logger
                try (MockedStatic<org.slf4j.LoggerFactory> mockedLoggerFactory = mockStatic(org.slf4j.LoggerFactory.class)) {
                    mockedLoggerFactory.when(() -> org.slf4j.LoggerFactory.getLogger(SecurityUtils.class))
                            .thenReturn(mockLogger);
                    
                    // Setup request mock
                    when(request.getMethod()).thenReturn("GET");
                    when(request.getRequestURI()).thenReturn("/api/applications");
                    
                    // Execute
                    SecurityUtils.logSecurityEvent("Test security event", request);
                    
                    // Verify
                    ArgumentCaptor<String> messageCaptor = ArgumentCaptor.forClass(String.class);
                    ArgumentCaptor<String> logCaptor = ArgumentCaptor.forClass(String.class);
                    verify(mockLogger).info(messageCaptor.capture(), logCaptor.capture());
                    
                    String capturedMessage = messageCaptor.getValue();
                    String capturedLog = logCaptor.getValue();
                    
                    assertEquals("SECURITY EVENT: {}", capturedMessage);
                    assertTrue(capturedLog.contains("Test security event"));
                    assertTrue(capturedLog.contains("User: testuser"));
                    assertTrue(capturedLog.contains("IP: 192.168.1.1"));
                    assertTrue(capturedLog.contains("Method: GET"));
                    assertTrue(capturedLog.contains("URI: /api/applications"));
                }
            }
        }
        
        @Test
        @DisplayName("logSecurityViolation should log warning with user information when authenticated")
        void logSecurityViolationShouldLogWarningWithUserInformationWhenAuthenticated() {
            // Setup - mock static methods
            try (MockedStatic<SecurityUtils> mockedSecurityUtils = mockStatic(SecurityUtils.class)) {
                mockedSecurityUtils.when(() -> SecurityUtils.getCurrentUsername())
                        .thenReturn(Optional.of("testuser"));
                mockedSecurityUtils.when(() -> SecurityUtils.getClientIpAddress(request))
                        .thenReturn("192.168.1.1");
                
                // Need to call the real method for logSecurityViolation
                mockedSecurityUtils.when(() -> SecurityUtils.logSecurityViolation(anyString(), any(HttpServletRequest.class)))
                        .thenCallRealMethod();
                
                // Mock the logger
                try (MockedStatic<org.slf4j.LoggerFactory> mockedLoggerFactory = mockStatic(org.slf4j.LoggerFactory.class)) {
                    mockedLoggerFactory.when(() -> org.slf4j.LoggerFactory.getLogger(SecurityUtils.class))
                            .thenReturn(mockLogger);
                    
                    // Setup request mock
                    when(request.getMethod()).thenReturn("POST");
                    when(request.getRequestURI()).thenReturn("/api/admin/users");
                    
                    // Execute
                    SecurityUtils.logSecurityViolation("Unauthorized access attempt", request);
                    
                    // Verify
                    ArgumentCaptor<String> messageCaptor = ArgumentCaptor.forClass(String.class);
                    ArgumentCaptor<String> logCaptor = ArgumentCaptor.forClass(String.class);
                    verify(mockLogger).warn(messageCaptor.capture(), logCaptor.capture());
                    
                    String capturedMessage = messageCaptor.getValue();
                    String capturedLog = logCaptor.getValue();
                    
                    assertEquals("SECURITY VIOLATION: {}", capturedMessage);
                    assertTrue(capturedLog.contains("Unauthorized access attempt"));
                    assertTrue(capturedLog.contains("User: testuser"));
                    assertTrue(capturedLog.contains("IP: 192.168.1.1"));
                    assertTrue(capturedLog.contains("Method: POST"));
                    assertTrue(capturedLog.contains("URI: /api/admin/users"));
                }
            }
        }
        
        @Test
        @DisplayName("sanitizeForLogging should remove line breaks and control characters")
        void sanitizeForLoggingShouldRemoveLineBreaksAndControlCharacters() {
            // Setup
            String input = "Line 1\nLine 2\rTab\tBell\a";
            
            // Execute
            String result = SecurityUtils.sanitizeForLogging(input);
            
            // Verify
            assertEquals("Line 1 Line 2 Tab Bell ", result);
        }
        
        @Test
        @DisplayName("sanitizeForLogging should handle null input")
        void sanitizeForLoggingShouldHandleNullInput() {
            // Execute & Verify
            assertNull(SecurityUtils.sanitizeForLogging(null));
        }
        
        @Test
        @DisplayName("maskSensitiveData should mask middle characters of string")
        void maskSensitiveDataShouldMaskMiddleCharactersOfString() {
            // Execute
            String result = SecurityUtils.maskSensitiveData("1234567890");
            
            // Verify
            assertEquals("12******90", result);
        }
        
        @Test
        @DisplayName("maskSensitiveData should handle short strings")
        void maskSensitiveDataShouldHandleShortStrings() {
            // Execute
            String result = SecurityUtils.maskSensitiveData("123");
            
            // Verify
            assertEquals("****", result);
        }
        
        @Test
        @DisplayName("maskSensitiveData should handle null and empty strings")
        void maskSensitiveDataShouldHandleNullAndEmptyStrings() {
            // Execute & Verify
            assertNull(SecurityUtils.maskSensitiveData(null));
            assertEquals("", SecurityUtils.maskSensitiveData(""));
        }
    }
    
    @Nested
    @DisplayName("Utility Accessor Tests")
    class UtilityAccessorTests {
        
        @Test
        @DisplayName("getPasswordEncoder should return BCryptPasswordEncoder")
        void getPasswordEncoderShouldReturnBCryptPasswordEncoder() {
            // Execute
            PasswordEncoder encoder = SecurityUtils.getPasswordEncoder();
            
            // Verify
            assertNotNull(encoder);
            assertTrue(encoder.encode("password").startsWith("$2a$"));
        }
        
        @Test
        @DisplayName("getSecureRandom should return SecureRandom instance")
        void getSecureRandomShouldReturnSecureRandomInstance() {
            // Execute & Verify
            assertNotNull(SecurityUtils.getSecureRandom());
        }
    }
}