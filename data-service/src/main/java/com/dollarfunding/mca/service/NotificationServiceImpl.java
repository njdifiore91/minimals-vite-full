package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.dollarfunding.mca.exception.WebhookDeliveryException;
import com.dollarfunding.mca.messaging.NotificationMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import com.dollarfunding.mca.repository.WebhookRepository;
import com.dollarfunding.mca.util.Constants;
import com.dollarfunding.mca.util.JsonUtil;
import com.dollarfunding.mca.util.TraceUtil;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

/**
 * Implementation of the NotificationService interface that manages notification delivery
 * for the MCA application. It sends notifications about application status changes,
 * document processing results, and system events through various channels (webhook, email, etc.).
 * 
 * This class interacts with WebhookService for webhook delivery and implements asynchronous
 * notification processing using RabbitMQ.
 */
@Service
public class NotificationServiceImpl implements NotificationService {

    private static final Logger logger = LoggerFactory.getLogger(NotificationServiceImpl.class);
    
    private final WebhookService webhookService;
    private final WebhookRepository webhookRepository;
    private final NotificationProducer notificationProducer;
    
    @Value("${notification.templates.path:classpath:templates/notifications/}")
    private String templatePath;
    
    @Value("${notification.retry.max-attempts:3}")
    private int maxRetryAttempts;
    
    @Value("${notification.retry.delay-ms:5000}")
    private long retryDelayMs;
    
    @Value("${notification.async.enabled:true}")
    private boolean asyncEnabled;

    @Autowired
    public NotificationServiceImpl(WebhookService webhookService, 
                                  WebhookRepository webhookRepository,
                                  NotificationProducer notificationProducer) {
        this.webhookService = webhookService;
        this.webhookRepository = webhookRepository;
        this.notificationProducer = notificationProducer;
    }

    /**
     * Sends a notification about an application status change.
     * 
     * @param application The application that had a status change
     * @param previousStatus The previous status of the application
     * @param newStatus The new status of the application
     * @return true if the notification was sent successfully, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean sendApplicationStatusNotification(Application application, String previousStatus, String newStatus) {
        logger.info("Sending application status notification for application ID: {}, status change: {} -> {}", 
                application.getId(), previousStatus, newStatus);
        
        EventType eventType = EventType.APPLICATION_UPDATED;
        
        // Create notification payload
        Map<String, Object> payload = createApplicationStatusPayload(application, previousStatus, newStatus);
        
        // Send notification through appropriate channels
        return sendNotification(eventType, payload, application.getId());
    }

    /**
     * Sends a notification about a new application being created.
     * 
     * @param application The newly created application
     * @return true if the notification was sent successfully, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean sendApplicationCreatedNotification(Application application) {
        logger.info("Sending application created notification for application ID: {}", application.getId());
        
        EventType eventType = EventType.APPLICATION_CREATED;
        
        // Create notification payload
        Map<String, Object> payload = createApplicationPayload(application);
        
        // Send notification through appropriate channels
        return sendNotification(eventType, payload, application.getId());
    }

    /**
     * Sends a notification about an application being approved.
     * 
     * @param application The approved application
     * @return true if the notification was sent successfully, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean sendApplicationApprovedNotification(Application application) {
        logger.info("Sending application approved notification for application ID: {}", application.getId());
        
        EventType eventType = EventType.APPLICATION_APPROVED;
        
        // Create notification payload
        Map<String, Object> payload = createApplicationPayload(application);
        payload.put("approvedAt", LocalDateTime.now().toString());
        
        // Send notification through appropriate channels
        return sendNotification(eventType, payload, application.getId());
    }

    /**
     * Sends a notification about an application being rejected.
     * 
     * @param application The rejected application
     * @param reason The reason for rejection
     * @return true if the notification was sent successfully, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean sendApplicationRejectedNotification(Application application, String reason) {
        logger.info("Sending application rejected notification for application ID: {}", application.getId());
        
        EventType eventType = EventType.APPLICATION_REJECTED;
        
        // Create notification payload
        Map<String, Object> payload = createApplicationPayload(application);
        payload.put("rejectedAt", LocalDateTime.now().toString());
        payload.put("reason", reason);
        
        // Send notification through appropriate channels
        return sendNotification(eventType, payload, application.getId());
    }

    /**
     * Sends a notification about a document being uploaded.
     * 
     * @param document The uploaded document
     * @param applicationId The ID of the application associated with the document
     * @return true if the notification was sent successfully, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean sendDocumentUploadedNotification(Document document, Long applicationId) {
        logger.info("Sending document uploaded notification for document ID: {}, application ID: {}", 
                document.getId(), applicationId);
        
        EventType eventType = EventType.DOCUMENT_UPLOADED;
        
        // Create notification payload
        Map<String, Object> payload = createDocumentPayload(document, applicationId);
        
        // Send notification through appropriate channels
        return sendNotification(eventType, payload, applicationId);
    }

    /**
     * Sends a notification about a document being processed.
     * 
     * @param document The processed document
     * @param applicationId The ID of the application associated with the document
     * @param extractionResults The results of the document data extraction
     * @return true if the notification was sent successfully, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean sendDocumentProcessedNotification(Document document, Long applicationId, Map<String, Object> extractionResults) {
        logger.info("Sending document processed notification for document ID: {}, application ID: {}", 
                document.getId(), applicationId);
        
        EventType eventType = EventType.DOCUMENT_PROCESSED;
        
        // Create notification payload
        Map<String, Object> payload = createDocumentPayload(document, applicationId);
        payload.put("extractionResults", extractionResults);
        payload.put("processedAt", LocalDateTime.now().toString());
        
        // Send notification through appropriate channels
        return sendNotification(eventType, payload, applicationId);
    }

    /**
     * Sends a system event notification.
     * 
     * @param eventType The type of system event
     * @param payload The event payload
     * @return true if the notification was sent successfully, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean sendSystemEventNotification(EventType eventType, Map<String, Object> payload) {
        logger.info("Sending system event notification for event type: {}", eventType);
        
        // Send notification through appropriate channels
        return sendNotification(eventType, payload, null);
    }

    /**
     * Retrieves notification templates from the cache or loads them from the filesystem.
     * 
     * @param templateName The name of the template to retrieve
     * @return The template content as a string
     */
    @Override
    @Cacheable(value = "notificationTemplates", key = "#templateName")
    public String getNotificationTemplate(String templateName) {
        logger.debug("Loading notification template: {}", templateName);
        
        // In a real implementation, this would load the template from the filesystem or database
        // For simplicity, we're returning a placeholder template
        return "Template for " + templateName;
    }

