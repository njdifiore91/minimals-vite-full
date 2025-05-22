package com.dollarfunding.mca.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;

import java.io.IOException;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * Test class for {@link JwtAuthenticationFilter} that verifies the correct extraction of JWT tokens
 * from the Authorization header, validation of tokens using JwtTokenProvider, and setting of
 * authentication in the SecurityContext.
 * <p>
 * This test ensures that the authentication filter properly authenticates requests before they
 * reach protected endpoints.
 */
@ExtendWith(MockitoExtension.class)
public class JwtAuthenticationFilterTest {

    private static final String VALID_TOKEN = "valid_token";
    private static final String INVALID_TOKEN = "invalid_token";
    private static final String EXPIRED_TOKEN = "expired_token";
    private static final String TEST_USERNAME = "testuser";
    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

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
    private UserDetails userDetails;

    @Mock
    private SecurityContext securityContext;

    private JwtAuthenticationFilter jwtAuthenticationFilter;

    @BeforeEach
    public void setUp() {
        jwtAuthenticationFilter = new JwtAuthenticationFilter(tokenProvider, userDetailsService);
        SecurityContextHolder.setContext(securityContext);

        // Configure mock UserDetails
        when(userDetails.getUsername()).thenReturn(TEST_USERNAME);
        when(userDetails.getAuthorities()).thenReturn(
                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));
    }

    @AfterEach
    public void tearDown() {
        SecurityContextHolder.clearContext();
    }

    /**
     * Test that the filter correctly extracts a valid JWT token from the Authorization header,
     * validates it, and sets the authentication in the SecurityContext.
     */
    @Test
    public void testDoFilterInternal_WithValidToken_ShouldSetAuthentication() throws ServletException, IOException {
        // Arrange
        mockRequestWithToken(VALID_TOKEN);
        mockTokenValidation(VALID_TOKEN, true);
        mockUserDetailsLoading(TEST_USERNAME);

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(tokenProvider).validateToken(VALID_TOKEN);
        verify(tokenProvider).getUsernameFromToken(VALID_TOKEN);
        verify(userDetailsService).loadUserByUsername(TEST_USERNAME);
        verify(securityContext).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles an invalid JWT token by not setting the authentication
     * in the SecurityContext but still continuing the filter chain.
     */
    @Test
    public void testDoFilterInternal_WithInvalidToken_ShouldNotSetAuthentication() throws ServletException, IOException {
        // Arrange
        mockRequestWithToken(INVALID_TOKEN);
        mockTokenValidation(INVALID_TOKEN, false);

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(tokenProvider).validateToken(INVALID_TOKEN);
        verify(tokenProvider, never()).getUsernameFromToken(anyString());
        verify(userDetailsService, never()).loadUserByUsername(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles an expired JWT token by not setting the authentication
     * in the SecurityContext but still continuing the filter chain.
     */
    @Test
    public void testDoFilterInternal_WithExpiredToken_ShouldNotSetAuthentication() throws ServletException, IOException {
        // Arrange
        mockRequestWithToken(EXPIRED_TOKEN);
        when(tokenProvider.validateToken(EXPIRED_TOKEN)).thenThrow(new io.jsonwebtoken.ExpiredJwtException(null, null, "Token expired"));

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(tokenProvider).validateToken(EXPIRED_TOKEN);
        verify(tokenProvider, never()).getUsernameFromToken(anyString());
        verify(userDetailsService, never()).loadUserByUsername(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles a missing JWT token by not setting the authentication
     * in the SecurityContext but still continuing the filter chain.
     */
    @Test
    public void testDoFilterInternal_WithMissingToken_ShouldNotSetAuthentication() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(null);

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(tokenProvider, never()).validateToken(anyString());
        verify(tokenProvider, never()).getUsernameFromToken(anyString());
        verify(userDetailsService, never()).loadUserByUsername(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles a malformed Authorization header (without Bearer prefix)
     * by not setting the authentication in the SecurityContext but still continuing the filter chain.
     */
    @Test
    public void testDoFilterInternal_WithMalformedAuthorizationHeader_ShouldNotSetAuthentication() throws ServletException, IOException {
        // Arrange
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(VALID_TOKEN); // Missing Bearer prefix

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(tokenProvider, never()).validateToken(anyString());
        verify(tokenProvider, never()).getUsernameFromToken(anyString());
        verify(userDetailsService, never()).loadUserByUsername(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles exceptions during token validation by not setting the
     * authentication in the SecurityContext but still continuing the filter chain.
     */
    @Test
    public void testDoFilterInternal_WithExceptionDuringValidation_ShouldNotSetAuthentication() throws ServletException, IOException {
        // Arrange
        mockRequestWithToken(VALID_TOKEN);
        when(tokenProvider.validateToken(VALID_TOKEN)).thenThrow(new RuntimeException("Validation error"));

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(tokenProvider).validateToken(VALID_TOKEN);
        verify(tokenProvider, never()).getUsernameFromToken(anyString());
        verify(userDetailsService, never()).loadUserByUsername(anyString());
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly handles exceptions during user details loading by not setting the
     * authentication in the SecurityContext but still continuing the filter chain.
     */
    @Test
    public void testDoFilterInternal_WithExceptionDuringUserDetailsLoading_ShouldNotSetAuthentication() throws ServletException, IOException {
        // Arrange
        mockRequestWithToken(VALID_TOKEN);
        mockTokenValidation(VALID_TOKEN, true);
        when(tokenProvider.getUsernameFromToken(VALID_TOKEN)).thenReturn(TEST_USERNAME);
        when(userDetailsService.loadUserByUsername(TEST_USERNAME)).thenThrow(new RuntimeException("User not found"));

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(tokenProvider).validateToken(VALID_TOKEN);
        verify(tokenProvider).getUsernameFromToken(VALID_TOKEN);
        verify(userDetailsService).loadUserByUsername(TEST_USERNAME);
        verify(securityContext, never()).setAuthentication(any());
        verify(filterChain).doFilter(request, response);
    }

    /**
     * Test that the filter correctly sets the authentication with the proper authorities in the
     * SecurityContext for a valid token.
     */
    @Test
    public void testDoFilterInternal_WithValidToken_ShouldSetAuthenticationWithCorrectAuthorities() throws ServletException, IOException {
        // Arrange
        mockRequestWithToken(VALID_TOKEN);
        mockTokenValidation(VALID_TOKEN, true);
        mockUserDetailsLoading(TEST_USERNAME);

        ArgumentCaptor<Authentication> authenticationCaptor = ArgumentCaptor.forClass(Authentication.class);

        // Act
        jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

        // Assert
        verify(securityContext).setAuthentication(authenticationCaptor.capture());
        Authentication authentication = authenticationCaptor.getValue();
        assertNotNull(authentication);
        assertEquals(userDetails, authentication.getPrincipal());
        assertTrue(authentication.getAuthorities().contains(new SimpleGrantedAuthority("ROLE_USER")));
    }

    /**
     * Helper method to mock a request with an Authorization header containing a JWT token.
     *
     * @param token the JWT token to include in the Authorization header
     */
    private void mockRequestWithToken(String token) {
        when(request.getHeader(AUTHORIZATION_HEADER)).thenReturn(BEARER_PREFIX + token);
    }

    /**
     * Helper method to mock token validation.
     *
     * @param token the JWT token to validate
     * @param isValid whether the token is valid
     */
    private void mockTokenValidation(String token, boolean isValid) {
        when(tokenProvider.validateToken(token)).thenReturn(isValid);
        if (isValid) {
            when(tokenProvider.getUsernameFromToken(token)).thenReturn(TEST_USERNAME);
        }
    }

    /**
     * Helper method to mock user details loading.
     *
     * @param username the username to load user details for
     */
    private void mockUserDetailsLoading(String username) {
        when(userDetailsService.loadUserByUsername(username)).thenReturn(userDetails);
    }
}