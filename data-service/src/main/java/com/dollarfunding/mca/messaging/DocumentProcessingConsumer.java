package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.dto.DocumentProcessingMessage;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.exception.ProcessingException;
import com.dollarfunding.mca.service.ProcessingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * RabbitMQ consumer that listens for document processing messages from the data.processing queue.
 * 
 * This class is responsible for consuming messages containing extracted document data from the OCR Service,
 * validating the message content, and delegating processing to the appropriate service. It implements
 * error handling, retry logic, and dead-letter queue routing for failed messages.
 * 
 * The consumer applies data validation, business rules, and application state management logic
 * to process merchant cash advance applications. It manages transactions across PostgreSQL and Redis,
 * and publishes status updates to RabbitMQ for notification delivery.
 */
@Component
public class DocumentProcessingConsumer {

    private static final Logger log = LoggerFactory.getLogger(DocumentProcessingConsumer.class);
    
    private final ProcessingService processingService;
    private final ObjectMapper objectMapper;
    
    @Value("${application.processing.confidence-threshold:0.75}")
    private double confidenceThreshold;
    
    @Value("${application.processing.max-retries:3}")
    private int maxRetries;
    
    /**
     * Constructor with required dependencies.
     * 
     * @param processingService Service for processing document data
     * @param objectMapper Jackson ObjectMapper for JSON serialization/deserialization
     */
    @Autowired
    public DocumentProcessingConsumer(ProcessingService processingService, ObjectMapper objectMapper) {
        this.processingService = processingService;
        this.objectMapper = objectMapper;
    }
    
    /**
     * Consumes document processing messages from the data.processing queue.
     * 
     * This method is annotated with @RabbitListener to listen for messages on the specified queue.
     * It deserializes the message payload, validates its content, and delegates processing to the
     * appropriate service method based on the message content.
     * 
     * @param payload The message payload as a JSON string
     * @param messageId The RabbitMQ message ID
     * @param retryCount The number of times this message has been retried
     * @throws AmqpRejectAndDontRequeueException if the message should be rejected and not requeued
     */
    @RabbitListener(queues = "${application.messaging.queues.data-processing.name:data.processing}")
    @Transactional
    public void consumeDocumentProcessingMessage(
            @Payload String payload,
            @Header(AmqpHeaders.MESSAGE_ID) String messageId,
            @Header(value = "x-retry-count", defaultValue = "0") int retryCount) {
        
        log.info("Received document processing message with ID: {}, retry count: {}", messageId, retryCount);
        
        try {
            // Deserialize the message payload
            DocumentProcessingMessage message = deserializeMessage(payload);
            
            // Validate the message content
            validateMessage(message);
            
            // Process the document based on the message content
            processDocument(message, retryCount);
            
            log.info("Successfully processed document with ID: {}", message.getDocumentId());
            
        } catch (JsonProcessingException e) {
            // Handle JSON deserialization errors
            log.error("Failed to deserialize document processing message: {}", e.getMessage(), e);
            handleDeserializationError(payload, messageId, retryCount, e);
            
        } catch (IllegalArgumentException e) {
            // Handle validation errors
            log.error("Invalid document processing message: {}", e.getMessage(), e);
            handleValidationError(payload, messageId, retryCount, e);
            
        } catch (ProcessingException e) {
            // Handle processing errors
            log.error("Error processing document: {}", e.getMessage(), e);
            handleProcessingError(payload, messageId, retryCount, e);
            
        } catch (Exception e) {
            // Handle unexpected errors
            log.error("Unexpected error processing document message: {}", e.getMessage(), e);
            handleUnexpectedError(payload, messageId, retryCount, e);
        }
    }
    
    /**
     * Deserializes the message payload into a DocumentProcessingMessage object.
     * 
     * @param payload The message payload as a JSON string
     * @return The deserialized DocumentProcessingMessage
     * @throws JsonProcessingException if the payload cannot be deserialized
     */
    private DocumentProcessingMessage deserializeMessage(String payload) throws JsonProcessingException {
        try {
            return objectMapper.readValue(payload, DocumentProcessingMessage.class);
        } catch (JsonProcessingException e) {
            log.error("Failed to deserialize message payload: {}", payload);
            throw e;
        }
    }
    
    /**
     * Validates the content of a document processing message.
     * 
     * @param message The document processing message to validate
     * @throws IllegalArgumentException if the message is invalid
     */
    private void validateMessage(DocumentProcessingMessage message) {
        if (message == null) {
            throw new IllegalArgumentException("Message cannot be null");
        }
        
        if (!message.isValid()) {
            throw new IllegalArgumentException("Message is missing required fields: " + message);
        }
        
        // Validate document type
        try {
            DocumentType.findByName(message.getDocumentType())
                .orElseThrow(() -> new IllegalArgumentException("Invalid document type: " + message.getDocumentType()));
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid document type: " + message.getDocumentType(), e);
        }
        
        // Validate storage path
        if (message.getStoragePath() == null || !message.getStoragePath().startsWith("s3://")) {
            throw new IllegalArgumentException("Invalid storage path: " + message.getStoragePath());
        }
        
        // Validate extracted data
        if (message.getExtractedData() == null || message.getExtractedData().isEmpty()) {
            throw new IllegalArgumentException("Message contains no extracted data");
        }
        
        log.debug("Message validation successful for document ID: {}", message.getDocumentId());
    }
    
