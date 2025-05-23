package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.dto.NotificationMessage;
import com.dollarfunding.mca.exception.MessagingException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.Connection;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the RabbitMQProducer class.
 * 
 * These tests verify that messages are correctly formatted, serialized, and published
 * to the appropriate RabbitMQ exchanges and queues as defined in the technical specification.
 * It covers scenarios like successful message publishing and handling of potential errors
 * during publishing.
 */
@ExtendWith(MockitoExtension.class)
@SpringBootTest
@TestPropertySource(properties = {
    "application.messaging.exchanges.documents.name=mca.documents",
    "application.messaging.exchanges.documents.type=fanout",
    "application.messaging.exchanges.documents.durable=true",
    "application.messaging.queues.notification.name=notification",
    "application.messaging.queues.notification.durable=true",
    "application.messaging.producer.retry-attempts=3",
    "application.messaging.producer.retry-delay=100"
})
public class RabbitMQProducerTest {

    @Mock
    private RabbitTemplate rabbitTemplate;
    
    @Mock
    private ObjectMapper objectMapper;
    
    @Mock
    private RetryTemplate retryTemplate;
    
    @Captor
    private ArgumentCaptor<String> exchangeCaptor;
    
    @Captor
    private ArgumentCaptor<String> routingKeyCaptor;
    
    @Captor
    private ArgumentCaptor<Object> messageCaptor;
    
    private RabbitMQProducer rabbitMQProducer;
    
    // Test data
    private static final String DOCUMENTS_EXCHANGE = "mca.documents";
    private static final String NOTIFICATION_QUEUE = "notification";
    private static final UUID APPLICATION_ID = UUID.randomUUID();
    private static final UUID DOCUMENT_ID = UUID.randomUUID();
    
    @BeforeEach
    void setUp() {
        rabbitMQProducer = new RabbitMQProducer(rabbitTemplate, objectMapper);
        
        // Set exchange name using reflection
        ReflectionTestUtils.setField(rabbitMQProducer, "documentsExchangeName", DOCUMENTS_EXCHANGE);
        ReflectionTestUtils.setField(rabbitMQProducer, "notificationQueueName", NOTIFICATION_QUEUE);
        ReflectionTestUtils.setField(rabbitMQProducer, "retryAttempts", 3);
        ReflectionTestUtils.setField(rabbitMQProducer, "retryDelayMs", 100L);
        
        // Configure retry template to execute the callback directly
        when(retryTemplate.execute(any(), any(), any()))
                .thenAnswer(invocation -> {
                    return invocation.getArgument(0, RetryTemplate.RetryCallback.class)
                            .doWithRetry(null);
                });
        
        ReflectionTestUtils.setField(rabbitMQProducer, "retryTemplate", retryTemplate);
    }
    
    /**
     * Creates a valid notification message for testing.
     * 
     * @return A valid NotificationMessage object
     */
    private NotificationMessage createNotificationMessage() {
        NotificationMessage message = new NotificationMessage();
        message.setMessageId(UUID.randomUUID().toString());
        message.setApplicationId(APPLICATION_ID.toString());
        message.setDocumentId(DOCUMENT_ID.toString());
        message.setType("STATUS_UPDATE");
        message.setTimestamp(LocalDateTime.now());
        message.setSourceService("data-service");
        
        // Add payload data
        Map<String, Object> payload = new HashMap<>();
        payload.put("status", "APPROVED");
        payload.put("updated_by", "system");
        payload.put("notes", "Automatically approved based on credit score");
        message.setPayload(payload);
        
        return message;
    }
    
    /**
     * Test successful publishing of a notification message to the documents exchange.
     */
    @Test
    void testPublishNotificationMessage() throws Exception {
        // Arrange
        NotificationMessage message = createNotificationMessage();
        String serializedMessage = "{\"message_id\":\"123\",\"type\":\"STATUS_UPDATE\"}";
        
        when(objectMapper.writeValueAsString(any(NotificationMessage.class)))
                .thenReturn(serializedMessage);
        
        // Act
        rabbitMQProducer.publishNotification(message);
        
        // Assert
        verify(objectMapper).writeValueAsString(eq(message));
        verify(rabbitTemplate).convertAndSend(
                exchangeCaptor.capture(),
                routingKeyCaptor.capture(),
                messageCaptor.capture());
        
        assertEquals(DOCUMENTS_EXCHANGE, exchangeCaptor.getValue());
        assertEquals(NOTIFICATION_QUEUE, routingKeyCaptor.getValue());
        assertEquals(serializedMessage, messageCaptor.getValue());
    }
    
