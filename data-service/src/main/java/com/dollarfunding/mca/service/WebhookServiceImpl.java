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
import com.dollarfunding.mca.util.TraceUtil;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.concurrent.CompletableFuture;

/**
 * Implementation of the WebhookService interface that manages webhook configurations,
 * delivery, and status tracking for the MCA application.
 * <p>
 * This class handles CRUD operations for webhook endpoints, implements HMAC signing
 * for secure payload delivery, and manages retry logic for failed deliveries.
 * It interacts with WebhookRepository for data persistence and implements
 * asynchronous webhook delivery for improved performance.
 * </p>
 */
@Service
public class WebhookServiceImpl implements WebhookService {

    private static final Logger logger = LoggerFactory.getLogger(WebhookServiceImpl.class);
    private static final String HMAC_SHA256_ALGORITHM = "HmacSHA256";
    private static final Random random = new Random();

    private final WebhookRepository webhookRepository;
    private final RestTemplate restTemplate;

    @Value("${webhook.delivery.timeout:5000}")
    private int webhookDeliveryTimeout;

    @Value("${webhook.retry.max-attempts:3}")
    private int maxRetryAttempts;

    @Value("${webhook.retry.initial-delay-ms:1000}")
    private long initialRetryDelayMs;

    @Value("${webhook.retry.max-delay-ms:60000}")
    private long maxRetryDelayMs;

    @Value("${webhook.retry.jitter-factor:0.5}")
    private double jitterFactor;

    /**
     * Constructor with required dependencies.
     *
     * @param webhookRepository The repository for webhook data persistence
     * @param restTemplate The REST template for making HTTP requests
     */
    @Autowired
    public WebhookServiceImpl(WebhookRepository webhookRepository, RestTemplate restTemplate) {
        this.webhookRepository = webhookRepository;
        this.restTemplate = restTemplate;
    }

    /**
     * Creates a new webhook configuration.
     *
     * @param webhookRequestDTO The webhook configuration data
     * @return The created webhook as a WebhookResponseDTO
     */
    @Override
    @Transactional
    @CacheEvict(value = "webhooks", allEntries = true)
    public WebhookResponseDTO createWebhook(WebhookRequestDTO webhookRequestDTO) {
        logger.info("Creating new webhook for event type: {}", webhookRequestDTO.getEventType());

        // Validate event type
        if (!webhookRequestDTO.isValidEventType()) {
            throw new IllegalArgumentException("Invalid event type: " + webhookRequestDTO.getEventType());
        }

        // Check if webhook with same URL already exists
        if (webhookRepository.existsByEndpointUrl(webhookRequestDTO.getEndpointUrl())) {
            throw new IllegalArgumentException("Webhook with URL " + webhookRequestDTO.getEndpointUrl() + " already exists");
        }

        // Convert DTO to entity and save
        Webhook webhook = webhookRequestDTO.toEntity();
        webhook = webhookRepository.save(webhook);

        logger.debug("Created webhook with ID: {}", webhook.getId());
        return WebhookResponseDTO.fromEntity(webhook);
    }

