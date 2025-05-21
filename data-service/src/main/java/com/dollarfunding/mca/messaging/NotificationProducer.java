package com.dollarfunding.mca.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.MessagePropertiesBuilder;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * RabbitMQ producer class that publishes notification messages to the notification queue.
 * It serializes notification data, applies message properties, and ensures reliable delivery
 * with publisher confirms. This class supports different notification types and priority levels,
 * with configurable retry logic for failed publications.
 */
@Component
public class NotificationProducer {

    private static final Logger log = LoggerFactory.getLogger(NotificationProducer.class);
    
    private final RabbitTemplate rabbitTemplate;
    private final ObjectMapper objectMapper;
    
    // Track pending confirmations with a concurrent map
    private final Map<String, PendingConfirmation> pendingConfirmations = new ConcurrentHashMap<>();
    
    @Value("${application.messaging.exchanges.documents.name}")
    private String exchangeName;
    
    @Value("${application.messaging.queues.notification.name}")
    private String notificationQueueName;
    
    @Value("${spring.rabbitmq.template.retry.initial-interval:1000}")
    private long initialRetryInterval;
    
    @Value("${spring.rabbitmq.template.retry.max-attempts:3}")
    private int maxRetryAttempts;
    
    @Value("${spring.rabbitmq.template.retry.multiplier:2.0}")
    private double retryMultiplier;
    
    /**
     * Class to track pending confirmations and handle retries.
     */
    private static class PendingConfirmation {
        private final NotificationMessage message;
        private final Map<String, Object> headers;
        private final long timestamp;
        private int attempts;
        
        public PendingConfirmation(NotificationMessage message, Map<String, Object> headers) {
            this.message = message;
            this.headers = headers;
            this.timestamp = System.currentTimeMillis();
            this.attempts = 1;
        }
        
        public NotificationMessage getMessage() {
            return message;
        }
        
        public Map<String, Object> getHeaders() {
            return headers;
        }
        
        public long getTimestamp() {
            return timestamp;
        }
        
        public int getAttempts() {
            return attempts;
        }
        
        public void incrementAttempts() {
            this.attempts++;
        }
    }
    
    @Autowired
    public NotificationProducer(RabbitTemplate rabbitTemplate, ObjectMapper objectMapper) {
        this.rabbitTemplate = rabbitTemplate;
        this.objectMapper = objectMapper;
    }
    
    /**
     * Initialize the producer with publisher confirms.
     */
    @PostConstruct
    public void init() {
        // Set up publisher confirms callback
        rabbitTemplate.setConfirmCallback((correlationData, ack, cause) -> {
            if (correlationData != null && correlationData.getId() != null) {
                String correlationId = correlationData.getId();
                if (ack) {
                    // Message was successfully delivered to the exchange
                    log.debug("Notification confirmed with correlation ID: {}", correlationId);
                    pendingConfirmations.remove(correlationId);
                } else {
                    // Message was not delivered to the exchange
                    log.error("Notification with correlation ID {} was not delivered to exchange. Cause: {}", correlationId, cause);
                    handleFailedPublication(correlationId, cause);
                }
            }
        });
        
        // Set up returns callback for messages that couldn't be routed to a queue
        rabbitTemplate.setReturnsCallback(returned -> {
            log.error("Notification message was returned: {}, replyCode: {}, replyText: {}, exchange: {}, routingKey: {}",
                    returned.getMessage(), returned.getReplyCode(), returned.getReplyText(), 
                    returned.getExchange(), returned.getRoutingKey());
            
            // Extract correlation ID from message properties
            String correlationId = returned.getMessage().getMessageProperties().getCorrelationId();
            if (correlationId != null) {
                handleFailedPublication(correlationId, returned.getReplyText());
            }
        });
        
        // Ensure mandatory flag is set to get returns for unroutable messages
        rabbitTemplate.setMandatory(true);
    }
    
