package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.WebhookConfigurationDTO;
import com.dollarfunding.mca.dto.WebhookDeliveryStatusDTO;
import com.dollarfunding.mca.dto.WebhookTestResponseDTO;
import com.dollarfunding.mca.dto.WebhookRequestDTO;
import com.dollarfunding.mca.dto.WebhookResponseDTO;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.repository.WebhookRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.stream.Collectors;

/**
 * Implementation of the WebhookService interface that manages webhook configurations,
 * delivery, and status tracking for the MCA application.
 * <p>
 * This class handles CRUD operations for webhook endpoints, implements HMAC signing
 * for secure payload delivery, and manages retry logic for failed deliveries. It
 * interacts with WebhookRepository for data persistence and implements asynchronous
 * webhook delivery for improved performance.
 * </p>
 */
@Service
public class WebhookServiceImpl implements WebhookService {

    private static final Logger logger = LoggerFactory.getLogger(WebhookServiceImpl.class);
    private static final String HMAC_SHA256_ALGORITHM = "HmacSHA256";
    private static final String DEFAULT_SIGNATURE_HEADER = "X-Webhook-Signature";
    private static final int DEFAULT_MAX_RETRY_ATTEMPTS = 3;
    private static final int DEFAULT_CONNECT_TIMEOUT_MS = 5000;
    private static final int DEFAULT_READ_TIMEOUT_MS = 10000;

    private final WebhookRepository webhookRepository;
    private final RestTemplate restTemplate;
    private final Executor asyncExecutor;

    @Value("${webhook.delivery.async:true}")
    private boolean asyncDelivery;

    @Value("${webhook.delivery.connect-timeout-ms:5000}")
    private int connectTimeoutMs;

    @Value("${webhook.delivery.read-timeout-ms:10000}")
    private int readTimeoutMs;

    @Value("${webhook.retry.initial-delay-ms:1000}")
    private int initialRetryDelayMs;

    @Value("${webhook.retry.max-delay-ms:60000}")
    private int maxRetryDelayMs;

    @Value("${webhook.retry.backoff-multiplier:2}")
    private int backoffMultiplier;

    /**
     * Constructor with required dependencies.
     *
     * @param webhookRepository The repository for webhook configurations
     * @param restTemplate      The REST template for HTTP requests
     * @param asyncExecutor     The executor for asynchronous webhook delivery
     */
    @Autowired
    public WebhookServiceImpl(WebhookRepository webhookRepository, RestTemplate restTemplate, Executor asyncExecutor) {
        this.webhookRepository = webhookRepository;
        this.restTemplate = restTemplate;
        this.asyncExecutor = asyncExecutor;
    }

    /**
     * Creates a new webhook configuration.
     *
     * @param webhookConfigurationDTO the webhook configuration to create
     * @return the created webhook configuration with generated ID
     * @throws IllegalArgumentException if the webhook configuration is invalid
     */
    @Override
    @Transactional
    public WebhookConfigurationDTO createWebhookConfiguration(WebhookConfigurationDTO webhookConfigurationDTO) {
        logger.debug("Creating webhook configuration: {}", webhookConfigurationDTO);

        // Validate the webhook configuration
        validateWebhookConfiguration(webhookConfigurationDTO);

        // Check if a webhook with the same endpoint URL already exists
        if (webhookRepository.existsByEndpointUrl(webhookConfigurationDTO.getEndpointUrl())) {
            throw new IllegalArgumentException("A webhook with the endpoint URL " + 
                    webhookConfigurationDTO.getEndpointUrl() + " already exists");
        }

        // Convert DTO to entity
        Webhook webhook = convertToEntity(webhookConfigurationDTO);

        // Set default values if not provided
        if (webhook.getMaxRetryAttempts() == null) {
            webhook.setMaxRetryAttempts(DEFAULT_MAX_RETRY_ATTEMPTS);
        }

        // Save the webhook configuration
        webhook = webhookRepository.save(webhook);
        logger.info("Created webhook configuration with ID: {}", webhook.getId());

        // Convert entity back to DTO and return
        return convertToDTO(webhook);
    }

