package com.dollarfunding.mca.security;

import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
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

import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link JwtAuthenticationEntryPoint} class.
 * 
 * These tests verify that the JwtAuthenticationEntryPoint correctly handles
 * authentication exceptions by returning appropriate HTTP 401 Unauthorized responses
 * with detailed error messages in JSON format.
 */
@ExtendWith(MockitoExtension.class)
public class JwtAuthenticationEntryPointTest {

    @Mock
    private ObjectMapper objectMapper;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @InjectMocks
    private JwtAuthenticationEntryPoint entryPoint;

    private MockHttpServletRequest mockRequest;
    private MockHttpServletResponse mockResponse;
    private StringWriter responseWriter;

    @BeforeEach
    public void setUp() throws IOException {
        // Set up mock request with realistic values
        mockRequest = new MockHttpServletRequest();
        mockRequest.setRequestURI("/api/v1/applications");
        mockRequest.setMethod("GET");
        mockRequest.setRemoteAddr("192.168.1.100");
        mockRequest.addHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");

        // Set up mock response with a StringWriter to capture the output
        mockResponse = new MockHttpServletResponse();
        responseWriter = new StringWriter();
        PrintWriter printWriter = new PrintWriter(responseWriter);
        when(response.getOutputStream()).thenReturn(mockResponse.getOutputStream());
    }

    @Test
    @DisplayName("Should return 401 Unauthorized with error details for missing JWT token")
    public void testCommenceWithMissingTokenException() throws IOException {
        // Arrange
        AuthenticationException authException = new InsufficientAuthenticationException("Missing JWT token");
        when(request.getRequestURI()).thenReturn("/api/v1/applications");
        when(request.getMethod()).thenReturn("GET");
        when(request.getRemoteAddr()).thenReturn("192.168.1.100");
        when(request.getHeader("User-Agent")).thenReturn("Mozilla/5.0");

        // Capture the ErrorResponseDTO that will be written to the response
        ArgumentCaptor<ErrorResponseDTO> errorResponseCaptor = ArgumentCaptor.forClass(ErrorResponseDTO.class);

        // Act
        entryPoint.commence(request, response, authException);

        // Assert
        verify(response).setStatus(HttpStatus.UNAUTHORIZED.value());
        verify(response).setContentType(MediaType.APPLICATION_JSON_VALUE);
        verify(response).setCharacterEncoding("UTF-8");
        verify(objectMapper).writeValue(any(), errorResponseCaptor.capture());

        // Verify the error response content
        ErrorResponseDTO capturedResponse = errorResponseCaptor.getValue();
        assertEquals("UNAUTHORIZED", capturedResponse.getErrorCode());
        assertEquals("Authentication failed: Missing JWT token", capturedResponse.getMessage());
        assertEquals(HttpStatus.UNAUTHORIZED.value(), capturedResponse.getStatus());
        assertNotNull(capturedResponse.getTimestamp());
        assertEquals("/api/v1/applications", capturedResponse.getPath());
    }

    @Test
    @DisplayName("Should return 401 Unauthorized with error details for invalid JWT token")
    public void testCommenceWithInvalidTokenException() throws IOException {
        // Arrange
        AuthenticationException authException = new BadCredentialsException("Invalid JWT token");
        when(request.getRequestURI()).thenReturn("/api/v1/applications/123");
        when(request.getMethod()).thenReturn("POST");
        when(request.getRemoteAddr()).thenReturn("10.0.0.1");
        when(request.getHeader("User-Agent")).thenReturn("PostmanRuntime/7.28.4");

        // Capture the ErrorResponseDTO that will be written to the response
        ArgumentCaptor<ErrorResponseDTO> errorResponseCaptor = ArgumentCaptor.forClass(ErrorResponseDTO.class);

        // Act
        entryPoint.commence(request, response, authException);

        // Assert
        verify(response).setStatus(HttpStatus.UNAUTHORIZED.value());
        verify(response).setContentType(MediaType.APPLICATION_JSON_VALUE);
        verify(response).setCharacterEncoding("UTF-8");
        verify(objectMapper).writeValue(any(), errorResponseCaptor.capture());

        // Verify the error response content
        ErrorResponseDTO capturedResponse = errorResponseCaptor.getValue();
        assertEquals("UNAUTHORIZED", capturedResponse.getErrorCode());
        assertEquals("Authentication failed: Invalid JWT token", capturedResponse.getMessage());
        assertEquals(HttpStatus.UNAUTHORIZED.value(), capturedResponse.getStatus());
        assertNotNull(capturedResponse.getTimestamp());
        assertEquals("/api/v1/applications/123", capturedResponse.getPath());
    }

