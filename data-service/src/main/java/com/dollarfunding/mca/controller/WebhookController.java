package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.WebhookConfigurationDTO;
import com.dollarfunding.mca.dto.WebhookDeliveryStatusDTO;
import com.dollarfunding.mca.dto.WebhookTestResultDTO;
import com.dollarfunding.mca.service.WebhookService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;
import java.util.Map;

/**
 * REST controller that manages webhook configurations through the /api/v1/webhooks endpoint.
 * <p>
 * This controller provides functionality for creating, updating, and deleting webhook endpoints,
 * as well as testing webhook delivery. It restricts access to the System Admin role, validates
 * webhook configurations, and ensures secure delivery of webhook payloads with HMAC signatures.
 * </p>
 */
@RestController
@RequestMapping("/api/v1/webhooks")
@PreAuthorize("hasRole('SYSTEM_ADMIN')")
public class WebhookController {

    private static final Logger logger = LoggerFactory.getLogger(WebhookController.class);

    private final WebhookService webhookService;

    /**
     * Constructor with required dependencies.
     *
     * @param webhookService The service for webhook management
     */
    @Autowired
    public WebhookController(WebhookService webhookService) {
        this.webhookService = webhookService;
    }

    /**
     * Creates a new webhook configuration.
     *
     * @param webhookConfigurationDTO The webhook configuration to create
     * @return The created webhook configuration with generated ID
     */
    @PostMapping
    public ResponseEntity<WebhookConfigurationDTO> createWebhook(
            @Valid @RequestBody WebhookConfigurationDTO webhookConfigurationDTO) {
        logger.info("Creating new webhook configuration");
        WebhookConfigurationDTO createdWebhook = webhookService.createWebhookConfiguration(webhookConfigurationDTO);
        return new ResponseEntity<>(createdWebhook, HttpStatus.CREATED);
    }

    /**
     * Retrieves all webhook configurations.
     *
     * @return A list of all webhook configurations
     */
    @GetMapping
    public ResponseEntity<List<WebhookConfigurationDTO>> getAllWebhooks() {
        logger.info("Retrieving all webhook configurations");
        List<WebhookConfigurationDTO> webhooks = webhookService.getAllWebhookConfigurations();
        return ResponseEntity.ok(webhooks);
    }