    /**
     * Refreshes the notification template cache.
     * 
     * @param templateName The name of the template to refresh, or null to refresh all templates
     */
    @Override
    @CacheEvict(value = "notificationTemplates", allEntries = true)
    public void refreshNotificationTemplates(String templateName) {
        logger.info("Refreshing notification templates: {}", templateName != null ? templateName : "all");
    }

    /**
     * Tracks the delivery status of a notification.
     * 
     * @param notificationId The ID of the notification
     * @param status The delivery status
     * @param details Additional details about the delivery status
     */
    @Override
    @Transactional
    public void trackNotificationDeliveryStatus(String notificationId, String status, Map<String, Object> details) {
        logger.info("Tracking notification delivery status for notification ID: {}, status: {}", notificationId, status);
        
        // In a real implementation, this would store the delivery status in the database
        // For simplicity, we're just logging it
        logger.info("Notification delivery status: {} for ID: {}, details: {}", status, notificationId, details);
    }

    /**
     * Retries a failed notification delivery.
     * 
     * @param notificationId The ID of the failed notification
     * @param maxAttempts The maximum number of retry attempts
     * @return true if the retry was successful, false otherwise
     */
    @Override
    @Transactional
    public boolean retryFailedNotification(String notificationId, int maxAttempts) {
        logger.info("Retrying failed notification for notification ID: {}, max attempts: {}", notificationId, maxAttempts);
        
        // In a real implementation, this would retrieve the failed notification from the database
        // and attempt to resend it with exponential backoff
        // For simplicity, we're just returning true
        return true;
    }

    /**
     * Sends a notification through all appropriate channels based on the event type.
     * 
     * @param eventType The type of event
     * @param payload The notification payload
     * @param applicationId The ID of the associated application, or null for system events
     * @return true if the notification was sent successfully through at least one channel, false otherwise
     */
    private boolean sendNotification(EventType eventType, Map<String, Object> payload, Long applicationId) {
        String correlationId = TraceUtil.getCurrentCorrelationId();
        String notificationId = java.util.UUID.randomUUID().toString();
        
        // Add metadata to payload
        payload.put("eventType", eventType.name());
        payload.put("timestamp", LocalDateTime.now().toString());
        payload.put("notificationId", notificationId);
        payload.put("correlationId", correlationId);
        
        if (applicationId != null) {
            payload.put("applicationId", applicationId);
        }
        
        boolean success = false;
        
        // Send webhook notifications
        boolean webhookSuccess = sendWebhookNotifications(eventType, payload, notificationId);
        
        // Send to RabbitMQ for asynchronous processing (email, SMS, etc.)
        boolean queueSuccess = sendToNotificationQueue(eventType, payload, notificationId);
        
        // If either channel was successful, consider the notification sent
        success = webhookSuccess || queueSuccess;
        
        // Track delivery status
        trackNotificationDeliveryStatus(notificationId, success ? "SENT" : "FAILED", 
                Map.of("webhookSuccess", webhookSuccess, "queueSuccess", queueSuccess));
        
        return success;
    }

