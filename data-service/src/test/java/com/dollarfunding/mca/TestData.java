package com.dollarfunding.mca;

import com.dollarfunding.mca.dto.*;
import com.dollarfunding.mca.entity.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.*;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * Factory class for creating test data objects used across test classes.
 * Provides methods to create instances of entities, DTOs, and other data structures
 * with predefined test values.
 * 
 * This class ensures consistent test data across different test scenarios and reduces
 * duplication in test setup code. Each factory method allows customization of specific
 * fields while providing sensible defaults for others.
 */
public class TestData {

    // ==============================================================================================
    // Entity Factory Methods
    // ==============================================================================================

    /**
     * Creates a test Application entity with default values.
     * 
     * @param customizer Optional consumer to customize the created entity
     * @return A new Application entity instance
     */
    public static Application createApplication(Consumer<Application> customizer) {
        Application application = new Application();
        application.setId(UUID.randomUUID());
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        application.setCreatedAt(LocalDateTime.now(ZoneOffset.UTC));
        application.setUpdatedAt(LocalDateTime.now(ZoneOffset.UTC));
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("emailSubject", "New MCA Application");
        metadata.put("receivedAt", LocalDateTime.now(ZoneOffset.UTC).toString());
        application.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.accept(application);
        }
        
        return application;
    }
    
    /**
     * Creates a test Application entity with default values.
     * 
     * @return A new Application entity instance
     */
    public static Application createApplication() {
        return createApplication(null);
    }
    
    /**
     * Creates a test Document entity with default values.
     * 
     * @param application The associated Application entity
     * @param customizer Optional consumer to customize the created entity
     * @return A new Document entity instance
     */
    public static Document createDocument(Application application, Consumer<Document> customizer) {
        Document document = new Document();
        document.setId(UUID.randomUUID());
        document.setApplication(application);
        document.setType(DocumentType.BANK_STATEMENT);
        document.setStoragePath("mca-documents-staging/" + UUID.randomUUID() + "/bank-statement.pdf");
        document.setClassification("bank_statement");
        document.setUploadedAt(LocalDateTime.now(ZoneOffset.UTC));
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", 1024 * 1024);
        metadata.put("mimeType", "application/pdf");
        metadata.put("pageCount", 3);
        metadata.put("confidenceScore", 0.95);
        metadata.put("extractedFields", Map.of(
            "accountNumber", "*****1234",
            "bankName", "First National Bank",
            "statementDate", "2023-01-15"
        ));
        document.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.accept(document);
        }
        
        return document;
    }
    
    /**
     * Creates a test Document entity with default values.
     * 
     * @param application The associated Application entity
     * @return A new Document entity instance
     */
    public static Document createDocument(Application application) {
        return createDocument(application, null);
    }
    
    /**
     * Creates a test MerchantDetails entity with default values.
     * 
     * @param application The associated Application entity
     * @param customizer Optional consumer to customize the created entity
     * @return A new MerchantDetails entity instance
     */
    public static MerchantDetails createMerchantDetails(Application application, Consumer<MerchantDetails> customizer) {
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setId(UUID.randomUUID());
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Acme Corporation LLC");
        merchantDetails.setDbaName("Acme Business Solutions");
        merchantDetails.setEin("12-3456789");
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main Street");
        address.put("city", "San Francisco");
        address.put("state", "CA");
        address.put("zipCode", "94105");
        address.put("country", "USA");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Retail");
        merchantDetails.setRevenue(new BigDecimal("1250000.00"));
        
        if (customizer != null) {
            customizer.accept(merchantDetails);
        }
        
        return merchantDetails;
    }
    
    /**
     * Creates a test MerchantDetails entity with default values.
     * 
     * @param application The associated Application entity
     * @return A new MerchantDetails entity instance
     */
    public static MerchantDetails createMerchantDetails(Application application) {
        return createMerchantDetails(application, null);
    }
    
    /**
     * Creates a test Webhook entity with default values.
     * 
     * @param customizer Optional consumer to customize the created entity
     * @return A new Webhook entity instance
     */
    public static Webhook createWebhook(Consumer<Webhook> customizer) {
        Webhook webhook = new Webhook();
        webhook.setId(UUID.randomUUID());
        webhook.setEndpointUrl("https://api.example.com/webhooks/mca");
        webhook.setSecretKey("whsec_" + UUID.randomUUID().toString().replace("-", ""));
        webhook.setActive(true);
        webhook.setEventType(EventType.APPLICATION_CREATED);
        webhook.setCreatedAt(LocalDateTime.now(ZoneOffset.UTC));
        webhook.setUpdatedAt(LocalDateTime.now(ZoneOffset.UTC));
        
        if (customizer != null) {
            customizer.accept(webhook);
        }
        
        return webhook;
    }
    
    /**
     * Creates a test Webhook entity with default values.
     * 
     * @return A new Webhook entity instance
     */
    public static Webhook createWebhook() {
        return createWebhook(null);
    }
    
    // ==============================================================================================
    // DTO Factory Methods
    // ==============================================================================================
    
    /**
     * Creates a test ApplicationRequestDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new ApplicationRequestDTO instance
     */
    public static ApplicationRequestDTO createApplicationRequestDTO(Consumer<ApplicationRequestDTO> customizer) {
        ApplicationRequestDTO dto = new ApplicationRequestDTO();
        dto.setStatus(ApplicationStatus.NEW);
        dto.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("emailSubject", "New MCA Application");
        metadata.put("receivedAt", LocalDateTime.now(ZoneOffset.UTC).toString());
        dto.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test ApplicationRequestDTO with default values.
     * 
     * @return A new ApplicationRequestDTO instance
     */
    public static ApplicationRequestDTO createApplicationRequestDTO() {
        return createApplicationRequestDTO(null);
    }
    
    /**
     * Creates a test ApplicationResponseDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new ApplicationResponseDTO instance
     */
    public static ApplicationResponseDTO createApplicationResponseDTO(Consumer<ApplicationResponseDTO> customizer) {
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setStatus(ApplicationStatus.NEW);
        dto.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        dto.setCreatedAt(LocalDateTime.now(ZoneOffset.UTC));
        dto.setUpdatedAt(LocalDateTime.now(ZoneOffset.UTC));
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("emailSubject", "New MCA Application");
        metadata.put("receivedAt", LocalDateTime.now(ZoneOffset.UTC).toString());
        dto.setMetadata(metadata);
        
        // Add merchant details reference
        dto.setMerchantDetailsId(UUID.randomUUID());
        
        // Add document references
        dto.setDocumentIds(List.of(UUID.randomUUID(), UUID.randomUUID()));
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test ApplicationResponseDTO with default values.
     * 
     * @return A new ApplicationResponseDTO instance
     */
    public static ApplicationResponseDTO createApplicationResponseDTO() {
        return createApplicationResponseDTO(null);
    }
    
    /**
     * Creates a test DocumentRequestDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new DocumentRequestDTO instance
     */
    public static DocumentRequestDTO createDocumentRequestDTO(Consumer<DocumentRequestDTO> customizer) {
        DocumentRequestDTO dto = new DocumentRequestDTO();
        dto.setApplicationId(UUID.randomUUID());
        dto.setType(DocumentType.BANK_STATEMENT);
        dto.setClassification("bank_statement");
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", 1024 * 1024);
        metadata.put("mimeType", "application/pdf");
        metadata.put("pageCount", 3);
        metadata.put("confidenceScore", 0.95);
        dto.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test DocumentRequestDTO with default values.
     * 
     * @return A new DocumentRequestDTO instance
     */
    public static DocumentRequestDTO createDocumentRequestDTO() {
        return createDocumentRequestDTO(null);
    }
    
    /**
     * Creates a test DocumentResponseDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new DocumentResponseDTO instance
     */
    public static DocumentResponseDTO createDocumentResponseDTO(Consumer<DocumentResponseDTO> customizer) {
        DocumentResponseDTO dto = new DocumentResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setApplicationId(UUID.randomUUID());
        dto.setType(DocumentType.BANK_STATEMENT);
        dto.setStoragePath("mca-documents-staging/" + UUID.randomUUID() + "/bank-statement.pdf");
        dto.setClassification("bank_statement");
        dto.setUploadedAt(LocalDateTime.now(ZoneOffset.UTC));
        dto.setDownloadUrl("https://storage.example.com/presigned-url/document.pdf?token=abc123");
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", 1024 * 1024);
        metadata.put("mimeType", "application/pdf");
        metadata.put("pageCount", 3);
        metadata.put("confidenceScore", 0.95);
        metadata.put("extractedFields", Map.of(
            "accountNumber", "*****1234",
            "bankName", "First National Bank",
            "statementDate", "2023-01-15"
        ));
        dto.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test DocumentResponseDTO with default values.
     * 
     * @return A new DocumentResponseDTO instance
     */
    public static DocumentResponseDTO createDocumentResponseDTO() {
        return createDocumentResponseDTO(null);
    }
    
    /**
     * Creates a test MerchantDetailsRequestDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new MerchantDetailsRequestDTO instance
     */
    public static MerchantDetailsRequestDTO createMerchantDetailsRequestDTO(Consumer<MerchantDetailsRequestDTO> customizer) {
        MerchantDetailsRequestDTO dto = new MerchantDetailsRequestDTO();
        dto.setLegalName("Acme Corporation LLC");
        dto.setDbaName("Acme Business Solutions");
        dto.setEin("12-3456789");
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main Street");
        address.put("city", "San Francisco");
        address.put("state", "CA");
        address.put("zipCode", "94105");
        address.put("country", "USA");
        dto.setAddress(address);
        
        dto.setIndustry("Retail");
        dto.setRevenue(new BigDecimal("1250000.00"));
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test MerchantDetailsRequestDTO with default values.
     * 
     * @return A new MerchantDetailsRequestDTO instance
     */
    public static MerchantDetailsRequestDTO createMerchantDetailsRequestDTO() {
        return createMerchantDetailsRequestDTO(null);
    }
    
    /**
     * Creates a test MerchantDetailsResponseDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new MerchantDetailsResponseDTO instance
     */
    public static MerchantDetailsResponseDTO createMerchantDetailsResponseDTO(Consumer<MerchantDetailsResponseDTO> customizer) {
        MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setApplicationId(UUID.randomUUID());
        dto.setLegalName("Acme Corporation LLC");
        dto.setDbaName("Acme Business Solutions");
        dto.setEin("12-3456789");
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main Street");
        address.put("city", "San Francisco");
        address.put("state", "CA");
        address.put("zipCode", "94105");
        address.put("country", "USA");
        dto.setAddress(address);
        
        dto.setIndustry("Retail");
        dto.setRevenue(new BigDecimal("1250000.00"));
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test MerchantDetailsResponseDTO with default values.
     * 
     * @return A new MerchantDetailsResponseDTO instance
     */
    public static MerchantDetailsResponseDTO createMerchantDetailsResponseDTO() {
        return createMerchantDetailsResponseDTO(null);
    }
    
    /**
     * Creates a test WebhookRequestDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new WebhookRequestDTO instance
     */
    public static WebhookRequestDTO createWebhookRequestDTO(Consumer<WebhookRequestDTO> customizer) {
        WebhookRequestDTO dto = new WebhookRequestDTO();
        dto.setEndpointUrl("https://api.example.com/webhooks/mca");
        dto.setSecretKey("whsec_" + UUID.randomUUID().toString().replace("-", ""));
        dto.setActive(true);
        dto.setEventType(EventType.APPLICATION_CREATED);
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test WebhookRequestDTO with default values.
     * 
     * @return A new WebhookRequestDTO instance
     */
    public static WebhookRequestDTO createWebhookRequestDTO() {
        return createWebhookRequestDTO(null);
    }
    
    /**
     * Creates a test WebhookResponseDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new WebhookResponseDTO instance
     */
    public static WebhookResponseDTO createWebhookResponseDTO(Consumer<WebhookResponseDTO> customizer) {
        WebhookResponseDTO dto = new WebhookResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setEndpointUrl("https://api.example.com/webhooks/mca");
        dto.setActive(true);
        dto.setEventType(EventType.APPLICATION_CREATED);
        dto.setCreatedAt(LocalDateTime.now(ZoneOffset.UTC));
        dto.setUpdatedAt(LocalDateTime.now(ZoneOffset.UTC));
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test WebhookResponseDTO with default values.
     * 
     * @return A new WebhookResponseDTO instance
     */
    public static WebhookResponseDTO createWebhookResponseDTO() {
        return createWebhookResponseDTO(null);
    }
    
    /**
     * Creates a test WebhookTestResponseDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new WebhookTestResponseDTO instance
     */
    public static WebhookTestResponseDTO createWebhookTestResponseDTO(Consumer<WebhookTestResponseDTO> customizer) {
        WebhookTestResponseDTO dto = new WebhookTestResponseDTO();
        dto.setSuccess(true);
        dto.setDeliveryTimestamp(LocalDateTime.now(ZoneOffset.UTC));
        dto.setResponseCode(200);
        dto.setResponseBody("{\"status\":\"received\",\"message\":\"Webhook received successfully\"}");
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test WebhookTestResponseDTO with default values.
     * 
     * @return A new WebhookTestResponseDTO instance
     */
    public static WebhookTestResponseDTO createWebhookTestResponseDTO() {
        return createWebhookTestResponseDTO(null);
    }
    
    /**
     * Creates a test ApplicationFilterDTO with default values.
     * 
     * @param customizer Optional consumer to customize the created DTO
     * @return A new ApplicationFilterDTO instance
     */
    public static ApplicationFilterDTO createApplicationFilterDTO(Consumer<ApplicationFilterDTO> customizer) {
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setStatus(ApplicationStatus.NEW);
        dto.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        dto.setFromDate(LocalDateTime.now(ZoneOffset.UTC).minusDays(30));
        dto.setToDate(LocalDateTime.now(ZoneOffset.UTC));
        dto.setMerchantName("Acme");
        dto.setPage(0);
        dto.setSize(20);
        dto.setSortBy("createdAt");
        dto.setSortDirection("DESC");
        
        if (customizer != null) {
            customizer.accept(dto);
        }
        
        return dto;
    }
    
    /**
     * Creates a test ApplicationFilterDTO with default values.
     * 
     * @return A new ApplicationFilterDTO instance
     */
    public static ApplicationFilterDTO createApplicationFilterDTO() {
        return createApplicationFilterDTO(null);
    }
    
    // ==============================================================================================
    // Collection Factory Methods
    // ==============================================================================================
    
    /**
     * Creates a list of test Application entities.
     * 
     * @param count Number of entities to create
     * @param customizer Optional consumer to customize each created entity
     * @return List of Application entities
     */
    public static List<Application> createApplications(int count, Consumer<Application> customizer) {
        return IntStream.range(0, count)
                .mapToObj(i -> createApplication(app -> {
                    if (customizer != null) {
                        customizer.accept(app);
                    }
                }))
                .collect(Collectors.toList());
    }
    
    /**
     * Creates a list of test Application entities.
     * 
     * @param count Number of entities to create
     * @return List of Application entities
     */
    public static List<Application> createApplications(int count) {
        return createApplications(count, null);
    }
    
    /**
     * Creates a list of test Document entities for a given application.
     * 
     * @param application The associated Application entity
     * @param count Number of entities to create
     * @param customizer Optional consumer to customize each created entity
     * @return List of Document entities
     */
    public static List<Document> createDocuments(Application application, int count, Consumer<Document> customizer) {
        return IntStream.range(0, count)
                .mapToObj(i -> createDocument(application, doc -> {
                    // Vary document types for more realistic test data
                    DocumentType[] types = DocumentType.values();
                    doc.setType(types[i % types.length]);
                    
                    if (customizer != null) {
                        customizer.accept(doc);
                    }
                }))
                .collect(Collectors.toList());
    }
    
    /**
     * Creates a list of test Document entities for a given application.
     * 
     * @param application The associated Application entity
     * @param count Number of entities to create
     * @return List of Document entities
     */
    public static List<Document> createDocuments(Application application, int count) {
        return createDocuments(application, count, null);
    }
    
    /**
     * Creates a list of test Webhook entities.
     * 
     * @param count Number of entities to create
     * @param customizer Optional consumer to customize each created entity
     * @return List of Webhook entities
     */
    public static List<Webhook> createWebhooks(int count, Consumer<Webhook> customizer) {
        return IntStream.range(0, count)
                .mapToObj(i -> createWebhook(webhook -> {
                    // Vary event types for more realistic test data
                    EventType[] types = EventType.values();
                    webhook.setEventType(types[i % types.length]);
                    
                    if (customizer != null) {
                        customizer.accept(webhook);
                    }
                }))
                .collect(Collectors.toList());
    }
    
    /**
     * Creates a list of test Webhook entities.
     * 
     * @param count Number of entities to create
     * @return List of Webhook entities
     */
    public static List<Webhook> createWebhooks(int count) {
        return createWebhooks(count, null);
    }
    
    /**
     * Creates a complete test application with associated merchant details and documents.
     * 
     * @param documentCount Number of documents to create
     * @param applicationCustomizer Optional consumer to customize the application
     * @param merchantDetailsCustomizer Optional consumer to customize the merchant details
     * @param documentCustomizer Optional consumer to customize each document
     * @return A map containing the created entities
     */
    public static Map<String, Object> createCompleteApplication(
            int documentCount,
            Consumer<Application> applicationCustomizer,
            Consumer<MerchantDetails> merchantDetailsCustomizer,
            Consumer<Document> documentCustomizer) {
        
        Application application = createApplication(applicationCustomizer);
        MerchantDetails merchantDetails = createMerchantDetails(application, merchantDetailsCustomizer);
        List<Document> documents = createDocuments(application, documentCount, documentCustomizer);
        
        Map<String, Object> result = new HashMap<>();
        result.put("application", application);
        result.put("merchantDetails", merchantDetails);
        result.put("documents", documents);
        
        return result;
    }
    
    /**
     * Creates a complete test application with associated merchant details and documents.
     * 
     * @param documentCount Number of documents to create
     * @return A map containing the created entities
     */
    public static Map<String, Object> createCompleteApplication(int documentCount) {
        return createCompleteApplication(documentCount, null, null, null);
    }
    
    /**
     * Creates a list of complete test applications with associated merchant details and documents.
     * 
     * @param applicationCount Number of applications to create
     * @param documentCount Number of documents per application
     * @return A list of maps, each containing a complete application with associated entities
     */
    public static List<Map<String, Object>> createCompleteApplications(int applicationCount, int documentCount) {
        return IntStream.range(0, applicationCount)
                .mapToObj(i -> createCompleteApplication(documentCount))
                .collect(Collectors.toList());
    }
}