    /**
     * Publishes a notification message to the notification queue.
     *
     * @param notificationMessage The notification message to be sent
     * @param headers Additional headers to include with the message
     * @return true if the message was successfully published, false otherwise
     */
    public boolean publishNotification(NotificationMessage notificationMessage, Map<String, Object> headers) {
        try {
            String correlationId = notificationMessage.getNotificationId();
            if (correlationId == null) {
                correlationId = UUID.randomUUID().toString();
                notificationMessage.setNotificationId(correlationId);
            }
            
            // Store the message details for potential retry
            pendingConfirmations.put(correlationId, new PendingConfirmation(notificationMessage, headers));
            
            // Serialize the notification message to JSON
            byte[] messageBody = objectMapper.writeValueAsBytes(notificationMessage);
            
            // Build message properties
            MessagePropertiesBuilder propertiesBuilder = MessagePropertiesBuilder.newInstance()
                    .setContentType(MessageProperties.CONTENT_TYPE_JSON)
                    .setContentEncoding(StandardCharsets.UTF_8.name())
                    .setCorrelationId(correlationId)
                    .setPriority(getPriorityValue(notificationMessage.getPriority()))
                    .setTimestamp(System.currentTimeMillis())
                    .setHeader("notification_type", notificationMessage.getType().name());
            
            // Add custom headers if provided
            if (headers != null && !headers.isEmpty()) {
                headers.forEach(propertiesBuilder::setHeader);
            }
            
            // Build the message
            Message message = MessageBuilder
                    .withBody(messageBody)
                    .andProperties(propertiesBuilder.build())
                    .build();
            
            // Create correlation data for publisher confirms
            CorrelationData correlationData = new CorrelationData(correlationId);
            
            // Send the message to the exchange with the notification queue routing key
            rabbitTemplate.send(exchangeName, notificationQueueName, message, correlationData);
            
            log.debug("Published notification message with correlation ID: {}, type: {}, priority: {}",
                    correlationId, notificationMessage.getType(), notificationMessage.getPriority());
            
            return true;
        } catch (Exception e) {
            log.error("Failed to publish notification message", e);
            throw MessagingException.deliveryError("Failed to publish notification message: " + e.getMessage(), e);
        }
    }
    
    /**
     * Publishes a notification message without additional headers.
     *
     * @param notificationMessage The notification message to be sent
     * @return true if the message was successfully published, false otherwise
     */
    public boolean publishNotification(NotificationMessage notificationMessage) {
        return publishNotification(notificationMessage, null);
    }
    
    /**
     * Creates and publishes a notification message with the specified parameters.
     *
     * @param type The type of notification
     * @param priority The priority level of the notification
     * @param recipient The recipient information
     * @param payload The payload data for the notification
     * @return true if the message was successfully published, false otherwise
     */
    public boolean publishNotification(NotificationMessage.Type type, 
                                      NotificationMessage.Priority priority, 
                                      NotificationMessage.Recipient recipient, 
                                      Map<String, Object> payload) {
        String notificationId = UUID.randomUUID().toString();
        NotificationMessage message = NotificationMessage.builder()
                .notificationId(notificationId)
                .type(type)
                .priority(priority)
                .recipient(recipient)
                .payload(payload)
                .build();
        
        return publishNotification(message);
    }
    
    /**
     * Creates and publishes a notification message with default priority (MEDIUM).
     *
     * @param type The type of notification
     * @param recipient The recipient information
     * @param payload The payload data for the notification
     * @return true if the message was successfully published, false otherwise
     */
    public boolean publishNotification(NotificationMessage.Type type, 
                                      NotificationMessage.Recipient recipient, 
                                      Map<String, Object> payload) {
        return publishNotification(type, NotificationMessage.Priority.MEDIUM, recipient, payload);
    }
    
