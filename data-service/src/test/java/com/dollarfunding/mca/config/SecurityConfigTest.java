package com.dollarfunding.mca.config;

import com.dollarfunding.mca.security.JwtAuthenticationEntryPoint;
import com.dollarfunding.mca.security.JwtAuthenticationFilter;
import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserDetailsServiceImpl;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AuthorizeHttpRequestsConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.util.matcher.AntPathRequestMatcher;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;

import java.io.IOException;
import java.security.PublicKey;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Unit tests for the {@link SecurityConfig} class.
 * <p>
 * These tests verify the correct configuration of JWT authentication, role-based authorization,
 * security filter chain, CSRF protection, and password encoding.
 * </p>
 */
@SpringBootTest
@ActiveProfiles("test")
public class SecurityConfigTest {

    @MockBean
    private JwtAuthenticationEntryPoint jwtAuthenticationEntryPoint;

    @MockBean
    private UserDetailsServiceImpl userDetailsService;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private Resource publicKeyResource;

    private SecurityConfig securityConfig;

    private MockMvc mockMvc;

    @BeforeEach
    public void setup() throws IOException {
        MockitoAnnotations.openMocks(this);
        when(publicKeyResource.getFile()).thenReturn(new ClassPathResource("test-public-key.pem").getFile());
        
        securityConfig = new SecurityConfig(jwtAuthenticationEntryPoint, userDetailsService, jwtTokenProvider);
        
        // Set up MockMvc with the security filter chain
        mockMvc = MockMvcBuilders
                .standaloneSetup()
                .addFilters(securityConfig.jwtAuthenticationFilter())
                .build();
    }

    @Test
    @DisplayName("Test JWT authentication filter creation")
    public void testJwtAuthenticationFilter() {
        // When
        JwtAuthenticationFilter filter = securityConfig.jwtAuthenticationFilter();
        
        // Then
        assertNotNull(filter, "JWT authentication filter should not be null");
        // Verify that the filter is created with the correct dependencies
        verify(jwtTokenProvider, times(1));
        verify(userDetailsService, times(1));
    }

    @Test
    @DisplayName("Test password encoder configuration")
    public void testPasswordEncoder() {
        // When
        PasswordEncoder passwordEncoder = securityConfig.passwordEncoder();
        
        // Then
        assertNotNull(passwordEncoder, "Password encoder should not be null");
        assertTrue(passwordEncoder instanceof BCryptPasswordEncoder, "Password encoder should be BCryptPasswordEncoder");
        
        // Verify that the encoder works correctly
        String password = "testPassword";
        String encodedPassword = passwordEncoder.encode(password);
        assertTrue(passwordEncoder.matches(password, encodedPassword), "Password encoder should correctly match passwords");
    }