    /**
     * Processes a document based on the message content.
     * 
     * This method delegates processing to the appropriate service method based on the message content.
     * If the message contains an application ID, it updates the existing application with the new document.
     * Otherwise, it processes the document as a new application or associates it with an existing application
     * based on the document content.
     * 
     * @param message The document processing message
     * @param retryCount The number of times this message has been retried
     * @throws ProcessingException if an error occurs during processing
     */
    private void processDocument(DocumentProcessingMessage message, int retryCount) throws ProcessingException {
        UUID documentId = message.getDocumentId();
        UUID applicationId = message.getApplicationId();
        Map<String, Object> extractedData = message.getExtractedData();
        
        // Add metadata about the processing
        Map<String, Object> processingMetadata = new HashMap<>();
        processingMetadata.put("messageId", documentId.toString());
        processingMetadata.put("retryCount", retryCount);
        processingMetadata.put("confidenceScores", message.getConfidenceScores());
        processingMetadata.put("averageConfidence", message.getAverageConfidenceScore());
        processingMetadata.put("processedAt", message.getProcessedAt());
        processingMetadata.put("documentType", message.getDocumentType());
        processingMetadata.put("classification", message.getClassification());
        
        try {
            // Check if this is an update to an existing application
            if (applicationId != null) {
                log.info("Updating existing application {} with document {}", applicationId, documentId);
                processingService.updateApplicationWithDocument(applicationId, documentId, extractedData);
            } else {
                // Process the document, which will either create a new application or associate with an existing one
                log.info("Processing document {} to determine application association", documentId);
                processingService.processDocument(documentId, extractedData);
            }
        } catch (ProcessingException e) {
            // Add context to the exception and rethrow
            log.error("Processing failed for document {}: {}", documentId, e.getMessage());
            
            // Handle the exception with the processing service
            processingService.handleProcessingException(documentId, applicationId, e, processingMetadata);
            
            // Rethrow the exception to trigger retry or dead-letter handling
            throw e;
        }
    }
    
    /**
     * Handles deserialization errors.
     * 
     * @param payload The original message payload
     * @param messageId The RabbitMQ message ID
     * @param retryCount The number of times this message has been retried
     * @param exception The exception that occurred
     * @throws AmqpRejectAndDontRequeueException to reject the message without requeuing
     */
    private void handleDeserializationError(String payload, String messageId, int retryCount, Exception exception) {
        if (retryCount < maxRetries) {
            // Log the error and let the message be requeued for retry
            log.warn("Deserialization failed for message {}, retry {}/{}: {}", 
                    messageId, retryCount, maxRetries, exception.getMessage());
            throw new RuntimeException("Deserialization failed, will retry: " + exception.getMessage(), exception);
        } else {
            // Max retries reached, reject the message
            log.error("Deserialization failed for message {} after {} retries, sending to dead-letter queue", 
                    messageId, retryCount);
            throw new AmqpRejectAndDontRequeueException("Deserialization failed after max retries: " + exception.getMessage(), exception);
        }
    }
    
    /**
     * Handles validation errors.
     * 
     * @param payload The original message payload
     * @param messageId The RabbitMQ message ID
     * @param retryCount The number of times this message has been retried
     * @param exception The exception that occurred
     * @throws AmqpRejectAndDontRequeueException to reject the message without requeuing
     */
    private void handleValidationError(String payload, String messageId, int retryCount, Exception exception) {
        // Validation errors are not retryable, send to dead-letter queue immediately
        log.error("Validation failed for message {}: {}", messageId, exception.getMessage());
        throw new AmqpRejectAndDontRequeueException("Validation failed: " + exception.getMessage(), exception);
    }
    
    /**
     * Handles processing errors.
     * 
     * @param payload The original message payload
     * @param messageId The RabbitMQ message ID
     * @param retryCount The number of times this message has been retried
     * @param exception The exception that occurred
     * @throws AmqpRejectAndDontRequeueException to reject the message without requeuing
     */
    private void handleProcessingError(String payload, String messageId, int retryCount, Exception exception) {
        if (retryCount < maxRetries) {
            // Log the error and let the message be requeued for retry
            log.warn("Processing failed for message {}, retry {}/{}: {}", 
                    messageId, retryCount, maxRetries, exception.getMessage());
            throw new RuntimeException("Processing failed, will retry: " + exception.getMessage(), exception);
        } else {
            // Max retries reached, reject the message
            log.error("Processing failed for message {} after {} retries, sending to dead-letter queue", 
                    messageId, retryCount);
            throw new AmqpRejectAndDontRequeueException("Processing failed after max retries: " + exception.getMessage(), exception);
        }
    }
    
    /**
     * Handles unexpected errors.
     * 
     * @param payload The original message payload
     * @param messageId The RabbitMQ message ID
     * @param retryCount The number of times this message has been retried
     * @param exception The exception that occurred
     * @throws AmqpRejectAndDontRequeueException to reject the message without requeuing
     */
    private void handleUnexpectedError(String payload, String messageId, int retryCount, Exception exception) {
        if (retryCount < maxRetries) {
            // Log the error and let the message be requeued for retry
            log.warn("Unexpected error for message {}, retry {}/{}: {}", 
                    messageId, retryCount, maxRetries, exception.getMessage());
            throw new RuntimeException("Unexpected error, will retry: " + exception.getMessage(), exception);
        } else {
            // Max retries reached, reject the message
            log.error("Unexpected error for message {} after {} retries, sending to dead-letter queue", 
                    messageId, retryCount);
            throw new AmqpRejectAndDontRequeueException("Unexpected error after max retries: " + exception.getMessage(), exception);
        }
    }
}