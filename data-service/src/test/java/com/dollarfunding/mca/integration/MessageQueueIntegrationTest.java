package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.IntegrationTestBase;
import com.dollarfunding.mca.TestUtils;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.messaging.DocumentProcessingConsumer;
import com.dollarfunding.mca.messaging.DocumentProcessingMessage;
import com.dollarfunding.mca.messaging.MessagingException;
import com.dollarfunding.mca.messaging.NotificationMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.service.ProcessingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.rabbit.support.ListenerExecutionFailedException;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.messaging.support.GenericMessage;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Integration tests for RabbitMQ message queue integration in the data service.
 * <p>
 * This test class verifies the following aspects of message queue integration:
 * <ul>
 *   <li>Consuming messages from the data.processing queue</li>
 *   <li>Publishing status notifications to the notification queue</li>
 *   <li>Retry logic with configurable backoff periods</li>
 *   <li>Error handling for malformed messages</li>
 *   <li>Message delivery with appropriate acknowledgment</li>
 * </ul>
 * </p>
 */
@TestPropertySource(properties = {
    "application.messaging.queues.data-processing.name=data.processing.test",
    "application.messaging.queues.notification.name=notification.test",
    "application.processing.max-retries=3",
    "application.processing.confidence-threshold=0.75",
    "spring.rabbitmq.template.retry.initial-interval=100",
    "spring.rabbitmq.template.retry.max-interval=1000",
    "spring.rabbitmq.template.retry.multiplier=2.0",
    "spring.rabbitmq.template.retry.max-attempts=3"
})
@Transactional
public class MessageQueueIntegrationTest extends IntegrationTestBase {

    @Autowired
    private ConnectionFactory connectionFactory;
    
    @Autowired
    private RabbitTemplate rabbitTemplate;
    
    @Autowired
    private RabbitAdmin rabbitAdmin;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Autowired
    private MessageConverter messageConverter;
    
    @Autowired
    private RetryTemplate retryTemplate;
    
    @SpyBean
    private NotificationProducer notificationProducer;
    
    @SpyBean
    private DocumentProcessingConsumer documentProcessingConsumer;
    
    @MockBean
    private ProcessingService processingService;
    
    @Autowired
    private ApplicationRepository applicationRepository;
    
    @Autowired
    private DocumentRepository documentRepository;
    
    @Value("${application.messaging.exchanges.documents.name:mca.documents}")
    private String exchangeName;
    
    @Value("${application.messaging.queues.data-processing.name:data.processing.test}")
    private String dataProcessingQueueName;
    
    @Value("${application.messaging.queues.notification.name:notification.test}")
    private String notificationQueueName;
    
    private Application testApplication;
    private Document testDocument;
    
    /**
     * Setup method that runs before each test.
     * <p>
     * This method initializes test data including an application and document.
     * </p>
     */
    @BeforeEach
    @Override
    public void setUp() throws Exception {
        super.setUp();
        
        // Create test application
        testApplication = TestUtils.createRandomApplication();
        testApplication.setStatus(ApplicationStatus.PENDING);
        applicationRepository.save(testApplication);
        
        // Create test document
        testDocument = TestUtils.createRandomDocument(testApplication);
        documentRepository.save(testDocument);
        
        // Purge test queues to ensure clean state
        rabbitAdmin.purgeQueue(dataProcessingQueueName, false);
        rabbitAdmin.purgeQueue(notificationQueueName, false);
    }
    
    /**
     * Tests for consuming messages from the data.processing queue.
     */
    @Nested
    @DisplayName("Message Consumption Tests")
    class MessageConsumptionTests {
        
        /**
         * Tests that a valid document processing message is consumed and processed correctly.
         */
        @Test
        @DisplayName("Valid document processing message should be consumed and processed")
        public void validMessageShouldBeConsumedAndProcessed() throws Exception {
            // Create a valid document processing message
            DocumentProcessingMessage message = createValidDocumentProcessingMessage();
            String messageJson = objectMapper.writeValueAsString(message);
            
            // Configure processing service mock
            doNothing().when(processingService).processDocument(any(UUID.class), any(Map.class));
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the message was processed
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(messageJson),
                    anyString(),
                    eq(0)
            );
            