    /**
     * Sends webhook notifications for the given event type.
     * 
     * @param eventType The type of event
     * @param payload The notification payload
     * @param notificationId The ID of the notification
     * @return true if at least one webhook notification was sent successfully, false otherwise
     */
    private boolean sendWebhookNotifications(EventType eventType, Map<String, Object> payload, String notificationId) {
        // Find all active webhooks for this event type
        List<Webhook> webhooks = webhookRepository.findByEventTypeAndActiveTrue(eventType);
        
        if (webhooks.isEmpty()) {
            logger.debug("No active webhooks found for event type: {}", eventType);
            return true; // No webhooks to send, so consider it successful
        }
        
        boolean anySuccess = false;
        
        for (Webhook webhook : webhooks) {
            try {
                // If async is enabled, send webhooks asynchronously
                if (asyncEnabled) {
                    sendWebhookAsync(webhook, payload, notificationId);
                    anySuccess = true; // Assume async delivery will succeed
                } else {
                    // Send webhook synchronously
                    boolean success = webhookService.deliverWebhook(webhook.getId(), payload);
                    anySuccess = anySuccess || success;
                    
                    // Track individual webhook delivery status
                    trackNotificationDeliveryStatus(notificationId + "-webhook-" + webhook.getId(), 
                            success ? "DELIVERED" : "FAILED", Map.of("webhookId", webhook.getId()));
                }
            } catch (WebhookDeliveryException e) {
                logger.error("Failed to deliver webhook notification for event type: {}, webhook ID: {}", 
                        eventType, webhook.getId(), e);
                
                // Track failure
                trackNotificationDeliveryStatus(notificationId + "-webhook-" + webhook.getId(), 
                        "FAILED", Map.of("webhookId", webhook.getId(), "error", e.getMessage()));
            }
        }
        
        return anySuccess;
    }

    /**
     * Sends a webhook notification asynchronously.
     * 
     * @param webhook The webhook to send
     * @param payload The notification payload
     * @param notificationId The ID of the notification
     * @return A CompletableFuture that completes when the webhook delivery is done
     */
    @Async
    private CompletableFuture<Boolean> sendWebhookAsync(Webhook webhook, Map<String, Object> payload, String notificationId) {
        try {
            boolean success = webhookService.deliverWebhook(webhook.getId(), payload);
            
            // Track individual webhook delivery status
            trackNotificationDeliveryStatus(notificationId + "-webhook-" + webhook.getId(), 
                    success ? "DELIVERED" : "FAILED", Map.of("webhookId", webhook.getId()));
            
            return CompletableFuture.completedFuture(success);
        } catch (WebhookDeliveryException e) {
            logger.error("Failed to deliver async webhook notification for webhook ID: {}", webhook.getId(), e);
            
            // Track failure
            trackNotificationDeliveryStatus(notificationId + "-webhook-" + webhook.getId(), 
                    "FAILED", Map.of("webhookId", webhook.getId(), "error", e.getMessage()));
            
            // Implement retry logic with exponential backoff
            return retryWebhookDelivery(webhook, payload, notificationId, 1);
        }
    }

