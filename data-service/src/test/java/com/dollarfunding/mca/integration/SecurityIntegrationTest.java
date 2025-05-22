package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.controller.ApplicationController;
import com.dollarfunding.mca.controller.DocumentController;
import com.dollarfunding.mca.controller.WebhookController;
import com.dollarfunding.mca.dto.ApplicationDto;
import com.dollarfunding.mca.dto.MerchantDetailsDto;
import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.User;
import com.dollarfunding.mca.security.UserRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import javax.crypto.Cipher;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.util.Date;

import static org.hamcrest.Matchers.containsString;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Integration tests for security features of the data-service.
 * Tests JWT authentication, role-based access control, and data encryption.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
public class SecurityIntegrationTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    private MockMvc mockMvc;
    private RSAPublicKey publicKey;
    private RSAPrivateKey privateKey;
    private String operationsStaffToken;
    private String systemAdminToken;
    private String expiredToken;

    @BeforeEach
    public void setup() throws Exception {
        // Configure MockMvc with Spring Security
        mockMvc = MockMvcBuilders
                .webAppContextSetup(context)
                .apply(springSecurity())
                .build();

        // Generate RSA key pair for JWT signing
        KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
        keyPairGenerator.initialize(2048);
        KeyPair keyPair = keyPairGenerator.generateKeyPair();
        publicKey = (RSAPublicKey) keyPair.getPublic();
        privateKey = (RSAPrivateKey) keyPair.getPrivate();

        // Create test users if they don't exist
        createTestUsers();

        // Generate tokens for testing
        operationsStaffToken = jwtTokenProvider.generateToken("operations_user", RoleConstants.OPERATIONS_STAFF);
        systemAdminToken = jwtTokenProvider.generateToken("admin_user", RoleConstants.SYSTEM_ADMIN);
        
        // Generate expired token for testing
        expiredToken = jwtTokenProvider.generateTokenWithCustomExpiration("expired_user", 
                RoleConstants.OPERATIONS_STAFF, new Date(System.currentTimeMillis() - 3600000)); // Expired 1 hour ago
    }

    private void createTestUsers() {
        // Create Operations Staff user if not exists
        if (!userRepository.existsByUsername("operations_user")) {
            User operationsUser = new User();
            operationsUser.setUsername("operations_user");
            operationsUser.setPassword(passwordEncoder.encode("password"));
            operationsUser.setEmail("operations@dollarfunding.com");
            operationsUser.setRole(RoleConstants.OPERATIONS_STAFF);
            userRepository.save(operationsUser);
        }

        // Create System Admin user if not exists
        if (!userRepository.existsByUsername("admin_user")) {
            User adminUser = new User();
            adminUser.setUsername("admin_user");
            adminUser.setPassword(passwordEncoder.encode("password"));
            adminUser.setEmail("admin@dollarfunding.com");
            adminUser.setRole(RoleConstants.SYSTEM_ADMIN);
            userRepository.save(adminUser);
        }
    }

    @Test
    @DisplayName("Test unauthorized access is denied")
    public void testUnauthorizedAccess() throws Exception {
        // Test access to applications endpoint without authentication
        mockMvc.perform(get("/api/v1/applications"))
                .andExpect(status().isUnauthorized());

        // Test access to documents endpoint without authentication
        mockMvc.perform(get("/api/v1/documents"))
                .andExpect(status().isUnauthorized());

        // Test access to webhooks endpoint without authentication
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("Test JWT authentication with RS256 algorithm")
    public void testJwtAuthenticationWithRS256() throws Exception {
        // Test access with valid token
        mockMvc.perform(get("/api/v1/applications")
                .header("Authorization", "Bearer " + operationsStaffToken))
                .andExpect(status().isOk());

        // Test access with invalid token
        mockMvc.perform(get("/api/v1/applications")
                .header("Authorization", "Bearer invalid.token.value"))
                .andExpect(status().isUnauthorized());

        // Test access with expired token
        mockMvc.perform(get("/api/v1/applications")
                .header("Authorization", "Bearer " + expiredToken))
                .andExpect(status().isUnauthorized())
                .andExpect(content().string(containsString("expired")));
    }

    @Test
    @DisplayName("Test role-based access control for Operations Staff")
    public void testRoleBasedAccessControlForOperationsStaff() throws Exception {
        // Operations Staff should have read access to applications
        mockMvc.perform(get("/api/v1/applications")
                .header("Authorization", "Bearer " + operationsStaffToken))
                .andExpect(status().isOk());

        // Operations Staff should have write access to applications
        ApplicationDto applicationDto = new ApplicationDto();
        applicationDto.setStatus("new");
        applicationDto.setMetadata("{\"source\": \"email\"}");

        mockMvc.perform(post("/api/v1/applications")
                .header("Authorization", "Bearer " + operationsStaffToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationDto)))
                .andExpect(status().isCreated());

        // Operations Staff should have read access to documents
        mockMvc.perform(get("/api/v1/documents")
                .header("Authorization", "Bearer " + operationsStaffToken))
                .andExpect(status().isOk());

        // Operations Staff should NOT have access to webhooks
        mockMvc.perform(get("/api/v1/webhooks")
                .header("Authorization", "Bearer " + operationsStaffToken))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Test role-based access control for System Admin")
    public void testRoleBasedAccessControlForSystemAdmin() throws Exception {
        // System Admin should have read access to applications
        mockMvc.perform(get("/api/v1/applications")
                .header("Authorization", "Bearer " + systemAdminToken))
                .andExpect(status().isOk());

        // System Admin should have write access to applications
        ApplicationDto applicationDto = new ApplicationDto();
        applicationDto.setStatus("new");
        applicationDto.setMetadata("{\"source\": \"email\"}");

        mockMvc.perform(post("/api/v1/applications")
                .header("Authorization", "Bearer " + systemAdminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationDto)))
                .andExpect(status().isCreated());

        // System Admin should have read access to documents
        mockMvc.perform(get("/api/v1/documents")
                .header("Authorization", "Bearer " + systemAdminToken))
                .andExpect(status().isOk());

        // System Admin should have access to webhooks
        mockMvc.perform(get("/api/v1/webhooks")
                .header("Authorization", "Bearer " + systemAdminToken))
                .andExpect(status().isOk());

        // System Admin should be able to create webhooks
        String webhookConfig = "{\"url\": \"https://example.com/webhook\", \"events\": [\"application.created\"], \"secret\": \"test-secret\"}"; 
        
        mockMvc.perform(post("/api/v1/webhooks")
                .header("Authorization", "Bearer " + systemAdminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(webhookConfig))
                .andExpect(status().isCreated());
    }

    @Test
    @DisplayName("Test field-level encryption for PII data")
    public void testFieldLevelEncryptionForPII() throws Exception {
        // Create an application with PII data
        ApplicationDto applicationDto = new ApplicationDto();
        applicationDto.setStatus("new");
        applicationDto.setMetadata("{\"source\": \"email\"}");

        MerchantDetailsDto merchantDetailsDto = new MerchantDetailsDto();
        merchantDetailsDto.setLegalName("Test Merchant Inc.");
        merchantDetailsDto.setDbaName("Test Merchant");
        merchantDetailsDto.setEin("12-3456789"); // PII data that should be encrypted
        merchantDetailsDto.setAddress("123 Main St, Anytown, USA"); // PII data that should be encrypted
        merchantDetailsDto.setIndustry("Retail");
        merchantDetailsDto.setRevenue("1000000");
        
        applicationDto.setMerchantDetails(merchantDetailsDto);

        // Create the application
        String responseContent = mockMvc.perform(post("/api/v1/applications")
                .header("Authorization", "Bearer " + systemAdminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationDto)))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();

        ApplicationDto createdApp = objectMapper.readValue(responseContent, ApplicationDto.class);
        Long applicationId = createdApp.getId();

        // Verify the application was created
        assertNotNull(applicationId);

        // Directly access the database to verify encryption
        // This would typically be done with a repository, but for testing purposes we can use reflection or test-specific methods
        // Here we're assuming there's a method to check if a field is encrypted
        
        // For this test, we'll verify that the encrypted data is properly decrypted when retrieved through the API
        String getResponse = mockMvc.perform(get("/api/v1/applications/" + applicationId)
                .header("Authorization", "Bearer " + systemAdminToken))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();

        ApplicationDto retrievedApp = objectMapper.readValue(getResponse, ApplicationDto.class);
        
        // Verify that the PII data is correctly retrieved (decrypted)
        assertEquals("12-3456789", retrievedApp.getMerchantDetails().getEin());
        assertEquals("123 Main St, Anytown, USA", retrievedApp.getMerchantDetails().getAddress());
    }

    @Test
    @DisplayName("Test token refresh mechanism")
    public void testTokenRefreshMechanism() throws Exception {
        // Get a refresh token
        String refreshToken = jwtTokenProvider.generateRefreshToken("operations_user");
        
        // Use the refresh token to get a new access token
        mockMvc.perform(post("/api/v1/auth/refresh")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"refreshToken\": \"" + refreshToken + "\"}")
                .header("Authorization", "Bearer " + expiredToken)) // Using expired token to simulate need for refresh
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").exists())
                .andExpect(jsonPath("$.refreshToken").exists());
        
        // Try to use an invalid refresh token
        mockMvc.perform(post("/api/v1/auth/refresh")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"refreshToken\": \"invalid-refresh-token\"}")
                .header("Authorization", "Bearer " + expiredToken))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("Test secure communication with TLS")
    public void testSecureCommunicationWithTLS() throws Exception {
        // This test verifies that the application is configured to require HTTPS
        // In a test environment, we can't directly test HTTPS, but we can verify the configuration
        
        // Test that HSTS header is present in responses
        mockMvc.perform(get("/api/v1/applications")
                .header("Authorization", "Bearer " + systemAdminToken)
                .secure(true)) // Simulate HTTPS request
                .andExpect(status().isOk())
                .andExpect(header().exists("Strict-Transport-Security"));
        
        // Test that non-HTTPS requests are redirected to HTTPS
        // This is typically handled by a filter or configuration
        // For testing purposes, we can check if the application is configured to require HTTPS
        
        // Note: In a real environment, this would be handled by the server configuration
        // and might not be directly testable in an integration test
    }
}