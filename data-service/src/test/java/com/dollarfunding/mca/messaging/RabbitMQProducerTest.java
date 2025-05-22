package com.dollarfunding.mca.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for RabbitMQ message producers in the Data Service.
 * 
 * These tests verify that messages are correctly formatted, serialized, and published
 * to the appropriate RabbitMQ exchanges and queues as defined in the technical specification.
 */
@ExtendWith(MockitoExtension.class)
public class RabbitMQProducerTest {

    @Mock
    private RabbitTemplate rabbitTemplate;
    
    @Mock
    private ObjectMapper objectMapper;
    
    @Captor
    private ArgumentCaptor<Message> messageCaptor;
    
    @Captor
    private ArgumentCaptor<String> exchangeCaptor;
    
    @Captor
    private ArgumentCaptor<String> routingKeyCaptor;
    
    @Captor
    private ArgumentCaptor<CorrelationData> correlationDataCaptor;
    
    private NotificationProducer notificationProducer;
    
    private static final String EXCHANGE_NAME = "mca.documents";
    private static final String NOTIFICATION_QUEUE_NAME = "notification";
    
    @BeforeEach
    void setUp() {
        notificationProducer = new NotificationProducer(rabbitTemplate, objectMapper);
        ReflectionTestUtils.setField(notificationProducer, "exchangeName", EXCHANGE_NAME);
        ReflectionTestUtils.setField(notificationProducer, "notificationQueueName", NOTIFICATION_QUEUE_NAME);
        ReflectionTestUtils.setField(notificationProducer, "initialRetryInterval", 1000L);
        ReflectionTestUtils.setField(notificationProducer, "maxRetryAttempts", 3);
        ReflectionTestUtils.setField(notificationProducer, "retryMultiplier", 2.0);
        
        // Initialize the producer (normally done by @PostConstruct)
        notificationProducer.init();
    }
    
    @Test
    @DisplayName("Should publish message to the correct exchange and queue")
    void shouldPublishMessageToCorrectExchangeAndQueue() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"STATUS_UPDATE\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        
        // Act
        notificationProducer.publishNotification(notificationMessage);
        
        // Assert
        verify(rabbitTemplate).send(
            eq(EXCHANGE_NAME),
            eq(NOTIFICATION_QUEUE_NAME),
            messageCaptor.capture(),
            correlationDataCaptor.capture()
        );
        
        Message capturedMessage = messageCaptor.getValue();
        CorrelationData correlationData = correlationDataCaptor.getValue();
        