    /**
     * Test successful publishing of a document processing message to the documents exchange.
     */
    @Test
    void testPublishDocumentProcessingMessage() throws Exception {
        // Arrange
        Map<String, Object> documentData = new HashMap<>();
        documentData.put("document_id", DOCUMENT_ID.toString());
        documentData.put("application_id", APPLICATION_ID.toString());
        documentData.put("status", "PROCESSED");
        documentData.put("timestamp", LocalDateTime.now().toString());
        
        String serializedMessage = "{\"document_id\":\"" + DOCUMENT_ID.toString() + "\",\"status\":\"PROCESSED\"}";
        
        when(objectMapper.writeValueAsString(any(Map.class)))
                .thenReturn(serializedMessage);
        
        // Act
        rabbitMQProducer.publishDocumentProcessing(documentData);
        
        // Assert
        verify(objectMapper).writeValueAsString(eq(documentData));
        verify(rabbitTemplate).convertAndSend(
                exchangeCaptor.capture(),
                routingKeyCaptor.capture(),
                messageCaptor.capture());
        
        assertEquals(DOCUMENTS_EXCHANGE, exchangeCaptor.getValue());
        // Empty routing key for fanout exchange
        assertEquals("", routingKeyCaptor.getValue());
        assertEquals(serializedMessage, messageCaptor.getValue());
    }
    
    /**
     * Test successful publishing of a notification message with publisher confirms.
     */
    @Test
    void testPublishNotificationWithConfirm() throws Exception {
        // Arrange
        NotificationMessage message = createNotificationMessage();
        String serializedMessage = "{\"message_id\":\"123\",\"type\":\"STATUS_UPDATE\"}";
        
        when(objectMapper.writeValueAsString(any(NotificationMessage.class)))
                .thenReturn(serializedMessage);
        
        // Mock RabbitTemplate to use publisher confirms
        when(rabbitTemplate.isConfirmListener()).thenReturn(true);
        
        // Act
        rabbitMQProducer.publishNotificationWithConfirm(message);
        
        // Assert
        verify(objectMapper).writeValueAsString(eq(message));
        verify(rabbitTemplate).convertAndSend(
                eq(DOCUMENTS_EXCHANGE),
                eq(NOTIFICATION_QUEUE),
                eq(serializedMessage),
                any());
    }
    
    /**
     * Test serialization error handling when publishing a message.
     */
    @Test
    void testSerializationError() throws Exception {
        // Arrange
        NotificationMessage message = createNotificationMessage();
        
        // Mock serialization error
        when(objectMapper.writeValueAsString(any(NotificationMessage.class)))
                .thenThrow(new JsonProcessingException("Failed to serialize message") {});
        
        // Act & Assert
        MessagingException exception = assertThrows(MessagingException.class, () -> {
            rabbitMQProducer.publishNotification(message);
        });
        
        assertTrue(exception.getMessage().contains("Failed to serialize message"));
        assertEquals(MessagingException.ErrorType.SERIALIZATION, exception.getErrorType());
        
        // Verify RabbitTemplate was never called
        verify(rabbitTemplate, never()).convertAndSend(anyString(), anyString(), any());
    }
    
    /**
     * Test connection error handling when publishing a message.
     */
    @Test
    void testConnectionError() throws Exception {
        // Arrange
        NotificationMessage message = createNotificationMessage();
        String serializedMessage = "{\"message_id\":\"123\",\"type\":\"STATUS_UPDATE\"}";
        
        when(objectMapper.writeValueAsString(any(NotificationMessage.class)))
                .thenReturn(serializedMessage);
        
        // Mock connection error
        doThrow(new AmqpException("Connection refused"))
                .when(rabbitTemplate)
                .convertAndSend(anyString(), anyString(), any());
        
        // Configure retry template to throw exception after retries
        when(retryTemplate.execute(any(), any(), any()))
                .thenThrow(new AmqpException("Connection refused after retries"));
        
        // Act & Assert
        MessagingException exception = assertThrows(MessagingException.class, () -> {
            rabbitMQProducer.publishNotification(message);
        });
        
        assertTrue(exception.getMessage().contains("Failed to publish message"));
        assertEquals(MessagingException.ErrorType.CONNECTION, exception.getErrorType());
    }
    
