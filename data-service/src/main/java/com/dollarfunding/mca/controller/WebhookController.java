package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.dto.WebhookRequestDTO;
import com.dollarfunding.mca.dto.WebhookResponseDTO;
import com.dollarfunding.mca.dto.WebhookTestRequestDTO;
import com.dollarfunding.mca.dto.WebhookTestResponseDTO;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.service.WebhookService;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;

/**
 * REST controller that manages webhook configurations through the /api/v1/webhooks endpoint.
 * It provides functionality for creating, updating, and deleting webhook endpoints,
 * as well as testing webhook delivery. The controller restricts access to System Admin role,
 * validates webhook configurations, and ensures secure delivery of webhook payloads with HMAC signatures.
 */
@RestController
@RequestMapping("/api/v1/webhooks")
@Validated
public class WebhookController extends BaseController {

    private final WebhookService webhookService;

    @Autowired
    public WebhookController(WebhookService webhookService) {
        this.webhookService = webhookService;
    }

    /**
     * Creates a new webhook configuration.
     *
     * @param webhookRequestDTO The webhook configuration data
     * @return The created webhook configuration
     */
    @PostMapping
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<WebhookResponseDTO> createWebhook(@Valid @RequestBody WebhookRequestDTO webhookRequestDTO) {
        WebhookResponseDTO createdWebhook = webhookService.createWebhook(webhookRequestDTO);
        return new ResponseEntity<>(createdWebhook, HttpStatus.CREATED);
    }

    /**
     * Retrieves all webhook configurations with pagination support.
     *
     * @param pageable Pagination parameters
     * @return A paginated list of webhook configurations
     */
    @GetMapping
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<PageResponseDTO<WebhookResponseDTO>> getAllWebhooks(Pageable pageable) {
        PageResponseDTO<WebhookResponseDTO> webhooks = webhookService.getAllWebhooks(pageable);
        return ResponseEntity.ok(webhooks);
    }

    /**
     * Retrieves a webhook configuration by ID.
     *
     * @param id The webhook ID
     * @return The webhook configuration
     */
    @GetMapping("/{id}")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<WebhookResponseDTO> getWebhookById(@PathVariable Long id) {
        WebhookResponseDTO webhook = webhookService.getWebhookById(id);
        return ResponseEntity.ok(webhook);
    }

    /**
     * Updates an existing webhook configuration.
     *
     * @param id The webhook ID
     * @param webhookRequestDTO The updated webhook configuration data
     * @return The updated webhook configuration
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<WebhookResponseDTO> updateWebhook(
            @PathVariable Long id,
            @Valid @RequestBody WebhookRequestDTO webhookRequestDTO) {
        WebhookResponseDTO updatedWebhook = webhookService.updateWebhook(id, webhookRequestDTO);
        return ResponseEntity.ok(updatedWebhook);
    }

    /**
     * Deletes a webhook configuration.
     *
     * @param id The webhook ID
     * @return No content response
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<Void> deleteWebhook(@PathVariable Long id) {
        webhookService.deleteWebhook(id);
        return ResponseEntity.noContent().build();
    }

    /**
     * Tests a webhook delivery by sending a test payload to the configured endpoint.
     *
     * @param id The webhook ID
     * @param testRequestDTO The test request data
     * @return The test result
     */
    @PostMapping("/{id}/test")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<WebhookTestResponseDTO> testWebhook(
            @PathVariable Long id,
            @Valid @RequestBody WebhookTestRequestDTO testRequestDTO) {
        WebhookTestResponseDTO testResult = webhookService.testWebhook(id, testRequestDTO);
        return ResponseEntity.ok(testResult);
    }

    /**
     * Activates a webhook configuration.
     *
     * @param id The webhook ID
     * @return The updated webhook configuration
     */
    @PatchMapping("/{id}/activate")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<WebhookResponseDTO> activateWebhook(@PathVariable Long id) {
        WebhookResponseDTO activatedWebhook = webhookService.activateWebhook(id);
        return ResponseEntity.ok(activatedWebhook);
    }

    /**
     * Deactivates a webhook configuration.
     *
     * @param id The webhook ID
     * @return The updated webhook configuration
     */
    @PatchMapping("/{id}/deactivate")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<WebhookResponseDTO> deactivateWebhook(@PathVariable Long id) {
        WebhookResponseDTO deactivatedWebhook = webhookService.deactivateWebhook(id);
        return ResponseEntity.ok(deactivatedWebhook);
    }

    /**
     * Retrieves webhook configurations by event type.
     *
     * @param eventType The event type
     * @return A list of webhook configurations for the specified event type
     */
    @GetMapping("/events/{eventType}")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<List<WebhookResponseDTO>> getWebhooksByEventType(
            @PathVariable EventType eventType) {
        List<WebhookResponseDTO> webhooks = webhookService.getWebhooksByEventType(eventType);
        return ResponseEntity.ok(webhooks);
    }

    /**
     * Retrieves all active webhook configurations.
     *
     * @return A list of active webhook configurations
     */
    @GetMapping("/active")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<List<WebhookResponseDTO>> getActiveWebhooks() {
        List<WebhookResponseDTO> activeWebhooks = webhookService.getActiveWebhooks();
        return ResponseEntity.ok(activeWebhooks);
    }

    /**
     * Regenerates the secret key for a webhook configuration.
     *
     * @param id The webhook ID
     * @return The updated webhook configuration with a new secret key
     */
    @PostMapping("/{id}/regenerate-secret")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<WebhookResponseDTO> regenerateWebhookSecret(@PathVariable Long id) {
        WebhookResponseDTO updatedWebhook = webhookService.regenerateWebhookSecret(id);
        return ResponseEntity.ok(updatedWebhook);
    }

    /**
     * Retrieves the delivery status history for a webhook.
     *
     * @param id The webhook ID
     * @param pageable Pagination parameters
     * @return A paginated list of webhook delivery status records
     */
    @GetMapping("/{id}/delivery-status")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    public ResponseEntity<PageResponseDTO<WebhookResponseDTO.DeliveryStatus>> getWebhookDeliveryStatus(
            @PathVariable Long id,
            Pageable pageable) {
        PageResponseDTO<WebhookResponseDTO.DeliveryStatus> deliveryStatus = 
                webhookService.getWebhookDeliveryStatus(id, pageable);
        return ResponseEntity.ok(deliveryStatus);
    }
}