    @Test
    @DisplayName("Should set security headers in the response")
    public void testResponseContainsSecurityHeaders() throws IOException {
        // Arrange
        AuthenticationException authException = new BadCredentialsException("Invalid JWT token");
        when(request.getRequestURI()).thenReturn("/api/v1/applications");
        when(request.getMethod()).thenReturn("GET");
        when(request.getRemoteAddr()).thenReturn("192.168.1.100");
        when(request.getHeader("User-Agent")).thenReturn("Mozilla/5.0");

        // Act
        entryPoint.commence(request, response, authException);

        // Assert
        verify(response).setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
        verify(response).setHeader("Pragma", "no-cache");
        verify(response).setHeader("Expires", "0");
    }

    @Test
    @DisplayName("Should log authentication failures with detailed information")
    public void testLoggingOfAuthenticationFailure() throws Exception {
        // Arrange
        AuthenticationException authException = new BadCredentialsException("Invalid JWT token");
        when(request.getRequestURI()).thenReturn("/api/v1/applications");
        when(request.getMethod()).thenReturn("GET");
        when(request.getRemoteAddr()).thenReturn("192.168.1.100");
        when(request.getHeader("User-Agent")).thenReturn("Mozilla/5.0");

        // Get the logger using reflection
        Logger loggerMock = mock(Logger.class);
        ReflectionTestUtils.setField(entryPoint, "logger", loggerMock);

        // Act
        entryPoint.commence(request, response, authException);

        // Assert
        verify(loggerMock).error(
                eq("Authentication failure: {}, Method: {}, URI: {}, Remote IP: {}, User-Agent: {}"),
                eq("Invalid JWT token"),
                eq("GET"),
                eq("/api/v1/applications"),
                eq("192.168.1.100"),
                eq("Mozilla/5.0")
        );
    }

    @Test
    @DisplayName("Should handle expired JWT token exception")
    public void testCommenceWithExpiredTokenException() throws IOException {
        // Arrange
        AuthenticationException authException = new BadCredentialsException("JWT token has expired");
        when(request.getRequestURI()).thenReturn("/api/v1/documents");
        when(request.getMethod()).thenReturn("GET");
        when(request.getRemoteAddr()).thenReturn("192.168.1.100");
        when(request.getHeader("User-Agent")).thenReturn("Mozilla/5.0");

        // Capture the ErrorResponseDTO that will be written to the response
        ArgumentCaptor<ErrorResponseDTO> errorResponseCaptor = ArgumentCaptor.forClass(ErrorResponseDTO.class);

        // Act
        entryPoint.commence(request, response, authException);

        // Assert
        verify(response).setStatus(HttpStatus.UNAUTHORIZED.value());
        verify(objectMapper).writeValue(any(), errorResponseCaptor.capture());

        // Verify the error response content
        ErrorResponseDTO capturedResponse = errorResponseCaptor.getValue();
        assertEquals("UNAUTHORIZED", capturedResponse.getErrorCode());
        assertEquals("Authentication failed: JWT token has expired", capturedResponse.getMessage());
        assertEquals(HttpStatus.UNAUTHORIZED.value(), capturedResponse.getStatus());
        assertEquals("/api/v1/documents", capturedResponse.getPath());
    }

    @Test
    @DisplayName("Should handle malformed JWT token exception")
    public void testCommenceWithMalformedTokenException() throws IOException {
        // Arrange
        AuthenticationException authException = new BadCredentialsException("Malformed JWT token");
        when(request.getRequestURI()).thenReturn("/api/v1/webhooks");
        when(request.getMethod()).thenReturn("POST");
        when(request.getRemoteAddr()).thenReturn("192.168.1.100");
        when(request.getHeader("User-Agent")).thenReturn("Mozilla/5.0");

        // Capture the ErrorResponseDTO that will be written to the response
        ArgumentCaptor<ErrorResponseDTO> errorResponseCaptor = ArgumentCaptor.forClass(ErrorResponseDTO.class);

        // Act
        entryPoint.commence(request, response, authException);

        // Assert
        verify(response).setStatus(HttpStatus.UNAUTHORIZED.value());
        verify(objectMapper).writeValue(any(), errorResponseCaptor.capture());

        // Verify the error response content
        ErrorResponseDTO capturedResponse = errorResponseCaptor.getValue();
        assertEquals("UNAUTHORIZED", capturedResponse.getErrorCode());
        assertEquals("Authentication failed: Malformed JWT token", capturedResponse.getMessage());
        assertEquals(HttpStatus.UNAUTHORIZED.value(), capturedResponse.getStatus());
        assertEquals("/api/v1/webhooks", capturedResponse.getPath());
    }
}