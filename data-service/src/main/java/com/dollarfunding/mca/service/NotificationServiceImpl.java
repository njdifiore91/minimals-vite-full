package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.messaging.MessagingException;
import com.dollarfunding.mca.messaging.NotificationMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import com.dollarfunding.mca.util.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Implementation of the NotificationService interface that manages notification delivery
 * for the MCA application. It sends notifications about application status changes,
 * document processing results, and system events through various channels (webhook, email, etc.).
 * 
 * This class interacts with NotificationProducer for RabbitMQ message publishing and implements
 * asynchronous notification processing. It also manages notification templates and tracks
 * delivery status.
 */
@Service
public class NotificationServiceImpl implements NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationServiceImpl.class);
    
    private final NotificationProducer notificationProducer;
    private final ResourceLoader resourceLoader;
    
    // In-memory store for notification delivery status tracking
    private final Map<String, Map<String, Object>> notificationStatusMap = new ConcurrentHashMap<>();
    
    // Cache for notification templates
    private final Map<String, String> templateCache = new ConcurrentHashMap<>();
    
    @Value("${application.notifications.templates.path:classpath:templates/notifications/}")
    private String templatesPath;
    
    @Value("${application.notifications.default-retry-count:3}")
    private int defaultRetryCount;
    
    @Value("${application.notifications.webhook-enabled:true}")
    private boolean webhookEnabled;
    
    @Value("${application.notifications.email-enabled:false}")
    private boolean emailEnabled;
    
    /**
     * Constructs a new NotificationServiceImpl with the specified dependencies.
     *
     * @param notificationProducer The producer for sending notification messages to RabbitMQ
     * @param resourceLoader The resource loader for loading notification templates
     */
    @Autowired
    public NotificationServiceImpl(NotificationProducer notificationProducer, ResourceLoader resourceLoader) {
        this.notificationProducer = notificationProducer;
        this.resourceLoader = resourceLoader;
        
        // Pre-load common templates
        try {
            loadTemplate("application-status-change");
            loadTemplate("application-created");
            loadTemplate("application-approved");
            loadTemplate("application-rejected");
            loadTemplate("document-uploaded");
            loadTemplate("document-processed");
            loadTemplate("system-event");
        } catch (Exception e) {
            log.warn("Failed to pre-load notification templates: {}", e.getMessage());
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean sendApplicationStatusNotification(Application application, String previousStatus, String newStatus) {
        if (application == null) {
            log.error("Cannot send status notification for null application");
            return false;
        }
        
        log.info("Sending application status notification for application ID: {}, status change: {} -> {}", 
                application.getId(), previousStatus, newStatus);
        
        try {
            // Create payload with application details and status change information
            Map<String, Object> payload = new HashMap<>();
            payload.put("applicationId", application.getId().toString());
            payload.put("previousStatus", previousStatus);
            payload.put("newStatus", newStatus);
            payload.put("timestamp", LocalDateTime.now().toString());
            
            // Add merchant details if available
            if (application.getMerchantDetails() != null) {
                Map<String, Object> merchantData = new HashMap<>();
                merchantData.put("legalName", application.getMerchantDetails().getLegalName());
                merchantData.put("dbaName", application.getMerchantDetails().getDbaName());
                merchantData.put("industry", application.getMerchantDetails().getIndustry());
                payload.put("merchant", merchantData);
            }
            
            // Add metadata from application
            payload.put("metadata", application.getMetadata());
            
            // Create recipients list
            List<NotificationMessage.Recipient> recipients = getRecipientsForApplication(application);
            
            // Send notification via RabbitMQ
            String notificationId = notificationProducer.publishStatusUpdate(
                    application.getId().toString(),
                    newStatus,
                    application.getMetadata(),
                    recipients);
            
            // Track notification status
            trackNotificationDeliveryStatus(notificationId, "SENT", Map.of(
                    "applicationId", application.getId().toString(),
                    "notificationType", "STATUS_UPDATE",
                    "sentAt", LocalDateTime.now().toString()
            ));
            
            return true;
        } catch (MessagingException e) {
            log.error("Failed to send application status notification: {}", e.getMessage());
            return false;
        } catch (Exception e) {
            log.error("Unexpected error sending application status notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean sendApplicationCreatedNotification(Application application) {
        if (application == null) {
            log.error("Cannot send creation notification for null application");
            return false;
        }
        
        log.info("Sending application created notification for application ID: {}", application.getId());
        
        try {
            // Create payload with application details
            Map<String, Object> payload = new HashMap<>();
            payload.put("applicationId", application.getId().toString());
            payload.put("status", application.getStatus().name());
            payload.put("createdAt", application.getCreatedAt().toString());
            
            // Add merchant details if available
            if (application.getMerchantDetails() != null) {
                Map<String, Object> merchantData = new HashMap<>();
                merchantData.put("legalName", application.getMerchantDetails().getLegalName());
                merchantData.put("dbaName", application.getMerchantDetails().getDbaName());
                merchantData.put("industry", application.getMerchantDetails().getIndustry());
                payload.put("merchant", merchantData);
            }
            
            // Create recipients list
            List<NotificationMessage.Recipient> recipients = getRecipientsForApplication(application);
            
            // Send notification via RabbitMQ
            String notificationId = notificationProducer.publishNotification(
                    NotificationMessage.NotificationType.APPLICATION_CREATED,
                    NotificationMessage.NotificationPriority.HIGH,
                    payload,
                    recipients);
            
            // Track notification status
            trackNotificationDeliveryStatus(notificationId, "SENT", Map.of(
                    "applicationId", application.getId().toString(),
                    "notificationType", "APPLICATION_CREATED",
                    "sentAt", LocalDateTime.now().toString()
            ));
            
            return true;
        } catch (MessagingException e) {
            log.error("Failed to send application created notification: {}", e.getMessage());
            return false;
        } catch (Exception e) {
            log.error("Unexpected error sending application created notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean sendApplicationApprovedNotification(Application application) {
        if (application == null) {
            log.error("Cannot send approval notification for null application");
            return false;
        }
        
        log.info("Sending application approved notification for application ID: {}", application.getId());
        
        try {
            // Create payload with application details
            Map<String, Object> payload = new HashMap<>();
            payload.put("applicationId", application.getId().toString());
            payload.put("status", application.getStatus().name());
            payload.put("approvedAt", LocalDateTime.now().toString());
            
            // Add merchant details if available
            if (application.getMerchantDetails() != null) {
                Map<String, Object> merchantData = new HashMap<>();
                merchantData.put("legalName", application.getMerchantDetails().getLegalName());
                merchantData.put("dbaName", application.getMerchantDetails().getDbaName());
                merchantData.put("industry", application.getMerchantDetails().getIndustry());
                payload.put("merchant", merchantData);
            }
            
            // Add metadata from application
            payload.put("metadata", application.getMetadata());
            
            // Create recipients list
            List<NotificationMessage.Recipient> recipients = getRecipientsForApplication(application);
            
            // Send notification via RabbitMQ
            String notificationId = notificationProducer.publishCompletionNotification(
                    application.getId().toString(),
                    "APPROVED",
                    application.getMetadata(),
                    recipients);
            
            // Track notification status
            trackNotificationDeliveryStatus(notificationId, "SENT", Map.of(
                    "applicationId", application.getId().toString(),
                    "notificationType", "APPLICATION_APPROVED",
                    "sentAt", LocalDateTime.now().toString()
            ));
            
            return true;
        } catch (MessagingException e) {
            log.error("Failed to send application approved notification: {}", e.getMessage());
            return false;
        } catch (Exception e) {
            log.error("Unexpected error sending application approved notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean sendApplicationRejectedNotification(Application application, String reason) {
        if (application == null) {
            log.error("Cannot send rejection notification for null application");
            return false;
        }
        
        log.info("Sending application rejected notification for application ID: {}, reason: {}", 
                application.getId(), reason);
        
        try {
            // Create payload with application details and rejection reason
            Map<String, Object> payload = new HashMap<>();
            payload.put("applicationId", application.getId().toString());
            payload.put("status", application.getStatus().name());
            payload.put("rejectedAt", LocalDateTime.now().toString());
            payload.put("reason", reason);
            
            // Add merchant details if available
            if (application.getMerchantDetails() != null) {
                Map<String, Object> merchantData = new HashMap<>();
                merchantData.put("legalName", application.getMerchantDetails().getLegalName());
                merchantData.put("dbaName", application.getMerchantDetails().getDbaName());
                merchantData.put("industry", application.getMerchantDetails().getIndustry());
                payload.put("merchant", merchantData);
            }
            
            // Add metadata from application
            payload.put("metadata", application.getMetadata());
            
            // Create recipients list
            List<NotificationMessage.Recipient> recipients = getRecipientsForApplication(application);
            
            // Send notification via RabbitMQ
            String notificationId = notificationProducer.publishCompletionNotification(
                    application.getId().toString(),
                    "REJECTED",
                    Map.of("reason", reason),
                    recipients);
            
            // Track notification status
            trackNotificationDeliveryStatus(notificationId, "SENT", Map.of(
                    "applicationId", application.getId().toString(),
                    "notificationType", "APPLICATION_REJECTED",
                    "sentAt", LocalDateTime.now().toString(),
                    "reason", reason
            ));
            
            return true;
        } catch (MessagingException e) {
            log.error("Failed to send application rejected notification: {}", e.getMessage());
            return false;
        } catch (Exception e) {
            log.error("Unexpected error sending application rejected notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean sendDocumentUploadedNotification(Document document, Long applicationId) {
        if (document == null) {
            log.error("Cannot send document uploaded notification for null document");
            return false;
        }
        
        log.info("Sending document uploaded notification for document ID: {}, application ID: {}", 
                document.getId(), applicationId);
        
        try {
            // Create payload with document details
            Map<String, Object> payload = new HashMap<>();
            payload.put("documentId", document.getId().toString());
            payload.put("applicationId", document.getApplicationId().toString());
            payload.put("documentType", document.getType().name());
            payload.put("classification", document.getClassification().name());
            payload.put("uploadedAt", document.getUploadedAt().toString());
            payload.put("fileName", document.getFileName());
            payload.put("confidenceScore", document.getConfidenceScore());
            
            // Add metadata from document
            payload.put("metadata", document.getMetadata());
            
            // Create recipients list based on application ID
            List<NotificationMessage.Recipient> recipients = getRecipientsForDocument(document);
            
            // Send notification via RabbitMQ
            String notificationId = notificationProducer.publishNotification(
                    NotificationMessage.NotificationType.DOCUMENT_RECEIVED,
                    NotificationMessage.NotificationPriority.MEDIUM,
                    payload,
                    recipients);
            
            // Track notification status
            trackNotificationDeliveryStatus(notificationId, "SENT", Map.of(
                    "documentId", document.getId().toString(),
                    "applicationId", document.getApplicationId().toString(),
                    "notificationType", "DOCUMENT_UPLOADED",
                    "sentAt", LocalDateTime.now().toString()
            ));
            
            return true;
        } catch (MessagingException e) {
            log.error("Failed to send document uploaded notification: {}", e.getMessage());
            return false;
        } catch (Exception e) {
            log.error("Unexpected error sending document uploaded notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean sendDocumentProcessedNotification(Document document, Long applicationId, Map<String, Object> extractionResults) {
        if (document == null) {
            log.error("Cannot send document processed notification for null document");
            return false;
        }
        
        log.info("Sending document processed notification for document ID: {}, application ID: {}", 
                document.getId(), applicationId);
        
        try {
            // Create payload with document details and extraction results
            Map<String, Object> payload = new HashMap<>();
            payload.put("documentId", document.getId().toString());
            payload.put("applicationId", document.getApplicationId().toString());
            payload.put("documentType", document.getType().name());
            payload.put("classification", document.getClassification().name());
            payload.put("processedAt", LocalDateTime.now().toString());
            payload.put("confidenceScore", document.getConfidenceScore());
            
            // Add extraction results if available
            if (extractionResults != null && !extractionResults.isEmpty()) {
                payload.put("extractionResults", extractionResults);
            }
            
            // Add metadata from document
            payload.put("metadata", document.getMetadata());
            
            // Create recipients list based on application ID
            List<NotificationMessage.Recipient> recipients = getRecipientsForDocument(document);
            
            // Send notification via RabbitMQ
            String notificationId = notificationProducer.publishNotification(
                    NotificationMessage.NotificationType.DOCUMENT_PROCESSED,
                    NotificationMessage.NotificationPriority.MEDIUM,
                    payload,
                    recipients);
            
            // Track notification status
            trackNotificationDeliveryStatus(notificationId, "SENT", Map.of(
                    "documentId", document.getId().toString(),
                    "applicationId", document.getApplicationId().toString(),
                    "notificationType", "DOCUMENT_PROCESSED",
                    "sentAt", LocalDateTime.now().toString()
            ));
            
            return true;
        } catch (MessagingException e) {
            log.error("Failed to send document processed notification: {}", e.getMessage());
            return false;
        } catch (Exception e) {
            log.error("Unexpected error sending document processed notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean sendSystemEventNotification(EventType eventType, Map<String, Object> payload) {
        if (eventType == null) {
            log.error("Cannot send system event notification for null event type");
            return false;
        }
        
        log.info("Sending system event notification for event type: {}", eventType.name());
        
        try {
            // Create complete payload with event details
            Map<String, Object> completePayload = new HashMap<>();
            completePayload.put("eventType", eventType.name());
            completePayload.put("eventId", "evt_" + UUID.randomUUID().toString().replace("-", ""));
            completePayload.put("timestamp", LocalDateTime.now().toString());
            
            // Add custom payload if available
            if (payload != null && !payload.isEmpty()) {
                completePayload.put("data", payload);
            } else {
                // Use sample payload from EventType if no custom payload provided
                completePayload.put("data", eventType.generateSamplePayload().get("data"));
            }
            
            // Create recipients list for system events
            List<NotificationMessage.Recipient> recipients = getRecipientsForSystemEvent(eventType);
            
            // Determine notification priority based on event type
            NotificationMessage.NotificationPriority priority = getSystemEventPriority(eventType);
            
            // Send notification via RabbitMQ
            String notificationId = notificationProducer.publishNotification(
                    NotificationMessage.NotificationType.SYSTEM,
                    priority,
                    completePayload,
                    recipients);
            
            // Track notification status
            trackNotificationDeliveryStatus(notificationId, "SENT", Map.of(
                    "eventType", eventType.name(),
                    "notificationType", "SYSTEM_EVENT",
                    "sentAt", LocalDateTime.now().toString()
            ));
            
            return true;
        } catch (MessagingException e) {
            log.error("Failed to send system event notification: {}", e.getMessage());
            return false;
        } catch (Exception e) {
            log.error("Unexpected error sending system event notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Cacheable(value = "notificationTemplates", key = "#templateName")
    public String getNotificationTemplate(String templateName) {
        if (templateName == null || templateName.isEmpty()) {
            log.error("Cannot get template with null or empty name");
            return null;
        }
        
        // Check cache first
        if (templateCache.containsKey(templateName)) {
            return templateCache.get(templateName);
        }
        
        // Load template from filesystem
        try {
            return loadTemplate(templateName);
        } catch (IOException e) {
            log.error("Failed to load notification template '{}': {}", templateName, e.getMessage());
            return null;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @CacheEvict(value = "notificationTemplates", allEntries = true)
    public void refreshNotificationTemplates(String templateName) {
        if (templateName == null || templateName.isEmpty()) {
            // Refresh all templates
            log.info("Refreshing all notification templates");
            templateCache.clear();
            
            // Pre-load common templates
            try {
                loadTemplate("application-status-change");
                loadTemplate("application-created");
                loadTemplate("application-approved");
                loadTemplate("application-rejected");
                loadTemplate("document-uploaded");
                loadTemplate("document-processed");
                loadTemplate("system-event");
            } catch (Exception e) {
                log.warn("Failed to pre-load notification templates during refresh: {}", e.getMessage());
            }
        } else {
            // Refresh specific template
            log.info("Refreshing notification template: {}", templateName);
            templateCache.remove(templateName);
            
            // Reload the template
            try {
                loadTemplate(templateName);
            } catch (Exception e) {
                log.warn("Failed to reload notification template '{}': {}", templateName, e.getMessage());
            }
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public void trackNotificationDeliveryStatus(String notificationId, String status, Map<String, Object> details) {
        if (notificationId == null || notificationId.isEmpty()) {
            log.error("Cannot track notification status with null or empty ID");
            return;
        }
        
        // Create status entry with timestamp
        Map<String, Object> statusEntry = new HashMap<>();
        statusEntry.put("status", status);
        statusEntry.put("timestamp", LocalDateTime.now().toString());
        
        // Add details if available
        if (details != null && !details.isEmpty()) {
            statusEntry.putAll(details);
        }
        
        // Store in status map
        notificationStatusMap.put(notificationId, statusEntry);
        
        log.debug("Tracked notification status for ID {}: {}", notificationId, status);
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean retryFailedNotification(String notificationId, int maxAttempts) {
        if (notificationId == null || notificationId.isEmpty()) {
            log.error("Cannot retry notification with null or empty ID");
            return false;
        }
        
        // Check if notification exists in status map
        if (!notificationStatusMap.containsKey(notificationId)) {
            log.error("Cannot retry unknown notification with ID: {}", notificationId);
            return false;
        }
        
        // Get current status
        Map<String, Object> statusEntry = notificationStatusMap.get(notificationId);
        String currentStatus = (String) statusEntry.get("status");
        
        // Only retry failed notifications
        if (!"FAILED".equals(currentStatus)) {
            log.warn("Cannot retry notification with ID {} because status is {}, not FAILED", 
                    notificationId, currentStatus);
            return false;
        }
        
        // Check retry count
        Integer attemptCount = (Integer) statusEntry.getOrDefault("attemptCount", 0);
        if (attemptCount >= maxAttempts) {
            log.warn("Cannot retry notification with ID {} because max retry attempts ({}) reached", 
                    notificationId, maxAttempts);
            return false;
        }
        
        // Increment attempt count
        statusEntry.put("attemptCount", attemptCount + 1);
        statusEntry.put("lastRetryAt", LocalDateTime.now().toString());
        
        // TODO: Implement actual retry logic by republishing the notification
        // This would require storing the original notification message or reconstructing it
        
        log.info("Retrying notification with ID {}, attempt {}/{}", 
                notificationId, attemptCount + 1, maxAttempts);
        
        // Update status to RETRYING
        statusEntry.put("status", "RETRYING");
        notificationStatusMap.put(notificationId, statusEntry);
        
        return true;
    }
    
    /**
     * Loads a notification template from the filesystem.
     *
     * @param templateName The name of the template to load
     * @return The template content as a string
     * @throws IOException if an error occurs while loading the template
     */
    private String loadTemplate(String templateName) throws IOException {
        // Construct template path
        String templatePath = templatesPath + templateName + ".html";
        
        // Load template resource
        Resource resource = resourceLoader.getResource(templatePath);
        if (!resource.exists()) {
            throw new IOException("Template not found: " + templatePath);
        }
        
        // Read template content
        String templateContent = new String(resource.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        
        // Cache template
        templateCache.put(templateName, templateContent);
        
        return templateContent;
    }
    
    /**
     * Gets the list of recipients for an application notification.
     *
     * @param application The application to get recipients for
     * @return The list of recipients
     */
    private List<NotificationMessage.Recipient> getRecipientsForApplication(Application application) {
        List<NotificationMessage.Recipient> recipients = new ArrayList<>();
        
        // Add webhook recipients if enabled
        if (webhookEnabled) {
            // In a real implementation, this would query the WebhookService for registered webhooks
            // For now, we'll add a placeholder webhook recipient
            recipients.add(new NotificationMessage.Recipient(
                    NotificationMessage.RecipientType.WEBHOOK,
                    "https://api.example.com/webhooks/mca-notifications",
                    "Default Webhook",
                    Map.of("hmacEnabled", true, "hmacAlgorithm", "HmacSHA256")
            ));
        }
        
        // Add email recipients if enabled
        if (emailEnabled) {
            // In a real implementation, this would query for email recipients based on the application
            // For now, we'll add a placeholder email recipient
            recipients.add(new NotificationMessage.Recipient(
                    NotificationMessage.RecipientType.EMAIL,
                    "notifications@example.com",
                    "MCA Notifications",
                    Map.of("template", "application-notification")
            ));
        }
        
        return recipients;
    }
    
    /**
     * Gets the list of recipients for a document notification.
     *
     * @param document The document to get recipients for
     * @return The list of recipients
     */
    private List<NotificationMessage.Recipient> getRecipientsForDocument(Document document) {
        List<NotificationMessage.Recipient> recipients = new ArrayList<>();
        
        // Add webhook recipients if enabled
        if (webhookEnabled) {
            // In a real implementation, this would query the WebhookService for registered webhooks
            // For now, we'll add a placeholder webhook recipient
            recipients.add(new NotificationMessage.Recipient(
                    NotificationMessage.RecipientType.WEBHOOK,
                    "https://api.example.com/webhooks/document-notifications",
                    "Document Webhook",
                    Map.of("hmacEnabled", true, "hmacAlgorithm", "HmacSHA256")
            ));
        }
        
        // Add email recipients if enabled
        if (emailEnabled) {
            // In a real implementation, this would query for email recipients based on the document
            // For now, we'll add a placeholder email recipient
            recipients.add(new NotificationMessage.Recipient(
                    NotificationMessage.RecipientType.EMAIL,
                    "documents@example.com",
                    "Document Notifications",
                    Map.of("template", "document-notification")
            ));
        }
        
        return recipients;
    }
    
    /**
     * Gets the list of recipients for a system event notification.
     *
     * @param eventType The event type to get recipients for
     * @return The list of recipients
     */
    private List<NotificationMessage.Recipient> getRecipientsForSystemEvent(EventType eventType) {
        List<NotificationMessage.Recipient> recipients = new ArrayList<>();
        
        // Add webhook recipients if enabled
        if (webhookEnabled) {
            // In a real implementation, this would query the WebhookService for registered webhooks
            // For now, we'll add a placeholder webhook recipient
            recipients.add(new NotificationMessage.Recipient(
                    NotificationMessage.RecipientType.WEBHOOK,
                    "https://api.example.com/webhooks/system-events",
                    "System Events Webhook",
                    Map.of("hmacEnabled", true, "hmacAlgorithm", "HmacSHA256")
            ));
        }
        
        // Add email recipients if enabled
        if (emailEnabled) {
            // In a real implementation, this would query for email recipients based on the event type
            // For now, we'll add a placeholder email recipient
            recipients.add(new NotificationMessage.Recipient(
                    NotificationMessage.RecipientType.EMAIL,
                    "system-events@example.com",
                    "System Events",
                    Map.of("template", "system-event-notification")
            ));
        }
        
        return recipients;
    }
    
    /**
     * Determines the notification priority for a system event.
     *
     * @param eventType The event type to determine priority for
     * @return The notification priority
     */
    private NotificationMessage.NotificationPriority getSystemEventPriority(EventType eventType) {
        switch (eventType) {
            case APPLICATION_APPROVED:
            case APPLICATION_REJECTED:
                return NotificationMessage.NotificationPriority.HIGH;
                
            case APPLICATION_CREATED:
            case APPLICATION_UPDATED:
                return NotificationMessage.NotificationPriority.MEDIUM;
                
            case DOCUMENT_UPLOADED:
            case DOCUMENT_PROCESSED:
                return NotificationMessage.NotificationPriority.LOW;
                
            default:
                return NotificationMessage.NotificationPriority.MEDIUM;
        }
    }
}