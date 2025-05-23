package com.dollarfunding.mca.security;

import io.jsonwebtoken.JwtException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.User;
import org.springframework.test.util.ReflectionTestUtils;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Test class for {@link JwtAuthenticationFilter} that verifies the correct extraction of JWT tokens
 * from the Authorization header, validation of tokens using JwtTokenProvider, and setting of
 * authentication in the SecurityContext.
 * <p>
 * This test ensures that the authentication filter properly authenticates requests before they
 * reach protected endpoints, handling various scenarios including valid tokens, invalid tokens,
 * expired tokens, and missing tokens.
 */
@ExtendWith(MockitoExtension.class)
public class JwtAuthenticationFilterTest {

    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";
    private static final String TEST_USERNAME = "testuser";
    private static final String VALID_TOKEN = "valid.jwt.token";
    private static final String INVALID_TOKEN = "invalid.jwt.token";
    private static final String EXPIRED_TOKEN = "expired.jwt.token";
    private static final String REFRESH_TOKEN = "refresh.jwt.token";

    @Mock
    private JwtTokenProvider tokenProvider;

    @Mock
    private UserDetailsServiceImpl userDetailsService;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @Mock
    private FilterChain filterChain;

    @Mock
    private SecurityContext securityContext;

    @Mock
    private Logger mockLogger;

    private JwtAuthenticationFilter jwtAuthenticationFilter;
    private Authentication authentication;

    @BeforeEach
    public void setUp() {
        // Create filter with mocked dependencies
        jwtAuthenticationFilter = new JwtAuthenticationFilter(tokenProvider, userDetailsService);
        
        // Inject mock logger
        ReflectionTestUtils.setField(jwtAuthenticationFilter, "logger", mockLogger);
        
        // Set up SecurityContextHolder with mock SecurityContext
        SecurityContextHolder.setContext(securityContext);
        
        // Create authentication object with test user and authorities
        User principal = new User(TEST_USERNAME, "", 
                Collections.singletonList(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)));
        authentication = new UsernamePasswordAuthenticationToken(
                principal, VALID_TOKEN, principal.getAuthorities());
        
        // Configure token provider mock for different token types
        when(tokenProvider.validateToken(VALID_TOKEN)).thenReturn(true);
        when(tokenProvider.validateToken(INVALID_TOKEN)).thenReturn(false);
        when(tokenProvider.validateToken(EXPIRED_TOKEN)).thenThrow(new JwtException("Token expired"));
        when(tokenProvider.validateToken(REFRESH_TOKEN)).thenReturn(true);
        
        when(tokenProvider.isAccessToken(VALID_TOKEN)).thenReturn(true);
        when(tokenProvider.isAccessToken(INVALID_TOKEN)).thenReturn(true);
        when(tokenProvider.isAccessToken(EXPIRED_TOKEN)).thenReturn(true);
        when(tokenProvider.isAccessToken(REFRESH_TOKEN)).thenReturn(false);
        
