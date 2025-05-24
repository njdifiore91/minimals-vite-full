package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.config.AsyncConfig;
import com.dollarfunding.mca.config.RabbitMQConfig;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.messaging.DocumentProcessingConsumer;
import com.dollarfunding.mca.messaging.DocumentProcessingMessage;
import com.dollarfunding.mca.messaging.NotificationMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.repository.MerchantDetailsRepository;
import com.dollarfunding.mca.service.ApplicationService;
import com.dollarfunding.mca.service.DocumentService;
import com.dollarfunding.mca.service.MerchantService;
import com.dollarfunding.mca.service.ProcessingService;
import com.dollarfunding.mca.service.ValidationService;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Integration test for the complete application processing flow.
 * 
 * This test verifies the end-to-end flow of processing application data from RabbitMQ,
 * applying business rules, storing in PostgreSQL, and publishing notifications.
 */
@SpringBootTest
@ActiveProfiles("test")
@Transactional
public class ApplicationProcessingIntegrationTest {

    @Autowired
    private ProcessingService processingService;
    
    @Autowired
    private ApplicationService applicationService;
    
    @Autowired
    private DocumentService documentService;
    
    @Autowired
    private MerchantService merchantService;
    
    @Autowired
    private ValidationService validationService;
    
    @Autowired
    private ApplicationRepository applicationRepository;
    
    @Autowired
    private DocumentRepository documentRepository;
    
    @Autowired
    private MerchantDetailsRepository merchantDetailsRepository;
    
    @Autowired
    private DocumentProcessingConsumer documentProcessingConsumer;
    
    @MockBean
    private RabbitTemplate rabbitTemplate;
    
    @MockBean
    private RedisTemplate<String, Object> redisTemplate;
    
    @SpyBean
    private NotificationProducer notificationProducer;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    private DocumentProcessingMessage testDocumentMessage;
    private Application testApplication;
    private Document testDocument;
    private MerchantDetails testMerchantDetails;
    
    @BeforeEach
    public void setup() throws IOException {
        // Load test document processing message from JSON file
        String messageJson = new String(
                new ClassPathResource("mocks/rabbitmq-document-message.json")
                        .getInputStream().readAllBytes(),
                StandardCharsets.UTF_8);
        
        // Parse the JSON to get the document message
        Map<String, Object> messageMap = objectMapper.readValue(messageJson, Map.class);
        Map<String, Object> documentMap = (Map<String, Object>) ((Map<String, Object>) messageMap.get("message")).get("document");
        
        // Create test document processing message
        testDocumentMessage = createTestDocumentProcessingMessage(documentMap);
        
        // Create test application
        testApplication = createTestApplication();
        applicationRepository.save(testApplication);
        
        // Create test document
        testDocument = createTestDocument(testApplication);
        documentRepository.save(testDocument);
        
        // Create test merchant details
        testMerchantDetails = createTestMerchantDetails(testApplication);
        merchantDetailsRepository.save(testMerchantDetails);
        
        // Mock S3 document retrieval
        when(documentService.getDocumentContent(anyString())).thenReturn("Test document content".getBytes());
    }
    