    /**
     * Handles failed publications by implementing retry logic.
     *
     * @param correlationId The correlation ID of the failed message
     * @param cause The cause of the failure
     */
    private void handleFailedPublication(String correlationId, String cause) {
        PendingConfirmation confirmation = pendingConfirmations.get(correlationId);
        
        if (confirmation != null) {
            if (confirmation.getAttempts() < maxRetryAttempts) {
                // Calculate backoff time using exponential backoff
                long backoffTime = (long) (initialRetryInterval * Math.pow(retryMultiplier, confirmation.getAttempts() - 1));
                
                log.info("Scheduling retry #{} for notification with correlation ID: {} in {} ms. Cause of failure: {}",
                        confirmation.getAttempts() + 1, correlationId, backoffTime, cause);
                
                // Increment attempt counter
                confirmation.incrementAttempts();
                
                // Schedule retry after backoff period
                try {
                    Thread.sleep(backoffTime);
                    retryPublication(correlationId, confirmation);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    log.error("Retry scheduling was interrupted for correlation ID: {}", correlationId, e);
                    pendingConfirmations.remove(correlationId);
                }
            } else {
                log.error("Maximum retry attempts ({}) reached for notification with correlation ID: {}",
                        maxRetryAttempts, correlationId);
                pendingConfirmations.remove(correlationId);
            }
        }
    }
    
    /**
     * Retries publication of a failed message.
     *
     * @param correlationId The correlation ID of the message to retry
     * @param confirmation The pending confirmation details
     */
    private void retryPublication(String correlationId, PendingConfirmation confirmation) {
        try {
            NotificationMessage notificationMessage = confirmation.getMessage();
            
            // Add retry metadata to the notification message
            notificationMessage.addMetadata("retry_count", confirmation.getAttempts());
            notificationMessage.addMetadata("retry_timestamp", System.currentTimeMillis());
            
            // Serialize the notification message to JSON
            byte[] messageBody = objectMapper.writeValueAsBytes(notificationMessage);
            
            // Build message properties
            MessagePropertiesBuilder propertiesBuilder = MessagePropertiesBuilder.newInstance()
                    .setContentType(MessageProperties.CONTENT_TYPE_JSON)
                    .setContentEncoding(StandardCharsets.UTF_8.name())
                    .setCorrelationId(correlationId)
                    .setPriority(getPriorityValue(notificationMessage.getPriority()))
                    .setTimestamp(System.currentTimeMillis())
                    .setHeader("notification_type", notificationMessage.getType().name())
                    .setHeader("x-retry-count", confirmation.getAttempts());
            
            // Add custom headers if provided
            if (confirmation.getHeaders() != null && !confirmation.getHeaders().isEmpty()) {
                confirmation.getHeaders().forEach(propertiesBuilder::setHeader);
            }
            
            // Build the message
            Message message = MessageBuilder
                    .withBody(messageBody)
                    .andProperties(propertiesBuilder.build())
                    .build();
            
            // Create correlation data for publisher confirms
            CorrelationData correlationData = new CorrelationData(correlationId);
            
            // Send the message to the exchange with the notification queue routing key
            rabbitTemplate.send(exchangeName, notificationQueueName, message, correlationData);
            
            log.debug("Retried notification message with correlation ID: {}, attempt: {}",
                    correlationId, confirmation.getAttempts());
            
        } catch (Exception e) {
            log.error("Failed to retry notification message with correlation ID: {}", correlationId, e);
            pendingConfirmations.remove(correlationId);
        }
    }
    
    /**
     * Waits for all pending confirmations to complete or time out.
     *
     * @param timeout The maximum time to wait in milliseconds
     * @return true if all confirmations were received, false if timed out
     */
    public boolean waitForConfirms(long timeout) {
        long startTime = System.currentTimeMillis();
        while (!pendingConfirmations.isEmpty()) {
            if (System.currentTimeMillis() - startTime > timeout) {
                log.warn("Timed out waiting for {} confirmation(s)", pendingConfirmations.size());
                return false;
            }
            try {
                TimeUnit.MILLISECONDS.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.warn("Interrupted while waiting for confirmations", e);
                return false;
            }
        }
        return true;
    }
    
    /**
     * Converts NotificationMessage.Priority to integer value for RabbitMQ message priority.
     *
     * @param priority The notification priority
     * @return The integer value for RabbitMQ message priority
     */
    private int getPriorityValue(NotificationMessage.Priority priority) {
        switch (priority) {
            case LOW:
                return 1;
            case MEDIUM:
                return 5;
            case HIGH:
                return 8;
            case CRITICAL:
                return 10;
            default:
                return 5; // Default to MEDIUM priority
        }
    }
}