package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.service.ProcessingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.dao.DataAccessException;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the DocumentProcessingConsumer class.
 * 
 * These tests verify that the RabbitMQ consumer correctly:
 * - Deserializes messages from the document-processing queue
 * - Validates message content
 * - Processes different types of documents
 * - Handles errors appropriately
 * - Interacts with the ProcessingService
 */
@ExtendWith(MockitoExtension.class)
public class RabbitMQConsumerTest {

    @Mock
    private ProcessingService processingService;

    @Mock
    private ObjectMapper objectMapper;

    @Mock
    private RabbitTemplate rabbitTemplate;

    @InjectMocks
    private DocumentProcessingConsumer documentProcessingConsumer;

    private MessageProperties messageProperties;
    private DocumentProcessingMessage validMessage;

    @BeforeEach
    public void setUp() {
        // Set up message properties
        messageProperties = new MessageProperties();
        messageProperties.setReceivedExchange("mca.documents");
        messageProperties.setReceivedRoutingKey("document.processing");
        messageProperties.setHeader("x-retry-count", 0);

        // Set up a valid document processing message
        validMessage = createValidDocumentProcessingMessage();

        // Reset the maxRetryAttempts field using reflection
        try {
            java.lang.reflect.Field field = DocumentProcessingConsumer.class.getDeclaredField("maxRetryAttempts");
            field.setAccessible(true);
            field.set(documentProcessingConsumer, 3);
        } catch (Exception e) {
            fail("Failed to set maxRetryAttempts field: " + e.getMessage());
        }

        // Set exchange and routing key values using reflection
        try {
            java.lang.reflect.Field exchangeField = DocumentProcessingConsumer.class.getDeclaredField("documentsExchange");
            exchangeField.setAccessible(true);
            exchangeField.set(documentProcessingConsumer, "mca.documents");

            java.lang.reflect.Field routingKeyField = DocumentProcessingConsumer.class.getDeclaredField("documentErrorRoutingKey");
            routingKeyField.setAccessible(true);
            routingKeyField.set(documentProcessingConsumer, "document.error");
        } catch (Exception e) {
            fail("Failed to set exchange or routing key fields: " + e.getMessage());
        }
    }

