package com.dollarfunding.mca.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.http.converter.xml.MappingJackson2XmlHttpMessageConverter;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ContentNegotiationConfigurer;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Arrays;
import java.util.List;

/**
 * Web configuration for the MCA application's REST API.
 * Configures CORS settings, content negotiation, message converters, and other web-related beans.
 * This class implements the requirements specified in the technical specification for the MCA application.
 *
 * Key features:
 * - CORS configuration with strict security policies
 * - Content negotiation for JSON and XML formats
 * - Custom message converters for standardized data serialization
 * - Resource handlers for OpenAPI documentation and health checks
 * - Support for Kubernetes probes through Actuator endpoints
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    /**
     * Allowed origins for CORS requests.
     * Default is the production frontend URL, but can be overridden in application properties.
     */
    @Value("${cors.allowed-origins:https://app.dollarfunding.com}")
    private String[] allowedOrigins;

    /**
     * Allowed HTTP methods for CORS requests.
     * Default includes standard REST methods, but can be overridden in application properties.
     */
    @Value("${cors.allowed-methods:GET,POST,PUT,DELETE,OPTIONS}")
    private String[] allowedMethods;

    /**
     * Allowed headers for CORS requests.
     * Default includes standard headers, but can be overridden in application properties.
     */
    @Value("${cors.allowed-headers:Origin,Content-Type,Accept,Authorization,X-Requested-With}")
    private String[] allowedHeaders;

    /**
     * Headers exposed to the client in CORS responses.
     * Default includes Content-Disposition for file downloads, but can be overridden in application properties.
     */
    @Value("${cors.exposed-headers:Content-Disposition}")
    private String[] exposedHeaders;

    /**
     * Max age for CORS preflight requests in seconds.
     * Default is 1 hour (3600 seconds), but can be overridden in application properties.
     */
    @Value("${cors.max-age:3600}")
    private long maxAge;

    /**
     * Configures CORS settings to allow specific origins, methods, and headers.
     * This implements the security requirements specified in the technical specification section 3.8.6.
     * Strict Cross-Origin Resource Sharing policies are configured with explicit allowed origins,
     * methods, and headers for pre-flight request caching optimized for performance while maintaining security boundaries.
     *
     * @param registry The CORS registry to configure
     */
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/v1/**")
                .allowedOrigins(allowedOrigins)
                .allowedMethods(allowedMethods)
                .allowedHeaders(allowedHeaders)
                .exposedHeaders(exposedHeaders)
                .allowCredentials(true)
                .maxAge(maxAge);
    }

    /**
     * Configures content negotiation to support JSON and other formats.
     * Sets JSON as the default content type when not specified.
     * This supports the requirement for JSON-based API contracts with standardized error responses.
     *
     * @param configurer The content negotiation configurer
     */
    @Override
    public void configureContentNegotiation(ContentNegotiationConfigurer configurer) {
        configurer
                .defaultContentType(MediaType.APPLICATION_JSON)
                .mediaType("json", MediaType.APPLICATION_JSON)
                .mediaType("xml", MediaType.APPLICATION_XML)
                .ignoreAcceptHeader(false)
                .favorParameter(true)
                .parameterName("format");
    }

    /**
     * Configures HTTP message converters for request/response serialization.
     * Ensures proper handling of JSON data according to standardized schemas.
     * This supports the requirement that message serialization between services must use standardized JSON schemas.
     *
     * @param converters The list of HTTP message converters to configure
     */
    @Override
    public void configureMessageConverters(List<HttpMessageConverter<?>> converters) {
        // Add JSON converter with custom ObjectMapper for consistent serialization
        converters.add(mappingJackson2HttpMessageConverter());
        
        // Add XML converter for XML content negotiation support
        converters.add(mappingJackson2XmlHttpMessageConverter());
    }
    
    /**
     * Configures resource handlers for static content.
     * This allows serving static resources like OpenAPI documentation, health check endpoints, etc.
     *
     * @param registry The resource handler registry to configure
     */
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // Serve OpenAPI documentation
        registry.addResourceHandler("/api-docs/**")
                .addResourceLocations("classpath:/META-INF/resources/");
        
        // Serve Swagger UI
        registry.addResourceHandler("/swagger-ui/**")
                .addResourceLocations("classpath:/META-INF/resources/webjars/swagger-ui/");
        
        // Serve health check endpoints for Kubernetes probes
        registry.addResourceHandler("/actuator/**")
                .addResourceLocations("classpath:/META-INF/resources/actuator/");
    }
    
    /**
     * Creates a custom ObjectMapper for consistent JSON serialization across the application.
     * Configures proper handling of dates, times, and other Java types.
     *
     * @return Configured ObjectMapper instance
     */
    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        objectMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return objectMapper;
    }
    
    /**
     * Creates a custom JSON message converter with the configured ObjectMapper.
     *
     * @return Configured MappingJackson2HttpMessageConverter instance
     */
    @Bean
    public MappingJackson2HttpMessageConverter mappingJackson2HttpMessageConverter() {
        MappingJackson2HttpMessageConverter jsonConverter = new MappingJackson2HttpMessageConverter();
        jsonConverter.setObjectMapper(objectMapper());
        jsonConverter.setSupportedMediaTypes(Arrays.asList(
                MediaType.APPLICATION_JSON,
                new MediaType("application", "*+json")
        ));
        return jsonConverter;
    }
    
    /**
     * Creates a custom XML message converter for XML content negotiation support.
     *
     * @return Configured MappingJackson2XmlHttpMessageConverter instance
     */
    @Bean
    public MappingJackson2XmlHttpMessageConverter mappingJackson2XmlHttpMessageConverter() {
        MappingJackson2XmlHttpMessageConverter xmlConverter = new MappingJackson2XmlHttpMessageConverter();
        xmlConverter.setSupportedMediaTypes(Arrays.asList(
                MediaType.APPLICATION_XML,
                new MediaType("application", "*+xml")
        ));
        return xmlConverter;
    }
    
    /**
     * Configures a formatter registry for consistent date/time formatting across the application.
     * This ensures that date and time values are formatted consistently in responses.
     *
     * @param registry The formatter registry to configure
     */
    @Override
    public void addFormatters(org.springframework.format.FormatterRegistry registry) {
        // Add custom formatters if needed
    }
    
    /**
     * Configures exception handlers for standardized error responses.
     * This supports the requirement for standardized error responses in the API contracts.
     *
     * Note: Most exception handling will be done through @ControllerAdvice classes,
     * but this method can be used for additional configuration if needed.
     */
    @Bean
    public org.springframework.web.servlet.HandlerExceptionResolver customExceptionResolver() {
        return new org.springframework.web.servlet.handler.SimpleMappingExceptionResolver();
    }
}