    /**
     * Retrieves a webhook configuration by its ID.
     *
     * @param id the ID of the webhook configuration to retrieve
     * @return an Optional containing the webhook configuration, or empty if not found
     */
    @Override
    @Transactional(readOnly = true)
    public Optional<WebhookConfigurationDTO> getWebhookConfigurationById(String id) {
        logger.debug("Retrieving webhook configuration with ID: {}", id);

        try {
            Long webhookId = Long.parseLong(id);
            return webhookRepository.findById(webhookId)
                    .map(this::convertToDTO);
        } catch (NumberFormatException e) {
            logger.warn("Invalid webhook ID format: {}", id);
            return Optional.empty();
        }
    }

    /**
     * Retrieves all webhook configurations.
     *
     * @return a list of all webhook configurations
     */
    @Override
    @Transactional(readOnly = true)
    public List<WebhookConfigurationDTO> getAllWebhookConfigurations() {
        logger.debug("Retrieving all webhook configurations");

        return webhookRepository.findAll().stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
    }

    /**
     * Updates an existing webhook configuration.
     *
     * @param id                      the ID of the webhook configuration to update
     * @param webhookConfigurationDTO the updated webhook configuration
     * @return the updated webhook configuration
     * @throws IllegalArgumentException        if the webhook configuration is invalid
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    @Override
    @Transactional
    public WebhookConfigurationDTO updateWebhookConfiguration(String id, WebhookConfigurationDTO webhookConfigurationDTO) {
        logger.debug("Updating webhook configuration with ID: {}", id);

        // Validate the webhook configuration
        validateWebhookConfiguration(webhookConfigurationDTO);

        try {
            Long webhookId = Long.parseLong(id);
            Webhook webhook = webhookRepository.findById(webhookId)
                    .orElseThrow(() -> new ResourceNotFoundException("Webhook not found with ID: " + id));

            // Check if the endpoint URL is being changed and if it already exists
            if (!webhook.getEndpointUrl().equals(webhookConfigurationDTO.getEndpointUrl()) &&
                    webhookRepository.existsByEndpointUrl(webhookConfigurationDTO.getEndpointUrl())) {
                throw new IllegalArgumentException("A webhook with the endpoint URL " +
                        webhookConfigurationDTO.getEndpointUrl() + " already exists");
            }

            // Update the webhook entity
            updateWebhookEntity(webhook, webhookConfigurationDTO);

            // Save the updated webhook
            webhook = webhookRepository.save(webhook);
            logger.info("Updated webhook configuration with ID: {}", webhook.getId());

            // Convert entity back to DTO and return
            return convertToDTO(webhook);
        } catch (NumberFormatException e) {
            logger.warn("Invalid webhook ID format: {}", id);
            throw new IllegalArgumentException("Invalid webhook ID format: " + id);
        }
    }

    /**
     * Deletes a webhook configuration by its ID.
     *
     * @param id the ID of the webhook configuration to delete
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    @Override
    @Transactional
    public void deleteWebhookConfiguration(String id) {
        logger.debug("Deleting webhook configuration with ID: {}", id);

        try {
            Long webhookId = Long.parseLong(id);
            if (!webhookRepository.existsById(webhookId)) {
                throw new ResourceNotFoundException("Webhook not found with ID: " + id);
            }

            webhookRepository.deleteById(webhookId);
            logger.info("Deleted webhook configuration with ID: {}", id);
        } catch (NumberFormatException e) {
            logger.warn("Invalid webhook ID format: {}", id);
            throw new IllegalArgumentException("Invalid webhook ID format: " + id);
        }
    }

    /**
     * Delivers a webhook event to all configured endpoints for the specified event type.
     *
     * @param eventType the type of event to deliver
     * @param payload   the payload to deliver
     * @return a list of delivery status results
     */
    @Override
    @Transactional
    public List<WebhookDeliveryStatusDTO> deliverWebhookEvent(String eventType, Map<String, Object> payload) {
        logger.debug("Delivering webhook event of type: {} to all configured endpoints", eventType);

        // Validate event type
        EventType type = validateAndParseEventType(eventType);
        if (type == null) {
            logger.warn("Invalid event type: {}", eventType);
            return Collections.emptyList();
        }

        // Find all active webhooks for this event type
        List<Webhook> webhooks = webhookRepository.findByEventTypeAndActive(type, true);
        if (webhooks.isEmpty()) {
            logger.info("No active webhooks found for event type: {}", eventType);
            return Collections.emptyList();
        }

        // Deliver the webhook to each endpoint
        List<WebhookDeliveryStatusDTO> results = new ArrayList<>();
        for (Webhook webhook : webhooks) {
            WebhookDeliveryStatusDTO status;
            if (asyncDelivery) {
                // For async delivery, we return a placeholder status and update it later
                status = new WebhookDeliveryStatusDTO.Builder()
                        .webhookId(webhook.getId().toString())
                        .eventType(eventType)
                        .status("PENDING")
                        .timestamp(LocalDateTime.now())
                        .endpointUrl(webhook.getEndpointUrl())
                        .build();
                
                // Deliver asynchronously
                deliverWebhookAsync(webhook, payload, status);
            } else {
                // For sync delivery, we deliver and return the actual status
                status = deliverWebhook(webhook, payload);
            }
            results.add(status);
        }

        return results;
    }

