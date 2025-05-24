package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.WebhookConfigurationDTO;
import com.dollarfunding.mca.dto.WebhookDeliveryStatusDTO;
import com.dollarfunding.mca.dto.WebhookTestResultDTO;
import com.dollarfunding.mca.service.WebhookService;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentMatchers;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import javax.persistence.EntityNotFoundException;
import java.time.LocalDateTime;
import java.util.*;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit and integration tests for the WebhookController class.
 * <p>
 * Tests verify CRUD operations for webhook configurations, role-based access control,
 * webhook testing functionality, and delivery status tracking.
 * </p>
 */
@ExtendWith(SpringExtension.class)
@WebMvcTest(WebhookController.class)
public class WebhookControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private WebhookService webhookService;

    private MockMvc mockMvc;

    private WebhookConfigurationDTO webhookConfigDTO;
    private WebhookDeliveryStatusDTO deliveryStatusDTO;
    private WebhookTestResultDTO testResultDTO;

    @BeforeEach
    public void setup() {
        mockMvc = MockMvcBuilders
                .webAppContextSetup(context)
                .apply(springSecurity())
                .build();

        // Setup test data
        webhookConfigDTO = createWebhookConfigDTO();
        deliveryStatusDTO = createDeliveryStatusDTO();
        testResultDTO = createTestResultDTO();
    }

    /**
     * Creates a sample WebhookConfigurationDTO for testing.
     *
     * @return A sample webhook configuration
     */
    private WebhookConfigurationDTO createWebhookConfigDTO() {
        WebhookConfigurationDTO dto = new WebhookConfigurationDTO();
        dto.setId("webhook-123");
        dto.setName("Test Webhook");
        dto.setUrl("https://example.com/webhook");
        dto.setEventTypes(Arrays.asList("application.created", "application.updated"));
        dto.setActive(true);
        dto.setSecretKey("test-secret-key");
        dto.setDescription("Test webhook for unit tests");
        dto.setCreatedAt(LocalDateTime.now());
        dto.setUpdatedAt(LocalDateTime.now());
        dto.setHeaders(Map.of("X-Custom-Header", "custom-value"));
        return dto;
    }

    /**
     * Creates a sample WebhookDeliveryStatusDTO for testing.
     *
     * @return A sample webhook delivery status
     */
    private WebhookDeliveryStatusDTO createDeliveryStatusDTO() {
        WebhookDeliveryStatusDTO dto = new WebhookDeliveryStatusDTO();
        dto.setId("delivery-123");
        dto.setWebhookConfigurationId("webhook-123");
        dto.setEventType("application.created");
        dto.setUrl("https://example.com/webhook");
        dto.setRequestPayload("{\"id\":\"app-123\",\"status\":\"created\"}");
        dto.setResponseStatus(200);
        dto.setResponseBody("{\"success\":true}");
        dto.setDeliveryTime(LocalDateTime.now());
        dto.setSuccess(true);
        dto.setRetryCount(0);
        dto.setNextRetryTime(null);
        return dto;
    }

    /**
     * Creates a sample WebhookTestResultDTO for testing.
     *
     * @return A sample webhook test result
     */
    private WebhookTestResultDTO createTestResultDTO() {
        WebhookTestResultDTO dto = new WebhookTestResultDTO();
        dto.setSuccess(true);
        dto.setStatusCode(200);
        dto.setResponseBody("{\"success\":true}");
        dto.setResponseTime(150L); // 150ms
        dto.setMessage("Webhook test successful");
        dto.setTimestamp(LocalDateTime.now());
        return dto;
    }

    @Test
    @DisplayName("Should return 403 when user is not authenticated")
    public void shouldReturn403WhenNotAuthenticated() throws Exception {
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Should return 403 when user does not have SYSTEM_ADMIN role")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    public void shouldReturn403WhenNotAuthorized() throws Exception {
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Should return all webhook configurations")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldReturnAllWebhookConfigurations() throws Exception {
        List<WebhookConfigurationDTO> webhooks = Arrays.asList(webhookConfigDTO);
        when(webhookService.getAllWebhookConfigurations()).thenReturn(webhooks);

        mockMvc.perform(get("/api/v1/webhooks")
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", is(webhookConfigDTO.getId())))
                .andExpect(jsonPath("$[0].name", is(webhookConfigDTO.getName())))
                .andExpect(jsonPath("$[0].url", is(webhookConfigDTO.getUrl())))
                .andExpect(jsonPath("$[0].active", is(webhookConfigDTO.isActive())));

        verify(webhookService, times(1)).getAllWebhookConfigurations();
    }

    @Test
    @DisplayName("Should return webhook configuration by ID")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldReturnWebhookConfigurationById() throws Exception {
        when(webhookService.getWebhookConfigurationById(webhookConfigDTO.getId()))
                .thenReturn(Optional.of(webhookConfigDTO));

        mockMvc.perform(get("/api/v1/webhooks/{id}", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is(webhookConfigDTO.getId())))
                .andExpect(jsonPath("$.name", is(webhookConfigDTO.getName())))
                .andExpect(jsonPath("$.url", is(webhookConfigDTO.getUrl())))
                .andExpect(jsonPath("$.active", is(webhookConfigDTO.isActive())));

        verify(webhookService, times(1)).getWebhookConfigurationById(webhookConfigDTO.getId());
    }

    @Test
    @DisplayName("Should return 404 when webhook configuration is not found")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldReturn404WhenWebhookConfigurationNotFound() throws Exception {
        when(webhookService.getWebhookConfigurationById("non-existent-id"))
                .thenReturn(Optional.empty());

        mockMvc.perform(get("/api/v1/webhooks/{id}", "non-existent-id")
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isNotFound());

        verify(webhookService, times(1)).getWebhookConfigurationById("non-existent-id");
    }

    @Test
    @DisplayName("Should create webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldCreateWebhookConfiguration() throws Exception {
        when(webhookService.createWebhookConfiguration(any(WebhookConfigurationDTO.class)))
                .thenReturn(webhookConfigDTO);

        mockMvc.perform(post("/api/v1/webhooks")
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(webhookConfigDTO)))
                .andExpect(status().isCreated())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is(webhookConfigDTO.getId())))
                .andExpect(jsonPath("$.name", is(webhookConfigDTO.getName())))
                .andExpect(jsonPath("$.url", is(webhookConfigDTO.getUrl())))
                .andExpect(jsonPath("$.active", is(webhookConfigDTO.isActive())));

        verify(webhookService, times(1)).createWebhookConfiguration(any(WebhookConfigurationDTO.class));
    }

    @Test
    @DisplayName("Should update webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldUpdateWebhookConfiguration() throws Exception {
        when(webhookService.updateWebhookConfiguration(eq(webhookConfigDTO.getId()), any(WebhookConfigurationDTO.class)))
                .thenReturn(webhookConfigDTO);

        mockMvc.perform(put("/api/v1/webhooks/{id}", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(webhookConfigDTO)))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is(webhookConfigDTO.getId())))
                .andExpect(jsonPath("$.name", is(webhookConfigDTO.getName())))
                .andExpect(jsonPath("$.url", is(webhookConfigDTO.getUrl())))
                .andExpect(jsonPath("$.active", is(webhookConfigDTO.isActive())));

        verify(webhookService, times(1)).updateWebhookConfiguration(
                eq(webhookConfigDTO.getId()), any(WebhookConfigurationDTO.class));
    }

    @Test
    @DisplayName("Should handle EntityNotFoundException when updating non-existent webhook")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldHandleEntityNotFoundExceptionWhenUpdating() throws Exception {
        when(webhookService.updateWebhookConfiguration(eq("non-existent-id"), any(WebhookConfigurationDTO.class)))
                .thenThrow(new EntityNotFoundException("Webhook configuration not found"));

        mockMvc.perform(put("/api/v1/webhooks/{id}", "non-existent-id")
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(webhookConfigDTO)))
                .andExpect(status().isNotFound());

        verify(webhookService, times(1)).updateWebhookConfiguration(
                eq("non-existent-id"), any(WebhookConfigurationDTO.class));
    }

    @Test
    @DisplayName("Should delete webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldDeleteWebhookConfiguration() throws Exception {
        doNothing().when(webhookService).deleteWebhookConfiguration(webhookConfigDTO.getId());

        mockMvc.perform(delete("/api/v1/webhooks/{id}", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isNoContent());

        verify(webhookService, times(1)).deleteWebhookConfiguration(webhookConfigDTO.getId());
    }

    @Test
    @DisplayName("Should handle EntityNotFoundException when deleting non-existent webhook")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldHandleEntityNotFoundExceptionWhenDeleting() throws Exception {
        doThrow(new EntityNotFoundException("Webhook configuration not found"))
                .when(webhookService).deleteWebhookConfiguration("non-existent-id");

        mockMvc.perform(delete("/api/v1/webhooks/{id}", "non-existent-id")
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isNotFound());

        verify(webhookService, times(1)).deleteWebhookConfiguration("non-existent-id");
    }

    @Test
    @DisplayName("Should test webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldTestWebhookConfiguration() throws Exception {
        when(webhookService.testWebhookConfiguration(webhookConfigDTO.getId()))
                .thenReturn(testResultDTO);

        mockMvc.perform(post("/api/v1/webhooks/{id}/test", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.success", is(testResultDTO.isSuccess())))
                .andExpect(jsonPath("$.statusCode", is(testResultDTO.getStatusCode())))
                .andExpect(jsonPath("$.responseBody", is(testResultDTO.getResponseBody())))
                .andExpect(jsonPath("$.responseTime", is(testResultDTO.getResponseTime().intValue())))
                .andExpect(jsonPath("$.message", is(testResultDTO.getMessage())));

        verify(webhookService, times(1)).testWebhookConfiguration(webhookConfigDTO.getId());
    }

    @Test
    @DisplayName("Should validate webhook URL")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldValidateWebhookUrl() throws Exception {
        String url = "https://example.com/webhook";
        Map<String, String> request = Map.of("url", url);
        when(webhookService.validateWebhookUrl(url)).thenReturn(true);

        mockMvc.perform(post("/api/v1/webhooks/validate-url")
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.valid", is(true)));

        verify(webhookService, times(1)).validateWebhookUrl(url);
    }

    @Test
    @DisplayName("Should regenerate secret key")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldRegenerateSecretKey() throws Exception {
        String newSecretKey = "new-secret-key";
        when(webhookService.generateHmacSecretKey(webhookConfigDTO.getId()))
                .thenReturn(newSecretKey);

        mockMvc.perform(post("/api/v1/webhooks/{id}/regenerate-secret", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.secretKey", is(newSecretKey)));

        verify(webhookService, times(1)).generateHmacSecretKey(webhookConfigDTO.getId());
    }

    @Test
    @DisplayName("Should get delivery status history")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldGetDeliveryStatusHistory() throws Exception {
        List<WebhookDeliveryStatusDTO> statusHistory = Arrays.asList(deliveryStatusDTO);
        when(webhookService.getWebhookDeliveryStatusHistory(eq(webhookConfigDTO.getId()), anyInt()))
                .thenReturn(statusHistory);

        mockMvc.perform(get("/api/v1/webhooks/{id}/delivery-status", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .param("limit", "10"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", is(deliveryStatusDTO.getId())))
                .andExpect(jsonPath("$[0].webhookConfigurationId", is(deliveryStatusDTO.getWebhookConfigurationId())))
                .andExpect(jsonPath("$[0].eventType", is(deliveryStatusDTO.getEventType())))
                .andExpect(jsonPath("$[0].success", is(deliveryStatusDTO.isSuccess())));

        verify(webhookService, times(1)).getWebhookDeliveryStatusHistory(eq(webhookConfigDTO.getId()), anyInt());
    }

    @Test
    @DisplayName("Should deliver webhook")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldDeliverWebhook() throws Exception {
        Map<String, Object> payload = Map.of(
                "id", "app-123",
                "status", "created"
        );

        when(webhookService.deliverWebhookEventToEndpoint(eq(webhookConfigDTO.getId()), ArgumentMatchers.<Map<String, Object>>any()))
                .thenReturn(deliveryStatusDTO);

        mockMvc.perform(post("/api/v1/webhooks/{id}/deliver", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is(deliveryStatusDTO.getId())))
                .andExpect(jsonPath("$.webhookConfigurationId", is(deliveryStatusDTO.getWebhookConfigurationId())))
                .andExpect(jsonPath("$.eventType", is(deliveryStatusDTO.getEventType())))
                .andExpect(jsonPath("$.success", is(deliveryStatusDTO.isSuccess())));

        verify(webhookService, times(1)).deliverWebhookEventToEndpoint(
                eq(webhookConfigDTO.getId()), ArgumentMatchers.<Map<String, Object>>any());
    }

    @Test
    @DisplayName("Should get failed deliveries")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldGetFailedDeliveries() throws Exception {
        // Create a failed delivery status
        WebhookDeliveryStatusDTO failedDelivery = createDeliveryStatusDTO();
        failedDelivery.setSuccess(false);
        failedDelivery.setResponseStatus(500);
        failedDelivery.setRetryCount(2);
        failedDelivery.setNextRetryTime(LocalDateTime.now().plusMinutes(5));

        List<WebhookDeliveryStatusDTO> failedDeliveries = Arrays.asList(failedDelivery);
        when(webhookService.getFailedWebhookDeliveriesForRetry()).thenReturn(failedDeliveries);

        mockMvc.perform(get("/api/v1/webhooks/failed-deliveries")
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", is(failedDelivery.getId())))
                .andExpect(jsonPath("$[0].success", is(false)))
                .andExpect(jsonPath("$[0].retryCount", is(2)));

        verify(webhookService, times(1)).getFailedWebhookDeliveriesForRetry();
    }

    @Test
    @DisplayName("Should retry delivery")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldRetryDelivery() throws Exception {
        String deliveryId = "delivery-123";
        when(webhookService.retryWebhookDelivery(deliveryId)).thenReturn(deliveryStatusDTO);

        mockMvc.perform(post("/api/v1/webhooks/retry/{deliveryId}", deliveryId)
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is(deliveryStatusDTO.getId())))
                .andExpect(jsonPath("$.webhookConfigurationId", is(deliveryStatusDTO.getWebhookConfigurationId())))
                .andExpect(jsonPath("$.success", is(deliveryStatusDTO.isSuccess())));

        verify(webhookService, times(1)).retryWebhookDelivery(deliveryId);
    }

    @Test
    @DisplayName("Should handle IllegalArgumentException when retrying non-failed delivery")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldHandleIllegalArgumentExceptionWhenRetrying() throws Exception {
        String deliveryId = "delivery-123";
        when(webhookService.retryWebhookDelivery(deliveryId))
                .thenThrow(new IllegalArgumentException("Delivery is not in a failed state"));

        mockMvc.perform(post("/api/v1/webhooks/retry/{deliveryId}", deliveryId)
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isBadRequest());

        verify(webhookService, times(1)).retryWebhookDelivery(deliveryId);
    }

    @Test
    @DisplayName("Should schedule retries")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldScheduleRetries() throws Exception {
        when(webhookService.scheduleWebhookRetries()).thenReturn(5);

        mockMvc.perform(post("/api/v1/webhooks/schedule-retries")
                        .with(SecurityMockMvcRequestPostProcessors.csrf()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.scheduledRetries", is(5)));

        verify(webhookService, times(1)).scheduleWebhookRetries();
    }

    @Test
    @DisplayName("Should purge old statuses")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldPurgeOldStatuses() throws Exception {
        when(webhookService.purgeOldWebhookDeliveryStatuses(30)).thenReturn(10);

        mockMvc.perform(post("/api/v1/webhooks/purge-old-statuses")
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .param("retentionDays", "30"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.purgedRecords", is(10)));

        verify(webhookService, times(1)).purgeOldWebhookDeliveryStatuses(30);
    }

    @Test
    @DisplayName("Should handle validation errors when creating webhook")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldHandleValidationErrorsWhenCreating() throws Exception {
        // Create an invalid webhook configuration (missing required fields)
        WebhookConfigurationDTO invalidWebhook = new WebhookConfigurationDTO();
        // URL is required but not set

        mockMvc.perform(post("/api/v1/webhooks")
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(invalidWebhook)))
                .andExpect(status().isBadRequest());

        verify(webhookService, never()).createWebhookConfiguration(any(WebhookConfigurationDTO.class));
    }

    @Test
    @DisplayName("Should handle validation errors when updating webhook")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldHandleValidationErrorsWhenUpdating() throws Exception {
        // Create an invalid webhook configuration (missing required fields)
        WebhookConfigurationDTO invalidWebhook = new WebhookConfigurationDTO();
        // URL is required but not set

        mockMvc.perform(put("/api/v1/webhooks/{id}", webhookConfigDTO.getId())
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(invalidWebhook)))
                .andExpect(status().isBadRequest());

        verify(webhookService, never()).updateWebhookConfiguration(anyString(), any(WebhookConfigurationDTO.class));
    }

    @Test
    @DisplayName("Should handle IllegalArgumentException when creating webhook")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    public void shouldHandleIllegalArgumentExceptionWhenCreating() throws Exception {
        when(webhookService.createWebhookConfiguration(any(WebhookConfigurationDTO.class)))
                .thenThrow(new IllegalArgumentException("Invalid webhook configuration"));

        mockMvc.perform(post("/api/v1/webhooks")
                        .with(SecurityMockMvcRequestPostProcessors.csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(webhookConfigDTO)))
                .andExpect(status().isBadRequest());

        verify(webhookService, times(1)).createWebhookConfiguration(any(WebhookConfigurationDTO.class));
    }
}