package com.dollarfunding.mca.dto;

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
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link WebhookTestRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and field validation.
 * 
 * This test suite ensures that the DTO properly validates webhook test requests,
 * handles custom payloads correctly, and validates delivery options appropriately.
 */
@DisplayName("WebhookTestRequestDTO Tests")
class WebhookTestRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    private WebhookTestRequestDTO validDto;
    private Map<String, Object> testPayload;

    @BeforeEach
    void setUp() {
        // Initialize validator
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Initialize ObjectMapper
        objectMapper = new ObjectMapper();
        
        // Create a test payload
        testPayload = new HashMap<>();
        testPayload.put("applicationId", "app-123");
        testPayload.put("status", "APPROVED");
        testPayload.put("timestamp", "2023-06-15T14:30:00Z");
        
        // Create a valid DTO for testing
        validDto = new WebhookTestRequestDTO(
                "webhook-123",
                testPayload,
                false,
                true,
                true
        );
    }

    @Nested
    @DisplayName("Validation Tests")
    class ValidationTests {

        @Test
        @DisplayName("Valid DTO should pass validation")
        void validDtoShouldPassValidation() {
            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "Valid DTO should not have validation violations");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "\t", "\n"})
        @DisplayName("DTO with blank webhook ID should fail validation")
        void dtoWithBlankWebhookIdShouldFailValidation(String webhookId) {
            // Given
            validDto.setWebhookId(webhookId);
            
            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with blank webhook ID should have validation violations");
            
            boolean hasWebhookIdViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("webhookId") && 
                              v.getMessage().equals("Webhook ID is required"));
            
            assertTrue(hasWebhookIdViolation, "Should have a violation on webhookId field");
        }

        @Test
        @DisplayName("DTO with webhook ID exceeding max length should fail validation")
        void dtoWithLongWebhookIdShouldFailValidation() {
            // Given
            String longWebhookId = "a".repeat(37); // 37 characters (max is 36)
            validDto.setWebhookId(longWebhookId);
            
            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with long webhook ID should have validation violations");
            
            boolean hasWebhookIdSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("webhookId") && 
                              v.getMessage().contains("cannot exceed 36 characters"));
            
            assertTrue(hasWebhookIdSizeViolation, "Should have a size violation on webhookId field");
        }

        @Test
        @DisplayName("DTO with null test payload should fail validation")
        void dtoWithNullTestPayloadShouldFailValidation() {
            // Given
            validDto.setTestPayload(null);
            
            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null test payload should have validation violations");
            
            boolean hasTestPayloadViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("testPayload") && 
                              v.getMessage().equals("Test payload is required"));
            
            assertTrue(hasTestPayloadViolation, "Should have a violation on testPayload field");
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
            assertTrue(json.contains("\"webhookId\":\"webhook-123\""), "JSON should contain webhookId field");
            assertTrue(json.contains("\"testPayload\":"), "JSON should contain testPayload field");
            assertTrue(json.contains("\"applicationId\":\"app-123\""), "JSON should contain applicationId in testPayload");
            assertTrue(json.contains("\"status\":\"APPROVED\""), "JSON should contain status in testPayload");
            assertTrue(json.contains("\"async\":false"), "JSON should contain async field");
            assertTrue(json.contains("\"retry\":true"), "JSON should contain retry field");
            assertTrue(json.contains("\"includeSignature\":true"), "JSON should contain includeSignature field");
        }

        @Test
        @DisplayName("JSON should deserialize to DTO correctly")
        void jsonShouldDeserializeToDtoCorrectly() throws Exception {
            // Given
            String json = "{\"webhookId\":\"webhook-456\",\"testPayload\":{\"applicationId\":\"app-456\",\"status\":\"REJECTED\",\"reason\":\"Insufficient documentation\"},\"async\":true,\"retry\":false,\"includeSignature\":false}";
            
            // When
            WebhookTestRequestDTO dto = objectMapper.readValue(json, WebhookTestRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("webhook-456", dto.getWebhookId(), "Webhook ID should match");
            assertNotNull(dto.getTestPayload(), "Test payload should not be null");
            assertEquals("app-456", dto.getTestPayload().get("applicationId"), "Application ID in test payload should match");
            assertEquals("REJECTED", dto.getTestPayload().get("status"), "Status in test payload should match");
            assertEquals("Insufficient documentation", dto.getTestPayload().get("reason"), "Reason in test payload should match");
            assertEquals(true, dto.getAsync(), "Async flag should match");
            assertEquals(false, dto.getRetry(), "Retry flag should match");
            assertEquals(false, dto.getIncludeSignature(), "Include signature flag should match");
        }

        @Test
        @DisplayName("DTO should ignore unknown JSON properties")
        void dtoShouldIgnoreUnknownJsonProperties() throws Exception {
            // Given
            String json = "{\"webhookId\":\"webhook-123\",\"testPayload\":{\"applicationId\":\"app-123\"},\"async\":false,\"retry\":true,\"includeSignature\":true,\"unknown_field\":\"value\"}";
            
            // When
            WebhookTestRequestDTO dto = objectMapper.readValue(json, WebhookTestRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("webhook-123", dto.getWebhookId(), "Webhook ID should match");
            assertNotNull(dto.getTestPayload(), "Test payload should not be null");
            assertEquals("app-123", dto.getTestPayload().get("applicationId"), "Application ID in test payload should match");
            assertEquals(false, dto.getAsync(), "Async flag should match");
            assertEquals(true, dto.getRetry(), "Retry flag should match");
            assertEquals(true, dto.getIncludeSignature(), "Include signature flag should match");
            // Unknown field should be ignored without exception
        }

        @Test
        @DisplayName("DTO should handle null optional fields during deserialization")
        void dtoShouldHandleNullOptionalFieldsDuringDeserialization() throws Exception {
            // Given
            String json = "{\"webhookId\":\"webhook-123\",\"testPayload\":{\"applicationId\":\"app-123\"}}";
            
            // When
            WebhookTestRequestDTO dto = objectMapper.readValue(json, WebhookTestRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("webhook-123", dto.getWebhookId(), "Webhook ID should match");
            assertNotNull(dto.getTestPayload(), "Test payload should not be null");
            assertEquals("app-123", dto.getTestPayload().get("applicationId"), "Application ID in test payload should match");
            assertEquals(false, dto.getAsync(), "Async flag should default to false");
            assertEquals(true, dto.getRetry(), "Retry flag should default to true");
            assertEquals(true, dto.getIncludeSignature(), "Include signature flag should default to true");
        }
    }

    @Nested
    @DisplayName("Custom Payload Tests")
    class CustomPayloadTests {

        @Test
        @DisplayName("DTO should accept complex nested payload")
        void dtoShouldAcceptComplexNestedPayload() {
            // Given
            Map<String, Object> nestedData = new HashMap<>();
            nestedData.put("firstName", "John");
            nestedData.put("lastName", "Doe");
            nestedData.put("age", 35);
            
            Map<String, Object> addressData = new HashMap<>();
            addressData.put("street", "123 Main St");
            addressData.put("city", "New York");
            addressData.put("zipCode", "10001");
            
            nestedData.put("address", addressData);
            
            Map<String, Object> complexPayload = new HashMap<>();
            complexPayload.put("applicationId", "app-789");
            complexPayload.put("merchant", nestedData);
            complexPayload.put("amount", 50000.00);
            complexPayload.put("approved", true);
            
            // When
            validDto.setTestPayload(complexPayload);
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "DTO with complex nested payload should pass validation");
            assertEquals(complexPayload, validDto.getTestPayload(), "Complex payload should be stored correctly");
            
            // Verify nested structure is preserved
            @SuppressWarnings("unchecked")
            Map<String, Object> merchant = (Map<String, Object>) validDto.getTestPayload().get("merchant");
            assertNotNull(merchant, "Nested merchant data should be preserved");
            assertEquals("John", merchant.get("firstName"), "Nested firstName should be preserved");
            
            @SuppressWarnings("unchecked")
            Map<String, Object> address = (Map<String, Object>) merchant.get("address");
            assertNotNull(address, "Nested address data should be preserved");
            assertEquals("New York", address.get("city"), "Nested city should be preserved");
        }

        @Test
        @DisplayName("DTO should handle empty payload map")
        void dtoShouldHandleEmptyPayloadMap() {
            // Given
            Map<String, Object> emptyPayload = new HashMap<>();
            
            // When
            validDto.setTestPayload(emptyPayload);
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "DTO with empty payload map should pass validation");
            assertEquals(emptyPayload, validDto.getTestPayload(), "Empty payload should be stored correctly");
            assertTrue(validDto.getTestPayload().isEmpty(), "Test payload should be empty");
        }

        @Test
        @DisplayName("DTO should handle payload with array values")
        void dtoShouldHandlePayloadWithArrayValues() throws Exception {
            // Given
            String json = "{\"webhookId\":\"webhook-123\",\"testPayload\":{\"applicationId\":\"app-123\",\"documents\":[\"doc1\",\"doc2\",\"doc3\"]}}";
            
            // When
            WebhookTestRequestDTO dto = objectMapper.readValue(json, WebhookTestRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertNotNull(dto.getTestPayload(), "Test payload should not be null");
            assertEquals("app-123", dto.getTestPayload().get("applicationId"), "Application ID should match");
            
            Object documentsObj = dto.getTestPayload().get("documents");
            assertTrue(documentsObj instanceof java.util.List, "Documents should be a List");
            
            @SuppressWarnings("unchecked")
            java.util.List<String> documents = (java.util.List<String>) documentsObj;
            assertEquals(3, documents.size(), "Documents list should have 3 items");
            assertEquals("doc1", documents.get(0), "First document should match");
            assertEquals("doc2", documents.get(1), "Second document should match");
            assertEquals("doc3", documents.get(2), "Third document should match");
        }
    }

    @Nested
    @DisplayName("Delivery Options Tests")
    class DeliveryOptionsTests {

        @Test
        @DisplayName("DTO should use default values for delivery options when not specified")
        void dtoShouldUseDefaultValuesForDeliveryOptionsWhenNotSpecified() {
            // Given
            WebhookTestRequestDTO dto = new WebhookTestRequestDTO();
            dto.setWebhookId("webhook-123");
            dto.setTestPayload(testPayload);
            
            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertTrue(violations.isEmpty(), "DTO with default delivery options should pass validation");
            assertEquals(false, dto.getAsync(), "Async should default to false");
            assertEquals(true, dto.getRetry(), "Retry should default to true");
            assertEquals(true, dto.getIncludeSignature(), "Include signature should default to true");
        }

        @Test
        @DisplayName("DTO should accept explicit delivery option values")
        void dtoShouldAcceptExplicitDeliveryOptionValues() {
            // Given
            validDto.setAsync(true);
            validDto.setRetry(false);
            validDto.setIncludeSignature(false);
            
            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "DTO with explicit delivery options should pass validation");
            assertEquals(true, validDto.getAsync(), "Async should be set to true");
            assertEquals(false, validDto.getRetry(), "Retry should be set to false");
            assertEquals(false, validDto.getIncludeSignature(), "Include signature should be set to false");
        }

        @Test
        @DisplayName("DTO should handle null delivery option values")
        void dtoShouldHandleNullDeliveryOptionValues() {
            // Given
            validDto.setAsync(null);
            validDto.setRetry(null);
            validDto.setIncludeSignature(null);
            
            // When
            Set<ConstraintViolation<WebhookTestRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "DTO with null delivery options should pass validation");
            assertEquals(false, validDto.getAsync(), "Async should default to false when null");
            assertEquals(true, validDto.getRetry(), "Retry should default to true when null");
            assertEquals(true, validDto.getIncludeSignature(), "Include signature should default to true when null");
        }
    }

    @Nested
    @DisplayName("ToString Tests")
    class ToStringTests {

        @Test
        @DisplayName("toString should include all fields")
        void toStringShouldIncludeAllFields() {
            // When
            String toString = validDto.toString();
            
            // Then
            assertTrue(toString.contains("webhookId='webhook-123'"), 
                    "toString should include webhookId field");
            assertTrue(toString.contains("testPayload="), 
                    "toString should include testPayload field");
            assertTrue(toString.contains("async=false"), 
                    "toString should include async field");
            assertTrue(toString.contains("retry=true"), 
                    "toString should include retry field");
            assertTrue(toString.contains("includeSignature=true"), 
                    "toString should include includeSignature field");
        }

        @Test
        @DisplayName("toString should include test payload content")
        void toStringShouldIncludeTestPayloadContent() {
            // When
            String toString = validDto.toString();
            
            // Then
            assertTrue(toString.contains("applicationId=app-123"), 
                    "toString should include applicationId in testPayload");
            assertTrue(toString.contains("status=APPROVED"), 
                    "toString should include status in testPayload");
            assertTrue(toString.contains("timestamp="), 
                    "toString should include timestamp in testPayload");
        }
    }
}