    /**
     * Retrieves all webhook configurations.
     *
     * @return A list of all webhooks as WebhookResponseDTOs
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(value = "webhooks", key = "'all'")
    public List<WebhookResponseDTO> getAllWebhooks() {
        logger.debug("Retrieving all webhooks");
        List<Webhook> webhooks = webhookRepository.findAll();
        return WebhookResponseDTO.fromEntities(webhooks);
    }

    /**
     * Retrieves a webhook configuration by ID.
     *
     * @param id The ID of the webhook to retrieve
     * @return The webhook as a WebhookResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(value = "webhooks", key = "#id")
    public WebhookResponseDTO getWebhookById(Long id) {
        logger.debug("Retrieving webhook with ID: {}", id);
        Webhook webhook = findWebhookById(id);
        return WebhookResponseDTO.fromEntity(webhook);
    }

    /**
     * Updates an existing webhook configuration.
     *
     * @param id The ID of the webhook to update
     * @param webhookRequestDTO The updated webhook configuration data
     * @return The updated webhook as a WebhookResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    @Override
    @Transactional
    @CacheEvict(value = "webhooks", allEntries = true)
    public WebhookResponseDTO updateWebhook(Long id, WebhookRequestDTO webhookRequestDTO) {
        logger.info("Updating webhook with ID: {}", id);

        // Validate event type
        if (!webhookRequestDTO.isValidEventType()) {
            throw new IllegalArgumentException("Invalid event type: " + webhookRequestDTO.getEventType());
        }

        // Find existing webhook
        Webhook webhook = findWebhookById(id);

        // Check if another webhook with the same URL exists (excluding this one)
        Optional<Webhook> existingWebhook = webhookRepository.findByEndpointUrl(webhookRequestDTO.getEndpointUrl());
        if (existingWebhook.isPresent() && !existingWebhook.get().getId().equals(id)) {
            throw new IllegalArgumentException("Another webhook with URL " + webhookRequestDTO.getEndpointUrl() + " already exists");
        }

        // Update webhook with new values
        webhook = webhookRequestDTO.updateEntity(webhook);
        webhook = webhookRepository.save(webhook);

        logger.debug("Updated webhook with ID: {}", webhook.getId());
        return WebhookResponseDTO.fromEntity(webhook);
    }

    /**
     * Deletes a webhook configuration.
     *
     * @param id The ID of the webhook to delete
     * @throws ResourceNotFoundException if the webhook is not found
     */
    @Override
    @Transactional
    @CacheEvict(value = "webhooks", allEntries = true)
    public void deleteWebhook(Long id) {
        logger.info("Deleting webhook with ID: {}", id);
        Webhook webhook = findWebhookById(id);
        webhookRepository.delete(webhook);
        logger.debug("Deleted webhook with ID: {}", id);
    }

