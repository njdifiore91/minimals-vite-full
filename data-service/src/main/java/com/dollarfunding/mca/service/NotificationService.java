package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.notification.NotificationDeliveryStatusDTO;
import com.dollarfunding.mca.dto.notification.NotificationRequestDTO;
import com.dollarfunding.mca.dto.notification.NotificationResponseDTO;
import com.dollarfunding.mca.dto.notification.NotificationTemplateDTO;
import com.dollarfunding.mca.dto.notification.NotificationTypeEnum;
import com.dollarfunding.mca.dto.notification.RecipientDTO;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Service interface that defines the contract for notification management in the MCA application.
 * It provides methods for sending notifications about application status changes, document processing results,
 * and system events. This interface is implemented by NotificationServiceImpl and used by other services
 * to notify users and external systems about important events.
 */
public interface NotificationService {

    /**
     * Sends a notification about an application status change.
     *
     * @param applicationId The ID of the application whose status has changed
     * @param oldStatus The previous status of the application
     * @param newStatus The new status of the application
     * @param metadata Additional metadata about the status change
     * @return The notification response containing the notification ID and delivery status
     */
    NotificationResponseDTO sendApplicationStatusNotification(
            String applicationId,
            String oldStatus,
            String newStatus,
            Map<String, Object> metadata);

    /**
     * Sends a notification about document processing results.
     *
     * @param applicationId The ID of the application the document belongs to
     * @param documentId The ID of the processed document
     * @param documentType The type of the document
     * @param processingStatus The status of the document processing
     * @param extractedData Data extracted from the document (if applicable)
     * @param metadata Additional metadata about the document processing
     * @return The notification response containing the notification ID and delivery status
     */
    NotificationResponseDTO sendDocumentProcessingNotification(
            String applicationId,
            String documentId,
            String documentType,
            String processingStatus,
            Map<String, Object> extractedData,
            Map<String, Object> metadata);

    /**
     * Sends a notification about a system event.
     *
     * @param eventType The type of system event
     * @param severity The severity of the event (INFO, WARNING, ERROR, CRITICAL)
     * @param message The event message
     * @param metadata Additional metadata about the event
     * @return The notification response containing the notification ID and delivery status
     */
    NotificationResponseDTO sendSystemEventNotification(
            String eventType,
            String severity,
            String message,
            Map<String, Object> metadata);

    /**
     * Sends a custom notification with the specified parameters.
     *
     * @param notificationRequest The notification request containing all notification details
     * @return The notification response containing the notification ID and delivery status
     */
    NotificationResponseDTO sendNotification(NotificationRequestDTO notificationRequest);

    /**
     * Retrieves the delivery status of a notification.
     *
     * @param notificationId The ID of the notification
     * @return The notification delivery status
     */
    NotificationDeliveryStatusDTO getNotificationStatus(String notificationId);

    /**
     * Retrieves the delivery statuses of multiple notifications.
     *
     * @param notificationIds The IDs of the notifications
     * @return A map of notification IDs to their delivery statuses
     */
    Map<String, NotificationDeliveryStatusDTO> getNotificationStatuses(List<String> notificationIds);

    /**
     * Creates a new notification template.
     *
     * @param template The notification template to create
     * @return The created notification template with its assigned ID
     */
    NotificationTemplateDTO createNotificationTemplate(NotificationTemplateDTO template);

    /**
     * Updates an existing notification template.
     *
     * @param templateId The ID of the template to update
     * @param template The updated notification template
     * @return The updated notification template
     */
    NotificationTemplateDTO updateNotificationTemplate(String templateId, NotificationTemplateDTO template);

    /**
     * Retrieves a notification template by its ID.
     *
     * @param templateId The ID of the template to retrieve
     * @return The notification template, or empty if not found
     */
    Optional<NotificationTemplateDTO> getNotificationTemplate(String templateId);

    /**
     * Retrieves all notification templates for a specific notification type.
     *
     * @param notificationType The type of notification
     * @return A list of notification templates for the specified type
     */
    List<NotificationTemplateDTO> getNotificationTemplatesByType(NotificationTypeEnum notificationType);

    /**
     * Deletes a notification template.
     *
     * @param templateId The ID of the template to delete
     * @return true if the template was deleted, false otherwise
     */
    boolean deleteNotificationTemplate(String templateId);

    /**
     * Adds a recipient to receive notifications for a specific application.
     *
     * @param applicationId The ID of the application
     * @param recipient The recipient to add
     * @return The added recipient with its assigned ID
     */
    RecipientDTO addApplicationRecipient(String applicationId, RecipientDTO recipient);

    /**
     * Removes a recipient from receiving notifications for a specific application.
     *
     * @param applicationId The ID of the application
     * @param recipientId The ID of the recipient to remove
     * @return true if the recipient was removed, false otherwise
     */
    boolean removeApplicationRecipient(String applicationId, String recipientId);

    /**
     * Retrieves all recipients configured to receive notifications for a specific application.
     *
     * @param applicationId The ID of the application
     * @return A list of recipients for the specified application
     */
    List<RecipientDTO> getApplicationRecipients(String applicationId);

    /**
     * Adds a recipient to receive system notifications.
     *
     * @param recipient The recipient to add
     * @return The added recipient with its assigned ID
     */
    RecipientDTO addSystemRecipient(RecipientDTO recipient);

    /**
     * Removes a recipient from receiving system notifications.
     *
     * @param recipientId The ID of the recipient to remove
     * @return true if the recipient was removed, false otherwise
     */
    boolean removeSystemRecipient(String recipientId);

    /**
     * Retrieves all recipients configured to receive system notifications.
     *
     * @return A list of system notification recipients
     */
    List<RecipientDTO> getSystemRecipients();

    /**
     * Resends a notification that was previously sent.
     *
     * @param notificationId The ID of the notification to resend
     * @return The notification response for the resent notification
     */
    NotificationResponseDTO resendNotification(String notificationId);

    /**
     * Cancels a pending notification that has not yet been delivered.
     *
     * @param notificationId The ID of the notification to cancel
     * @return true if the notification was cancelled, false otherwise
     */
    boolean cancelNotification(String notificationId);

    /**
     * Sends a notification using a template.
     *
     * @param templateId The ID of the template to use
     * @param templateVariables The variables to substitute in the template
     * @param recipients The recipients of the notification
     * @param metadata Additional metadata for the notification
     * @return The notification response containing the notification ID and delivery status
     */
    NotificationResponseDTO sendTemplatedNotification(
            String templateId,
            Map<String, Object> templateVariables,
            List<RecipientDTO> recipients,
            Map<String, Object> metadata);

    /**
     * Configures notification channels for a specific application.
     *
     * @param applicationId The ID of the application
     * @param channelConfigurations A map of channel types to their configurations
     * @return true if the channels were configured successfully, false otherwise
     */
    boolean configureApplicationNotificationChannels(
            String applicationId,
            Map<String, Object> channelConfigurations);

    /**
     * Retrieves the notification channel configurations for a specific application.
     *
     * @param applicationId The ID of the application
     * @return A map of channel types to their configurations
     */
    Map<String, Object> getApplicationNotificationChannels(String applicationId);
}