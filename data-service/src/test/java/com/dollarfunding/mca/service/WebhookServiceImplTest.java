package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.WebhookConfigurationDTO;
import com.dollarfunding.mca.dto.WebhookDeliveryStatusDTO;
import com.dollarfunding.mca.dto.WebhookResponseDTO;
import com.dollarfunding.mca.dto.WebhookTestResultDTO;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.repository.WebhookRepository;
import com.dollarfunding.mca.service.WebhookServiceImpl.WebhookDeliveryStatusDTO.Builder;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the WebhookServiceImpl class.
 * <p>
 * These tests verify the functionality of the WebhookServiceImpl class, which manages
 * webhook configurations, delivery, and status tracking for the MCA application.
 * </p>
 */
@ExtendWith(MockitoExtension.class)
public class WebhookServiceImplTest {

    @Mock
    private WebhookRepository webhookRepository;

    @Mock
    private RestTemplate restTemplate;

    @Mock
    private Executor asyncExecutor;

    @InjectMocks
    private WebhookServiceImpl webhookService;

    @Captor
    private ArgumentCaptor<Webhook> webhookCaptor;

    @Captor
    private ArgumentCaptor<HttpEntity<String>> httpEntityCaptor;

    private Webhook testWebhook;
    private WebhookConfigurationDTO testWebhookDTO;
    private Map<String, Object> testPayload;

    @BeforeEach
    void setUp() {
        // Set up default configuration values
        ReflectionTestUtils.setField(webhookService, "asyncDelivery", true);
        ReflectionTestUtils.setField(webhookService, "connectTimeoutMs", 5000);
        ReflectionTestUtils.setField(webhookService, "readTimeoutMs", 10000);
        ReflectionTestUtils.setField(webhookService, "initialRetryDelayMs", 1000);
        ReflectionTestUtils.setField(webhookService, "maxRetryDelayMs", 60000);
        ReflectionTestUtils.setField(webhookService, "backoffMultiplier", 2);

        // Create test webhook entity
        testWebhook = new Webhook();
        testWebhook.setId(1L);
        testWebhook.setEndpointUrl("https://example.com/webhook");
        testWebhook.setSecretKey("secretKey123456789012345678901234567890");
        testWebhook.setActive(true);
        testWebhook.setEventType(EventType.APPLICATION_CREATED);
        testWebhook.setMaxRetryAttempts(3);
        testWebhook.setDescription("Test webhook");

        // Create test webhook DTO
        testWebhookDTO = new WebhookConfigurationDTO() {
            @Override
            public String getEndpointUrl() {
                return "https://example.com/webhook";
            }

            @Override
            public String getSecretKey() {
                return "secretKey123456789012345678901234567890";
            }

            @Override
            public Boolean getActive() {
                return true;
            }

            @Override
            public EventType getEventType() {
                return EventType.APPLICATION_CREATED;
            }

            @Override
            public Integer getMaxRetryAttempts() {
                return 3;
            }

            @Override
            public String getDescription() {
                return "Test webhook";
            }

            @Override
            public String getSignatureHeader() {
                return "X-Webhook-Signature";
            }
        };

        // Create test payload
        testPayload = new HashMap<>();
        testPayload.put("event_type", "APPLICATION_CREATED");
        testPayload.put("event_id", "evt_12345");
        testPayload.put("timestamp", System.currentTimeMillis());
        testPayload.put("data", Map.of(
                "application_id", "app_12345",
                "status", "PENDING",
                "merchant", Map.of(
                        "legal_name", "Example Business LLC",
                        "dba_name", "Example Business",
                        "industry", "Retail"
                )
        ));

        // Mock WebhookResponseDTO.fromEntity
        mockStatic(WebhookResponseDTO.class);
        when(WebhookResponseDTO.fromEntity(any(Webhook.class))).thenAnswer(invocation -> {
            Webhook webhook = invocation.getArgument(0);
            return new WebhookConfigurationDTO() {
                @Override
                public String getEndpointUrl() {
                    return webhook.getEndpointUrl();
                }

                @Override
                public String getSecretKey() {
                    return webhook.getSecretKey();
                }

                @Override
                public Boolean getActive() {
                    return webhook.getActive();
                }

                @Override
                public EventType getEventType() {
                    return webhook.getEventType();
                }

                @Override
                public Integer getMaxRetryAttempts() {
                    return webhook.getMaxRetryAttempts();
                }

                @Override
                public String getDescription() {
                    return webhook.getDescription();
                }

                @Override
                public String getSignatureHeader() {
                    return webhook.getSignatureHeader();
                }
            };
        });
    }

    /**
     * Tests for webhook configuration CRUD operations.
     */
    @Nested
    @DisplayName("Webhook Configuration CRUD Tests")
    class WebhookConfigurationCrudTests {

