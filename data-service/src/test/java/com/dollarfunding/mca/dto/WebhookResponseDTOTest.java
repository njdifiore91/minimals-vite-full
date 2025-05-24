package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.TestUtils;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link WebhookResponseDTO} that validates the webhook configuration structure,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly represents webhook configurations,
 * masks sensitive information appropriately, and includes delivery status information.
 */
@DisplayName("Webhook Response DTO Tests")
public class WebhookResponseDTOTest {

    private ObjectMapper objectMapper;
    
    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
    }
    
    /**
     * Test data provider for different event types.
     */
    static Stream<Arguments> eventTypeProvider() {
        return Stream.of(
            Arguments.of(EventType.APPLICATION_CREATED, "APPLICATION_CREATED"),
            Arguments.of(EventType.APPLICATION_UPDATED, "APPLICATION_UPDATED"),
            Arguments.of(EventType.APPLICATION_APPROVED, "APPLICATION_APPROVED"),
            Arguments.of(EventType.APPLICATION_REJECTED, "APPLICATION_REJECTED"),
            Arguments.of(EventType.DOCUMENT_UPLOADED, "DOCUMENT_UPLOADED"),
            Arguments.of(EventType.DOCUMENT_PROCESSED, "DOCUMENT_PROCESSED")
        );
    }

    @Test
    @DisplayName("Should create a valid DTO with default constructor")
    void shouldCreateValidDTOWithDefaultConstructor() {
        // Given/When
        WebhookResponseDTO dto = new WebhookResponseDTO();
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertNull(dto.getId(), "ID should be null");
        assertNull(dto.getEndpointUrl(), "Endpoint URL should be null");
        assertNull(dto.getEventType(), "Event type should be null");
        assertNull(dto.getActive(), "Active status should be null");
        assertNull(dto.getCreatedAt(), "Created at should be null");
        assertNull(dto.getUpdatedAt(), "Updated at should be null");
    }
    
    @Test
    @DisplayName("Should create a valid DTO from Webhook entity")
    void shouldCreateValidDTOFromWebhookEntity() {
        // Given
        Webhook webhook = TestUtils.createRandomWebhook();
        webhook.setMaxRetryAttempts(5);
        webhook.setConsecutiveFailures(2);
        webhook.setLastSuccessAt(LocalDateTime.now().minusDays(1));
        webhook.setLastFailureAt(LocalDateTime.now().minusHours(2));
        
        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertEquals(webhook.getId(), dto.getId(), "ID should match");
        assertEquals(webhook.getEndpointUrl(), dto.getEndpointUrl(), "Endpoint URL should match");
        assertEquals(webhook.getEventType(), dto.getEventType(), "Event type should match");
        assertEquals(webhook.getActive(), dto.getActive(), "Active status should match");
        assertEquals(webhook.getMaxRetryAttempts(), dto.getMaxRetryAttempts(), "Max retry attempts should match");
        assertEquals(webhook.getFailedAttempts(), dto.getFailedAttempts(), "Failed attempts should match");
        assertEquals(webhook.getCreatedAt(), dto.getCreatedAt(), "Created at should match");
        assertEquals(webhook.getUpdatedAt(), dto.getUpdatedAt(), "Updated at should match");
        
        // Check that secret key is masked
        assertNotNull(dto.getMaskedSecretKey(), "Masked secret key should not be null");
        assertNotEquals(webhook.getSecretKey(), dto.getMaskedSecretKey(), "Secret key should be masked");
        assertTrue(dto.getMaskedSecretKey().contains("*"), "Masked secret key should contain asterisks");
    }
    
    @Test
    @DisplayName("Should return null when creating DTO from null entity")
    void shouldReturnNullWhenCreatingDTOFromNullEntity() {
        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(null);
        
        // Then
        assertNull(dto, "DTO should be null when entity is null");
    }
    
    @Test
    @DisplayName("Should correctly mask secret key")
    void shouldCorrectlyMaskSecretKey() {
        // Given
        Webhook webhook = new Webhook();
        webhook.setSecretKey("abcdefghijklmnopqrstuvwxyz");
        
        // When
        WebhookResponseDTO dto = WebhookResponseDTO.fromEntity(webhook);
        
        // Then
        assertNotNull(dto.getMaskedSecretKey(), "Masked secret key should not be null");
        assertEquals("abcd**********wxyz", dto.getMaskedSecretKey(), "Secret key should be masked correctly");
        
        // Test with short key
        webhook.setSecretKey("abc");
        dto = WebhookResponseDTO.fromEntity(webhook);
        assertEquals("a*****c", dto.getMaskedSecretKey(), "Short secret key should be masked correctly");
        
        // Test with null key
        webhook.setSecretKey(null);
        dto = WebhookResponseDTO.fromEntity(webhook);
        assertNull(dto.getMaskedSecretKey(), "Masked secret key should be null when key is null");
    }
    
    @ParameterizedTest
    @DisplayName("Should correctly set and get event type")
    @MethodSource("eventTypeProvider")
    void shouldCorrectlySetAndGetEventType(EventType eventType, String expectedString) {
        // Given
        WebhookResponseDTO dto = new WebhookResponseDTO();
        
        // When
        dto.setEventType(eventType);
        
        // Then
        assertEquals(eventType, dto.getEventType(), "Event type should match");
        assertEquals(expectedString, dto.getEventType().name(), "Event type name should match");
    }
    
    @Test
    @DisplayName("Should correctly set and get delivery status information")
    void shouldCorrectlySetAndGetDeliveryStatusInformation() {
        // Given
        WebhookResponseDTO dto = new WebhookResponseDTO();
        LocalDateTime now = LocalDateTime.now();
        
        // When
        dto.setLastDeliveryStatus("SUCCESS");
        dto.setLastDeliveryAttempt(now);
        dto.setFailedAttempts(3);
        dto.setLastDeliverySuccess(true);
        dto.setLastDeliveryStatusCode(200);
        dto.setLastDeliveryError(null);
        dto.setSuccessfulDeliveriesCount(10L);
        dto.setFailedDeliveriesCount(5L);
        
        // Then
        assertEquals("SUCCESS", dto.getLastDeliveryStatus(), "Last delivery status should match");
        assertEquals(now, dto.getLastDeliveryAttempt(), "Last delivery attempt should match");
        assertEquals(3, dto.getFailedAttempts(), "Failed attempts should match");
        assertTrue(dto.getLastDeliverySuccess(), "Last delivery success should match");
        assertEquals(200, dto.getLastDeliveryStatusCode(), "Last delivery status code should match");
        assertNull(dto.getLastDeliveryError(), "Last delivery error should be null");
        assertEquals(10L, dto.getSuccessfulDeliveriesCount(), "Successful deliveries count should match");
        assertEquals(5L, dto.getFailedDeliveriesCount(), "Failed deliveries count should match");
    }
    
    @Test
    @DisplayName("Should correctly calculate delivery status summary")
    void shouldCorrectlyCalculateDeliveryStatusSummary() {
        // Given
        WebhookResponseDTO dto = new WebhookResponseDTO();
        
        // When/Then - No delivery attempt
        assertEquals("Never triggered", dto.getDeliveryStatusSummary(), "Should indicate never triggered");
        
        // When - Successful delivery
        LocalDateTime now = LocalDateTime.now();
        dto.setLastDeliveryAttempt(now);
        dto.setLastDeliverySuccess(true);
        
        // Then
        assertTrue(dto.getDeliveryStatusSummary().startsWith("Last delivery successful at"), 
                "Should indicate successful delivery");
        
        // When - Failed delivery
        dto.setLastDeliverySuccess(false);
        dto.setFailedAttempts(3);
        
        // Then
        assertTrue(dto.getDeliveryStatusSummary().startsWith("Failed delivery (3 attempts)"), 
                "Should indicate failed delivery with attempts");
        
        // When - Custom status
        dto.setLastDeliveryStatus("PENDING");
        dto.setFailedAttempts(0);
        
        // Then
        assertEquals("PENDING", dto.getDeliveryStatusSummary(), "Should use custom status");
    }
    
    @Test
    @DisplayName("Should correctly calculate health status")
    void shouldCorrectlyCalculateHealthStatus() {
        // Given
        WebhookResponseDTO dto = new WebhookResponseDTO();
        
        // When/Then - No delivery attempt
        assertEquals("unknown", dto.getHealthStatus(), "Health status should be unknown");
        
        // When - Successful delivery
        dto.setLastDeliveryAttempt(LocalDateTime.now());
        dto.setLastDeliverySuccess(true);
        
        // Then
        assertEquals("healthy", dto.getHealthStatus(), "Health status should be healthy");
        
        // When - Failed delivery but under max retries
        dto.setLastDeliverySuccess(false);
        dto.setFailedAttempts(2);
        dto.setMaxRetryAttempts(5);
        
        // Then
        assertEquals("warning", dto.getHealthStatus(), "Health status should be warning");
        
        // When - Failed delivery over max retries
        dto.setFailedAttempts(5);
        
        // Then
        assertEquals("error", dto.getHealthStatus(), "Health status should be error");
    }
    
    @Test
    @DisplayName("Should correctly format dates in JSON serialization")
    void shouldCorrectlyFormatDatesInJsonSerialization() throws Exception {
        // Given
        WebhookResponseDTO dto = new WebhookResponseDTO();
        LocalDateTime now = LocalDateTime.now();
        dto.setCreatedAt(now);
        dto.setUpdatedAt(now);
        dto.setLastDeliveryAttempt(now);
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        String expectedDateFormat = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS"));
        assertTrue(json.contains("\"created_at\":\"" + expectedDateFormat + "\""), "JSON should contain formatted created_at");
        assertTrue(json.contains("\"updated_at\":\"" + expectedDateFormat + "\""), "JSON should contain formatted updated_at");
        assertTrue(json.contains("\"last_delivery_attempt\":\"" + expectedDateFormat + "\""), 
                "JSON should contain formatted last_delivery_attempt");
    }
    
    @Test
    @DisplayName("Should correctly serialize to JSON")
    void shouldCorrectlySerializeToJson() throws Exception {
        // Given
        WebhookResponseDTO dto = new WebhookResponseDTO();
        dto.setId(1L);
        dto.setEndpointUrl("https://example.com/webhook");
        dto.setEventType(EventType.APPLICATION_CREATED);
        dto.setActive(true);
        dto.setMaxRetryAttempts(3);
        dto.setLastDeliveryStatus("SUCCESS");
        dto.setLastDeliverySuccess(true);
        dto.setLastDeliveryStatusCode(200);
        dto.setSuccessfulDeliveriesCount(10L);
        dto.setFailedDeliveriesCount(2L);
        dto.setSignatureHeader("X-Webhook-Signature");
        dto.setMaskedSecretKey("abcd*****wxyz");
        
        LocalDateTime now = LocalDateTime.now();
        dto.setCreatedAt(now);
        dto.setUpdatedAt(now);
        dto.setLastDeliveryAttempt(now);
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertTrue(json.contains("\"id\":1"), "JSON should contain id");
        assertTrue(json.contains("\"endpoint_url\":\"https://example.com/webhook\""), "JSON should contain endpoint_url");
        assertTrue(json.contains("\"event_type\":\"APPLICATION_CREATED\""), "JSON should contain event_type");
        assertTrue(json.contains("\"active\":true"), "JSON should contain active");
        assertTrue(json.contains("\"max_retry_attempts\":3"), "JSON should contain max_retry_attempts");
        assertTrue(json.contains("\"last_delivery_status\":\"SUCCESS\""), "JSON should contain last_delivery_status");
        assertTrue(json.contains("\"last_delivery_success\":true"), "JSON should contain last_delivery_success");
        assertTrue(json.contains("\"last_delivery_status_code\":200"), "JSON should contain last_delivery_status_code");
        assertTrue(json.contains("\"successful_deliveries_count\":10"), "JSON should contain successful_deliveries_count");
        assertTrue(json.contains("\"failed_deliveries_count\":2"), "JSON should contain failed_deliveries_count");
        assertTrue(json.contains("\"signature_header\":\"X-Webhook-Signature\""), "JSON should contain signature_header");
        assertTrue(json.contains("\"masked_secret_key\":\"abcd*****wxyz\""), "JSON should contain masked_secret_key");
        assertTrue(json.contains("\"delivery_status_summary\":"), "JSON should contain delivery_status_summary");
        assertTrue(json.contains("\"health_status\":"), "JSON should contain health_status");
    }
    
    @Test
    @DisplayName("Should correctly deserialize from JSON")
    void shouldCorrectlyDeserializeFromJson() throws Exception {
        // Given
        String createdAt = "2023-01-01T12:00:00.000";
        String updatedAt = "2023-01-02T12:00:00.000";
        String lastDeliveryAttempt = "2023-01-03T12:00:00.000";
        
        String json = "{"
                + "\"id\":1,"
                + "\"endpoint_url\":\"https://example.com/webhook\","
                + "\"event_type\":\"APPLICATION_CREATED\","
                + "\"active\":true,"
                + "\"max_retry_attempts\":3,"
                + "\"last_delivery_status\":\"SUCCESS\","
                + "\"last_delivery_attempt\":\"" + lastDeliveryAttempt + "\","
                + "\"failed_attempts\":0,"
                + "\"last_delivery_success\":true,"
                + "\"last_delivery_status_code\":200,"
                + "\"successful_deliveries_count\":10,"
                + "\"failed_deliveries_count\":2,"
                + "\"signature_header\":\"X-Webhook-Signature\","
                + "\"created_at\":\"" + createdAt + "\","
                + "\"updated_at\":\"" + updatedAt + "\","
                + "\"masked_secret_key\":\"abcd*****wxyz\""
                + "}";
        
        // When
        WebhookResponseDTO dto = objectMapper.readValue(json, WebhookResponseDTO.class);
        
        // Then
        assertEquals(1L, dto.getId(), "ID should match");
        assertEquals("https://example.com/webhook", dto.getEndpointUrl(), "Endpoint URL should match");
        assertEquals(EventType.APPLICATION_CREATED, dto.getEventType(), "Event type should match");
        assertTrue(dto.getActive(), "Active status should match");
        assertEquals(3, dto.getMaxRetryAttempts(), "Max retry attempts should match");
        assertEquals("SUCCESS", dto.getLastDeliveryStatus(), "Last delivery status should match");
        assertEquals(0, dto.getFailedAttempts(), "Failed attempts should match");
        assertTrue(dto.getLastDeliverySuccess(), "Last delivery success should match");
        assertEquals(200, dto.getLastDeliveryStatusCode(), "Last delivery status code should match");
        assertEquals(10L, dto.getSuccessfulDeliveriesCount(), "Successful deliveries count should match");
        assertEquals(2L, dto.getFailedDeliveriesCount(), "Failed deliveries count should match");
        assertEquals("X-Webhook-Signature", dto.getSignatureHeader(), "Signature header should match");
        assertEquals("abcd*****wxyz", dto.getMaskedSecretKey(), "Masked secret key should match");
        
        // Check date parsing
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS");
        LocalDateTime expectedCreatedAt = LocalDateTime.parse(createdAt, formatter);
        LocalDateTime expectedUpdatedAt = LocalDateTime.parse(updatedAt, formatter);
        LocalDateTime expectedLastDeliveryAttempt = LocalDateTime.parse(lastDeliveryAttempt, formatter);
        assertEquals(expectedCreatedAt, dto.getCreatedAt(), "Created at should match");
        assertEquals(expectedUpdatedAt, dto.getUpdatedAt(), "Updated at should match");
        assertEquals(expectedLastDeliveryAttempt, dto.getLastDeliveryAttempt(), "Last delivery attempt should match");
    }
    
    @Test
    @DisplayName("Should handle null values in JSON deserialization")
    void shouldHandleNullValuesInJsonDeserialization() throws Exception {
        // Given
        String json = "{"
                + "\"id\":1,"
                + "\"endpoint_url\":\"https://example.com/webhook\","
                + "\"event_type\":null,"
                + "\"active\":null,"
                + "\"max_retry_attempts\":null,"
                + "\"last_delivery_status\":null,"
                + "\"last_delivery_attempt\":null,"
                + "\"failed_attempts\":null,"
                + "\"last_delivery_success\":null,"
                + "\"last_delivery_status_code\":null,"
                + "\"successful_deliveries_count\":null,"
                + "\"failed_deliveries_count\":null,"
                + "\"signature_header\":null,"
                + "\"created_at\":null,"
                + "\"updated_at\":null,"
                + "\"masked_secret_key\":null"
                + "}";
        
        // When
        WebhookResponseDTO dto = objectMapper.readValue(json, WebhookResponseDTO.class);
        
        // Then
        assertEquals(1L, dto.getId(), "ID should match");
        assertEquals("https://example.com/webhook", dto.getEndpointUrl(), "Endpoint URL should match");
        assertNull(dto.getEventType(), "Event type should be null");
        assertNull(dto.getActive(), "Active status should be null");
        assertNull(dto.getMaxRetryAttempts(), "Max retry attempts should be null");
        assertNull(dto.getLastDeliveryStatus(), "Last delivery status should be null");
        assertNull(dto.getLastDeliveryAttempt(), "Last delivery attempt should be null");
        assertNull(dto.getFailedAttempts(), "Failed attempts should be null");
        assertNull(dto.getLastDeliverySuccess(), "Last delivery success should be null");
        assertNull(dto.getLastDeliveryStatusCode(), "Last delivery status code should be null");
        assertNull(dto.getSuccessfulDeliveriesCount(), "Successful deliveries count should be null");
        assertNull(dto.getFailedDeliveriesCount(), "Failed deliveries count should be null");
        assertNull(dto.getSignatureHeader(), "Signature header should be null");
        assertNull(dto.getCreatedAt(), "Created at should be null");
        assertNull(dto.getUpdatedAt(), "Updated at should be null");
        assertNull(dto.getMaskedSecretKey(), "Masked secret key should be null");
    }
    
    @Test
    @DisplayName("Should correctly implement toString method")
    void shouldCorrectlyImplementToStringMethod() {
        // Given
        WebhookResponseDTO dto = new WebhookResponseDTO();
        dto.setId(1L);
        dto.setEndpointUrl("https://example.com/webhook");
        dto.setEventType(EventType.APPLICATION_CREATED);
        dto.setActive(true);
        
        // When
        String toString = dto.toString();
        
        // Then
        assertNotNull(toString, "toString should not be null");
        assertTrue(toString.contains("id=1"), "toString should contain id");
        assertTrue(toString.contains("endpointUrl='https://example.com/webhook'"), "toString should contain endpointUrl");
        assertTrue(toString.contains("eventType=APPLICATION_CREATED"), "toString should contain eventType");
        assertTrue(toString.contains("active=true"), "toString should contain active");
    }
}