    /**
     * Retries a webhook delivery with exponential backoff.
     * 
     * @param webhook The webhook to retry
     * @param payload The notification payload
     * @param notificationId The ID of the notification
     * @param attempt The current attempt number
     * @return A CompletableFuture that completes when the webhook delivery is done
     */
    private CompletableFuture<Boolean> retryWebhookDelivery(Webhook webhook, Map<String, Object> payload, 
                                                         String notificationId, int attempt) {
        if (attempt > maxRetryAttempts) {
            logger.error("Max retry attempts reached for webhook ID: {}, notification ID: {}", 
                    webhook.getId(), notificationId);
            return CompletableFuture.completedFuture(false);
        }
        
        // Calculate exponential backoff delay
        long delay = retryDelayMs * (long) Math.pow(2, attempt - 1);
        
        logger.info("Scheduling webhook retry for webhook ID: {}, notification ID: {}, attempt: {}, delay: {}ms", 
                webhook.getId(), notificationId, attempt, delay);
        
        return CompletableFuture.supplyAsync(() -> {
            try {
                // Sleep for the calculated delay
                Thread.sleep(delay);
                
                // Retry the webhook delivery
                boolean success = webhookService.deliverWebhook(webhook.getId(), payload);
                
                // Track retry status
                trackNotificationDeliveryStatus(notificationId + "-webhook-" + webhook.getId() + "-retry-" + attempt, 
                        success ? "DELIVERED" : "FAILED", 
                        Map.of("webhookId", webhook.getId(), "attempt", attempt));
                
                return success;
            } catch (WebhookDeliveryException | InterruptedException e) {
                logger.error("Failed to deliver webhook notification on retry attempt {}", attempt, e);
                
                // Track retry failure
                trackNotificationDeliveryStatus(notificationId + "-webhook-" + webhook.getId() + "-retry-" + attempt, 
                        "FAILED", 
                        Map.of("webhookId", webhook.getId(), "attempt", attempt, "error", e.getMessage()));
                
                // If interrupted, restore the interrupt status
                if (e instanceof InterruptedException) {
                    Thread.currentThread().interrupt();
                }
                
                // Recursively retry
                return retryWebhookDelivery(webhook, payload, notificationId, attempt + 1).join();
            }
        });
    }

    /**
     * Sends a notification to the RabbitMQ queue for asynchronous processing.
     * 
     * @param eventType The type of event
     * @param payload The notification payload
     * @param notificationId The ID of the notification
     * @return true if the message was sent to the queue successfully, false otherwise
     */
    private boolean sendToNotificationQueue(EventType eventType, Map<String, Object> payload, String notificationId) {
        try {
            // Create notification message
            NotificationMessage message = new NotificationMessage();
            message.setEventType(eventType.name());
            message.setPayload(payload);
            message.setNotificationId(notificationId);
            message.setTimestamp(LocalDateTime.now());
            message.setCorrelationId(TraceUtil.getCurrentCorrelationId());
            
            // Send to RabbitMQ
            notificationProducer.sendNotification(message);
            
            logger.debug("Sent notification to queue: {}", notificationId);
            return true;
        } catch (Exception e) {
            logger.error("Failed to send notification to queue: {}", notificationId, e);
            return false;
        }
    }

    /**
     * Creates a payload for application status notifications.
     * 
     * @param application The application
     * @param previousStatus The previous status
     * @param newStatus The new status
     * @return The notification payload
     */
    private Map<String, Object> createApplicationStatusPayload(Application application, String previousStatus, String newStatus) {
        Map<String, Object> payload = createApplicationPayload(application);
        payload.put("previousStatus", previousStatus);
        payload.put("newStatus", newStatus);
        payload.put("statusChangedAt", LocalDateTime.now().toString());
        return payload;
    }

    /**
     * Creates a payload for application notifications.
     * 
     * @param application The application
     * @return The notification payload
     */
    private Map<String, Object> createApplicationPayload(Application application) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", application.getId());
        payload.put("status", application.getStatus().name());
        payload.put("reviewStatus", application.getReviewStatus().name());
        payload.put("createdAt", application.getCreatedAt().toString());
        payload.put("updatedAt", application.getUpdatedAt().toString());
        
        // Add merchant details if available
        if (application.getMerchantDetails() != null) {
            Map<String, Object> merchantDetails = new HashMap<>();
            merchantDetails.put("id", application.getMerchantDetails().getId());
            merchantDetails.put("legalName", application.getMerchantDetails().getLegalName());
            merchantDetails.put("dbaName", application.getMerchantDetails().getDbaName());
            merchantDetails.put("industry", application.getMerchantDetails().getIndustry());
            payload.put("merchantDetails", merchantDetails);
        }
        
        return payload;
    }

    /**
     * Creates a payload for document notifications.
     * 
     * @param document The document
     * @param applicationId The ID of the associated application
     * @return The notification payload
     */
    private Map<String, Object> createDocumentPayload(Document document, Long applicationId) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("documentId", document.getId());
        payload.put("applicationId", applicationId);
        payload.put("documentType", document.getType().name());
        payload.put("classification", document.getClassification());
        payload.put("uploadedAt", document.getUploadedAt().toString());
        
        // Add metadata if available
        if (document.getMetadata() != null) {
            payload.put("metadata", document.getMetadata());
        }
        
        return payload;
    }
}