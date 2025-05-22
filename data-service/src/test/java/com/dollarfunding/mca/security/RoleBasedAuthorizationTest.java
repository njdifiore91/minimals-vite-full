package com.dollarfunding.mca.security;

import com.dollarfunding.mca.controller.ApplicationController;
import com.dollarfunding.mca.controller.WebhookController;
import com.dollarfunding.mca.dto.ApplicationDto;
import com.dollarfunding.mca.dto.WebhookConfigDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import java.util.Collections;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Test class for role-based authorization that verifies the correct implementation of access control
 * based on user roles. It tests authorization for Operations Staff and System Admin roles, as well as
 * unauthorized roles, and role-based access to protected endpoints.
 */
@WebMvcTest({ApplicationController.class, WebhookController.class})
@Import(TestSecurityConfig.class)
public class RoleBasedAuthorizationTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private UserDetailsService userDetailsService;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    private MockMvc mockMvc;

    @BeforeEach
    public void setup() {
        mockMvc = MockMvcBuilders
                .webAppContextSetup(context)
                .apply(springSecurity())
                .build();

        // Mock the UserDetailsService to return a valid user
        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(1L)
                .username("testuser")
                .password("password")
                .email("test@example.com")
                .authorities(Collections.emptyList())
                .accountNonExpired(true)
                .accountNonLocked(true)
                .credentialsNonExpired(true)
                .enabled(true)
                .build();

        when(userDetailsService.loadUserByUsername("testuser")).thenReturn(userPrincipal);
        when(jwtTokenProvider.validateToken(any())).thenReturn(true);
    }

    /**
     * Test that Operations Staff can access application data (read).
     */
    @Test
    @DisplayName("Operations Staff can read application data")
    public void testOperationsStaffCanReadApplicationData() throws Exception {
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF))))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/v1/applications/1")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF))))
                .andExpect(status().isOk());
    }

    /**
     * Test that Operations Staff can create and update application data (write).
     */
    @Test
    @DisplayName("Operations Staff can write application data")
    public void testOperationsStaffCanWriteApplicationData() throws Exception {
        ApplicationDto applicationDto = new ApplicationDto();
        applicationDto.setStatus("PENDING");

        mockMvc.perform(post("/api/v1/applications")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)))
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationDto)))
                .andExpect(status().isCreated());

        mockMvc.perform(put("/api/v1/applications/1")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)))
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationDto)))
                .andExpect(status().isOk());
    }

    /**
     * Test that Operations Staff cannot delete application data.
     */
    @Test
    @DisplayName("Operations Staff cannot delete application data")
    public void testOperationsStaffCannotDeleteApplicationData() throws Exception {
        mockMvc.perform(delete("/api/v1/applications/1")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF))))
                .andExpect(status().isForbidden());
    }

    /**
     * Test that Operations Staff cannot access webhook configuration endpoints.
     */
    @Test
    @DisplayName("Operations Staff cannot access webhook configuration")
    public void testOperationsStaffCannotAccessWebhookConfiguration() throws Exception {
        mockMvc.perform(get("/api/v1/webhooks")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF))))
                .andExpect(status().isForbidden());

        WebhookConfigDto webhookConfigDto = new WebhookConfigDto();
        webhookConfigDto.setUrl("https://example.com/webhook");
        webhookConfigDto.setEvents(List.of("APPLICATION_CREATED"));

        mockMvc.perform(post("/api/v1/webhooks")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF)))
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(webhookConfigDto)))
                .andExpect(status().isForbidden());
    }

    /**
     * Test that System Admin can access application data (read).
     */
    @Test
    @DisplayName("System Admin can read application data")
    public void testSystemAdminCanReadApplicationData() throws Exception {
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN))))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/v1/applications/1")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN))))
                .andExpect(status().isOk());
    }

    /**
     * Test that System Admin can create and update application data (write).
     */
    @Test
    @DisplayName("System Admin can write application data")
    public void testSystemAdminCanWriteApplicationData() throws Exception {
        ApplicationDto applicationDto = new ApplicationDto();
        applicationDto.setStatus("PENDING");

        mockMvc.perform(post("/api/v1/applications")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)))
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationDto)))
                .andExpect(status().isCreated());

        mockMvc.perform(put("/api/v1/applications/1")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)))
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationDto)))
                .andExpect(status().isOk());
    }

    /**
     * Test that System Admin can delete application data.
     */
    @Test
    @DisplayName("System Admin can delete application data")
    public void testSystemAdminCanDeleteApplicationData() throws Exception {
        mockMvc.perform(delete("/api/v1/applications/1")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN))))
                .andExpect(status().isOk());
    }

    /**
     * Test that System Admin can access webhook configuration endpoints.
     */
    @Test
    @DisplayName("System Admin can access webhook configuration")
    public void testSystemAdminCanAccessWebhookConfiguration() throws Exception {
        mockMvc.perform(get("/api/v1/webhooks")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN))))
                .andExpect(status().isOk());

        WebhookConfigDto webhookConfigDto = new WebhookConfigDto();
        webhookConfigDto.setUrl("https://example.com/webhook");
        webhookConfigDto.setEvents(List.of("APPLICATION_CREATED"));

        mockMvc.perform(post("/api/v1/webhooks")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN)))
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(webhookConfigDto)))
                .andExpect(status().isCreated());
    }

    /**
     * Test that unauthorized users cannot access protected endpoints.
     */
    @Test
    @DisplayName("Unauthorized users cannot access protected endpoints")
    public void testUnauthorizedUsersCannotAccessProtectedEndpoints() throws Exception {
        // Without authentication
        mockMvc.perform(get("/api/v1/applications"))
                .andExpect(status().isUnauthorized());

        // With invalid role
        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().authorities(new SimpleGrantedAuthority("ROLE_INVALID"))))
                .andExpect(status().isForbidden());
    }

    /**
     * Test that users with invalid tokens cannot access protected endpoints.
     */
    @Test
    @DisplayName("Users with invalid tokens cannot access protected endpoints")
    public void testInvalidTokenCannotAccessProtectedEndpoints() throws Exception {
        // Mock the token validation to return false
        when(jwtTokenProvider.validateToken(any())).thenReturn(false);

        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF))))
                .andExpect(status().isUnauthorized());
    }

    /**
     * Test that expired tokens are rejected.
     */
    @Test
    @DisplayName("Expired tokens are rejected")
    public void testExpiredTokensAreRejected() throws Exception {
        // Mock the token validation to throw JwtException for expired token
        when(jwtTokenProvider.validateToken(any())).thenThrow(new JwtException("JWT token is expired"));

        mockMvc.perform(get("/api/v1/applications")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF))))
                .andExpect(status().isUnauthorized());
    }

    /**
     * Test that public endpoints are accessible without authentication.
     */
    @Test
    @DisplayName("Public endpoints are accessible without authentication")
    public void testPublicEndpointsAreAccessibleWithoutAuthentication() throws Exception {
        mockMvc.perform(get("/api/v1/public/health"))
                .andExpect(status().isOk());

        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk());
    }

    /**
     * Test that method-level security annotations work correctly.
     */
    @Test
    @DisplayName("Method-level security annotations work correctly")
    public void testMethodLevelSecurityAnnotations() throws Exception {
        // Test @PreAuthorize annotation with hasRole('OPERATIONS_STAFF')
        mockMvc.perform(get("/api/v1/applications/reports")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_OPERATIONS_STAFF))))
                .andExpect(status().isOk());

        // Test @PreAuthorize annotation with hasRole('SYSTEM_ADMIN')
        mockMvc.perform(get("/api/v1/applications/reports")
                .with(jwt().authorities(new SimpleGrantedAuthority(RoleConstants.ROLE_SYSTEM_ADMIN))))
                .andExpect(status().isOk());

        // Test @PreAuthorize annotation with hasRole('INVALID_ROLE')
        mockMvc.perform(get("/api/v1/applications/reports")
                .with(jwt().authorities(new SimpleGrantedAuthority("ROLE_INVALID"))))
                .andExpect(status().isForbidden());
    }
}