package com.dollarfunding.mca.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.messaging.DocumentProcessingConsumer;
import com.dollarfunding.mca.messaging.DocumentProcessingMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.repository.MerchantDetailsRepository;
import com.dollarfunding.mca.service.ApplicationService;
import com.dollarfunding.mca.service.DocumentService;
import com.dollarfunding.mca.service.ProcessingService;
import com.dollarfunding.mca.service.ValidationService;
import com.dollarfunding.mca.util.JsonUtil;

/**
 * Integration test for the end-to-end flow of processing application data from RabbitMQ,
 * applying business rules, storing in PostgreSQL, and publishing notifications.
 * 
 * This test verifies that the complete application processing pipeline works correctly,
 * including data validation, business rule application, and state transitions.
 */
@SpringBootTest
@ActiveProfiles("test")
public class ApplicationProcessingIntegrationTest {

    @Autowired
    private DocumentProcessingConsumer documentProcessingConsumer;
    
    @Autowired
    private ProcessingService processingService;
    
    @SpyBean
    private ApplicationService applicationService;
    
    @SpyBean
    private DocumentService documentService;
    
    @SpyBean
    private ValidationService validationService;
    
    @MockBean
    private NotificationProducer notificationProducer;
    
    @Autowired
    private ApplicationRepository applicationRepository;
    
    @Autowired
    private DocumentRepository documentRepository;
    
    @Autowired
    private MerchantDetailsRepository merchantDetailsRepository;
    
    @Autowired
    private RabbitTemplate rabbitTemplate;
    
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;
    
    @Autowired
    private JsonUtil jsonUtil;
    
    private DocumentProcessingMessage applicationFormMessage;
    private DocumentProcessingMessage bankStatementMessage;
    private DocumentProcessingMessage taxDocumentMessage;
    private DocumentProcessingMessage identityDocumentMessage;
    
    @BeforeEach
    public void setup() throws Exception {
        // Clear any existing test data
        merchantDetailsRepository.deleteAll();
        documentRepository.deleteAll();
        applicationRepository.deleteAll();
        
        // Clear Redis cache
        redisTemplate.getConnectionFactory().getConnection().flushAll();
        
        // Load test messages from JSON files
        applicationFormMessage = jsonUtil.fromJson(
                getClass().getResourceAsStream("/mocks/ocr-application-form.json"),
                DocumentProcessingMessage.class);
        
        bankStatementMessage = jsonUtil.fromJson(
                getClass().getResourceAsStream("/mocks/ocr-bank-statement.json"),
                DocumentProcessingMessage.class);
        
        taxDocumentMessage = jsonUtil.fromJson(
                getClass().getResourceAsStream("/mocks/ocr-tax-document.json"),
                DocumentProcessingMessage.class);
        
        identityDocumentMessage = jsonUtil.fromJson(
                getClass().getResourceAsStream("/mocks/ocr-identity-document.json"),
                DocumentProcessingMessage.class);
    }
    
