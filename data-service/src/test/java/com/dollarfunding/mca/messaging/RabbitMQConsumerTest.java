package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.dto.DocumentProcessingMessage;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.exception.ProcessingException;
import com.dollarfunding.mca.service.ProcessingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.messaging.support.GenericMessage;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Integration tests for RabbitMQ message consumers in the Data Service.
 * 
 * These tests verify that the service correctly subscribes to relevant queues,
 * deserializes messages, and processes them according to the business logic.
 * It includes tests for successful message consumption, error handling, and
 * idempotency.
 */
@ExtendWith(MockitoExtension.class)
@SpringBootTest
@TestPropertySource(properties = {
    "application.messaging.queues.data-processing.name=data.processing",
    "application.messaging.queues.document-processing.name=document-processing",
    "application.messaging.queues.data-extraction.name=data-extraction",
    "application.processing.confidence-threshold=0.75",
    "application.processing.max-retries=3"
})
public class RabbitMQConsumerTest {

    @Mock
    private ProcessingService processingService;
    
    @Mock
    private ObjectMapper objectMapper;
    
    @Captor
    private ArgumentCaptor<UUID> documentIdCaptor;
    
    @Captor
    private ArgumentCaptor<UUID> applicationIdCaptor;
    
    @Captor
    private ArgumentCaptor<Map<String, Object>> extractedDataCaptor;
    
    private DocumentProcessingConsumer documentProcessingConsumer;
    private MessageConverter messageConverter;
    
    // Test data
    private static final String VALID_MESSAGE_ID = "msg-123";
    private static final UUID DOCUMENT_ID = UUID.randomUUID();
    private static final UUID APPLICATION_ID = UUID.randomUUID();
    private static final String DOCUMENT_TYPE = "LOAN_APPLICATION";
    private static final String STORAGE_PATH = "s3://mca-documents/doc-123.pdf";
    
    @BeforeEach
    void setUp() {
        messageConverter = new Jackson2JsonMessageConverter();
        documentProcessingConsumer = new DocumentProcessingConsumer(processingService, objectMapper);
        
        // Set confidence threshold and max retries using reflection
        ReflectionTestUtils.setField(documentProcessingConsumer, "confidenceThreshold", 0.75);
        ReflectionTestUtils.setField(documentProcessingConsumer, "maxRetries", 3);
    }
    
    /**
     * Creates a valid document processing message for testing.
     * 
     * @return A valid DocumentProcessingMessage object
     */
    private DocumentProcessingMessage createValidMessage() {
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setMessageId(VALID_MESSAGE_ID);
        message.setDocumentId(DOCUMENT_ID.toString());
        message.setDocumentType(DocumentType.LOAN_APPLICATION);
        message.setApplicationId(APPLICATION_ID.toString());
        message.setStoragePath(STORAGE_PATH);
        message.setContentType("application/pdf");
        message.setTimestamp(LocalDateTime.now());
        message.setSourceService("ocr-service");
        message.setStatus("completed");
        
        // Add extracted data
        Map<String, Object> extractionResults = new HashMap<>();
        extractionResults.put("business_name", "Acme Corp");
        extractionResults.put("tax_id", "12-3456789");
        extractionResults.put("requested_amount", 50000.00);
        message.setExtractionResults(extractionResults);
        
        // Add confidence scores
        Map<String, Float> confidenceScores = new HashMap<>();
        confidenceScores.put("business_name", 0.95f);
        confidenceScores.put("tax_id", 0.90f);
        confidenceScores.put("requested_amount", 0.85f);
        message.setConfidenceScores(confidenceScores);
        
        return message;
    }
    
