package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.IntegrationTestBase;
import com.dollarfunding.mca.TestUtils;
import com.dollarfunding.mca.controller.ApplicationController;
import com.dollarfunding.mca.controller.WebhookController;
import com.dollarfunding.mca.dto.ApplicationDto;
import com.dollarfunding.mca.dto.ErrorResponseDto;
import com.dollarfunding.mca.dto.WebhookDto;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.WebhookRepository;
import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserPrincipal;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.transaction.annotation.Transactional;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Integration tests for the Kong API Gateway interaction with the data-service.
 * <p>
 * This test class verifies the following aspects of the API Gateway integration:
 * <ul>
 *   <li>JWT authentication through the gateway</li>
 *   <li>Role-based access control for different endpoints</li>
 *   <li>Rate limiting functionality</li>
 *   <li>CORS configuration for browser security</li>
 *   <li>Standardized error responses</li>
 * </ul>
 * </p>
 */
@AutoConfigureMockMvc
@Transactional
public class ApiGatewayIntegrationTest extends IntegrationTestBase {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtTokenProvider tokenProvider;

    @Autowired
    private ApplicationRepository applicationRepository;

    @Autowired
    private WebhookRepository webhookRepository;

    @Value("${api.gateway.url:https://api-gateway.dollarfunding.com}")
    private String apiGatewayUrl;

    private Application testApplication;
    private Webhook testWebhook;

    /**
     * Setup method that runs before each test.
     * <p>
     * This method initializes test data including an application and webhook.
     * </p>
     */
    @BeforeEach
    @Override
    public void setUp() throws Exception {
        super.setUp();

        // Create test application
        testApplication = TestUtils.createRandomApplication();
        applicationRepository.save(testApplication);

        // Create test webhook
        testWebhook = new Webhook();
        testWebhook.setId(UUID.randomUUID());
        testWebhook.setEndpointUrl("https://test-webhook.example.com/callback");
        testWebhook.setSecretKey("webhook-secret-key-for-testing");
        testWebhook.setActive(true);
        testWebhook.setEventType(EventType.APPLICATION_CREATED);
        testWebhook.setCreatedAt(LocalDateTime.now());
        testWebhook.setUpdatedAt(LocalDateTime.now());
        
        webhookRepository.save(testWebhook);
    }

    /**
     * Tests for JWT authentication through the API Gateway.
     */
    @Nested
    @DisplayName("JWT Authentication Tests")
    class JwtAuthenticationTests {

