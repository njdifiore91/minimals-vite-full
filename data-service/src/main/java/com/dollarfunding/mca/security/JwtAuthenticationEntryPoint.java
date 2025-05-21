package com.dollarfunding.mca.security;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.LocalDateTime;

/**
 * Component that handles authentication exceptions by returning appropriate HTTP 401 Unauthorized responses
 * when a user attempts to access a protected resource without proper authentication.
 * <p>
 * This class implements Spring Security's AuthenticationEntryPoint interface and is responsible for
 * providing meaningful error responses for authentication failures.
 * <p>
 * The error response includes:
 * - Error code: UNAUTHORIZED
 * - Error message: Detailed authentication failure message
 * - Timestamp: When the error occurred
 * - Path: The requested URL that triggered the authentication failure
 * - HTTP Status: 401 Unauthorized
 * <p>
 * This component is configured in the SecurityConfig class and is triggered when an unauthenticated user
 * attempts to access a protected resource or when JWT token validation fails.
 */
@Component
public class JwtAuthenticationEntryPoint implements AuthenticationEntryPoint {

    private static final Logger logger = LoggerFactory.getLogger(JwtAuthenticationEntryPoint.class);
    private final ObjectMapper objectMapper;

    /**
     * Constructor with dependency injection for required beans.
     *
     * @param objectMapper The ObjectMapper bean for JSON serialization
     */
    @Autowired
    public JwtAuthenticationEntryPoint(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * This method is called when an AuthenticationException is thrown during the authentication process.
     * It returns a standardized error response in JSON format with HTTP status 401 Unauthorized.
     * <p>
     * Common scenarios that trigger this method:
     * - Missing JWT token in the request
     * - Expired JWT token
     * - Invalid JWT signature
     * - Malformed JWT token
     * - User not found in the database
     *
     * @param request       The HTTP request that resulted in an AuthenticationException
     * @param response      The HTTP response to be modified
     * @param authException The exception that triggered this method
     * @throws IOException If an input or output exception occurs
     */
    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response,
                         AuthenticationException authException) throws IOException {
        
        String requestUri = request.getRequestURI();
        String method = request.getMethod();
        String remoteAddr = request.getRemoteAddr();
        String userAgent = request.getHeader("User-Agent");
        
        // Log detailed information about the authentication failure for security monitoring
        logger.error("Authentication failure: {}, Method: {}, URI: {}, Remote IP: {}, User-Agent: {}", 
                authException.getMessage(), method, requestUri, remoteAddr, userAgent);
        
        // Create a standardized error response
        ErrorResponseDTO errorResponse = new ErrorResponseDTO();
        errorResponse.setCode("UNAUTHORIZED");
        errorResponse.setMessage("Authentication failed: " + authException.getMessage());
        errorResponse.setStatus(HttpStatus.UNAUTHORIZED.value());
        errorResponse.setTimestamp(LocalDateTime.now());
        errorResponse.setPath(requestUri);

        // Set response status and content type
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        
        // Add security headers to prevent caching of error responses
        response.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
        response.setHeader("Pragma", "no-cache");
        response.setHeader("Expires", "0");
        
        // Write the error response as JSON to the response output stream
        objectMapper.writeValue(response.getOutputStream(), errorResponse);
    }
}