package com.dollarfunding.mca.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Spring Security filter that intercepts incoming HTTP requests, extracts JWT tokens from the
 * Authorization header, validates them using JwtTokenProvider, and sets the authentication in
 * the SecurityContext.
 * <p>
 * This filter is crucial for the authentication process as it ensures that every request is
 * properly authenticated before reaching protected endpoints.
 * <p>
 * The filter performs the following steps:
 * 1. Extract JWT token from the Authorization header
 * 2. Validate the token using JwtTokenProvider
 * 3. Load user details based on the token
 * 4. Set authentication in SecurityContext if the token is valid
 * 5. Handle and log authentication exceptions
 * <p>
 * This filter integrates with the Minimal UI Kit's JWT authentication system and supports
 * the following JWT parameters:
 * - Algorithm: RS256
 * - Token expiry: 60 minutes
 * - Refresh token: 7 days
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger logger = LoggerFactory.getLogger(JwtAuthenticationFilter.class);
    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtTokenProvider tokenProvider;
    private final UserDetailsServiceImpl userDetailsService;

    /**
     * Constructor with dependency injection for required beans.
     *
     * @param tokenProvider     The JwtTokenProvider bean for token validation
     * @param userDetailsService The UserDetailsService bean for loading user details
     */
    @Autowired
    public JwtAuthenticationFilter(JwtTokenProvider tokenProvider, UserDetailsServiceImpl userDetailsService) {
        this.tokenProvider = tokenProvider;
        this.userDetailsService = userDetailsService;
    }

    /**
     * This method is called for each HTTP request to protected resources and performs
     * JWT token extraction, validation, and authentication.
     *
     * @param request     The HTTP request
     * @param response    The HTTP response
     * @param filterChain The filter chain for executing the next filter
     * @throws ServletException If a servlet exception occurs
     * @throws IOException      If an I/O exception occurs
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        try {
            // Extract JWT token from the request
            String jwt = extractJwtFromRequest(request);

            // If token exists and is valid, set authentication in context
            if (StringUtils.hasText(jwt) && tokenProvider.validateToken(jwt)) {
                // Get username from token
                String username = tokenProvider.getUsernameFromToken(jwt);
                
                // Load user details
                UserDetails userDetails = userDetailsService.loadUserByUsername(username);
                
                // Create authentication token
                UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                        userDetails, null, userDetails.getAuthorities());
                
                // Set request details in authentication token
                authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                
                // Set authentication in security context
                SecurityContextHolder.getContext().setAuthentication(authentication);
                
                // Log successful authentication
                if (logger.isDebugEnabled()) {
                    logger.debug("Authentication successful for user: {}, roles: {}", username, 
                            userDetails.getAuthorities());
                }
            }
        } catch (Exception ex) {
            // Log authentication failure but don't stop the filter chain
            logger.error("Could not set user authentication in security context: {}", ex.getMessage());
            
            // Add detailed logging for security monitoring
            String requestUri = request.getRequestURI();
            String method = request.getMethod();
            String remoteAddr = request.getRemoteAddr();
            String userAgent = request.getHeader("User-Agent");
            
            logger.error("Authentication failure details - Method: {}, URI: {}, Remote IP: {}, User-Agent: {}", 
                    method, requestUri, remoteAddr, userAgent);
        }

        // Continue filter chain regardless of authentication result
        // (AuthenticationEntryPoint will handle unauthorized requests)
        filterChain.doFilter(request, response);
    }

    /**
     * Extracts JWT token from the Authorization header.
     * The header format should be: "Authorization: Bearer [token]"
     *
     * @param request The HTTP request
     * @return The JWT token, or null if not found or invalid format
     */
    private String extractJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader(AUTHORIZATION_HEADER);
        
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith(BEARER_PREFIX)) {
            // Return token without "Bearer " prefix
            return bearerToken.substring(BEARER_PREFIX.length());
        }
        
        return null;
    }
}