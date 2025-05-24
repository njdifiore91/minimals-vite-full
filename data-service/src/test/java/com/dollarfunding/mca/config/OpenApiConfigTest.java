package com.dollarfunding.mca.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;
import io.swagger.v3.oas.models.tags.Tag;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the OpenApiConfig class that configures OpenAPI 3.0 documentation for the REST API.
 * Tests verify API information configuration, security scheme setup, documentation settings,
 * API group configuration, and Swagger UI setup.
 */
@ExtendWith(MockitoExtension.class)
public class OpenApiConfigTest {

    @InjectMocks
    private OpenApiConfig openApiConfig;

    @BeforeEach
    public void setUp() {
        // Set up the application properties that would normally be injected via @Value
        ReflectionTestUtils.setField(openApiConfig, "applicationName", "MCA Data Service");
        ReflectionTestUtils.setField(openApiConfig, "applicationDescription", "Merchant Cash Advance Application Processing System");
        ReflectionTestUtils.setField(openApiConfig, "applicationVersion", "1.0.0");
    }

    @Test
    @DisplayName("Should configure OpenAPI with correct API information")
    public void testOpenAPIConfiguration() {
        // When
        OpenAPI openAPI = openApiConfig.openAPI();
        
        // Then
        assertNotNull(openAPI, "OpenAPI configuration should not be null");
        assertNotNull(openAPI.getInfo(), "API info should not be null");
        assertEquals("MCA Data Service", openAPI.getInfo().getTitle(), "API title should match application name");
        assertEquals("Merchant Cash Advance Application Processing System", openAPI.getInfo().getDescription(), "API description should match application description");
        assertEquals("1.0.0", openAPI.getInfo().getVersion(), "API version should match application version");
    }

    @Test
    @DisplayName("Should configure API information with correct contact details")
    public void testApiInfoContactDetails() {
        // When
        OpenAPI openAPI = openApiConfig.openAPI();
        Info info = openAPI.getInfo();
        
        // Then
        assertNotNull(info.getContact(), "Contact information should not be null");
        assertEquals("Dollar Funding Support", info.getContact().getName(), "Contact name should be correct");
        assertEquals("support@dollarfunding.com", info.getContact().getEmail(), "Contact email should be correct");
        assertEquals("https://dollarfunding.com/support", info.getContact().getUrl(), "Contact URL should be correct");
        
        assertNotNull(info.getLicense(), "License information should not be null");
        assertEquals("Dollar Funding License", info.getLicense().getName(), "License name should be correct");
        assertEquals("https://dollarfunding.com/license", info.getLicense().getUrl(), "License URL should be correct");
    }

    @Test
    @DisplayName("Should configure API servers for different environments")
    public void testApiServers() {
        // When
        OpenAPI openAPI = openApiConfig.openAPI();
        List<Server> servers = openAPI.getServers();
        
        // Then
        assertNotNull(servers, "API servers should not be null");
        assertEquals(3, servers.size(), "Should have 3 server environments configured");
        
        // Verify production server
        Server productionServer = servers.get(0);
        assertEquals("https://api.dollarfunding.com", productionServer.getUrl(), "Production server URL should be correct");
        assertEquals("Production Server", productionServer.getDescription(), "Production server description should be correct");
        
        // Verify staging server
        Server stagingServer = servers.get(1);
        assertEquals("https://api-staging.dollarfunding.com", stagingServer.getUrl(), "Staging server URL should be correct");
        assertEquals("Staging Server", stagingServer.getDescription(), "Staging server description should be correct");
        
        // Verify development server
        Server developmentServer = servers.get(2);
        assertEquals("https://api-dev.dollarfunding.com", developmentServer.getUrl(), "Development server URL should be correct");
        assertEquals("Development Server", developmentServer.getDescription(), "Development server description should be correct");
    }

    @Test
    @DisplayName("Should configure API tags for grouping endpoints")
    public void testApiTags() {
        // When
        OpenAPI openAPI = openApiConfig.openAPI();
        List<Tag> tags = openAPI.getTags();
        
        // Then
        assertNotNull(tags, "API tags should not be null");
        assertEquals(4, tags.size(), "Should have 4 API tags configured");
        
        // Verify Applications tag
        Tag applicationsTag = tags.get(0);
        assertEquals("Applications", applicationsTag.getName(), "Applications tag name should be correct");
        assertEquals("Operations related to MCA applications", applicationsTag.getDescription(), "Applications tag description should be correct");
        
        // Verify Documents tag
        Tag documentsTag = tags.get(1);
        assertEquals("Documents", documentsTag.getName(), "Documents tag name should be correct");
        assertEquals("Operations related to application documents", documentsTag.getDescription(), "Documents tag description should be correct");
        
        // Verify Webhooks tag
        Tag webhooksTag = tags.get(2);
        assertEquals("Webhooks", webhooksTag.getName(), "Webhooks tag name should be correct");
        assertEquals("Operations related to webhook configuration and management", webhooksTag.getDescription(), "Webhooks tag description should be correct");
        
        // Verify Health tag
        Tag healthTag = tags.get(3);
        assertEquals("Health", healthTag.getName(), "Health tag name should be correct");
        assertEquals("Health check endpoints for Kubernetes probes", healthTag.getDescription(), "Health tag description should be correct");
    }

    @Test
    @DisplayName("Should configure security components with JWT authentication")
    public void testSecurityComponents() {
        // When
        OpenAPI openAPI = openApiConfig.openAPI();
        Components components = openAPI.getComponents();
        
        // Then
        assertNotNull(components, "Components should not be null");
        assertNotNull(components.getSecuritySchemes(), "Security schemes should not be null");
        assertTrue(components.getSecuritySchemes().containsKey("JWT"), "Should have JWT security scheme");
        
        SecurityScheme jwtScheme = components.getSecuritySchemes().get("JWT");
        assertEquals(SecurityScheme.Type.HTTP, jwtScheme.getType(), "Security scheme type should be HTTP");
        assertEquals("bearer", jwtScheme.getScheme(), "Security scheme should be bearer");
        assertEquals("JWT", jwtScheme.getBearerFormat(), "Bearer format should be JWT");
        assertEquals(SecurityScheme.In.HEADER, jwtScheme.getIn(), "Security scheme should be in header");
        assertEquals("Authorization", jwtScheme.getName(), "Security scheme name should be Authorization");
        assertTrue(jwtScheme.getDescription().contains("JWT token authentication"), "Description should mention JWT token authentication");
    }

    @Test
    @DisplayName("Should add global security requirement for JWT")
    public void testGlobalSecurityRequirement() {
        // When
        OpenAPI openAPI = openApiConfig.openAPI();
        List<SecurityRequirement> security = openAPI.getSecurity();
        
        // Then
        assertNotNull(security, "Security requirements should not be null");
        assertEquals(1, security.size(), "Should have 1 security requirement");
        assertTrue(security.get(0).containsKey("JWT"), "Security requirement should be for JWT");
    }
}