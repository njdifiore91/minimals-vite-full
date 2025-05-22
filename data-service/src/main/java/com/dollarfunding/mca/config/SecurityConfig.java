package com.dollarfunding.mca.config;

import com.dollarfunding.mca.security.JwtAuthenticationEntryPoint;
import com.dollarfunding.mca.security.JwtAuthenticationFilter;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserDetailsServiceImpl;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

/**
 * Security configuration for the MCA application.
 * <p>
 * This class configures security settings including JWT authentication, authorization rules,
 * and security filters. It defines the security filter chain, authentication manager, JWT decoder,
 * and role-based access control.
 * </p>
 * <p>
 * Key features:
 * <ul>
 *   <li>JWT authentication with RS256 algorithm and 60-minute token expiry</li>
 *   <li>Role-based authorization for Operations Staff and System Admin roles</li>
 *   <li>Security filters for request validation and protection</li>
 *   <li>CSRF protection and security headers</li>
 *   <li>Password encoding for user authentication</li>
 * </ul>
 * </p>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(securedEnabled = true, jsr250Enabled = true)
public class SecurityConfig {

    private final JwtAuthenticationEntryPoint unauthorizedHandler;
    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final UserDetailsServiceImpl userDetailsService;

    @Value("${app.cors.allowed-origins:*}")
    private String[] allowedOrigins;

    @Value("${app.cors.allowed-methods:GET,POST,PUT,DELETE,OPTIONS}")
    private String[] allowedMethods;

    @Value("${app.cors.allowed-headers:Authorization,Content-Type,X-Requested-With,Accept,Origin,Access-Control-Request-Method,Access-Control-Request-Headers}")
    private String[] allowedHeaders;

    @Value("${app.cors.exposed-headers:Authorization,Content-Disposition}")
    private String[] exposedHeaders;

    @Value("${app.cors.max-age:3600}")
    private long maxAge;

    @Value("${app.security.csrf.enabled:true}")
    private boolean csrfEnabled;

    /**
     * Constructor with dependency injection for required beans.
     *
     * @param unauthorizedHandler    The authentication entry point for handling unauthorized requests
     * @param jwtAuthenticationFilter The JWT authentication filter for token validation
     * @param userDetailsService     The user details service for loading user information
     */
    @Autowired
    public SecurityConfig(JwtAuthenticationEntryPoint unauthorizedHandler,
                          JwtAuthenticationFilter jwtAuthenticationFilter,
                          UserDetailsServiceImpl userDetailsService) {
        this.unauthorizedHandler = unauthorizedHandler;
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
        this.userDetailsService = userDetailsService;
    }

    /**
     * Configures the security filter chain with JWT authentication, authorization rules,
     * CSRF protection, and security headers.
     *
     * @param http The HttpSecurity to configure
     * @return The configured SecurityFilterChain
     * @throws Exception If an error occurs during configuration
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        // Configure CSRF protection
        if (csrfEnabled) {
            http.csrf(csrf -> csrf
                    .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
                    .csrfTokenRequestHandler(new CsrfTokenRequestAttributeHandler()));
        } else {
            http.csrf(csrf -> csrf.disable());
        }

        // Configure security settings
        http
            // Configure exception handling
            .exceptionHandling(exceptionHandling -> 
                exceptionHandling.authenticationEntryPoint(unauthorizedHandler))
            
            // Configure session management (stateless for JWT)
            .sessionManagement(sessionManagement -> 
                sessionManagement.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            
            // Configure CORS
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            
            // Configure security headers
            .headers(headers -> headers
                .contentSecurityPolicy(csp -> csp
                    .policyDirectives("default-src 'self'; frame-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'"))
                .referrerPolicy(referrer -> referrer
                    .policy(ReferrerPolicyHeaderWriter.ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN))
                .frameOptions(frame -> frame.deny())
                .xssProtection(xss -> xss.disable()) // Modern browsers use CSP instead
            )
            
            // Configure authorization rules
            .authorizeHttpRequests(authorize -> authorize
                // Public endpoints
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/api/v1/public/**").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/actuator/info").permitAll()
                .requestMatchers("/v3/api-docs/**").permitAll()
                .requestMatchers("/swagger-ui/**").permitAll()
                .requestMatchers("/swagger-resources/**").permitAll()
                
                // Webhook configuration endpoints - System Admin only
                .requestMatchers("/api/v1/webhooks/**").hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
                
                // Application endpoints - Operations Staff and System Admin
                .requestMatchers(HttpMethod.GET, "/api/v1/applications/**").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                .requestMatchers(HttpMethod.POST, "/api/v1/applications/**").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                .requestMatchers(HttpMethod.PUT, "/api/v1/applications/**").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                .requestMatchers(HttpMethod.DELETE, "/api/v1/applications/**").hasAuthority(
                    RoleConstants.ROLE_SYSTEM_ADMIN)
                
                // Document endpoints - Operations Staff and System Admin
                .requestMatchers(HttpMethod.GET, "/api/v1/documents/**").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                .requestMatchers(HttpMethod.POST, "/api/v1/documents/**").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                .requestMatchers(HttpMethod.PUT, "/api/v1/documents/**").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                .requestMatchers(HttpMethod.DELETE, "/api/v1/documents/**").hasAuthority(
                    RoleConstants.ROLE_SYSTEM_ADMIN)
                
                // Admin endpoints - System Admin only
                .requestMatchers("/api/v1/admin/**").hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
                
                // All other endpoints require authentication
                .anyRequest().authenticated()
            );

        // Add JWT authentication filter before UsernamePasswordAuthenticationFilter
        http.addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    /**
     * Configures CORS settings for cross-origin requests.
     *
     * @return The CORS configuration source
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(Arrays.asList(allowedOrigins));
        configuration.setAllowedMethods(Arrays.asList(allowedMethods));
        configuration.setAllowedHeaders(Arrays.asList(allowedHeaders));
        configuration.setExposedHeaders(Arrays.asList(exposedHeaders));
        configuration.setMaxAge(maxAge);
        configuration.setAllowCredentials(true);
        
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    /**
     * Configures the authentication manager for user authentication.
     *
     * @param authenticationConfiguration The authentication configuration
     * @return The authentication manager
     * @throws Exception If an error occurs during configuration
     */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }

    /**
     * Configures the authentication provider with user details service and password encoder.
     *
     * @return The configured authentication provider
     */
    @Bean
    public DaoAuthenticationProvider authenticationProvider() {
        DaoAuthenticationProvider authProvider = new DaoAuthenticationProvider();
        authProvider.setUserDetailsService(userDetailsService);
        authProvider.setPasswordEncoder(passwordEncoder());
        return authProvider;
    }

    /**
     * Configures the password encoder for secure password storage.
     *
     * @return The password encoder
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12); // Higher strength for better security
    }
}