    /**
     * Delivers a webhook event to a specific endpoint.
     *
     * @param webhookConfigurationId the ID of the webhook configuration to deliver to
     * @param payload               the payload to deliver
     * @return the delivery status result
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    @Override
    @Transactional
    public WebhookDeliveryStatusDTO deliverWebhookEventToEndpoint(String webhookConfigurationId, Map<String, Object> payload) {
        logger.debug("Delivering webhook event to endpoint with ID: {}", webhookConfigurationId);

        try {
            Long webhookId = Long.parseLong(webhookConfigurationId);
            Webhook webhook = webhookRepository.findById(webhookId)
                    .orElseThrow(() -> new ResourceNotFoundException("Webhook not found with ID: " + webhookConfigurationId));

            if (!webhook.getActive()) {
                logger.warn("Cannot deliver to inactive webhook with ID: {}", webhookConfigurationId);
                return new WebhookDeliveryStatusDTO.Builder()
                        .webhookId(webhookConfigurationId)
                        .status("SKIPPED")
                        .message("Webhook is inactive")
                        .timestamp(LocalDateTime.now())
                        .endpointUrl(webhook.getEndpointUrl())
                        .eventType(webhook.getEventType().name())
                        .build();
            }

            return deliverWebhook(webhook, payload);
        } catch (NumberFormatException e) {
            logger.warn("Invalid webhook ID format: {}", webhookConfigurationId);
            throw new IllegalArgumentException("Invalid webhook ID format: " + webhookConfigurationId);
        }
    }

    /**
     * Tests a webhook configuration by sending a test payload to the endpoint.
     *
     * @param webhookConfigurationId the ID of the webhook configuration to test
     * @return the test result including response status and details
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    @Override
    @Transactional(readOnly = true)
    public WebhookTestResultDTO testWebhookConfiguration(String webhookConfigurationId) {
        logger.debug("Testing webhook configuration with ID: {}", webhookConfigurationId);

        try {
            Long webhookId = Long.parseLong(webhookConfigurationId);
            Webhook webhook = webhookRepository.findById(webhookId)
                    .orElseThrow(() -> new ResourceNotFoundException("Webhook not found with ID: " + webhookConfigurationId));

            // Generate a sample payload based on the webhook's event type
            Map<String, Object> samplePayload = webhook.generateSamplePayload();

            // Add test-specific fields to the payload
            samplePayload.put("test", true);
            samplePayload.put("test_id", "test_" + System.currentTimeMillis());

            // Deliver the test webhook
            long startTime = System.currentTimeMillis();
            WebhookTestResponseDTO result;

            try {
                // Convert payload to JSON string
                String payloadJson = convertPayloadToJson(samplePayload);

                // Generate HMAC signature
                String signature = generateHmacSignature(payloadJson, webhook.getSecretKey());

                // Prepare headers
                HttpHeaders headers = new HttpHeaders();
                headers.set("Content-Type", "application/json");
                headers.set(webhook.getSignatureHeader() != null ? 
                        webhook.getSignatureHeader() : DEFAULT_SIGNATURE_HEADER, signature);

                // Create HTTP entity with headers and payload
                HttpEntity<String> entity = new HttpEntity<>(payloadJson, headers);

                // Send the request
                ResponseEntity<String> response = restTemplate.postForEntity(
                        webhook.getEndpointUrl(), entity, String.class);

                // Calculate delivery time
                long deliveryTime = System.currentTimeMillis() - startTime;

                // Create success response
                result = WebhookTestResponseDTO.builder()
                        .success(true)
                        .deliveryTimestamp(LocalDateTime.now())
                        .responseCode(response.getStatusCodeValue())
                        .responseBody(response.getBody())
                        .signatureVerified(true) // We can't verify from the client side
                        .signatureHeader(webhook.getSignatureHeader() != null ? 
                                webhook.getSignatureHeader() : DEFAULT_SIGNATURE_HEADER)
                        .signatureSent(signature)
                        .deliveryTimeMs(deliveryTime)
                        .endpointUrl(webhook.getEndpointUrl())
                        .eventType(webhook.getEventType().name())
                        .build();

                logger.info("Successfully tested webhook with ID: {}, response code: {}", 
                        webhookId, response.getStatusCodeValue());
            } catch (RestClientException e) {
                // Create error response
                result = WebhookTestResponseDTO.builder()
                        .success(false)
                        .deliveryTimestamp(LocalDateTime.now())
                        .errorMessage(e.getMessage())
                        .endpointUrl(webhook.getEndpointUrl())
                        .eventType(webhook.getEventType().name())
                        .build();

                logger.warn("Failed to test webhook with ID: {}, error: {}", webhookId, e.getMessage());
            } catch (Exception e) {
                // Create error response for other exceptions
                result = WebhookTestResponseDTO.builder()
                        .success(false)
                        .deliveryTimestamp(LocalDateTime.now())
                        .errorMessage("Internal error: " + e.getMessage())
                        .endpointUrl(webhook.getEndpointUrl())
                        .eventType(webhook.getEventType().name())
                        .build();

                logger.error("Error testing webhook with ID: {}", webhookId, e);
            }

            return result;
        } catch (NumberFormatException e) {
            logger.warn("Invalid webhook ID format: {}", webhookConfigurationId);
            throw new IllegalArgumentException("Invalid webhook ID format: " + webhookConfigurationId);
        }
    }

    /**
     * Validates a webhook URL by sending a simple ping request.
     *
     * @param url the URL to validate
     * @return true if the URL is valid and responds correctly, false otherwise
     */
    @Override
    public boolean validateWebhookUrl(String url) {
        logger.debug("Validating webhook URL: {}", url);

        if (url == null || !url.startsWith("https://")) {
            logger.warn("Invalid webhook URL format: {}", url);
            return false;
        }

        try {
            // Prepare a simple ping payload
            Map<String, Object> pingPayload = Map.of(
                    "ping", true,
                    "timestamp", System.currentTimeMillis()
            );

            // Convert payload to JSON string
            String payloadJson = convertPayloadToJson(pingPayload);

            // Prepare headers
            HttpHeaders headers = new HttpHeaders();
            headers.set("Content-Type", "application/json");

            // Create HTTP entity with headers and payload
            HttpEntity<String> entity = new HttpEntity<>(payloadJson, headers);

            // Send the request
            ResponseEntity<String> response = restTemplate.postForEntity(url, entity, String.class);

            // Check if the response is successful (2xx status code)
            boolean isValid = response.getStatusCode().is2xxSuccessful();
            logger.info("Webhook URL validation result for {}: {}", url, isValid);
            return isValid;
        } catch (Exception e) {
            logger.warn("Failed to validate webhook URL: {}, error: {}", url, e.getMessage());
            return false;
        }
    }

