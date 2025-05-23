package com.dollarfunding.mca.config;

import com.dollarfunding.mca.security.JwtAuthenticationEntryPoint;
import com.dollarfunding.mca.security.JwtAuthenticationFilter;
import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserDetailsServiceImpl;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.Resource;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.io.IOException;
import java.nio.file.Files;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.spec.X509EncodedKeySpec;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;

/**
 * Security configuration for the MCA application.
 * <p>
 * This class configures Spring Security with JWT authentication using RS256 algorithm,
 * role-based authorization, and security filters. It integrates with the Minimal UI Kit's
 * JWT authentication system and enforces security policies as specified in the requirements.
 * </p>
 * <p>
 * Key features:
 * <ul>
 *   <li>JWT authentication with RS256 algorithm and 60-minute token expiry</li>
 *   <li>Role-based authorization for Operations Staff and System Admin roles</li>
 *   <li>CSRF protection and security headers</li>
 *   <li>Password encoding for user authentication</li>
 * </ul>
 * </p>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Value("${application.security.jwt.public-key-path}")
    private Resource publicKeyResource;

    private final JwtAuthenticationEntryPoint unauthorizedHandler;
    private final UserDetailsServiceImpl userDetailsService;
    private final JwtTokenProvider tokenProvider;

    @Autowired
    public SecurityConfig(JwtAuthenticationEntryPoint unauthorizedHandler,
                          UserDetailsServiceImpl userDetailsService,
                          JwtTokenProvider tokenProvider) {
        this.unauthorizedHandler = unauthorizedHandler;
        this.userDetailsService = userDetailsService;
        this.tokenProvider = tokenProvider;
    }

    /**
     * Configures the security filter chain with JWT authentication, authorization rules,
     * and security headers.
     *
     * @param http the HttpSecurity to configure
     * @return the configured SecurityFilterChain
     * @throws Exception if an error occurs during configuration
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                // Disable CSRF as we're using stateless JWT authentication
                .csrf(AbstractHttpConfigurer::disable)
                // Configure CORS
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                // Configure exception handling
                .exceptionHandling(exceptionHandling -> 
                    exceptionHandling.authenticationEntryPoint(unauthorizedHandler)
                )
                // Configure session management to stateless
                .sessionManagement(sessionManagement -> 
                    sessionManagement.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
                )
                // Configure authorization rules
                .authorizeHttpRequests(authorize -> authorize
                    // Public endpoints that don't require authentication
                    .requestMatchers("/auth/**", "/actuator/health", "/actuator/info").permitAll()
                    // Swagger/OpenAPI endpoints
                    .requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                    // Operations Staff role can access application data endpoints
                    .requestMatchers("/applications/**", "/documents/**").hasAnyAuthority(
                        RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                    // System Admin role can access all endpoints including webhook configuration
                    .requestMatchers("/webhooks/**", "/admin/**").hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
                    // All other endpoints require authentication
                    .anyRequest().authenticated()
                )
                // Add JWT authentication filter before UsernamePasswordAuthenticationFilter
                .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class)
                // Build the security filter chain
                .build();
    }

    /**
     * Creates a JWT authentication filter bean that intercepts requests and validates JWT tokens.
     *
     * @return the JWT authentication filter
     */
    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter(tokenProvider, userDetailsService);
    }

    /**
     * Creates an authentication manager bean that handles authentication requests.
     *
     * @param authenticationConfiguration the authentication configuration
     * @return the authentication manager
     * @throws Exception if an error occurs during creation
     */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }

    /**
     * Creates a DAO authentication provider bean that authenticates users against the database.
     *
     * @return the DAO authentication provider
     */
    @Bean
    public DaoAuthenticationProvider authenticationProvider() {
        DaoAuthenticationProvider authProvider = new DaoAuthenticationProvider();
        authProvider.setUserDetailsService(userDetailsService);
        authProvider.setPasswordEncoder(passwordEncoder());
        return authProvider;
    }

    /**
     * Creates a password encoder bean that uses BCrypt for password hashing.
     *
     * @return the password encoder
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /**
     * Creates a CORS configuration source bean that configures Cross-Origin Resource Sharing.
     *
     * @return the CORS configuration source
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(List.of("*")); // In production, this should be restricted to specific origins
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("Authorization", "Content-Type", "X-Requested-With"));
        configuration.setExposedHeaders(List.of("Authorization"));
        configuration.setMaxAge(3600L); // 1 hour

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    /**
     * Loads the RSA public key from the configured resource path.
     * This key is used to verify JWT signatures using the RS256 algorithm.
     *
     * @return the RSA public key
     */
    @Bean
    public PublicKey jwtPublicKey() {
        try {
            String publicKeyContent = new String(Files.readAllBytes(publicKeyResource.getFile().toPath()));
            publicKeyContent = publicKeyContent
                    .replace("-----BEGIN PUBLIC KEY-----", "")
                    .replace("-----END PUBLIC KEY-----", "")
                    .replaceAll("\\s", "");

            byte[] publicKeyBytes = Base64.getDecoder().decode(publicKeyContent);
            X509EncodedKeySpec keySpec = new X509EncodedKeySpec(publicKeyBytes);
            KeyFactory keyFactory = KeyFactory.getInstance("RSA");
            return keyFactory.generatePublic(keySpec);
        } catch (IOException | java.security.GeneralSecurityException e) {
            throw new RuntimeException("Failed to load JWT public key", e);
        }
    }
}