    /**
     * Creates a JSON string representation of a valid message.
     * 
     * @return JSON string of a valid message
     */
    private String createValidMessageJson() {
        return "{"
                + "\"message_id\":\"" + VALID_MESSAGE_ID + "\","
                + "\"document_id\":\"" + DOCUMENT_ID + "\","
                + "\"document_type\":\"LOAN_APPLICATION\","
                + "\"application_id\":\"" + APPLICATION_ID + "\","
                + "\"storage_path\":\"" + STORAGE_PATH + "\","
                + "\"content_type\":\"application/pdf\","
                + "\"timestamp\":\"2023-01-01T12:00:00.000Z\","
                + "\"source_service\":\"ocr-service\","
                + "\"status\":\"completed\","
                + "\"extraction_results\":{"
                + "\"business_name\":\"Acme Corp\","
                + "\"tax_id\":\"12-3456789\","
                + "\"requested_amount\":50000.00"
                + "},"
                + "\"confidence_scores\":{"
                + "\"business_name\":0.95,"
                + "\"tax_id\":0.90,"
                + "\"requested_amount\":0.85"
                + "}"
                + "}";
    }
    
    /**
     * Creates an invalid JSON message with missing required fields.
     * 
     * @return Invalid JSON message string
     */
    private String createInvalidMessageJson() {
        return "{"
                + "\"message_id\":\"" + VALID_MESSAGE_ID + "\","
                + "\"document_type\":\"INVALID_TYPE\","
                + "\"content_type\":\"application/pdf\","
                + "\"timestamp\":\"2023-01-01T12:00:00.000Z\","
                + "\"source_service\":\"ocr-service\","
                + "\"status\":\"completed\""
                + "}";
    }
    
    /**
     * Creates a malformed JSON message that will cause deserialization errors.
     * 
     * @return Malformed JSON message string
     */
    private String createMalformedMessageJson() {
        return "{"
                + "\"message_id\":\"" + VALID_MESSAGE_ID + "\","
                + "\"document_id\":\"" + DOCUMENT_ID + "\","
                + "\"document_type\":LOAN_APPLICATION," // Missing quotes
                + "\"application_id\":\"" + APPLICATION_ID + "\","
                + "\"storage_path\":\"" + STORAGE_PATH + "\","
                + "\"content_type\":\"application/pdf\","
                + "\"timestamp\":\"2023-01-01T12:00:00.000Z\","
                + "\"source_service\":\"ocr-service\","
                + "\"status\":\"completed\""
                + "}";
    }
    
