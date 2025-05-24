package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.util.Constants;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.MessagePropertiesBuilder;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * RabbitMQ producer for publishing notification messages to the notification queue.
 * <p>
 * This class is responsible for serializing notification data, applying message properties,
 * and ensuring reliable delivery with publisher confirms. It supports different notification
 * types and priority levels, with configurable retry logic for failed publications.
 * </p>
 */
@Component
public class NotificationProducer {

    private static final Logger log = LoggerFactory.getLogger(NotificationProducer.class);

    private final RabbitTemplate rabbitTemplate;
    private final ObjectMapper objectMapper;
    private final RetryTemplate retryTemplate;

    @Value("${application.messaging.exchanges.documents.name:mca.documents}")
    private String exchangeName;

    @Value("${application.messaging.queues.notification.name:notification}")
    private String queueName;

    /**
     * Constructs a new NotificationProducer with the specified dependencies.
     *
     * @param rabbitTemplate The RabbitTemplate for sending messages to RabbitMQ
     * @param objectMapper   The ObjectMapper for serializing notification messages to JSON
     * @param retryTemplate  The RetryTemplate for retrying failed message publications
     */
    @Autowired
    public NotificationProducer(RabbitTemplate rabbitTemplate, ObjectMapper objectMapper, RetryTemplate retryTemplate) {
        this.rabbitTemplate = rabbitTemplate;
        this.objectMapper = objectMapper;
        this.retryTemplate = retryTemplate;
    }

