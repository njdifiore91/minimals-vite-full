package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.service.ProcessingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;

/**
 * RabbitMQ consumer class that listens for document processing messages from the data.processing queue.
 * It deserializes incoming messages, validates their content, and delegates processing to the appropriate service.
 * This class implements error handling, retry logic, and dead-letter queue routing for failed messages.
 */
@Component
public class DocumentProcessingConsumer {

    private static final Logger logger = LoggerFactory.getLogger(DocumentProcessingConsumer.class);

    private final ProcessingService processingService;
    private final ObjectMapper objectMapper;
    private final RabbitTemplate rabbitTemplate;

    @Value("${rabbitmq.exchange.documents}")
    private String documentsExchange;

    @Value("${rabbitmq.routing-key.document.error}")
    private String documentErrorRoutingKey;

    @Value("${rabbitmq.max-retry-attempts}")
    private int maxRetryAttempts;

    /**
     * Constructor for DocumentProcessingConsumer.
     *
     * @param processingService Service for processing document data
     * @param objectMapper     JSON object mapper for message serialization/deserialization
     * @param rabbitTemplate   RabbitMQ template for message operations
     */
    @Autowired
    public DocumentProcessingConsumer(ProcessingService processingService, 
                                     ObjectMapper objectMapper,
                                     RabbitTemplate rabbitTemplate) {
        this.processingService = processingService;
        this.objectMapper = objectMapper;
        this.rabbitTemplate = rabbitTemplate;
    }

    /**
     * Processes document processing messages from the data.processing queue.
     * This method deserializes the message, validates its content, and delegates processing to the ProcessingService.
     * It implements error handling with retry and dead-letter queue routing for failed messages.
     *
     * @param message The RabbitMQ message containing document processing data
     */
    @RabbitListener(queues = "${rabbitmq.queue.data.processing}")
    @Transactional
    public void processDocumentMessage(Message message) {
        String messageBody = new String(message.getBody(), StandardCharsets.UTF_8);
        logger.info("Received document processing message: {}", messageBody);

        try {
            // Extract retry count from message headers
            Integer retryCount = (Integer) message.getMessageProperties().getHeaders().getOrDefault("x-retry-count", 0);
            
            // Deserialize message
            DocumentProcessingMessage processingMessage = deserializeMessage(messageBody);
            
            // Validate message content
            validateMessage(processingMessage);
            
            // Process the document data based on processing type
            processDocumentData(processingMessage);
            
            logger.info("Successfully processed document message with ID: {}", processingMessage.getDocumentId());
        } catch (JsonProcessingException e) {
            // Handle deserialization errors
            logger.error("Failed to deserialize document processing message: {}", e.getMessage());
            handleMessageError(message, e, "DESERIALIZATION_ERROR");
        } catch (IllegalArgumentException e) {
            // Handle validation errors
            logger.error("Invalid document processing message: {}", e.getMessage());
            handleMessageError(message, e, "VALIDATION_ERROR");
        } catch (DataAccessException e) {
            // Handle database errors
            logger.error("Database error while processing document message: {}", e.getMessage());
            handleMessageError(message, e, "DATABASE_ERROR");
        } catch (Exception e) {
            // Handle other unexpected errors
            logger.error("Unexpected error while processing document message: {}", e.getMessage(), e);
            handleMessageError(message, e, "PROCESSING_ERROR");
        }
    }

    /**
     * Deserializes the message body into a DocumentProcessingMessage object.
     *
     * @param messageBody The message body as a string
     * @return The deserialized DocumentProcessingMessage
     * @throws JsonProcessingException If deserialization fails
     */
    private DocumentProcessingMessage deserializeMessage(String messageBody) throws JsonProcessingException {
        try {
            return objectMapper.readValue(messageBody, DocumentProcessingMessage.class);
        } catch (JsonProcessingException e) {
            logger.error("Failed to deserialize message: {}", messageBody);
            throw e;
        }
    }

