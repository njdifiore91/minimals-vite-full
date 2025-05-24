package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.Set;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link WebhookRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly validates webhook configurations,
 * handles event type mapping correctly, and converts between DTO and entity
 * objects appropriately.
 */
@DisplayName("Webhook Request DTO Tests")
public class WebhookRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    
    @BeforeEach
    void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        objectMapper = new ObjectMapper();
        // Configure ObjectMapper to handle Java 8 date/time types
        objectMapper.findAndRegisterModules();
    }
    
    /**
     * Test data provider for invalid endpoint URLs.
     */
    static Stream<Arguments> invalidEndpointUrlProvider() {
        return Stream.of(
            Arguments.of(null, "endpointUrl", "Endpoint URL is required"),
            Arguments.of("", "endpointUrl", "Endpoint URL is required"),
            Arguments.of("http://example.com", "endpointUrl", "Endpoint URL must use HTTPS protocol"),
            Arguments.of("ftp://example.com", "endpointUrl", "Endpoint URL must use HTTPS protocol"),
            Arguments.of("https://" + "a".repeat(256), "endpointUrl", "Endpoint URL cannot exceed 255 characters")
        );
    }
    
    /**
     * Test data provider for invalid secret keys.
     */
    static Stream<Arguments> invalidSecretKeyProvider() {
        return Stream.of(
            Arguments.of(null, "secretKey", "Secret key is required"),
            Arguments.of("", "secretKey", "Secret key is required"),
            Arguments.of("short", "secretKey", "Secret key must be between 32 and 128 characters"),
            Arguments.of("a".repeat(31), "secretKey", "Secret key must be between 32 and 128 characters"),
            Arguments.of("a".repeat(129), "secretKey", "Secret key must be between 32 and 128 characters")
        );
    }
    
    /**
     * Test data provider for invalid max retry attempts.
     */
    static Stream<Arguments> invalidMaxRetryAttemptsProvider() {
        return Stream.of(
            Arguments.of(-1, "maxRetryAttempts", "Max retry attempts must be at least 0"),
            Arguments.of(11, "maxRetryAttempts", "Max retry attempts cannot exceed 10")
        );
    }

    @Test
    @DisplayName("Should create a valid DTO with all required fields")
    void shouldCreateValidDTO() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED
        );
        
        // When
        Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertTrue(violations.isEmpty(), "No validation violations should be present");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate endpoint URL field")
    @MethodSource("invalidEndpointUrlProvider")
    void shouldValidateEndpointUrlField(String endpointUrl, String fieldName, String expectedMessage) {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                endpointUrl,
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED
        );
        
        // When
        Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        boolean foundExpectedViolation = false;
        for (ConstraintViolation<WebhookRequestDTO> violation : violations) {
            if (violation.getPropertyPath().toString().equals(fieldName) && 
                violation.getMessage().equals(expectedMessage)) {
                foundExpectedViolation = true;
                break;
            }
        }
        assertTrue(foundExpectedViolation, "Expected violation not found: " + expectedMessage);
    }
    
    @ParameterizedTest
    @DisplayName("Should validate secret key field")
    @MethodSource("invalidSecretKeyProvider")
    void shouldValidateSecretKeyField(String secretKey, String fieldName, String expectedMessage) {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                secretKey,
                true,
                EventType.APPLICATION_CREATED
        );
        
        // When
        Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        boolean foundExpectedViolation = false;
        for (ConstraintViolation<WebhookRequestDTO> violation : violations) {
            if (violation.getPropertyPath().toString().equals(fieldName) && 
                violation.getMessage().equals(expectedMessage)) {
                foundExpectedViolation = true;
                break;
            }
        }
        assertTrue(foundExpectedViolation, "Expected violation not found: " + expectedMessage);
    }
    
    @Test
    @DisplayName("Should validate active field is not null")
    void shouldValidateActiveFieldNotNull() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                null,
                EventType.APPLICATION_CREATED
        );
        
        // When
        Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        ConstraintViolation<WebhookRequestDTO> violation = violations.iterator().next();
        assertEquals("active", violation.getPropertyPath().toString(), "Violation should be for the active field");
        assertEquals("Active status is required", violation.getMessage(), "Violation message should match expected");
    }
    
    @Test
    @DisplayName("Should validate event type field is not null")
    void shouldValidateEventTypeFieldNotNull() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                null
        );
        
        // When
        Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        ConstraintViolation<WebhookRequestDTO> violation = violations.iterator().next();
        assertEquals("eventType", violation.getPropertyPath().toString(), "Violation should be for the eventType field");
        assertEquals("Event type is required", violation.getMessage(), "Violation message should match expected");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate max retry attempts field")
    @MethodSource("invalidMaxRetryAttemptsProvider")
    void shouldValidateMaxRetryAttemptsField(Integer maxRetryAttempts, String fieldName, String expectedMessage) {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED,
                maxRetryAttempts,
                "X-Webhook-Signature"
        );
        
        // When
        Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        boolean foundExpectedViolation = false;
        for (ConstraintViolation<WebhookRequestDTO> violation : violations) {
            if (violation.getPropertyPath().toString().equals(fieldName) && 
                violation.getMessage().equals(expectedMessage)) {
                foundExpectedViolation = true;
                break;
            }
        }
        assertTrue(foundExpectedViolation, "Expected violation not found: " + expectedMessage);
    }
    
    @Test
    @DisplayName("Should validate signature header length")
    void shouldValidateSignatureHeaderLength() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED,
                3,
                "X".repeat(101) // Exceeds max length of 100
        );
        
        // When
        Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        ConstraintViolation<WebhookRequestDTO> violation = violations.iterator().next();
        assertEquals("signatureHeader", violation.getPropertyPath().toString(), "Violation should be for the signatureHeader field");
        assertEquals("Signature header cannot exceed 100 characters", violation.getMessage(), "Violation message should match expected");
    }
    
    @Test
    @DisplayName("Should serialize to JSON correctly")
    void shouldSerializeToJsonCorrectly() throws Exception {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED,
                5,
                "X-Custom-Signature"
        );
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertTrue(json.contains("\"endpoint_url\":\"https://example.com/webhook\""), "JSON should contain endpoint_url field");
        assertTrue(json.contains("\"secret_key\":\"" + "a".repeat(32) + "\""), "JSON should contain secret_key field");
        assertTrue(json.contains("\"active\":true"), "JSON should contain active field");
        assertTrue(json.contains("\"event_type\":\"APPLICATION_CREATED\""), "JSON should contain event_type field");
        assertTrue(json.contains("\"max_retry_attempts\":5"), "JSON should contain max_retry_attempts field");
        assertTrue(json.contains("\"signature_header\":\"X-Custom-Signature\""), "JSON should contain signature_header field");
    }
    
    @Test
    @DisplayName("Should deserialize from JSON correctly")
    void shouldDeserializeFromJsonCorrectly() throws Exception {
        // Given
        String json = "{\"endpoint_url\":\"https://example.com/webhook\",\"secret_key\":\"" + "a".repeat(32) + "\",\"active\":true,\"event_type\":\"APPLICATION_CREATED\",\"max_retry_attempts\":5,\"signature_header\":\"X-Custom-Signature\"}";
        
        // When
        WebhookRequestDTO dto = objectMapper.readValue(json, WebhookRequestDTO.class);
        
        // Then
        assertEquals("https://example.com/webhook", dto.getEndpointUrl(), "Endpoint URL should be deserialized correctly");
        assertEquals("a".repeat(32), dto.getSecretKey(), "Secret key should be deserialized correctly");
        assertTrue(dto.getActive(), "Active should be deserialized correctly");
        assertEquals(EventType.APPLICATION_CREATED, dto.getEventType(), "Event type should be deserialized correctly");
        assertEquals(5, dto.getMaxRetryAttempts(), "Max retry attempts should be deserialized correctly");
        assertEquals("X-Custom-Signature", dto.getSignatureHeader(), "Signature header should be deserialized correctly");
    }
    
    @Test
    @DisplayName("Should convert to entity correctly")
    void shouldConvertToEntityCorrectly() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED,
                5,
                "X-Custom-Signature"
        );
        
        // When
        Webhook entity = dto.toEntity();
        
        // Then
        assertEquals("https://example.com/webhook", entity.getEndpointUrl(), "Entity endpoint URL should match DTO");
        assertEquals("a".repeat(32), entity.getSecretKey(), "Entity secret key should match DTO");
        assertTrue(entity.getActive(), "Entity active status should match DTO");
        assertEquals(EventType.APPLICATION_CREATED, entity.getEventType(), "Entity event type should match DTO");
        assertEquals(5, entity.getMaxRetryAttempts(), "Entity max retry attempts should match DTO");
        assertEquals("X-Custom-Signature", entity.getSignatureHeader(), "Entity signature header should match DTO");
    }
    
    @Test
    @DisplayName("Should convert to entity with default values when optional fields are null")
    void shouldConvertToEntityWithDefaultValues() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED
                // maxRetryAttempts and signatureHeader are null
        );
        
        // When
        Webhook entity = dto.toEntity();
        
        // Then
        assertEquals("https://example.com/webhook", entity.getEndpointUrl(), "Entity endpoint URL should match DTO");
        assertEquals("a".repeat(32), entity.getSecretKey(), "Entity secret key should match DTO");
        assertTrue(entity.getActive(), "Entity active status should match DTO");
        assertEquals(EventType.APPLICATION_CREATED, entity.getEventType(), "Entity event type should match DTO");
        // Default values should be used for null fields
        assertNotNull(entity.getMaxRetryAttempts(), "Entity max retry attempts should not be null");
        assertEquals(3, entity.getMaxRetryAttempts(), "Entity max retry attempts should use default value");
        // signatureHeader might be null or have a default value depending on the entity implementation
    }
    
    @Test
    @DisplayName("Should update entity correctly")
    void shouldUpdateEntityCorrectly() {
        // Given
        Webhook entity = new Webhook(
                "https://old-example.com/webhook",
                "b".repeat(32),
                false,
                EventType.DOCUMENT_UPLOADED
        );
        entity.setMaxRetryAttempts(2);
        entity.setSignatureHeader("X-Old-Signature");
        
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://new-example.com/webhook",
                "c".repeat(32),
                true,
                EventType.APPLICATION_CREATED,
                5,
                "X-New-Signature"
        );
        
        // When
        Webhook updatedEntity = dto.updateEntity(entity);
        
        // Then
        assertEquals("https://new-example.com/webhook", updatedEntity.getEndpointUrl(), "Entity endpoint URL should be updated");
        assertEquals("c".repeat(32), updatedEntity.getSecretKey(), "Entity secret key should be updated");
        assertTrue(updatedEntity.getActive(), "Entity active status should be updated");
        assertEquals(EventType.APPLICATION_CREATED, updatedEntity.getEventType(), "Entity event type should be updated");
        assertEquals(5, updatedEntity.getMaxRetryAttempts(), "Entity max retry attempts should be updated");
        assertEquals("X-New-Signature", updatedEntity.getSignatureHeader(), "Entity signature header should be updated");
    }
    
    @Test
    @DisplayName("Should create new entity when updating with null entity")
    void shouldCreateNewEntityWhenUpdatingWithNullEntity() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED,
                5,
                "X-Custom-Signature"
        );
        
        // When
        Webhook entity = dto.updateEntity(null);
        
        // Then
        assertNotNull(entity, "Entity should not be null");
        assertEquals("https://example.com/webhook", entity.getEndpointUrl(), "Entity endpoint URL should match DTO");
        assertEquals("a".repeat(32), entity.getSecretKey(), "Entity secret key should match DTO");
        assertTrue(entity.getActive(), "Entity active status should match DTO");
        assertEquals(EventType.APPLICATION_CREATED, entity.getEventType(), "Entity event type should match DTO");
        assertEquals(5, entity.getMaxRetryAttempts(), "Entity max retry attempts should match DTO");
        assertEquals("X-Custom-Signature", entity.getSignatureHeader(), "Entity signature header should match DTO");
    }
    
    @Test
    @DisplayName("Should create DTO from entity correctly")
    void shouldCreateDtoFromEntityCorrectly() {
        // Given
        Webhook entity = new Webhook(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED
        );
        entity.setMaxRetryAttempts(5);
        entity.setSignatureHeader("X-Custom-Signature");
        
        // When
        WebhookRequestDTO dto = WebhookRequestDTO.fromEntity(entity);
        
        // Then
        assertEquals("https://example.com/webhook", dto.getEndpointUrl(), "DTO endpoint URL should match entity");
        assertEquals("a".repeat(32), dto.getSecretKey(), "DTO secret key should match entity");
        assertTrue(dto.getActive(), "DTO active status should match entity");
        assertEquals(EventType.APPLICATION_CREATED, dto.getEventType(), "DTO event type should match entity");
        assertEquals(5, dto.getMaxRetryAttempts(), "DTO max retry attempts should match entity");
        assertEquals("X-Custom-Signature", dto.getSignatureHeader(), "DTO signature header should match entity");
    }
    
    @Test
    @DisplayName("Should return null when creating DTO from null entity")
    void shouldReturnNullWhenCreatingDtoFromNullEntity() {
        // When
        WebhookRequestDTO dto = WebhookRequestDTO.fromEntity(null);
        
        // Then
        assertNull(dto, "DTO should be null when entity is null");
    }
    
    @Test
    @DisplayName("Should validate event type correctly")
    void shouldValidateEventTypeCorrectly() {
        // Given
        WebhookRequestDTO validDto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED
        );
        
        WebhookRequestDTO nullEventTypeDto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                null
        );
        
        // When/Then
        assertTrue(validDto.isValidEventType(), "Valid event type should be validated as true");
        assertFalse(nullEventTypeDto.isValidEventType(), "Null event type should be validated as false");
    }
    
    @Test
    @DisplayName("Should handle toString correctly")
    void shouldHandleToStringCorrectly() {
        // Given
        WebhookRequestDTO dto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "a".repeat(32),
                true,
                EventType.APPLICATION_CREATED,
                5,
                "X-Custom-Signature"
        );
        
        // When
        String toString = dto.toString();
        
        // Then
        assertTrue(toString.contains("endpointUrl='https://example.com/webhook'"), "toString should include endpointUrl");
        assertTrue(toString.contains("active=true"), "toString should include active");
        assertTrue(toString.contains("eventType=APPLICATION_CREATED"), "toString should include eventType");
        assertTrue(toString.contains("maxRetryAttempts=5"), "toString should include maxRetryAttempts");
        assertTrue(toString.contains("signatureHeader='X-Custom-Signature'"), "toString should include signatureHeader");
        // Secret key should not be included in toString for security reasons
        assertFalse(toString.contains("a".repeat(32)), "toString should not include the secret key");
    }
}