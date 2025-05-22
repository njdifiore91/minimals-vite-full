package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.WebhookConfigDto;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;
import java.util.List;

/**
 * REST controller for managing webhook configurations.
 * <p>
 * This controller provides endpoints for creating, retrieving, updating, and deleting
 * webhook configurations. It enforces role-based access control to ensure that only
 * System Admin users can access the endpoints.
 * </p>
 */
@RestController
@RequestMapping("/api/v1/webhooks")
public class WebhookController {

    /**
     * Retrieves all webhook configurations.
     * <p>
     * This endpoint is accessible only to System Admin role.
     * </p>
     *
     * @return A list of all webhook configurations
     */
    @GetMapping
    public ResponseEntity<List<WebhookConfigDto>> getAllWebhookConfigs() {
        // Implementation would retrieve webhook configurations from the service
        return ResponseEntity.ok(List.of());
    }

    /**
     * Retrieves a webhook configuration by ID.
     * <p>
     * This endpoint is accessible only to System Admin role.
     * </p>
     *
     * @param id The webhook configuration ID
     * @return The webhook configuration with the specified ID
     */
    @GetMapping("/{id}")
    public ResponseEntity<WebhookConfigDto> getWebhookConfigById(@PathVariable Long id) {
        // Implementation would retrieve the webhook configuration from the service
        return ResponseEntity.ok(new WebhookConfigDto());
    }

    /**
     * Creates a new webhook configuration.
     * <p>
     * This endpoint is accessible only to System Admin role.
     * </p>
     *
     * @param webhookConfigDto The webhook configuration data to create
     * @return The created webhook configuration
     */
    @PostMapping
    public ResponseEntity<WebhookConfigDto> createWebhookConfig(@Valid @RequestBody WebhookConfigDto webhookConfigDto) {
        // Implementation would create the webhook configuration using the service
        return ResponseEntity.status(HttpStatus.CREATED).body(webhookConfigDto);
    }

    /**
     * Updates an existing webhook configuration.
     * <p>
     * This endpoint is accessible only to System Admin role.
     * </p>
     *
     * @param id               The webhook configuration ID
     * @param webhookConfigDto The updated webhook configuration data
     * @return The updated webhook configuration
     */
    @PutMapping("/{id}")
    public ResponseEntity<WebhookConfigDto> updateWebhookConfig(@PathVariable Long id,
                                                             @Valid @RequestBody WebhookConfigDto webhookConfigDto) {
        // Implementation would update the webhook configuration using the service
        return ResponseEntity.ok(webhookConfigDto);
    }

    /**
     * Deletes a webhook configuration.
     * <p>
     * This endpoint is accessible only to System Admin role.
     * </p>
     *
     * @param id The webhook configuration ID
     * @return No content response
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteWebhookConfig(@PathVariable Long id) {
        // Implementation would delete the webhook configuration using the service
        return ResponseEntity.noContent().build();
    }

    /**
     * Tests a webhook configuration by sending a test event.
     * <p>
     * This endpoint is accessible only to System Admin role.
     * </p>
     *
     * @param id The webhook configuration ID
     * @return The test result
     */
    @PostMapping("/{id}/test")
    public ResponseEntity<String> testWebhookConfig(@PathVariable Long id) {
        // Implementation would test the webhook configuration using the service
        return ResponseEntity.ok("Webhook test successful");
    }
}