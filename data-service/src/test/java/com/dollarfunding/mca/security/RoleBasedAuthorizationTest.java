package com.dollarfunding.mca.security;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import com.dollarfunding.mca.config.SecurityConfig;

/**
 * Tests for role-based authorization in the MCA application.
 * Verifies that the application correctly enforces role-based access control
 * according to the technical requirements.
 */
@WebMvcTest
@Import(SecurityConfig.class)
public class RoleBasedAuthorizationTest {

    @Autowired
    private MockMvc mockMvc;

    /**
     * Test setup
     */
    @BeforeEach
    public void setup() {
        // Additional setup if needed
    }

    /**
     * Tests for Operations Staff role authorization
     */
    @Test
    @DisplayName("Operations Staff should be able to read application data")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    public void operationsStaffCanReadApplicationData() throws Exception {
        mockMvc.perform(get("/api/v1/applications"))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("Operations Staff should be able to write application data")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    public void operationsStaffCanWriteApplicationData() throws Exception {
        mockMvc.perform(post("/api/v1/applications")
                .contentType("application/json")
                .content("{\"merchantName\":\"Test Merchant\",\"amount\":10000}"))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("Operations Staff should not be able to access webhook configuration")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    public void operationsStaffCannotAccessWebhookConfig() throws Exception {
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isForbidden());
    }

    /**
     * Tests for System Admin role authorization
     */
    @Test
    @DisplayName("System Admin should have full access to applications")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void systemAdminCanAccessApplications() throws Exception {
        mockMvc.perform(get("/api/v1/applications"))
                .andExpect(status().isOk());

        mockMvc.perform(post("/api/v1/applications")
                .contentType("application/json")
                .content("{\"merchantName\":\"Test Merchant\",\"amount\":10000}"))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("System Admin should have full access to webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void systemAdminCanAccessWebhookConfig() throws Exception {
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isOk());

        mockMvc.perform(post("/api/v1/webhooks")
                .contentType("application/json")
                .content("{\"url\":\"https://example.com/webhook\",\"events\":[\"application.created\"]}")
                .andExpect(status().isOk()));
    }

    @Test
    @DisplayName("System Admin should have full access to documents")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void systemAdminCanAccessDocuments() throws Exception {
        mockMvc.perform(get("/api/v1/documents"))
                .andExpect(status().isOk());
    }

    /**
     * Tests for unauthorized role scenarios
     */
    @Test
    @DisplayName("Unauthenticated users should not be able to access protected resources")
    public void unauthenticatedUserCannotAccessProtectedResources() throws Exception {
        mockMvc.perform(get("/api/v1/applications"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/documents"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("Users with invalid roles should not be able to access protected resources")
    @WithMockUser(roles = {"INVALID_ROLE"})
    public void invalidRoleCannotAccessProtectedResources() throws Exception {
        mockMvc.perform(get("/api/v1/applications"))
                .andExpect(status().isForbidden());

        mockMvc.perform(get("/api/v1/documents"))
                .andExpect(status().isForbidden());

        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isForbidden());
    }

    /**
     * Tests for role-based access to protected endpoints
     */
    @Test
    @DisplayName("JWT authentication with Operations Staff role should work")
    public void jwtAuthenticationWithOperationsStaffRole() throws Exception {
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().jwt(token -> token.claim("roles", "ROLE_OPERATIONS_STAFF"))))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("JWT authentication with System Admin role should work")
    public void jwtAuthenticationWithSystemAdminRole() throws Exception {
        mockMvc.perform(get("/api/v1/webhooks")
                .with(jwt().jwt(token -> token.claim("roles", "ROLE_SYSTEM_ADMIN"))))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("JWT authentication with invalid role should be forbidden")
    public void jwtAuthenticationWithInvalidRole() throws Exception {
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().jwt(token -> token.claim("roles", "ROLE_INVALID"))))
                .andExpect(status().isForbidden());
    }

    /**
     * Tests for integration with Spring Security authorization framework
     */
    @Test
    @DisplayName("JWT token expiry should be enforced")
    public void jwtTokenExpiryShouldBeEnforced() throws Exception {
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().jwt(token -> token
                        .claim("roles", "ROLE_OPERATIONS_STAFF")
                        .expiresAt(System.currentTimeMillis() / 1000 - 3600) // Expired 1 hour ago
                )))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("JWT token algorithm should be RS256")
    public void jwtTokenAlgorithmShouldBeRS256() throws Exception {
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt()
                        .algorithm("RS256")
                        .jwt(token -> token.claim("roles", "ROLE_OPERATIONS_STAFF"))))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("JWT token with wrong algorithm should be rejected")
    public void jwtTokenWithWrongAlgorithmShouldBeRejected() throws Exception {
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt()
                        .algorithm("HS256") // Wrong algorithm
                        .jwt(token -> token.claim("roles", "ROLE_OPERATIONS_STAFF"))))
                .andExpect(status().isUnauthorized());
    }
}