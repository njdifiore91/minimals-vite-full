package com.dollarfunding.mca.security;

import io.jsonwebtoken.JwtException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;
import com.dollarfunding.mca.security.UserDetailsServiceImpl;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * JWT Authentication Filter that intercepts incoming HTTP requests, extracts JWT tokens
 * from the Authorization header, validates them using JwtTokenProvider, and sets the
 * authentication in the SecurityContext.
 * <p>
 * This filter is crucial for the authentication process as it ensures that every request
 * is properly authenticated before reaching protected endpoints. It integrates with the
 * Minimal UI Kit's JWT authentication system and supports the RS256 algorithm with
 * automatic key rotation.
 * </p>
 * <p>
 * The filter handles two specific roles as defined in the requirements:
 * - Operations Staff: Read all, write application data
 * - System Admin: Full access to all endpoints and webhook configuration
 * </p>
 */
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger logger = LoggerFactory.getLogger(JwtAuthenticationFilter.class);
    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtTokenProvider tokenProvider;
    private final UserDetailsServiceImpl userDetailsService;

    /**
     * Constructor with JwtTokenProvider and UserDetailsServiceImpl dependencies.
     *
     * @param tokenProvider     the JWT token provider for token validation
     * @param userDetailsService the user details service for loading user information
     */
    public JwtAuthenticationFilter(JwtTokenProvider tokenProvider, UserDetailsServiceImpl userDetailsService) {
        this.tokenProvider = tokenProvider;
        this.userDetailsService = userDetailsService;
    }

    /**
     * Filters each request exactly once to extract and validate JWT tokens.
     * If a valid token is found, it sets the authentication in the SecurityContext.
     *
     * @param request     the HTTP request
     * @param response    the HTTP response
     * @param filterChain the filter chain for executing the next filter
     * @throws ServletException if a servlet error occurs
     * @throws IOException      if an I/O error occurs
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        try {
            String jwt = extractJwtFromRequest(request);

            if (StringUtils.hasText(jwt) && tokenProvider.validateToken(jwt)) {
                // Only process access tokens in this filter
                if (tokenProvider.isAccessToken(jwt)) {
                    // Get authentication from token and set it in the security context
                    UsernamePasswordAuthenticationToken authentication =
                            (UsernamePasswordAuthenticationToken) tokenProvider.getAuthentication(jwt);
                    
                    // Set additional details from the request
                    authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    
                    // Set the authentication in the security context
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                    
                    logger.debug("Set authentication for user '{}' with roles {}",
                            authentication.getName(), authentication.getAuthorities());
                } else {
                    logger.debug("Token is not an access token, skipping authentication");
                }
            } else if (StringUtils.hasText(jwt)) {
                logger.debug("Invalid JWT token");
            }
        } catch (JwtException e) {
            logger.error("JWT authentication failed: {}", e.getMessage());
            SecurityContextHolder.clearContext();
        } catch (Exception e) {
            logger.error("Cannot set user authentication: {}", e.getMessage(), e);
            SecurityContextHolder.clearContext();
        }

        filterChain.doFilter(request, response);
    }

    /**
     * Extracts the JWT token from the Authorization header.
     *
     * @param request the HTTP request
     * @return the JWT token or null if not found
     */
    private String extractJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader(AUTHORIZATION_HEADER);
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith(BEARER_PREFIX)) {
            return bearerToken.substring(BEARER_PREFIX.length());
        }
        return null;
    }

    /**
     * Determines whether this filter should be applied to the current request.
     * This filter is applied to all requests except those explicitly excluded.
     *
     * @param request the HTTP request
     * @return true if the filter should be applied, false otherwise
     */
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // Apply this filter to all requests except those explicitly excluded
        // For example, public endpoints like /api/auth/login or /api/public/**
        String path = request.getServletPath();
        
        // Exclude authentication endpoints
        return path.startsWith("/api/auth/login") ||
               path.startsWith("/api/auth/refresh") ||
               path.startsWith("/api/public/") ||
               path.equals("/api/health") ||
               path.equals("/error");
    }
}