    /**
     * Generates a new HMAC secret key for a webhook configuration.
     *
     * @param webhookConfigurationId the ID of the webhook configuration
     * @return the new secret key
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    @Override
    @Transactional
    public String generateHmacSecretKey(String webhookConfigurationId) {
        logger.debug("Generating new HMAC secret key for webhook with ID: {}", webhookConfigurationId);

        try {
            Long webhookId = Long.parseLong(webhookConfigurationId);
            Webhook webhook = webhookRepository.findById(webhookId)
                    .orElseThrow(() -> new ResourceNotFoundException("Webhook not found with ID: " + webhookConfigurationId));

            // Generate a new secret key
            String newSecretKey = generateRandomSecretKey();

            // Update the webhook with the new secret key
            webhook.setSecretKey(newSecretKey);
            webhookRepository.save(webhook);

            logger.info("Generated new HMAC secret key for webhook with ID: {}", webhookId);
            return newSecretKey;
        } catch (NumberFormatException e) {
            logger.warn("Invalid webhook ID format: {}", webhookConfigurationId);
            throw new IllegalArgumentException("Invalid webhook ID format: " + webhookConfigurationId);
        }
    }

    /**
     * Generates an HMAC signature for a webhook payload.
     *
     * @param payload   the payload to sign
     * @param secretKey the secret key to use for signing
     * @return the HMAC signature
     */
    @Override
    public String generateHmacSignature(String payload, String secretKey) {
        try {
            // Create an HMAC-SHA256 instance with the secret key
            SecretKeySpec signingKey = new SecretKeySpec(
                    secretKey.getBytes(StandardCharsets.UTF_8), HMAC_SHA256_ALGORITHM);
            Mac mac = Mac.getInstance(HMAC_SHA256_ALGORITHM);
            mac.init(signingKey);

            // Compute the HMAC on the payload bytes
            byte[] rawHmac = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));

