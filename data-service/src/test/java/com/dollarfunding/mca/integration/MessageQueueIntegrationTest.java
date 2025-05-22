package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.messaging.DocumentProcessingConsumer;
import com.dollarfunding.mca.messaging.DocumentProcessingMessage;
import com.dollarfunding.mca.messaging.NotificationMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import com.dollarfunding.mca.service.ProcessingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mockito;
import org.mockito.Spy;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.MessagePropertiesBuilder;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Integration tests for RabbitMQ message queue integration in the data service.
 * 
 * This test class verifies:
 * 1. Consuming messages from the data.processing queue
 * 2. Publishing status notifications to the notification queue
 * 3. Testing retry logic with configurable backoff periods
 * 4. Handling malformed messages with appropriate error logging
 * 5. Ensuring message delivery with appropriate acknowledgment
 */
@ExtendWith(SpringExtension.class)
@SpringBootTest
@ActiveProfiles("test")
public class MessageQueueIntegrationTest {

    @Autowired
    private RabbitTemplate rabbitTemplate;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @SpyBean
    private NotificationProducer notificationProducer;
    
    @MockBean
    private ProcessingService processingService;
    
    @SpyBean
    private DocumentProcessingConsumer documentProcessingConsumer;
    
    @Value("${application.messaging.queues.document-processing.name:document-processing}")
    private String documentProcessingQueueName;
    
    @Value("${application.messaging.queues.notification.name:notification}")
    private String notificationQueueName;
    
    @Value("${application.messaging.exchanges.documents.name:mca.documents}")
    private String documentsExchangeName;
    
    @Captor
    private ArgumentCaptor<DocumentProcessingMessage> messageCaptor;
    
    @Captor
    private ArgumentCaptor<Message> rabbitMessageCaptor;
    
    @Captor
    private ArgumentCaptor<NotificationMessage> notificationCaptor;
    
    private DocumentProcessingMessage validMessage;
    private String validMessageJson;
    
    @BeforeEach
    public void setup() throws JsonProcessingException {
        // Create a valid document processing message for testing
        Map<String, DocumentProcessingMessage.ExtractedField> extractedFields = new HashMap<>();
        extractedFields.put("businessName", new DocumentProcessingMessage.ExtractedField("Dollar Funding LLC", 95.5));
        extractedFields.put("taxId", new DocumentProcessingMessage.ExtractedField("12-3456789", 90.2));
        extractedFields.put("address", new DocumentProcessingMessage.ExtractedField("123 Main St, Anytown, CA 90210", 88.7));
        
        validMessage = DocumentProcessingMessage.builder()
                .id(UUID.randomUUID().toString())
                .documentId(UUID.randomUUID().toString())
                .documentType(DocumentProcessingMessage.DocumentType.APPLICATION_FORM)
                .classification("loan_application")
                .classificationConfidence(92.5)
                .processingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION)
                .extractedFields(extractedFields)
                .build();
        
        validMessageJson = objectMapper.writeValueAsString(validMessage);
        
