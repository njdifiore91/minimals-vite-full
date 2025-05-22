package com.dollarfunding.mca.config;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.enums.SecuritySchemeIn;
import io.swagger.v3.oas.annotations.enums.SecuritySchemeType;
import io.swagger.v3.oas.annotations.info.Contact;
import io.swagger.v3.oas.annotations.info.Info;
import io.swagger.v3.oas.annotations.info.License;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.security.SecurityScheme;
import io.swagger.v3.oas.annotations.servers.Server;
import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.ExternalDocumentation;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.Paths;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.responses.ApiResponses;
import io.swagger.v3.oas.models.security.OAuthFlow;
import io.swagger.v3.oas.models.security.OAuthFlows;
import io.swagger.v3.oas.models.security.Scopes;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.tags.Tag;

import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.dto.WebhookRequestDTO;
import com.dollarfunding.mca.dto.WebhookResponseDTO;
import com.dollarfunding.mca.dto.WebhookTestRequestDTO;
import com.dollarfunding.mca.dto.WebhookTestResponseDTO;

/**
 * Configuration class for OpenAPI 3.0 documentation of the MCA application's REST API.
 * <p>
 * This class configures the OpenAPI documentation with API information, security schemes,
 * and documentation settings. It enables developers to understand and interact with the API
 * through generated documentation, including endpoints, request/response models, and security
 * requirements.
 */
@Configuration
@OpenAPIDefinition(
        info = @Info(
                title = "Merchant Cash Advance (MCA) API",
                version = "1.0",
                description = "REST API for the Merchant Cash Advance (MCA) Application Processing System. " +
                        "This API enables automation of email-based application processing with a 93% reduction in manual processing. " +
                        "Applications are processed in under 5 minutes from receipt to completion with 99% data extraction accuracy.",
                contact = @Contact(
                        name = "Dollar Funding Support",
                        email = "support@dollarfunding.com",
                        url = "https://dollarfunding.com/support"
                ),
                license = @License(
                        name = "Proprietary",
                        url = "https://dollarfunding.com/terms"
                )
        ),
        servers = {
                @Server(
                        url = "/",
                        description = "Default Server URL"
                )
        },
        security = {
                @SecurityRequirement(name = "bearerAuth")
        }
)
@SecurityScheme(
        name = "bearerAuth",
        type = SecuritySchemeType.HTTP,
        scheme = "bearer",
        bearerFormat = "JWT",
        in = SecuritySchemeIn.HEADER,
        description = "JWT Authentication using RS256 algorithm with 60-minute token expiry. " +
                "Refresh tokens are valid for 7 days. Two specific roles are supported: " +
                "Operations Staff (Read all, write application data) and " +
                "System Admin (Full access to all endpoints and webhook configuration)."
)
public class OpenApiConfig {

    @Value("${spring.application.name:MCA Data Service}")
    private String applicationName;

