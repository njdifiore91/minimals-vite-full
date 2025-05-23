package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link WebhookTestResponseDTO}.
 * Tests JSON serialization/deserialization, field validation, builder pattern,
 * and factory methods for webhook test response data.
 */
class WebhookTestResponseDTOTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Nested
    @DisplayName("Builder Pattern Tests")
    class BuilderTests {

        @Test
        @DisplayName("Should build a complete WebhookTestResponseDTO with all fields")
        void shouldBuildCompleteDTO() {
            // Given
            LocalDateTime now = LocalDateTime.now();
            String endpointUrl = "https://example.com/webhook";
            Integer responseCode = 200;
            String responseBody = "{\"status\":\"received\"}";
            Long deliveryTimeMs = 150L;
            Boolean signatureVerified = true;
            String signatureHeader = "X-Webhook-Signature";
            String signatureSent = "sha256=abc123";
            String eventType = "application.created";
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.builder()
                    .success(true)
                    .deliveryTimestamp(now)
                    .responseCode(responseCode)
                    .responseBody(responseBody)
                    .deliveryTimeMs(deliveryTimeMs)
                    .signatureVerified(signatureVerified)
                    .signatureHeader(signatureHeader)
                    .signatureSent(signatureSent)
                    .endpointUrl(endpointUrl)
                    .eventType(eventType)
                    .build();
            
            // Then
            assertTrue(dto.getSuccess());
            assertEquals(now, dto.getDeliveryTimestamp());
            assertEquals(responseCode, dto.getResponseCode());
            assertEquals(responseBody, dto.getResponseBody());
            assertEquals(deliveryTimeMs, dto.getDeliveryTimeMs());
            assertEquals(signatureVerified, dto.getSignatureVerified());
            assertEquals(signatureHeader, dto.getSignatureHeader());
            assertEquals(signatureSent, dto.getSignatureSent());
            assertEquals(endpointUrl, dto.getEndpointUrl());
            assertEquals(eventType, dto.getEventType());
            assertNull(dto.getErrorMessage()); // Not set, should be null
        }

        @Test
        @DisplayName("Should build a minimal WebhookTestResponseDTO with required fields")
        void shouldBuildMinimalDTO() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.builder()
                    .success(false)
                    .endpointUrl(endpointUrl)
                    .build();
            
            // Then
            assertFalse(dto.getSuccess());
            assertEquals(endpointUrl, dto.getEndpointUrl());
            assertNull(dto.getDeliveryTimestamp());
            assertNull(dto.getResponseCode());
            assertNull(dto.getResponseBody());
            assertNull(dto.getDeliveryTimeMs());
            assertNull(dto.getSignatureVerified());
            assertNull(dto.getSignatureHeader());
            assertNull(dto.getSignatureSent());
            assertNull(dto.getEventType());
            assertNull(dto.getErrorMessage());
        }
    }

    @Nested
    @DisplayName("Factory Method Tests")
    class FactoryMethodTests {

        @Test
        @DisplayName("Should create a success response with createSuccessResponse")
        void shouldCreateSuccessResponse() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            Integer responseCode = 200;
            String responseBody = "{\"status\":\"received\"}";
            Long deliveryTimeMs = 150L;
            Boolean signatureVerified = true;
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.createSuccessResponse(
                    endpointUrl, responseCode, responseBody, deliveryTimeMs, signatureVerified);
            
            // Then
            assertTrue(dto.getSuccess());
            assertNotNull(dto.getDeliveryTimestamp()); // Should be set to now
            assertEquals(responseCode, dto.getResponseCode());
            assertEquals(responseBody, dto.getResponseBody());
            assertEquals(deliveryTimeMs, dto.getDeliveryTimeMs());
            assertEquals(signatureVerified, dto.getSignatureVerified());
            assertEquals(endpointUrl, dto.getEndpointUrl());
            assertNull(dto.getErrorMessage()); // Not set for success response
        }

        @Test
        @DisplayName("Should create an error response with createErrorResponse")
        void shouldCreateErrorResponse() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            String errorMessage = "Connection timeout";
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.createErrorResponse(
                    endpointUrl, errorMessage);
            
            // Then
            assertFalse(dto.getSuccess());
            assertNotNull(dto.getDeliveryTimestamp()); // Should be set to now
            assertEquals(endpointUrl, dto.getEndpointUrl());
            assertEquals(errorMessage, dto.getErrorMessage());
            assertNull(dto.getResponseCode()); // Not set for error response
            assertNull(dto.getResponseBody()); // Not set for error response
            assertNull(dto.getDeliveryTimeMs()); // Not set for error response
            assertNull(dto.getSignatureVerified()); // Not set for error response
        }
    }

    @Nested
    @DisplayName("JSON Serialization Tests")
    class JsonSerializationTests {

        @Test
        @DisplayName("Should serialize success response to JSON")
        void shouldSerializeSuccessResponse() throws Exception {
            // Given
            LocalDateTime now = LocalDateTime.of(2023, 5, 15, 10, 30, 0);
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.builder()
                    .success(true)
                    .deliveryTimestamp(now)
                    .responseCode(200)
                    .responseBody("{\"status\":\"received\"}")
                    .deliveryTimeMs(150L)
                    .signatureVerified(true)
                    .signatureHeader("X-Webhook-Signature")
                    .signatureSent("sha256=abc123")
                    .endpointUrl("https://example.com/webhook")
                    .eventType("application.created")
                    .build();
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertTrue(json.contains("\"success\":true"));
            assertTrue(json.contains("\"delivery_timestamp\":\"2023-05-15T10:30:00.000Z\""));
            assertTrue(json.contains("\"response_code\":200"));
            assertTrue(json.contains("\"response_body\":\"{\\\"status\\\":\\\"received\\\"}\""));
            assertTrue(json.contains("\"delivery_time_ms\":150"));
            assertTrue(json.contains("\"signature_verified\":true"));
            assertTrue(json.contains("\"signature_header\":\"X-Webhook-Signature\""));
            assertTrue(json.contains("\"signature_sent\":\"sha256=abc123\""));
            assertTrue(json.contains("\"endpoint_url\":\"https://example.com/webhook\""));
            assertTrue(json.contains("\"event_type\":\"application.created\""));
            assertFalse(json.contains("error_message")); // Should not include null fields
        }

        @Test
        @DisplayName("Should serialize error response to JSON")
        void shouldSerializeErrorResponse() throws Exception {
            // Given
            LocalDateTime now = LocalDateTime.of(2023, 5, 15, 10, 30, 0);
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.builder()
                    .success(false)
                    .deliveryTimestamp(now)
                    .errorMessage("Connection timeout")
                    .endpointUrl("https://example.com/webhook")
                    .build();
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertTrue(json.contains("\"success\":false"));
            assertTrue(json.contains("\"delivery_timestamp\":\"2023-05-15T10:30:00.000Z\""));
            assertTrue(json.contains("\"error_message\":\"Connection timeout\""));
            assertTrue(json.contains("\"endpoint_url\":\"https://example.com/webhook\""));
            assertFalse(json.contains("response_code")); // Should not include null fields
            assertFalse(json.contains("response_body")); // Should not include null fields
            assertFalse(json.contains("delivery_time_ms")); // Should not include null fields
            assertFalse(json.contains("signature_verified")); // Should not include null fields
        }
    }

    @Nested
    @DisplayName("JSON Deserialization Tests")
    class JsonDeserializationTests {

        @Test
        @DisplayName("Should deserialize success response from JSON")
        void shouldDeserializeSuccessResponse() throws Exception {
            // Given
            String json = "{\"success\":true,\"delivery_timestamp\":\"2023-05-15T10:30:00.000Z\",\"response_code\":200,\"response_body\":\"{\\\"status\\\":\\\"received\\\"}\",\"delivery_time_ms\":150,\"signature_verified\":true,\"signature_header\":\"X-Webhook-Signature\",\"signature_sent\":\"sha256=abc123\",\"endpoint_url\":\"https://example.com/webhook\",\"event_type\":\"application.created\"}";
            
            // When
            WebhookTestResponseDTO dto = objectMapper.readValue(json, WebhookTestResponseDTO.class);
            
            // Then
            assertTrue(dto.getSuccess());
            assertEquals(LocalDateTime.of(2023, 5, 15, 10, 30, 0), dto.getDeliveryTimestamp());
            assertEquals(200, dto.getResponseCode());
            assertEquals("{\"status\":\"received\"}", dto.getResponseBody());
            assertEquals(150L, dto.getDeliveryTimeMs());
            assertTrue(dto.getSignatureVerified());
            assertEquals("X-Webhook-Signature", dto.getSignatureHeader());
            assertEquals("sha256=abc123", dto.getSignatureSent());
            assertEquals("https://example.com/webhook", dto.getEndpointUrl());
            assertEquals("application.created", dto.getEventType());
            assertNull(dto.getErrorMessage());
        }

        @Test
        @DisplayName("Should deserialize error response from JSON")
        void shouldDeserializeErrorResponse() throws Exception {
            // Given
            String json = "{\"success\":false,\"delivery_timestamp\":\"2023-05-15T10:30:00.000Z\",\"error_message\":\"Connection timeout\",\"endpoint_url\":\"https://example.com/webhook\"}";
            
            // When
            WebhookTestResponseDTO dto = objectMapper.readValue(json, WebhookTestResponseDTO.class);
            
            // Then
            assertFalse(dto.getSuccess());
            assertEquals(LocalDateTime.of(2023, 5, 15, 10, 30, 0), dto.getDeliveryTimestamp());
            assertEquals("Connection timeout", dto.getErrorMessage());
            assertEquals("https://example.com/webhook", dto.getEndpointUrl());
            assertNull(dto.getResponseCode());
            assertNull(dto.getResponseBody());
            assertNull(dto.getDeliveryTimeMs());
            assertNull(dto.getSignatureVerified());
            assertNull(dto.getSignatureHeader());
            assertNull(dto.getSignatureSent());
            assertNull(dto.getEventType());
        }

        @Test
        @DisplayName("Should deserialize partial response from JSON")
        void shouldDeserializePartialResponse() throws Exception {
            // Given
            String json = "{\"success\":true,\"endpoint_url\":\"https://example.com/webhook\"}";
            
            // When
            WebhookTestResponseDTO dto = objectMapper.readValue(json, WebhookTestResponseDTO.class);
            
            // Then
            assertTrue(dto.getSuccess());
            assertEquals("https://example.com/webhook", dto.getEndpointUrl());
            assertNull(dto.getDeliveryTimestamp());
            assertNull(dto.getResponseCode());
            assertNull(dto.getResponseBody());
            assertNull(dto.getDeliveryTimeMs());
            assertNull(dto.getSignatureVerified());
            assertNull(dto.getSignatureHeader());
            assertNull(dto.getSignatureSent());
            assertNull(dto.getEventType());
            assertNull(dto.getErrorMessage());
        }
    }

    @Nested
    @DisplayName("Delivery Status Scenario Tests")
    class DeliveryStatusScenarioTests {

        @Test
        @DisplayName("Should handle successful delivery with verified signature")
        void shouldHandleSuccessfulDeliveryWithVerifiedSignature() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            Integer responseCode = 200;
            String responseBody = "{\"status\":\"received\"}";
            Long deliveryTimeMs = 150L;
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.createSuccessResponse(
                    endpointUrl, responseCode, responseBody, deliveryTimeMs, true);
            
            // Then
            assertTrue(dto.getSuccess());
            assertEquals(responseCode, dto.getResponseCode());
            assertEquals(responseBody, dto.getResponseBody());
            assertEquals(deliveryTimeMs, dto.getDeliveryTimeMs());
            assertTrue(dto.getSignatureVerified());
            assertEquals(endpointUrl, dto.getEndpointUrl());
        }

        @Test
        @DisplayName("Should handle successful delivery with unverified signature")
        void shouldHandleSuccessfulDeliveryWithUnverifiedSignature() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            Integer responseCode = 200;
            String responseBody = "{\"status\":\"received\"}";
            Long deliveryTimeMs = 150L;
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.createSuccessResponse(
                    endpointUrl, responseCode, responseBody, deliveryTimeMs, false);
            
            // Then
            assertTrue(dto.getSuccess());
            assertEquals(responseCode, dto.getResponseCode());
            assertEquals(responseBody, dto.getResponseBody());
            assertEquals(deliveryTimeMs, dto.getDeliveryTimeMs());
            assertFalse(dto.getSignatureVerified());
            assertEquals(endpointUrl, dto.getEndpointUrl());
        }

        @Test
        @DisplayName("Should handle non-200 response as successful delivery")
        void shouldHandleNon200ResponseAsSuccessfulDelivery() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            Integer responseCode = 422;
            String responseBody = "{\"error\":\"Invalid payload\"}";
            Long deliveryTimeMs = 150L;
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.createSuccessResponse(
                    endpointUrl, responseCode, responseBody, deliveryTimeMs, true);
            
            // Then
            assertTrue(dto.getSuccess());
            assertEquals(responseCode, dto.getResponseCode());
            assertEquals(responseBody, dto.getResponseBody());
            assertEquals(deliveryTimeMs, dto.getDeliveryTimeMs());
            assertTrue(dto.getSignatureVerified());
            assertEquals(endpointUrl, dto.getEndpointUrl());
        }

        @Test
        @DisplayName("Should handle connection error")
        void shouldHandleConnectionError() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            String errorMessage = "Connection refused";
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.createErrorResponse(
                    endpointUrl, errorMessage);
            
            // Then
            assertFalse(dto.getSuccess());
            assertEquals(errorMessage, dto.getErrorMessage());
            assertEquals(endpointUrl, dto.getEndpointUrl());
            assertNull(dto.getResponseCode());
            assertNull(dto.getResponseBody());
        }

        @Test
        @DisplayName("Should handle timeout error")
        void shouldHandleTimeoutError() {
            // Given
            String endpointUrl = "https://example.com/webhook";
            String errorMessage = "Connection timed out after 5000ms";
            
            // When
            WebhookTestResponseDTO dto = WebhookTestResponseDTO.createErrorResponse(
                    endpointUrl, errorMessage);
            
            // Then
            assertFalse(dto.getSuccess());
            assertEquals(errorMessage, dto.getErrorMessage());
            assertEquals(endpointUrl, dto.getEndpointUrl());
            assertNull(dto.getResponseCode());
            assertNull(dto.getResponseBody());
        }
    }

    @Nested
    @DisplayName("Getter and Setter Tests")
    class GetterSetterTests {

        @Test
        @DisplayName("Should set and get all fields correctly")
        void shouldSetAndGetAllFieldsCorrectly() {
            // Given
            WebhookTestResponseDTO dto = new WebhookTestResponseDTO();
            LocalDateTime now = LocalDateTime.now();
            
            // When
            dto.setSuccess(true);
            dto.setDeliveryTimestamp(now);
            dto.setResponseCode(200);
            dto.setResponseBody("{\"status\":\"received\"}");
            dto.setErrorMessage(null);
            dto.setSignatureVerified(true);
            dto.setSignatureHeader("X-Webhook-Signature");
            dto.setSignatureSent("sha256=abc123");
            dto.setDeliveryTimeMs(150L);
            dto.setEndpointUrl("https://example.com/webhook");
            dto.setEventType("application.created");
            
            // Then
            assertTrue(dto.getSuccess());
            assertEquals(now, dto.getDeliveryTimestamp());
            assertEquals(200, dto.getResponseCode());
            assertEquals("{\"status\":\"received\"}", dto.getResponseBody());
            assertNull(dto.getErrorMessage());
            assertTrue(dto.getSignatureVerified());
            assertEquals("X-Webhook-Signature", dto.getSignatureHeader());
            assertEquals("sha256=abc123", dto.getSignatureSent());
            assertEquals(150L, dto.getDeliveryTimeMs());
            assertEquals("https://example.com/webhook", dto.getEndpointUrl());
            assertEquals("application.created", dto.getEventType());
        }
    }

    @Test
    @DisplayName("Should generate proper toString output")
    void shouldGenerateProperToStringOutput() {
        // Given
        LocalDateTime now = LocalDateTime.now();
        WebhookTestResponseDTO dto = WebhookTestResponseDTO.builder()
                .success(true)
                .deliveryTimestamp(now)
                .responseCode(200)
                .responseBody("{\"status\":\"received\"}")
                .deliveryTimeMs(150L)
                .signatureVerified(true)
                .signatureHeader("X-Webhook-Signature")
                .signatureSent("sha256=abc123")
                .endpointUrl("https://example.com/webhook")
                .eventType("application.created")
                .build();
        
        // When
        String toStringResult = dto.toString();
        
        // Then
        assertTrue(toStringResult.contains("success=true"));
        assertTrue(toStringResult.contains("deliveryTimestamp=" + now));
        assertTrue(toStringResult.contains("responseCode=200"));
        assertTrue(toStringResult.contains("responseBody='{\"status\":\"received\"}'")); 
        assertTrue(toStringResult.contains("deliveryTimeMs=150"));
        assertTrue(toStringResult.contains("signatureVerified=true"));
        assertTrue(toStringResult.contains("signatureHeader='X-Webhook-Signature'"));
        assertTrue(toStringResult.contains("signatureSent='sha256=abc123'"));
        assertTrue(toStringResult.contains("endpointUrl='https://example.com/webhook'"));
        assertTrue(toStringResult.contains("eventType='application.created'"));
    }

    @Test
    @DisplayName("Should create DTO with all-args constructor")
    void shouldCreateDTOWithAllArgsConstructor() {
        // Given
        LocalDateTime now = LocalDateTime.now();
        Boolean success = true;
        Integer responseCode = 200;
        String responseBody = "{\"status\":\"received\"}";
        String errorMessage = null;
        Boolean signatureVerified = true;
        String signatureHeader = "X-Webhook-Signature";
        String signatureSent = "sha256=abc123";
        Long deliveryTimeMs = 150L;
        String endpointUrl = "https://example.com/webhook";
        String eventType = "application.created";
        
        // When
        WebhookTestResponseDTO dto = new WebhookTestResponseDTO(
                success, now, responseCode, responseBody, errorMessage,
                signatureVerified, signatureHeader, signatureSent, deliveryTimeMs,
                endpointUrl, eventType);
        
        // Then
        assertEquals(success, dto.getSuccess());
        assertEquals(now, dto.getDeliveryTimestamp());
        assertEquals(responseCode, dto.getResponseCode());
        assertEquals(responseBody, dto.getResponseBody());
        assertEquals(errorMessage, dto.getErrorMessage());
        assertEquals(signatureVerified, dto.getSignatureVerified());
        assertEquals(signatureHeader, dto.getSignatureHeader());
        assertEquals(signatureSent, dto.getSignatureSent());
        assertEquals(deliveryTimeMs, dto.getDeliveryTimeMs());
        assertEquals(endpointUrl, dto.getEndpointUrl());
        assertEquals(eventType, dto.getEventType());
    }
}