        @Test
        @DisplayName("Should create a webhook configuration successfully")
        void shouldCreateWebhookConfiguration() {
            // Given
            when(webhookRepository.existsByEndpointUrl(anyString())).thenReturn(false);
            when(webhookRepository.save(any(Webhook.class))).thenAnswer(invocation -> {
                Webhook webhook = invocation.getArgument(0);
                webhook.setId(1L);
                return webhook;
            });

            // When
            WebhookConfigurationDTO result = webhookService.createWebhookConfiguration(testWebhookDTO);

            // Then
            verify(webhookRepository).existsByEndpointUrl(testWebhookDTO.getEndpointUrl());
            verify(webhookRepository).save(webhookCaptor.capture());

            Webhook capturedWebhook = webhookCaptor.getValue();
            assertEquals(testWebhookDTO.getEndpointUrl(), capturedWebhook.getEndpointUrl());
            assertEquals(testWebhookDTO.getSecretKey(), capturedWebhook.getSecretKey());
            assertEquals(testWebhookDTO.getActive(), capturedWebhook.getActive());
            assertEquals(testWebhookDTO.getEventType(), capturedWebhook.getEventType());
            assertEquals(testWebhookDTO.getMaxRetryAttempts(), capturedWebhook.getMaxRetryAttempts());
            assertEquals(testWebhookDTO.getDescription(), capturedWebhook.getDescription());

            assertNotNull(result);
            assertEquals(testWebhookDTO.getEndpointUrl(), result.getEndpointUrl());
        }

        @Test
        @DisplayName("Should throw exception when creating webhook with existing endpoint URL")
        void shouldThrowExceptionWhenCreatingWebhookWithExistingEndpointUrl() {
            // Given
            when(webhookRepository.existsByEndpointUrl(anyString())).thenReturn(true);

            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.createWebhookConfiguration(testWebhookDTO));

            assertTrue(exception.getMessage().contains("already exists"));
            verify(webhookRepository).existsByEndpointUrl(testWebhookDTO.getEndpointUrl());
            verify(webhookRepository, never()).save(any(Webhook.class));
        }

        @Test
        @DisplayName("Should throw exception when creating webhook with invalid configuration")
        void shouldThrowExceptionWhenCreatingWebhookWithInvalidConfiguration() {
            // Given
            WebhookConfigurationDTO invalidDTO = new WebhookConfigurationDTO() {
                @Override
                public String getEndpointUrl() {
                    return "invalid-url";
                }

                @Override
                public String getSecretKey() {
                    return "short";
                }

                @Override
                public Boolean getActive() {
                    return true;
                }

                @Override
                public EventType getEventType() {
                    return EventType.APPLICATION_CREATED;
                }

                @Override
                public Integer getMaxRetryAttempts() {
                    return 3;
                }

                @Override
                public String getDescription() {
                    return "Test webhook";
                }

                @Override
                public String getSignatureHeader() {
                    return "X-Webhook-Signature";
                }
            };

            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.createWebhookConfiguration(invalidDTO));

