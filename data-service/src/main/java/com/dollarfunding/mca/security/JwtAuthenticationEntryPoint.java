package com.dollarfunding.mca.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.stereotype.Component;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * Custom JWT Authentication Entry Point that handles authentication exceptions
 * by returning standardized HTTP 401 Unauthorized responses.
 * <p>
 * This component is triggered whenever an unauthenticated user tries to access
 * a protected resource, providing a consistent error response format across the application.
 * <p>
 * The error response includes:
 * - timestamp: When the error occurred
 * - status: HTTP status code (401)
 * - error: Error type description
 * - message: Detailed error message
 * - path: The request URI that caused the error
 */
@Component
public class JwtAuthenticationEntryPoint implements AuthenticationEntryPoint {

    private static final Logger logger = LoggerFactory.getLogger(JwtAuthenticationEntryPoint.class);
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * This method is called whenever an AuthenticationException is thrown,
     * typically when a user attempts to access a secured endpoint without valid authentication.
     *
     * @param request       The HTTP request that resulted in the authentication failure
     * @param response      The HTTP response to be modified
     * @param authException The exception that triggered this entry point
     * @throws IOException      If an input or output error occurs
     * @throws ServletException If a servlet error occurs
     */
    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response,
                         AuthenticationException authException) throws IOException, ServletException {
        
        // Log the authentication failure for security monitoring
        logger.error("Authentication failed: {}", authException.getMessage(), authException);
        
        // Prepare error response
        Map<String, Object> errorDetails = new HashMap<>();
        errorDetails.put("timestamp", LocalDateTime.now().format(DateTimeFormatter.ISO_DATE_TIME));
        errorDetails.put("status", HttpStatus.UNAUTHORIZED.value());
        errorDetails.put("error", "Unauthorized");
        errorDetails.put("message", authException.getMessage());
        errorDetails.put("path", request.getRequestURI());
        
        // Set response status and content type
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        
        // Write the error response as JSON
        objectMapper.writeValue(response.getOutputStream(), errorDetails);
    }
}