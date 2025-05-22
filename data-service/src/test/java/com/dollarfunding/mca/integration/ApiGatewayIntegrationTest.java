package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.dto.ApplicationDto;
import com.dollarfunding.mca.dto.WebhookConfigDto;
import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.*;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.web.client.RestTemplate;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration tests for the Kong API Gateway interaction with the data-service.
 * Tests authentication, authorization, rate limiting, and CORS configuration.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
public class ApiGatewayIntegrationTest {

    @Value("${kong.gateway.url}")
    private String kongGatewayUrl;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private ObjectMapper objectMapper;

    private RestTemplate restTemplate;
    private String operationsStaffToken;
    private String systemAdminToken;
    private String expiredToken;

    @BeforeEach
    public void setup() {
        restTemplate = new RestTemplate();
        
        // Generate tokens for testing
        operationsStaffToken = jwtTokenProvider.generateToken("operations_user", RoleConstants.OPERATIONS_STAFF);
        systemAdminToken = jwtTokenProvider.generateToken("admin_user", RoleConstants.SYSTEM_ADMIN);
        expiredToken = jwtTokenProvider.generateTokenWithCustomExpiration("expired_user", 
                RoleConstants.OPERATIONS_STAFF, java.util.Date.from(java.time.Instant.now().minusSeconds(3600))); // Expired 1 hour ago
    }

    /**
     * Tests that the API Gateway properly enforces authentication for protected endpoints.
     */
    @Test
    @DisplayName("Test API Gateway authentication enforcement")
    public void testApiGatewayAuthenticationEnforcement() {
        // Test access to applications endpoint without authentication
        ResponseEntity<String> response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.GET,
                new HttpEntity<>(new HttpHeaders()),
                String.class);
        
        assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
        
