package com.dollarfunding.mca.dto;

import static org.junit.jupiter.api.Assertions.*;

import java.time.LocalDateTime;

import org.junit.jupiter.api.Test;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

/**
 * Test class for {@link WebhookResponseDTO}.
 * 
 * This class tests the webhook response DTO functionality including:
 * - Validation of webhook configuration structure
 * - JSON serialization/deserialization
 * - Entity conversion
 * - Field masking for sensitive data
 * - Delivery status information
 */
public class WebhookResponseDTOTest {

    private final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    /**
     * Tests the creation of a WebhookResponseDTO using the builder pattern.
     */
    @Test
    public void testWebhookResponseDTOBuilder() {
        // Given
        Long id = 1L;
        String endpointUrl = "https://example.com/webhook";
        String eventType = EventType.APPLICATION_CREATED.name();
        boolean active = true;
        String secretKeyMasked = "abcd****";
        LocalDateTime createdAt = LocalDateTime.now().minusDays(1);
        LocalDateTime updatedAt = LocalDateTime.now();
        LocalDateTime lastDeliveryAt = LocalDateTime.now().minusHours(1);
        Boolean lastDeliverySuccess = true;
        Integer lastDeliveryStatusCode = 200;
        String lastDeliveryError = null;
        Long successfulDeliveriesCount = 10L;
        Long failedDeliveriesCount = 2L;
        String signatureHeader = "X-Webhook-Signature";

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.builder()
                .id(id)
                .endpointUrl(endpointUrl)
                .eventType(eventType)
                .active(active)
                .secretKeyMasked(secretKeyMasked)
                .createdAt(createdAt)
                .updatedAt(updatedAt)
                .lastDeliveryAt(lastDeliveryAt)
                .lastDeliverySuccess(lastDeliverySuccess)
                .lastDeliveryStatusCode(lastDeliveryStatusCode)
                .lastDeliveryError(lastDeliveryError)
                .successfulDeliveriesCount(successfulDeliveriesCount)
                .failedDeliveriesCount(failedDeliveriesCount)
                .signatureHeader(signatureHeader)
                .build();

        // Then
        assertEquals(id, dto.getId());
        assertEquals(endpointUrl, dto.getEndpointUrl());
        assertEquals(eventType, dto.getEventType());
        assertEquals(active, dto.isActive());
        assertEquals(secretKeyMasked, dto.getSecretKeyMasked());
        assertEquals(createdAt, dto.getCreatedAt());
        assertEquals(updatedAt, dto.getUpdatedAt());
        assertEquals(lastDeliveryAt, dto.getLastDeliveryAt());
        assertEquals(lastDeliverySuccess, dto.getLastDeliverySuccess());
        assertEquals(lastDeliveryStatusCode, dto.getLastDeliveryStatusCode());
        assertEquals(lastDeliveryError, dto.getLastDeliveryError());
        assertEquals(successfulDeliveriesCount, dto.getSuccessfulDeliveriesCount());
        assertEquals(failedDeliveriesCount, dto.getFailedDeliveriesCount());
        assertEquals(signatureHeader, dto.getSignatureHeader());
    }

    /**
     * Tests the conversion from a Webhook entity to a WebhookResponseDTO.
     */
    @Test
    public void testFromEntity() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setId(1L);
        webhook.setEndpointUrl("https://example.com/webhook");
        webhook.setEventType(EventType.APPLICATION_CREATED);
        webhook.setActive(true);
        webhook.setSecretKey("abcdefghijklmnopqrstuvwxyz123456"); // 32 characters
        
        LocalDateTime createdAt = LocalDateTime.now().minusDays(1);
        LocalDateTime updatedAt = LocalDateTime.now();
        
        // Use reflection to set the createdAt and updatedAt fields
        try {
            java.lang.reflect.Field createdAtField = Webhook.class.getDeclaredField("createdAt");
            createdAtField.setAccessible(true);
            createdAtField.set(webhook, createdAt);
            
            java.lang.reflect.Field updatedAtField = Webhook.class.getDeclaredField("updatedAt");
            updatedAtField.setAccessible(true);
            updatedAtField.set(webhook, updatedAt);
        } catch (Exception e) {
            fail("Failed to set createdAt and updatedAt fields: " + e.getMessage());
        }
        