    /**
     * Retrieves all active webhooks for a specific event type.
     *
     * @param eventType The event type to filter by
     * @return A list of active webhooks for the specified event type
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(value = "webhooks", key = "'eventType-' + #eventType.name()")
    public List<Webhook> getActiveWebhooksByEventType(EventType eventType) {
        logger.debug("Retrieving active webhooks for event type: {}", eventType);
        return webhookRepository.findByEventTypeAndActive(eventType, true);
    }

    /**
     * Tests a webhook delivery with a custom payload.
     *
     * @param id The ID of the webhook to test
     * @param testRequestDTO The test request data
     * @return The test results as a WebhookTestResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    @Override
    @Transactional(readOnly = true)
    public WebhookTestResponseDTO testWebhook(Long id, WebhookTestRequestDTO testRequestDTO) {
        logger.info("Testing webhook with ID: {}", id);
        Webhook webhook = findWebhookById(id);

        // Validate webhook ID in request matches path parameter
        if (!testRequestDTO.getWebhookId().equals(id.toString())) {
            throw new IllegalArgumentException("Webhook ID in request body does not match path parameter");
        }

        // Convert payload to JSON string
        String payload = JsonUtil.toJson(testRequestDTO.getTestPayload());

        // If async delivery is requested, deliver asynchronously
        if (Boolean.TRUE.equals(testRequestDTO.getAsync())) {
            logger.debug("Delivering test webhook asynchronously");
            deliverWebhookAsync(webhook, testRequestDTO.getTestPayload());
            
            // Return immediate response for async delivery
            return WebhookTestResponseDTO.builder()
                    .success(true)
                    .deliveryTimestamp(LocalDateTime.now())
                    .responseCode(null)
                    .responseBody("Webhook delivery initiated asynchronously")
                    .deliveryTimeMs(0L)
                    .signatureVerified(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()))
                    .generatedSignature(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()) ? 
                            generateHmacSignature(payload, webhook.getSecretKey()) : null)
                    .signatureHeader(webhook.getSignatureHeader())
                    .build();
        }

        // For synchronous delivery, deliver and return results
        try {
            long startTime = System.currentTimeMillis();
            
            // Prepare headers with HMAC signature if requested
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            if (Boolean.TRUE.equals(testRequestDTO.getIncludeSignature())) {
                String signature = generateHmacSignature(payload, webhook.getSecretKey());
                headers.set(webhook.getSignatureHeader(), signature);
            }
            
            // Create HTTP entity with headers and payload
            HttpEntity<String> requestEntity = new HttpEntity<>(payload, headers);
            
            // Send request and measure time
            ResponseEntity<String> response = restTemplate.postForEntity(
                    webhook.getEndpointUrl(), requestEntity, String.class);
            
            long endTime = System.currentTimeMillis();
            long deliveryTime = endTime - startTime;
            
            // Build successful response
            return WebhookTestResponseDTO.builder()
                    .success(true)
                    .deliveryTimestamp(LocalDateTime.now())
                    .responseCode(response.getStatusCodeValue())
                    .responseBody(response.getBody())
                    .deliveryTimeMs(deliveryTime)
                    .signatureVerified(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()))
                    .generatedSignature(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()) ? 
                            generateHmacSignature(payload, webhook.getSecretKey()) : null)
                    .signatureHeader(webhook.getSignatureHeader())
                    .build();
            
        } catch (HttpStatusCodeException e) {
            // Handle HTTP error responses
            return WebhookTestResponseDTO.builder()
                    .success(false)
                    .deliveryTimestamp(LocalDateTime.now())
                    .responseCode(e.getRawStatusCode())
                    .errorMessage("HTTP error: " + e.getStatusCode())
                    .errorDetails(e.getResponseBodyAsString())
                    .signatureVerified(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()))
                    .generatedSignature(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()) ? 
                            generateHmacSignature(payload, webhook.getSecretKey()) : null)
                    .signatureHeader(webhook.getSignatureHeader())
                    .build();
            
        } catch (Exception e) {
            // Handle other errors
            return WebhookTestResponseDTO.builder()
                    .success(false)
                    .deliveryTimestamp(LocalDateTime.now())
                    .errorMessage("Error delivering webhook: " + e.getMessage())
                    .errorDetails(e.getClass().getName() + ": " + e.getMessage())
                    .signatureVerified(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()))
                    .generatedSignature(Boolean.TRUE.equals(testRequestDTO.getIncludeSignature()) ? 
                            generateHmacSignature(payload, webhook.getSecretKey()) : null)
                    .signatureHeader(webhook.getSignatureHeader())
                    .build();
        }
    }

    /**
     * Delivers a webhook notification.
     *
     * @param webhookId The ID of the webhook to deliver
     * @param payload The payload to send
     * @return true if the delivery was successful, false otherwise
     * @throws ResourceNotFoundException if the webhook is not found
     * @throws WebhookDeliveryException if there is an error delivering the webhook
     */
    @Override
    @Transactional
    public boolean deliverWebhook(Long webhookId, Map<String, Object> payload) {
        logger.debug("Delivering webhook with ID: {}", webhookId);
        Webhook webhook = findWebhookById(webhookId);

        // Check if webhook is active
        if (!webhook.getActive()) {
            logger.warn("Webhook with ID {} is inactive, skipping delivery", webhookId);
            return false;
        }

        try {
            // Convert payload to JSON string
            String jsonPayload = JsonUtil.toJson(payload);
            
            // Prepare headers with HMAC signature
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            // Generate and add HMAC signature
            String signature = generateHmacSignature(jsonPayload, webhook.getSecretKey());
            headers.set(webhook.getSignatureHeader(), signature);
            
            // Add correlation ID for tracing
            String correlationId = TraceUtil.getCurrentCorrelationId();
            if (correlationId != null) {
                headers.set("X-Correlation-ID", correlationId);
            }
            
            // Create HTTP entity with headers and payload
            HttpEntity<String> requestEntity = new HttpEntity<>(jsonPayload, headers);
            
            // Send request
            ResponseEntity<String> response = restTemplate.postForEntity(
                    webhook.getEndpointUrl(), requestEntity, String.class);
            
            // Check if response is successful (2xx)
            boolean success = response.getStatusCode().is2xxSuccessful();
            
            // Update webhook delivery status
            if (success) {
                webhook.recordSuccessfulDelivery();
                webhook.setLastDeliverySuccess(true);
                webhook.setLastDeliveryStatusCode(response.getStatusCodeValue());
                webhook.setLastDeliveryError(null);
                webhook.setSuccessfulDeliveriesCount(webhook.getSuccessfulDeliveriesCount() + 1);
            } else {
                webhook.recordFailedDelivery("Non-2xx response: " + response.getStatusCode());
                webhook.setLastDeliverySuccess(false);
                webhook.setLastDeliveryStatusCode(response.getStatusCodeValue());
                webhook.setLastDeliveryError("Non-2xx response: " + response.getStatusCode());
                webhook.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount() + 1);
            }
            
            webhook.setLastDeliveryAt(LocalDateTime.now());
            webhookRepository.save(webhook);
            
            logger.debug("Webhook delivery result for ID {}: {}", webhookId, success ? "SUCCESS" : "FAILURE");
            return success;
            
        } catch (HttpStatusCodeException e) {
            // Handle HTTP error responses
            String errorMessage = "HTTP error: " + e.getStatusCode() + " - " + e.getResponseBodyAsString();
            logger.error("Webhook delivery failed for ID {}: {}", webhookId, errorMessage);
            
            // Update webhook delivery status
            webhook.recordFailedDelivery(errorMessage);
            webhook.setLastDeliverySuccess(false);
            webhook.setLastDeliveryStatusCode(e.getRawStatusCode());
            webhook.setLastDeliveryError(errorMessage);
            webhook.setLastDeliveryAt(LocalDateTime.now());
            webhook.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount() + 1);
            webhookRepository.save(webhook);
            