        // Reset mocks
        reset(processingService, notificationProducer, documentProcessingConsumer);
    }
    
    /**
     * Tests successful consumption of a valid message from the data.processing queue.
     * Verifies that the message is properly deserialized and processed by the service.
     */
    @Test
    public void testConsumeValidMessage() throws Exception {
        // Arrange
        doNothing().when(processingService).processNewApplication(any(DocumentProcessingMessage.class));
        
        // Create a RabbitMQ message with the valid JSON payload
        MessageProperties props = new MessageProperties();
        props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
        Message rabbitMessage = new Message(validMessageJson.getBytes(StandardCharsets.UTF_8), props);
        
        // Act
        documentProcessingConsumer.processDocumentMessage(rabbitMessage);
        
        // Assert
        verify(processingService, times(1)).processNewApplication(messageCaptor.capture());
        DocumentProcessingMessage capturedMessage = messageCaptor.getValue();
        assertEquals(validMessage.getId(), capturedMessage.getId());
        assertEquals(validMessage.getDocumentId(), capturedMessage.getDocumentId());
        assertEquals(validMessage.getDocumentType(), capturedMessage.getDocumentType());
        assertEquals(validMessage.getClassification(), capturedMessage.getClassification());
        assertEquals(validMessage.getClassificationConfidence(), capturedMessage.getClassificationConfidence());
        assertEquals(validMessage.getProcessingAction(), capturedMessage.getProcessingAction());
        
        // Verify extracted fields
        assertEquals("Dollar Funding LLC", capturedMessage.getExtractedFields().get("businessName").getValue());
        assertEquals(95.5, capturedMessage.getExtractedFields().get("businessName").getConfidence());
        assertEquals("12-3456789", capturedMessage.getExtractedFields().get("taxId").getValue());
        assertEquals(90.2, capturedMessage.getExtractedFields().get("taxId").getConfidence());
    }
    
    /**
     * Tests handling of malformed messages from the data.processing queue.
     * Verifies that invalid messages are rejected and not requeued.
     */
    @Test
    public void testConsumeInvalidMessage() {
        // Arrange
        String invalidJson = "{\"id\":\"123\", \"invalid_field\": true}";
        MessageProperties props = new MessageProperties();
        props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
        Message rabbitMessage = new Message(invalidJson.getBytes(StandardCharsets.UTF_8), props);
        
        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(rabbitMessage);
        });
        
        // Verify that the processing service was never called
        verify(processingService, never()).processNewApplication(any());
        verify(processingService, never()).updateExistingApplication(any());
        verify(processingService, never()).processSupportingDocument(any());
    }
    
    /**
     * Tests the retry mechanism for failed message processing.
     * Verifies that messages are retried with exponential backoff when processing fails.
     */
    @Test
    public void testRetryLogic() throws Exception {
        // Arrange
        // Configure the processing service to throw an exception to trigger retry
        doThrow(new RuntimeException("Simulated processing error"))
                .when(processingService).processNewApplication(any(DocumentProcessingMessage.class));
        
        // Mock the rabbitTemplate to capture the retry message
        doNothing().when(rabbitTemplate).send(anyString(), anyString(), any(Message.class));
        
        // Create a RabbitMQ message with the valid JSON payload
        MessageProperties props = new MessageProperties();
        props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
        Message rabbitMessage = new Message(validMessageJson.getBytes(StandardCharsets.UTF_8), props);
        
        // Set the rabbitTemplate field in the consumer using reflection
        java.lang.reflect.Field rabbitTemplateField = DocumentProcessingConsumer.class.getDeclaredField("rabbitTemplate");
        rabbitTemplateField.setAccessible(true);
        rabbitTemplateField.set(documentProcessingConsumer, rabbitTemplate);
        
        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(rabbitMessage);
        });
        
        // Verify that the processing service was called
        verify(processingService, times(1)).processNewApplication(any(DocumentProcessingMessage.class));
        
        // Verify that the message was sent for retry
        verify(rabbitTemplate, times(1)).send(anyString(), anyString(), rabbitMessageCaptor.capture());
        
        // Verify retry count header was incremented
        Message retryMessage = rabbitMessageCaptor.getValue();
        assertNotNull(retryMessage);
        assertEquals(1, retryMessage.getMessageProperties().getHeaders().get("x-retry-count"));
        
        // Verify exponential backoff delay was set
        assertTrue(retryMessage.getMessageProperties().getHeaders().containsKey("x-delay"));
        long delay = (long) retryMessage.getMessageProperties().getHeaders().get("x-delay");
        assertEquals(1000L, delay); // First retry should have 1000ms delay
    }
    
    /**
     * Tests publishing notifications to the notification queue.
     * Verifies that notifications are properly serialized and published to the queue.
     */
    @Test
    public void testPublishNotification() throws Exception {
        // Arrange
        String applicationId = UUID.randomUUID().toString();
        String documentId = UUID.randomUUID().toString();
        
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", applicationId);
        payload.put("documentId", documentId);
        payload.put("status", "PROCESSED");
        payload.put("timestamp", LocalDateTime.now().toString());
        
        List<NotificationMessage.Recipient> recipients = new ArrayList<>();
        recipients.add(new NotificationMessage.Recipient(
                NotificationMessage.Channel.WEBHOOK,
                "https://example.com/webhook",
                "Example Webhook",
                new HashMap<>()));
        
        NotificationMessage notification = NotificationMessage.builder()
                .id(UUID.randomUUID().toString())
                .type(NotificationMessage.Type.STATUS_UPDATE)
                .priority(NotificationMessage.Priority.HIGH)
                .recipients(recipients)
                .payload(payload)
                .build();
        
        // Configure the rabbitTemplate to capture the published message
        doNothing().when(rabbitTemplate).send(anyString(), anyString(), any(Message.class), any(CorrelationData.class));
        
        // Act
        boolean result = notificationProducer.publishNotification(notification);
        
        // Assert
        assertTrue(result);
        verify(rabbitTemplate, times(1)).send(
                eq(documentsExchangeName),
                eq(notificationQueueName),
                any(Message.class),
                any(CorrelationData.class));
    }
    
    /**
     * Tests message acknowledgment for successfully processed messages.
     * Verifies that messages are properly acknowledged when processing succeeds.
     */
    @Test
    public void testMessageAcknowledgment() throws Exception {
        // Arrange
        CountDownLatch latch = new CountDownLatch(1);
        
        // Configure the processing service to count down the latch when called
        doAnswer(invocation -> {
            latch.countDown();
            return null;
        }).when(processingService).processNewApplication(any(DocumentProcessingMessage.class));
        
        // Create a RabbitMQ message with the valid JSON payload
        MessageProperties props = new MessageProperties();
        props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
        Message rabbitMessage = new Message(validMessageJson.getBytes(StandardCharsets.UTF_8), props);
        
        // Act
        documentProcessingConsumer.processDocumentMessage(rabbitMessage);
        
        // Assert
        assertTrue(latch.await(5, TimeUnit.SECONDS), "Processing service was not called");
        verify(processingService, times(1)).processNewApplication(any(DocumentProcessingMessage.class));
        
        // No exception means the message was acknowledged successfully
        // If there was an issue with acknowledgment, an exception would have been thrown
    }
    
    /**
     * Tests handling of messages with missing required fields.
     * Verifies that validation errors are properly handled and messages are rejected.
     */
    @Test
    public void testMessageValidation() throws Exception {
        // Arrange
        // Create a message with missing required fields
        DocumentProcessingMessage invalidMessage = DocumentProcessingMessage.builder()
                .id(UUID.randomUUID().toString())
                // Missing documentId
                .documentType(DocumentProcessingMessage.DocumentType.APPLICATION_FORM)
                .classification("loan_application")
                .classificationConfidence(92.5)
                .processingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION)
                .build();
        
        String invalidMessageJson = objectMapper.writeValueAsString(invalidMessage);
        
        MessageProperties props = new MessageProperties();
        props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
        Message rabbitMessage = new Message(invalidMessageJson.getBytes(StandardCharsets.UTF_8), props);
        
        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(rabbitMessage);
        });
        
        // Verify that the processing service was never called
        verify(processingService, never()).processNewApplication(any());
    }
    
    /**
     * Tests the notification delivery with retry for failed publications.
     * Verifies that notifications are retried with exponential backoff when publishing fails.
     */
    @Test
    public void testNotificationRetry() throws Exception {
        // Arrange
        NotificationMessage notification = createTestNotification();
        
        // Configure the rabbitTemplate to throw an exception on first call, then succeed
        doThrow(new RuntimeException("Simulated connection error"))
                .doNothing()
                .when(rabbitTemplate).send(anyString(), anyString(), any(Message.class), any(CorrelationData.class));
        
        // Act
        boolean result = notificationProducer.publishNotification(notification);
        
        // Assert
        assertTrue(result);
        
        // Verify initial publish attempt
        verify(rabbitTemplate, times(1)).send(
                eq(documentsExchangeName),
                eq(notificationQueueName),
                any(Message.class),
                any(CorrelationData.class));
        
        // Verify retry logic was triggered
        // This would normally happen in a separate thread, so we need to manually trigger it
        // Use reflection to access the private method
        java.lang.reflect.Method handleFailedPublicationMethod = NotificationProducer.class.getDeclaredMethod(
                "handleFailedPublication", String.class, String.class);
        handleFailedPublicationMethod.setAccessible(true);
        handleFailedPublicationMethod.invoke(notificationProducer, notification.getId(), "Simulated connection error");
        
        // Verify second publish attempt (the retry)
        verify(rabbitTemplate, times(2)).send(
                eq(documentsExchangeName),
                eq(notificationQueueName),
                any(Message.class),
                any(CorrelationData.class));
    }
    
    /**
     * Tests handling of messages with different processing actions.
     * Verifies that messages are routed to the appropriate processing method based on action.
     */
    @Test
    public void testDifferentProcessingActions() throws Exception {
        // Test UPDATE_EXISTING_APPLICATION action
        testProcessingAction(DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION, "updateExistingApplication");
        
        // Test SUPPORTING_DOCUMENT action
        testProcessingAction(DocumentProcessingMessage.ProcessingAction.SUPPORTING_DOCUMENT, "processSupportingDocument");
    }
    
    /**
     * Helper method to test different processing actions.
     */
    private void testProcessingAction(DocumentProcessingMessage.ProcessingAction action, String methodName) throws Exception {
        // Reset mocks
        reset(processingService);
        
        // Create a message with the specified action
        validMessage.setProcessingAction(action);
        String messageJson = objectMapper.writeValueAsString(validMessage);
        
        MessageProperties props = new MessageProperties();
        props.setContentType(MessageProperties.CONTENT_TYPE_JSON);
        Message rabbitMessage = new Message(messageJson.getBytes(StandardCharsets.UTF_8), props);
        
        // Process the message
        documentProcessingConsumer.processDocumentMessage(rabbitMessage);
        
        // Verify the correct method was called based on the action
        switch (methodName) {
            case "updateExistingApplication":
                verify(processingService, times(1)).updateExistingApplication(any(DocumentProcessingMessage.class));
                break;
            case "processSupportingDocument":
                verify(processingService, times(1)).processSupportingDocument(any(DocumentProcessingMessage.class));
                break;
            default:
                fail("Unknown method name: " + methodName);
        }
    }
    
    /**
     * Helper method to create a test notification message.
     */
    private NotificationMessage createTestNotification() {
        String applicationId = UUID.randomUUID().toString();
        String documentId = UUID.randomUUID().toString();
        
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", applicationId);
        payload.put("documentId", documentId);
        payload.put("status", "PROCESSED");
        payload.put("timestamp", LocalDateTime.now().toString());
        
        List<NotificationMessage.Recipient> recipients = new ArrayList<>();
        recipients.add(new NotificationMessage.Recipient(
                NotificationMessage.Channel.WEBHOOK,
                "https://example.com/webhook",
                "Example Webhook",
                new HashMap<>()));
        
        return NotificationMessage.builder()
                .id(UUID.randomUUID().toString())
                .type(NotificationMessage.Type.STATUS_UPDATE)
                .priority(NotificationMessage.Priority.HIGH)
                .recipients(recipients)
                .payload(payload)
                .build();
    }
}