        assertNotNull(capturedMessage, "Message should not be null");
        assertNotNull(correlationData, "CorrelationData should not be null");
        assertEquals(notificationMessage.getId(), correlationData.getId(), "Correlation ID should match notification ID");
        assertEquals(MessageProperties.CONTENT_TYPE_JSON, capturedMessage.getMessageProperties().getContentType(), 
                "Content type should be JSON");
        assertEquals(serializedMessage, capturedMessage.getBody(), "Message body should match serialized content");
    }
    
    @Test
    @DisplayName("Should set correct message properties")
    void shouldSetCorrectMessageProperties() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        notificationMessage.setPriority(NotificationMessage.NotificationType.CRITICAL);
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"CRITICAL\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        
        // Act
        notificationProducer.publishNotification(notificationMessage);
        
        // Assert
        verify(rabbitTemplate).send(
            anyString(),
            anyString(),
            messageCaptor.capture(),
            any(CorrelationData.class)
        );
        
        MessageProperties properties = messageCaptor.getValue().getMessageProperties();
        
        assertNotNull(properties, "Message properties should not be null");
        assertEquals(MessageProperties.CONTENT_TYPE_JSON, properties.getContentType(), "Content type should be JSON");
        assertEquals("UTF-8", properties.getContentEncoding(), "Content encoding should be UTF-8");
        assertEquals(notificationMessage.getId(), properties.getCorrelationId(), "Correlation ID should match notification ID");
        assertNotNull(properties.getTimestamp(), "Timestamp should be set");
        assertEquals(notificationMessage.getType().name(), properties.getHeader("notification_type"), 
                "Notification type header should be set");
    }
    
    @Test
    @DisplayName("Should handle serialization exceptions")
    void shouldHandleSerializationExceptions() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class)))
            .thenThrow(new RuntimeException("Serialization error"));
        
        // Act & Assert
        MessagingException exception = assertThrows(MessagingException.class, () -> {
            notificationProducer.publishNotification(notificationMessage);
        });
        
        assertTrue(exception.getMessage().contains("Failed to publish notification message"), 
                "Exception message should indicate publishing failure");
        verify(rabbitTemplate, never()).send(
            anyString(),
            anyString(),
            any(Message.class),
            any(CorrelationData.class)
        );
    }
    
    @Test
    @DisplayName("Should handle RabbitMQ connection exceptions")
    void shouldHandleRabbitMQConnectionExceptions() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"STATUS_UPDATE\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        doThrow(new RuntimeException("Connection error"))
            .when(rabbitTemplate).send(
                anyString(),
                anyString(),
                any(Message.class),
                any(CorrelationData.class)
            );
        
        // Act & Assert
        MessagingException exception = assertThrows(MessagingException.class, () -> {
            notificationProducer.publishNotification(notificationMessage);
        });
        
        assertTrue(exception.getMessage().contains("Failed to publish notification message"), 
                "Exception message should indicate publishing failure");
    }
    
    @Test
    @DisplayName("Should handle publisher confirms for successful delivery")
    void shouldHandlePublisherConfirmsForSuccessfulDelivery() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"STATUS_UPDATE\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        
        // Act
        notificationProducer.publishNotification(notificationMessage);
        
        // Capture the correlation data
        verify(rabbitTemplate).send(
            anyString(),
            anyString(),
            any(Message.class),
            correlationDataCaptor.capture()
        );
        
        CorrelationData correlationData = correlationDataCaptor.getValue();
        
        // Simulate a successful publisher confirm
        rabbitTemplate.getConfirmCallback().confirm(correlationData, true, null);
        
        // Assert - No exceptions should be thrown
        // The pending confirmations map should be cleared (can't directly test this as it's private)
        assertTrue(notificationProducer.waitForConfirms(100), "Should return true when all confirmations are received");
    }
    
    @Test
    @DisplayName("Should handle publisher confirms for failed delivery")
    void shouldHandlePublisherConfirmsForFailedDelivery() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"STATUS_UPDATE\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        
        // Act
        notificationProducer.publishNotification(notificationMessage);
        
        // Capture the correlation data
        verify(rabbitTemplate).send(
            anyString(),
            anyString(),
            any(Message.class),
            correlationDataCaptor.capture()
        );
        
        CorrelationData correlationData = correlationDataCaptor.getValue();
        
        // Simulate a failed publisher confirm
        rabbitTemplate.getConfirmCallback().confirm(correlationData, false, "Channel closed");
        
        // We can't directly test the retry logic as it involves Thread.sleep
        // But we can verify that the message is not immediately removed from pending confirmations
        assertFalse(notificationProducer.waitForConfirms(100), "Should return false when confirmations are pending");
    }
    
    @Test
    @DisplayName("Should handle returned messages")
    void shouldHandleReturnedMessages() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"STATUS_UPDATE\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        
        // Act
        notificationProducer.publishNotification(notificationMessage);
        
        // Capture the message
        verify(rabbitTemplate).send(
            anyString(),
            anyString(),
            messageCaptor.capture(),
            any(CorrelationData.class)
        );
        
        Message capturedMessage = messageCaptor.getValue();
        
        // Simulate a returned message
        rabbitTemplate.getReturnsCallback().returnedMessage(
            org.springframework.amqp.core.ReturnedMessage.builder()
                .message(capturedMessage)
                .replyCode(312)
                .replyText("No route")
                .exchange(EXCHANGE_NAME)
                .routingKey(NOTIFICATION_QUEUE_NAME)
                .build()
        );
        
        // We can't directly test the retry logic as it involves Thread.sleep
        // But we can verify that the message is not immediately removed from pending confirmations
        assertFalse(notificationProducer.waitForConfirms(100), "Should return false when confirmations are pending");
    }
    
    @Test
    @DisplayName("Should publish notification with custom headers")
    void shouldPublishNotificationWithCustomHeaders() throws Exception {
        // Arrange
        NotificationMessage notificationMessage = createSampleNotificationMessage();
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"STATUS_UPDATE\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        
        Map<String, Object> customHeaders = new HashMap<>();
        customHeaders.put("custom_header1", "value1");
        customHeaders.put("custom_header2", 123);
        
        // Act
        notificationProducer.publishNotification(notificationMessage, customHeaders);
        
        // Assert
        verify(rabbitTemplate).send(
            anyString(),
            anyString(),
            messageCaptor.capture(),
            any(CorrelationData.class)
        );
        
        MessageProperties properties = messageCaptor.getValue().getMessageProperties();
        
        assertEquals("value1", properties.getHeader("custom_header1"), "Custom header 1 should be set");
        assertEquals(123, properties.getHeader("custom_header2"), "Custom header 2 should be set");
    }
    
    @Test
    @DisplayName("Should publish notification with convenience methods")
    void shouldPublishNotificationWithConvenienceMethods() throws Exception {
        // Arrange
        byte[] serializedMessage = "{\"id\":\"test-id\",\"type\":\"STATUS_UPDATE\"}".getBytes();
        when(objectMapper.writeValueAsBytes(any(NotificationMessage.class))).thenReturn(serializedMessage);
        
        NotificationMessage.NotificationType type = NotificationMessage.NotificationType.STATUS_UPDATE;
        NotificationMessage.NotificationPriority priority = NotificationMessage.NotificationPriority.HIGH;
        NotificationMessage.Recipient recipient = new NotificationMessage.Recipient(
                NotificationMessage.NotificationChannel.WEBHOOK, "https://example.com/webhook");
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", "app-123");
        payload.put("status", "APPROVED");
        
        // Act
        notificationProducer.publishNotification(type, priority, recipient, payload);
        
        // Assert
        verify(rabbitTemplate).send(
            eq(EXCHANGE_NAME),
            eq(NOTIFICATION_QUEUE_NAME),
            any(Message.class),
            any(CorrelationData.class)
        );
        
        // Verify the message was created with the correct parameters
        ArgumentCaptor<NotificationMessage> notificationCaptor = ArgumentCaptor.forClass(NotificationMessage.class);
        verify(objectMapper).writeValueAsBytes(notificationCaptor.capture());
        
        NotificationMessage capturedNotification = notificationCaptor.getValue();
        assertEquals(type, capturedNotification.getType(), "Notification type should match");
        assertEquals(priority, capturedNotification.getPriority(), "Notification priority should match");
        assertEquals(payload, capturedNotification.getPayload(), "Notification payload should match");
    }
    
    /**
     * Creates a sample notification message for testing.
     * 
     * @return A sample notification message
     */
    private NotificationMessage createSampleNotificationMessage() {
        String notificationId = UUID.randomUUID().toString();
        NotificationMessage message = new NotificationMessage();
        message.setId(notificationId);
        message.setType(NotificationMessage.NotificationType.STATUS_UPDATE);
        message.setPriority(NotificationMessage.NotificationPriority.MEDIUM);
        
        NotificationMessage.Recipient recipient = new NotificationMessage.Recipient(
                NotificationMessage.NotificationChannel.WEBHOOK, "https://example.com/webhook");
        message.setRecipients(java.util.Collections.singletonList(recipient));
        
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", "app-123");
        payload.put("status", "APPROVED");
        message.setPayload(payload);
        
        return message;
    }
}