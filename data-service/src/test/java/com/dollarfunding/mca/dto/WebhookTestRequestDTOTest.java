package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link WebhookTestRequestDTO}.
 * Tests validation constraints, JSON serialization/deserialization, and field validation.
 */
public class WebhookTestRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        objectMapper = new ObjectMapper();
    }

    /**
     * Creates a valid WebhookTestRequestDTO for testing.
     *
     * @return A valid WebhookTestRequestDTO instance
     */
    private WebhookTestRequestDTO createValidDTO() {
        Map<String, Object> payload = new HashMap<>();
        payload.put("event", "application.approved");
        payload.put("applicationId", "app-123");
        payload.put("timestamp", "2023-01-01T12:00:00Z");

        WebhookTestRequestDTO dto = new WebhookTestRequestDTO();
        dto.setWebhookId("webhook-123");
        dto.setTestPayload(payload);
        dto.setAsync(false);
        dto.setRetry(true);
        dto.setIncludeSignature(true);

        return dto;
    }

    @Nested
    @DisplayName("Required Field Validation Tests")
    class RequiredFieldValidationTests {

        @Test
        @DisplayName("Should validate when all required fields are present")
        void shouldValidateWhenAllRequiredFieldsArePresent() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertTrue(violations.isEmpty(), "No violations should be found");
        }

        @Test
        @DisplayName("Should fail validation when webhookId is null")
        void shouldFailValidationWhenWebhookIdIsNull() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();
            dto.setWebhookId(null);

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertEquals(1, violations.size(), "Should have one violation");
            ConstraintViolation<WebhookTestRequestDTO> violation = violations.iterator().next();
            assertEquals("webhookId", violation.getPropertyPath().toString(), "Violation should be on webhookId field");
            assertEquals("Webhook ID is required", violation.getMessage(), "Violation message should match");
        }

        @Test
        @DisplayName("Should fail validation when webhookId is empty")
        void shouldFailValidationWhenWebhookIdIsEmpty() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();
            dto.setWebhookId("");

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertEquals(1, violations.size(), "Should have one violation");
            ConstraintViolation<WebhookTestRequestDTO> violation = violations.iterator().next();
            assertEquals("webhookId", violation.getPropertyPath().toString(), "Violation should be on webhookId field");
            assertEquals("Webhook ID is required", violation.getMessage(), "Violation message should match");
        }

        @Test
        @DisplayName("Should fail validation when webhookId exceeds maximum length")
        void shouldFailValidationWhenWebhookIdExceedsMaxLength() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();
            dto.setWebhookId("a".repeat(37)); // 37 characters, max is 36

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertEquals(1, violations.size(), "Should have one violation");
            ConstraintViolation<WebhookTestRequestDTO> violation = violations.iterator().next();
            assertEquals("webhookId", violation.getPropertyPath().toString(), "Violation should be on webhookId field");
            assertEquals("Webhook ID cannot exceed 36 characters", violation.getMessage(), "Violation message should match");
        }

        @Test
        @DisplayName("Should fail validation when testPayload is null")
        void shouldFailValidationWhenTestPayloadIsNull() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();
            dto.setTestPayload(null);

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertEquals(1, violations.size(), "Should have one violation");
            ConstraintViolation<WebhookTestRequestDTO> violation = violations.iterator().next();
            assertEquals("testPayload", violation.getPropertyPath().toString(), "Violation should be on testPayload field");
            assertEquals("Test payload is required", violation.getMessage(), "Violation message should match");
        }
    }

    @Nested
    @DisplayName("JSON Serialization Tests")
    class JsonSerializationTests {

        @Test
        @DisplayName("Should serialize to JSON correctly")
        void shouldSerializeToJsonCorrectly() throws IOException {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();

            // When
            String json = objectMapper.writeValueAsString(dto);

            // Then
            assertTrue(json.contains("\"webhookId\":\"webhook-123\""), "JSON should contain webhookId");
            assertTrue(json.contains("\"testPayload\":"), "JSON should contain testPayload");
            assertTrue(json.contains("\"event\":\"application.approved\""), "JSON should contain event in payload");
            assertTrue(json.contains("\"applicationId\":\"app-123\""), "JSON should contain applicationId in payload");
            assertTrue(json.contains("\"async\":false"), "JSON should contain async=false");
            assertTrue(json.contains("\"retry\":true"), "JSON should contain retry=true");
            assertTrue(json.contains("\"includeSignature\":true"), "JSON should contain includeSignature=true");
        }

        @Test
        @DisplayName("Should deserialize from JSON correctly")
        void shouldDeserializeFromJsonCorrectly() throws IOException {
            // Given
            String json = "{\"webhookId\":\"webhook-123\",\"testPayload\":{\"event\":\"application.approved\",\"applicationId\":\"app-123\",\"timestamp\":\"2023-01-01T12:00:00Z\"},\"async\":false,\"retry\":true,\"includeSignature\":true}";

            // When
            WebhookTestRequestDTO dto = objectMapper.readValue(json, WebhookTestRequestDTO.class);

            // Then
            assertEquals("webhook-123", dto.getWebhookId(), "webhookId should match");
            assertNotNull(dto.getTestPayload(), "testPayload should not be null");
            assertEquals("application.approved", dto.getTestPayload().get("event"), "event in payload should match");
            assertEquals("app-123", dto.getTestPayload().get("applicationId"), "applicationId in payload should match");
            assertEquals("2023-01-01T12:00:00Z", dto.getTestPayload().get("timestamp"), "timestamp in payload should match");
            assertFalse(dto.getAsync(), "async should be false");
            assertTrue(dto.getRetry(), "retry should be true");
            assertTrue(dto.getIncludeSignature(), "includeSignature should be true");
        }

        @Test
        @DisplayName("Should throw exception when deserializing JSON with unknown properties")
        void shouldThrowExceptionWhenDeserializingJsonWithUnknownProperties() {
            // Given
            String json = "{\"webhookId\":\"webhook-123\",\"testPayload\":{\"event\":\"application.approved\"},\"unknownProperty\":\"value\"}";

            // When & Then
            assertThrows(UnrecognizedPropertyException.class, () -> {
                objectMapper.readValue(json, WebhookTestRequestDTO.class);
            }, "Should throw UnrecognizedPropertyException for unknown properties");
        }
    }

    @Nested
    @DisplayName("Custom Test Payload Handling Tests")
    class CustomTestPayloadHandlingTests {

        @Test
        @DisplayName("Should handle simple payload")
        void shouldHandleSimplePayload() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();
            Map<String, Object> simplePayload = new HashMap<>();
            simplePayload.put("key", "value");
            dto.setTestPayload(simplePayload);

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertTrue(violations.isEmpty(), "No violations should be found");
            assertEquals(1, dto.getTestPayload().size(), "Payload should have 1 entry");
            assertEquals("value", dto.getTestPayload().get("key"), "Payload value should match");
        }

        @Test
        @DisplayName("Should handle complex nested payload")
        void shouldHandleComplexNestedPayload() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();
            Map<String, Object> nestedMap = new HashMap<>();
            nestedMap.put("nestedKey", "nestedValue");
            nestedMap.put("nestedNumber", 123);

            Map<String, Object> complexPayload = new HashMap<>();
            complexPayload.put("string", "value");
            complexPayload.put("number", 42);
            complexPayload.put("boolean", true);
            complexPayload.put("nested", nestedMap);
            dto.setTestPayload(complexPayload);

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertTrue(violations.isEmpty(), "No violations should be found");
            assertEquals(4, dto.getTestPayload().size(), "Payload should have 4 entries");
            assertEquals("value", dto.getTestPayload().get("string"), "String value should match");
            assertEquals(42, dto.getTestPayload().get("number"), "Number value should match");
            assertEquals(true, dto.getTestPayload().get("boolean"), "Boolean value should match");
            assertTrue(dto.getTestPayload().get("nested") instanceof Map, "Nested value should be a Map");

            @SuppressWarnings("unchecked")
            Map<String, Object> retrievedNestedMap = (Map<String, Object>) dto.getTestPayload().get("nested");
            assertEquals("nestedValue", retrievedNestedMap.get("nestedKey"), "Nested string value should match");
            assertEquals(123, retrievedNestedMap.get("nestedNumber"), "Nested number value should match");
        }

        @Test
        @DisplayName("Should handle empty payload map")
        void shouldHandleEmptyPayloadMap() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();
            dto.setTestPayload(new HashMap<>());

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertTrue(violations.isEmpty(), "No violations should be found");
            assertTrue(dto.getTestPayload().isEmpty(), "Payload should be empty");
        }
    }

    @Nested
    @DisplayName("Delivery Options Tests")
    class DeliveryOptionsTests {

        @Test
        @DisplayName("Should have correct default values for delivery options")
        void shouldHaveCorrectDefaultValuesForDeliveryOptions() {
            // Given
            WebhookTestRequestDTO dto = new WebhookTestRequestDTO();

            // Then
            assertFalse(dto.getAsync(), "Default async value should be false");
            assertTrue(dto.getRetry(), "Default retry value should be true");
            assertTrue(dto.getIncludeSignature(), "Default includeSignature value should be true");
        }

        @Test
        @DisplayName("Should set async option correctly")
        void shouldSetAsyncOptionCorrectly() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();

            // When
            dto.setAsync(true);

            // Then
            assertTrue(dto.getAsync(), "Async should be true");
        }

        @Test
        @DisplayName("Should set retry option correctly")
        void shouldSetRetryOptionCorrectly() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();

            // When
            dto.setRetry(false);

            // Then
            assertFalse(dto.getRetry(), "Retry should be false");
        }

        @Test
        @DisplayName("Should set includeSignature option correctly")
        void shouldSetIncludeSignatureOptionCorrectly() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();

            // When
            dto.setIncludeSignature(false);

            // Then
            assertFalse(dto.getIncludeSignature(), "IncludeSignature should be false");
        }

        @Test
        @DisplayName("Should deserialize JSON with missing delivery options to default values")
        void shouldDeserializeJsonWithMissingDeliveryOptionsToDefaultValues() throws IOException {
            // Given
            String json = "{\"webhookId\":\"webhook-123\",\"testPayload\":{\"event\":\"application.approved\"}}";

            // When
            WebhookTestRequestDTO dto = objectMapper.readValue(json, WebhookTestRequestDTO.class);

            // Then
            assertFalse(dto.getAsync(), "Default async value should be false");
            assertTrue(dto.getRetry(), "Default retry value should be true");
            assertTrue(dto.getIncludeSignature(), "Default includeSignature value should be true");
        }
    }

    @Nested
    @DisplayName("Validation Failure Scenarios Tests")
    class ValidationFailureScenariosTests {

        @Test
        @DisplayName("Should fail validation with multiple violations")
        void shouldFailValidationWithMultipleViolations() {
            // Given
            WebhookTestRequestDTO dto = new WebhookTestRequestDTO();
            // Both required fields are missing

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertEquals(2, violations.size(), "Should have two violations");
            
            // Convert violations to a more easily testable format
            Map<String, String> violationMap = new HashMap<>();
            for (ConstraintViolation<WebhookTestRequestDTO> violation : violations) {
                violationMap.put(violation.getPropertyPath().toString(), violation.getMessage());
            }
            
            assertTrue(violationMap.containsKey("webhookId"), "Should have violation for webhookId");
            assertEquals("Webhook ID is required", violationMap.get("webhookId"), "webhookId violation message should match");
            
            assertTrue(violationMap.containsKey("testPayload"), "Should have violation for testPayload");
            assertEquals("Test payload is required", violationMap.get("testPayload"), "testPayload violation message should match");
        }

        @Test
        @DisplayName("Should validate with all fields set to valid values")
        void shouldValidateWithAllFieldsSetToValidValues() {
            // Given
            WebhookTestRequestDTO dto = createValidDTO();

            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);

            // Then
            assertTrue(violations.isEmpty(), "No violations should be found");
        }
    }

    @Test
    @DisplayName("Should use constructor with all fields")
    void shouldUseConstructorWithAllFields() {
        // Given
        Map<String, Object> payload = new HashMap<>();
        payload.put("event", "application.approved");

        // When
        WebhookTestRequestDTO dto = new WebhookTestRequestDTO(
                "webhook-123",
                payload,
                true,
                false,
                false
        );

        // Then
        assertEquals("webhook-123", dto.getWebhookId(), "webhookId should match");
        assertSame(payload, dto.getTestPayload(), "testPayload should be the same instance");
        assertTrue(dto.getAsync(), "async should be true");
        assertFalse(dto.getRetry(), "retry should be false");
        assertFalse(dto.getIncludeSignature(), "includeSignature should be false");
    }

    @Test
    @DisplayName("Should generate correct toString output")
    void shouldGenerateCorrectToStringOutput() {
        // Given
        WebhookTestRequestDTO dto = createValidDTO();

        // When
        String toStringResult = dto.toString();

        // Then
        assertTrue(toStringResult.contains("webhookId='webhook-123'"), "toString should contain webhookId");
        assertTrue(toStringResult.contains("testPayload="), "toString should contain testPayload");
        assertTrue(toStringResult.contains("async=false"), "toString should contain async=false");
        assertTrue(toStringResult.contains("retry=true"), "toString should contain retry=true");
        assertTrue(toStringResult.contains("includeSignature=true"), "toString should contain includeSignature=true");
    }
}