        // Test access with valid token
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + operationsStaffToken);
        
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Test access with expired token
        headers.set("Authorization", "Bearer " + expiredToken);
        
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        
        assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
        assertTrue(response.getBody().contains("expired"));
    }

    /**
     * Tests that the API Gateway properly enforces role-based access control.
     */
    @Test
    @DisplayName("Test API Gateway role-based access control")
    public void testApiGatewayRoleBasedAccessControl() throws Exception {
        // Setup headers for Operations Staff
        HttpHeaders operationsHeaders = new HttpHeaders();
        operationsHeaders.set("Authorization", "Bearer " + operationsStaffToken);
        operationsHeaders.setContentType(MediaType.APPLICATION_JSON);
        
        // Setup headers for System Admin
        HttpHeaders adminHeaders = new HttpHeaders();
        adminHeaders.set("Authorization", "Bearer " + systemAdminToken);
        adminHeaders.setContentType(MediaType.APPLICATION_JSON);
        
        // Test Operations Staff access to applications (should be allowed)
        ResponseEntity<String> response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.GET,
                new HttpEntity<>(operationsHeaders),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Test Operations Staff access to webhooks (should be forbidden)
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/webhooks",
                HttpMethod.GET,
                new HttpEntity<>(operationsHeaders),
                String.class);
        
        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        
        // Test System Admin access to applications (should be allowed)
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.GET,
                new HttpEntity<>(adminHeaders),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Test System Admin access to webhooks (should be allowed)
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/webhooks",
                HttpMethod.GET,
                new HttpEntity<>(adminHeaders),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Test creating a webhook with System Admin role (should be allowed)
        WebhookConfigDto webhookConfig = new WebhookConfigDto();
        webhookConfig.setUrl("https://example.com/webhook");
        webhookConfig.setEvents(Collections.singletonList("application.created"));
        webhookConfig.setSecret("test-secret");
        
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/webhooks",
                HttpMethod.POST,
                new HttpEntity<>(objectMapper.writeValueAsString(webhookConfig), adminHeaders),
                String.class);
        
        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        
        // Test creating a webhook with Operations Staff role (should be forbidden)
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/webhooks",
                HttpMethod.POST,
                new HttpEntity<>(objectMapper.writeValueAsString(webhookConfig), operationsHeaders),
                String.class);
        
        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
    }

    /**
     * Tests that the API Gateway properly enforces rate limits.
     */
    @Test
    @DisplayName("Test API Gateway rate limiting")
    public void testApiGatewayRateLimiting() {
        // Setup headers for authenticated requests
        HttpHeaders authHeaders = new HttpHeaders();
        authHeaders.set("Authorization", "Bearer " + operationsStaffToken);
        
        // Make multiple requests to trigger rate limiting
        // Note: In a real test, we would make more requests to hit the limit,
        // but for demonstration purposes, we'll make a few and check for rate limit headers
        
        for (int i = 0; i < 5; i++) {
            ResponseEntity<String> response = restTemplate.exchange(
                    kongGatewayUrl + "/api/v1/applications",
                    HttpMethod.GET,
                    new HttpEntity<>(authHeaders),
                    String.class);
            
            assertEquals(HttpStatus.OK, response.getStatusCode());
            
            // Check for rate limit headers
            HttpHeaders responseHeaders = response.getHeaders();
            assertTrue(responseHeaders.containsKey("X-RateLimit-Limit"));
            assertTrue(responseHeaders.containsKey("X-RateLimit-Remaining"));
            assertTrue(responseHeaders.containsKey("X-RateLimit-Reset"));
            
            // Verify the rate limit is set to 60 requests per minute for authenticated users
            assertEquals("60", responseHeaders.getFirst("X-RateLimit-Limit"));
            
            // Verify remaining count is decreasing
            int remaining = Integer.parseInt(responseHeaders.getFirst("X-RateLimit-Remaining"));
            assertTrue(remaining <= 60 - i - 1);
        }
        
        // Test unauthenticated rate limiting
        HttpHeaders unauthHeaders = new HttpHeaders();
        
        for (int i = 0; i < 3; i++) {
            ResponseEntity<String> response = restTemplate.exchange(
                    kongGatewayUrl + "/api/v1/health", // Using a public endpoint
                    HttpMethod.GET,
                    new HttpEntity<>(unauthHeaders),
                    String.class);
            
            // Health endpoint should be accessible without authentication
            assertEquals(HttpStatus.OK, response.getStatusCode());
            
            // Check for rate limit headers
            HttpHeaders responseHeaders = response.getHeaders();
            assertTrue(responseHeaders.containsKey("X-RateLimit-Limit"));
            assertTrue(responseHeaders.containsKey("X-RateLimit-Remaining"));
            
            // Verify the rate limit is set to 10 requests per minute for unauthenticated users
            assertEquals("10", responseHeaders.getFirst("X-RateLimit-Limit"));
            
            // Verify remaining count is decreasing
            int remaining = Integer.parseInt(responseHeaders.getFirst("X-RateLimit-Remaining"));
            assertTrue(remaining <= 10 - i - 1);
        }
    }

    /**
     * Tests that the API Gateway properly enforces CORS policies.
     */
    @Test
    @DisplayName("Test API Gateway CORS configuration")
    public void testApiGatewayCorsConfiguration() {
        // Test CORS preflight request
        HttpHeaders preflightHeaders = new HttpHeaders();
        preflightHeaders.set("Origin", "https://app.dollarfunding.com");
        preflightHeaders.set("Access-Control-Request-Method", "GET");
        preflightHeaders.set("Access-Control-Request-Headers", "Authorization,Content-Type");
        
        ResponseEntity<String> response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.OPTIONS,
                new HttpEntity<>(preflightHeaders),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Verify CORS headers
        HttpHeaders responseHeaders = response.getHeaders();
        assertTrue(responseHeaders.containsKey("Access-Control-Allow-Origin"));
        assertTrue(responseHeaders.containsKey("Access-Control-Allow-Methods"));
        assertTrue(responseHeaders.containsKey("Access-Control-Allow-Headers"));
        assertTrue(responseHeaders.containsKey("Access-Control-Max-Age"));
        
        // Verify allowed origin
        assertEquals("https://app.dollarfunding.com", responseHeaders.getFirst("Access-Control-Allow-Origin"));
        
        // Verify allowed methods include GET, POST, PUT, DELETE
        String allowedMethods = responseHeaders.getFirst("Access-Control-Allow-Methods");
        assertTrue(allowedMethods.contains("GET"));
        assertTrue(allowedMethods.contains("POST"));
        assertTrue(allowedMethods.contains("PUT"));
        assertTrue(allowedMethods.contains("DELETE"));
        
        // Verify allowed headers include Authorization and Content-Type
        String allowedHeaders = responseHeaders.getFirst("Access-Control-Allow-Headers");
        assertTrue(allowedHeaders.contains("Authorization"));
        assertTrue(allowedHeaders.contains("Content-Type"));
        
        // Test CORS with disallowed origin
        HttpHeaders disallowedOriginHeaders = new HttpHeaders();
        disallowedOriginHeaders.set("Origin", "https://malicious-site.com");
        disallowedOriginHeaders.set("Access-Control-Request-Method", "GET");
        
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.OPTIONS,
                new HttpEntity<>(disallowedOriginHeaders),
                String.class);
        
        // The response should not include CORS headers for disallowed origins
        responseHeaders = response.getHeaders();
        assertFalse(responseHeaders.containsKey("Access-Control-Allow-Origin") && 
                   responseHeaders.getFirst("Access-Control-Allow-Origin").equals("https://malicious-site.com"));
    }

    /**
     * Tests that the API Gateway properly routes requests to the appropriate endpoints.
     */
    @Test
    @DisplayName("Test API Gateway routing")
    public void testApiGatewayRouting() throws Exception {
        // Setup headers
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + systemAdminToken);
        headers.setContentType(MediaType.APPLICATION_JSON);
        
        // Test routing to applications endpoint
        ResponseEntity<String> response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Test routing to documents endpoint
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/documents",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Test routing to webhooks endpoint
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/webhooks",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        
        assertEquals(HttpStatus.OK, response.getStatusCode());
        
        // Test routing to non-existent endpoint
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/non-existent",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        
        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        
        // Test creating an application through the gateway
        ApplicationDto applicationDto = new ApplicationDto();
        applicationDto.setStatus("new");
        applicationDto.setMetadata("{\"source\": \"email\"}");
        
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.POST,
                new HttpEntity<>(objectMapper.writeValueAsString(applicationDto), headers),
                String.class);
        
        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        assertTrue(response.getBody().contains("id"));
    }

    /**
     * Tests that the API Gateway returns standardized error responses.
     */
    @Test
    @DisplayName("Test API Gateway standardized error responses")
    public void testApiGatewayStandardizedErrorResponses() throws Exception {
        // Setup headers
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + systemAdminToken);
        headers.setContentType(MediaType.APPLICATION_JSON);
        
        // Test invalid request body
        String invalidJson = "{invalid_json}";
        
        ResponseEntity<String> response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.POST,
                new HttpEntity<>(invalidJson, headers),
                String.class);
        
        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertTrue(response.getBody().contains("error"));
        assertTrue(response.getBody().contains("message"));
        assertTrue(response.getBody().contains("timestamp"));
        assertTrue(response.getBody().contains("path"));
        
        // Test validation error
        ApplicationDto invalidApplication = new ApplicationDto();
        // Missing required fields
        
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications",
                HttpMethod.POST,
                new HttpEntity<>(objectMapper.writeValueAsString(invalidApplication), headers),
                String.class);
        
        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertTrue(response.getBody().contains("error"));
        assertTrue(response.getBody().contains("message"));
        assertTrue(response.getBody().contains("timestamp"));
        assertTrue(response.getBody().contains("path"));
        assertTrue(response.getBody().contains("fieldErrors"));
        
        // Test resource not found
        response = restTemplate.exchange(
                kongGatewayUrl + "/api/v1/applications/999999",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        
        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertTrue(response.getBody().contains("error"));
        assertTrue(response.getBody().contains("message"));
        assertTrue(response.getBody().contains("timestamp"));
        assertTrue(response.getBody().contains("path"));
    }
}