            assertTrue(exception.getMessage().contains("HTTPS protocol"));
            verify(webhookRepository, never()).existsByEndpointUrl(anyString());
            verify(webhookRepository, never()).save(any(Webhook.class));
        }

        @Test
        @DisplayName("Should get webhook configuration by ID successfully")
        void shouldGetWebhookConfigurationById() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));

            // When
            Optional<WebhookConfigurationDTO> result = webhookService.getWebhookConfigurationById("1");

            // Then
            assertTrue(result.isPresent());
            assertEquals(testWebhook.getEndpointUrl(), result.get().getEndpointUrl());
            verify(webhookRepository).findById(1L);
        }

        @Test
        @DisplayName("Should return empty when getting webhook with non-existent ID")
        void shouldReturnEmptyWhenGettingWebhookWithNonExistentId() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.empty());

            // When
            Optional<WebhookConfigurationDTO> result = webhookService.getWebhookConfigurationById("1");

            // Then
            assertFalse(result.isPresent());
            verify(webhookRepository).findById(1L);
        }

        @Test
        @DisplayName("Should return empty when getting webhook with invalid ID format")
        void shouldReturnEmptyWhenGettingWebhookWithInvalidIdFormat() {
            // When
            Optional<WebhookConfigurationDTO> result = webhookService.getWebhookConfigurationById("invalid");

            // Then
            assertFalse(result.isPresent());
            verify(webhookRepository, never()).findById(anyLong());
        }

        @Test
        @DisplayName("Should get all webhook configurations successfully")
        void shouldGetAllWebhookConfigurations() {
            // Given
            Webhook webhook1 = new Webhook();
            webhook1.setId(1L);
            webhook1.setEndpointUrl("https://example.com/webhook1");
            webhook1.setSecretKey("secretKey1");
            webhook1.setActive(true);
            webhook1.setEventType(EventType.APPLICATION_CREATED);

            Webhook webhook2 = new Webhook();
            webhook2.setId(2L);
            webhook2.setEndpointUrl("https://example.com/webhook2");
            webhook2.setSecretKey("secretKey2");
            webhook2.setActive(false);
            webhook2.setEventType(EventType.APPLICATION_UPDATED);

            when(webhookRepository.findAll()).thenReturn(Arrays.asList(webhook1, webhook2));

            // When
            List<WebhookConfigurationDTO> result = webhookService.getAllWebhookConfigurations();

            // Then
            assertEquals(2, result.size());
            assertEquals(webhook1.getEndpointUrl(), result.get(0).getEndpointUrl());
            assertEquals(webhook2.getEndpointUrl(), result.get(1).getEndpointUrl());
            verify(webhookRepository).findAll();
        }

        @Test
        @DisplayName("Should update webhook configuration successfully")
        void shouldUpdateWebhookConfiguration() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(webhookRepository.existsByEndpointUrl(anyString())).thenReturn(false);
            when(webhookRepository.save(any(Webhook.class))).thenAnswer(invocation -> invocation.getArgument(0));

            WebhookConfigurationDTO updatedDTO = new WebhookConfigurationDTO() {
                @Override
                public String getEndpointUrl() {
                    return "https://example.com/updated";
                }

                @Override
                public String getSecretKey() {
                    return "updatedSecretKey123456789012345678901234567890";
                }

                @Override
                public Boolean getActive() {
                    return false;
                }

                @Override
                public EventType getEventType() {
                    return EventType.APPLICATION_UPDATED;
                }

                @Override
                public Integer getMaxRetryAttempts() {
                    return 5;
                }

                @Override
                public String getDescription() {
                    return "Updated description";
                }

                @Override
                public String getSignatureHeader() {
                    return "X-Updated-Signature";
                }
            };

            // When
            WebhookConfigurationDTO result = webhookService.updateWebhookConfiguration("1", updatedDTO);

            // Then
            verify(webhookRepository).findById(1L);
            verify(webhookRepository).existsByEndpointUrl(updatedDTO.getEndpointUrl());
            verify(webhookRepository).save(webhookCaptor.capture());

            Webhook capturedWebhook = webhookCaptor.getValue();
            assertEquals(updatedDTO.getEndpointUrl(), capturedWebhook.getEndpointUrl());
            assertEquals(updatedDTO.getSecretKey(), capturedWebhook.getSecretKey());
            assertEquals(updatedDTO.getActive(), capturedWebhook.getActive());
            assertEquals(updatedDTO.getEventType(), capturedWebhook.getEventType());
            assertEquals(updatedDTO.getMaxRetryAttempts(), capturedWebhook.getMaxRetryAttempts());
            assertEquals(updatedDTO.getDescription(), capturedWebhook.getDescription());
            assertEquals(updatedDTO.getSignatureHeader(), capturedWebhook.getSignatureHeader());

            assertNotNull(result);
            assertEquals(updatedDTO.getEndpointUrl(), result.getEndpointUrl());
        }

        @Test
        @DisplayName("Should throw exception when updating webhook with non-existent ID")
        void shouldThrowExceptionWhenUpdatingWebhookWithNonExistentId() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.empty());

            // When/Then
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () ->
                    webhookService.updateWebhookConfiguration("1", testWebhookDTO));

            assertTrue(exception.getMessage().contains("not found"));
            verify(webhookRepository).findById(1L);
            verify(webhookRepository, never()).save(any(Webhook.class));
        }

        @Test
        @DisplayName("Should throw exception when updating webhook with invalid ID format")
        void shouldThrowExceptionWhenUpdatingWebhookWithInvalidIdFormat() {
            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.updateWebhookConfiguration("invalid", testWebhookDTO));

            assertTrue(exception.getMessage().contains("Invalid webhook ID format"));
            verify(webhookRepository, never()).findById(anyLong());
            verify(webhookRepository, never()).save(any(Webhook.class));
        }

        @Test
        @DisplayName("Should throw exception when updating webhook with existing endpoint URL")
        void shouldThrowExceptionWhenUpdatingWebhookWithExistingEndpointUrl() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(webhookRepository.existsByEndpointUrl(anyString())).thenReturn(true);

            WebhookConfigurationDTO updatedDTO = new WebhookConfigurationDTO() {
                @Override
                public String getEndpointUrl() {
                    return "https://example.com/existing";
                }

                @Override
                public String getSecretKey() {
                    return "secretKey123456789012345678901234567890";
                }

                @Override
                public Boolean getActive() {
                    return true;
                }

                @Override
                public EventType getEventType() {
                    return EventType.APPLICATION_CREATED;
                }

                @Override
                public Integer getMaxRetryAttempts() {
                    return 3;
                }

                @Override
                public String getDescription() {
                    return "Test webhook";
                }

                @Override
                public String getSignatureHeader() {
                    return "X-Webhook-Signature";
                }
            };

            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.updateWebhookConfiguration("1", updatedDTO));

            assertTrue(exception.getMessage().contains("already exists"));
            verify(webhookRepository).findById(1L);
            verify(webhookRepository).existsByEndpointUrl(updatedDTO.getEndpointUrl());
            verify(webhookRepository, never()).save(any(Webhook.class));
        }

        @Test
        @DisplayName("Should delete webhook configuration successfully")
        void shouldDeleteWebhookConfiguration() {
            // Given
            when(webhookRepository.existsById(1L)).thenReturn(true);
            doNothing().when(webhookRepository).deleteById(1L);

            // When
            webhookService.deleteWebhookConfiguration("1");

            // Then
            verify(webhookRepository).existsById(1L);
            verify(webhookRepository).deleteById(1L);
        }

        @Test
        @DisplayName("Should throw exception when deleting webhook with non-existent ID")
        void shouldThrowExceptionWhenDeletingWebhookWithNonExistentId() {
            // Given
            when(webhookRepository.existsById(1L)).thenReturn(false);

            // When/Then
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () ->
                    webhookService.deleteWebhookConfiguration("1"));

            assertTrue(exception.getMessage().contains("not found"));
            verify(webhookRepository).existsById(1L);
            verify(webhookRepository, never()).deleteById(anyLong());
        }

        @Test
        @DisplayName("Should throw exception when deleting webhook with invalid ID format")
        void shouldThrowExceptionWhenDeletingWebhookWithInvalidIdFormat() {
            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.deleteWebhookConfiguration("invalid"));

            assertTrue(exception.getMessage().contains("Invalid webhook ID format"));
            verify(webhookRepository, never()).existsById(anyLong());
            verify(webhookRepository, never()).deleteById(anyLong());
        }
    }

    /**
     * Tests for webhook delivery functionality.
     */
    @Nested
    @DisplayName("Webhook Delivery Tests")
    class WebhookDeliveryTests {

        @Test
        @DisplayName("Should deliver webhook event to all configured endpoints successfully")
        void shouldDeliverWebhookEventToAllConfiguredEndpoints() {
            // Given
            Webhook webhook1 = new Webhook();
            webhook1.setId(1L);
            webhook1.setEndpointUrl("https://example.com/webhook1");
            webhook1.setSecretKey("secretKey1");
            webhook1.setActive(true);
            webhook1.setEventType(EventType.APPLICATION_CREATED);

            Webhook webhook2 = new Webhook();
            webhook2.setId(2L);
            webhook2.setEndpointUrl("https://example.com/webhook2");
            webhook2.setSecretKey("secretKey2");
            webhook2.setActive(true);
            webhook2.setEventType(EventType.APPLICATION_CREATED);

            when(webhookRepository.findByEventTypeAndActive(EventType.APPLICATION_CREATED, true))
                    .thenReturn(Arrays.asList(webhook1, webhook2));

            // Mock async delivery
            doAnswer(invocation -> {
                Runnable runnable = invocation.getArgument(0);
                runnable.run();
                return null;
            }).when(asyncExecutor).execute(any(Runnable.class));

            // When
            List<WebhookDeliveryStatusDTO> results = webhookService.deliverWebhookEvent("APPLICATION_CREATED", testPayload);

            // Then
            assertEquals(2, results.size());
            assertEquals("1", results.get(0).getWebhookId());
            assertEquals("2", results.get(1).getWebhookId());
            assertEquals("PENDING", results.get(0).getStatus());
            assertEquals("PENDING", results.get(1).getStatus());
            verify(webhookRepository).findByEventTypeAndActive(EventType.APPLICATION_CREATED, true);
        }

        @Test
        @DisplayName("Should return empty list when no webhooks are configured for event type")
        void shouldReturnEmptyListWhenNoWebhooksAreConfiguredForEventType() {
            // Given
            when(webhookRepository.findByEventTypeAndActive(EventType.APPLICATION_CREATED, true))
                    .thenReturn(Collections.emptyList());

            // When
            List<WebhookDeliveryStatusDTO> results = webhookService.deliverWebhookEvent("APPLICATION_CREATED", testPayload);

            // Then
            assertTrue(results.isEmpty());
            verify(webhookRepository).findByEventTypeAndActive(EventType.APPLICATION_CREATED, true);
        }

        @Test
        @DisplayName("Should return empty list when event type is invalid")
        void shouldReturnEmptyListWhenEventTypeIsInvalid() {
            // When
            List<WebhookDeliveryStatusDTO> results = webhookService.deliverWebhookEvent("INVALID_EVENT_TYPE", testPayload);

            // Then
            assertTrue(results.isEmpty());
            verify(webhookRepository, never()).findByEventTypeAndActive(any(EventType.class), anyBoolean());
        }

        @Test
        @DisplayName("Should deliver webhook event to specific endpoint successfully")
        void shouldDeliverWebhookEventToSpecificEndpoint() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(restTemplate.postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class)))
                    .thenReturn(new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK));

            // When
            WebhookDeliveryStatusDTO result = webhookService.deliverWebhookEventToEndpoint("1", testPayload);

            // Then
            assertNotNull(result);
            assertEquals("1", result.getWebhookId());
            assertEquals("SUCCESS", result.getStatus());
            assertEquals(200, result.getStatusCode());
            verify(webhookRepository).findById(1L);
            verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), httpEntityCaptor.capture(), eq(String.class));

            // Verify HMAC signature
            HttpEntity<String> capturedEntity = httpEntityCaptor.getValue();
            assertNotNull(capturedEntity.getHeaders().get("X-Webhook-Signature"));
            assertNotNull(capturedEntity.getBody());
        }

        @Test
        @DisplayName("Should handle webhook delivery failure correctly")
        void shouldHandleWebhookDeliveryFailureCorrectly() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(restTemplate.postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class)))
                    .thenThrow(new RestClientException("Connection refused"));

            // When
            WebhookDeliveryStatusDTO result = webhookService.deliverWebhookEventToEndpoint("1", testPayload);

            // Then
            assertNotNull(result);
            assertEquals("1", result.getWebhookId());
            assertEquals("FAILED", result.getStatus());
            assertTrue(result.getMessage().contains("Connection refused"));
            assertEquals(1, result.getRetryCount());
            verify(webhookRepository).findById(1L);
            verify(webhookRepository).save(webhookCaptor.capture());

            Webhook capturedWebhook = webhookCaptor.getValue();
            assertEquals(1, capturedWebhook.getConsecutiveFailures());
            assertNotNull(capturedWebhook.getLastFailureAt());
        }

        @Test
        @DisplayName("Should deactivate webhook after maximum retry attempts")
        void shouldDeactivateWebhookAfterMaximumRetryAttempts() {
            // Given
            testWebhook.setConsecutiveFailures(2); // Already failed twice
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(restTemplate.postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class)))
                    .thenThrow(new RestClientException("Connection refused"));

            // When
            WebhookDeliveryStatusDTO result = webhookService.deliverWebhookEventToEndpoint("1", testPayload);

            // Then
            assertNotNull(result);
            assertEquals("1", result.getWebhookId());
            assertEquals("DEACTIVATED", result.getStatus());
            assertTrue(result.getMessage().contains("Connection refused"));
            assertEquals(3, result.getRetryCount());
            verify(webhookRepository).findById(1L);
            verify(webhookRepository).save(webhookCaptor.capture());

            Webhook capturedWebhook = webhookCaptor.getValue();
            assertEquals(3, capturedWebhook.getConsecutiveFailures());
            assertFalse(capturedWebhook.getActive());
            assertNotNull(capturedWebhook.getLastFailureAt());
        }

        @Test
        @DisplayName("Should skip delivery to inactive webhook")
        void shouldSkipDeliveryToInactiveWebhook() {
            // Given
            testWebhook.setActive(false);
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));

            // When
            WebhookDeliveryStatusDTO result = webhookService.deliverWebhookEventToEndpoint("1", testPayload);

            // Then
            assertNotNull(result);
            assertEquals("1", result.getWebhookId());
            assertEquals("SKIPPED", result.getStatus());
            assertTrue(result.getMessage().contains("inactive"));
            verify(webhookRepository).findById(1L);
            verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should throw exception when delivering to webhook with invalid ID format")
        void shouldThrowExceptionWhenDeliveringToWebhookWithInvalidIdFormat() {
            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.deliverWebhookEventToEndpoint("invalid", testPayload));

            assertTrue(exception.getMessage().contains("Invalid webhook ID format"));
            verify(webhookRepository, never()).findById(anyLong());
            verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should throw exception when delivering to non-existent webhook")
        void shouldThrowExceptionWhenDeliveringToNonExistentWebhook() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.empty());

            // When/Then
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () ->
                    webhookService.deliverWebhookEventToEndpoint("1", testPayload));

            assertTrue(exception.getMessage().contains("not found"));
            verify(webhookRepository).findById(1L);
            verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
        }
    }

    /**
     * Tests for webhook testing and validation functionality.
     */
    @Nested
    @DisplayName("Webhook Testing and Validation Tests")
    class WebhookTestingAndValidationTests {

        @Test
        @DisplayName("Should test webhook configuration successfully")
        void shouldTestWebhookConfigurationSuccessfully() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(restTemplate.postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class)))
                    .thenReturn(new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK));

            // When
            WebhookTestResultDTO result = webhookService.testWebhookConfiguration("1");

            // Then
            assertNotNull(result);
            assertTrue(result.isSuccess());
            assertEquals(200, result.getResponseCode());
            assertEquals("{\"status\":\"success\"}", result.getResponseBody());
            assertEquals(testWebhook.getEndpointUrl(), result.getEndpointUrl());
            assertEquals(testWebhook.getEventType().name(), result.getEventType());
            verify(webhookRepository).findById(1L);
            verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), httpEntityCaptor.capture(), eq(String.class));

            // Verify HMAC signature
            HttpEntity<String> capturedEntity = httpEntityCaptor.getValue();
            assertNotNull(capturedEntity.getHeaders().get("X-Webhook-Signature"));
            assertNotNull(capturedEntity.getBody());
        }

        @Test
        @DisplayName("Should handle webhook test failure correctly")
        void shouldHandleWebhookTestFailureCorrectly() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(restTemplate.postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class)))
                    .thenThrow(new RestClientException("Connection refused"));

            // When
            WebhookTestResultDTO result = webhookService.testWebhookConfiguration("1");

            // Then
            assertNotNull(result);
            assertFalse(result.isSuccess());
            assertEquals("Connection refused", result.getErrorMessage());
            assertEquals(testWebhook.getEndpointUrl(), result.getEndpointUrl());
            assertEquals(testWebhook.getEventType().name(), result.getEventType());
            verify(webhookRepository).findById(1L);
            verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should throw exception when testing webhook with invalid ID format")
        void shouldThrowExceptionWhenTestingWebhookWithInvalidIdFormat() {
            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.testWebhookConfiguration("invalid"));

            assertTrue(exception.getMessage().contains("Invalid webhook ID format"));
            verify(webhookRepository, never()).findById(anyLong());
            verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should throw exception when testing non-existent webhook")
        void shouldThrowExceptionWhenTestingNonExistentWebhook() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.empty());

            // When/Then
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () ->
                    webhookService.testWebhookConfiguration("1"));

            assertTrue(exception.getMessage().contains("not found"));
            verify(webhookRepository).findById(1L);
            verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should validate webhook URL successfully")
        void shouldValidateWebhookUrlSuccessfully() {
            // Given
            String validUrl = "https://example.com/webhook";
            when(restTemplate.postForEntity(eq(validUrl), any(HttpEntity.class), eq(String.class)))
                    .thenReturn(new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK));

            // When
            boolean result = webhookService.validateWebhookUrl(validUrl);

            // Then
            assertTrue(result);
            verify(restTemplate).postForEntity(eq(validUrl), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should return false when validating invalid webhook URL")
        void shouldReturnFalseWhenValidatingInvalidWebhookUrl() {
            // Given
            String invalidUrl = "http://example.com/webhook"; // Not HTTPS

            // When
            boolean result = webhookService.validateWebhookUrl(invalidUrl);

            // Then
            assertFalse(result);
            verify(restTemplate, never()).postForEntity(anyString(), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should return false when webhook URL validation fails")
        void shouldReturnFalseWhenWebhookUrlValidationFails() {
            // Given
            String validUrl = "https://example.com/webhook";
            when(restTemplate.postForEntity(eq(validUrl), any(HttpEntity.class), eq(String.class)))
                    .thenThrow(new RestClientException("Connection refused"));

            // When
            boolean result = webhookService.validateWebhookUrl(validUrl);

            // Then
            assertFalse(result);
            verify(restTemplate).postForEntity(eq(validUrl), any(HttpEntity.class), eq(String.class));
        }
    }

    /**
     * Tests for HMAC signature generation and verification.
     */
    @Nested
    @DisplayName("HMAC Signature Tests")
    class HmacSignatureTests {

        @Test
        @DisplayName("Should generate HMAC signature correctly")
        void shouldGenerateHmacSignatureCorrectly() {
            // Given
            String payload = "{\"event\":\"test\"}";
            String secretKey = "secretKey123456789012345678901234567890";

            // When
            String signature = webhookService.generateHmacSignature(payload, secretKey);

            // Then
            assertNotNull(signature);
            assertFalse(signature.isEmpty());
        }

        @Test
        @DisplayName("Should verify valid HMAC signature correctly")
        void shouldVerifyValidHmacSignatureCorrectly() {
            // Given
            String payload = "{\"event\":\"test\"}";
            String secretKey = "secretKey123456789012345678901234567890";
            String signature = webhookService.generateHmacSignature(payload, secretKey);

            // When
            boolean result = webhookService.verifyHmacSignature(payload, signature, secretKey);

            // Then
            assertTrue(result);
        }

        @Test
        @DisplayName("Should reject invalid HMAC signature")
        void shouldRejectInvalidHmacSignature() {
            // Given
            String payload = "{\"event\":\"test\"}";
            String secretKey = "secretKey123456789012345678901234567890";
            String invalidSignature = "invalidSignature";

            // When
            boolean result = webhookService.verifyHmacSignature(payload, invalidSignature, secretKey);

            // Then
            assertFalse(result);
        }

        @Test
        @DisplayName("Should generate new HMAC secret key for webhook")
        void shouldGenerateNewHmacSecretKeyForWebhook() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.of(testWebhook));
            when(webhookRepository.save(any(Webhook.class))).thenAnswer(invocation -> invocation.getArgument(0));

            // When
            String newSecretKey = webhookService.generateHmacSecretKey("1");

            // Then
            assertNotNull(newSecretKey);
            assertFalse(newSecretKey.isEmpty());
            verify(webhookRepository).findById(1L);
            verify(webhookRepository).save(webhookCaptor.capture());

            Webhook capturedWebhook = webhookCaptor.getValue();
            assertEquals(newSecretKey, capturedWebhook.getSecretKey());
        }

        @Test
        @DisplayName("Should throw exception when generating HMAC secret key for webhook with invalid ID format")
        void shouldThrowExceptionWhenGeneratingHmacSecretKeyForWebhookWithInvalidIdFormat() {
            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.generateHmacSecretKey("invalid"));

            assertTrue(exception.getMessage().contains("Invalid webhook ID format"));
            verify(webhookRepository, never()).findById(anyLong());
            verify(webhookRepository, never()).save(any(Webhook.class));
        }

        @Test
        @DisplayName("Should throw exception when generating HMAC secret key for non-existent webhook")
        void shouldThrowExceptionWhenGeneratingHmacSecretKeyForNonExistentWebhook() {
            // Given
            when(webhookRepository.findById(1L)).thenReturn(Optional.empty());

            // When/Then
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () ->
                    webhookService.generateHmacSecretKey("1"));

            assertTrue(exception.getMessage().contains("not found"));
            verify(webhookRepository).findById(1L);
            verify(webhookRepository, never()).save(any(Webhook.class));
        }
    }

    /**
     * Tests for webhook delivery status tracking and retry functionality.
     */
    @Nested
    @DisplayName("Webhook Delivery Status and Retry Tests")
    class WebhookDeliveryStatusAndRetryTests {

        @Test
        @DisplayName("Should get webhook delivery status history successfully")
        void shouldGetWebhookDeliveryStatusHistorySuccessfully() {
            // Given
            when(webhookRepository.existsById(1L)).thenReturn(true);

            // When
            List<WebhookDeliveryStatusDTO> results = webhookService.getWebhookDeliveryStatusHistory("1", 10);

            // Then
            assertNotNull(results);
            assertTrue(results.isEmpty()); // Currently returns empty list as placeholder
            verify(webhookRepository).existsById(1L);
        }

        @Test
        @DisplayName("Should throw exception when getting delivery status history for webhook with invalid ID format")
        void shouldThrowExceptionWhenGettingDeliveryStatusHistoryForWebhookWithInvalidIdFormat() {
            // When/Then
            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () ->
                    webhookService.getWebhookDeliveryStatusHistory("invalid", 10));

            assertTrue(exception.getMessage().contains("Invalid webhook ID format"));
            verify(webhookRepository, never()).existsById(anyLong());
        }

        @Test
        @DisplayName("Should throw exception when getting delivery status history for non-existent webhook")
        void shouldThrowExceptionWhenGettingDeliveryStatusHistoryForNonExistentWebhook() {
            // Given
            when(webhookRepository.existsById(1L)).thenReturn(false);

            // When/Then
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () ->
                    webhookService.getWebhookDeliveryStatusHistory("1", 10));

            assertTrue(exception.getMessage().contains("not found"));
            verify(webhookRepository).existsById(1L);
        }

        @Test
        @DisplayName("Should get failed webhook deliveries for retry successfully")
        void shouldGetFailedWebhookDeliveriesForRetrySuccessfully() {
            // Given
            Webhook webhook1 = new Webhook();
            webhook1.setId(1L);
            webhook1.setEndpointUrl("https://example.com/webhook1");
            webhook1.setSecretKey("secretKey1");
            webhook1.setActive(true);
            webhook1.setEventType(EventType.APPLICATION_CREATED);
            webhook1.setConsecutiveFailures(1);
            webhook1.setLastFailureAt(LocalDateTime.now());

            Webhook webhook2 = new Webhook();
            webhook2.setId(2L);
            webhook2.setEndpointUrl("https://example.com/webhook2");
            webhook2.setSecretKey("secretKey2");
            webhook2.setActive(true);
            webhook2.setEventType(EventType.APPLICATION_UPDATED);
            webhook2.setConsecutiveFailures(2);
            webhook2.setLastFailureAt(LocalDateTime.now());

            when(webhookRepository.findWebhooksEligibleForRetry()).thenReturn(Arrays.asList(webhook1, webhook2));

            // When
            List<WebhookDeliveryStatusDTO> results = webhookService.getFailedWebhookDeliveriesForRetry();

            // Then
            assertEquals(2, results.size());
            assertEquals("1", results.get(0).getWebhookId());
            assertEquals("2", results.get(1).getWebhookId());
            assertEquals("FAILED", results.get(0).getStatus());
            assertEquals("FAILED", results.get(1).getStatus());
            assertEquals(1, results.get(0).getRetryCount());
            assertEquals(2, results.get(1).getRetryCount());
            verify(webhookRepository).findWebhooksEligibleForRetry();
        }

        @Test
        @DisplayName("Should schedule webhook retries successfully")
        void shouldScheduleWebhookRetriesSuccessfully() {
            // Given
            Webhook webhook1 = new Webhook();
            webhook1.setId(1L);
            webhook1.setEndpointUrl("https://example.com/webhook1");
            webhook1.setSecretKey("secretKey1");
            webhook1.setActive(true);
            webhook1.setEventType(EventType.APPLICATION_CREATED);
            webhook1.setConsecutiveFailures(1);
            webhook1.setLastFailureAt(LocalDateTime.now());

            Webhook webhook2 = new Webhook();
            webhook2.setId(2L);
            webhook2.setEndpointUrl("https://example.com/webhook2");
            webhook2.setSecretKey("secretKey2");
            webhook2.setActive(true);
            webhook2.setEventType(EventType.APPLICATION_UPDATED);
            webhook2.setConsecutiveFailures(2);
            webhook2.setLastFailureAt(LocalDateTime.now());

            when(webhookRepository.findWebhooksEligibleForRetry()).thenReturn(Arrays.asList(webhook1, webhook2));

            // When
            int count = webhookService.scheduleWebhookRetries();

            // Then
            assertEquals(2, count);
            verify(webhookRepository).findWebhooksEligibleForRetry();
        }

        @Test
        @DisplayName("Should purge old webhook delivery statuses successfully")
        void shouldPurgeOldWebhookDeliveryStatusesSuccessfully() {
            // When
            int count = webhookService.purgeOldWebhookDeliveryStatuses(30);

            // Then
            assertEquals(0, count); // Currently returns 0 as placeholder
        }

        @Test
        @DisplayName("Should throw exception when retrying webhook delivery")
        void shouldThrowExceptionWhenRetryingWebhookDelivery() {
            // When/Then
            UnsupportedOperationException exception = assertThrows(UnsupportedOperationException.class, () ->
                    webhookService.retryWebhookDelivery("1"));

            assertTrue(exception.getMessage().contains("not implemented yet"));
        }
    }

    /**
     * Tests for asynchronous webhook delivery.
     */
    @Nested
    @DisplayName("Asynchronous Webhook Delivery Tests")
    class AsynchronousWebhookDeliveryTests {

        @Test
        @DisplayName("Should deliver webhook asynchronously")
        void shouldDeliverWebhookAsynchronously() {
            // Given
            ReflectionTestUtils.setField(webhookService, "asyncDelivery", true);

            when(webhookRepository.findByEventTypeAndActive(EventType.APPLICATION_CREATED, true))
                    .thenReturn(Collections.singletonList(testWebhook));

            // Mock async execution
            doAnswer(invocation -> {
                Runnable runnable = invocation.getArgument(0);
                runnable.run();
                return CompletableFuture.completedFuture(null);
            }).when(asyncExecutor).execute(any(Runnable.class));

            // Mock successful delivery
            when(restTemplate.postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class)))
                    .thenReturn(new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK));

            // When
            List<WebhookDeliveryStatusDTO> results = webhookService.deliverWebhookEvent("APPLICATION_CREATED", testPayload);

            // Then
            assertEquals(1, results.size());
            assertEquals("1", results.get(0).getWebhookId());
            assertEquals("PENDING", results.get(0).getStatus());
            verify(webhookRepository).findByEventTypeAndActive(EventType.APPLICATION_CREATED, true);
            verify(asyncExecutor).execute(any(Runnable.class));
            verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
        }

        @Test
        @DisplayName("Should deliver webhook synchronously when async is disabled")
        void shouldDeliverWebhookSynchronouslyWhenAsyncIsDisabled() {
            // Given
            ReflectionTestUtils.setField(webhookService, "asyncDelivery", false);

            when(webhookRepository.findByEventTypeAndActive(EventType.APPLICATION_CREATED, true))
                    .thenReturn(Collections.singletonList(testWebhook));

            // Mock successful delivery
            when(restTemplate.postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class)))
                    .thenReturn(new ResponseEntity<>("{\"status\":\"success\"}", HttpStatus.OK));

            // When
            List<WebhookDeliveryStatusDTO> results = webhookService.deliverWebhookEvent("APPLICATION_CREATED", testPayload);

            // Then
            assertEquals(1, results.size());
            assertEquals("1", results.get(0).getWebhookId());
            assertEquals("SUCCESS", results.get(0).getStatus());
            verify(webhookRepository).findByEventTypeAndActive(EventType.APPLICATION_CREATED, true);
            verify(asyncExecutor, never()).execute(any(Runnable.class));
            verify(restTemplate).postForEntity(eq(testWebhook.getEndpointUrl()), any(HttpEntity.class), eq(String.class));
        }
    }

    /**
     * Helper method to mock static methods.
     */
    private static <T> void mockStatic(Class<T> classToMock) {
        Mockito.mockStatic(classToMock);
    }
}