    /**
     * Test retry logic when publishing a message with temporary connection issues.
     */
    @Test
    void testRetryLogic() throws Exception {
        // Arrange
        NotificationMessage message = createNotificationMessage();
        String serializedMessage = "{\"message_id\":\"123\",\"type\":\"STATUS_UPDATE\"}";
        
        when(objectMapper.writeValueAsString(any(NotificationMessage.class)))
                .thenReturn(serializedMessage);
        
        // First call throws exception, second call succeeds
        doThrow(new AmqpException("Temporary connection issue"))
                .doNothing()
                .when(rabbitTemplate)
                .convertAndSend(anyString(), anyString(), any());
        
        // Configure retry template to execute the callback and retry on exception
        when(retryTemplate.execute(any(), any(), any()))
                .thenAnswer(invocation -> {
                    try {
                        return invocation.getArgument(0, RetryTemplate.RetryCallback.class)
                                .doWithRetry(null);
                    } catch (Exception e) {
                        // Simulate retry by calling the callback again
                        return invocation.getArgument(0, RetryTemplate.RetryCallback.class)
                                .doWithRetry(null);
                    }
                });
        
        // Act
        rabbitMQProducer.publishNotification(message);
        
        // Assert
        verify(objectMapper).writeValueAsString(eq(message));
        // Verify convertAndSend was called twice (once for the failure, once for the retry)
        verify(rabbitTemplate, times(2)).convertAndSend(
                eq(DOCUMENTS_EXCHANGE),
                eq(NOTIFICATION_QUEUE),
                eq(serializedMessage));
    }
    
    /**
     * Test publishing a batch of messages.
     */
    @Test
    void testPublishBatch() throws Exception {
        // Arrange
        NotificationMessage message1 = createNotificationMessage();
        NotificationMessage message2 = createNotificationMessage();
        NotificationMessage message3 = createNotificationMessage();
        
        String serializedMessage1 = "{\"message_id\":\"1\",\"type\":\"STATUS_UPDATE\"}";
        String serializedMessage2 = "{\"message_id\":\"2\",\"type\":\"STATUS_UPDATE\"}";
        String serializedMessage3 = "{\"message_id\":\"3\",\"type\":\"STATUS_UPDATE\"}";
        
        when(objectMapper.writeValueAsString(eq(message1)))
                .thenReturn(serializedMessage1);
        when(objectMapper.writeValueAsString(eq(message2)))
                .thenReturn(serializedMessage2);
        when(objectMapper.writeValueAsString(eq(message3)))
                .thenReturn(serializedMessage3);
        
        // Act
        rabbitMQProducer.publishNotificationBatch(java.util.Arrays.asList(message1, message2, message3));
        
        // Assert
        verify(objectMapper, times(3)).writeValueAsString(any(NotificationMessage.class));
        verify(rabbitTemplate, times(3)).convertAndSend(
                eq(DOCUMENTS_EXCHANGE),
                eq(NOTIFICATION_QUEUE),
                any(String.class));
    }
    
    /**
     * Test partial success when publishing a batch of messages.
     */
    @Test
    void testPartialBatchSuccess() throws Exception {
        // Arrange
        NotificationMessage message1 = createNotificationMessage();
        NotificationMessage message2 = createNotificationMessage();
        NotificationMessage message3 = createNotificationMessage();
        
        String serializedMessage1 = "{\"message_id\":\"1\",\"type\":\"STATUS_UPDATE\"}";
        String serializedMessage2 = "{\"message_id\":\"2\",\"type\":\"STATUS_UPDATE\"}";
        
        when(objectMapper.writeValueAsString(eq(message1)))
                .thenReturn(serializedMessage1);
        when(objectMapper.writeValueAsString(eq(message2)))
                .thenReturn(serializedMessage2);
        when(objectMapper.writeValueAsString(eq(message3)))
                .thenThrow(new JsonProcessingException("Serialization failed for message 3") {});
        
        // Act
        MessagingException exception = assertThrows(MessagingException.class, () -> {
            rabbitMQProducer.publishNotificationBatch(java.util.Arrays.asList(message1, message2, message3));
        });
        
        // Assert
        assertTrue(exception.getMessage().contains("Failed to serialize message"));
        assertEquals(MessagingException.ErrorType.SERIALIZATION, exception.getErrorType());
        
        // Verify first two messages were published
        verify(rabbitTemplate, times(2)).convertAndSend(
                eq(DOCUMENTS_EXCHANGE),
                eq(NOTIFICATION_QUEUE),
                any(String.class));
    }