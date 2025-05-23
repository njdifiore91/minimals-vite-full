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

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Arrays;
import java.util.List;

/**
 * Configuration class for OpenAPI 3.0 documentation of the MCA application's REST API.
 * This class defines API information, security schemes, and documentation settings.
 */
@Configuration
public class OpenApiConfig {

    @Value("${spring.application.name:MCA Data Service}")
    private String applicationName;

    @Value("${spring.application.description:Merchant Cash Advance Application Processing System}")
    private String applicationDescription;

    @Value("${spring.application.version:1.0.0}")
    private String applicationVersion;

    /**
     * Configures the OpenAPI documentation for the MCA application.
     *
     * @return the OpenAPI configuration
     */
    @Bean
    public OpenAPI openAPI() {
        return new OpenAPI()
                .info(apiInfo())
                .servers(apiServers())
                .tags(apiTags())
                .components(securityComponents())
                .addSecurityItem(new SecurityRequirement().addList("JWT"));
    }

    /**
     * Defines the API information including title, description, version, and contact details.
     *
     * @return the API information
     */
    private Info apiInfo() {
        return new Info()
                .title(applicationName)
                .description(applicationDescription)
                .version(applicationVersion)
                .contact(new Contact()
                        .name("Dollar Funding Support")
                        .email("support@dollarfunding.com")
                        .url("https://dollarfunding.com/support"))
                .license(new License()
                        .name("Dollar Funding License")
                        .url("https://dollarfunding.com/license"));
    }

    /**
     * Defines the API servers for different environments.
     *
     * @return the list of API servers
     */
    private List<Server> apiServers() {
        Server productionServer = new Server()
                .url("https://api.dollarfunding.com")
                .description("Production Server");

        Server stagingServer = new Server()
                .url("https://api-staging.dollarfunding.com")
                .description("Staging Server");

        Server developmentServer = new Server()
                .url("https://api-dev.dollarfunding.com")
                .description("Development Server");

        return Arrays.asList(productionServer, stagingServer, developmentServer);
    }

    /**
     * Defines the API tags for grouping endpoints.
     *
     * @return the list of API tags
     */
    private List<Tag> apiTags() {
        Tag applicationsTag = new Tag()
                .name("Applications")
                .description("Operations related to MCA applications");

        Tag documentsTag = new Tag()
                .name("Documents")
                .description("Operations related to application documents");

        Tag webhooksTag = new Tag()
                .name("Webhooks")
                .description("Operations related to webhook configuration and management");

        Tag healthTag = new Tag()
                .name("Health")
                .description("Health check endpoints for Kubernetes probes");

        return Arrays.asList(applicationsTag, documentsTag, webhooksTag, healthTag);
    }

    /**
     * Defines the security components for the API, including JWT authentication.
     *
     * @return the security components
     */
    private Components securityComponents() {
        return new Components()
                .addSecuritySchemes("JWT", new SecurityScheme()
                        .type(SecurityScheme.Type.HTTP)
                        .scheme("bearer")
                        .bearerFormat("JWT")
                        .in(SecurityScheme.In.HEADER)
                        .name("Authorization")
                        .description("JWT token authentication. Use format: Bearer {token}"));
    }
}