        when(tokenProvider.getAuthentication(VALID_TOKEN)).thenReturn(authentication);
    }

    /**
     * Test that the filter correctly extracts JWT token from the Authorization header.
     */
    @Test
    public void testExtractJwtFromRequest_WithValidToken_ShouldExtractToken() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(BEARER_PREFIX + VALID_TOKEN);
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(tokenProvider).validateToken(VALID_TOKEN);
        verify(tokenProvider).isAccessToken(VALID_TOKEN);
        verify(tokenProvider).getAuthentication(VALID_TOKEN);
        verify(securityContext).setAuthentication(authentication);
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles missing Authorization header.
     */
    @Test
    public void testDoFilterInternal_WithMissingAuthHeader_ShouldContinueFilterChain() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(null);
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(tokenProvider, never()).validateToken(anyString());
        verify(tokenProvider, never()).getAuthentication(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles Authorization header without Bearer prefix.
     */
    @Test
    public void testDoFilterInternal_WithoutBearerPrefix_ShouldContinueFilterChain() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(VALID_TOKEN); // Missing Bearer prefix
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(tokenProvider, never()).validateToken(anyString());
        verify(tokenProvider, never()).getAuthentication(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles invalid JWT tokens.
     */
    @Test
    public void testDoFilterInternal_WithInvalidToken_ShouldContinueFilterChain() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(BEARER_PREFIX + INVALID_TOKEN);
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(tokenProvider).validateToken(INVALID_TOKEN);
        verify(tokenProvider, never()).getAuthentication(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(mockLogger).debug(eq("Invalid JWT token"));
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles expired JWT tokens.
     */
    @Test
    public void testDoFilterInternal_WithExpiredToken_ShouldClearContextAndContinueFilterChain() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(BEARER_PREFIX + EXPIRED_TOKEN);
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(tokenProvider).validateToken(EXPIRED_TOKEN);
        verify(tokenProvider, never()).getAuthentication(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(mockLogger).error(eq("JWT authentication failed: {}"), eq("Token expired"));
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles refresh tokens (should not authenticate).
     */
    @Test
    public void testDoFilterInternal_WithRefreshToken_ShouldNotAuthenticate() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(BEARER_PREFIX + REFRESH_TOKEN);
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(tokenProvider).validateToken(REFRESH_TOKEN);
        verify(tokenProvider).isAccessToken(REFRESH_TOKEN);
        verify(tokenProvider, never()).getAuthentication(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(mockLogger).debug(eq("Token is not an access token, skipping authentication"));
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles exceptions during authentication.
     */
    @Test
    public void testDoFilterInternal_WithAuthenticationException_ShouldClearContextAndContinueFilterChain() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(BEARER_PREFIX + VALID_TOKEN);
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        when(tokenProvider.getAuthentication(VALID_TOKEN)).thenThrow(new RuntimeException("Authentication error"));
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(tokenProvider).validateToken(VALID_TOKEN);
        verify(tokenProvider).isAccessToken(VALID_TOKEN);
        verify(tokenProvider).getAuthentication(VALID_TOKEN);
        verify(securityContext, never()).setAuthentication(any());
        verify(mockLogger).error(eq("Cannot set user authentication: {}"), eq("Authentication error"), any(RuntimeException.class));
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the shouldNotFilter method correctly identifies paths that should be excluded from filtering.
     */
    @Test
    public void testShouldNotFilter_WithExcludedPaths_ShouldReturnTrue() {
        // Arrange
        String[] excludedPaths = {
            "/api/auth/login",
            "/api/auth/refresh",
            "/api/public/docs",
            "/api/health",
            "/error"
        };
        
        for (String path : excludedPaths) {
            when(request.getServletPath()).thenReturn(path);
            
            // Act & Assert
            assertTrue(jwtAuthenticationFilter.shouldNotFilter(request), "Path " + path + " should be excluded");
        }
    }

    /**
     * Test that the shouldNotFilter method correctly identifies paths that should be included in filtering.
     */
    @Test
    public void testShouldNotFilter_WithIncludedPaths_ShouldReturnFalse() {
        // Arrange
        String[] includedPaths = {
            "/api/v1/applications",
            "/api/v1/documents",
            "/api/v1/webhooks",
            "/api/admin/users"
        };
        
        for (String path : includedPaths) {
            when(request.getServletPath()).thenReturn(path);
            
            // Act & Assert
            assertFalse(jwtAuthenticationFilter.shouldNotFilter(request), "Path " + path + " should be included");
        }
    }

    /**
     * Test that the filter correctly sets authentication details from the request.
     */
    @Test
    public void testDoFilterInternal_WithValidToken_ShouldSetAuthenticationDetails() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(BEARER_PREFIX + VALID_TOKEN);
        when(request.getServletPath()).thenReturn("/api/v1/applications");
        
        // Create a captor to capture the authentication object
        ArgumentCaptor<Authentication> authCaptor = ArgumentCaptor.forClass(Authentication.class);
        
        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);
        
        // Assert
        verify(securityContext).setAuthentication(authCaptor.capture());
        Authentication capturedAuth = authCaptor.getValue();
        
        assertNotNull(capturedAuth.getDetails(), "Authentication details should not be null");
        verify(mockLogger).debug(eq("Set authentication for user '{}' with roles {}"), 
                eq(TEST_USERNAME), eq(capturedAuth.getAuthorities()));
        verify(filterChain).doFilter(request, response);
    }
}