    /**
     * Retrieves a webhook configuration by its ID.
     *
     * @param id The ID of the webhook configuration to retrieve
     * @return The webhook configuration if found
     */
    @GetMapping("/{id}")
    public ResponseEntity<WebhookConfigurationDTO> getWebhookById(@PathVariable String id) {
        logger.info("Retrieving webhook configuration with ID: {}", id);
        return webhookService.getWebhookConfigurationById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Updates an existing webhook configuration.
     *
     * @param id                      The ID of the webhook configuration to update
     * @param webhookConfigurationDTO The updated webhook configuration
     * @return The updated webhook configuration
     */
    @PutMapping("/{id}")
    public ResponseEntity<WebhookConfigurationDTO> updateWebhook(
            @PathVariable String id,
            @Valid @RequestBody WebhookConfigurationDTO webhookConfigurationDTO) {
        logger.info("Updating webhook configuration with ID: {}", id);
        WebhookConfigurationDTO updatedWebhook = webhookService.updateWebhookConfiguration(id, webhookConfigurationDTO);
        return ResponseEntity.ok(updatedWebhook);
    }

    /**
     * Deletes a webhook configuration by its ID.
     *
     * @param id The ID of the webhook configuration to delete
     * @return No content if successful
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteWebhook(@PathVariable String id) {
        logger.info("Deleting webhook configuration with ID: {}", id);
        webhookService.deleteWebhookConfiguration(id);
        return ResponseEntity.noContent().build();
    }

    /**
     * Tests a webhook configuration by sending a test payload to the endpoint.
     *
     * @param id The ID of the webhook configuration to test
     * @return The test result including response status and details
     */
    @PostMapping("/{id}/test")
    public ResponseEntity<WebhookTestResultDTO> testWebhook(@PathVariable String id) {
        logger.info("Testing webhook configuration with ID: {}", id);
        WebhookTestResultDTO testResult = webhookService.testWebhookConfiguration(id);
        return ResponseEntity.ok(testResult);
    }

    /**
     * Validates a webhook URL by sending a simple ping request.
     *
     * @param url The URL to validate
     * @return True if the URL is valid and responds correctly, false otherwise
     */
    @PostMapping("/validate-url")
    public ResponseEntity<Map<String, Boolean>> validateWebhookUrl(@RequestBody Map<String, String> request) {
        String url = request.get("url");
        logger.info("Validating webhook URL: {}", url);
        boolean isValid = webhookService.validateWebhookUrl(url);
        return ResponseEntity.ok(Map.of("valid", isValid));
    }

    /**
     * Generates a new HMAC secret key for a webhook configuration.
     *
     * @param id The ID of the webhook configuration
     * @return The new secret key
     */
    @PostMapping("/{id}/regenerate-secret")
    public ResponseEntity<Map<String, String>> regenerateSecretKey(@PathVariable String id) {
        logger.info("Regenerating secret key for webhook with ID: {}", id);
        String newSecretKey = webhookService.generateHmacSecretKey(id);
        return ResponseEntity.ok(Map.of("secretKey", newSecretKey));
    }

    /**
     * Retrieves the delivery status history for a webhook configuration.
     *
     * @param id    The ID of the webhook configuration
     * @param limit The maximum number of status entries to retrieve (optional, defaults to 10)
     * @return A list of delivery status entries
     */
    @GetMapping("/{id}/delivery-status")
    public ResponseEntity<List<WebhookDeliveryStatusDTO>> getDeliveryStatusHistory(
            @PathVariable String id,
            @RequestParam(defaultValue = "10") int limit) {
        logger.info("Retrieving delivery status history for webhook with ID: {}, limit: {}", id, limit);
        List<WebhookDeliveryStatusDTO> statusHistory = webhookService.getWebhookDeliveryStatusHistory(id, limit);
        return ResponseEntity.ok(statusHistory);
    }

    /**
     * Delivers a webhook event to a specific endpoint.
     *
     * @param id      The ID of the webhook configuration to deliver to
     * @param payload The payload to deliver
     * @return The delivery status result
     */
    @PostMapping("/{id}/deliver")
    public ResponseEntity<WebhookDeliveryStatusDTO> deliverWebhook(
            @PathVariable String id,
            @RequestBody Map<String, Object> payload) {
        logger.info("Manually delivering webhook with ID: {}", id);
        WebhookDeliveryStatusDTO deliveryStatus = webhookService.deliverWebhookEventToEndpoint(id, payload);
        return ResponseEntity.ok(deliveryStatus);
    }

    /**
     * Retrieves failed webhook deliveries that are eligible for retry.
     *
     * @return A list of failed delivery status entries
     */
    @GetMapping("/failed-deliveries")
    public ResponseEntity<List<WebhookDeliveryStatusDTO>> getFailedDeliveries() {
        logger.info("Retrieving failed webhook deliveries eligible for retry");
        List<WebhookDeliveryStatusDTO> failedDeliveries = webhookService.getFailedWebhookDeliveriesForRetry();
        return ResponseEntity.ok(failedDeliveries);
    }

    /**
     * Retries a failed webhook delivery.
     *
     * @param deliveryId The ID of the failed delivery to retry
     * @return The updated delivery status
     */
    @PostMapping("/retry/{deliveryId}")
    public ResponseEntity<WebhookDeliveryStatusDTO> retryDelivery(@PathVariable String deliveryId) {
        logger.info("Retrying webhook delivery with ID: {}", deliveryId);
        WebhookDeliveryStatusDTO retryStatus = webhookService.retryWebhookDelivery(deliveryId);
        return ResponseEntity.ok(retryStatus);
    }

    /**
     * Schedules automatic retries for failed webhook deliveries based on configured retry policy.
     * This endpoint is typically called by a scheduled job.
     *
     * @return The number of deliveries scheduled for retry
     */
    @PostMapping("/schedule-retries")
    public ResponseEntity<Map<String, Integer>> scheduleRetries() {
        logger.info("Scheduling automatic retries for failed webhook deliveries");
        int count = webhookService.scheduleWebhookRetries();
        return ResponseEntity.ok(Map.of("scheduledRetries", count));
    }

    /**
     * Purges old webhook delivery status records based on retention policy.
     * This endpoint is typically called by a scheduled job.
     *
     * @param retentionDays The number of days to retain delivery status records (optional, defaults to 30)
     * @return The number of records purged
     */
    @PostMapping("/purge-old-statuses")
    public ResponseEntity<Map<String, Integer>> purgeOldStatuses(
            @RequestParam(defaultValue = "30") int retentionDays) {
        logger.info("Purging webhook delivery statuses older than {} days", retentionDays);
        int count = webhookService.purgeOldWebhookDeliveryStatuses(retentionDays);
        return ResponseEntity.ok(Map.of("purgedRecords", count));
    }
}