    /**
     * Test successful processing of a new application message.
     */
    @Test
    public void testProcessNewApplicationSuccess() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);
        when(processingService.processNewApplication(any(DocumentProcessingMessage.class))).thenReturn("app123");

        // Act
        documentProcessingConsumer.processDocumentMessage(message);

        // Assert
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(processingService).processNewApplication(validMessage);
        verifyNoMoreInteractions(rabbitTemplate); // No error handling should occur
    }

    /**
     * Test successful processing of an update to an existing application message.
     */
    @Test
    public void testUpdateExistingApplicationSuccess() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION);
        validMessage.setApplicationId("app123");
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);
        when(processingService.updateExistingApplication(any(DocumentProcessingMessage.class))).thenReturn("app123");

        // Act
        documentProcessingConsumer.processDocumentMessage(message);

        // Assert
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(processingService).updateExistingApplication(validMessage);
        verifyNoMoreInteractions(rabbitTemplate); // No error handling should occur
    }

    /**
     * Test successful processing of a supporting document message.
     */
    @Test
    public void testProcessSupportingDocumentSuccess() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.APPEND_TO_APPLICATION);
        validMessage.setApplicationId("app123");
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);
        when(processingService.processSupportingDocument(any(DocumentProcessingMessage.class))).thenReturn("app123");

        // Act
        documentProcessingConsumer.processDocumentMessage(message);

        // Assert
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(processingService).processSupportingDocument(validMessage);
        verifyNoMoreInteractions(rabbitTemplate); // No error handling should occur
    }

    /**
     * Test handling of JSON deserialization errors.
     */
    @Test
    public void testDeserializationError() throws Exception {
        // Arrange
        String invalidJson = "{invalid:json}"; // Invalid JSON
        Message message = new Message(invalidJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class)))
            .thenThrow(new JsonProcessingException("Invalid JSON") {});

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(rabbitTemplate).send(eq("mca.documents"), eq("document.error"), any(Message.class));
    }

    /**
     * Test handling of validation errors (null document ID).
     */
    @Test
    public void testValidationError_NullDocumentId() throws Exception {
        // Arrange
        DocumentProcessingMessage invalidMessage = createValidDocumentProcessingMessage();
        invalidMessage.setDocumentId(null); // Invalid: null document ID
        
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(invalidMessage);

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(rabbitTemplate).send(eq("mca.documents"), eq("document.error"), any(Message.class));
    }

    /**
     * Test handling of validation errors (null document type).
     */
    @Test
    public void testValidationError_NullDocumentType() throws Exception {
        // Arrange
        DocumentProcessingMessage invalidMessage = createValidDocumentProcessingMessage();
        invalidMessage.setDocumentType(null); // Invalid: null document type
        
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(invalidMessage);

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(rabbitTemplate).send(eq("mca.documents"), eq("document.error"), any(Message.class));
    }

    /**
     * Test handling of database errors with retry logic.
     */
    @Test
    public void testDatabaseError_WithRetry() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);
        when(processingService.processNewApplication(any(DocumentProcessingMessage.class)))
            .thenThrow(new DataAccessException("Database error") {});

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(processingService).processNewApplication(validMessage);
        
        // Verify that the message is sent for retry
        ArgumentCaptor<Message> messageCaptor = ArgumentCaptor.forClass(Message.class);
        verify(rabbitTemplate).send(
            eq(messageProperties.getReceivedExchange()),
            eq(messageProperties.getReceivedRoutingKey()),
            messageCaptor.capture()
        );
        
        // Verify retry count is incremented
        Message retryMessage = messageCaptor.getValue();
        assertEquals(1, retryMessage.getMessageProperties().getHeaders().get("x-retry-count"));
        assertEquals("DATABASE_ERROR", retryMessage.getMessageProperties().getHeaders().get("x-error-type"));
    }

    /**
     * Test handling of database errors after max retries.
     */
    @Test
    public void testDatabaseError_AfterMaxRetries() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        
        // Set retry count to max
        messageProperties.setHeader("x-retry-count", 3); // Max retries
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);
        when(processingService.processNewApplication(any(DocumentProcessingMessage.class)))
            .thenThrow(new DataAccessException("Database error") {});

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(processingService).processNewApplication(validMessage);
        
        // Verify that the message is sent to the error queue instead of retrying
        verify(rabbitTemplate).send(eq("mca.documents"), eq("document.error"), any(Message.class));
    }

    /**
     * Test handling of general processing errors.
     */
    @Test
    public void testGeneralProcessingError() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);
        when(processingService.processNewApplication(any(DocumentProcessingMessage.class)))
            .thenThrow(new RuntimeException("Unexpected error"));

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(processingService).processNewApplication(validMessage);
        
        // Verify that the message is sent for retry
        ArgumentCaptor<Message> messageCaptor = ArgumentCaptor.forClass(Message.class);
        verify(rabbitTemplate).send(
            eq(messageProperties.getReceivedExchange()),
            eq(messageProperties.getReceivedRoutingKey()),
            messageCaptor.capture()
        );
        
        // Verify retry count is incremented
        Message retryMessage = messageCaptor.getValue();
        assertEquals(1, retryMessage.getMessageProperties().getHeaders().get("x-retry-count"));
        assertEquals("PROCESSING_ERROR", retryMessage.getMessageProperties().getHeaders().get("x-error-type"));
    }

    /**
     * Test handling of unknown processing action.
     */
    @Test
    public void testUnknownProcessingAction() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.VERIFICATION_ONLY);
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        
        // Verify that the message is sent to the error queue
        verify(rabbitTemplate).send(eq("mca.documents"), eq("document.error"), any(Message.class));
    }

    /**
     * Test handling of empty extracted data.
     */
    @Test
    public void testEmptyExtractedData() throws Exception {
        // Arrange
        DocumentProcessingMessage invalidMessage = createValidDocumentProcessingMessage();
        invalidMessage.setExtractedFields(new HashMap<>()); // Invalid: empty extracted data
        
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(invalidMessage);

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(rabbitTemplate).send(eq("mca.documents"), eq("document.error"), any(Message.class));
    }

    /**
     * Test handling of missing application ID for update operation.
     */
    @Test
    public void testMissingApplicationIdForUpdate() throws Exception {
        // Arrange
        DocumentProcessingMessage invalidMessage = createValidDocumentProcessingMessage();
        invalidMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION);
        invalidMessage.setApplicationId(null); // Invalid: missing application ID for update
        
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(invalidMessage);

        // Act & Assert
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.processDocumentMessage(message);
        });
        
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(rabbitTemplate).send(eq("mca.documents"), eq("document.error"), any(Message.class));
    }

    /**
     * Test idempotent processing (duplicate message handling).
     */
    @Test
    public void testIdempotentProcessing() throws Exception {
        // Arrange
        validMessage.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        validMessage.setId("msg123"); // Set a specific message ID for duplicate detection
        String messageJson = "{\"valid\":\"json\"}"; // Simplified for test
        Message message = new Message(messageJson.getBytes(StandardCharsets.UTF_8), messageProperties);
        
        // Add a message ID header to simulate a duplicate message
        messageProperties.setHeader("x-message-id", "msg123");
        
        when(objectMapper.readValue(anyString(), eq(DocumentProcessingMessage.class))).thenReturn(validMessage);
        when(processingService.processNewApplication(any(DocumentProcessingMessage.class))).thenReturn("app123");

        // Act
        documentProcessingConsumer.processDocumentMessage(message);

        // Assert
        verify(objectMapper).readValue(anyString(), eq(DocumentProcessingMessage.class));
        verify(processingService).processNewApplication(validMessage);
        verifyNoMoreInteractions(rabbitTemplate); // No error handling should occur
    }

    /**
     * Helper method to create a valid document processing message for testing.
     */
    private DocumentProcessingMessage createValidDocumentProcessingMessage() {
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setId("msg123");
        message.setDocumentId("doc123");
        message.setDocumentType(DocumentProcessingMessage.DocumentType.APPLICATION_FORM);
        message.setClassification("application_form");
        message.setClassificationConfidence(95.0);
        message.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        message.setTimestamp(LocalDateTime.now());
        message.setStoragePath("s3://mca-documents/doc123.pdf");
        
        // Add extracted fields
        Map<String, DocumentProcessingMessage.ExtractedField> extractedFields = new HashMap<>();
        extractedFields.put("legal_name", new DocumentProcessingMessage.ExtractedField("ABC Company", 98.5));
        extractedFields.put("dba_name", new DocumentProcessingMessage.ExtractedField("ABC Business", 97.2));
        extractedFields.put("ein", new DocumentProcessingMessage.ExtractedField("12-3456789", 99.0));
        extractedFields.put("address_line1", new DocumentProcessingMessage.ExtractedField("123 Main St", 95.5));
        extractedFields.put("city", new DocumentProcessingMessage.ExtractedField("New York", 96.8));
        extractedFields.put("state", new DocumentProcessingMessage.ExtractedField("NY", 99.5));
        extractedFields.put("zip_code", new DocumentProcessingMessage.ExtractedField("10001", 98.0));
        extractedFields.put("industry", new DocumentProcessingMessage.ExtractedField("Retail", 90.5));
        extractedFields.put("annual_revenue", new DocumentProcessingMessage.ExtractedField("1500000", 85.0));
        message.setExtractedFields(extractedFields);
        
        // Add metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("email_subject", "Application for Funding");
        metadata.put("email_sender", "applicant@example.com");
        message.setMetadata(metadata);
        
        // Add processing metadata
        DocumentProcessingMessage.ProcessingMetadata processingMetadata = new DocumentProcessingMessage.ProcessingMetadata();
        processingMetadata.setProcessingTimeMs(1250L);
        processingMetadata.setOcrEngine("TesseractOCR");
        processingMetadata.setOcrEngineVersion("5.0.1");
        processingMetadata.setClassificationModel("DocumentClassifier");
        processingMetadata.setClassificationModelVersion("2.1.0");
        processingMetadata.setProcessingNode("ocr-service-pod-1");
        processingMetadata.setRetryCount(0);
        message.setProcessingMetadata(processingMetadata);
        
        return message;
    }
}