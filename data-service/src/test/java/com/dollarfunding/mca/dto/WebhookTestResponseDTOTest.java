package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link WebhookTestResponseDTO}.
 * Validates the webhook test result structure, JSON serialization/deserialization, and field validation.
 * Tests delivery status handling, response details formatting, and error information inclusion.
 */
class WebhookTestResponseDTOTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final LocalDateTime testTimestamp = LocalDateTime.of(2023, 5, 15, 10, 30, 0);

    @Test
    @DisplayName("Should create a successful webhook test response with all fields")
    void shouldCreateSuccessfulWebhookTestResponse() {
        // Given
        Integer responseCode = 200;
        String responseBody = "{\"status\":\"received\"}";
        Long deliveryTimeMs = 150L;
        Boolean signatureVerified = true;
        String generatedSignature = "hmac-sha256=abc123def456";
        String signatureHeader = "X-Webhook-Signature";

        // When
        WebhookTestResponseDTO response = WebhookTestResponseDTO.success(
                responseCode, responseBody, deliveryTimeMs, signatureVerified, generatedSignature, signatureHeader);

        // Then
        assertTrue(response.isSuccess());
        assertNotNull(response.getDeliveryTimestamp());
        assertEquals(responseCode, response.getResponseCode());
        assertEquals(responseBody, response.getResponseBody());
        assertEquals(deliveryTimeMs, response.getDeliveryTimeMs());
        assertEquals(signatureVerified, response.getSignatureVerified());
        assertEquals(generatedSignature, response.getGeneratedSignature());
        assertEquals(signatureHeader, response.getSignatureHeader());
        assertNull(response.getErrorMessage());
        assertNull(response.getErrorDetails());
    }

    @Test
    @DisplayName("Should create a failed webhook test response with error information")
    void shouldCreateFailedWebhookTestResponse() {
        // Given
        String errorMessage = "Connection timeout";
        String errorDetails = "Failed to connect to endpoint after 5000ms";
        Boolean signatureVerified = false;
        String generatedSignature = "hmac-sha256=abc123def456";
        String signatureHeader = "X-Webhook-Signature";

        // When
        WebhookTestResponseDTO response = WebhookTestResponseDTO.failure(
                errorMessage, errorDetails, signatureVerified, generatedSignature, signatureHeader);

        // Then
        assertFalse(response.isSuccess());
        assertNotNull(response.getDeliveryTimestamp());
        assertNull(response.getResponseCode());
        assertNull(response.getResponseBody());
        assertNull(response.getDeliveryTimeMs());
        assertEquals(errorMessage, response.getErrorMessage());
        assertEquals(errorDetails, response.getErrorDetails());
        assertEquals(signatureVerified, response.getSignatureVerified());
        assertEquals(generatedSignature, response.getGeneratedSignature());
        assertEquals(signatureHeader, response.getSignatureHeader());
    }

    @Test
    @DisplayName("Should create a webhook test response using the builder pattern")
    void shouldCreateWebhookTestResponseUsingBuilder() {
        // Given
        boolean success = true;
        Integer responseCode = 201;
        String responseBody = "{\"status\":\"processed\"}";
        Long deliveryTimeMs = 120L;
        Boolean signatureVerified = true;
        String generatedSignature = "hmac-sha256=xyz789abc";
        String signatureHeader = "X-Webhook-Signature";

        // When
        WebhookTestResponseDTO response = WebhookTestResponseDTO.builder()
                .success(success)
                .deliveryTimestamp(testTimestamp)
                .responseCode(responseCode)
                .responseBody(responseBody)
                .deliveryTimeMs(deliveryTimeMs)
                .signatureVerified(signatureVerified)
                .generatedSignature(generatedSignature)
                .signatureHeader(signatureHeader)
                .build();

        // Then
        assertEquals(success, response.isSuccess());
        assertEquals(testTimestamp, response.getDeliveryTimestamp());
        assertEquals(responseCode, response.getResponseCode());
        assertEquals(responseBody, response.getResponseBody());
        assertEquals(deliveryTimeMs, response.getDeliveryTimeMs());
        assertEquals(signatureVerified, response.getSignatureVerified());
        assertEquals(generatedSignature, response.getGeneratedSignature());
        assertEquals(signatureHeader, response.getSignatureHeader());
    }

    @Test
    @DisplayName("Should create a failed webhook test response using the builder pattern")
    void shouldCreateFailedWebhookTestResponseUsingBuilder() {
        // Given
        boolean success = false;
        String errorMessage = "Invalid response format";
        String errorDetails = "Expected JSON but received plain text";
        Boolean signatureVerified = true;
        String generatedSignature = "hmac-sha256=def456ghi789";
        String signatureHeader = "X-Webhook-Signature";

        // When
        WebhookTestResponseDTO response = WebhookTestResponseDTO.builder()
                .success(success)
                .deliveryTimestamp(testTimestamp)
                .errorMessage(errorMessage)
                .errorDetails(errorDetails)
                .signatureVerified(signatureVerified)
                .generatedSignature(generatedSignature)
                .signatureHeader(signatureHeader)
                .build();

        // Then
        assertEquals(success, response.isSuccess());
        assertEquals(testTimestamp, response.getDeliveryTimestamp());
        assertNull(response.getResponseCode());
        assertNull(response.getResponseBody());
        assertNull(response.getDeliveryTimeMs());
        assertEquals(errorMessage, response.getErrorMessage());
        assertEquals(errorDetails, response.getErrorDetails());
        assertEquals(signatureVerified, response.getSignatureVerified());
        assertEquals(generatedSignature, response.getGeneratedSignature());
        assertEquals(signatureHeader, response.getSignatureHeader());
    }

    @Test
    @DisplayName("Should serialize and deserialize webhook test response to/from JSON")
    void shouldSerializeAndDeserializeWebhookTestResponse() throws Exception {
        // Given
        WebhookTestResponseDTO response = WebhookTestResponseDTO.builder()
                .success(true)
                .deliveryTimestamp(testTimestamp)
                .responseCode(200)
                .responseBody("{\"status\":\"received\"}")
                .deliveryTimeMs(150L)
                .signatureVerified(true)
                .generatedSignature("hmac-sha256=abc123def456")
                .signatureHeader("X-Webhook-Signature")
                .build();

        // Configure ObjectMapper for LocalDateTime serialization
        objectMapper.findAndRegisterModules();

        // When
        String json = objectMapper.writeValueAsString(response);
        WebhookTestResponseDTO deserialized = objectMapper.readValue(json, WebhookTestResponseDTO.class);

        // Then
        assertEquals(response.isSuccess(), deserialized.isSuccess());
        assertEquals(response.getResponseCode(), deserialized.getResponseCode());
        assertEquals(response.getResponseBody(), deserialized.getResponseBody());
        assertEquals(response.getDeliveryTimeMs(), deserialized.getDeliveryTimeMs());
        assertEquals(response.getSignatureVerified(), deserialized.getSignatureVerified());
        assertEquals(response.getGeneratedSignature(), deserialized.getGeneratedSignature());
        assertEquals(response.getSignatureHeader(), deserialized.getSignatureHeader());
    }

    @Test
    @DisplayName("Should serialize and deserialize failed webhook test response to/from JSON")
    void shouldSerializeAndDeserializeFailedWebhookTestResponse() throws Exception {
        // Given
        WebhookTestResponseDTO response = WebhookTestResponseDTO.builder()
                .success(false)
                .deliveryTimestamp(testTimestamp)
                .errorMessage("Connection refused")
                .errorDetails("Target server refused connection on port 443")
                .signatureVerified(false)
                .generatedSignature("hmac-sha256=abc123def456")
                .signatureHeader("X-Webhook-Signature")
                .build();

        // Configure ObjectMapper for LocalDateTime serialization
        objectMapper.findAndRegisterModules();

        // When
        String json = objectMapper.writeValueAsString(response);
        WebhookTestResponseDTO deserialized = objectMapper.readValue(json, WebhookTestResponseDTO.class);

        // Then
        assertEquals(response.isSuccess(), deserialized.isSuccess());
        assertEquals(response.getErrorMessage(), deserialized.getErrorMessage());
        assertEquals(response.getErrorDetails(), deserialized.getErrorDetails());
        assertEquals(response.getSignatureVerified(), deserialized.getSignatureVerified());
        assertEquals(response.getGeneratedSignature(), deserialized.getGeneratedSignature());
        assertEquals(response.getSignatureHeader(), deserialized.getSignatureHeader());
    }

    @Test
    @DisplayName("Should test JSON field names match expected properties")
    void shouldTestJsonFieldNamesMatchExpectedProperties() throws Exception {
        // Given
        WebhookTestResponseDTO response = WebhookTestResponseDTO.builder()
                .success(true)
                .deliveryTimestamp(testTimestamp)
                .responseCode(200)
                .responseBody("{\"status\":\"received\"}")
                .deliveryTimeMs(150L)
                .signatureVerified(true)
                .generatedSignature("hmac-sha256=abc123def456")
                .signatureHeader("X-Webhook-Signature")
                .build();

        // Configure ObjectMapper for LocalDateTime serialization
        objectMapper.findAndRegisterModules();

        // When
        String json = objectMapper.writeValueAsString(response);

        // Then
        assertTrue(json.contains("\"success\":true"));
        assertTrue(json.contains("\"delivery_timestamp\":"));
        assertTrue(json.contains("\"response_code\":200"));
        assertTrue(json.contains("\"response_body\":\"{\\\"status\\\":\\\"received\\\"}\""));
        assertTrue(json.contains("\"delivery_time_ms\":150"));
        assertTrue(json.contains("\"signature_verified\":true"));
        assertTrue(json.contains("\"generated_signature\":\"hmac-sha256=abc123def456\""));
        assertTrue(json.contains("\"signature_header\":\"X-Webhook-Signature\""));
    }

    @Test
    @DisplayName("Should test constructors for successful webhook test response")
    void shouldTestConstructorsForSuccessfulWebhookTestResponse() {
        // Given
        LocalDateTime deliveryTimestamp = testTimestamp;
        Integer responseCode = 200;
        String responseBody = "{\"status\":\"received\"}";
        Long deliveryTimeMs = 150L;
        Boolean signatureVerified = true;
        String generatedSignature = "hmac-sha256=abc123def456";
        String signatureHeader = "X-Webhook-Signature";

        // When
        WebhookTestResponseDTO response = new WebhookTestResponseDTO(
                deliveryTimestamp, responseCode, responseBody, deliveryTimeMs, 
                signatureVerified, generatedSignature, signatureHeader);

        // Then
        assertTrue(response.isSuccess());
        assertEquals(deliveryTimestamp, response.getDeliveryTimestamp());
        assertEquals(responseCode, response.getResponseCode());
        assertEquals(responseBody, response.getResponseBody());
        assertEquals(deliveryTimeMs, response.getDeliveryTimeMs());
        assertEquals(signatureVerified, response.getSignatureVerified());
        assertEquals(generatedSignature, response.getGeneratedSignature());
        assertEquals(signatureHeader, response.getSignatureHeader());
    }

    @Test
    @DisplayName("Should test constructors for failed webhook test response")
    void shouldTestConstructorsForFailedWebhookTestResponse() {
        // Given
        String errorMessage = "Connection timeout";
        String errorDetails = "Failed to connect to endpoint after 5000ms";
        Boolean signatureVerified = false;
        String generatedSignature = "hmac-sha256=abc123def456";
        String signatureHeader = "X-Webhook-Signature";

        // When
        WebhookTestResponseDTO response = new WebhookTestResponseDTO(
                errorMessage, errorDetails, signatureVerified, generatedSignature, signatureHeader);

        // Then
        assertFalse(response.isSuccess());
        assertNotNull(response.getDeliveryTimestamp());
        assertNull(response.getResponseCode());
        assertNull(response.getResponseBody());
        assertNull(response.getDeliveryTimeMs());
        assertEquals(errorMessage, response.getErrorMessage());
        assertEquals(errorDetails, response.getErrorDetails());
        assertEquals(signatureVerified, response.getSignatureVerified());
        assertEquals(generatedSignature, response.getGeneratedSignature());
        assertEquals(signatureHeader, response.getSignatureHeader());
    }

    @Test
    @DisplayName("Should test default constructor and setters")
    void shouldTestDefaultConstructorAndSetters() {
        // Given
        WebhookTestResponseDTO response = new WebhookTestResponseDTO();

        // When
        response.setSuccess(true);
        response.setDeliveryTimestamp(testTimestamp);
        response.setResponseCode(202);
        response.setResponseBody("{\"status\":\"accepted\"}")
        response.setDeliveryTimeMs(180L);
        response.setSignatureVerified(true);
        response.setGeneratedSignature("hmac-sha256=ghi789jkl012");
        response.setSignatureHeader("X-Webhook-Signature");

        // Then
        assertTrue(response.isSuccess());
        assertEquals(testTimestamp, response.getDeliveryTimestamp());
        assertEquals(202, response.getResponseCode());
        assertEquals("{\"status\":\"accepted\"}", response.getResponseBody());
        assertEquals(180L, response.getDeliveryTimeMs());
        assertTrue(response.getSignatureVerified());
        assertEquals("hmac-sha256=ghi789jkl012", response.getGeneratedSignature());
        assertEquals("X-Webhook-Signature", response.getSignatureHeader());
    }

    @Test
    @DisplayName("Should test error information setters")
    void shouldTestErrorInformationSetters() {
        // Given
        WebhookTestResponseDTO response = new WebhookTestResponseDTO();

        // When
        response.setSuccess(false);
        response.setErrorMessage("Invalid webhook URL");
        response.setErrorDetails("URL format is invalid or contains unsupported protocol");

        // Then
        assertFalse(response.isSuccess());
        assertEquals("Invalid webhook URL", response.getErrorMessage());
        assertEquals("URL format is invalid or contains unsupported protocol", response.getErrorDetails());
    }

    @Test
    @DisplayName("Should test different HTTP response codes")
    void shouldTestDifferentHttpResponseCodes() {
        // Given
        Integer[] responseCodes = {200, 201, 202, 204, 400, 401, 403, 404, 500, 502, 503};
        
        for (Integer responseCode : responseCodes) {
            // When
            WebhookTestResponseDTO response = WebhookTestResponseDTO.builder()
                    .success(responseCode < 400) // Success for 2xx codes
                    .responseCode(responseCode)
                    .build();
            
            // Then
            assertEquals(responseCode < 400, response.isSuccess());
            assertEquals(responseCode, response.getResponseCode());
        }
    }

    @Test
    @DisplayName("Should test different signature verification scenarios")
    void shouldTestDifferentSignatureVerificationScenarios() {
        // Scenario 1: Signature verified successfully
        WebhookTestResponseDTO response1 = WebhookTestResponseDTO.builder()
                .success(true)
                .responseCode(200)
                .signatureVerified(true)
                .generatedSignature("hmac-sha256=abc123def456")
                .signatureHeader("X-Webhook-Signature")
                .build();
        
        assertTrue(response1.isSuccess());
        assertTrue(response1.getSignatureVerified());
        
        // Scenario 2: Signature verification failed but delivery succeeded
        WebhookTestResponseDTO response2 = WebhookTestResponseDTO.builder()
                .success(true)
                .responseCode(200)
                .signatureVerified(false)
                .generatedSignature("hmac-sha256=abc123def456")
                .signatureHeader("X-Webhook-Signature")
                .build();
        
        assertTrue(response2.isSuccess());
        assertFalse(response2.getSignatureVerified());
        
        // Scenario 3: Signature verification succeeded but delivery failed
        WebhookTestResponseDTO response3 = WebhookTestResponseDTO.builder()
                .success(false)
                .errorMessage("Connection timeout")
                .signatureVerified(true)
                .generatedSignature("hmac-sha256=abc123def456")
                .signatureHeader("X-Webhook-Signature")
                .build();
        
        assertFalse(response3.isSuccess());
        assertTrue(response3.getSignatureVerified());
    }
}