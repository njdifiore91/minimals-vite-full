package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link WebhookRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly validates webhook configurations,
 * handles event type mapping correctly, and converts between DTO and entity
 * objects appropriately.
 */
@DisplayName("WebhookRequestDTO Tests")
class WebhookRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    private WebhookRequestDTO validDto;

    @BeforeEach
    void setUp() {
        // Initialize validator
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Initialize ObjectMapper
        objectMapper = new ObjectMapper();
        
        // Create a valid DTO for testing
        validDto = new WebhookRequestDTO(
                "https://example.com/webhook",
                "APPLICATION_CREATED",
                "secretKey1234567890abcdef",
                true,
                "X-Webhook-Signature"
        );
    }

    @Nested
    @DisplayName("Validation Tests")
    class ValidationTests {

        @Test
        @DisplayName("Valid DTO should pass validation")
        void validDtoShouldPassValidation() {
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "Valid DTO should not have validation violations");
        }

        @Test
        @DisplayName("DTO with null active status should fail validation")
        void dtoWithNullActiveStatusShouldFailValidation() {
            // Given
            WebhookRequestDTO dto = new WebhookRequestDTO(
                    "https://example.com/webhook",
                    "APPLICATION_CREATED",
                    "secretKey1234567890abcdef",
                    null,
                    "X-Webhook-Signature"
            );
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null active status should have validation violations");
            assertEquals(1, violations.size(), "Should have exactly one violation");
            
            ConstraintViolation<WebhookRequestDTO> violation = violations.iterator().next();
            assertEquals("active", violation.getPropertyPath().toString(), "Violation should be on active field");
            assertEquals("Active status is required", violation.getMessage(), "Violation message should match annotation");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "\t", "\n"})
        @DisplayName("DTO with blank endpoint URL should fail validation")
        void dtoWithBlankEndpointUrlShouldFailValidation(String url) {
            // Given
            validDto.setEndpointUrl(url);
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with blank endpoint URL should have validation violations");
            
            boolean hasEndpointUrlViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("endpointUrl") && 
                              v.getMessage().equals("Endpoint URL is required"));
            
            assertTrue(hasEndpointUrlViolation, "Should have a violation on endpointUrl field");
        }

        @ParameterizedTest
        @ValueSource(strings = {"ftp://example.com", "example.com", "http:/invalid-url", "https://"})
        @DisplayName("DTO with invalid endpoint URL pattern should fail validation")
        void dtoWithInvalidEndpointUrlPatternShouldFailValidation(String url) {
            // Given
            validDto.setEndpointUrl(url);
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with invalid endpoint URL pattern should have validation violations");
            
            boolean hasEndpointUrlPatternViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("endpointUrl") && 
                              v.getMessage().contains("must be a valid URL"));
            
            assertTrue(hasEndpointUrlPatternViolation, "Should have a pattern violation on endpointUrl field");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "\t", "\n"})
        @DisplayName("DTO with blank event type should fail validation")
        void dtoWithBlankEventTypeShouldFailValidation(String eventType) {
            // Given
            validDto.setEventType(eventType);
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with blank event type should have validation violations");
            
            boolean hasEventTypeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("eventType") && 
                              v.getMessage().equals("Event type is required"));
            
            assertTrue(hasEventTypeViolation, "Should have a violation on eventType field");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "\t", "\n"})
        @DisplayName("DTO with blank secret key should fail validation")
        void dtoWithBlankSecretKeyShouldFailValidation(String secretKey) {
            // Given
            validDto.setSecretKey(secretKey);
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with blank secret key should have validation violations");
            
            boolean hasSecretKeyViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("secretKey") && 
                              v.getMessage().equals("Secret key is required"));
            
            assertTrue(hasSecretKeyViolation, "Should have a violation on secretKey field");
        }

        @ParameterizedTest
        @ValueSource(strings = {"short", "123456789012345"})
        @DisplayName("DTO with secret key shorter than 16 characters should fail validation")
        void dtoWithShortSecretKeyShouldFailValidation(String secretKey) {
            // Given
            validDto.setSecretKey(secretKey);
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with short secret key should have validation violations");
            
            boolean hasSecretKeySizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("secretKey") && 
                              v.getMessage().contains("must be between 16 and 64"));
            
            assertTrue(hasSecretKeySizeViolation, "Should have a size violation on secretKey field");
        }

        @Test
        @DisplayName("DTO with secret key longer than 64 characters should fail validation")
        void dtoWithLongSecretKeyShouldFailValidation() {
            // Given
            String longSecretKey = "a".repeat(65); // 65 characters
            validDto.setSecretKey(longSecretKey);
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with long secret key should have validation violations");
            
            boolean hasSecretKeySizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("secretKey") && 
                              v.getMessage().contains("must be between 16 and 64"));
            
            assertTrue(hasSecretKeySizeViolation, "Should have a size violation on secretKey field");
        }

        @Test
        @DisplayName("DTO with signature header longer than 100 characters should fail validation")
        void dtoWithLongSignatureHeaderShouldFailValidation() {
            // Given
            String longHeader = "X-".repeat(50); // 100+ characters
            validDto.setSignatureHeader(longHeader);
            
            // When
            Set<ConstraintViolation<WebhookRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with long signature header should have validation violations");
            
            boolean hasSignatureHeaderSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("signatureHeader") && 
                              v.getMessage().contains("cannot exceed 100 characters"));
            
            assertTrue(hasSignatureHeaderSizeViolation, "Should have a size violation on signatureHeader field");
        }
    }

    @Nested
    @DisplayName("JSON Serialization/Deserialization Tests")
    class JsonTests {

        @Test
        @DisplayName("DTO should serialize to JSON correctly")
        void dtoShouldSerializeToJsonCorrectly() throws Exception {
            // When
            String json = objectMapper.writeValueAsString(validDto);
            
            // Then
            assertNotNull(json, "JSON should not be null");
            assertTrue(json.contains("\"endpoint_url\":\"https://example.com/webhook\""), "JSON should contain endpoint_url field");
            assertTrue(json.contains("\"event_type\":\"APPLICATION_CREATED\""), "JSON should contain event_type field");
            assertTrue(json.contains("\"secret_key\":\"secretKey1234567890abcdef\""), "JSON should contain secret_key field");
            assertTrue(json.contains("\"active\":true"), "JSON should contain active field");
            assertTrue(json.contains("\"signature_header\":\"X-Webhook-Signature\""), "JSON should contain signature_header field");
        }

        @Test
        @DisplayName("JSON should deserialize to DTO correctly")
        void jsonShouldDeserializeToDtoCorrectly() throws Exception {
            // Given
            String json = "{\"endpoint_url\":\"https://api.example.org/hooks\",\"event_type\":\"DOCUMENT_UPLOADED\",\"secret_key\":\"abcdef1234567890abcdef\",\"active\":false,\"signature_header\":\"X-Signature\"}";            
            
            // When
            WebhookRequestDTO dto = objectMapper.readValue(json, WebhookRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("https://api.example.org/hooks", dto.getEndpointUrl(), "Endpoint URL should match");
            assertEquals("DOCUMENT_UPLOADED", dto.getEventType(), "Event type should match");
            assertEquals("abcdef1234567890abcdef", dto.getSecretKey(), "Secret key should match");
            assertEquals(false, dto.getActive(), "Active status should match");
            assertEquals("X-Signature", dto.getSignatureHeader(), "Signature header should match");
        }

        @Test
        @DisplayName("DTO should ignore unknown JSON properties")
        void dtoShouldIgnoreUnknownJsonProperties() throws Exception {
            // Given
            String json = "{\"endpoint_url\":\"https://example.com/webhook\",\"event_type\":\"APPLICATION_CREATED\",\"secret_key\":\"secretKey1234567890abcdef\",\"active\":true,\"unknown_field\":\"value\"}";            
            
            // When
            WebhookRequestDTO dto = objectMapper.readValue(json, WebhookRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("https://example.com/webhook", dto.getEndpointUrl(), "Endpoint URL should match");
            assertEquals("APPLICATION_CREATED", dto.getEventType(), "Event type should match");
            assertEquals("secretKey1234567890abcdef", dto.getSecretKey(), "Secret key should match");
            assertEquals(true, dto.getActive(), "Active status should match");
            // Unknown field should be ignored without exception
        }
    }

    @Nested
    @DisplayName("Entity Conversion Tests")
    class EntityConversionTests {

        @Test
        @DisplayName("DTO should convert to entity correctly")
        void dtoShouldConvertToEntityCorrectly() {
            // When
            Webhook entity = validDto.toEntity();
            
            // Then
            assertNotNull(entity, "Entity should not be null");
            assertEquals(validDto.getEndpointUrl(), entity.getEndpointUrl(), "Endpoint URL should match");
            assertEquals(EventType.valueOf(validDto.getEventType()), entity.getEventType(), "Event type should match");
            assertEquals(validDto.getSecretKey(), entity.getSecretKey(), "Secret key should match");
            assertEquals(validDto.getActive(), entity.getActive(), "Active status should match");
            assertEquals(validDto.getSignatureHeader(), entity.getSignatureHeader(), "Signature header should match");
        }

        @Test
        @DisplayName("DTO should update existing entity correctly")
        void dtoShouldUpdateExistingEntityCorrectly() {
            // Given
            Webhook existingEntity = new Webhook();
            existingEntity.setEndpointUrl("https://old-url.com/webhook");
            existingEntity.setEventType(EventType.APPLICATION_UPDATED);
            existingEntity.setSecretKey("oldSecretKey12345678");
            existingEntity.setActive(false);
            existingEntity.setSignatureHeader("X-Old-Signature");
            
            // When
            Webhook updatedEntity = validDto.updateEntity(existingEntity);
            
            // Then
            assertNotNull(updatedEntity, "Updated entity should not be null");
            assertSame(existingEntity, updatedEntity, "Should return the same entity instance");
            assertEquals(validDto.getEndpointUrl(), updatedEntity.getEndpointUrl(), "Endpoint URL should be updated");
            assertEquals(EventType.valueOf(validDto.getEventType()), updatedEntity.getEventType(), "Event type should be updated");
            assertEquals(validDto.getSecretKey(), updatedEntity.getSecretKey(), "Secret key should be updated");
            assertEquals(validDto.getActive(), updatedEntity.getActive(), "Active status should be updated");
            assertEquals(validDto.getSignatureHeader(), updatedEntity.getSignatureHeader(), "Signature header should be updated");
        }

        @Test
        @DisplayName("DTO should throw exception when updating null entity")
        void dtoShouldThrowExceptionWhenUpdatingNullEntity() {
            // When/Then
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validDto.updateEntity(null),
                "Should throw IllegalArgumentException when entity is null"
            );
            
            assertEquals("Webhook entity cannot be null", exception.getMessage(), "Exception message should match");
        }
    }

    @Nested
    @DisplayName("Event Type Validation Tests")
    class EventTypeValidationTests {

        @ParameterizedTest
        @ValueSource(strings = {
            "APPLICATION_CREATED", "APPLICATION_UPDATED", "APPLICATION_APPROVED", 
            "APPLICATION_REJECTED", "DOCUMENT_UPLOADED", "DOCUMENT_PROCESSED"
        })
        @DisplayName("DTO with valid event type should pass validation")
        void dtoWithValidEventTypeShouldPassValidation(String eventType) {
            // Given
            validDto.setEventType(eventType);
            
            // When
            boolean isValid = validDto.isValidEventType();
            
            // Then
            assertTrue(isValid, "Valid event type should pass validation");
        }

        @ParameterizedTest
        @ValueSource(strings = {
            "INVALID_EVENT", "APPLICATION_DELETED", "DOCUMENT_VIEWED", 
            "application_created", "Application_Created", ""
        })
        @DisplayName("DTO with invalid event type should fail validation")
        void dtoWithInvalidEventTypeShouldFailValidation(String eventType) {
            // Given
            validDto.setEventType(eventType);
            
            // When
            boolean isValid = validDto.isValidEventType();
            
            // Then
            assertFalse(isValid, "Invalid event type should fail validation");
        }

        @Test
        @DisplayName("toEntity should throw exception for invalid event type")
        void toEntityShouldThrowExceptionForInvalidEventType() {
            // Given
            validDto.setEventType("INVALID_EVENT");
            
            // When/Then
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validDto.toEntity(),
                "Should throw IllegalArgumentException for invalid event type"
            );
            
            assertTrue(exception.getMessage().contains("Invalid event type"), 
                    "Exception message should mention invalid event type");
        }

        @Test
        @DisplayName("updateEntity should throw exception for invalid event type")
        void updateEntityShouldThrowExceptionForInvalidEventType() {
            // Given
            validDto.setEventType("INVALID_EVENT");
            Webhook existingEntity = new Webhook();
            
            // When/Then
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validDto.updateEntity(existingEntity),
                "Should throw IllegalArgumentException for invalid event type"
            );
            
            assertTrue(exception.getMessage().contains("Invalid event type"), 
                    "Exception message should mention invalid event type");
        }
    }

    @Nested
    @DisplayName("ToString Tests")
    class ToStringTests {

        @Test
        @DisplayName("toString should include all fields except secret key value")
        void toStringShouldIncludeAllFieldsExceptSecretKeyValue() {
            // When
            String toString = validDto.toString();
            
            // Then
            assertTrue(toString.contains("endpointUrl='https://example.com/webhook'"), 
                    "toString should include endpointUrl field");
            assertTrue(toString.contains("eventType='APPLICATION_CREATED'"), 
                    "toString should include eventType field");
            assertTrue(toString.contains("secretKey='[REDACTED]'"), 
                    "toString should include secretKey field but redact the value");
            assertTrue(toString.contains("active=true"), 
                    "toString should include active field");
            assertTrue(toString.contains("signatureHeader='X-Webhook-Signature'"), 
                    "toString should include signatureHeader field");
            
            // Ensure the actual secret key value is not included
            assertFalse(toString.contains("secretKey1234567890abcdef"), 
                    "toString should not include the actual secret key value");
        }
    }
}