    @Test
    @DisplayName("Should process application data from RabbitMQ and update application status")
    public void testApplicationProcessingFlow() throws Exception {
        // Given: A document processing message from RabbitMQ
        Message rabbitMessage = new Message(objectMapper.writeValueAsBytes(testDocumentMessage), null);
        
        // When: The message is consumed and processed
        documentProcessingConsumer.onMessage(rabbitMessage);
        
        // Then: The application should be processed and status updated
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> updatedApp = applicationRepository.findById(testApplication.getId());
            assertThat(updatedApp).isPresent();
            assertThat(updatedApp.get().getStatus()).isEqualTo(ApplicationStatus.PROCESSING);
        });
        
        // Complete the processing flow
        processingService.completeApplicationProcessing(testApplication.getId());
        
        // Then: The application should be marked as complete
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> completedApp = applicationRepository.findById(testApplication.getId());
            assertThat(completedApp).isPresent();
            assertThat(completedApp.get().getStatus()).isEqualTo(ApplicationStatus.COMPLETED);
        });
        
        // Verify notification was sent
        ArgumentCaptor<NotificationMessage> notificationCaptor = ArgumentCaptor.forClass(NotificationMessage.class);
        verify(notificationProducer, times(2)).sendNotification(notificationCaptor.capture());
        
        List<NotificationMessage> notifications = notificationCaptor.getAllValues();
        assertThat(notifications).hasSize(2);
        assertThat(notifications.get(0).getPayload().get("applicationId")).isEqualTo(testApplication.getId());
        assertThat(notifications.get(1).getPayload().get("applicationId")).isEqualTo(testApplication.getId());
        
        // Verify RabbitMQ message was sent
        verify(rabbitTemplate, times(2)).convertAndSend(
                eq(RabbitMQConfig.NOTIFICATION_EXCHANGE),
                eq(RabbitMQConfig.NOTIFICATION_ROUTING_KEY),
                any(NotificationMessage.class));
    }
    
    @Test
    @DisplayName("Should handle validation errors and set application to exception status")
    public void testApplicationProcessingWithValidationErrors() throws Exception {
        // Given: A document processing message with invalid data
        testDocumentMessage.getExtractedData().put("revenue", "invalid_revenue");
        Message rabbitMessage = new Message(objectMapper.writeValueAsBytes(testDocumentMessage), null);
        
        // When: The message is consumed and processed
        documentProcessingConsumer.onMessage(rabbitMessage);
        
        // Then: The application should be marked as exception
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> updatedApp = applicationRepository.findById(testApplication.getId());
            assertThat(updatedApp).isPresent();
            assertThat(updatedApp.get().getStatus()).isEqualTo(ApplicationStatus.EXCEPTION);
        });
        
        // Verify error notification was sent
        ArgumentCaptor<NotificationMessage> notificationCaptor = ArgumentCaptor.forClass(NotificationMessage.class);
        verify(notificationProducer).sendNotification(notificationCaptor.capture());
        
        NotificationMessage notification = notificationCaptor.getValue();
        assertThat(notification.getPayload().get("applicationId")).isEqualTo(testApplication.getId());
        assertThat(notification.getPayload().get("status")).isEqualTo("EXCEPTION");
        assertThat(notification.getPayload().get("errorType")).isEqualTo("VALIDATION_ERROR");
    }
    
    @Test
    @DisplayName("Should process application within 5 minutes as per requirements")
    public void testApplicationProcessingPerformance() throws Exception {
        // Given: A document processing message from RabbitMQ
        Message rabbitMessage = new Message(objectMapper.writeValueAsBytes(testDocumentMessage), null);
        
        // When: The message is consumed and processed
        long startTime = System.currentTimeMillis();
        documentProcessingConsumer.onMessage(rabbitMessage);
        
        // Then: The application should be processed within 5 minutes
        await().atMost(5, TimeUnit.MINUTES).untilAsserted(() -> {
            Optional<Application> updatedApp = applicationRepository.findById(testApplication.getId());
            assertThat(updatedApp).isPresent();
            assertThat(updatedApp.get().getStatus()).isEqualTo(ApplicationStatus.PROCESSING);
        });
        
        // Complete the processing flow
        processingService.completeApplicationProcessing(testApplication.getId());
        
        // Then: The application should be marked as complete within 5 minutes
        await().atMost(5, TimeUnit.MINUTES).untilAsserted(() -> {
            Optional<Application> completedApp = applicationRepository.findById(testApplication.getId());
            assertThat(completedApp).isPresent();
            assertThat(completedApp.get().getStatus()).isEqualTo(ApplicationStatus.COMPLETED);
        });
        
        long endTime = System.currentTimeMillis();
        Duration processingTime = Duration.ofMillis(endTime - startTime);
        
        // Verify processing time is under 5 minutes
        assertThat(processingTime).isLessThan(Duration.ofMinutes(5));
    }
    
    @Test
    @DisplayName("Should maintain data extraction accuracy above 99%")
    public void testDataExtractionAccuracy() throws Exception {
        // Given: A document processing message with confidence scores
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("legalName", 0.99);
        confidenceScores.put("dbaName", 0.98);
        confidenceScores.put("ein", 0.995);
        confidenceScores.put("address", 0.97);
        confidenceScores.put("industry", 0.99);
        confidenceScores.put("revenue", 0.985);
        testDocumentMessage.setConfidenceScores(confidenceScores);
        
        Message rabbitMessage = new Message(objectMapper.writeValueAsBytes(testDocumentMessage), null);
        
        // When: The message is consumed and processed
        documentProcessingConsumer.onMessage(rabbitMessage);
        
        // Then: The application should be processed with high accuracy
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> updatedApp = applicationRepository.findById(testApplication.getId());
            assertThat(updatedApp).isPresent();
            
            // Calculate overall confidence score
            double avgConfidence = confidenceScores.values().stream()
                    .mapToDouble(Double::doubleValue)
                    .average()
                    .orElse(0.0);
            
            // Verify confidence is above 99%
            assertThat(avgConfidence).isGreaterThanOrEqualTo(0.99);
            
            // Verify application metadata contains accuracy information
            Map<String, Object> metadata = updatedApp.get().getMetadata();
            assertThat(metadata).containsKey("extraction_confidence");
            double extractionConfidence = Double.parseDouble(metadata.get("extraction_confidence").toString());
            assertThat(extractionConfidence).isGreaterThanOrEqualTo(0.99);
        });
    }
    
    @Test
    @DisplayName("Should apply business rules to validate application data")
    public void testBusinessRuleApplication() throws Exception {
        // Given: A document processing message from RabbitMQ
        Message rabbitMessage = new Message(objectMapper.writeValueAsBytes(testDocumentMessage), null);
        
        // When: The message is consumed and processed
        documentProcessingConsumer.onMessage(rabbitMessage);
        
        // Then: Business rules should be applied
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> updatedApp = applicationRepository.findById(testApplication.getId());
            assertThat(updatedApp).isPresent();
            
            // Verify application metadata contains business rule results
            Map<String, Object> metadata = updatedApp.get().getMetadata();
            assertThat(metadata).containsKey("business_rules_applied");
            assertThat(metadata).containsKey("business_rules_passed");
            
            // Verify merchant details were validated
            Optional<MerchantDetails> merchantDetails = merchantDetailsRepository.findByApplicationId(testApplication.getId());
            assertThat(merchantDetails).isPresent();
            
            // Verify document was processed
            List<Document> documents = documentRepository.findByApplicationId(testApplication.getId());
            assertThat(documents).isNotEmpty();
            assertThat(documents.get(0).getMetadata()).containsKey("validation_result");
        });
    }
    
    @Test
    @DisplayName("Should transition application through all required states")
    public void testApplicationStateTransitions() throws Exception {
        // Given: An application in NEW status
        assertThat(testApplication.getStatus()).isEqualTo(ApplicationStatus.NEW);
        
        // When: Processing a document message
        Message rabbitMessage = new Message(objectMapper.writeValueAsBytes(testDocumentMessage), null);
        documentProcessingConsumer.onMessage(rabbitMessage);
        
        // Then: Application should transition to PROCESSING
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> updatedApp = applicationRepository.findById(testApplication.getId());
            assertThat(updatedApp).isPresent();
            assertThat(updatedApp.get().getStatus()).isEqualTo(ApplicationStatus.PROCESSING);
        });
        
        // When: Setting application to PENDING (awaiting more documents)
        processingService.setApplicationPending(testApplication.getId(), "Awaiting additional documents");
        
        // Then: Application should be in PENDING status
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> pendingApp = applicationRepository.findById(testApplication.getId());
            assertThat(pendingApp).isPresent();
            assertThat(pendingApp.get().getStatus()).isEqualTo(ApplicationStatus.PENDING);
        });
        
        // When: Completing the application processing
        processingService.completeApplicationProcessing(testApplication.getId());
        
        // Then: Application should be in COMPLETED status
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            Optional<Application> completedApp = applicationRepository.findById(testApplication.getId());
            assertThat(completedApp).isPresent();
            assertThat(completedApp.get().getStatus()).isEqualTo(ApplicationStatus.COMPLETED);
        });
    }
    
    /**
     * Creates a test document processing message from the provided document map.
     */
    private DocumentProcessingMessage createTestDocumentProcessingMessage(Map<String, Object> documentMap) {
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setDocumentId("DOC-" + UUID.randomUUID().toString());
        message.setApplicationId(testApplication != null ? testApplication.getId() : "APP-" + UUID.randomUUID().toString());
        message.setDocumentType(DocumentType.TAX_RETURN.name());
        message.setStoragePath("app-test/tax_return/doc-test/v1");
        message.setProcessingTimestamp(LocalDateTime.now());
        
        // Extract data from document
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("legalName", "Acme Supplies Inc.");
        extractedData.put("dbaName", "Acme Supplies");
        extractedData.put("ein", "12-3456789");
        extractedData.put("address", "123 Business St, Commerce City, CA 90001");
        extractedData.put("industry", "Retail");
        extractedData.put("revenue", "1250000");
        extractedData.put("taxYear", "2024");
        extractedData.put("netIncome", "350000");
        message.setExtractedData(extractedData);
        
        // Set confidence scores
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("legalName", 0.99);
        confidenceScores.put("dbaName", 0.98);
        confidenceScores.put("ein", 0.995);
        confidenceScores.put("address", 0.97);
        confidenceScores.put("industry", 0.99);
        confidenceScores.put("revenue", 0.985);
        confidenceScores.put("taxYear", 0.99);
        confidenceScores.put("netIncome", 0.98);
        message.setConfidenceScores(confidenceScores);
        
        return message;
    }
    
    /**
     * Creates a test application entity.
     */
    private Application createTestApplication() {
        Application application = new Application();
        application.setId("APP-" + UUID.randomUUID().toString());
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        // Set application metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("funding_amount", 75000.00);
        metadata.put("term_length", 12);
        metadata.put("purpose", "Inventory expansion");
        metadata.put("business_type", "Retail");
        metadata.put("time_in_business", 36);
        metadata.put("monthly_revenue", 45000.00);
        metadata.put("credit_score", 720);
        metadata.put("automation_confidence", 0.95);
        application.setMetadata(metadata);
        
        application.setCreatedAt(LocalDateTime.now());
        application.setUpdatedAt(LocalDateTime.now());
        
        return application;
    }
    
    /**
     * Creates a test document entity associated with the given application.
     */
    private Document createTestDocument(Application application) {
        Document document = new Document();
        document.setId("DOC-" + UUID.randomUUID().toString());
        document.setApplication(application);
        document.setType(DocumentType.TAX_RETURN);
        document.setStoragePath("app-test/tax_return/doc-test/v1");
        document.setClassification("tax_return");
        document.setUploadedAt(LocalDateTime.now());
        
        // Set document metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("filename", "business_tax_return_2024.pdf");
        metadata.put("size", 2458631);
        metadata.put("mime_type", "application/pdf");
        metadata.put("page_count", 12);
        metadata.put("classification_confidence", 0.92);
        document.setMetadata(metadata);
        
        return document;
    }
    
    /**
     * Creates test merchant details associated with the given application.
     */
    private MerchantDetails createTestMerchantDetails(Application application) {
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setId(UUID.randomUUID().toString());
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Acme Supplies Inc.");
        merchantDetails.setDbaName("Acme Supplies");
        merchantDetails.setEin("12-3456789");
        
        // Set address as JSON
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Business St");
        address.put("city", "Commerce City");
        address.put("state", "CA");
        address.put("zip", "90001");
        address.put("country", "USA");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Retail");
        merchantDetails.setRevenue(new BigDecimal("1250000"));
        
        return merchantDetails;
    }
}