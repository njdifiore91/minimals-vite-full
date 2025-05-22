package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.WebhookConfigDto;
import com.dollarfunding.mca.dto.WebhookDeliveryStatusDTO;
import com.dollarfunding.mca.dto.WebhookTestResultDTO;
import com.dollarfunding.mca.exception.AuthorizationException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.service.WebhookService;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit and integration tests for the WebhookController class that manages webhook configurations
 * through the /api/v1/webhooks endpoint.
 * <p>
 * Tests verify CRUD operations for webhook endpoints, role-based access control (restricted to
 * System Admin role), webhook testing functionality, and delivery status tracking. Includes tests
 * for webhook configuration validation, HMAC signature configuration, and error handling.
 * </p>
 * <p>
 * Uses MockMvc to simulate HTTP requests and mock services to isolate the controller from
 * external dependencies.
 * </p>
 */
@WebMvcTest(WebhookController.class)
public class WebhookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private WebhookService webhookService;

    private WebhookConfigDto validWebhookConfig;
    private WebhookTestResultDTO successfulTestResult;
    private WebhookDeliveryStatusDTO deliveryStatus;

    @BeforeEach
    void setUp() {
        // Set up a valid webhook configuration for testing
        validWebhookConfig = new WebhookConfigDto();
        validWebhookConfig.setId(1L);
        validWebhookConfig.setUrl("https://example.com/webhook");
        validWebhookConfig.setEvents(Arrays.asList("application.created", "application.updated"));
        validWebhookConfig.setDescription("Test webhook");
        validWebhookConfig.setActive(true);
        validWebhookConfig.setSecretKey("test-secret-key");
        validWebhookConfig.setCreatedAt(LocalDateTime.now());
        validWebhookConfig.setUpdatedAt(LocalDateTime.now());

        // Set up a successful test result
        successfulTestResult = new WebhookTestResultDTO();
        successfulTestResult.setSuccess(true);
        successfulTestResult.setStatusCode(200);
        successfulTestResult.setMessage("Webhook test successful");
        successfulTestResult.setResponseBody("{\"status\":\"ok\"}");
        successfulTestResult.setResponseHeaders(Map.of("Content-Type", "application/json"));
        successfulTestResult.setTimestamp(LocalDateTime.now());

        // Set up a delivery status
        deliveryStatus = new WebhookDeliveryStatusDTO();
        deliveryStatus.setId("delivery-123");
        deliveryStatus.setWebhookConfigId("1");
        deliveryStatus.setEventType("application.created");
        deliveryStatus.setSuccess(true);
        deliveryStatus.setStatusCode(200);
        deliveryStatus.setAttemptCount(1);
        deliveryStatus.setTimestamp(LocalDateTime.now());
    }

    //-------------------------------------------------------------------------
    // GET /api/v1/webhooks - Get all webhook configurations
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should return all webhook configurations when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnAllWebhookConfigurations() throws Exception {
        // Given
        List<WebhookConfigDto> webhookConfigs = Arrays.asList(validWebhookConfig);
        when(webhookService.getAllWebhookConfigurations()).thenReturn(webhookConfigs);

        // When/Then
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", is(1)))
                .andExpect(jsonPath("$[0].url", is("https://example.com/webhook")))
                .andExpect(jsonPath("$[0].events", hasSize(2)))
                .andExpect(jsonPath("$[0].events[0]", is("application.created")))
                .andExpect(jsonPath("$[0].events[1]", is("application.updated")));

        verify(webhookService, times(1)).getAllWebhookConfigurations();
    }

    @Test
    @DisplayName("Should return 403 Forbidden when not authenticated as System Admin")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void shouldReturnForbiddenWhenNotSystemAdmin() throws Exception {
        // Given
        doThrow(new AuthorizationException("webhooks", "view", "System Admin"))
                .when(webhookService).getAllWebhookConfigurations();

        // When/Then
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isForbidden())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(403)))
                .andExpect(jsonPath("$.error", is("Forbidden")))
                .andExpect(jsonPath("$.message", containsString("Access denied")));

        verify(webhookService, times(1)).getAllWebhookConfigurations();
    }

    @Test
    @DisplayName("Should return 401 Unauthorized when not authenticated")
    void shouldReturnUnauthorizedWhenNotAuthenticated() throws Exception {
        // When/Then
        mockMvc.perform(get("/api/v1/webhooks"))
                .andExpect(status().isUnauthorized());

        verify(webhookService, never()).getAllWebhookConfigurations();
    }

    //-------------------------------------------------------------------------
    // GET /api/v1/webhooks/{id} - Get webhook configuration by ID
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should return webhook configuration by ID when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnWebhookConfigurationById() throws Exception {
        // Given
        when(webhookService.getWebhookConfigurationById(anyString()))
                .thenReturn(Optional.of(validWebhookConfig));

        // When/Then
        mockMvc.perform(get("/api/v1/webhooks/1"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is(1)))
                .andExpect(jsonPath("$.url", is("https://example.com/webhook")))
                .andExpect(jsonPath("$.events", hasSize(2)))
                .andExpect(jsonPath("$.events[0]", is("application.created")));

        verify(webhookService, times(1)).getWebhookConfigurationById("1");
    }

    @Test
    @DisplayName("Should return 404 Not Found when webhook configuration does not exist")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnNotFoundWhenWebhookConfigurationDoesNotExist() throws Exception {
        // Given
        when(webhookService.getWebhookConfigurationById(anyString()))
                .thenReturn(Optional.empty());

        // When/Then
        mockMvc.perform(get("/api/v1/webhooks/999"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(404)))
                .andExpect(jsonPath("$.error", is("Not Found")));

        verify(webhookService, times(1)).getWebhookConfigurationById("999");
    }

    //-------------------------------------------------------------------------
    // POST /api/v1/webhooks - Create webhook configuration
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should create webhook configuration when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldCreateWebhookConfiguration() throws Exception {
        // Given
        WebhookConfigDto newWebhookConfig = new WebhookConfigDto();
        newWebhookConfig.setUrl("https://example.com/webhook");
        newWebhookConfig.setEvents(Arrays.asList("application.created", "application.updated"));
        newWebhookConfig.setDescription("Test webhook");

        when(webhookService.createWebhookConfiguration(any(WebhookConfigDto.class)))
                .thenReturn(validWebhookConfig);

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newWebhookConfig)))
                .andExpect(status().isCreated())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is(1)))
                .andExpect(jsonPath("$.url", is("https://example.com/webhook")));

        verify(webhookService, times(1)).createWebhookConfiguration(any(WebhookConfigDto.class));
    }

    @Test
    @DisplayName("Should return 400 Bad Request when webhook configuration is invalid")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnBadRequestWhenWebhookConfigurationIsInvalid() throws Exception {
        // Given
        WebhookConfigDto invalidWebhookConfig = new WebhookConfigDto();
        invalidWebhookConfig.setUrl("not-a-url"); // Invalid URL
        invalidWebhookConfig.setEvents(Arrays.asList("application.created"));

        Map<String, String> validationErrors = new HashMap<>();
        validationErrors.put("url", "Webhook URL must use HTTPS");
        ValidationException validationException = new ValidationException("Validation failed", validationErrors);

        when(webhookService.createWebhookConfiguration(any(WebhookConfigDto.class)))
                .thenThrow(validationException);

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalidWebhookConfig)))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(400)))
                .andExpect(jsonPath("$.error", is("Bad Request")))
                .andExpect(jsonPath("$.validationErrors.url", is("Webhook URL must use HTTPS")));

        verify(webhookService, times(1)).createWebhookConfiguration(any(WebhookConfigDto.class));
    }

    //-------------------------------------------------------------------------
    // PUT /api/v1/webhooks/{id} - Update webhook configuration
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should update webhook configuration when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldUpdateWebhookConfiguration() throws Exception {
        // Given
        WebhookConfigDto updatedWebhookConfig = new WebhookConfigDto();
        updatedWebhookConfig.setUrl("https://example.com/updated-webhook");
        updatedWebhookConfig.setEvents(Arrays.asList("application.created", "application.deleted"));
        updatedWebhookConfig.setDescription("Updated test webhook");

        when(webhookService.updateWebhookConfiguration(eq("1"), any(WebhookConfigDto.class)))
                .thenReturn(updatedWebhookConfig);

        // When/Then
        mockMvc.perform(put("/api/v1/webhooks/1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updatedWebhookConfig)))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.url", is("https://example.com/updated-webhook")))
                .andExpect(jsonPath("$.events", hasSize(2)))
                .andExpect(jsonPath("$.events[1]", is("application.deleted")));

        verify(webhookService, times(1)).updateWebhookConfiguration(eq("1"), any(WebhookConfigDto.class));
    }

    @Test
    @DisplayName("Should return 404 Not Found when updating non-existent webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnNotFoundWhenUpdatingNonExistentWebhookConfiguration() throws Exception {
        // Given
        WebhookConfigDto updatedWebhookConfig = new WebhookConfigDto();
        updatedWebhookConfig.setUrl("https://example.com/updated-webhook");
        updatedWebhookConfig.setEvents(Arrays.asList("application.created"));

        when(webhookService.updateWebhookConfiguration(eq("999"), any(WebhookConfigDto.class)))
                .thenThrow(new ResourceNotFoundException("Webhook configuration", "999"));

        // When/Then
        mockMvc.perform(put("/api/v1/webhooks/999")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updatedWebhookConfig)))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(404)))
                .andExpect(jsonPath("$.error", is("Not Found")));

        verify(webhookService, times(1)).updateWebhookConfiguration(eq("999"), any(WebhookConfigDto.class));
    }

    //-------------------------------------------------------------------------
    // DELETE /api/v1/webhooks/{id} - Delete webhook configuration
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should delete webhook configuration when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldDeleteWebhookConfiguration() throws Exception {
        // Given
        doNothing().when(webhookService).deleteWebhookConfiguration(anyString());

        // When/Then
        mockMvc.perform(delete("/api/v1/webhooks/1"))
                .andExpect(status().isNoContent());

        verify(webhookService, times(1)).deleteWebhookConfiguration("1");
    }

    @Test
    @DisplayName("Should return 404 Not Found when deleting non-existent webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnNotFoundWhenDeletingNonExistentWebhookConfiguration() throws Exception {
        // Given
        doThrow(new ResourceNotFoundException("Webhook configuration", "999"))
                .when(webhookService).deleteWebhookConfiguration("999");

        // When/Then
        mockMvc.perform(delete("/api/v1/webhooks/999"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(404)))
                .andExpect(jsonPath("$.error", is("Not Found")));

        verify(webhookService, times(1)).deleteWebhookConfiguration("999");
    }

    //-------------------------------------------------------------------------
    // POST /api/v1/webhooks/{id}/test - Test webhook configuration
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should test webhook configuration when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldTestWebhookConfiguration() throws Exception {
        // Given
        when(webhookService.testWebhookConfiguration(anyString()))
                .thenReturn(successfulTestResult);

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/1/test"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.success", is(true)))
                .andExpect(jsonPath("$.statusCode", is(200)))
                .andExpect(jsonPath("$.message", is("Webhook test successful")));

        verify(webhookService, times(1)).testWebhookConfiguration("1");
    }

    @Test
    @DisplayName("Should return 404 Not Found when testing non-existent webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnNotFoundWhenTestingNonExistentWebhookConfiguration() throws Exception {
        // Given
        when(webhookService.testWebhookConfiguration("999"))
                .thenThrow(new ResourceNotFoundException("Webhook configuration", "999"));

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/999/test"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(404)))
                .andExpect(jsonPath("$.error", is("Not Found")));

        verify(webhookService, times(1)).testWebhookConfiguration("999");
    }

    //-------------------------------------------------------------------------
    // GET /api/v1/webhooks/{id}/status - Get webhook delivery status history
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should return webhook delivery status history when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnWebhookDeliveryStatusHistory() throws Exception {
        // Given
        List<WebhookDeliveryStatusDTO> deliveryStatuses = Arrays.asList(deliveryStatus);
        when(webhookService.getWebhookDeliveryStatusHistory(eq("1"), anyInt()))
                .thenReturn(deliveryStatuses);

        // When/Then
        mockMvc.perform(get("/api/v1/webhooks/1/status").param("limit", "10"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", is("delivery-123")))
                .andExpect(jsonPath("$[0].webhookConfigId", is("1")))
                .andExpect(jsonPath("$[0].eventType", is("application.created")))
                .andExpect(jsonPath("$[0].success", is(true)))
                .andExpect(jsonPath("$[0].statusCode", is(200)));

        verify(webhookService, times(1)).getWebhookDeliveryStatusHistory(eq("1"), eq(10));
    }

    @Test
    @DisplayName("Should return 404 Not Found when getting status history for non-existent webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnNotFoundWhenGettingStatusHistoryForNonExistentWebhookConfiguration() throws Exception {
        // Given
        when(webhookService.getWebhookDeliveryStatusHistory(eq("999"), anyInt()))
                .thenThrow(new ResourceNotFoundException("Webhook configuration", "999"));

        // When/Then
        mockMvc.perform(get("/api/v1/webhooks/999/status"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(404)))
                .andExpect(jsonPath("$.error", is("Not Found")));

        verify(webhookService, times(1)).getWebhookDeliveryStatusHistory(eq("999"), anyInt());
    }

    //-------------------------------------------------------------------------
    // POST /api/v1/webhooks/{id}/key - Generate new HMAC secret key
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should generate new HMAC secret key when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldGenerateNewHmacSecretKey() throws Exception {
        // Given
        String newSecretKey = "new-secret-key-123";
        when(webhookService.generateHmacSecretKey(anyString()))
                .thenReturn(newSecretKey);

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/1/key"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.secretKey", is(newSecretKey)));

        verify(webhookService, times(1)).generateHmacSecretKey("1");
    }

    @Test
    @DisplayName("Should return 404 Not Found when generating key for non-existent webhook configuration")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnNotFoundWhenGeneratingKeyForNonExistentWebhookConfiguration() throws Exception {
        // Given
        when(webhookService.generateHmacSecretKey("999"))
                .thenThrow(new ResourceNotFoundException("Webhook configuration", "999"));

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/999/key"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(404)))
                .andExpect(jsonPath("$.error", is("Not Found")));

        verify(webhookService, times(1)).generateHmacSecretKey("999");
    }

    //-------------------------------------------------------------------------
    // POST /api/v1/webhooks/validate-url - Validate webhook URL
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should validate webhook URL when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldValidateWebhookUrl() throws Exception {
        // Given
        String url = "https://example.com/webhook";
        when(webhookService.validateWebhookUrl(anyString()))
                .thenReturn(true);

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/validate-url")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of("url", url))))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.valid", is(true)));

        verify(webhookService, times(1)).validateWebhookUrl(url);
    }

    @Test
    @DisplayName("Should return invalid for invalid webhook URL")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnInvalidForInvalidWebhookUrl() throws Exception {
        // Given
        String url = "https://example.com/invalid-webhook";
        when(webhookService.validateWebhookUrl(anyString()))
                .thenReturn(false);

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/validate-url")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of("url", url))))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.valid", is(false)));

        verify(webhookService, times(1)).validateWebhookUrl(url);
    }

    //-------------------------------------------------------------------------
    // POST /api/v1/webhooks/{id}/retry/{deliveryId} - Retry webhook delivery
    //-------------------------------------------------------------------------

    @Test
    @DisplayName("Should retry webhook delivery when authenticated as System Admin")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldRetryWebhookDelivery() throws Exception {
        // Given
        when(webhookService.retryWebhookDelivery(anyString()))
                .thenReturn(deliveryStatus);

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/1/retry/delivery-123"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.id", is("delivery-123")))
                .andExpect(jsonPath("$.webhookConfigId", is("1")))
                .andExpect(jsonPath("$.success", is(true)));

        verify(webhookService, times(1)).retryWebhookDelivery("delivery-123");
    }

    @Test
    @DisplayName("Should return 404 Not Found when retrying non-existent webhook delivery")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void shouldReturnNotFoundWhenRetryingNonExistentWebhookDelivery() throws Exception {
        // Given
        when(webhookService.retryWebhookDelivery("non-existent-delivery"))
                .thenThrow(new ResourceNotFoundException("Webhook delivery", "non-existent-delivery"));

        // When/Then
        mockMvc.perform(post("/api/v1/webhooks/1/retry/non-existent-delivery"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status", is(404)))
                .andExpect(jsonPath("$.error", is("Not Found")));

        verify(webhookService, times(1)).retryWebhookDelivery("non-existent-delivery");
    }
}