    @Test
    void testConsumeValidMessage() throws Exception {
        // Arrange
        String validMessageJson = createValidMessageJson();
        DocumentProcessingMessage validMessage = createValidMessage();
        
        when(objectMapper.readValue(eq(validMessageJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(validMessage);
        
        // Act
        documentProcessingConsumer.consumeDocumentProcessingMessage(
                validMessageJson, VALID_MESSAGE_ID, 0);
        
        // Assert
        verify(processingService).updateApplicationWithDocument(
                eq(UUID.fromString(validMessage.getApplicationId())),
                eq(UUID.fromString(validMessage.getDocumentId())),
                eq(validMessage.getExtractionResults()));
        
        // Verify no errors were thrown
        verify(processingService, never()).handleProcessingException(
                any(UUID.class), any(UUID.class), any(Exception.class), anyMap());
    }
    
    @Test
    void testConsumeMessageWithoutApplicationId() throws Exception {
        // Arrange
        DocumentProcessingMessage message = createValidMessage();
        message.setApplicationId(null); // No application ID
        String messageJson = createValidMessageJson().replace(
                "\"application_id\":\"" + APPLICATION_ID + "\",", "");
        
        when(objectMapper.readValue(eq(messageJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(message);
        
        // Act
        documentProcessingConsumer.consumeDocumentProcessingMessage(
                messageJson, VALID_MESSAGE_ID, 0);
        
        // Assert
        verify(processingService).processDocument(
                eq(UUID.fromString(message.getDocumentId())),
                eq(message.getExtractionResults()));
        
        // Verify no errors were thrown
        verify(processingService, never()).handleProcessingException(
                any(UUID.class), any(UUID.class), any(Exception.class), anyMap());
    }
    
    @Test
    void testDeserializationError() throws Exception {
        // Arrange
        String malformedJson = createMalformedMessageJson();
        
        when(objectMapper.readValue(eq(malformedJson), eq(DocumentProcessingMessage.class)))
                .thenThrow(new JsonProcessingException("Invalid JSON") {});
        
        // Act & Assert
        // First retry should throw RuntimeException to trigger requeue
        Exception exception = assertThrows(RuntimeException.class, () -> {
            documentProcessingConsumer.consumeDocumentProcessingMessage(
                    malformedJson, VALID_MESSAGE_ID, 0);
        });
        
        assertTrue(exception.getMessage().contains("Deserialization failed"));
        
        // After max retries, should throw AmqpRejectAndDontRequeueException
        exception = assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.consumeDocumentProcessingMessage(
                    malformedJson, VALID_MESSAGE_ID, 3);
        });
        
        assertTrue(exception.getMessage().contains("Deserialization failed after max retries"));
        
        // Verify no processing was attempted
        verify(processingService, never()).processDocument(any(UUID.class), anyMap());
        verify(processingService, never()).updateApplicationWithDocument(
                any(UUID.class), any(UUID.class), anyMap());
    }
    
    @Test
    void testValidationError() throws Exception {
        // Arrange
        String invalidJson = createInvalidMessageJson();
        DocumentProcessingMessage invalidMessage = new DocumentProcessingMessage();
        invalidMessage.setMessageId(VALID_MESSAGE_ID);
        // Missing required fields
        
        when(objectMapper.readValue(eq(invalidJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(invalidMessage);
        
        // Act & Assert
        // Validation errors should immediately go to dead-letter queue
        Exception exception = assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.consumeDocumentProcessingMessage(
                    invalidJson, VALID_MESSAGE_ID, 0);
        });
        
        assertTrue(exception.getMessage().contains("Validation failed"));
        
        // Verify no processing was attempted
        verify(processingService, never()).processDocument(any(UUID.class), anyMap());
        verify(processingService, never()).updateApplicationWithDocument(
                any(UUID.class), any(UUID.class), anyMap());
    }
    
    @Test
    void testProcessingError() throws Exception {
        // Arrange
        String validMessageJson = createValidMessageJson();
        DocumentProcessingMessage validMessage = createValidMessage();
        
        when(objectMapper.readValue(eq(validMessageJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(validMessage);
        
        // Simulate processing error
        doThrow(new ProcessingException("Processing failed"))
                .when(processingService)
                .updateApplicationWithDocument(
                        eq(UUID.fromString(validMessage.getApplicationId())),
                        eq(UUID.fromString(validMessage.getDocumentId())),
                        eq(validMessage.getExtractionResults()));
        
        // Act & Assert
        // First retry should throw RuntimeException to trigger requeue
        Exception exception = assertThrows(RuntimeException.class, () -> {
            documentProcessingConsumer.consumeDocumentProcessingMessage(
                    validMessageJson, VALID_MESSAGE_ID, 0);
        });
        
        assertTrue(exception.getMessage().contains("Processing failed"));
        
        // Verify error was handled
        verify(processingService).handleProcessingException(
                eq(UUID.fromString(validMessage.getDocumentId())),
                eq(UUID.fromString(validMessage.getApplicationId())),
                any(ProcessingException.class),
                anyMap());
        
        // After max retries, should throw AmqpRejectAndDontRequeueException
        exception = assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.consumeDocumentProcessingMessage(
                    validMessageJson, VALID_MESSAGE_ID, 3);
        });
        
        assertTrue(exception.getMessage().contains("Processing failed after max retries"));
    }
    
    @Test
    void testUnexpectedError() throws Exception {
        // Arrange
        String validMessageJson = createValidMessageJson();
        DocumentProcessingMessage validMessage = createValidMessage();
        
        when(objectMapper.readValue(eq(validMessageJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(validMessage);
        
        // Simulate unexpected error
        doThrow(new NullPointerException("Unexpected error"))
                .when(processingService)
                .updateApplicationWithDocument(
                        eq(UUID.fromString(validMessage.getApplicationId())),
                        eq(UUID.fromString(validMessage.getDocumentId())),
                        eq(validMessage.getExtractionResults()));
        
        // Act & Assert
        // First retry should throw RuntimeException to trigger requeue
        Exception exception = assertThrows(RuntimeException.class, () -> {
            documentProcessingConsumer.consumeDocumentProcessingMessage(
                    validMessageJson, VALID_MESSAGE_ID, 0);
        });
        
        assertTrue(exception.getMessage().contains("Unexpected error"));
        
        // After max retries, should throw AmqpRejectAndDontRequeueException
        exception = assertThrows(AmqpRejectAndDontRequeueException.class, () -> {
            documentProcessingConsumer.consumeDocumentProcessingMessage(
                    validMessageJson, VALID_MESSAGE_ID, 3);
        });
        
        assertTrue(exception.getMessage().contains("Unexpected error after max retries"));
    }
    
    @Test
    void testMessageWithLowConfidenceScores() throws Exception {
        // Arrange
        DocumentProcessingMessage message = createValidMessage();
        
        // Set low confidence scores
        Map<String, Float> lowConfidenceScores = new HashMap<>();
        lowConfidenceScores.put("business_name", 0.95f); // Good
        lowConfidenceScores.put("tax_id", 0.60f); // Below threshold
        lowConfidenceScores.put("requested_amount", 0.50f); // Below threshold
        message.setConfidenceScores(lowConfidenceScores);
        
        // Update the message JSON to include low confidence scores
        String messageJson = createValidMessageJson().replace(
                "\"confidence_scores\":{"
                + "\"business_name\":0.95,"
                + "\"tax_id\":0.90,"
                + "\"requested_amount\":0.85"
                + "}",
                "\"confidence_scores\":{"
                + "\"business_name\":0.95,"
                + "\"tax_id\":0.60,"
                + "\"requested_amount\":0.50"
                + "}");
        
        when(objectMapper.readValue(eq(messageJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(message);
        
        // Act
        documentProcessingConsumer.consumeDocumentProcessingMessage(
                messageJson, VALID_MESSAGE_ID, 0);
        
        // Assert
        // Even with low confidence, the message should be processed
        verify(processingService).updateApplicationWithDocument(
                eq(UUID.fromString(message.getApplicationId())),
                eq(UUID.fromString(message.getDocumentId())),
                eq(message.getExtractionResults()));
    }
    
    @Test
    void testMessageRequiringVerification() throws Exception {
        // Arrange
        DocumentProcessingMessage message = createValidMessage();
        message.setRequiresVerification(true);
        message.setVerificationFields(Arrays.asList("tax_id", "requested_amount"));
        
        // Update the message JSON to include verification fields
        String messageJson = createValidMessageJson().replace(
                "}",
                ",\"requires_verification\":true,"
                + "\"verification_fields\":[\"tax_id\",\"requested_amount\"]"
                + "}");
        
        when(objectMapper.readValue(eq(messageJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(message);
        
        // Act
        documentProcessingConsumer.consumeDocumentProcessingMessage(
                messageJson, VALID_MESSAGE_ID, 0);
        
        // Assert
        // Even with verification required, the message should be processed
        verify(processingService).updateApplicationWithDocument(
                eq(UUID.fromString(message.getApplicationId())),
                eq(UUID.fromString(message.getDocumentId())),
                eq(message.getExtractionResults()));
    }
    
    @Test
    void testIdempotentProcessing() throws Exception {
        // Arrange
        String validMessageJson = createValidMessageJson();
        DocumentProcessingMessage validMessage = createValidMessage();
        
        when(objectMapper.readValue(eq(validMessageJson), eq(DocumentProcessingMessage.class)))
                .thenReturn(validMessage);
        
        // Act - Process the same message twice
        documentProcessingConsumer.consumeDocumentProcessingMessage(
                validMessageJson, VALID_MESSAGE_ID, 0);
        documentProcessingConsumer.consumeDocumentProcessingMessage(
                validMessageJson, VALID_MESSAGE_ID, 0);
        
        // Assert - The service should be called twice (no idempotency check in the consumer)
        // In a real implementation, the service layer would handle idempotency
        verify(processingService, times(2)).updateApplicationWithDocument(
                eq(UUID.fromString(validMessage.getApplicationId())),
                eq(UUID.fromString(validMessage.getDocumentId())),
                eq(validMessage.getExtractionResults()));
    }
}