            throw new WebhookDeliveryException("Failed to deliver webhook: " + errorMessage, e);
            
        } catch (Exception e) {
            // Handle other errors
            String errorMessage = "Error delivering webhook: " + e.getMessage();
            logger.error("Webhook delivery failed for ID {}: {}", webhookId, errorMessage, e);
            
            // Update webhook delivery status
            webhook.recordFailedDelivery(errorMessage);
            webhook.setLastDeliverySuccess(false);
            webhook.setLastDeliveryStatusCode(null);
            webhook.setLastDeliveryError(errorMessage);
            webhook.setLastDeliveryAt(LocalDateTime.now());
            webhook.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount() + 1);
            webhookRepository.save(webhook);
            
            throw new WebhookDeliveryException("Failed to deliver webhook: " + errorMessage, e);
        }
    }

    /**
     * Delivers a webhook notification asynchronously.
     *
     * @param webhookId The ID of the webhook to deliver
     * @param payload The payload to send
     * @return A CompletableFuture that completes when the webhook delivery is done
     * @throws ResourceNotFoundException if the webhook is not found
     */
    @Override
    @Async
    @Transactional
    public CompletableFuture<Boolean> deliverWebhookAsync(Long webhookId, Map<String, Object> payload) {
        logger.debug("Delivering webhook asynchronously with ID: {}", webhookId);
        Webhook webhook = findWebhookById(webhookId);
        return deliverWebhookAsync(webhook, payload);
    }

    /**
     * Retries failed webhook deliveries.
     *
     * @return The number of webhooks that were retried
     */
    @Override
    @Transactional
    public int retryFailedWebhooks() {
        logger.info("Retrying failed webhooks");
        List<Webhook> webhooksToRetry = webhookRepository.findWebhooksForRetry();
        
        int retryCount = 0;
        for (Webhook webhook : webhooksToRetry) {
            try {
                // Retrieve the last payload from the webhook (in a real implementation, this would be stored)
                // For simplicity, we're using a placeholder payload
                Map<String, Object> payload = Map.of(
                        "event", "retry",
                        "webhookId", webhook.getId(),
                        "timestamp", LocalDateTime.now().toString(),
                        "retryAttempt", webhook.getFailedAttempts()
                );
                
                // Deliver the webhook asynchronously
                deliverWebhookAsync(webhook, payload);
                retryCount++;
                
            } catch (Exception e) {
                logger.error("Error retrying webhook with ID {}: {}", webhook.getId(), e.getMessage(), e);
            }
        }
        
        logger.info("Retried {} failed webhooks", retryCount);
        return retryCount;
    }

    /**
     * Activates or deactivates a webhook.
     *
     * @param id The ID of the webhook to update
     * @param active Whether the webhook should be active
     * @return The updated webhook as a WebhookResponseDTO
     * @throws ResourceNotFoundException if the webhook is not found
     */
    @Override
    @Transactional
    @CacheEvict(value = "webhooks", allEntries = true)
    public WebhookResponseDTO setWebhookActive(Long id, boolean active) {
        logger.info("Setting webhook with ID {} active status to {}", id, active);
        Webhook webhook = findWebhookById(id);
        webhook.setActive(active);
        webhook = webhookRepository.save(webhook);
        return WebhookResponseDTO.fromEntity(webhook);
    }

    /**
     * Finds a webhook by ID.
     *
     * @param id The ID of the webhook to find
     * @return The webhook entity
     * @throws ResourceNotFoundException if the webhook is not found
     */
    private Webhook findWebhookById(Long id) {
        return webhookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Webhook not found with ID: " + id));
    }

    /**
     * Delivers a webhook notification asynchronously with retry logic.
     *
     * @param webhook The webhook to deliver
     * @param payload The payload to send
     * @return A CompletableFuture that completes when the webhook delivery is done
     */
    private CompletableFuture<Boolean> deliverWebhookAsync(Webhook webhook, Map<String, Object> payload) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                // Convert payload to JSON string
                String jsonPayload = JsonUtil.toJson(payload);
                
                // Prepare headers with HMAC signature
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                
                // Generate and add HMAC signature
                String signature = generateHmacSignature(jsonPayload, webhook.getSecretKey());
                headers.set(webhook.getSignatureHeader(), signature);
                
                // Add correlation ID for tracing
                String correlationId = TraceUtil.getCurrentCorrelationId();
                if (correlationId != null) {
                    headers.set("X-Correlation-ID", correlationId);
                }
                
                // Create HTTP entity with headers and payload
                HttpEntity<String> requestEntity = new HttpEntity<>(jsonPayload, headers);
                
                // Send request
                ResponseEntity<String> response = restTemplate.postForEntity(
                        webhook.getEndpointUrl(), requestEntity, String.class);
                
                // Check if response is successful (2xx)
                boolean success = response.getStatusCode().is2xxSuccessful();
                
                // Update webhook delivery status
                if (success) {
                    webhook.recordSuccessfulDelivery();
                    webhook.setLastDeliverySuccess(true);
                    webhook.setLastDeliveryStatusCode(response.getStatusCodeValue());
                    webhook.setLastDeliveryError(null);
                    webhook.setSuccessfulDeliveriesCount(webhook.getSuccessfulDeliveriesCount() + 1);
                } else {
                    webhook.recordFailedDelivery("Non-2xx response: " + response.getStatusCode());
                    webhook.setLastDeliverySuccess(false);
                    webhook.setLastDeliveryStatusCode(response.getStatusCodeValue());
                    webhook.setLastDeliveryError("Non-2xx response: " + response.getStatusCode());
                    webhook.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount() + 1);
                }
                
                webhook.setLastDeliveryAt(LocalDateTime.now());
                webhookRepository.save(webhook);
                
                logger.debug("Async webhook delivery result for ID {}: {}", webhook.getId(), success ? "SUCCESS" : "FAILURE");
                return success;
                
            } catch (Exception e) {
                // Handle errors
                String errorMessage = "Error delivering webhook: " + e.getMessage();
                logger.error("Async webhook delivery failed for ID {}: {}", webhook.getId(), errorMessage, e);
                
                // Update webhook delivery status
                webhook.recordFailedDelivery(errorMessage);
                webhook.setLastDeliverySuccess(false);
                webhook.setLastDeliveryStatusCode(e instanceof HttpStatusCodeException ? 
                        ((HttpStatusCodeException) e).getRawStatusCode() : null);
                webhook.setLastDeliveryError(errorMessage);
                webhook.setLastDeliveryAt(LocalDateTime.now());
                webhook.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount() + 1);
                webhookRepository.save(webhook);
                
                // Check if we should retry
                if (webhook.shouldRetry()) {
                    return retryWebhookDelivery(webhook, payload, 1);
                }
                
                return false;
            }
        });
    }

    /**
     * Retries a webhook delivery with exponential backoff.
     *
     * @param webhook The webhook to retry
     * @param payload The payload to send
     * @param attempt The current retry attempt number
     * @return true if the delivery was successful, false otherwise
     */
    private boolean retryWebhookDelivery(Webhook webhook, Map<String, Object> payload, int attempt) {
        if (attempt > maxRetryAttempts) {
            logger.error("Max retry attempts reached for webhook ID: {}", webhook.getId());
            return false;
        }
        
        // Calculate exponential backoff delay with jitter
        long delay = calculateExponentialBackoffWithJitter(attempt);
        
        logger.info("Retrying webhook delivery for ID: {}, attempt: {}, delay: {}ms", 
                webhook.getId(), attempt, delay);
        
        try {
            // Sleep for the calculated delay
            Thread.sleep(delay);
            
            // Convert payload to JSON string
            String jsonPayload = JsonUtil.toJson(payload);
            
            // Prepare headers with HMAC signature
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            // Generate and add HMAC signature
            String signature = generateHmacSignature(jsonPayload, webhook.getSecretKey());
            headers.set(webhook.getSignatureHeader(), signature);
            
            // Add correlation ID for tracing
            String correlationId = TraceUtil.getCurrentCorrelationId();
            if (correlationId != null) {
                headers.set("X-Correlation-ID", correlationId);
            }
            
            // Add retry attempt header
            headers.set("X-Retry-Attempt", String.valueOf(attempt));
            
            // Create HTTP entity with headers and payload
            HttpEntity<String> requestEntity = new HttpEntity<>(jsonPayload, headers);
            
            // Send request
            ResponseEntity<String> response = restTemplate.postForEntity(
                    webhook.getEndpointUrl(), requestEntity, String.class);
            
            // Check if response is successful (2xx)
            boolean success = response.getStatusCode().is2xxSuccessful();
            
            // Update webhook delivery status
            if (success) {
                webhook.recordSuccessfulDelivery();
                webhook.setLastDeliverySuccess(true);
                webhook.setLastDeliveryStatusCode(response.getStatusCodeValue());
                webhook.setLastDeliveryError(null);
                webhook.setSuccessfulDeliveriesCount(webhook.getSuccessfulDeliveriesCount() + 1);
                webhookRepository.save(webhook);
                
                logger.info("Webhook retry successful for ID: {}, attempt: {}", webhook.getId(), attempt);
                return true;
            } else {
                webhook.recordFailedDelivery("Non-2xx response: " + response.getStatusCode());
                webhook.setLastDeliverySuccess(false);
                webhook.setLastDeliveryStatusCode(response.getStatusCodeValue());
                webhook.setLastDeliveryError("Non-2xx response: " + response.getStatusCode());
                webhook.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount() + 1);
                webhookRepository.save(webhook);
                
                logger.warn("Webhook retry failed for ID: {}, attempt: {}, status: {}", 
                        webhook.getId(), attempt, response.getStatusCode());
                
                // Recursively retry
                return retryWebhookDelivery(webhook, payload, attempt + 1);
            }
            
        } catch (InterruptedException e) {
            // Restore interrupt status
            Thread.currentThread().interrupt();
            logger.error("Webhook retry interrupted for ID: {}, attempt: {}", webhook.getId(), attempt, e);
            return false;
            
        } catch (Exception e) {
            // Handle errors
            String errorMessage = "Error in webhook retry: " + e.getMessage();
            logger.error("Webhook retry failed for ID: {}, attempt: {}", webhook.getId(), attempt, e);
            
            // Update webhook delivery status
            webhook.recordFailedDelivery(errorMessage);
            webhook.setLastDeliverySuccess(false);
            webhook.setLastDeliveryStatusCode(e instanceof HttpStatusCodeException ? 
                    ((HttpStatusCodeException) e).getRawStatusCode() : null);
            webhook.setLastDeliveryError(errorMessage);
            webhook.setLastDeliveryAt(LocalDateTime.now());
            webhook.setFailedDeliveriesCount(webhook.getFailedDeliveriesCount() + 1);
            webhookRepository.save(webhook);
            
            // Recursively retry
            return retryWebhookDelivery(webhook, payload, attempt + 1);
        }
    }

    /**
     * Calculates the exponential backoff delay with jitter for retry attempts.
     *
     * @param attempt The current retry attempt number
     * @return The delay in milliseconds
     */
    private long calculateExponentialBackoffWithJitter(int attempt) {
        // Calculate exponential backoff: initialDelay * 2^attempt
        double exponentialDelay = initialRetryDelayMs * Math.pow(2, attempt - 1);
        
        // Apply jitter: random value between (1-jitterFactor) and (1+jitterFactor) of the delay
        double jitter = 1.0 + jitterFactor * (2 * random.nextDouble() - 1);
        long delay = (long) (exponentialDelay * jitter);
        
        // Cap at maximum delay
        return Math.min(delay, maxRetryDelayMs);
    }

    /**
     * Generates an HMAC-SHA256 signature for a payload using a secret key.
     *
     * @param payload The payload to sign
     * @param secretKey The secret key to use for signing
     * @return The Base64-encoded HMAC signature
     * @throws WebhookDeliveryException if there is an error generating the signature
     */
    private String generateHmacSignature(String payload, String secretKey) {
        try {
            // Create MAC instance with the secret key
            Mac mac = Mac.getInstance(HMAC_SHA256_ALGORITHM);
            SecretKeySpec secretKeySpec = new SecretKeySpec(secretKey.getBytes(StandardCharsets.UTF_8), HMAC_SHA256_ALGORITHM);
            mac.init(secretKeySpec);
            
            // Compute HMAC
            byte[] hmacBytes = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            
            // Encode as Base64
            return Base64.getEncoder().encodeToString(hmacBytes);
            
        } catch (Exception e) {
            throw new WebhookDeliveryException("Error generating HMAC signature: " + e.getMessage(), e);
        }
    }
}