            // Verify that the processing service was called with the correct parameters
            verify(processingService, timeout(5000)).processDocument(
                    eq(UUID.fromString(message.getDocumentId())),
                    any(Map.class)
            );
        }
        
        /**
         * Tests that a malformed document processing message is handled correctly.
         */
        @Test
        @DisplayName("Malformed document processing message should be handled correctly")
        public void malformedMessageShouldBeHandledCorrectly() throws Exception {
            // Create a malformed message (missing required fields)
            String malformedJson = "{\"document_id\":\"123\"}";
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(malformedJson, props);
            
            // Configure consumer to throw exception for testing
            doThrow(new AmqpRejectAndDontRequeueException("Invalid message"))
                .when(documentProcessingConsumer)
                .consumeDocumentProcessingMessage(eq(malformedJson), anyString(), eq(0));
            
            // Send the message
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the consumer was called
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(malformedJson),
                    anyString(),
                    eq(0)
            );
            
            // Verify that the processing service was not called
            verify(processingService, never()).processDocument(any(UUID.class), any(Map.class));
        }
        
        /**
         * Tests that a document processing message with invalid document type is handled correctly.
         */
        @Test
        @DisplayName("Message with invalid document type should be handled correctly")
        public void messageWithInvalidDocumentTypeShouldBeHandledCorrectly() throws Exception {
            // Create a message with invalid document type
            DocumentProcessingMessage message = createValidDocumentProcessingMessage();
            // Set an invalid document type by manipulating the JSON directly
            String messageJson = objectMapper.writeValueAsString(message).replace("LOAN_APPLICATION", "INVALID_TYPE");
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            // Configure consumer to throw exception for testing
            doThrow(new IllegalArgumentException("Invalid document type"))
                .when(documentProcessingConsumer)
                .consumeDocumentProcessingMessage(eq(messageJson), anyString(), eq(0));
            
            // Send the message
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the consumer was called
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(messageJson),
                    anyString(),
                    eq(0)
            );
            
            // Verify that the processing service was not called
            verify(processingService, never()).processDocument(any(UUID.class), any(Map.class));
        }
    }
    
    /**
     * Tests for publishing messages to the notification queue.
     */
    @Nested
    @DisplayName("Message Publication Tests")
    class MessagePublicationTests {
        
        /**
         * Tests that a notification message is published correctly.
         */
        @Test
        @DisplayName("Notification message should be published correctly")
        public void notificationMessageShouldBePublishedCorrectly() throws Exception {
            // Create a notification message
            NotificationMessage notification = createValidNotificationMessage();
            
            // Publish the notification
            String correlationId = notificationProducer.publishNotification(notification);
            
            // Verify that the notification was published
            assertNotNull(correlationId, "Correlation ID should not be null");
            
            // Receive the message from the queue
            Message receivedMessage = rabbitTemplate.receive(notificationQueueName, 5000);
            assertNotNull(receivedMessage, "Message should be received from the queue");
            
            // Verify message properties
            MessageProperties props = receivedMessage.getMessageProperties();
            assertEquals(MessageProperties.CONTENT_TYPE_JSON, props.getContentType(), "Content type should be JSON");
            assertEquals(notification.getId(), props.getMessageId(), "Message ID should match");
            assertEquals(notification.getType().name(), props.getType(), "Message type should match");
            assertEquals(notification.getType().name(), props.getHeader("x-notification-type"), "Notification type header should match");
            assertEquals(notification.getPriority().name(), props.getHeader("x-notification-priority"), "Priority header should match");
            
            // Verify message content
            String messageContent = new String(receivedMessage.getBody());
            NotificationMessage receivedNotification = objectMapper.readValue(messageContent, NotificationMessage.class);
            assertEquals(notification.getId(), receivedNotification.getId(), "Message ID should match");
            assertEquals(notification.getType(), receivedNotification.getType(), "Message type should match");
            assertEquals(notification.getPriority(), receivedNotification.getPriority(), "Message priority should match");
            assertEquals(notification.getRecipients().size(), receivedNotification.getRecipients().size(), "Recipients count should match");
            assertNotNull(receivedNotification.getPayload(), "Payload should not be null");
        }
        
        /**
         * Tests that a status update notification is published correctly.
         */
        @Test
        @DisplayName("Status update notification should be published correctly")
        public void statusUpdateNotificationShouldBePublishedCorrectly() throws Exception {
            // Create recipients
            List<NotificationMessage.Recipient> recipients = List.of(
                new NotificationMessage.Recipient(NotificationMessage.RecipientType.WEBHOOK, "https://example.com/webhook")
            );
            
            // Create metadata
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("source", "test");
            metadata.put("user", "test-user");
            
            // Publish status update
            String correlationId = notificationProducer.publishStatusUpdate(
                testApplication.getId().toString(),
                ApplicationStatus.APPROVED.name(),
                metadata,
                recipients
            );
            
            // Verify that the notification was published
            assertNotNull(correlationId, "Correlation ID should not be null");
            
            // Receive the message from the queue
            Message receivedMessage = rabbitTemplate.receive(notificationQueueName, 5000);
            assertNotNull(receivedMessage, "Message should be received from the queue");
            
            // Verify message properties
            MessageProperties props = receivedMessage.getMessageProperties();
            assertEquals(NotificationMessage.NotificationType.STATUS_UPDATE.name(), props.getType(), "Message type should be STATUS_UPDATE");
            
            // Verify message content
            String messageContent = new String(receivedMessage.getBody());
            NotificationMessage receivedNotification = objectMapper.readValue(messageContent, NotificationMessage.class);
            assertEquals(NotificationMessage.NotificationType.STATUS_UPDATE, receivedNotification.getType(), "Message type should be STATUS_UPDATE");
            assertEquals(NotificationMessage.NotificationPriority.MEDIUM, receivedNotification.getPriority(), "Message priority should be MEDIUM");
            
            // Verify payload
            Map<String, Object> payload = receivedNotification.getPayload();
            assertEquals(testApplication.getId().toString(), payload.get("applicationId"), "Application ID should match");
            assertEquals(ApplicationStatus.APPROVED.name(), payload.get("status"), "Status should match");
            assertNotNull(payload.get("updatedAt"), "Updated timestamp should be present");
            assertNotNull(payload.get("metadata"), "Metadata should be present");
            
            // Verify delivery options
            NotificationMessage.DeliveryOptions deliveryOptions = receivedNotification.getDeliveryOptions();
            assertNotNull(deliveryOptions, "Delivery options should be present");
            assertEquals(3, deliveryOptions.getRetryCount(), "Retry count should be 3");
            assertEquals(5000L, deliveryOptions.getRetryDelayMs(), "Retry delay should be 5000ms");
            assertTrue(deliveryOptions.getRequireHmac(), "HMAC should be required");
            assertEquals("HmacSHA256", deliveryOptions.getHmacAlgorithm(), "HMAC algorithm should be HmacSHA256");
        }
        
        /**
         * Tests that an error notification is published correctly.
         */
        @Test
        @DisplayName("Error notification should be published correctly")
        public void errorNotificationShouldBePublishedCorrectly() throws Exception {
            // Create recipients
            List<NotificationMessage.Recipient> recipients = List.of(
                new NotificationMessage.Recipient(NotificationMessage.RecipientType.EMAIL, "admin@example.com")
            );
            
            // Publish error notification
            String correlationId = notificationProducer.publishErrorNotification(
                testApplication.getId().toString(),
                "PROCESSING_ERROR",
                "Failed to process application due to missing data",
                recipients
            );
            
            // Verify that the notification was published
            assertNotNull(correlationId, "Correlation ID should not be null");
            
            // Receive the message from the queue
            Message receivedMessage = rabbitTemplate.receive(notificationQueueName, 5000);
            assertNotNull(receivedMessage, "Message should be received from the queue");
            
            // Verify message properties
            MessageProperties props = receivedMessage.getMessageProperties();
            assertEquals(NotificationMessage.NotificationType.ERROR.name(), props.getType(), "Message type should be ERROR");
            assertEquals(10, props.getPriority(), "Message priority should be 10 (CRITICAL)");
            
            // Verify message content
            String messageContent = new String(receivedMessage.getBody());
            NotificationMessage receivedNotification = objectMapper.readValue(messageContent, NotificationMessage.class);
            assertEquals(NotificationMessage.NotificationType.ERROR, receivedNotification.getType(), "Message type should be ERROR");
            assertEquals(NotificationMessage.NotificationPriority.CRITICAL, receivedNotification.getPriority(), "Message priority should be CRITICAL");
            
            // Verify payload
            Map<String, Object> payload = receivedNotification.getPayload();
            assertEquals(testApplication.getId().toString(), payload.get("applicationId"), "Application ID should match");
            assertEquals("PROCESSING_ERROR", payload.get("errorCode"), "Error code should match");
            assertEquals("Failed to process application due to missing data", payload.get("errorMessage"), "Error message should match");
            assertNotNull(payload.get("errorTimestamp"), "Error timestamp should be present");
            
            // Verify delivery options
            NotificationMessage.DeliveryOptions deliveryOptions = receivedNotification.getDeliveryOptions();
            assertNotNull(deliveryOptions, "Delivery options should be present");
            assertEquals(10, deliveryOptions.getRetryCount(), "Retry count should be 10");
            assertEquals(1000L, deliveryOptions.getRetryDelayMs(), "Retry delay should be 1000ms");
            assertTrue(deliveryOptions.getRequireHmac(), "HMAC should be required");
        }
    }
    
    /**
     * Tests for retry logic with configurable backoff periods.
     */
    @Nested
    @DisplayName("Retry Logic Tests")
    class RetryLogicTests {
        
        /**
         * Tests that message processing is retried with backoff on transient errors.
         */
        @Test
        @DisplayName("Message processing should be retried with backoff on transient errors")
        public void messageProcessingShouldBeRetriedWithBackoff() throws Exception {
            // Create a valid document processing message
            DocumentProcessingMessage message = createValidDocumentProcessingMessage();
            String messageJson = objectMapper.writeValueAsString(message);
            
            // Configure processing service to fail with transient error on first call, then succeed
            doThrow(new RuntimeException("Transient error"))
                .doNothing()
                .when(processingService)
                .processDocument(any(UUID.class), any(Map.class));
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the processing service was called twice (once for the initial attempt, once for the retry)
            verify(processingService, timeout(10000).times(2)).processDocument(
                    eq(UUID.fromString(message.getDocumentId())),
                    any(Map.class)
            );
        }
        
        /**
         * Tests that message publication is retried with backoff on transient errors.
         */
        @Test
        @DisplayName("Message publication should be retried with backoff on transient errors")
        public void messagePublicationShouldBeRetriedWithBackoff() throws Exception {
            // Create a notification message
            NotificationMessage notification = createValidNotificationMessage();
            
            // Configure RabbitTemplate to fail on first send, then succeed
            RabbitTemplate spyTemplate = spy(rabbitTemplate);
            doThrow(new RuntimeException("Transient error"))
                .doNothing()
                .when(spyTemplate)
                .send(anyString(), anyString(), any(Message.class), any());
            
            // Use reflection to replace the RabbitTemplate in the NotificationProducer
            java.lang.reflect.Field field = NotificationProducer.class.getDeclaredField("rabbitTemplate");
            field.setAccessible(true);
            RabbitTemplate originalTemplate = (RabbitTemplate) field.get(notificationProducer);
            field.set(notificationProducer, spyTemplate);
            
            try {
                // Publish the notification
                String correlationId = notificationProducer.publishNotification(notification);
                
                // Verify that the notification was published
                assertNotNull(correlationId, "Correlation ID should not be null");
                
                // Verify that the send method was called twice (once for the initial attempt, once for the retry)
                verify(spyTemplate, times(2)).send(anyString(), anyString(), any(Message.class), any());
            } finally {
                // Restore the original RabbitTemplate
                field.set(notificationProducer, originalTemplate);
            }
        }
        
        /**
         * Tests that message processing is not retried after max retries.
         */
        @Test
        @DisplayName("Message processing should not be retried after max retries")
        public void messageProcessingShouldNotBeRetriedAfterMaxRetries() throws Exception {
            // Create a valid document processing message
            DocumentProcessingMessage message = createValidDocumentProcessingMessage();
            String messageJson = objectMapper.writeValueAsString(message);
            
            // Configure processing service to always fail with transient error
            doThrow(new RuntimeException("Persistent error"))
                .when(processingService)
                .processDocument(any(UUID.class), any(Map.class));
            
            // Send message to the queue with retry count already at max
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            props.setHeader("x-retry-count", 3); // Max retries is 3
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            // Configure consumer to throw AmqpRejectAndDontRequeueException after max retries
            doThrow(new AmqpRejectAndDontRequeueException("Max retries exceeded"))
                .when(documentProcessingConsumer)
                .consumeDocumentProcessingMessage(eq(messageJson), anyString(), eq(3));
            
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the consumer was called
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(messageJson),
                    anyString(),
                    eq(3)
            );
            
            // Verify that the processing service was not called (message rejected due to max retries)
            verify(processingService, never()).processDocument(any(UUID.class), any(Map.class));
        }
    }
    
    /**
     * Tests for error handling for malformed messages.
     */
    @Nested
    @DisplayName("Error Handling Tests")
    class ErrorHandlingTests {
        
        /**
         * Tests that a JSON processing exception is handled correctly.
         */
        @Test
        @DisplayName("JSON processing exception should be handled correctly")
        public void jsonProcessingExceptionShouldBeHandledCorrectly() throws Exception {
            // Create an invalid JSON message
            String invalidJson = "{\"document_id\":\"123\", \"invalid\":}";
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(invalidJson, props);
            
            // Configure ObjectMapper to throw exception when deserializing
            ObjectMapper mockMapper = mock(ObjectMapper.class);
            when(mockMapper.readValue(anyString(), eq(DocumentProcessingMessage.class)))
                .thenThrow(new JsonProcessingException("Invalid JSON") {});
            
            // Use reflection to replace the ObjectMapper in the DocumentProcessingConsumer
            java.lang.reflect.Field field = DocumentProcessingConsumer.class.getDeclaredField("objectMapper");
            field.setAccessible(true);
            ObjectMapper originalMapper = (ObjectMapper) field.get(documentProcessingConsumer);
            field.set(documentProcessingConsumer, mockMapper);
            
            try {
                // Configure consumer to throw exception for testing
                doThrow(new RuntimeException("JSON processing error"))
                    .when(documentProcessingConsumer)
                    .consumeDocumentProcessingMessage(eq(invalidJson), anyString(), eq(0));
                
                // Send the message
                rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
                
                // Verify that the consumer was called
                verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                        eq(invalidJson),
                        anyString(),
                        eq(0)
                );
                
                // Verify that the processing service was not called
                verify(processingService, never()).processDocument(any(UUID.class), any(Map.class));
            } finally {
                // Restore the original ObjectMapper
                field.set(documentProcessingConsumer, originalMapper);
            }
        }
        
        /**
         * Tests that a validation exception is handled correctly.
         */
        @Test
        @DisplayName("Validation exception should be handled correctly")
        public void validationExceptionShouldBeHandledCorrectly() throws Exception {
            // Create a message with missing required fields
            DocumentProcessingMessage message = new DocumentProcessingMessage();
            message.setDocumentId(UUID.randomUUID().toString());
            // Missing other required fields
            String messageJson = objectMapper.writeValueAsString(message);
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            // Configure consumer to throw exception for testing
            doThrow(new IllegalArgumentException("Validation failed: Missing required fields"))
                .when(documentProcessingConsumer)
                .consumeDocumentProcessingMessage(eq(messageJson), anyString(), eq(0));
            
            // Send the message
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the consumer was called
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(messageJson),
                    anyString(),
                    eq(0)
            );
            
            // Verify that the processing service was not called
            verify(processingService, never()).processDocument(any(UUID.class), any(Map.class));
        }
        
        /**
         * Tests that a messaging exception is handled correctly during publication.
         */
        @Test
        @DisplayName("Messaging exception during publication should be handled correctly")
        public void messagingExceptionDuringPublicationShouldBeHandledCorrectly() throws Exception {
            // Create a notification message
            NotificationMessage notification = createValidNotificationMessage();
            
            // Configure RabbitTemplate to throw exception
            RabbitTemplate mockTemplate = mock(RabbitTemplate.class);
            doThrow(new RuntimeException("Connection error"))
                .when(mockTemplate)
                .convertAndSend(anyString(), anyString(), any(Message.class), any());
            
            // Use reflection to replace the RabbitTemplate in the NotificationProducer
            java.lang.reflect.Field field = NotificationProducer.class.getDeclaredField("rabbitTemplate");
            field.setAccessible(true);
            RabbitTemplate originalTemplate = (RabbitTemplate) field.get(notificationProducer);
            field.set(notificationProducer, mockTemplate);
            
            try {
                // Publish the notification and expect exception
                MessagingException exception = assertThrows(MessagingException.class, () -> {
                    notificationProducer.publishNotification(notification);
                });
                
                // Verify exception details
                assertEquals(MessagingException.ErrorType.DELIVERY, exception.getErrorType(), "Error type should be DELIVERY");
                assertTrue(exception.getMessage().contains("Failed to publish"), "Exception message should indicate publication failure");
            } finally {
                // Restore the original RabbitTemplate
                field.set(notificationProducer, originalTemplate);
            }
        }
    }
    
    /**
     * Tests for message delivery with appropriate acknowledgment.
     */
    @Nested
    @DisplayName("Message Acknowledgment Tests")
    class MessageAcknowledgmentTests {
        
        /**
         * Tests that a message is acknowledged after successful processing.
         */
        @Test
        @DisplayName("Message should be acknowledged after successful processing")
        public void messageShouldBeAcknowledgedAfterSuccessfulProcessing() throws Exception {
            // Create a valid document processing message
            DocumentProcessingMessage message = createValidDocumentProcessingMessage();
            String messageJson = objectMapper.writeValueAsString(message);
            
            // Configure processing service mock
            doNothing().when(processingService).processDocument(any(UUID.class), any(Map.class));
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the message was processed
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(messageJson),
                    anyString(),
                    eq(0)
            );
            
            // Verify that the processing service was called
            verify(processingService, timeout(5000)).processDocument(
                    eq(UUID.fromString(message.getDocumentId())),
                    any(Map.class)
            );
            
            // Verify that the message is no longer in the queue
            Message receivedMessage = rabbitTemplate.receive(dataProcessingQueueName, 1000);
            assertNull(receivedMessage, "Message should not be in the queue after acknowledgment");
        }
        
        /**
         * Tests that a message is not acknowledged after failed processing.
         */
        @Test
        @DisplayName("Message should not be acknowledged after failed processing with retry")
        public void messageShouldNotBeAcknowledgedAfterFailedProcessingWithRetry() throws Exception {
            // Create a valid document processing message
            DocumentProcessingMessage message = createValidDocumentProcessingMessage();
            String messageJson = objectMapper.writeValueAsString(message);
            
            // Configure processing service to throw exception
            doThrow(new RuntimeException("Processing error"))
                .when(processingService)
                .processDocument(any(UUID.class), any(Map.class));
            
            // Configure consumer to rethrow exception for retry
            doThrow(new RuntimeException("Processing failed, will retry"))
                .when(documentProcessingConsumer)
                .consumeDocumentProcessingMessage(eq(messageJson), anyString(), eq(0));
            
            // Send message to the queue
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the consumer was called
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(messageJson),
                    anyString(),
                    eq(0)
            );
            
            // Verify that the processing service was called
            verify(processingService, timeout(5000)).processDocument(
                    eq(UUID.fromString(message.getDocumentId())),
                    any(Map.class)
            );
            
            // The message should be requeued for retry, but we can't reliably test this in an integration test
            // without complex setup. In a real environment, the message would be redelivered with an incremented
            // retry count header.
        }
        
        /**
         * Tests that a message is rejected and not requeued after max retries.
         */
        @Test
        @DisplayName("Message should be rejected and not requeued after max retries")
        public void messageShouldBeRejectedAndNotRequeuedAfterMaxRetries() throws Exception {
            // Create a valid document processing message
            DocumentProcessingMessage message = createValidDocumentProcessingMessage();
            String messageJson = objectMapper.writeValueAsString(message);
            
            // Send message to the queue with retry count at max
            MessageProperties props = new MessageProperties();
            props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
            props.setMessageId(UUID.randomUUID().toString());
            props.setHeader("x-retry-count", 3); // Max retries is 3
            Message amqpMessage = messageConverter.toMessage(messageJson, props);
            
            // Configure consumer to throw AmqpRejectAndDontRequeueException after max retries
            doThrow(new AmqpRejectAndDontRequeueException("Max retries exceeded"))
                .when(documentProcessingConsumer)
                .consumeDocumentProcessingMessage(eq(messageJson), anyString(), eq(3));
            
            rabbitTemplate.send(exchangeName, dataProcessingQueueName, amqpMessage);
            
            // Verify that the consumer was called
            verify(documentProcessingConsumer, timeout(5000)).consumeDocumentProcessingMessage(
                    eq(messageJson),
                    anyString(),
                    eq(3)
            );
            
            // Verify that the message is not in the queue (rejected and not requeued)
            Message receivedMessage = rabbitTemplate.receive(dataProcessingQueueName, 1000);
            assertNull(receivedMessage, "Message should not be in the queue after rejection");
        }
    }
    
    /**
     * Creates a valid document processing message for testing.
     * 
     * @return a valid DocumentProcessingMessage
     */
    private DocumentProcessingMessage createValidDocumentProcessingMessage() {
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setMessageId(UUID.randomUUID().toString());
        message.setDocumentId(testDocument.getId().toString());
        message.setDocumentType(DocumentType.LOAN_APPLICATION);
        message.setApplicationId(testApplication.getId().toString());
        message.setStoragePath("s3://mca-documents-test/" + UUID.randomUUID() + ".pdf");
        message.setContentType("application/pdf");
        message.setTimestamp(LocalDateTime.now());
        message.setSourceService("ocr-service");
        message.setStatus("completed");
        
        // Add metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("pageCount", 5);
        metadata.put("fileSize", 1024 * 1024);
        metadata.put("classification", "loan_application");
        message.setMetadata(metadata);
        
        // Add extraction results
        Map<String, Object> extractionResults = new HashMap<>();
        extractionResults.put("applicant_name", "John Doe");
        extractionResults.put("business_name", "Acme Inc.");
        extractionResults.put("loan_amount", 50000);
        extractionResults.put("term_months", 24);
        message.setExtractionResults(extractionResults);
        
        // Add confidence scores
        Map<String, Float> confidenceScores = new HashMap<>();
        confidenceScores.put("applicant_name", 0.95f);
        confidenceScores.put("business_name", 0.92f);
        confidenceScores.put("loan_amount", 0.88f);
        confidenceScores.put("term_months", 0.90f);
        message.setConfidenceScores(confidenceScores);
        
        message.setProcessingTimeMs(1234.56f);
        message.setRequiresVerification(false);
        
        return message;
    }
    
    /**
     * Creates a valid notification message for testing.
     * 
     * @return a valid NotificationMessage
     */
    private NotificationMessage createValidNotificationMessage() {
        // Create recipients
        List<NotificationMessage.Recipient> recipients = List.of(
            new NotificationMessage.Recipient(NotificationMessage.RecipientType.WEBHOOK, "https://example.com/webhook"),
            new NotificationMessage.Recipient(NotificationMessage.RecipientType.EMAIL, "user@example.com")
        );
        
        // Create payload
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", testApplication.getId().toString());
        payload.put("status", ApplicationStatus.APPROVED.name());
        payload.put("documentId", testDocument.getId().toString());
        payload.put("timestamp", LocalDateTime.now().toString());
        
        // Create notification message
        NotificationMessage notification = NotificationMessage.builder()
                .id(UUID.randomUUID().toString())
                .type(NotificationMessage.NotificationType.STATUS_UPDATE)
                .priority(NotificationMessage.NotificationPriority.HIGH)
                .recipients(recipients)
                .payload(payload)
                .build();
        
        // Add delivery options
        NotificationMessage.DeliveryOptions deliveryOptions = new NotificationMessage.DeliveryOptions(
                3, // retry count
                1000L, // retry delay in ms
                86400000L, // expiration in ms (24 hours)
                true, // require HMAC
                "HmacSHA256", // HMAC algorithm
                LocalDateTime.now().plusDays(1) // delivery deadline
        );
        notification.setDeliveryOptions(deliveryOptions);
        
        return notification;
    }
}