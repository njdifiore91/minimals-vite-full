package com.dollarfunding.mca.security;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Test security configuration for role-based authorization tests.
 * <p>
 * This configuration mirrors the production security configuration but is simplified for testing purposes.
 * It configures JWT authentication, authorization rules, and security filters for test environments.
 * </p>
 */
@TestConfiguration
@EnableWebSecurity
@EnableMethodSecurity(securedEnabled = true, jsr250Enabled = true)
public class TestSecurityConfig {

    /**
     * Configures the security filter chain for testing with JWT authentication and authorization rules.
     *
     * @param http The HttpSecurity to configure
     * @return The configured SecurityFilterChain
     * @throws Exception If an error occurs during configuration
     */
    @Bean
    @Primary
    public SecurityFilterChain testSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            // Disable CSRF for testing
            .csrf(csrf -> csrf.disable())
            
            // Configure session management (stateless for JWT)
            .sessionManagement(sessionManagement -> 
                sessionManagement.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            
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
                .requestMatchers("/api/v1/applications/reports").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                .requestMatchers("/api/v1/applications/**").hasAnyAuthority(
                    RoleConstants.ROLE_OPERATIONS_STAFF, RoleConstants.ROLE_SYSTEM_ADMIN)
                
                // Admin endpoints - System Admin only
                .requestMatchers("/api/v1/admin/**").hasAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)
                
                // All other endpoints require authentication
                .anyRequest().authenticated()
            );

        return http.build();
    }
}