        webhook.setLastDeliverySuccess(true);
        webhook.setLastDeliveryStatusCode(200);
        webhook.setLastDeliveryError(null);
        webhook.setSuccessfulDeliveriesCount(10L);
        webhook.setFailedDeliveriesCount(2L);
        webhook.setSignatureHeader("X-Webhook-Signature");
        
        // Set the last delivery attempt
        LocalDateTime lastDeliveryAttempt = LocalDateTime.now().minusHours(1);
        webhook.setLastDeliveryAttempt(lastDeliveryAttempt);

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertEquals(webhook.getId(), dto.getId());
        assertEquals(webhook.getEndpointUrl(), dto.getEndpointUrl());
        assertEquals(webhook.getEventType().name(), dto.getEventType());
        assertEquals(webhook.isActive(), dto.isActive());
        
        // Check that the secret key is masked
        assertNotNull(dto.getSecretKeyMasked());
        assertTrue(dto.getSecretKeyMasked().startsWith("abcd"));
        assertTrue(dto.getSecretKeyMasked().endsWith("****"));
        
        assertEquals(createdAt, dto.getCreatedAt());
        assertEquals(updatedAt, dto.getUpdatedAt());
        assertEquals(lastDeliveryAttempt, dto.getLastDeliveryAt());
        assertEquals(webhook.getLastDeliverySuccess(), dto.getLastDeliverySuccess());
        assertEquals(webhook.getLastDeliveryStatusCode(), dto.getLastDeliveryStatusCode());
        assertEquals(webhook.getLastDeliveryError(), dto.getLastDeliveryError());
        assertEquals(webhook.getSuccessfulDeliveriesCount(), dto.getSuccessfulDeliveriesCount());
        assertEquals(webhook.getFailedDeliveriesCount(), dto.getFailedDeliveriesCount());
        assertEquals(webhook.getSignatureHeader(), dto.getSignatureHeader());
    }

    /**
     * Tests the conversion from a null Webhook entity to a null WebhookResponseDTO.
     */
    @Test
    public void testFromEntityWithNull() {
        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(null);

        // Then
        assertNull(dto);
    }

    /**
     * Tests the conversion from a list of Webhook entities to a list of WebhookResponseDTOs.
     */
    @Test
    public void testFromEntities() {
        // Given
        Webhook webhook1 = new Webhook();
        webhook1.setId(1L);
        webhook1.setEndpointUrl("https://example.com/webhook1");
        webhook1.setEventType(EventType.APPLICATION_CREATED);
        webhook1.setActive(true);
        webhook1.setSecretKey("abcdefghijklmnopqrstuvwxyz123456");

        Webhook webhook2 = new Webhook();
        webhook2.setId(2L);
        webhook2.setEndpointUrl("https://example.com/webhook2");
        webhook2.setEventType(EventType.DOCUMENT_UPLOADED);
        webhook2.setActive(false);
        webhook2.setSecretKey("zyxwvutsrqponmlkjihgfedcba654321");

        java.util.List<Webhook> webhooks = java.util.Arrays.asList(webhook1, webhook2);

        // When
        java.util.List<WebhookResponseDTO> dtos = WebhookResponseDTO.fromEntities(webhooks);

        // Then
        assertEquals(2, dtos.size());
        assertEquals(webhook1.getId(), dtos.get(0).getId());
        assertEquals(webhook1.getEndpointUrl(), dtos.get(0).getEndpointUrl());
        assertEquals(webhook1.getEventType().name(), dtos.get(0).getEventType());
        assertEquals(webhook1.isActive(), dtos.get(0).isActive());

        assertEquals(webhook2.getId(), dtos.get(1).getId());
        assertEquals(webhook2.getEndpointUrl(), dtos.get(1).getEndpointUrl());
        assertEquals(webhook2.getEventType().name(), dtos.get(1).getEventType());
        assertEquals(webhook2.isActive(), dtos.get(1).isActive());
    }

    /**
     * Tests the conversion from a null list of Webhook entities to an empty list of WebhookResponseDTOs.
     */
    @Test
    public void testFromEntitiesWithNull() {
        // When
        java.util.List<WebhookResponseDTO> dtos = WebhookResponseDTO.fromEntities(null);

        // Then
        assertNotNull(dtos);
        assertTrue(dtos.isEmpty());
    }

    /**
     * Tests the JSON serialization of a WebhookResponseDTO.
     */
    @Test
    public void testJsonSerialization() throws Exception {
        // Given
        WebhookResponseDTO dto = WebhookResponseDTO.builder()
                .id(1L)
                .endpointUrl("https://example.com/webhook")
                .eventType(EventType.APPLICATION_CREATED.name())
                .active(true)
                .secretKeyMasked("abcd****")
                .createdAt(LocalDateTime.of(2023, 1, 1, 12, 0))
                .updatedAt(LocalDateTime.of(2023, 1, 2, 12, 0))
                .lastDeliveryAt(LocalDateTime.of(2023, 1, 2, 10, 0))
                .lastDeliverySuccess(true)
                .lastDeliveryStatusCode(200)
                .successfulDeliveriesCount(10L)
                .failedDeliveriesCount(2L)
                .signatureHeader("X-Webhook-Signature")
                .build();

        // When
        String json = objectMapper.writeValueAsString(dto);

        // Then
        assertTrue(json.contains("\"id\":1"));
        assertTrue(json.contains("\"endpoint_url\":\"https://example.com/webhook\""));
        assertTrue(json.contains("\"event_type\":\"APPLICATION_CREATED\""));
        assertTrue(json.contains("\"active\":true"));
        assertTrue(json.contains("\"secret_key_masked\":\"abcd****\""));
        assertTrue(json.contains("\"created_at\":\"2023-01-01T12:00:00.000Z\""));
        assertTrue(json.contains("\"updated_at\":\"2023-01-02T12:00:00.000Z\""));
        assertTrue(json.contains("\"last_delivery_at\":\"2023-01-02T10:00:00.000Z\""));
        assertTrue(json.contains("\"last_delivery_success\":true"));
        assertTrue(json.contains("\"last_delivery_status_code\":200"));
        assertTrue(json.contains("\"successful_deliveries_count\":10"));
        assertTrue(json.contains("\"failed_deliveries_count\":2"));
        assertTrue(json.contains("\"signature_header\":\"X-Webhook-Signature\""));
    }

    /**
     * Tests the JSON deserialization of a WebhookResponseDTO.
     */
    @Test
    public void testJsonDeserialization() throws Exception {
        // Given
        String json = "{\"id\":1,\"endpoint_url\":\"https://example.com/webhook\",\"event_type\":\"APPLICATION_CREATED\",\"active\":true,\"secret_key_masked\":\"abcd****\",\"created_at\":\"2023-01-01T12:00:00.000Z\",\"updated_at\":\"2023-01-02T12:00:00.000Z\",\"last_delivery_at\":\"2023-01-02T10:00:00.000Z\",\"last_delivery_success\":true,\"last_delivery_status_code\":200,\"successful_deliveries_count\":10,\"failed_deliveries_count\":2,\"signature_header\":\"X-Webhook-Signature\"}";

        // When
        WebhookResponseDTO dto = objectMapper.readValue(json, WebhookResponseDTO.class);

        // Then
        assertEquals(1L, dto.getId());
        assertEquals("https://example.com/webhook", dto.getEndpointUrl());
        assertEquals("APPLICATION_CREATED", dto.getEventType());
        assertTrue(dto.isActive());
        assertEquals("abcd****", dto.getSecretKeyMasked());
        assertEquals(LocalDateTime.of(2023, 1, 1, 12, 0), dto.getCreatedAt());
        assertEquals(LocalDateTime.of(2023, 1, 2, 12, 0), dto.getUpdatedAt());
        assertEquals(LocalDateTime.of(2023, 1, 2, 10, 0), dto.getLastDeliveryAt());
        assertTrue(dto.getLastDeliverySuccess());
        assertEquals(200, dto.getLastDeliveryStatusCode());
        assertEquals(10L, dto.getSuccessfulDeliveriesCount());
        assertEquals(2L, dto.getFailedDeliveriesCount());
        assertEquals("X-Webhook-Signature", dto.getSignatureHeader());
    }

    /**
     * Tests the masking of the secret key in the WebhookResponseDTO.
     */
    @Test
    public void testSecretKeyMasking() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setSecretKey("abcdefghijklmnopqrstuvwxyz123456"); // 32 characters

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertNotNull(dto.getSecretKeyMasked());
        assertEquals("abcd****", dto.getSecretKeyMasked());
    }

    /**
     * Tests the masking of a short secret key in the WebhookResponseDTO.
     */
    @Test
    public void testShortSecretKeyMasking() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setSecretKey("abc"); // 3 characters

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertNotNull(dto.getSecretKeyMasked());
        assertEquals("abc*****", dto.getSecretKeyMasked());
    }

    /**
     * Tests the handling of a null secret key in the WebhookResponseDTO.
     */
    @Test
    public void testNullSecretKeyMasking() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setSecretKey(null);

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertNull(dto.getSecretKeyMasked());
    }

    /**
     * Tests the handling of an empty secret key in the WebhookResponseDTO.
     */
    @Test
    public void testEmptySecretKeyMasking() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setSecretKey("");

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertNull(dto.getSecretKeyMasked());
    }

    /**
     * Tests the delivery status information in the WebhookResponseDTO.
     */
    @Test
    public void testDeliveryStatusInformation() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setLastDeliverySuccess(true);
        webhook.setLastDeliveryStatusCode(200);
        webhook.setLastDeliveryError(null);
        webhook.setSuccessfulDeliveriesCount(10L);
        webhook.setFailedDeliveriesCount(2L);
        LocalDateTime lastDeliveryAttempt = LocalDateTime.now().minusHours(1);
        webhook.setLastDeliveryAttempt(lastDeliveryAttempt);

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertEquals(lastDeliveryAttempt, dto.getLastDeliveryAt());
        assertTrue(dto.getLastDeliverySuccess());
        assertEquals(200, dto.getLastDeliveryStatusCode());
        assertNull(dto.getLastDeliveryError());
        assertEquals(10L, dto.getSuccessfulDeliveriesCount());
        assertEquals(2L, dto.getFailedDeliveriesCount());
    }

    /**
     * Tests the delivery status information with error in the WebhookResponseDTO.
     */
    @Test
    public void testDeliveryStatusWithError() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setLastDeliverySuccess(false);
        webhook.setLastDeliveryStatusCode(500);
        webhook.setLastDeliveryError("Internal Server Error");
        webhook.setSuccessfulDeliveriesCount(10L);
        webhook.setFailedDeliveriesCount(3L);
        LocalDateTime lastDeliveryAttempt = LocalDateTime.now().minusHours(1);
        webhook.setLastDeliveryAttempt(lastDeliveryAttempt);

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertEquals(lastDeliveryAttempt, dto.getLastDeliveryAt());
        assertFalse(dto.getLastDeliverySuccess());
        assertEquals(500, dto.getLastDeliveryStatusCode());
        assertEquals("Internal Server Error", dto.getLastDeliveryError());
        assertEquals(10L, dto.getSuccessfulDeliveriesCount());
        assertEquals(3L, dto.getFailedDeliveriesCount());
    }

    /**
     * Tests the handling of null delivery status information in the WebhookResponseDTO.
     */
    @Test
    public void testNullDeliveryStatusInformation() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setLastDeliverySuccess(null);
        webhook.setLastDeliveryStatusCode(null);
        webhook.setLastDeliveryError(null);
        webhook.setSuccessfulDeliveriesCount(null);
        webhook.setFailedDeliveriesCount(null);
        webhook.setLastDeliveryAttempt(null);

        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);

        // Then
        assertNull(dto.getLastDeliveryAt());
        assertNull(dto.getLastDeliverySuccess());
        assertNull(dto.getLastDeliveryStatusCode());
        assertNull(dto.getLastDeliveryError());
        assertNull(dto.getSuccessfulDeliveriesCount());
        assertNull(dto.getFailedDeliveriesCount());
    }
}