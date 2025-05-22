package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.WebhookRequestDTO;
import com.dollarfunding.mca.dto.WebhookResponseDTO;
import com.dollarfunding.mca.dto.WebhookTestRequestDTO;
import com.dollarfunding.mca.dto.WebhookTestResponseDTO;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.WebhookDeliveryException;
import com.dollarfunding.mca.repository.WebhookRepository;
import com.dollarfunding.mca.util.JsonUtil;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the WebhookServiceImpl class.
 * 
 * Tests verify CRUD operations for webhook endpoints, HMAC signing for secure payload delivery,
 * retry logic for failed deliveries, and asynchronous webhook delivery.
 */
@ExtendWith(MockitoExtension.class)
public class WebhookServiceImplTest {

    @Mock
    private WebhookRepository webhookRepository;

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private WebhookServiceImpl webhookService;

    private Webhook testWebhook;
    private WebhookRequestDTO testWebhookRequestDTO;
    private WebhookResponseDTO testWebhookResponseDTO;
    private Map<String, Object> testPayload;

    @BeforeEach
    void setUp() {
        // Set up test data
        testWebhook = new Webhook();
        testWebhook.setId(1L);
        testWebhook.setEndpointUrl("https://test-webhook.example.com/endpoint");
        testWebhook.setEventType(EventType.APPLICATION_CREATED);
        testWebhook.setSecretKey("test-secret-key");
        testWebhook.setSignatureHeader("X-Webhook-Signature");
        testWebhook.setActive(true);
        testWebhook.setCreatedAt(LocalDateTime.now().minusDays(1));
        testWebhook.setUpdatedAt(LocalDateTime.now());
        testWebhook.setLastDeliveryAt(null);
        testWebhook.setLastDeliverySuccess(null);
        testWebhook.setLastDeliveryStatusCode(null);
        testWebhook.setLastDeliveryError(null);
        testWebhook.setSuccessfulDeliveriesCount(0);
        testWebhook.setFailedDeliveriesCount(0);
        testWebhook.setFailedAttempts(0);

        testWebhookRequestDTO = new WebhookRequestDTO();
        testWebhookRequestDTO.setEndpointUrl("https://test-webhook.example.com/endpoint");
        testWebhookRequestDTO.setEventType(EventType.APPLICATION_CREATED.name());
        testWebhookRequestDTO.setSecretKey("test-secret-key");
        testWebhookRequestDTO.setSignatureHeader("X-Webhook-Signature");
        testWebhookRequestDTO.setActive(true);

        testWebhookResponseDTO = WebhookResponseDTO.fromEntity(testWebhook);

        testPayload = new HashMap<>();
        testPayload.put("event", "test-event");
        testPayload.put("timestamp", LocalDateTime.now().toString());
        testPayload.put("data", Map.of("key", "value"));

        // Set up configuration values using ReflectionTestUtils
        ReflectionTestUtils.setField(webhookService, "webhookDeliveryTimeout", 5000);
        ReflectionTestUtils.setField(webhookService, "maxRetryAttempts", 3);
        ReflectionTestUtils.setField(webhookService, "initialRetryDelayMs", 1000L);
        ReflectionTestUtils.setField(webhookService, "maxRetryDelayMs", 60000L);
        ReflectionTestUtils.setField(webhookService, "jitterFactor", 0.5);
    }

    @Test
    @DisplayName("Should create webhook successfully")
    void createWebhook_Success() {
        // Arrange
        when(webhookRepository.existsByEndpointUrl(anyString())).thenReturn(false);
        when(webhookRepository.save(any(Webhook.class))).thenReturn(testWebhook);

        // Act
        WebhookResponseDTO result = webhookService.createWebhook(testWebhookRequestDTO);

        // Assert
        assertNotNull(result);
        assertEquals(testWebhook.getId(), result.getId());
        assertEquals(testWebhook.getEndpointUrl(), result.getEndpointUrl());
        assertEquals(testWebhook.getEventType().name(), result.getEventType());
        assertTrue(result.getActive());

        // Verify repository interactions
        verify(webhookRepository).existsByEndpointUrl(testWebhookRequestDTO.getEndpointUrl());
        verify(webhookRepository).save(any(Webhook.class));
    }

    @Test
    @DisplayName("Should throw exception when creating webhook with existing URL")
    void createWebhook_ExistingUrl_ThrowsException() {
        // Arrange
        when(webhookRepository.existsByEndpointUrl(anyString())).thenReturn(true);

        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, 
                () -> webhookService.createWebhook(testWebhookRequestDTO));
        
