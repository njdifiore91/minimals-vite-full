package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.WebhookRequestDTO;
import com.dollarfunding.mca.dto.WebhookResponseDTO;
import com.dollarfunding.mca.dto.WebhookTestRequestDTO;
import com.dollarfunding.mca.dto.WebhookTestResponseDTO;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.WebhookDeliveryException;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Service interface that defines the contract for webhook management in the MCA application.
 * <p>
 * It provides methods for creating, retrieving, updating, and deleting webhook configurations,
 * as well as methods for webhook delivery and status tracking.
 * </p>
 * <p>
 * This interface is implemented by WebhookServiceImpl and used by WebhookController
 * to handle webhook-related operations.
 * </p>
 */
public interface WebhookService {

    /**
     * Creates a new webhook configuration.
     *
     * @param webhookRequestDTO The webhook configuration data
     * @return The created webhook as a WebhookResponseDTO
     */
    WebhookResponseDTO createWebhook(WebhookRequestDTO webhookRequestDTO);

    /**
     * Retrieves all webhook configurations.
     *
     * @return A list of all webhooks as WebhookResponseDTOs
     */
    List<WebhookResponseDTO> getAllWebhooks();

    /**
     * Retrieves a webhook configuration by ID.
     *
     * @param id The ID of the webhook to retrieve
     * @return The webhook as a WebhookResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    WebhookResponseDTO getWebhookById(Long id);

    /**
     * Updates an existing webhook configuration.
     *
     * @param id The ID of the webhook to update
     * @param webhookRequestDTO The updated webhook configuration data
     * @return The updated webhook as a WebhookResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    WebhookResponseDTO updateWebhook(Long id, WebhookRequestDTO webhookRequestDTO);

    /**
     * Deletes a webhook configuration.
     *
     * @param id The ID of the webhook to delete
     * @throws ResourceNotFoundException if the webhook is not found
     */
    void deleteWebhook(Long id);

    /**
     * Retrieves all active webhooks for a specific event type.
     *
     * @param eventType The event type to filter by
     * @return A list of active webhooks for the specified event type
     */
    List<Webhook> getActiveWebhooksByEventType(EventType eventType);

    /**
     * Tests a webhook delivery with a custom payload.
     *
     * @param id The ID of the webhook to test
     * @param testRequestDTO The test request data
     * @return The test results as a WebhookTestResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    WebhookTestResponseDTO testWebhook(Long id, WebhookTestRequestDTO testRequestDTO);

    /**
     * Delivers a webhook notification.
     *
     * @param webhookId The ID of the webhook to deliver
     * @param payload The payload to send
     * @return true if the delivery was successful, false otherwise
     * @throws ResourceNotFoundException if the webhook is not found
     * @throws WebhookDeliveryException if there is an error delivering the webhook
     */
    boolean deliverWebhook(Long webhookId, Map<String, Object> payload);

    /**
     * Delivers a webhook notification asynchronously.
     *
     * @param webhookId The ID of the webhook to deliver
     * @param payload The payload to send
     * @return A CompletableFuture that completes when the webhook delivery is done
     * @throws ResourceNotFoundException if the webhook is not found
     */
    CompletableFuture<Boolean> deliverWebhookAsync(Long webhookId, Map<String, Object> payload);

    /**
     * Retries failed webhook deliveries.
     *
     * @return The number of webhooks that were retried
     */
    int retryFailedWebhooks();

    /**
     * Activates or deactivates a webhook.
     *
     * @param id The ID of the webhook to update
     * @param active Whether the webhook should be active
     * @return The updated webhook as a WebhookResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    WebhookResponseDTO setWebhookActive(Long id, boolean active);
}