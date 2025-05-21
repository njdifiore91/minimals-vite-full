package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.EventType;

import java.util.Map;

/**
 * Service interface that defines the contract for notification management in the MCA application.
 * It provides methods for sending notifications about application status changes,
 * document processing results, and system events.
 * 
 * This interface is implemented by NotificationServiceImpl and used by other services
 * to notify users and external systems about important events.
 */
public interface NotificationService {
    
    /**
     * Sends a notification about an application status change.
     * 
     * @param application The application that had a status change
     * @param previousStatus The previous status of the application
     * @param newStatus The new status of the application
     * @return true if the notification was sent successfully, false otherwise
     */
    boolean sendApplicationStatusNotification(Application application, String previousStatus, String newStatus);
    
    /**
     * Sends a notification about a new application being created.
     * 
     * @param application The newly created application
     * @return true if the notification was sent successfully, false otherwise
     */
    boolean sendApplicationCreatedNotification(Application application);
    
    /**
     * Sends a notification about an application being approved.
     * 
     * @param application The approved application
     * @return true if the notification was sent successfully, false otherwise
     */
    boolean sendApplicationApprovedNotification(Application application);
    
    /**
     * Sends a notification about an application being rejected.
     * 
     * @param application The rejected application
     * @param reason The reason for rejection
     * @return true if the notification was sent successfully, false otherwise
     */
    boolean sendApplicationRejectedNotification(Application application, String reason);
    
    /**
     * Sends a notification about a document being uploaded.
     * 
     * @param document The uploaded document
     * @param applicationId The ID of the application associated with the document
     * @return true if the notification was sent successfully, false otherwise
     */
    boolean sendDocumentUploadedNotification(Document document, Long applicationId);
    
    /**
     * Sends a notification about a document being processed.
     * 
     * @param document The processed document
     * @param applicationId The ID of the application associated with the document
     * @param extractionResults The results of the document data extraction
     * @return true if the notification was sent successfully, false otherwise
     */
    boolean sendDocumentProcessedNotification(Document document, Long applicationId, Map<String, Object> extractionResults);
    
    /**
     * Sends a system event notification.
     * 
     * @param eventType The type of system event
     * @param payload The event payload
     * @return true if the notification was sent successfully, false otherwise
     */
    boolean sendSystemEventNotification(EventType eventType, Map<String, Object> payload);
    
    /**
     * Retrieves notification templates from the cache or loads them from the filesystem.
     * 
     * @param templateName The name of the template to retrieve
     * @return The template content as a string
     */
    String getNotificationTemplate(String templateName);
    
    /**
     * Refreshes the notification template cache.
     * 
     * @param templateName The name of the template to refresh, or null to refresh all templates
     */
    void refreshNotificationTemplates(String templateName);
    
    /**
     * Tracks the delivery status of a notification.
     * 
     * @param notificationId The ID of the notification
     * @param status The delivery status
     * @param details Additional details about the delivery status
     */
    void trackNotificationDeliveryStatus(String notificationId, String status, Map<String, Object> details);
    
    /**
     * Retries a failed notification delivery.
     * 
     * @param notificationId The ID of the failed notification
     * @param maxAttempts The maximum number of retry attempts
     * @return true if the retry was successful, false otherwise
     */
    boolean retryFailedNotification(String notificationId, int maxAttempts);
}