    /**
     * Validates the content of the document processing message.
     *
     * @param message The document processing message to validate
     * @throws IllegalArgumentException If the message is invalid
     */
    private void validateMessage(DocumentProcessingMessage message) {
        if (message == null) {
            throw new IllegalArgumentException("Message cannot be null");
        }
        
        if (message.getDocumentId() == null || message.getDocumentId().isEmpty()) {
            throw new IllegalArgumentException("Document ID is required");
        }
        
        if (message.getDocumentType() == null) {
            throw new IllegalArgumentException("Document type is required");
        }
        
        if (message.getExtractedData() == null || message.getExtractedData().isEmpty()) {
            throw new IllegalArgumentException("Extracted data is required");
        }
        
        logger.debug("Message validation successful for document ID: {}", message.getDocumentId());
    }

    /**
     * Processes the document data based on the processing type.
     *
     * @param message The document processing message containing extracted data
     */
    private void processDocumentData(DocumentProcessingMessage message) {
        logger.debug("Processing document data for document ID: {}, type: {}", 
                message.getDocumentId(), message.getDocumentType());
        
        switch (message.getProcessingType()) {
            case NEW_APPLICATION:
                processingService.processNewApplication(message);
                break;
            case UPDATE_EXISTING:
                processingService.updateExistingApplication(message);
                break;
            case SUPPORTING_DOCUMENT:
                processingService.processSupportingDocument(message);
                break;
            default:
                throw new IllegalArgumentException("Unknown processing type: " + message.getProcessingType());
        }
    }

    /**
     * Handles message processing errors with retry logic and dead-letter queue routing.
     *
     * @param message    The original RabbitMQ message
     * @param exception  The exception that occurred during processing
     * @param errorType  The type of error that occurred
     */
    private void handleMessageError(Message message, Exception exception, String errorType) {
        Integer retryCount = (Integer) message.getMessageProperties().getHeaders().getOrDefault("x-retry-count", 0);
        
        // Check if we should retry or send to dead-letter queue
        if (retryCount < maxRetryAttempts && isRetryableError(errorType)) {
            // Increment retry count and publish for retry
            retryCount++;
            message.getMessageProperties().getHeaders().put("x-retry-count", retryCount);
            message.getMessageProperties().getHeaders().put("x-error-type", errorType);
            message.getMessageProperties().getHeaders().put("x-error-message", exception.getMessage());
            
            // Calculate exponential backoff delay
            long delay = calculateBackoffDelay(retryCount);
            message.getMessageProperties().getHeaders().put("x-delay", delay);
            
            logger.info("Retrying message processing, attempt {} of {}, delay: {} ms", 
                    retryCount, maxRetryAttempts, delay);
            
            // Re-queue the message with the same routing key
            rabbitTemplate.send(message.getMessageProperties().getReceivedExchange(), 
                    message.getMessageProperties().getReceivedRoutingKey(), 
                    message);
        } else {
            // Send to dead-letter queue
            logger.warn("Sending message to dead-letter queue after {} retry attempts or non-retryable error: {}", 
                    retryCount, errorType);
            
            message.getMessageProperties().getHeaders().put("x-error-type", errorType);
            message.getMessageProperties().getHeaders().put("x-error-message", exception.getMessage());
            
            rabbitTemplate.send(documentsExchange, documentErrorRoutingKey, message);
            
            // Reject the message to prevent redelivery
            throw new AmqpRejectAndDontRequeueException("Message processing failed after retries or non-retryable error", 
                    exception);
        }
    }

    /**
     * Determines if an error is retryable based on its type.
     *
     * @param errorType The type of error
     * @return true if the error is retryable, false otherwise
     */
    private boolean isRetryableError(String errorType) {
        // Database errors and processing errors are retryable
        // Deserialization and validation errors are not retryable
        return "DATABASE_ERROR".equals(errorType) || "PROCESSING_ERROR".equals(errorType);
    }

    /**
     * Calculates the backoff delay for retry attempts using exponential backoff.
     *
     * @param retryCount The current retry count
     * @return The delay in milliseconds
     */
    private long calculateBackoffDelay(int retryCount) {
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, etc.
        return (long) (Math.pow(2, retryCount - 1) * 1000);
    }
}