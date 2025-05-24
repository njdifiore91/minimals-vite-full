package com.dollarfunding.mca.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.http.converter.xml.MappingJackson2XmlHttpMessageConverter;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.web.servlet.HandlerExceptionResolver;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ContentNegotiationConfigurer;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.handler.SimpleMappingExceptionResolver;

import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Unit tests for the {@link WebConfig} class.
 * 
 * These tests verify that the web configuration is properly set up for the MCA application's REST API,
 * including CORS settings, content negotiation, message converters, and other web-related beans.
 */
@ExtendWith(SpringExtension.class)
@WebMvcTest(WebConfig.class)
@Import(WebConfig.class)
public class WebConfigTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private WebConfig webConfig;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private MappingJackson2HttpMessageConverter jsonConverter;

    @Autowired
    private MappingJackson2XmlHttpMessageConverter xmlConverter;

    @Autowired
    private HandlerExceptionResolver exceptionResolver;

    @Value("${cors.allowed-origins:https://app.dollarfunding.com}")
    private String[] allowedOrigins;

    @Value("${cors.allowed-methods:GET,POST,PUT,DELETE,OPTIONS}")
    private String[] allowedMethods;

    @Value("${cors.allowed-headers:Origin,Content-Type,Accept,Authorization,X-Requested-With}")
    private String[] allowedHeaders;

    @Value("${cors.exposed-headers:Content-Disposition}")
    private String[] exposedHeaders;

    @Value("${cors.max-age:3600}")
    private long maxAge;

    /**
     * Tests that the WebConfig bean is properly created and autowired.
     */
    @Test
    @DisplayName("WebConfig bean should be created")
    public void webConfigBeanShouldBeCreated() {
        assertNotNull(webConfig, "WebConfig bean should not be null");
    }

    /**
     * Tests that CORS settings are properly configured with the expected values.
     * This test verifies that the CORS configuration allows the specified origins, methods, headers,
     * and exposed headers, and sets the correct max age for preflight requests.
     */
    @Test
    @DisplayName("CORS settings should be properly configured")
    public void corsSettingsShouldBeProperlyConfigured() throws Exception {
        // Create a mock CorsRegistry to verify the CORS configuration
        CorsRegistry registry = mock(CorsRegistry.class);
        when(registry.addMapping(anyString())).thenReturn(mock(org.springframework.web.servlet.config.annotation.CorsRegistration.class));

        // Call the addCorsMappings method with the mock registry
        webConfig.addCorsMappings(registry);

        // Verify that the registry was called with the expected mapping
        verify(registry).addMapping("/api/v1/**");

        // Create a MockMvc instance to test the actual CORS behavior
        MockMvc mockMvc = MockMvcBuilders.webAppContextSetup(context)
                .build();

        // Test a preflight request to verify CORS headers
        mockMvc.perform(options("/api/v1/applications")
                .header("Origin", allowedOrigins[0])
                .header("Access-Control-Request-Method", "GET")
                .header("Access-Control-Request-Headers", "Content-Type,Authorization"))
                .andExpect(status().isOk())
                .andExpect(header().exists("Access-Control-Allow-Origin"))
                .andExpect(header().exists("Access-Control-Allow-Methods"))
                .andExpect(header().exists("Access-Control-Allow-Headers"))
                .andExpect(header().exists("Access-Control-Max-Age"));
    }

    /**
     * Tests that content negotiation is properly configured with JSON as the default content type.
     * This test verifies that the content negotiation configuration supports JSON and XML formats,
     * with JSON as the default when not specified.
     */
    @Test
    @DisplayName("Content negotiation should be properly configured")
    public void contentNegotiationShouldBeProperlyConfigured() {
        // Create a mock ContentNegotiationConfigurer to verify the content negotiation configuration
        ContentNegotiationConfigurer configurer = mock(ContentNegotiationConfigurer.class);
        when(configurer.defaultContentType(any())).thenReturn(configurer);
        when(configurer.mediaType(anyString(), any())).thenReturn(configurer);
        when(configurer.ignoreAcceptHeader(anyBoolean())).thenReturn(configurer);
        when(configurer.favorParameter(anyBoolean())).thenReturn(configurer);
        when(configurer.parameterName(anyString())).thenReturn(configurer);

        // Call the configureContentNegotiation method with the mock configurer
        webConfig.configureContentNegotiation(configurer);

        // Verify that the configurer was called with the expected configuration
        verify(configurer).defaultContentType(MediaType.APPLICATION_JSON);
        verify(configurer).mediaType("json", MediaType.APPLICATION_JSON);
        verify(configurer).mediaType("xml", MediaType.APPLICATION_XML);
        verify(configurer).ignoreAcceptHeader(false);
        verify(configurer).favorParameter(true);
        verify(configurer).parameterName("format");
    }

    /**
     * Tests that message converters are properly configured for JSON and XML serialization/deserialization.
     * This test verifies that the message converter configuration adds the expected converters to the list.
     */
    @Test
    @DisplayName("Message converters should be properly configured")
    public void messageConvertersShouldBeProperlyConfigured() {
        // Create a mock list of HttpMessageConverter to verify the message converter configuration
        List<HttpMessageConverter<?>> converters = mock(List.class);

        // Call the configureMessageConverters method with the mock list
        webConfig.configureMessageConverters(converters);

        // Verify that the converters were added to the list
        verify(converters).add(any(MappingJackson2HttpMessageConverter.class));
        verify(converters).add(any(MappingJackson2XmlHttpMessageConverter.class));

        // Verify that the autowired converters are properly configured
        assertNotNull(jsonConverter, "JSON converter should not be null");
        assertNotNull(xmlConverter, "XML converter should not be null");

        // Verify that the JSON converter supports the expected media types
        assertTrue(jsonConverter.getSupportedMediaTypes().contains(MediaType.APPLICATION_JSON),
                "JSON converter should support APPLICATION_JSON");

        // Verify that the XML converter supports the expected media types
        assertTrue(xmlConverter.getSupportedMediaTypes().contains(MediaType.APPLICATION_XML),
                "XML converter should support APPLICATION_XML");
    }

    /**
     * Tests that resource handlers are properly configured for static content.
     * This test verifies that the resource handler configuration adds the expected handlers for
     * OpenAPI documentation, Swagger UI, and Actuator endpoints.
     */
    @Test
    @DisplayName("Resource handlers should be properly configured")
    public void resourceHandlersShouldBeProperlyConfigured() {
        // Create a mock ResourceHandlerRegistry to verify the resource handler configuration
        ResourceHandlerRegistry registry = mock(ResourceHandlerRegistry.class);
        when(registry.addResourceHandler(anyString())).thenReturn(mock(org.springframework.web.servlet.config.annotation.ResourceHandlerRegistration.class));

        // Call the addResourceHandlers method with the mock registry
        webConfig.addResourceHandlers(registry);

        // Verify that the registry was called with the expected handlers
        verify(registry).addResourceHandler("/api-docs/**");
        verify(registry).addResourceHandler("/swagger-ui/**");
        verify(registry).addResourceHandler("/actuator/**");
    }

    /**
     * Tests that the ObjectMapper is properly configured with the expected modules and features.
     * This test verifies that the ObjectMapper has the JavaTimeModule registered and has
     * WRITE_DATES_AS_TIMESTAMPS disabled for proper date/time handling.
     */
    @Test
    @DisplayName("ObjectMapper should be properly configured")
    public void objectMapperShouldBeProperlyConfigured() {
        // Verify that the autowired ObjectMapper is properly configured
        assertNotNull(objectMapper, "ObjectMapper should not be null");

        // Verify that the ObjectMapper has the JavaTimeModule registered
        assertTrue(objectMapper.getRegisteredModuleIds().contains(JavaTimeModule.class.getName()),
                "ObjectMapper should have JavaTimeModule registered");

        // Verify that WRITE_DATES_AS_TIMESTAMPS is disabled
        assertFalse(objectMapper.getSerializationConfig().hasSerializationFeature(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS),
                "ObjectMapper should have WRITE_DATES_AS_TIMESTAMPS disabled");
    }

    /**
     * Tests that the JSON message converter is properly configured with the expected ObjectMapper.
     * This test verifies that the JSON converter has an ObjectMapper with the JavaTimeModule registered
     * and WRITE_DATES_AS_TIMESTAMPS disabled.
     */
    @Test
    @DisplayName("JSON message converter should be properly configured")
    public void jsonMessageConverterShouldBeProperlyConfigured() {
        // Get the JSON converter bean from the application context
        MappingJackson2HttpMessageConverter converter = webConfig.mappingJackson2HttpMessageConverter();

        // Verify that the converter is properly configured
        assertNotNull(converter, "JSON converter should not be null");

        // Verify that the converter's ObjectMapper has the JavaTimeModule registered
        ObjectMapper converterObjectMapper = converter.getObjectMapper();
        assertTrue(converterObjectMapper.getRegisteredModuleIds().contains(JavaTimeModule.class.getName()),
                "JSON converter's ObjectMapper should have JavaTimeModule registered");

        // Verify that WRITE_DATES_AS_TIMESTAMPS is disabled
        assertFalse(converterObjectMapper.getSerializationConfig().hasSerializationFeature(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS),
                "JSON converter's ObjectMapper should have WRITE_DATES_AS_TIMESTAMPS disabled");

        // Verify that the converter supports the expected media types
        List<MediaType> supportedMediaTypes = converter.getSupportedMediaTypes();
        assertTrue(supportedMediaTypes.contains(MediaType.APPLICATION_JSON),
                "JSON converter should support APPLICATION_JSON");
        assertTrue(supportedMediaTypes.stream().anyMatch(mediaType ->
                        mediaType.getType().equals("application") &&
                        mediaType.getSubtype().endsWith("+json")),
                "JSON converter should support application/*+json");
    }

    /**
     * Tests that the XML message converter is properly configured with the expected media types.
     * This test verifies that the XML converter supports APPLICATION_XML and application/*+xml media types.
     */
    @Test
    @DisplayName("XML message converter should be properly configured")
    public void xmlMessageConverterShouldBeProperlyConfigured() {
        // Get the XML converter bean from the application context
        MappingJackson2XmlHttpMessageConverter converter = webConfig.mappingJackson2XmlHttpMessageConverter();

        // Verify that the converter is properly configured
        assertNotNull(converter, "XML converter should not be null");

        // Verify that the converter supports the expected media types
        List<MediaType> supportedMediaTypes = converter.getSupportedMediaTypes();
        assertTrue(supportedMediaTypes.contains(MediaType.APPLICATION_XML),
                "XML converter should support APPLICATION_XML");
        assertTrue(supportedMediaTypes.stream().anyMatch(mediaType ->
                        mediaType.getType().equals("application") &&
                        mediaType.getSubtype().endsWith("+xml")),
                "XML converter should support application/*+xml");
    }

    /**
     * Tests that the exception resolver is properly configured.
     * This test verifies that the exception resolver is a SimpleMappingExceptionResolver.
     */
    @Test
    @DisplayName("Exception resolver should be properly configured")
    public void exceptionResolverShouldBeProperlyConfigured() {
        // Get the exception resolver bean from the application context
        HandlerExceptionResolver resolver = webConfig.customExceptionResolver();

        // Verify that the resolver is properly configured
        assertNotNull(resolver, "Exception resolver should not be null");
        assertTrue(resolver instanceof SimpleMappingExceptionResolver,
                "Exception resolver should be a SimpleMappingExceptionResolver");
    }

    /**
     * Tests that all required beans are available in the application context.
     * This test verifies that all the beans required by the WebConfig class are properly created
     * and available in the application context.
     */
    @Test
    @DisplayName("All required beans should be available in the application context")
    public void allRequiredBeansShouldBeAvailableInApplicationContext() {
        // Verify that all required beans are available in the application context
        assertNotNull(context.getBean(WebConfig.class), "WebConfig bean should be available");
        assertNotNull(context.getBean(ObjectMapper.class), "ObjectMapper bean should be available");
        assertNotNull(context.getBean(MappingJackson2HttpMessageConverter.class), "JSON converter bean should be available");
        assertNotNull(context.getBean(MappingJackson2XmlHttpMessageConverter.class), "XML converter bean should be available");
        assertNotNull(context.getBean(HandlerExceptionResolver.class), "Exception resolver bean should be available");
    }

    /**
     * Test configuration class to provide any additional beans needed for testing.
     */
    @TestConfiguration
    static class TestConfig {
        // Add any additional beans needed for testing here
    }
}