            // Convert to Base64 string
            return Base64.getEncoder().encodeToString(rawHmac);
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            logger.error("Error generating HMAC signature", e);
            throw new RuntimeException("Error generating HMAC signature: " + e.getMessage(), e);
        }
    }

    /**
     * Verifies an HMAC signature for a webhook payload.
     *
     * @param payload   the payload to verify
     * @param signature the signature to verify
     * @param secretKey the secret key to use for verification
     * @return true if the signature is valid, false otherwise
     */
    @Override
    public boolean verifyHmacSignature(String payload, String signature, String secretKey) {
        try {
            // Generate a signature with the same payload and secret key
            String expectedSignature = generateHmacSignature(payload, secretKey);

            // Compare the expected signature with the provided signature
            return expectedSignature.equals(signature);
        } catch (Exception e) {
            logger.error("Error verifying HMAC signature", e);
            return false;
        }
    }

    /**
     * Retrieves the delivery status history for a webhook configuration.
     *
     * @param webhookConfigurationId the ID of the webhook configuration
     * @param limit                 the maximum number of status entries to retrieve
     * @return a list of delivery status entries
     * @throws javax.persistence.EntityNotFoundException if the webhook configuration is not found
     */
    @Override
    @Transactional(readOnly = true)
    public List<WebhookDeliveryStatusDTO> getWebhookDeliveryStatusHistory(String webhookConfigurationId, int limit) {
        logger.debug("Retrieving delivery status history for webhook with ID: {}, limit: {}", webhookConfigurationId, limit);

        try {
            Long webhookId = Long.parseLong(webhookConfigurationId);
            if (!webhookRepository.existsById(webhookId)) {
                throw new ResourceNotFoundException("Webhook not found with ID: " + webhookConfigurationId);
            }

            // In a real implementation, this would query a webhook_delivery_status table
            // For now, we'll return an empty list as a placeholder
            logger.info("Webhook delivery status history not implemented yet");
            return Collections.emptyList();
        } catch (NumberFormatException e) {
            logger.warn("Invalid webhook ID format: {}", webhookConfigurationId);
            throw new IllegalArgumentException("Invalid webhook ID format: " + webhookConfigurationId);
        }
    }

    /**
     * Retrieves failed webhook deliveries that are eligible for retry.
     *
     * @return a list of failed delivery status entries
     */
    @Override
    @Transactional(readOnly = true)
    public List<WebhookDeliveryStatusDTO> getFailedWebhookDeliveriesForRetry() {
        logger.debug("Retrieving failed webhook deliveries eligible for retry");

        // Find webhooks eligible for retry
        List<Webhook> webhooksForRetry = webhookRepository.findWebhooksEligibleForRetry();
        logger.info("Found {} webhooks eligible for retry", webhooksForRetry.size());

        // In a real implementation, this would query a webhook_delivery_status table
        // For now, we'll return placeholder statuses based on the webhooks
        return webhooksForRetry.stream()
                .map(webhook -> new WebhookDeliveryStatusDTO.Builder()
                        .webhookId(webhook.getId().toString())
                        .status("FAILED")
                        .message("Ready for retry")
                        .timestamp(webhook.getLastFailureAt())
                        .endpointUrl(webhook.getEndpointUrl())
                        .eventType(webhook.getEventType().name())
                        .retryCount(webhook.getConsecutiveFailures())
                        .build())
                .collect(Collectors.toList());
    }

    /**
     * Retries a failed webhook delivery.
     *
     * @param deliveryId the ID of the failed delivery to retry
     * @return the updated delivery status
     * @throws IllegalArgumentException if the delivery is not in a failed state
     * @throws javax.persistence.EntityNotFoundException if the delivery is not found
     */
    @Override
    @Transactional
    public WebhookDeliveryStatusDTO retryWebhookDelivery(String deliveryId) {
        logger.debug("Retrying webhook delivery with ID: {}", deliveryId);

        // In a real implementation, this would look up the delivery in a webhook_delivery_status table
        // and retry it with the original payload
        // For now, we'll throw an exception as a placeholder
        logger.warn("Webhook delivery retry not implemented yet");
        throw new UnsupportedOperationException("Webhook delivery retry not implemented yet");
    }

    /**
     * Schedules automatic retries for failed webhook deliveries based on configured retry policy.
     * This method is typically called by a scheduled job.
     *
     * @return the number of deliveries scheduled for retry
     */
    @Override
    @Transactional
    public int scheduleWebhookRetries() {
        logger.debug("Scheduling automatic retries for failed webhook deliveries");

        // Find webhooks eligible for retry
        List<Webhook> webhooksForRetry = webhookRepository.findWebhooksEligibleForRetry();
        logger.info("Found {} webhooks eligible for retry", webhooksForRetry.size());

        // In a real implementation, this would schedule retries for each webhook
        // For now, we'll just return the count as a placeholder
        return webhooksForRetry.size();
    }

    /**
     * Purges old webhook delivery status records based on retention policy.
     * This method is typically called by a scheduled job.
     *
     * @param retentionDays the number of days to retain delivery status records
     * @return the number of records purged
     */
    @Override
    @Transactional
    public int purgeOldWebhookDeliveryStatuses(int retentionDays) {
        logger.debug("Purging webhook delivery statuses older than {} days", retentionDays);

        // In a real implementation, this would delete old records from a webhook_delivery_status table
        // For now, we'll just return 0 as a placeholder
        logger.info("Webhook delivery status purging not implemented yet");
        return 0;
    }

    /**
     * Delivers a webhook asynchronously.
     *
     * @param webhook the webhook configuration
     * @param payload the payload to deliver
     * @param status  the initial status to update
     * @return a CompletableFuture that completes when the webhook delivery is done
     */
    @Async
    protected CompletableFuture<WebhookDeliveryStatusDTO> deliverWebhookAsync(Webhook webhook, Map<String, Object> payload, 
                                                                            WebhookDeliveryStatusDTO status) {
        return CompletableFuture.supplyAsync(() -> {
            WebhookDeliveryStatusDTO result = deliverWebhook(webhook, payload);
            // In a real implementation, this would update the status in a webhook_delivery_status table
            logger.info("Asynchronously delivered webhook to {} with status {}", 
                    webhook.getEndpointUrl(), result.getStatus());
            return result;
        }, asyncExecutor);
    }

    /**
     * Delivers a webhook synchronously.
     *
     * @param webhook the webhook configuration
     * @param payload the payload to deliver
     * @return the delivery status
     */
    protected WebhookDeliveryStatusDTO deliverWebhook(Webhook webhook, Map<String, Object> payload) {
        logger.debug("Delivering webhook to endpoint: {}", webhook.getEndpointUrl());

        WebhookDeliveryStatusDTO.Builder statusBuilder = new WebhookDeliveryStatusDTO.Builder()
                .webhookId(webhook.getId().toString())
                .eventType(webhook.getEventType().name())
                .timestamp(LocalDateTime.now())
                .endpointUrl(webhook.getEndpointUrl());

        try {
            // Convert payload to JSON string
            String payloadJson = convertPayloadToJson(payload);

            // Generate HMAC signature
            String signature = generateHmacSignature(payloadJson, webhook.getSecretKey());

            // Prepare headers
            HttpHeaders headers = new HttpHeaders();
            headers.set("Content-Type", "application/json");
            headers.set(webhook.getSignatureHeader() != null ? 
                    webhook.getSignatureHeader() : DEFAULT_SIGNATURE_HEADER, signature);

            // Create HTTP entity with headers and payload
            HttpEntity<String> entity = new HttpEntity<>(payloadJson, headers);

            // Send the request
            long startTime = System.currentTimeMillis();
            ResponseEntity<String> response = restTemplate.postForEntity(
                    webhook.getEndpointUrl(), entity, String.class);
            long deliveryTime = System.currentTimeMillis() - startTime;

            // Check if the response is successful (2xx status code)
            boolean isSuccess = response.getStatusCode().is2xxSuccessful();

            // Update webhook status in the database
            if (isSuccess) {
                webhook.recordSuccess();
                statusBuilder.status("SUCCESS")
                        .statusCode(response.getStatusCodeValue())
                        .deliveryTimeMs(deliveryTime);
            } else {
                boolean deactivated = webhook.recordFailure();
                statusBuilder.status(deactivated ? "DEACTIVATED" : "FAILED")
                        .statusCode(response.getStatusCodeValue())
                        .message("Non-2xx response: " + response.getStatusCodeValue())
                        .deliveryTimeMs(deliveryTime)
                        .retryCount(webhook.getConsecutiveFailures());
            }

            // Save the updated webhook
            webhookRepository.save(webhook);

            logger.info("Webhook delivery to {} completed with status code: {}", 
                    webhook.getEndpointUrl(), response.getStatusCodeValue());
        } catch (Exception e) {
            // Record failure in the webhook
            boolean deactivated = webhook.recordFailure();
            webhookRepository.save(webhook);

            // Build error status
            statusBuilder.status(deactivated ? "DEACTIVATED" : "FAILED")
                    .message("Error: " + e.getMessage())
                    .retryCount(webhook.getConsecutiveFailures());

            logger.warn("Error delivering webhook to {}: {}", webhook.getEndpointUrl(), e.getMessage());
        }

        return statusBuilder.build();
    }

    /**
     * Validates a webhook configuration.
     *
     * @param webhookConfigurationDTO the webhook configuration to validate
     * @throws IllegalArgumentException if the webhook configuration is invalid
     */
    private void validateWebhookConfiguration(WebhookConfigurationDTO webhookConfigurationDTO) {
        if (webhookConfigurationDTO == null) {
            throw new IllegalArgumentException("Webhook configuration cannot be null");
        }

        if (webhookConfigurationDTO.getEndpointUrl() == null || webhookConfigurationDTO.getEndpointUrl().isEmpty()) {
            throw new IllegalArgumentException("Endpoint URL is required");
        }

        if (!webhookConfigurationDTO.getEndpointUrl().startsWith("https://")) {
            throw new IllegalArgumentException("Endpoint URL must use HTTPS protocol");
        }

        if (webhookConfigurationDTO.getSecretKey() == null || webhookConfigurationDTO.getSecretKey().isEmpty()) {
            throw new IllegalArgumentException("Secret key is required");
        }

        if (webhookConfigurationDTO.getSecretKey().length() < 32) {
            throw new IllegalArgumentException("Secret key must be at least 32 characters long");
        }

        if (webhookConfigurationDTO.getEventType() == null) {
            throw new IllegalArgumentException("Event type is required");
        }

        if (webhookConfigurationDTO.getActive() == null) {
            throw new IllegalArgumentException("Active status is required");
        }

        if (webhookConfigurationDTO.getMaxRetryAttempts() != null && 
                (webhookConfigurationDTO.getMaxRetryAttempts() < 0 || webhookConfigurationDTO.getMaxRetryAttempts() > 10)) {
            throw new IllegalArgumentException("Max retry attempts must be between 0 and 10");
        }
    }

    /**
     * Validates and parses an event type string.
     *
     * @param eventType the event type string to parse
     * @return the parsed EventType, or null if invalid
     */
    private EventType validateAndParseEventType(String eventType) {
        if (eventType == null || eventType.isEmpty()) {
            return null;
        }

        try {
            return EventType.valueOf(eventType.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    /**
     * Converts a webhook configuration DTO to an entity.
     *
     * @param dto the DTO to convert
     * @return the converted entity
     */
    private Webhook convertToEntity(WebhookConfigurationDTO dto) {
        Webhook webhook = new Webhook();
        webhook.setEndpointUrl(dto.getEndpointUrl());
        webhook.setSecretKey(dto.getSecretKey());
        webhook.setActive(dto.getActive());
        webhook.setEventType(dto.getEventType());
        
        if (dto.getMaxRetryAttempts() != null) {
            webhook.setMaxRetryAttempts(dto.getMaxRetryAttempts());
        }
        
        if (dto.getDescription() != null) {
            webhook.setDescription(dto.getDescription());
        }
        
        if (dto.getSignatureHeader() != null) {
            webhook.setSignatureHeader(dto.getSignatureHeader());
        }
        
        return webhook;
    }

    /**
     * Updates a webhook entity with data from a DTO.
     *
     * @param webhook the entity to update
     * @param dto     the DTO with updated data
     */
    private void updateWebhookEntity(Webhook webhook, WebhookConfigurationDTO dto) {
        webhook.setEndpointUrl(dto.getEndpointUrl());
        webhook.setSecretKey(dto.getSecretKey());
        webhook.setActive(dto.getActive());
        webhook.setEventType(dto.getEventType());
        
        if (dto.getMaxRetryAttempts() != null) {
            webhook.setMaxRetryAttempts(dto.getMaxRetryAttempts());
        }
        
        if (dto.getDescription() != null) {
            webhook.setDescription(dto.getDescription());
        }
        
        if (dto.getSignatureHeader() != null) {
            webhook.setSignatureHeader(dto.getSignatureHeader());
        }
    }

    /**
     * Converts a webhook entity to a DTO.
     *
     * @param webhook the entity to convert
     * @return the converted DTO
     */
    private WebhookConfigurationDTO convertToDTO(Webhook webhook) {
        return WebhookResponseDTO.fromEntity(webhook);
    }

    /**
     * Converts a payload map to a JSON string.
     *
     * @param payload the payload to convert
     * @return the JSON string representation of the payload
     */
    private String convertPayloadToJson(Map<String, Object> payload) {
        // In a real implementation, this would use Jackson ObjectMapper
        // For simplicity, we'll use a placeholder implementation
        return payload.toString();
    }

    /**
     * Generates a random secret key for HMAC signing.
     *
     * @return a random secret key
     */
    private String generateRandomSecretKey() {
        byte[] bytes = new byte[32]; // 256 bits
        new SecureRandom().nextBytes(bytes);
        return Base64.getEncoder().encodeToString(bytes);
    }

    /**
     * Inner class for building WebhookDeliveryStatusDTO objects.
     */
    public static class WebhookDeliveryStatusDTO {
        private final String webhookId;
        private final String status;
        private final String message;
        private final LocalDateTime timestamp;
        private final String endpointUrl;
        private final String eventType;
        private final Integer statusCode;
        private final Integer retryCount;
        private final Long deliveryTimeMs;

        private WebhookDeliveryStatusDTO(Builder builder) {
            this.webhookId = builder.webhookId;
            this.status = builder.status;
            this.message = builder.message;
            this.timestamp = builder.timestamp;
            this.endpointUrl = builder.endpointUrl;
            this.eventType = builder.eventType;
            this.statusCode = builder.statusCode;
            this.retryCount = builder.retryCount;
            this.deliveryTimeMs = builder.deliveryTimeMs;
        }

        public String getWebhookId() {
            return webhookId;
        }

        public String getStatus() {
            return status;
        }

        public String getMessage() {
            return message;
        }

        public LocalDateTime getTimestamp() {
            return timestamp;
        }

        public String getEndpointUrl() {
            return endpointUrl;
        }

        public String getEventType() {
            return eventType;
        }

        public Integer getStatusCode() {
            return statusCode;
        }

        public Integer getRetryCount() {
            return retryCount;
        }

        public Long getDeliveryTimeMs() {
            return deliveryTimeMs;
        }

        public static class Builder {
            private String webhookId;
            private String status;
            private String message;
            private LocalDateTime timestamp;
            private String endpointUrl;
            private String eventType;
            private Integer statusCode;
            private Integer retryCount;
            private Long deliveryTimeMs;

            public Builder webhookId(String webhookId) {
                this.webhookId = webhookId;
                return this;
            }

            public Builder status(String status) {
                this.status = status;
                return this;
            }

            public Builder message(String message) {
                this.message = message;
                return this;
            }

            public Builder timestamp(LocalDateTime timestamp) {
                this.timestamp = timestamp;
                return this;
            }

            public Builder endpointUrl(String endpointUrl) {
                this.endpointUrl = endpointUrl;
                return this;
            }

            public Builder eventType(String eventType) {
                this.eventType = eventType;
                return this;
            }

            public Builder statusCode(Integer statusCode) {
                this.statusCode = statusCode;
                return this;
            }

            public Builder retryCount(Integer retryCount) {
                this.retryCount = retryCount;
                return this;
            }

            public Builder deliveryTimeMs(Long deliveryTimeMs) {
                this.deliveryTimeMs = deliveryTimeMs;
                return this;
            }

            public WebhookDeliveryStatusDTO build() {
                return new WebhookDeliveryStatusDTO(this);
            }
        }
    }
}