    /**
     * Tests the complete flow of processing a new application from an application form document.
     * Verifies that the application is created with the correct status, data is persisted in PostgreSQL,
     * and a notification is published to RabbitMQ.
     */
    @Test
    @DisplayName("Should process new application from application form document")
    @Transactional
    public void testProcessNewApplication() throws Exception {
        // Set a unique correlation ID for this test
        String correlationId = UUID.randomUUID().toString();
        applicationFormMessage.setCorrelationId(correlationId);
        
        // Set processing type to NEW_APPLICATION
        applicationFormMessage.setProcessingType("NEW_APPLICATION");
        
        // Create RabbitMQ message properties
        MessageProperties messageProperties = new MessageProperties();
        messageProperties.setCorrelationId(correlationId);
        messageProperties.setContentType("application/json");
        
        // Create RabbitMQ message
        Message message = new Message(
                jsonUtil.toJson(applicationFormMessage).getBytes(),
                messageProperties);
        
        // Process the message
        LocalDateTime startTime = LocalDateTime.now();
        documentProcessingConsumer.onMessage(message);
        
        // Verify that the application was created
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
            List<Application> applications = applicationRepository.findAll();
            assertThat(applications).isNotEmpty();
            
            Application application = applications.get(0);
            assertThat(application.getStatus()).isEqualTo(ApplicationStatus.NEW);
            
            // Verify processing time is under 5 minutes (actually should be much faster in test)
            Duration processingTime = Duration.between(startTime, LocalDateTime.now());
            assertThat(processingTime).isLessThan(Duration.ofMinutes(5));
            
            // Verify that a document was created and associated with the application
            List<Document> documents = documentRepository.findByApplicationId(application.getId());
            assertThat(documents).hasSize(1);
            assertThat(documents.get(0).getType()).isEqualTo(DocumentType.APPLICATION_FORM);
            
            // Verify that a notification was published
            verify(notificationProducer, times(1)).sendApplicationStatusNotification(any());
        });
    }
    
    /**
     * Tests the flow of updating an existing application with a new supporting document (bank statement).
     * Verifies that the document is associated with the application, business rules are applied,
     * and the application status is updated appropriately.
     */
    @Test
    @DisplayName("Should update existing application with supporting document")
    @Transactional
    public void testUpdateExistingApplication() throws Exception {
        // First create a new application
        testProcessNewApplication();
        
        // Get the created application
        Application application = applicationRepository.findAll().get(0);
        Long applicationId = application.getId();
        
        // Set a unique correlation ID for this test
        String correlationId = UUID.randomUUID().toString();
        bankStatementMessage.setCorrelationId(correlationId);
        
        // Set processing type to UPDATE_APPLICATION and link to existing application
        bankStatementMessage.setProcessingType("UPDATE_APPLICATION");
        bankStatementMessage.setApplicationId(applicationId);
        
        // Create RabbitMQ message properties
        MessageProperties messageProperties = new MessageProperties();
        messageProperties.setCorrelationId(correlationId);
        messageProperties.setContentType("application/json");
        
        // Create RabbitMQ message
        Message message = new Message(
                jsonUtil.toJson(bankStatementMessage).getBytes(),
                messageProperties);
        
        // Process the message
        LocalDateTime startTime = LocalDateTime.now();
        documentProcessingConsumer.onMessage(message);
        
        // Verify that the application was updated
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
            Optional<Application> updatedApplication = applicationRepository.findById(applicationId);
            assertThat(updatedApplication).isPresent();
            
            // Application should now be in PENDING status after receiving a supporting document
            assertThat(updatedApplication.get().getStatus()).isEqualTo(ApplicationStatus.PENDING);
            
            // Verify processing time is under 5 minutes
            Duration processingTime = Duration.between(startTime, LocalDateTime.now());
            assertThat(processingTime).isLessThan(Duration.ofMinutes(5));
            
            // Verify that a new document was created and associated with the application
            List<Document> documents = documentRepository.findByApplicationId(applicationId);
            assertThat(documents).hasSize(2); // Now we have 2 documents (application form + bank statement)
            assertThat(documents).anyMatch(doc -> doc.getType().equals(DocumentType.BANK_STATEMENT));
            
            // Verify that a notification was published for the status update
            verify(notificationProducer, times(2)).sendApplicationStatusNotification(any());
        });
    }
    
    /**
     * Tests the complete application flow with all required documents (application form, bank statement,
     * tax document, and identity document). Verifies that the application transitions to COMPLETE status
     * when all required documents are processed and business rules are satisfied.
     */
    @Test
    @DisplayName("Should complete application when all required documents are processed")
    @Transactional
    public void testCompleteApplicationFlow() throws Exception {
        // First create a new application with application form
        testProcessNewApplication();
        
        // Get the created application
        Application application = applicationRepository.findAll().get(0);
        Long applicationId = application.getId();
        
        // Add bank statement document
        processDocument(bankStatementMessage, applicationId, "UPDATE_APPLICATION");
        
        // Add tax document
        processDocument(taxDocumentMessage, applicationId, "UPDATE_APPLICATION");
        
        // Add identity document (should complete the application)
        processDocument(identityDocumentMessage, applicationId, "UPDATE_APPLICATION");
        
        // Verify that the application was completed
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
            Optional<Application> completedApplication = applicationRepository.findById(applicationId);
            assertThat(completedApplication).isPresent();
            
            // Application should now be in COMPLETE status after receiving all required documents
            assertThat(completedApplication.get().getStatus()).isEqualTo(ApplicationStatus.COMPLETE);
            
            // Verify that all documents were created and associated with the application
            List<Document> documents = documentRepository.findByApplicationId(applicationId);
            assertThat(documents).hasSize(4); // Now we have 4 documents
            
            // Verify that merchant details were extracted and stored
            Optional<MerchantDetails> merchantDetails = merchantDetailsRepository.findByApplicationId(applicationId);
            assertThat(merchantDetails).isPresent();
            
            // Verify that notifications were published for each status update
            // 1 for NEW, 1 for PENDING, 1 for each document processed, and 1 for COMPLETE
            verify(notificationProducer, times(6)).sendApplicationStatusNotification(any());
            
            // Verify that the application data is cached in Redis
            String cacheKey = "application:" + applicationId;
            assertThat(redisTemplate.hasKey(cacheKey)).isTrue();
        });
    }
    
    /**
     * Tests the error handling flow when processing a document with validation errors.
     * Verifies that the application is marked with an exception status and appropriate
     * error information is stored.
     */
    @Test
    @DisplayName("Should handle validation errors during document processing")
    @Transactional
    public void testValidationErrorHandling() throws Exception {
        // First create a new application
        testProcessNewApplication();
        
        // Get the created application
        Application application = applicationRepository.findAll().get(0);
        Long applicationId = application.getId();
        
        // Create a bank statement message with validation errors
        DocumentProcessingMessage invalidMessage = bankStatementMessage;
        invalidMessage.setApplicationId(applicationId);
        invalidMessage.setProcessingType("UPDATE_APPLICATION");
        
        // Simulate validation failure
        when(validationService.validateDocumentData(any())).thenReturn(false);
        
        // Process the invalid document
        processDocument(invalidMessage, applicationId, "UPDATE_APPLICATION");
        
        // Verify that the application was marked with exception
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
            Optional<Application> updatedApplication = applicationRepository.findById(applicationId);
            assertThat(updatedApplication).isPresent();
            
            // Application should be in EXCEPTION status due to validation errors
            assertThat(updatedApplication.get().getStatus()).isEqualTo(ApplicationStatus.EXCEPTION);
            
            // Verify that error information is stored in the application metadata
            assertThat(updatedApplication.get().getMetadata()).containsKey("validationErrors");
            
            // Verify that a notification was published for the exception
            verify(notificationProducer, times(2)).sendApplicationStatusNotification(any());
        });
    }
    
    /**
     * Tests the performance of the application processing pipeline to ensure it meets
     * the 5-minute SLA requirement. Also verifies that data extraction maintains 99%
     * accuracy by comparing extracted fields with expected values.
     */
    @Test
    @DisplayName("Should meet performance SLA and data accuracy requirements")
    @Transactional
    public void testPerformanceAndAccuracy() throws Exception {
        // Set a unique correlation ID for this test
        String correlationId = UUID.randomUUID().toString();
        applicationFormMessage.setCorrelationId(correlationId);
        
        // Set processing type to NEW_APPLICATION
        applicationFormMessage.setProcessingType("NEW_APPLICATION");
        
        // Create RabbitMQ message properties
        MessageProperties messageProperties = new MessageProperties();
        messageProperties.setCorrelationId(correlationId);
        messageProperties.setContentType("application/json");
        
        // Create RabbitMQ message
        Message message = new Message(
                jsonUtil.toJson(applicationFormMessage).getBytes(),
                messageProperties);
        
        // Process the message and measure time
        LocalDateTime startTime = LocalDateTime.now();
        documentProcessingConsumer.onMessage(message);
        
        // Verify performance and accuracy
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
            List<Application> applications = applicationRepository.findAll();
            assertThat(applications).isNotEmpty();
            
            Application application = applications.get(0);
            
            // Verify processing time is under 5 minutes
            Duration processingTime = Duration.between(startTime, LocalDateTime.now());
            assertThat(processingTime).isLessThan(Duration.ofMinutes(5));
            
            // Verify data extraction accuracy by comparing extracted fields with expected values
            // from the application form message
            
            // Get merchant details associated with the application
            Optional<MerchantDetails> merchantDetails = merchantDetailsRepository.findByApplicationId(application.getId());
            assertThat(merchantDetails).isPresent();
            
            // Compare extracted fields with expected values from the test message
            MerchantDetails merchant = merchantDetails.get();
            
            // Count correctly extracted fields
            int totalFields = 5; // legal_name, dba_name, ein, address, industry
            int correctFields = 0;
            
            // Check each field against expected values from the test message
            if (merchant.getLegalName().equals(applicationFormMessage.getExtractedData().get("legal_name"))) {
                correctFields++;
            }
            
            if (merchant.getDbaName().equals(applicationFormMessage.getExtractedData().get("dba_name"))) {
                correctFields++;
            }
            
            if (merchant.getEin().equals(applicationFormMessage.getExtractedData().get("ein"))) {
                correctFields++;
            }
            
            // Address is stored as JSON, so we need to check individual components
            if (merchant.getAddress().contains(applicationFormMessage.getExtractedData().get("address_line1")) &&
                merchant.getAddress().contains(applicationFormMessage.getExtractedData().get("city")) &&
                merchant.getAddress().contains(applicationFormMessage.getExtractedData().get("state")) &&
                merchant.getAddress().contains(applicationFormMessage.getExtractedData().get("zip"))) {
                correctFields++;
            }
            
            if (merchant.getIndustry().equals(applicationFormMessage.getExtractedData().get("industry"))) {
                correctFields++;
            }
            
            // Calculate accuracy percentage
            double accuracy = (double) correctFields / totalFields * 100;
            
            // Verify 99% accuracy requirement
            assertThat(accuracy).isGreaterThanOrEqualTo(99.0);
        });
    }
    
    /**
     * Helper method to process a document message for an existing application.
     */
    private void processDocument(DocumentProcessingMessage documentMessage, Long applicationId, String processingType) throws Exception {
        // Set a unique correlation ID
        String correlationId = UUID.randomUUID().toString();
        documentMessage.setCorrelationId(correlationId);
        
        // Set processing type and application ID
        documentMessage.setProcessingType(processingType);
        documentMessage.setApplicationId(applicationId);
        
        // Create RabbitMQ message properties
        MessageProperties messageProperties = new MessageProperties();
        messageProperties.setCorrelationId(correlationId);
        messageProperties.setContentType("application/json");
        
        // Create RabbitMQ message
        Message message = new Message(
                jsonUtil.toJson(documentMessage).getBytes(),
                messageProperties);
        
        // Process the message
        documentProcessingConsumer.onMessage(message);
    }
}