    /**
     * Publishes a notification message to the notification queue.
     *
     * @param notification The notification message to publish
     * @return The correlation ID of the published message
     * @throws MessagingException if an error occurs during message publication
     */
    public String publishNotification(NotificationMessage notification) throws MessagingException {
        String correlationId = UUID.randomUUID().toString();
        try {
            log.info("Publishing notification message with ID: {}, type: {}, priority: {}", 
                    notification.getId(), notification.getType(), notification.getPriority());
            
            // Ensure timestamp is set
            if (notification.getTimestamp() == null) {
                notification.setTimestamp(LocalDateTime.now());
            }
            
            // Serialize the notification message to JSON
            String messageBody = serializeNotification(notification);
            
            // Create message properties based on notification attributes
            MessageProperties messageProperties = createMessageProperties(notification, correlationId);
            
            // Build the message
            Message message = MessageBuilder
                    .withBody(messageBody.getBytes(StandardCharsets.UTF_8))
                    .andProperties(messageProperties)
                    .build();
            
            // Create correlation data for publisher confirms
            CorrelationData correlationData = new CorrelationData(correlationId);
            
            // Publish the message with retry logic
            retryTemplate.execute(context -> {
                rabbitTemplate.convertAndSend(exchangeName, "", message, correlationData);
                return null;
            }, context -> {
                Throwable t = context.getLastThrowable();
                log.error("Failed to publish notification after multiple retries: {}", t.getMessage());
                throw MessagingException.deliveryError(
                        "Failed to publish notification after multiple retries",
                        t,
                        context.getRetryCount(),
                        context.getLastBackOffPeriod(),
                        exchangeName);
            });
            
            log.debug("Successfully published notification message with correlation ID: {}", correlationId);
            return correlationId;
            
        } catch (AmqpException e) {
            log.error("AMQP error while publishing notification: {}", e.getMessage());
            throw MessagingException.deliveryError(
                    "Failed to publish notification due to AMQP error",
                    e,
                    exchangeName);
        } catch (Exception e) {
            log.error("Unexpected error while publishing notification: {}", e.getMessage());
            throw new MessagingException(
                    "Unexpected error while publishing notification",
                    MessagingException.ErrorType.OTHER,
                    e,
                    org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Publishes a notification message with the specified type and priority.
     *
     * @param type     The type of notification
     * @param priority The priority level of the notification
     * @param payload  The payload data for the notification
     * @param recipients The list of recipients for the notification
     * @return The correlation ID of the published message
     * @throws MessagingException if an error occurs during message publication
     */
    public String publishNotification(
            NotificationMessage.NotificationType type,
            NotificationMessage.NotificationPriority priority,
            java.util.Map<String, Object> payload,
            java.util.List<NotificationMessage.Recipient> recipients) throws MessagingException {
        
        // Create a new notification message
        NotificationMessage notification = NotificationMessage.builder()
                .id(UUID.randomUUID().toString())
                .type(type)
                .priority(priority)
                .recipients(recipients)
                .payload(payload)
                .build();
        
        return publishNotification(notification);
    }

    /**
     * Publishes a status update notification for an application.
     *
     * @param applicationId The ID of the application
     * @param status        The new status of the application
     * @param metadata      Additional metadata about the status update
     * @param recipients    The list of recipients for the notification
     * @return The correlation ID of the published message
     * @throws MessagingException if an error occurs during message publication
     */
    public String publishStatusUpdate(
            String applicationId,
            String status,
            java.util.Map<String, Object> metadata,
            java.util.List<NotificationMessage.Recipient> recipients) throws MessagingException {
        
        // Create payload for status update
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("applicationId", applicationId);
        payload.put("status", status);
        payload.put("updatedAt", LocalDateTime.now().toString());
        
        if (metadata != null) {
            payload.put("metadata", metadata);
        }
        
        // Create notification message
        NotificationMessage notification = NotificationMessage.builder()
                .id(UUID.randomUUID().toString())
                .type(NotificationMessage.NotificationType.STATUS_UPDATE)
                .priority(NotificationMessage.NotificationPriority.MEDIUM)
                .recipients(recipients)
                .payload(payload)
                .build();
        
        // Add delivery options with retry
        NotificationMessage.DeliveryOptions deliveryOptions = new NotificationMessage.DeliveryOptions(
                3, // retry count
                5000L, // retry delay in ms
                86400000L, // expiration in ms (24 hours)
                true, // require HMAC
                "HmacSHA256", // HMAC algorithm
                LocalDateTime.now().plusDays(1) // delivery deadline
        );
        notification.setDeliveryOptions(deliveryOptions);
        
        return publishNotification(notification);
    }

    /**
     * Publishes a completion notification for an application.
     *
     * @param applicationId The ID of the application
     * @param result        The result of the application processing
     * @param metadata      Additional metadata about the completion
     * @param recipients    The list of recipients for the notification
     * @return The correlation ID of the published message
     * @throws MessagingException if an error occurs during message publication
     */
    public String publishCompletionNotification(
            String applicationId,
            String result,
            java.util.Map<String, Object> metadata,
            java.util.List<NotificationMessage.Recipient> recipients) throws MessagingException {
        
        // Create payload for completion notification
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("applicationId", applicationId);
        payload.put("result", result);
        payload.put("completedAt", LocalDateTime.now().toString());
        
        if (metadata != null) {
            payload.put("metadata", metadata);
        }
        
        // Create notification message with high priority
        NotificationMessage notification = NotificationMessage.builder()
                .id(UUID.randomUUID().toString())
                .type(NotificationMessage.NotificationType.COMPLETION)
                .priority(NotificationMessage.NotificationPriority.HIGH)
                .recipients(recipients)
                .payload(payload)
                .build();
        
        // Add delivery options with retry and HMAC
        NotificationMessage.DeliveryOptions deliveryOptions = new NotificationMessage.DeliveryOptions(
                5, // retry count
                3000L, // retry delay in ms
                259200000L, // expiration in ms (3 days)
                true, // require HMAC
                "HmacSHA256", // HMAC algorithm
                LocalDateTime.now().plusDays(3) // delivery deadline
        );
        notification.setDeliveryOptions(deliveryOptions);
        
        return publishNotification(notification);
    }

    /**
     * Publishes an error notification for an application.
     *
     * @param applicationId The ID of the application
     * @param errorCode     The error code
     * @param errorMessage  The error message
     * @param recipients    The list of recipients for the notification
     * @return The correlation ID of the published message
     * @throws MessagingException if an error occurs during message publication
     */
    public String publishErrorNotification(
            String applicationId,
            String errorCode,
            String errorMessage,
            java.util.List<NotificationMessage.Recipient> recipients) throws MessagingException {
        
        // Create payload for error notification
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("applicationId", applicationId);
        payload.put("errorCode", errorCode);
        payload.put("errorMessage", errorMessage);
        payload.put("errorTimestamp", LocalDateTime.now().toString());
        
        // Create notification message with critical priority
        NotificationMessage notification = NotificationMessage.builder()
                .id(UUID.randomUUID().toString())
                .type(NotificationMessage.NotificationType.ERROR)
                .priority(NotificationMessage.NotificationPriority.CRITICAL)
                .recipients(recipients)
                .payload(payload)
                .build();
        
        // Add delivery options with aggressive retry
        NotificationMessage.DeliveryOptions deliveryOptions = new NotificationMessage.DeliveryOptions(
                10, // retry count
                1000L, // retry delay in ms
                86400000L, // expiration in ms (24 hours)
                true, // require HMAC
                "HmacSHA256", // HMAC algorithm
                LocalDateTime.now().plusDays(1) // delivery deadline
        );
        notification.setDeliveryOptions(deliveryOptions);
        
        return publishNotification(notification);
    }

    /**
     * Serializes a notification message to JSON.
     *
     * @param notification The notification message to serialize
     * @return The JSON string representation of the notification message
     * @throws MessagingException if an error occurs during serialization
     */
    private String serializeNotification(NotificationMessage notification) throws MessagingException {
        try {
            return objectMapper.writeValueAsString(notification);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize notification message: {}", e.getMessage());
            throw MessagingException.serializationError(
                    "Failed to serialize notification message",
                    e);
        }
    }

    /**
     * Creates message properties based on notification attributes.
     *
     * @param notification  The notification message
     * @param correlationId The correlation ID for the message
     * @return The message properties
     */
    private MessageProperties createMessageProperties(NotificationMessage notification, String correlationId) {
        MessagePropertiesBuilder builder = MessagePropertiesBuilder.newInstance()
                .setContentType(MessageProperties.CONTENT_TYPE_JSON)
                .setContentEncoding(StandardCharsets.UTF_8.name())
                .setCorrelationId(correlationId)
                .setMessageId(notification.getId())
                .setTimestamp(java.util.Date.from(notification.getTimestamp().atZone(java.time.ZoneId.systemDefault()).toInstant()))
                .setType(notification.getType().name())
                .setAppId(Constants.APPLICATION_NAME);
        
        // Set priority based on notification priority
        switch (notification.getPriority()) {
            case LOW:
                builder.setPriority(1);
                break;
            case MEDIUM:
                builder.setPriority(5);
                break;
            case HIGH:
                builder.setPriority(8);
                break;
            case CRITICAL:
                builder.setPriority(10);
                break;
            default:
                builder.setPriority(5); // Default to medium priority
        }
        
        // Set expiration if specified in delivery options
        if (notification.getDeliveryOptions() != null && notification.getDeliveryOptions().getExpirationMs() != null) {
            builder.setExpiration(notification.getDeliveryOptions().getExpirationMs().toString());
        }
        
        // Add custom headers
        builder.setHeader("x-notification-type", notification.getType().name());
        builder.setHeader("x-notification-priority", notification.getPriority().name());
        
        if (notification.getDeliveryOptions() != null) {
            if (notification.getDeliveryOptions().getRetryCount() != null) {
                builder.setHeader("x-retry-count", notification.getDeliveryOptions().getRetryCount());
            }
            if (notification.getDeliveryOptions().getRequireHmac() != null && notification.getDeliveryOptions().getRequireHmac()) {
                builder.setHeader("x-require-hmac", true);
                if (notification.getDeliveryOptions().getHmacAlgorithm() != null) {
                    builder.setHeader("x-hmac-algorithm", notification.getDeliveryOptions().getHmacAlgorithm());
                }
            }
        }
        
        return builder.build();
    }
}