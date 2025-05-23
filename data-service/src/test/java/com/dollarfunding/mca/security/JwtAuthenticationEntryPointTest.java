package com.dollarfunding.mca.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.InsufficientAuthenticationException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.test.util.ReflectionTestUtils;

import javax.servlet.ServletException;
import javax.servlet.ServletOutputStream;
import java.io.IOException;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Test class for {@link JwtAuthenticationEntryPoint} that verifies the correct handling
 * of authentication exceptions.
 * <p>
 * This test ensures that the entry point properly generates HTTP 401 Unauthorized responses
 * with detailed error messages, JSON formatting, and inclusion of timestamp and path information.
 */
@ExtendWith(MockitoExtension.class)
public class JwtAuthenticationEntryPointTest {

    @InjectMocks
    private JwtAuthenticationEntryPoint jwtAuthenticationEntryPoint;

    private Logger mockLogger;

    private MockHttpServletRequest request;
    private MockHttpServletResponse response;
    private AuthenticationException authException;
    private ObjectMapper objectMapper;

    @BeforeEach
    public void setUp() {
        // Initialize test objects
        request = new MockHttpServletRequest();
        response = new MockHttpServletResponse();
        authException = new BadCredentialsException("Invalid credentials");
        objectMapper = new ObjectMapper();
        
        // Set up request URI
        request.setRequestURI("/api/v1/applications");
        
        // Create a mock logger and inject it into the entry point
        mockLogger = mock(Logger.class);
        ReflectionTestUtils.setField(jwtAuthenticationEntryPoint, "logger", mockLogger);
    }

    /**
     * Test that the commence method sets the response status to 401 (Unauthorized)
     */
    @Test
    public void testCommenceSetsUnauthorizedStatus() throws IOException, ServletException {
        // Execute the method under test
        jwtAuthenticationEntryPoint.commence(request, response, authException);
        
        // Verify that the response status is set to 401
        assertEquals(HttpStatus.UNAUTHORIZED.value(), response.getStatus());
    }

    /**
     * Test that the commence method sets the content type to application/json
     */
    @Test
    public void testCommenceSetsJsonContentType() throws IOException, ServletException {
        // Execute the method under test
        jwtAuthenticationEntryPoint.commence(request, response, authException);
        
        // Verify that the content type is set to application/json
        assertEquals(MediaType.APPLICATION_JSON_VALUE, response.getContentType());
    }

    /**
     * Test that the commence method includes all required fields in the error response
     */
    @Test
    public void testCommenceIncludesAllRequiredFields() throws IOException, ServletException {
        // Execute the method under test
        jwtAuthenticationEntryPoint.commence(request, response, authException);
        
        // Parse the response content as a Map
        String content = response.getContentAsString();
        Map<String, Object> errorDetails = objectMapper.readValue(content, Map.class);
        
        // Verify that all required fields are present
        assertTrue(errorDetails.containsKey("timestamp"));
        assertTrue(errorDetails.containsKey("status"));
        assertTrue(errorDetails.containsKey("error"));
        assertTrue(errorDetails.containsKey("message"));
        assertTrue(errorDetails.containsKey("path"));
        
        // Verify the values of the fields
        assertEquals(HttpStatus.UNAUTHORIZED.value(), errorDetails.get("status"));
        assertEquals("Unauthorized", errorDetails.get("error"));
        assertEquals(authException.getMessage(), errorDetails.get("message"));
        assertEquals(request.getRequestURI(), errorDetails.get("path"));
    }
    
    /**
     * Test that the commence method includes the authentication exception message in the error response
     */
    @Test
    public void testCommenceIncludesExceptionMessage() throws IOException, ServletException {
        // Create a specific authentication exception with a custom message
        String customMessage = "JWT token has expired";
        AuthenticationException customException = new BadCredentialsException(customMessage);
        
        // Execute the method under test
        jwtAuthenticationEntryPoint.commence(request, response, customException);
        
        // Parse the response content as a Map
        String content = response.getContentAsString();
        Map<String, Object> errorDetails = objectMapper.readValue(content, Map.class);
        
        // Verify that the exception message is included in the error response
        assertEquals(customMessage, errorDetails.get("message"));
    }
    
    /**
     * Test that the commence method includes the request URI in the error response
     */
    @Test
    public void testCommenceIncludesRequestURI() throws IOException, ServletException {
        // Set a specific request URI
        String customURI = "/api/v1/documents/123";
        request.setRequestURI(customURI);
        
        // Execute the method under test
        jwtAuthenticationEntryPoint.commence(request, response, authException);
        
        // Parse the response content as a Map
        String content = response.getContentAsString();
        Map<String, Object> errorDetails = objectMapper.readValue(content, Map.class);
        
        // Verify that the request URI is included in the error response
        assertEquals(customURI, errorDetails.get("path"));
    }
    
    /**
     * Test that the commence method logs the authentication failure
     */
    @Test
    public void testCommenceLogsAuthenticationFailure() throws IOException, ServletException {
        // Execute the method under test
        jwtAuthenticationEntryPoint.commence(request, response, authException);
        
        // Verify that the authentication failure is logged
        verify(mockLogger).error(eq("Authentication failed: {}"), eq(authException.getMessage()), eq(authException));
    }
    
    /**
     * Test that the commence method handles different types of authentication exceptions
     */
    @Test
    public void testCommenceHandlesDifferentExceptionTypes() throws IOException, ServletException {
        // Create different types of authentication exceptions
        AuthenticationException[] exceptions = {
            new BadCredentialsException("Invalid credentials"),
            new InsufficientAuthenticationException("Full authentication is required"),
            new AuthenticationException("Custom authentication error") {}
        };
        
        for (AuthenticationException exception : exceptions) {
            // Reset the response for each test
            response = new MockHttpServletResponse();
            
            // Execute the method under test
            jwtAuthenticationEntryPoint.commence(request, response, exception);
            
            // Parse the response content as a Map
            String content = response.getContentAsString();
            Map<String, Object> errorDetails = objectMapper.readValue(content, Map.class);
            
            // Verify that the response status is 401 and the exception message is included
            assertEquals(HttpStatus.UNAUTHORIZED.value(), response.getStatus());
            assertEquals(exception.getMessage(), errorDetails.get("message"));
        }
    }
    
    /**
     * Test that the timestamp in the error response is in ISO format
     */
    @Test
    public void testTimestampFormatInErrorResponse() throws IOException, ServletException {
        // Execute the method under test
        jwtAuthenticationEntryPoint.commence(request, response, authException);
        
        // Parse the response content as a Map
        String content = response.getContentAsString();
        Map<String, Object> errorDetails = objectMapper.readValue(content, Map.class);
        
        // Get the timestamp from the error details
        String timestamp = (String) errorDetails.get("timestamp");
        
        // Verify that the timestamp is not null and matches ISO format pattern
        assertNotNull(timestamp);
        assertTrue(timestamp.matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?.*"));
    }