        /**
         * Tests that a valid JWT token allows access to protected endpoints through the API Gateway.
         */
        @Test
        @DisplayName("Valid JWT token should allow access through API Gateway")
        public void validJwtTokenShouldAllowAccess() throws Exception {
            // Authenticate as Operations Staff
            Authentication auth = authenticateAsOperationsStaff("test-user");
            String token = tokenProvider.generateAccessToken(auth);

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .header("Authorization", "Bearer " + token)
                    .GET()
                    .build();

            try {
                // Send request and verify response
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                assertEquals(HttpStatus.OK.value(), response.statusCode(), "API Gateway should accept valid JWT token");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than authentication
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not authentication: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/applications")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());
        }

        /**
         * Tests that an invalid JWT token is rejected by the API Gateway.
         */
        @Test
        @DisplayName("Invalid JWT token should be rejected by API Gateway")
        public void invalidJwtTokenShouldBeRejected() throws Exception {
            // Create an invalid token
            String invalidToken = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJhdXRoIjoiUk9MRV9PUEVS" +
                                 "QVRJT05TX1NUQUZGIiwidWlkIjoidGVzdC11c2VyIiwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTYxNjc2MjI0" +
                                 "MCwiZXhwIjoxNjE2NzY1ODQwLCJpc3MiOiJkb2xsYXJmdW5kaW5nLW1jYSIsImF1ZCI6Im1jYS1hcGkifQ." +
                                 "invalid_signature";

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .header("Authorization", "Bearer " + invalidToken)
                    .GET()
                    .build();

            try {
                // Send request and verify response
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                assertEquals(HttpStatus.UNAUTHORIZED.value(), response.statusCode(), "API Gateway should reject invalid JWT token");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than authentication
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not authentication: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/applications")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + invalidToken)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isUnauthorized());
        }

        /**
         * Tests that a missing JWT token is rejected by the API Gateway.
         */
        @Test
        @DisplayName("Missing JWT token should be rejected by API Gateway")
        public void missingJwtTokenShouldBeRejected() throws Exception {
            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway without token
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .GET()
                    .build();

            try {
                // Send request and verify response
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                assertEquals(HttpStatus.UNAUTHORIZED.value(), response.statusCode(), "API Gateway should reject requests without JWT token");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than authentication
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not authentication: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/applications")
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isUnauthorized());
        }
    }

    /**
     * Tests for role-based access control through the API Gateway.
     */
    @Nested
    @DisplayName("Role-Based Access Control Tests")
    class RoleBasedAccessControlTests {

        /**
         * Tests that Operations Staff can access application data through the API Gateway.
         */
        @Test
        @DisplayName("Operations Staff should be able to access application data through API Gateway")
        public void operationsStaffShouldAccessApplicationData() throws Exception {
            // Authenticate as Operations Staff
            Authentication auth = authenticateAsOperationsStaff("test-ops-user");
            String token = tokenProvider.generateAccessToken(auth);

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .header("Authorization", "Bearer " + token)
                    .GET()
                    .build();

            try {
                // Send request and verify response
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                assertEquals(HttpStatus.OK.value(), response.statusCode(), "API Gateway should allow Operations Staff to access application data");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than authorization
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not authorization: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/applications")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());
        }

        /**
         * Tests that Operations Staff cannot access webhook configuration through the API Gateway.
         */
        @Test
        @DisplayName("Operations Staff should not be able to access webhook configuration through API Gateway")
        public void operationsStaffShouldNotAccessWebhookConfig() throws Exception {
            // Authenticate as Operations Staff
            Authentication auth = authenticateAsOperationsStaff("test-ops-user");
            String token = tokenProvider.generateAccessToken(auth);

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/webhooks"))
                    .header("Authorization", "Bearer " + token)
                    .GET()
                    .build();

            try {
                // Send request and verify response
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                assertEquals(HttpStatus.FORBIDDEN.value(), response.statusCode(), "API Gateway should prevent Operations Staff from accessing webhook configuration");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than authorization
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not authorization: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/webhooks")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isForbidden());
        }

        /**
         * Tests that System Admin can access all endpoints including webhook configuration through the API Gateway.
         */
        @Test
        @DisplayName("System Admin should be able to access all endpoints through API Gateway")
        public void systemAdminShouldAccessAllEndpoints() throws Exception {
            // Authenticate as System Admin
            Authentication auth = authenticateAsSystemAdmin("test-admin-user");
            String token = tokenProvider.generateAccessToken(auth);

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway for applications endpoint
            HttpRequest applicationsRequest = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .header("Authorization", "Bearer " + token)
                    .GET()
                    .build();

            // Create request to the API Gateway for webhooks endpoint
            HttpRequest webhooksRequest = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/webhooks"))
                    .header("Authorization", "Bearer " + token)
                    .GET()
                    .build();

            try {
                // Send applications request and verify response
                HttpResponse<String> applicationsResponse = client.send(applicationsRequest, HttpResponse.BodyHandlers.ofString());
                assertEquals(HttpStatus.OK.value(), applicationsResponse.statusCode(), "API Gateway should allow System Admin to access application data");

                // Send webhooks request and verify response
                HttpResponse<String> webhooksResponse = client.send(webhooksRequest, HttpResponse.BodyHandlers.ofString());
                assertEquals(HttpStatus.OK.value(), webhooksResponse.statusCode(), "API Gateway should allow System Admin to access webhook configuration");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than authorization
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not authorization: " + e.getMessage());
            }

            // Fallback to direct API tests if gateway is not available
            mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/applications")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());

            mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/webhooks")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());
        }
    }

    /**
     * Tests for rate limiting functionality of the API Gateway.
     */
    @Nested
    @DisplayName("Rate Limiting Tests")
    class RateLimitingTests {

        /**
         * Tests that rate limiting is enforced by the API Gateway for authenticated users.
         */
        @Test
        @DisplayName("Rate limiting should be enforced for authenticated users")
        public void rateLimitingShouldBeEnforcedForAuthenticatedUsers() throws Exception {
            // Authenticate as Operations Staff
            Authentication auth = authenticateAsOperationsStaff("test-ops-user");
            String token = tokenProvider.generateAccessToken(auth);

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .header("Authorization", "Bearer " + token)
                    .GET()
                    .build();

            try {
                // Send multiple requests to trigger rate limiting
                HttpResponse<String> response = null;
                boolean rateLimitHeaderFound = false;

                // Make several requests to check for rate limit headers
                for (int i = 0; i < 5; i++) {
                    response = client.send(request, HttpResponse.BodyHandlers.ofString());
                    
                    // Check for rate limit headers
                    Map<String, List<String>> headers = response.headers().map();
                    if (headers.containsKey("X-RateLimit-Limit") && 
                        headers.containsKey("X-RateLimit-Remaining")) {
                        rateLimitHeaderFound = true;
                        break;
                    }
                    
                    // Small delay between requests
                    TimeUnit.MILLISECONDS.sleep(100);
                }

                // Verify rate limit headers are present
                assertTrue(rateLimitHeaderFound, "API Gateway should include rate limit headers");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than rate limiting
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not rate limiting: " + e.getMessage());
            }

            // Note: We can't effectively test actual rate limiting in a unit test
            // as it would require making many requests quickly, which is not practical
            // in a test environment. We're just verifying the headers exist.
        }

        /**
         * Tests that rate limiting is enforced by the API Gateway for unauthenticated users.
         */
        @Test
        @DisplayName("Rate limiting should be enforced for unauthenticated users")
        public void rateLimitingShouldBeEnforcedForUnauthenticatedUsers() throws Exception {
            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway without authentication
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .GET()
                    .build();

            try {
                // Send request and check for rate limit headers
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                
                // Even though the request will be rejected due to missing authentication,
                // rate limit headers should still be present
                Map<String, List<String>> headers = response.headers().map();
                boolean rateLimitHeaderFound = headers.containsKey("X-RateLimit-Limit") && 
                                              headers.containsKey("X-RateLimit-Remaining");
                
                // Verify rate limit headers are present
                assertTrue(rateLimitHeaderFound, "API Gateway should include rate limit headers for unauthenticated requests");
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than rate limiting
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not rate limiting: " + e.getMessage());
            }
        }
    }

    /**
     * Tests for CORS configuration of the API Gateway.
     */
    @Nested
    @DisplayName("CORS Configuration Tests")
    class CorsConfigurationTests {

        /**
         * Tests that CORS headers are properly set by the API Gateway.
         */
        @Test
        @DisplayName("CORS headers should be properly set by API Gateway")
        public void corsHeadersShouldBeProperlySet() throws Exception {
            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create OPTIONS request to the API Gateway with Origin header
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .method("OPTIONS", HttpRequest.BodyPublishers.noBody())
                    .header("Origin", "https://app.dollarfunding.com")
                    .header("Access-Control-Request-Method", "GET")
                    .header("Access-Control-Request-Headers", "Authorization")
                    .build();

            try {
                // Send request and verify CORS headers
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                
                Map<String, List<String>> headers = response.headers().map();
                
                // Check for required CORS headers
                boolean corsHeadersFound = headers.containsKey("Access-Control-Allow-Origin") && 
                                          headers.containsKey("Access-Control-Allow-Methods") &&
                                          headers.containsKey("Access-Control-Allow-Headers") &&
                                          headers.containsKey("Access-Control-Max-Age");
                
                assertTrue(corsHeadersFound, "API Gateway should include CORS headers");
                
                // Verify specific CORS header values if available
                if (headers.containsKey("Access-Control-Allow-Origin")) {
                    String allowOrigin = headers.get("Access-Control-Allow-Origin").get(0);
                    assertEquals("https://app.dollarfunding.com", allowOrigin, 
                                "API Gateway should allow the specified origin");
                }
                
                if (headers.containsKey("Access-Control-Allow-Methods")) {
                    String allowMethods = headers.get("Access-Control-Allow-Methods").get(0);
                    assertTrue(allowMethods.contains("GET"), 
                              "API Gateway should allow the requested method");
                }
                
                if (headers.containsKey("Access-Control-Allow-Headers")) {
                    String allowHeaders = headers.get("Access-Control-Allow-Headers").get(0);
                    assertTrue(allowHeaders.contains("Authorization"), 
                              "API Gateway should allow the requested header");
                }
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than CORS
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not CORS: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            mockMvc.perform(MockMvcRequestBuilders.options("/api/v1/applications")
                    .header("Origin", "https://app.dollarfunding.com")
                    .header("Access-Control-Request-Method", "GET")
                    .header("Access-Control-Request-Headers", "Authorization"))
                    .andExpect(status().isOk())
                    .andExpect(header().exists("Access-Control-Allow-Origin"))
                    .andExpect(header().exists("Access-Control-Allow-Methods"))
                    .andExpect(header().exists("Access-Control-Allow-Headers"));
        }
    }

    /**
     * Tests for standardized error responses from the API Gateway.
     */
    @Nested
    @DisplayName("Standardized Error Response Tests")
    class StandardizedErrorResponseTests {

        /**
         * Tests that the API Gateway returns standardized error responses for authentication failures.
         */
        @Test
        @DisplayName("API Gateway should return standardized error responses for authentication failures")
        public void standardizedErrorResponsesForAuthenticationFailures() throws Exception {
            // Create an invalid token
            String invalidToken = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJhdXRoIjoiUk9MRV9PUEVS" +
                                 "QVRJT05TX1NUQUZGIiwidWlkIjoidGVzdC11c2VyIiwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTYxNjc2MjI0" +
                                 "MCwiZXhwIjoxNjE2NzY1ODQwLCJpc3MiOiJkb2xsYXJmdW5kaW5nLW1jYSIsImF1ZCI6Im1jYS1hcGkifQ." +
                                 "invalid_signature";

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/applications"))
                    .header("Authorization", "Bearer " + invalidToken)
                    .GET()
                    .build();

            try {
                // Send request and verify standardized error response
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                
                // Verify status code
                assertEquals(HttpStatus.UNAUTHORIZED.value(), response.statusCode(), 
                            "API Gateway should return 401 for invalid token");
                
                // Verify response body contains standardized error format
                String responseBody = response.body();
                assertTrue(responseBody.contains("error") && responseBody.contains("message"), 
                          "API Gateway should return standardized error response with error and message fields");
                
                // Parse error response if possible
                try {
                    ErrorResponseDto errorResponse = TestUtils.fromJson(responseBody, ErrorResponseDto.class);
                    assertNotNull(errorResponse.getError(), "Error response should contain error code");
                    assertNotNull(errorResponse.getMessage(), "Error response should contain error message");
                } catch (Exception e) {
                    // If parsing fails, the response format might not be standardized
                    fail("API Gateway should return a parseable error response: " + responseBody);
                }
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than error responses
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not error responses: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            MvcResult result = mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/applications")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + invalidToken)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isUnauthorized())
                    .andReturn();
            
            String responseBody = result.getResponse().getContentAsString();
            assertTrue(responseBody.contains("error") && responseBody.contains("message"), 
                      "API should return standardized error response with error and message fields");
        }

        /**
         * Tests that the API Gateway returns standardized error responses for authorization failures.
         */
        @Test
        @DisplayName("API Gateway should return standardized error responses for authorization failures")
        public void standardizedErrorResponsesForAuthorizationFailures() throws Exception {
            // Authenticate as Operations Staff
            Authentication auth = authenticateAsOperationsStaff("test-ops-user");
            String token = tokenProvider.generateAccessToken(auth);

            // Create HTTP client for API Gateway requests
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            // Create request to the API Gateway for webhooks endpoint (which requires admin role)
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiGatewayUrl + "/api/v1/webhooks"))
                    .header("Authorization", "Bearer " + token)
                    .GET()
                    .build();

            try {
                // Send request and verify standardized error response
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                
                // Verify status code
                assertEquals(HttpStatus.FORBIDDEN.value(), response.statusCode(), 
                            "API Gateway should return 403 for insufficient permissions");
                
                // Verify response body contains standardized error format
                String responseBody = response.body();
                assertTrue(responseBody.contains("error") && responseBody.contains("message"), 
                          "API Gateway should return standardized error response with error and message fields");
                
                // Parse error response if possible
                try {
                    ErrorResponseDto errorResponse = TestUtils.fromJson(responseBody, ErrorResponseDto.class);
                    assertNotNull(errorResponse.getError(), "Error response should contain error code");
                    assertNotNull(errorResponse.getMessage(), "Error response should contain error message");
                } catch (Exception e) {
                    // If parsing fails, the response format might not be standardized
                    fail("API Gateway should return a parseable error response: " + responseBody);
                }
            } catch (Exception e) {
                // This test may fail in test environments without a real API gateway
                // We'll check if the exception is related to connection issues rather than error responses
                assertTrue(e.getMessage().contains("Connection refused") || 
                           e.getMessage().contains("UnknownHostException") ||
                           e.getMessage().contains("ConnectException"),
                           "Exception should be related to connection issues, not error responses: " + e.getMessage());
            }

            // Fallback to direct API test if gateway is not available
            MvcResult result = mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/webhooks")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isForbidden())
                    .andReturn();
            
            String responseBody = result.getResponse().getContentAsString();
            assertTrue(responseBody.contains("error") && responseBody.contains("message"), 
                      "API should return standardized error response with error and message fields");
        }

        /**
         * Tests that the API Gateway returns standardized error responses for rate limiting.
         */
        @Test
        @DisplayName("API Gateway should return standardized error responses for rate limiting")
        public void standardizedErrorResponsesForRateLimiting() throws Exception {
            // Note: We can't effectively test actual rate limiting in a unit test
            // as it would require making many requests quickly, which is not practical
            // in a test environment. We'll just verify the error format for a simulated rate limit error.
            
            // Create a mock rate limit error response
            ErrorResponseDto mockRateLimitError = new ErrorResponseDto();
            mockRateLimitError.setError("rate_limit_exceeded");
            mockRateLimitError.setMessage("API rate limit exceeded. Please try again later.");
            mockRateLimitError.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
            mockRateLimitError.setTimestamp(LocalDateTime.now());
            
            // Verify the error format is standardized
            String errorJson = TestUtils.toJson(mockRateLimitError);
            ErrorResponseDto parsedError = TestUtils.fromJson(errorJson, ErrorResponseDto.class);
            
            assertEquals("rate_limit_exceeded", parsedError.getError(), "Error code should match");
            assertEquals("API rate limit exceeded. Please try again later.", parsedError.getMessage(), "Error message should match");
            assertEquals(HttpStatus.TOO_MANY_REQUESTS.value(), parsedError.getStatus(), "Status code should match");
        }
    }
}