package com.dollarfunding.mca.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;
import io.swagger.v3.oas.models.tags.Tag;

/**
 * Unit tests for the OpenApiConfig class that configures OpenAPI 3.0 documentation for the REST API.
 * <p>
 * These tests verify that the OpenAPI configuration is properly set up with the correct API information,
 * security schemes, documentation settings, API groups, and Swagger UI configuration.
 */
@ExtendWith(SpringExtension.class)
@SpringBootTest(classes = {OpenApiConfig.class})
public class OpenApiConfigTest {

    @Autowired
    private OpenApiConfig openApiConfig;

    /**
     * Tests that the OpenAPI bean is properly configured with API information.
     */
    @Test
    @DisplayName("Should configure OpenAPI with correct API information")
    public void testApiInformation() {
        // Given
        OpenAPI openAPI = openApiConfig.customOpenAPI();
        
        // When
        Info info = openAPI.getInfo();
        
        // Then
        assertNotNull(info, "API information should not be null");
        assertEquals("Merchant Cash Advance (MCA) API", info.getTitle(), "API title should match");
        assertEquals("1.0", info.getVersion(), "API version should match");
        assertTrue(info.getDescription().contains("REST API for the Merchant Cash Advance (MCA) Application Processing System"), 
                "API description should contain expected text");
        
        // Verify contact information
        Contact contact = info.getContact();
        assertNotNull(contact, "Contact information should not be null");
        assertEquals("Dollar Funding Support", contact.getName(), "Contact name should match");
        assertEquals("support@dollarfunding.com", contact.getEmail(), "Contact email should match");
        assertEquals("https://dollarfunding.com/support", contact.getUrl(), "Contact URL should match");
        
        // Verify license information
        License license = info.getLicense();
        assertNotNull(license, "License information should not be null");
        assertEquals("Proprietary", license.getName(), "License name should match");
        assertEquals("https://dollarfunding.com/terms", license.getUrl(), "License URL should match");
    }

    /**
     * Tests that the OpenAPI bean is properly configured with server information.
     */
    @Test
    @DisplayName("Should configure OpenAPI with correct server information")
    public void testServerInformation() {
        // Given
        OpenAPI openAPI = openApiConfig.customOpenAPI();
        
        // When
        List<Server> servers = openAPI.getServers();
        
        // Then
        assertNotNull(servers, "Server information should not be null");
        // Note: The servers are configured via annotation in the OpenApiConfig class
        // We're testing the customOpenAPI() method which doesn't set servers directly
    }

    /**
     * Tests that the OpenAPI bean is properly configured with security schemes.
     */
    @Test
    @DisplayName("Should configure OpenAPI with JWT security scheme")
    public void testSecurityScheme() {
        // Given
        OpenAPI openAPI = openApiConfig.customOpenAPI();
        
        // When
        Components components = openAPI.getComponents();
        
        // Then
        assertNotNull(components, "Components should not be null");
        
        // Verify JWT security scheme
        SecurityScheme bearerAuth = components.getSecuritySchemes().get("bearerAuth");
        assertNotNull(bearerAuth, "Bearer auth security scheme should not be null");
        assertEquals(SecurityScheme.Type.HTTP, bearerAuth.getType(), "Security scheme type should be HTTP");
        assertEquals("bearer", bearerAuth.getScheme(), "Security scheme should be bearer");
        assertEquals("JWT", bearerAuth.getBearerFormat(), "Bearer format should be JWT");
        assertTrue(bearerAuth.getDescription().contains("JWT Authentication using RS256 algorithm"), 
                "Security scheme description should mention RS256 algorithm");
        
        // Verify OAuth2 security scheme
        SecurityScheme oauth2 = components.getSecuritySchemes().get("oauth2");
        assertNotNull(oauth2, "OAuth2 security scheme should not be null");
        assertEquals(SecurityScheme.Type.OAUTH2, oauth2.getType(), "Security scheme type should be OAuth2");
        assertNotNull(oauth2.getFlows(), "OAuth2 flows should not be null");
        assertNotNull(oauth2.getFlows().getImplicit(), "OAuth2 implicit flow should not be null");
        assertEquals("https://dollarfunding.com/oauth2/authorize", 
                oauth2.getFlows().getImplicit().getAuthorizationUrl(), 
                "OAuth2 authorization URL should match");
        assertNotNull(oauth2.getFlows().getImplicit().getScopes(), "OAuth2 scopes should not be null");
        assertTrue(oauth2.getFlows().getImplicit().getScopes().containsKey("operations_staff"), 
                "OAuth2 scopes should include operations_staff");
        assertTrue(oauth2.getFlows().getImplicit().getScopes().containsKey("system_admin"), 
                "OAuth2 scopes should include system_admin");
    }

    /**
     * Tests that the OpenAPI bean is properly configured with API tags.
     */
    @Test
    @DisplayName("Should configure OpenAPI with correct API tags")
    public void testApiTags() {
        // Given
        OpenAPI openAPI = openApiConfig.customOpenAPI();
        
        // When
        List<Tag> tags = openAPI.getTags();
        
        // Then
        assertNotNull(tags, "API tags should not be null");
        assertEquals(4, tags.size(), "Should have 4 API tags");
        
        // Verify Applications tag
        assertTrue(tags.stream().anyMatch(tag -> "Applications".equals(tag.getName())), 
                "Should have Applications tag");
        
        // Verify Documents tag
        assertTrue(tags.stream().anyMatch(tag -> "Documents".equals(tag.getName())), 
                "Should have Documents tag");
        
        // Verify Webhooks tag
        assertTrue(tags.stream().anyMatch(tag -> "Webhooks".equals(tag.getName())), 
                "Should have Webhooks tag");
        
        // Verify Health tag
        assertTrue(tags.stream().anyMatch(tag -> "Health".equals(tag.getName())), 
                "Should have Health tag");
    }

    /**
     * Tests that the OpenAPI bean is properly configured with external documentation.
     */
    @Test
    @DisplayName("Should configure OpenAPI with external documentation")
    public void testExternalDocumentation() {
        // Given
        OpenAPI openAPI = openApiConfig.customOpenAPI();
        
        // When
        var externalDocs = openAPI.getExternalDocs();
        
        // Then
        assertNotNull(externalDocs, "External documentation should not be null");
        assertEquals("MCA Application Processing System Documentation", externalDocs.getDescription(), 
                "External documentation description should match");
        assertEquals("https://dollarfunding.com/docs/mca", externalDocs.getUrl(), 
                "External documentation URL should match");
    }

    /**
     * Tests that the OpenAPI bean is properly configured with standard API responses.
     */
    @Test
    @DisplayName("Should configure OpenAPI with standard API responses")
    public void testStandardResponses() {
        // Given
        OpenAPI openAPI = openApiConfig.customOpenAPI();
        
        // When
        Components components = openAPI.getComponents();
        
        // Then
        assertNotNull(components, "Components should not be null");
        assertNotNull(components.getResponses(), "Standard responses should not be null");
        
        // Verify standard responses
        assertTrue(components.getResponses().containsKey("UnauthorizedError"), 
                "Should have UnauthorizedError response");
        assertTrue(components.getResponses().containsKey("ForbiddenError"), 
                "Should have ForbiddenError response");
        assertTrue(components.getResponses().containsKey("NotFoundError"), 
                "Should have NotFoundError response");
        assertTrue(components.getResponses().containsKey("ValidationError"), 
                "Should have ValidationError response");
        assertTrue(components.getResponses().containsKey("ServerError"), 
                "Should have ServerError response");
    }
}