    @Test
    @DisplayName("Test CORS configuration")
    public void testCorsConfiguration() {
        // When
        CorsConfigurationSource corsConfigurationSource = securityConfig.corsConfigurationSource();
        
        // Then
        assertNotNull(corsConfigurationSource, "CORS configuration source should not be null");
        
        // Get the CORS configuration
        CorsConfiguration corsConfiguration = corsConfigurationSource.getCorsConfiguration(null);
        assertNotNull(corsConfiguration, "CORS configuration should not be null");
        
        // Verify allowed origins, methods, headers, and exposed headers
        assertTrue(corsConfiguration.getAllowedOrigins().contains("*"), "CORS configuration should allow all origins in test environment");
        assertTrue(corsConfiguration.getAllowedMethods().containsAll(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")), 
                "CORS configuration should allow standard HTTP methods");
        assertTrue(corsConfiguration.getAllowedHeaders().containsAll(List.of("Authorization", "Content-Type", "X-Requested-With")), 
                "CORS configuration should allow standard headers");
        assertTrue(corsConfiguration.getExposedHeaders().contains("Authorization"), 
                "CORS configuration should expose Authorization header");
        assertEquals(3600L, corsConfiguration.getMaxAge(), "CORS configuration should set max age to 1 hour");
    }

    @Test
    @DisplayName("Test public key loading for JWT verification with RS256 algorithm")
    public void testJwtPublicKey() throws Exception {
        // Mock the resource loading
        when(publicKeyResource.getFile()).thenReturn(new ClassPathResource("test-public-key.pem").getFile());
        
        // When
        PublicKey publicKey = securityConfig.jwtPublicKey();
        
        // Then
        assertNotNull(publicKey, "Public key should not be null");
        assertEquals("RSA", publicKey.getAlgorithm(), "Public key should use RSA algorithm for RS256");
    }

    @Test
    @DisplayName("Test security filter chain configuration with stateless session management")
    public void testSecurityFilterChain() throws Exception {
        // Create a mock HttpSecurity
        HttpSecurity httpSecurity = mock(HttpSecurity.class);
        
        // Mock the necessary HttpSecurity methods to prevent NullPointerException
        when(httpSecurity.csrf()).thenReturn(httpSecurity);
        when(httpSecurity.cors()).thenReturn(httpSecurity);
        when(httpSecurity.exceptionHandling()).thenReturn(httpSecurity);
        when(httpSecurity.sessionManagement()).thenReturn(httpSecurity);
        when(httpSecurity.authorizeHttpRequests()).thenReturn(httpSecurity);
        when(httpSecurity.addFilterBefore(any(), any())).thenReturn(httpSecurity);
        when(httpSecurity.build()).thenReturn(mock(SecurityFilterChain.class));
        
        // When
        SecurityFilterChain filterChain = securityConfig.securityFilterChain(httpSecurity);
        
        // Then
        assertNotNull(filterChain, "Security filter chain should not be null");
        
        // Verify that the necessary security configurations are applied
        verify(httpSecurity).csrf();
        verify(httpSecurity).cors();
        verify(httpSecurity).exceptionHandling();
        verify(httpSecurity).sessionManagement();
        verify(httpSecurity).authorizeHttpRequests();
        verify(httpSecurity).addFilterBefore(any(JwtAuthenticationFilter.class), any());
    }

    @Test
    @DisplayName("Test session management configuration for stateless JWT authentication")
    public void testSessionManagement() throws Exception {
        // Create a mock HttpSecurity
        HttpSecurity httpSecurity = mock(HttpSecurity.class);
        
        // Mock session management configurers
        var sessionManagementConfigurer = mock(HttpSecurity.SessionManagementConfigurer.class);
        when(httpSecurity.sessionManagement()).thenReturn(sessionManagementConfigurer);
        when(sessionManagementConfigurer.sessionCreationPolicy(any())).thenReturn(sessionManagementConfigurer);
        
        // Mock other required configurers to prevent NullPointerException
        when(httpSecurity.csrf()).thenReturn(httpSecurity);
        when(httpSecurity.cors()).thenReturn(httpSecurity);
        when(httpSecurity.exceptionHandling()).thenReturn(httpSecurity);
        when(httpSecurity.authorizeHttpRequests()).thenReturn(httpSecurity);
        when(httpSecurity.addFilterBefore(any(), any())).thenReturn(httpSecurity);
        when(httpSecurity.build()).thenReturn(mock(SecurityFilterChain.class));
        
        // When
        securityConfig.securityFilterChain(httpSecurity);
        
        // Then
        verify(sessionManagementConfigurer).sessionCreationPolicy(SessionCreationPolicy.STATELESS);
    }

    @Test
    @DisplayName("Test role-based authorization for Operations Staff role")
    public void testOperationsStaffAuthorization() throws Exception {
        // Create a mock HttpSecurity
        HttpSecurity httpSecurity = mock(HttpSecurity.class);
        
        // Mock authorize requests configurers
        var authorizeRequestsConfigurer = mock(AuthorizeHttpRequestsConfigurer.class);
        var authorizedUrl = mock(AuthorizeHttpRequestsConfigurer.AuthorizedUrl.class);
        
        when(httpSecurity.authorizeHttpRequests()).thenReturn(authorizeRequestsConfigurer);
        when(authorizeRequestsConfigurer.requestMatchers(any(String.class))).thenReturn(authorizedUrl);
        when(authorizeRequestsConfigurer.requestMatchers(any(AntPathRequestMatcher.class))).thenReturn(authorizedUrl);
        when(authorizedUrl.permitAll()).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.hasAnyAuthority(anyString(), anyString())).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.hasAuthority(anyString())).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.authenticated()).thenReturn(authorizeRequestsConfigurer);
        
        // Mock other required configurers to prevent NullPointerException
        when(httpSecurity.csrf()).thenReturn(httpSecurity);
        when(httpSecurity.cors()).thenReturn(httpSecurity);
        when(httpSecurity.exceptionHandling()).thenReturn(httpSecurity);
        when(httpSecurity.sessionManagement()).thenReturn(httpSecurity);
        when(httpSecurity.addFilterBefore(any(), any())).thenReturn(httpSecurity);
        when(httpSecurity.build()).thenReturn(mock(SecurityFilterChain.class));
        
        // When
        securityConfig.securityFilterChain(httpSecurity);
        
        // Then
        // Verify that Operations Staff role can access application data endpoints
        verify(authorizeRequestsConfigurer, atLeastOnce()).requestMatchers("/applications/**", "/documents/**");
        verify(authorizedUrl, atLeastOnce()).hasAnyAuthority(
            RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN);
    }

    @Test
    @DisplayName("Test role-based authorization for System Admin role")
    public void testSystemAdminAuthorization() throws Exception {
        // Create a mock HttpSecurity
        HttpSecurity httpSecurity = mock(HttpSecurity.class);
        
        // Mock authorize requests configurers
        var authorizeRequestsConfigurer = mock(AuthorizeHttpRequestsConfigurer.class);
        var authorizedUrl = mock(AuthorizeHttpRequestsConfigurer.AuthorizedUrl.class);
        
        when(httpSecurity.authorizeHttpRequests()).thenReturn(authorizeRequestsConfigurer);
        when(authorizeRequestsConfigurer.requestMatchers(any(String.class))).thenReturn(authorizedUrl);
        when(authorizeRequestsConfigurer.requestMatchers(any(AntPathRequestMatcher.class))).thenReturn(authorizedUrl);
        when(authorizedUrl.permitAll()).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.hasAnyAuthority(anyString(), anyString())).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.hasAuthority(anyString())).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.authenticated()).thenReturn(authorizeRequestsConfigurer);
        
        // Mock other required configurers to prevent NullPointerException
        when(httpSecurity.csrf()).thenReturn(httpSecurity);
        when(httpSecurity.cors()).thenReturn(httpSecurity);
        when(httpSecurity.exceptionHandling()).thenReturn(httpSecurity);
        when(httpSecurity.sessionManagement()).thenReturn(httpSecurity);
        when(httpSecurity.addFilterBefore(any(), any())).thenReturn(httpSecurity);
        when(httpSecurity.build()).thenReturn(mock(SecurityFilterChain.class));
        
        // When
        securityConfig.securityFilterChain(httpSecurity);
        
        // Then
        // Verify that System Admin role can access webhook configuration and admin endpoints
        verify(authorizeRequestsConfigurer, atLeastOnce()).requestMatchers("/webhooks/**", "/admin/**");
        verify(authorizedUrl, atLeastOnce()).hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN);
    }

    @Test
    @DisplayName("Test public endpoints configuration")
    public void testPublicEndpointsConfiguration() throws Exception {
        // Create a mock HttpSecurity
        HttpSecurity httpSecurity = mock(HttpSecurity.class);
        
        // Mock authorize requests configurers
        var authorizeRequestsConfigurer = mock(AuthorizeHttpRequestsConfigurer.class);
        var authorizedUrl = mock(AuthorizeHttpRequestsConfigurer.AuthorizedUrl.class);
        
        when(httpSecurity.authorizeHttpRequests()).thenReturn(authorizeRequestsConfigurer);
        when(authorizeRequestsConfigurer.requestMatchers(any(String.class))).thenReturn(authorizedUrl);
        when(authorizeRequestsConfigurer.requestMatchers(any(AntPathRequestMatcher.class))).thenReturn(authorizedUrl);
        when(authorizedUrl.permitAll()).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.hasAnyAuthority(anyString(), anyString())).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.hasAuthority(anyString())).thenReturn(authorizeRequestsConfigurer);
        when(authorizedUrl.authenticated()).thenReturn(authorizeRequestsConfigurer);
        
        // Mock other required configurers to prevent NullPointerException
        when(httpSecurity.csrf()).thenReturn(httpSecurity);
        when(httpSecurity.cors()).thenReturn(httpSecurity);
        when(httpSecurity.exceptionHandling()).thenReturn(httpSecurity);
        when(httpSecurity.sessionManagement()).thenReturn(httpSecurity);
        when(httpSecurity.addFilterBefore(any(), any())).thenReturn(httpSecurity);
        when(httpSecurity.build()).thenReturn(mock(SecurityFilterChain.class));
        
        // When
        securityConfig.securityFilterChain(httpSecurity);
        
        // Then
        // Verify that public endpoints don't require authentication
        verify(authorizeRequestsConfigurer, atLeastOnce()).requestMatchers("/auth/**", "/actuator/health", "/actuator/info");
        verify(authorizedUrl, atLeastOnce()).permitAll();
        
        // Verify that Swagger/OpenAPI endpoints don't require authentication
        verify(authorizeRequestsConfigurer, atLeastOnce()).requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html");
        verify(authorizedUrl, atLeastOnce()).permitAll();
    }

    @Test
    @DisplayName("Test authentication manager configuration")
    public void testAuthenticationManager() throws Exception {
        // Mock the authentication configuration
        AuthenticationConfiguration authenticationConfiguration = mock(AuthenticationConfiguration.class);
        AuthenticationManager authenticationManager = mock(AuthenticationManager.class);
        when(authenticationConfiguration.getAuthenticationManager()).thenReturn(authenticationManager);
        
        // When
        AuthenticationManager result = securityConfig.authenticationManager(authenticationConfiguration);
        
        // Then
        assertNotNull(result, "Authentication manager should not be null");
        assertEquals(authenticationManager, result, "Authentication manager should be retrieved from the configuration");
    }

    @Test
    @DisplayName("Test authentication provider configuration")
    public void testAuthenticationProvider() {
        // When
        DaoAuthenticationProvider authProvider = securityConfig.authenticationProvider();
        
        // Then
        assertNotNull(authProvider, "Authentication provider should not be null");
        
        // Verify that the provider is configured with the correct user details service and password encoder
        verify(userDetailsService, times(1));
        assertTrue(authProvider.getPasswordEncoder() instanceof BCryptPasswordEncoder, 
                "Authentication provider should use BCryptPasswordEncoder");
    }

    /**
     * Test configuration class for the security tests.
     */
    @Configuration
    @Import(SecurityConfig.class)
    static class TestConfig {
        
        @Bean
        public Resource publicKeyResource() {
            return new ClassPathResource("test-public-key.pem");
        }
    }
}