        assertTrue(exception.getMessage().contains("already exists"));
        verify(webhookRepository).existsByEndpointUrl(testWebhookRequestDTO.getEndpointUrl());
        verify(webhookRepository, never()).save(any(Webhook.class));
    }

    @Test
    @DisplayName("Should throw exception when creating webhook with invalid event type")
    void createWebhook_InvalidEventType_ThrowsException() {
        // Arrange
        testWebhookRequestDTO.setEventType("INVALID_EVENT_TYPE");

        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, 
                () -> webhookService.createWebhook(testWebhookRequestDTO));
        
        assertTrue(exception.getMessage().contains("Invalid event type"));
        verify(webhookRepository, never()).existsByEndpointUrl(anyString());
        verify(webhookRepository, never()).save(any(Webhook.class));
    }

    @Test
    @DisplayName("Should get all webhooks successfully")
    void getAllWebhooks_Success() {
        // Arrange
        List<Webhook> webhooks = Arrays.asList(testWebhook);
        when(webhookRepository.findAll()).thenReturn(webhooks);

        // Act
        List<WebhookResponseDTO> result = webhookService.getAllWebhooks();

        // Assert
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals(testWebhook.getId(), result.get(0).getId());
        assertEquals(testWebhook.getEndpointUrl(), result.get(0).getEndpointUrl());
        assertEquals(testWebhook.getEventType().name(), result.get(0).getEventType());

        // Verify repository interactions
        verify(webhookRepository).findAll();
    }

    @Test
    @DisplayName("Should get webhook by ID successfully")
    void getWebhookById_Success() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));

        // Act
        WebhookResponseDTO result = webhookService.getWebhookById(1L);

        // Assert
        assertNotNull(result);
        assertEquals(testWebhook.getId(), result.getId());
        assertEquals(testWebhook.getEndpointUrl(), result.getEndpointUrl());
        assertEquals(testWebhook.getEventType().name(), result.getEventType());

        // Verify repository interactions
        verify(webhookRepository).findById(1L);
    }

    @Test
    @DisplayName("Should throw exception when getting webhook with non-existent ID")
    void getWebhookById_NonExistentId_ThrowsException() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, 
                () -> webhookService.getWebhookById(1L));
        
        assertTrue(exception.getMessage().contains("not found"));
        verify(webhookRepository).findById(1L);
    }

    @Test
    @DisplayName("Should update webhook successfully")
    void updateWebhook_Success() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        when(webhookRepository.findByEndpointUrl(anyString())).thenReturn(Optional.empty());
        when(webhookRepository.save(any(Webhook.class))).thenReturn(testWebhook);

        // Update the request DTO
        testWebhookRequestDTO.setEventType(EventType.APPLICATION_UPDATED.name());
        testWebhookRequestDTO.setActive(false);

        // Act
        WebhookResponseDTO result = webhookService.updateWebhook(1L, testWebhookRequestDTO);

        // Assert
        assertNotNull(result);
        assertEquals(testWebhook.getId(), result.getId());
        assertEquals(testWebhook.getEndpointUrl(), result.getEndpointUrl());
        assertEquals(testWebhook.getEventType().name(), result.getEventType());

        // Verify repository interactions
        verify(webhookRepository).findById(1L);
        verify(webhookRepository).findByEndpointUrl(testWebhookRequestDTO.getEndpointUrl());
        verify(webhookRepository).save(any(Webhook.class));
    }

    @Test
    @DisplayName("Should throw exception when updating webhook with non-existent ID")
    void updateWebhook_NonExistentId_ThrowsException() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, 
                () -> webhookService.updateWebhook(1L, testWebhookRequestDTO));
        
        assertTrue(exception.getMessage().contains("not found"));
        verify(webhookRepository).findById(1L);
        verify(webhookRepository, never()).findByEndpointUrl(anyString());
        verify(webhookRepository, never()).save(any(Webhook.class));
    }

    @Test
    @DisplayName("Should throw exception when updating webhook with URL that already exists for another webhook")
    void updateWebhook_ExistingUrlForAnotherWebhook_ThrowsException() {
        // Arrange
        Webhook existingWebhook = new Webhook();
        existingWebhook.setId(2L); // Different ID
        existingWebhook.setEndpointUrl(testWebhookRequestDTO.getEndpointUrl());

        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        when(webhookRepository.findByEndpointUrl(anyString())).thenReturn(Optional.of(existingWebhook));

        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, 
                () -> webhookService.updateWebhook(1L, testWebhookRequestDTO));
        
        assertTrue(exception.getMessage().contains("already exists"));
        verify(webhookRepository).findById(1L);
        verify(webhookRepository).findByEndpointUrl(testWebhookRequestDTO.getEndpointUrl());
        verify(webhookRepository, never()).save(any(Webhook.class));
    }

    @Test
    @DisplayName("Should delete webhook successfully")
    void deleteWebhook_Success() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        doNothing().when(webhookRepository).delete(any(Webhook.class));

        // Act
        webhookService.deleteWebhook(1L);

        // Verify repository interactions
        verify(webhookRepository).findById(1L);
        verify(webhookRepository).delete(testWebhook);
    }

    @Test
    @DisplayName("Should throw exception when deleting webhook with non-existent ID")
    void deleteWebhook_NonExistentId_ThrowsException() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, 
                () -> webhookService.deleteWebhook(1L));
        
        assertTrue(exception.getMessage().contains("not found"));
        verify(webhookRepository).findById(1L);
        verify(webhookRepository, never()).delete(any(Webhook.class));
    }

    @Test
    @DisplayName("Should get active webhooks by event type successfully")
    void getActiveWebhooksByEventType_Success() {
        // Arrange
        List<Webhook> webhooks = Arrays.asList(testWebhook);
        when(webhookRepository.findByEventTypeAndActive(any(EventType.class), anyBoolean()))
                .thenReturn(webhooks);

        // Act
        List<Webhook> result = webhookService.getActiveWebhooksByEventType(EventType.APPLICATION_CREATED);

        // Assert
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals(testWebhook.getId(), result.get(0).getId());
        assertEquals(testWebhook.getEndpointUrl(), result.get(0).getEndpointUrl());
        assertEquals(testWebhook.getEventType(), result.get(0).getEventType());

        // Verify repository interactions
        verify(webhookRepository).findByEventTypeAndActive(EventType.APPLICATION_CREATED, true);
    }

    @Test
    @DisplayName("Should test webhook successfully with synchronous delivery")
    void testWebhook_SynchronousDelivery_Success() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        WebhookTestRequestDTO testRequestDTO = new WebhookTestRequestDTO();
        testRequestDTO.setWebhookId("1");
        testRequestDTO.setTestPayload(testPayload);
        testRequestDTO.setIncludeSignature(true);
        testRequestDTO.setAsync(false);
        
        ResponseEntity<String> responseEntity = new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK);
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenReturn(responseEntity);

        // Act
        WebhookTestResponseDTO result = webhookService.testWebhook(1L, testRequestDTO);

        // Assert
        assertNotNull(result);
        assertTrue(result.getSuccess());
        assertEquals(HttpStatus.OK.value(), result.getResponseCode());
        assertEquals("{\"status\":\"success\"}", result.getResponseBody());
        assertNotNull(result.getDeliveryTimestamp());
        assertNotNull(result.getGeneratedSignature());
        assertTrue(result.getSignatureVerified());

        // Verify repository and RestTemplate interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should test webhook successfully with asynchronous delivery")
    void testWebhook_AsynchronousDelivery_Success() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        WebhookTestRequestDTO testRequestDTO = new WebhookTestRequestDTO();
        testRequestDTO.setWebhookId("1");
        testRequestDTO.setTestPayload(testPayload);
        testRequestDTO.setIncludeSignature(true);
        testRequestDTO.setAsync(true);

        // Act
        WebhookTestResponseDTO result = webhookService.testWebhook(1L, testRequestDTO);

        // Assert
        assertNotNull(result);
        assertTrue(result.getSuccess());
        assertNull(result.getResponseCode());
        assertNotNull(result.getResponseBody());
        assertNotNull(result.getDeliveryTimestamp());
        assertNotNull(result.getGeneratedSignature());
        assertTrue(result.getSignatureVerified());

        // Verify repository interactions
        verify(webhookRepository).findById(1L);
        // RestTemplate should not be called for async delivery in the test method
        verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should handle HTTP error when testing webhook")
    void testWebhook_HttpError_ReturnsErrorResponse() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        WebhookTestRequestDTO testRequestDTO = new WebhookTestRequestDTO();
        testRequestDTO.setWebhookId("1");
        testRequestDTO.setTestPayload(testPayload);
        testRequestDTO.setIncludeSignature(true);
        testRequestDTO.setAsync(false);
        
        HttpStatusCodeException exception = mock(HttpStatusCodeException.class);
        when(exception.getRawStatusCode()).thenReturn(HttpStatus.BAD_REQUEST.value());
        when(exception.getStatusCode()).thenReturn(HttpStatus.BAD_REQUEST);
        when(exception.getResponseBodyAsString()).thenReturn("{\"error\":\"Invalid request\"}");
        
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenThrow(exception);

        // Act
        WebhookTestResponseDTO result = webhookService.testWebhook(1L, testRequestDTO);

        // Assert
        assertNotNull(result);
        assertFalse(result.getSuccess());
        assertEquals(HttpStatus.BAD_REQUEST.value(), result.getResponseCode());
        assertNotNull(result.getErrorMessage());
        assertEquals("{\"error\":\"Invalid request\"}", result.getErrorDetails());
        assertNotNull(result.getDeliveryTimestamp());
        assertNotNull(result.getGeneratedSignature());
        assertTrue(result.getSignatureVerified());

        // Verify repository and RestTemplate interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should handle general exception when testing webhook")
    void testWebhook_GeneralException_ReturnsErrorResponse() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        WebhookTestRequestDTO testRequestDTO = new WebhookTestRequestDTO();
        testRequestDTO.setWebhookId("1");
        testRequestDTO.setTestPayload(testPayload);
        testRequestDTO.setIncludeSignature(true);
        testRequestDTO.setAsync(false);
        
        RestClientException exception = new RestClientException("Connection timeout");
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenThrow(exception);

        // Act
        WebhookTestResponseDTO result = webhookService.testWebhook(1L, testRequestDTO);

        // Assert
        assertNotNull(result);
        assertFalse(result.getSuccess());
        assertNull(result.getResponseCode());
        assertNotNull(result.getErrorMessage());
        assertTrue(result.getErrorMessage().contains("Connection timeout"));
        assertNotNull(result.getErrorDetails());
        assertNotNull(result.getDeliveryTimestamp());
        assertNotNull(result.getGeneratedSignature());
        assertTrue(result.getSignatureVerified());

        // Verify repository and RestTemplate interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should throw exception when webhook IDs don't match in test request")
    void testWebhook_IdMismatch_ThrowsException() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        WebhookTestRequestDTO testRequestDTO = new WebhookTestRequestDTO();
        testRequestDTO.setWebhookId("2"); // Different ID
        testRequestDTO.setTestPayload(testPayload);

        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, 
                () -> webhookService.testWebhook(1L, testRequestDTO));
        
        assertTrue(exception.getMessage().contains("does not match"));
        verify(webhookRepository).findById(1L);
        verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should deliver webhook successfully")
    void deliverWebhook_Success() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        ResponseEntity<String> responseEntity = new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK);
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenReturn(responseEntity);

        // Act
        boolean result = webhookService.deliverWebhook(1L, testPayload);

        // Assert
        assertTrue(result);

        // Verify webhook status updates
        ArgumentCaptor<Webhook> webhookCaptor = ArgumentCaptor.forClass(Webhook.class);
        verify(webhookRepository).save(webhookCaptor.capture());
        
        Webhook savedWebhook = webhookCaptor.getValue();
        assertTrue(savedWebhook.getLastDeliverySuccess());
        assertEquals(HttpStatus.OK.value(), savedWebhook.getLastDeliveryStatusCode());
        assertNull(savedWebhook.getLastDeliveryError());
        assertEquals(1, savedWebhook.getSuccessfulDeliveriesCount());
        assertNotNull(savedWebhook.getLastDeliveryAt());

        // Verify repository and RestTemplate interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should not deliver webhook when it's inactive")
    void deliverWebhook_InactiveWebhook_ReturnsFalse() {
        // Arrange
        testWebhook.setActive(false);
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));

        // Act
        boolean result = webhookService.deliverWebhook(1L, testPayload);

        // Assert
        assertFalse(result);

        // Verify repository interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
        verify(webhookRepository, never()).save(any(Webhook.class));
    }

    @Test
    @DisplayName("Should handle HTTP error when delivering webhook")
    void deliverWebhook_HttpError_ThrowsException() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        HttpStatusCodeException exception = mock(HttpStatusCodeException.class);
        when(exception.getRawStatusCode()).thenReturn(HttpStatus.BAD_REQUEST.value());
        when(exception.getStatusCode()).thenReturn(HttpStatus.BAD_REQUEST);
        when(exception.getResponseBodyAsString()).thenReturn("{\"error\":\"Invalid request\"}");
        
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenThrow(exception);

        // Act & Assert
        WebhookDeliveryException deliveryException = assertThrows(WebhookDeliveryException.class, 
                () -> webhookService.deliverWebhook(1L, testPayload));
        
        assertTrue(deliveryException.getMessage().contains("Failed to deliver webhook"));

        // Verify webhook status updates
        ArgumentCaptor<Webhook> webhookCaptor = ArgumentCaptor.forClass(Webhook.class);
        verify(webhookRepository).save(webhookCaptor.capture());
        
        Webhook savedWebhook = webhookCaptor.getValue();
        assertFalse(savedWebhook.getLastDeliverySuccess());
        assertEquals(HttpStatus.BAD_REQUEST.value(), savedWebhook.getLastDeliveryStatusCode());
        assertNotNull(savedWebhook.getLastDeliveryError());
        assertEquals(1, savedWebhook.getFailedDeliveriesCount());
        assertNotNull(savedWebhook.getLastDeliveryAt());

        // Verify repository and RestTemplate interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should handle general exception when delivering webhook")
    void deliverWebhook_GeneralException_ThrowsException() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        RestClientException exception = new RestClientException("Connection timeout");
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenThrow(exception);

        // Act & Assert
        WebhookDeliveryException deliveryException = assertThrows(WebhookDeliveryException.class, 
                () -> webhookService.deliverWebhook(1L, testPayload));
        
        assertTrue(deliveryException.getMessage().contains("Failed to deliver webhook"));

        // Verify webhook status updates
        ArgumentCaptor<Webhook> webhookCaptor = ArgumentCaptor.forClass(Webhook.class);
        verify(webhookRepository).save(webhookCaptor.capture());
        
        Webhook savedWebhook = webhookCaptor.getValue();
        assertFalse(savedWebhook.getLastDeliverySuccess());
        assertNull(savedWebhook.getLastDeliveryStatusCode());
        assertNotNull(savedWebhook.getLastDeliveryError());
        assertEquals(1, savedWebhook.getFailedDeliveriesCount());
        assertNotNull(savedWebhook.getLastDeliveryAt());

        // Verify repository and RestTemplate interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should deliver webhook asynchronously")
    void deliverWebhookAsync_Success() throws ExecutionException, InterruptedException {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        
        ResponseEntity<String> responseEntity = new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK);
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenReturn(responseEntity);

        // Act
        CompletableFuture<Boolean> future = webhookService.deliverWebhookAsync(1L, testPayload);
        
        // Assert
        assertTrue(future.get()); // Wait for the future to complete and check result

        // Verify repository and RestTemplate interactions
        verify(webhookRepository).findById(1L);
        verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
    }

    @Test
    @DisplayName("Should retry failed webhooks")
    void retryFailedWebhooks_Success() {
        // Arrange
        List<Webhook> webhooksToRetry = Arrays.asList(testWebhook);
        when(webhookRepository.findWebhooksForRetry()).thenReturn(webhooksToRetry);

        // Act
        int retryCount = webhookService.retryFailedWebhooks();

        // Assert
        assertEquals(1, retryCount);

        // Verify repository interactions
        verify(webhookRepository).findWebhooksForRetry();
    }

    @Test
    @DisplayName("Should set webhook active status")
    void setWebhookActive_Success() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.of(testWebhook));
        when(webhookRepository.save(any(Webhook.class))).thenReturn(testWebhook);

        // Act
        WebhookResponseDTO result = webhookService.setWebhookActive(1L, false);

        // Assert
        assertNotNull(result);
        assertFalse(result.getActive());

        // Verify repository interactions
        verify(webhookRepository).findById(1L);
        
        ArgumentCaptor<Webhook> webhookCaptor = ArgumentCaptor.forClass(Webhook.class);
        verify(webhookRepository).save(webhookCaptor.capture());
        
        Webhook savedWebhook = webhookCaptor.getValue();
        assertFalse(savedWebhook.getActive());
    }

    @Test
    @DisplayName("Should throw exception when setting active status for non-existent webhook")
    void setWebhookActive_NonExistentId_ThrowsException() {
        // Arrange
        when(webhookRepository.findById(anyLong())).thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, 
                () -> webhookService.setWebhookActive(1L, false));
        
        assertTrue(exception.getMessage().contains("not found"));
        verify(webhookRepository).findById(1L);
        verify(webhookRepository, never()).save(any(Webhook.class));
    }
}