package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.WebhookConfigurationDTO;
import com.dollarfunding.mca.dto.WebhookDeliveryStatusDTO;
import com.dollarfunding.mca.dto.WebhookTestResultDTO;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Service interface for webhook management in the MCA application.
 * Provides methods for creating, retrieving, updating, and deleting webhook configurations,
 * as well as methods for webhook delivery, status tracking, and security.
 */
public interface WebhookService {

    /**
     * Creates a new webhook configuration.
     *
     * @param webhookConfigurationDTO the webhook configuration to create
     * @return the created webhook configuration with generated ID
     * @throws IllegalArgumentException if the webhook configuration is invalid
     */
    WebhookConfigurationDTO createWebhookConfiguration(WebhookConfigurationDTO webhookConfigurationDTO);

    /**
     * Retrieves a webhook configuration by its ID.
     *
     * @param id the ID of the webhook configuration to retrieve
     * @return an Optional containing the webhook configuration, or empty if not found
     */
    Optional<WebhookConfigurationDTO> getWebhookConfigurationById(String id);

    /**
     * Retrieves all webhook configurations.
     *
     * @return a list of all webhook configurations
     */
    List<WebhookConfigurationDTO> getAllWebhookConfigurations();

    /**
     * Updates an existing webhook configuration.
     *
     * @param id the ID of the webhook configuration to update
     * @param webhookConfigurationDTO the updated webhook configuration
     * @return the updated webhook configuration
     * @throws IllegalArgumentException if the webhook configuration is invalid
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    WebhookConfigurationDTO updateWebhookConfiguration(String id, WebhookConfigurationDTO webhookConfigurationDTO);

    /**
     * Deletes a webhook configuration by its ID.
     *
     * @param id the ID of the webhook configuration to delete
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    void deleteWebhookConfiguration(String id);

    /**
     * Delivers a webhook event to all configured endpoints for the specified event type.
     *
     * @param eventType the type of event to deliver
     * @param payload the payload to deliver
     * @return a list of delivery status results
     */
    List<WebhookDeliveryStatusDTO> deliverWebhookEvent(String eventType, Map<String, Object> payload);

    /**
     * Delivers a webhook event to a specific endpoint.
     *
     * @param webhookConfigurationId the ID of the webhook configuration to deliver to
     * @param payload the payload to deliver
     * @return the delivery status result
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    WebhookDeliveryStatusDTO deliverWebhookEventToEndpoint(String webhookConfigurationId, Map<String, Object> payload);

    /**
     * Tests a webhook configuration by sending a test payload to the endpoint.
     *
     * @param webhookConfigurationId the ID of the webhook configuration to test
     * @return the test result including response status and details
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    WebhookTestResultDTO testWebhookConfiguration(String webhookConfigurationId);

    /**
     * Validates a webhook URL by sending a simple ping request.
     *
     * @param url the URL to validate
     * @return true if the URL is valid and responds correctly, false otherwise
     */
    boolean validateWebhookUrl(String url);

    /**
     * Generates a new HMAC secret key for a webhook configuration.
     *
     * @param webhookConfigurationId the ID of the webhook configuration
     * @return the new secret key
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    String generateHmacSecretKey(String webhookConfigurationId);

    /**
     * Generates an HMAC signature for a webhook payload.
     *
     * @param payload the payload to sign
     * @param secretKey the secret key to use for signing
     * @return the HMAC signature
     */
    String generateHmacSignature(String payload, String secretKey);

    /**
     * Verifies an HMAC signature for a webhook payload.
     *
     * @param payload the payload to verify
     * @param signature the signature to verify
     * @param secretKey the secret key to use for verification
     * @return true if the signature is valid, false otherwise
     */
    boolean verifyHmacSignature(String payload, String signature, String secretKey);

    /**
     * Retrieves the delivery status history for a webhook configuration.
     *
     * @param webhookConfigurationId the ID of the webhook configuration
     * @param limit the maximum number of status entries to retrieve
     * @return a list of delivery status entries
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    List<WebhookDeliveryStatusDTO> getWebhookDeliveryStatusHistory(String webhookConfigurationId, int limit);

    /**
     * Retrieves failed webhook deliveries that are eligible for retry.
     *
     * @return a list of failed delivery status entries
     */
    List<WebhookDeliveryStatusDTO> getFailedWebhookDeliveriesForRetry();

    /**
     * Retries a failed webhook delivery.
     *
     * @param deliveryId the ID of the failed delivery to retry
     * @return the updated delivery status
     * @throws IllegalArgumentException if the delivery is not in a failed state
     * @throws javax.persistence.EntityNotFoundException if the delivery is not found
     */
    WebhookDeliveryStatusDTO retryWebhookDelivery(String deliveryId);

    /**
     * Schedules automatic retries for failed webhook deliveries based on configured retry policy.
     * This method is typically called by a scheduled job.
     *
     * @return the number of deliveries scheduled for retry
     */
    int scheduleWebhookRetries();

    /**
     * Purges old webhook delivery status records based on retention policy.
     * This method is typically called by a scheduled job.
     *
     * @param retentionDays the number of days to retain delivery status records
     * @return the number of records purged
     */
    int purgeOldWebhookDeliveryStatuses(int retentionDays);
}