    /**
     * Configures the OpenAPI documentation for the MCA application.
     *
     * @return the OpenAPI configuration bean
     */
    /**
     * Configures the OpenAPI documentation for the MCA application.
     *
     * @return the OpenAPI configuration bean
     */
    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .components(new Components()
                        .addResponses("UnauthorizedError", createApiResponse("Unauthorized", "Authentication credentials are missing or invalid"))
                        .addResponses("ForbiddenError", createApiResponse("Forbidden", "User does not have permission to access this resource"))
                        .addResponses("NotFoundError", createApiResponse("Not Found", "The requested resource was not found"))
                        .addResponses("ValidationError", createApiResponse("Validation Error", "The request contains invalid parameters"))
                        .addResponses("ServerError", createApiResponse("Server Error", "An unexpected server error occurred"))
                        .addSecuritySchemes("bearerAuth", new SecurityScheme()
                                .type(SecurityScheme.Type.HTTP)
                                .scheme("bearer")
                                .bearerFormat("JWT")
                                .description("JWT Authentication using RS256 algorithm with 60-minute token expiry"))
                        .addSecuritySchemes("oauth2", new SecurityScheme()
                                .type(SecurityScheme.Type.OAUTH2)
                                .description("OAuth2 authentication with role-based access control")
                                .flows(new OAuthFlows()
                                        .implicit(new OAuthFlow()
                                                .authorizationUrl("https://dollarfunding.com/oauth2/authorize")
                                                .scopes(new Scopes()
                                                        .addString("operations_staff", "Read all, write application data")
                                                        .addString("system_admin", "Full access to all endpoints and webhook configuration")))))
                )
                .tags(Arrays.asList(
                        createTag("Applications", "Operations for managing MCA applications"),
                        createTag("Documents", "Operations for managing documents associated with applications"),
                        createTag("Webhooks", "Operations for configuring webhook notifications"),
                        createTag("Health", "Health check endpoints for Kubernetes probes")
                ))
                .externalDocs(new ExternalDocumentation()
                        .description("MCA Application Processing System Documentation")
                        .url("https://dollarfunding.com/docs/mca"));
    }

    /**
     * Creates a standardized API response for the OpenAPI documentation.
     *
     * @param title       the response title
     * @param description the response description
     * @return the API response object
     */
    private ApiResponse createApiResponse(String title, String description) {
        return new ApiResponse()
                .description(description)
                .content(new Content()
                        .addMediaType("application/json", new MediaType()
                                .schema(new Schema<Map<String, Object>>()
                                        .name("ErrorResponse")
                                        .type("object")
                                        .addProperties("code", new Schema<String>().type("string").example("VALIDATION_ERROR"))
                                        .addProperties("message", new Schema<String>().type("string").example(title))
                                        .addProperties("details", new Schema<Object>().type("object"))
                                        .addProperties("timestamp", new Schema<String>().type("string").format("date-time").example("2023-01-01T12:00:00Z"))
                                        .addProperties("path", new Schema<String>().type("string").example("/api/v1/applications"))
                                )
                        ));
    }

    /**
     * Customizes the OpenAPI documentation with additional details about API endpoints.
     *
     * @return the OpenApiCustomizer bean
     */
    @Bean
    public OpenApiCustomizer openApiCustomizer() {
        return openApi -> {
            // Add paths if not already defined by controllers
            Paths paths = openApi.getPaths();
            if (paths == null) {
                paths = new Paths();
                openApi.setPaths(paths);
            }
            
            // Add application endpoints documentation
            addApplicationEndpoints(paths);
            
            // Add document endpoints documentation
            addDocumentEndpoints(paths);
            
            // Add webhook endpoints documentation
            addWebhookEndpoints(paths);
            
            // Add health check endpoint documentation
            addHealthEndpoint(paths);
        };
    }
    
    /**
     * Adds documentation for application management endpoints.
     *
     * @param paths the OpenAPI paths object
     */
    private void addApplicationEndpoints(Paths paths) {
        // GET /api/v1/applications - List applications
        PathItem applicationsPath = new PathItem();
        applicationsPath.get(new Operation()
                .summary("List applications")
                .description("Returns a paginated list of MCA applications with optional filtering")
                .addTagsItem("Applications")
                .addParametersItem(createParameter("page", "query", "Page number (zero-based)", "integer", false))
                .addParametersItem(createParameter("size", "query", "Page size", "integer", false))
                .addParametersItem(createParameter("status", "query", "Filter by application status", "string", false))
                .addParametersItem(createParameter("reviewStatus", "query", "Filter by review status", "string", false))
                .addParametersItem(createParameter("fromDate", "query", "Filter by creation date (from)", "string", false))
                .addParametersItem(createParameter("toDate", "query", "Filter by creation date (to)", "string", false))
                .responses(new ApiResponses()
                        .addApiResponse("200", createPagedResponse("ApplicationResponseDTO", "Successful operation"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                ));
        
        // POST /api/v1/applications - Create application
        applicationsPath.post(new Operation()
                .summary("Create application")
                .description("Creates a new MCA application")
                .addTagsItem("Applications")
                .requestBody(createRequestBody(ApplicationRequestDTO.class.getSimpleName(), "Application data", true))
                .responses(new ApiResponses()
                        .addApiResponse("201", createApiResponse("ApplicationResponseDTO", "Application created successfully"))
                        .addApiResponse("400", new ApiResponse().$ref("#/components/responses/ValidationError"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                ));
        
        paths.addPathItem("/api/v1/applications", applicationsPath);
        
        // GET /api/v1/applications/{id} - Get application by ID
        PathItem applicationPath = new PathItem();
        applicationPath.get(new Operation()
                .summary("Get application by ID")
                .description("Returns a single MCA application by ID")
                .addTagsItem("Applications")
                .addParametersItem(createParameter("id", "path", "Application ID", "string", true))
                .responses(new ApiResponses()
                        .addApiResponse("200", createApiResponse("ApplicationResponseDTO", "Successful operation"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        // PUT /api/v1/applications/{id} - Update application
        applicationPath.put(new Operation()
                .summary("Update application")
                .description("Updates an existing MCA application")
                .addTagsItem("Applications")
                .addParametersItem(createParameter("id", "path", "Application ID", "string", true))
                .requestBody(createRequestBody(ApplicationRequestDTO.class.getSimpleName(), "Updated application data", true))
                .responses(new ApiResponses()
                        .addApiResponse("200", createApiResponse("ApplicationResponseDTO", "Application updated successfully"))
                        .addApiResponse("400", new ApiResponse().$ref("#/components/responses/ValidationError"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        // DELETE /api/v1/applications/{id} - Delete application
        applicationPath.delete(new Operation()
                .summary("Delete application")
                .description("Deletes an MCA application")
                .addTagsItem("Applications")
                .addParametersItem(createParameter("id", "path", "Application ID", "string", true))
                .responses(new ApiResponses()
                        .addApiResponse("204", new ApiResponse().description("Application deleted successfully"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        paths.addPathItem("/api/v1/applications/{id}", applicationPath);
    }
    
    /**
     * Adds documentation for document management endpoints.
     *
     * @param paths the OpenAPI paths object
     */
    private void addDocumentEndpoints(Paths paths) {
        // GET /api/v1/documents - List documents
        PathItem documentsPath = new PathItem();
        documentsPath.get(new Operation()
                .summary("List documents")
                .description("Returns a paginated list of documents with optional filtering")
                .addTagsItem("Documents")
                .addParametersItem(createParameter("page", "query", "Page number (zero-based)", "integer", false))
                .addParametersItem(createParameter("size", "query", "Page size", "integer", false))
                .addParametersItem(createParameter("applicationId", "query", "Filter by application ID", "string", false))
                .addParametersItem(createParameter("type", "query", "Filter by document type", "string", false))
                .responses(new ApiResponses()
                        .addApiResponse("200", createPagedResponse("DocumentResponseDTO", "Successful operation"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                ));
        
        // POST /api/v1/documents - Upload document
        documentsPath.post(new Operation()
                .summary("Upload document")
                .description("Uploads a new document and associates it with an application")
                .addTagsItem("Documents")
                .requestBody(createRequestBody(DocumentRequestDTO.class.getSimpleName(), "Document data and file", true))
                .responses(new ApiResponses()
                        .addApiResponse("201", createApiResponse("DocumentResponseDTO", "Document uploaded successfully"))
                        .addApiResponse("400", new ApiResponse().$ref("#/components/responses/ValidationError"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                ));
        
        paths.addPathItem("/api/v1/documents", documentsPath);
        
        // GET /api/v1/documents/{id} - Get document by ID
        PathItem documentPath = new PathItem();
        documentPath.get(new Operation()
                .summary("Get document by ID")
                .description("Returns a single document by ID with a pre-signed URL for download")
                .addTagsItem("Documents")
                .addParametersItem(createParameter("id", "path", "Document ID", "string", true))
                .responses(new ApiResponses()
                        .addApiResponse("200", createApiResponse("DocumentResponseDTO", "Successful operation"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        // DELETE /api/v1/documents/{id} - Delete document
        documentPath.delete(new Operation()
                .summary("Delete document")
                .description("Deletes a document")
                .addTagsItem("Documents")
                .addParametersItem(createParameter("id", "path", "Document ID", "string", true))
                .responses(new ApiResponses()
                        .addApiResponse("204", new ApiResponse().description("Document deleted successfully"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        paths.addPathItem("/api/v1/documents/{id}", documentPath);
    }
    
    /**
     * Adds documentation for webhook configuration endpoints.
     *
     * @param paths the OpenAPI paths object
     */
    private void addWebhookEndpoints(Paths paths) {
        // GET /api/v1/webhooks - List webhooks
        PathItem webhooksPath = new PathItem();
        webhooksPath.get(new Operation()
                .summary("List webhooks")
                .description("Returns a list of configured webhooks")
                .addTagsItem("Webhooks")
                .responses(new ApiResponses()
                        .addApiResponse("200", createListResponse("WebhookResponseDTO", "Successful operation"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                ));
        
        // POST /api/v1/webhooks - Create webhook
        webhooksPath.post(new Operation()
                .summary("Create webhook")
                .description("Creates a new webhook configuration")
                .addTagsItem("Webhooks")
                .requestBody(createRequestBody(WebhookRequestDTO.class.getSimpleName(), "Webhook configuration data", true))
                .responses(new ApiResponses()
                        .addApiResponse("201", createApiResponse("WebhookResponseDTO", "Webhook created successfully"))
                        .addApiResponse("400", new ApiResponse().$ref("#/components/responses/ValidationError"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                ));
        
        paths.addPathItem("/api/v1/webhooks", webhooksPath);
        
        // GET /api/v1/webhooks/{id} - Get webhook by ID
        PathItem webhookPath = new PathItem();
        webhookPath.get(new Operation()
                .summary("Get webhook by ID")
                .description("Returns a single webhook configuration by ID")
                .addTagsItem("Webhooks")
                .addParametersItem(createParameter("id", "path", "Webhook ID", "string", true))
                .responses(new ApiResponses()
                        .addApiResponse("200", createApiResponse("WebhookResponseDTO", "Successful operation"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        // PUT /api/v1/webhooks/{id} - Update webhook
        webhookPath.put(new Operation()
                .summary("Update webhook")
                .description("Updates an existing webhook configuration")
                .addTagsItem("Webhooks")
                .addParametersItem(createParameter("id", "path", "Webhook ID", "string", true))
                .requestBody(createRequestBody(WebhookRequestDTO.class.getSimpleName(), "Updated webhook configuration data", true))
                .responses(new ApiResponses()
                        .addApiResponse("200", createApiResponse("WebhookResponseDTO", "Webhook updated successfully"))
                        .addApiResponse("400", new ApiResponse().$ref("#/components/responses/ValidationError"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        // DELETE /api/v1/webhooks/{id} - Delete webhook
        webhookPath.delete(new Operation()
                .summary("Delete webhook")
                .description("Deletes a webhook configuration")
                .addTagsItem("Webhooks")
                .addParametersItem(createParameter("id", "path", "Webhook ID", "string", true))
                .responses(new ApiResponses()
                        .addApiResponse("204", new ApiResponse().description("Webhook deleted successfully"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        paths.addPathItem("/api/v1/webhooks/{id}", webhookPath);
        
        // POST /api/v1/webhooks/{id}/test - Test webhook
        PathItem webhookTestPath = new PathItem();
        webhookTestPath.post(new Operation()
                .summary("Test webhook")
                .description("Tests a webhook by sending a test payload to the configured endpoint")
                .addTagsItem("Webhooks")
                .addParametersItem(createParameter("id", "path", "Webhook ID", "string", true))
                .requestBody(createRequestBody(WebhookTestRequestDTO.class.getSimpleName(), "Test configuration and payload", false))
                .responses(new ApiResponses()
                        .addApiResponse("200", createApiResponse("WebhookTestResponseDTO", "Test results"))
                        .addApiResponse("401", new ApiResponse().$ref("#/components/responses/UnauthorizedError"))
                        .addApiResponse("403", new ApiResponse().$ref("#/components/responses/ForbiddenError"))
                        .addApiResponse("404", new ApiResponse().$ref("#/components/responses/NotFoundError"))
                ));
        
        paths.addPathItem("/api/v1/webhooks/{id}/test", webhookTestPath);
    }
    
    /**
     * Adds documentation for health check endpoint.
     *
     * @param paths the OpenAPI paths object
     */
    private void addHealthEndpoint(Paths paths) {
        // GET /actuator/health - Health check
        PathItem healthPath = new PathItem();
        healthPath.get(new Operation()
                .summary("Health check")
                .description("Returns the health status of the service for Kubernetes probes")
                .addTagsItem("Health")
                .responses(new ApiResponses()
                        .addApiResponse("200", createApiResponse("HealthResponse", "Service is healthy"))
                        .addApiResponse("503", createApiResponse("HealthResponse", "Service is unhealthy"))
                ));
        
        paths.addPathItem("/actuator/health", healthPath);
    }
    
    /**
     * Creates a parameter for the OpenAPI documentation.
     *
     * @param name        the parameter name
     * @param in          the parameter location (path, query, header, cookie)
     * @param description the parameter description
     * @param type        the parameter type
     * @param required    whether the parameter is required
     * @return the parameter object
     */
    private Parameter createParameter(String name, String in, String description, String type, boolean required) {
        return new Parameter()
                .name(name)
                .in(in)
                .description(description)
                .schema(new Schema<>().type(type))
                .required(required);
    }
    
    /**
     * Creates a paginated API response for the OpenAPI documentation.
     *
     * @param schemaName  the name of the schema for the response items
     * @param description the response description
     * @return the API response object
     */
    private ApiResponse createPagedResponse(String schemaName, String description) {
        Schema<?> itemsSchema = new Schema<>()
                .type("object")
                .description(schemaName);
                
        Schema<?> contentSchema = new Schema<>()
                .type("object")
                .addProperties("content", new Schema<>().type("array").items(itemsSchema))
                .addProperties("totalElements", new Schema<>().type("integer").format("int64").example(100))
                .addProperties("totalPages", new Schema<>().type("integer").format("int32").example(10))
                .addProperties("size", new Schema<>().type("integer").format("int32").example(10))
                .addProperties("number", new Schema<>().type("integer").format("int32").example(0))
                .addProperties("first", new Schema<>().type("boolean").example(true))
                .addProperties("last", new Schema<>().type("boolean").example(false))
                .addProperties("empty", new Schema<>().type("boolean").example(false));
                
        return new ApiResponse()
                .description(description)
                .content(new Content()
                        .addMediaType("application/json", new MediaType().schema(contentSchema)));
    }
    
    /**
     * Creates a list API response for the OpenAPI documentation.
     *
     * @param schemaName  the name of the schema for the response items
     * @param description the response description
     * @return the API response object
     */
    private ApiResponse createListResponse(String schemaName, String description) {
        Schema<?> itemsSchema = new Schema<>()
                .type("object")
                .description(schemaName);
                
        Schema<?> contentSchema = new Schema<>()
                .type("array")
                .items(itemsSchema);
                
        return new ApiResponse()
                .description(description)
                .content(new Content()
                        .addMediaType("application/json", new MediaType().schema(contentSchema)));
    }
    
    /**
     * Creates a request body for the OpenAPI documentation.
     *
     * @param schemaName  the name of the schema for the request body
     * @param description the request body description
     * @param required    whether the request body is required
     * @return the request body object
     */
    private io.swagger.v3.oas.models.parameters.RequestBody createRequestBody(String schemaName, String description, boolean required) {
        Schema<?> schema = new Schema<>()
                .type("object")
                .description(schemaName);
                
        return new io.swagger.v3.oas.models.parameters.RequestBody()
                .description(description)
                .required(required)
                .content(new Content()
                        .addMediaType("application/json", new MediaType().schema(schema)));
    }
    
    /**
     * Creates a tag for grouping API operations in the OpenAPI documentation.
     *
     * @param name        the tag name
     * @param description the tag description
     * @return the tag object
     */
    private Tag createTag(String name, String description) {
        return new Tag().name(name).description(description);
    }
}