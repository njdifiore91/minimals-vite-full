package com.dollarfunding.mca;

import com.dollarfunding.mca.dto.*;
import com.dollarfunding.mca.entity.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * Factory class for creating test data objects used across test classes.
 * <p>
 * This class provides methods to create instances of entities, DTOs, and other data structures
 * with predefined test values. It ensures consistent test data across different test scenarios
 * and reduces duplication in test setup code.
 * <p>
 * Each factory method allows customization of specific fields while providing sensible defaults for others.
 */
public class TestData {

    /**
     * Creates a test Application entity with default values.
     *
     * @return a new Application instance with test data
     */
    public static Application createApplication() {
        return createApplication(null);
    }

    /**
     * Creates a test Application entity with customized values.
     *
     * @param customizer a lambda to customize the Application instance
     * @return a new Application instance with test data
     */
    public static Application createApplication(ApplicationCustomizer customizer) {
        Application application = new Application();
        application.setId(UUID.randomUUID());
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        application.setCreatedAt(LocalDateTime.now().minusDays(1));
        application.setUpdatedAt(LocalDateTime.now());
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("priority", "normal");
        metadata.put("automationScore", 85);
        application.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.customize(application);
        }
        
        return application;
    }

    /**
     * Creates a test Document entity with default values.
     *
     * @return a new Document instance with test data
     */
    public static Document createDocument() {
        return createDocument(null);
    }

    /**
     * Creates a test Document entity with customized values.
     *
     * @param customizer a lambda to customize the Document instance
     * @return a new Document instance with test data
     */
    public static Document createDocument(DocumentCustomizer customizer) {
        Document document = new Document();
        document.setId(UUID.randomUUID());
        document.setType(DocumentType.BANK_STATEMENT);
        document.setStoragePath("documents/" + UUID.randomUUID() + "/bank-statement.pdf");
        document.setClassification("bank_statement");
        document.setUploadedAt(LocalDateTime.now());
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", 1024 * 1024);
        metadata.put("mimeType", "application/pdf");
        metadata.put("pages", 3);
        metadata.put("confidenceScore", 0.95);
        document.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.customize(document);
        }
        
        return document;
    }

    /**
     * Creates a test MerchantDetails entity with default values.
     *
     * @return a new MerchantDetails instance with test data
     */
    public static MerchantDetails createMerchantDetails() {
        return createMerchantDetails(null);
    }

    /**
     * Creates a test MerchantDetails entity with customized values.
     *
     * @param customizer a lambda to customize the MerchantDetails instance
     * @return a new MerchantDetails instance with test data
     */
    public static MerchantDetails createMerchantDetails(MerchantDetailsCustomizer customizer) {
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setId(UUID.randomUUID());
        merchantDetails.setLegalName("Acme Corporation");
        merchantDetails.setDbaName("Acme");
        merchantDetails.setEin("12-3456789");
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "New York");
        address.put("state", "NY");
        address.put("zipCode", "10001");
        address.put("country", "USA");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Retail");
        merchantDetails.setRevenue(new BigDecimal("1000000.00"));
        
        if (customizer != null) {
            customizer.customize(merchantDetails);
        }
        
        return merchantDetails;
    }

    /**
     * Creates a test Webhook entity with default values.
     *
     * @return a new Webhook instance with test data
     */
    public static Webhook createWebhook() {
        return createWebhook(null);
    }

    /**
     * Creates a test Webhook entity with customized values.
     *
     * @param customizer a lambda to customize the Webhook instance
     * @return a new Webhook instance with test data
     */
    public static Webhook createWebhook(WebhookCustomizer customizer) {
        Webhook webhook = new Webhook();
        webhook.setId(UUID.randomUUID());
        webhook.setEndpointUrl("https://example.com/webhooks/mca");
        webhook.setSecretKey("test-webhook-secret-key");
        webhook.setActive(true);
        webhook.setEventType(EventType.APPLICATION_CREATED);
        webhook.setCreatedAt(LocalDateTime.now().minusDays(7));
        webhook.setUpdatedAt(LocalDateTime.now());
        
        if (customizer != null) {
            customizer.customize(webhook);
        }
        
        return webhook;
    }

    /**
     * Creates a test ApplicationRequestDTO with default values.
     *
     * @return a new ApplicationRequestDTO instance with test data
     */
    public static ApplicationRequestDTO createApplicationRequestDTO() {
        return createApplicationRequestDTO(null);
    }

    /**
     * Creates a test ApplicationRequestDTO with customized values.
     *
     * @param customizer a lambda to customize the ApplicationRequestDTO instance
     * @return a new ApplicationRequestDTO instance with test data
     */
    public static ApplicationRequestDTO createApplicationRequestDTO(ApplicationRequestDTOCustomizer customizer) {
        ApplicationRequestDTO dto = new ApplicationRequestDTO();
        dto.setStatus(ApplicationStatus.NEW);
        dto.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("priority", "normal");
        metadata.put("automationScore", 85);
        dto.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test ApplicationResponseDTO with default values.
     *
     * @return a new ApplicationResponseDTO instance with test data
     */
    public static ApplicationResponseDTO createApplicationResponseDTO() {
        return createApplicationResponseDTO(null);
    }

    /**
     * Creates a test ApplicationResponseDTO with customized values.
     *
     * @param customizer a lambda to customize the ApplicationResponseDTO instance
     * @return a new ApplicationResponseDTO instance with test data
     */
    public static ApplicationResponseDTO createApplicationResponseDTO(ApplicationResponseDTOCustomizer customizer) {
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setStatus(ApplicationStatus.NEW);
        dto.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        dto.setCreatedAt(LocalDateTime.now().minusDays(1));
        dto.setUpdatedAt(LocalDateTime.now());
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("priority", "normal");
        metadata.put("automationScore", 85);
        dto.setMetadata(metadata);
        
        // Add merchant details reference
        dto.setMerchantDetailsId(UUID.randomUUID());
        
        // Add document references
        List<UUID> documentIds = new ArrayList<>();
        documentIds.add(UUID.randomUUID());
        documentIds.add(UUID.randomUUID());
        dto.setDocumentIds(documentIds);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test DocumentRequestDTO with default values.
     *
     * @return a new DocumentRequestDTO instance with test data
     */
    public static DocumentRequestDTO createDocumentRequestDTO() {
        return createDocumentRequestDTO(null);
    }

    /**
     * Creates a test DocumentRequestDTO with customized values.
     *
     * @param customizer a lambda to customize the DocumentRequestDTO instance
     * @return a new DocumentRequestDTO instance with test data
     */
    public static DocumentRequestDTO createDocumentRequestDTO(DocumentRequestDTOCustomizer customizer) {
        DocumentRequestDTO dto = new DocumentRequestDTO();
        dto.setType(DocumentType.BANK_STATEMENT);
        dto.setApplicationId(UUID.randomUUID());
        dto.setClassification("bank_statement");
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", 1024 * 1024);
        metadata.put("mimeType", "application/pdf");
        metadata.put("pages", 3);
        metadata.put("confidenceScore", 0.95);
        dto.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test DocumentResponseDTO with default values.
     *
     * @return a new DocumentResponseDTO instance with test data
     */
    public static DocumentResponseDTO createDocumentResponseDTO() {
        return createDocumentResponseDTO(null);
    }

    /**
     * Creates a test DocumentResponseDTO with customized values.
     *
     * @param customizer a lambda to customize the DocumentResponseDTO instance
     * @return a new DocumentResponseDTO instance with test data
     */
    public static DocumentResponseDTO createDocumentResponseDTO(DocumentResponseDTOCustomizer customizer) {
        DocumentResponseDTO dto = new DocumentResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setApplicationId(UUID.randomUUID());
        dto.setType(DocumentType.BANK_STATEMENT);
        dto.setStoragePath("documents/" + UUID.randomUUID() + "/bank-statement.pdf");
        dto.setClassification("bank_statement");
        dto.setUploadedAt(LocalDateTime.now());
        dto.setDownloadUrl("https://example-bucket.s3.amazonaws.com/documents/test-document.pdf?signature=abc123");
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", 1024 * 1024);
        metadata.put("mimeType", "application/pdf");
        metadata.put("pages", 3);
        metadata.put("confidenceScore", 0.95);
        dto.setMetadata(metadata);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test MerchantDetailsRequestDTO with default values.
     *
     * @return a new MerchantDetailsRequestDTO instance with test data
     */
    public static MerchantDetailsRequestDTO createMerchantDetailsRequestDTO() {
        return createMerchantDetailsRequestDTO(null);
    }

    /**
     * Creates a test MerchantDetailsRequestDTO with customized values.
     *
     * @param customizer a lambda to customize the MerchantDetailsRequestDTO instance
     * @return a new MerchantDetailsRequestDTO instance with test data
     */
    public static MerchantDetailsRequestDTO createMerchantDetailsRequestDTO(MerchantDetailsRequestDTOCustomizer customizer) {
        MerchantDetailsRequestDTO dto = new MerchantDetailsRequestDTO();
        dto.setLegalName("Acme Corporation");
        dto.setDbaName("Acme");
        dto.setEin("12-3456789");
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "New York");
        address.put("state", "NY");
        address.put("zipCode", "10001");
        address.put("country", "USA");
        dto.setAddress(address);
        
        dto.setIndustry("Retail");
        dto.setRevenue(new BigDecimal("1000000.00"));
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test MerchantDetailsResponseDTO with default values.
     *
     * @return a new MerchantDetailsResponseDTO instance with test data
     */
    public static MerchantDetailsResponseDTO createMerchantDetailsResponseDTO() {
        return createMerchantDetailsResponseDTO(null);
    }

    /**
     * Creates a test MerchantDetailsResponseDTO with customized values.
     *
     * @param customizer a lambda to customize the MerchantDetailsResponseDTO instance
     * @return a new MerchantDetailsResponseDTO instance with test data
     */
    public static MerchantDetailsResponseDTO createMerchantDetailsResponseDTO(MerchantDetailsResponseDTOCustomizer customizer) {
        MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setApplicationId(UUID.randomUUID());
        dto.setLegalName("Acme Corporation");
        dto.setDbaName("Acme");
        dto.setEin("12-3456789");
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "New York");
        address.put("state", "NY");
        address.put("zipCode", "10001");
        address.put("country", "USA");
        dto.setAddress(address);
        
        dto.setIndustry("Retail");
        dto.setRevenue(new BigDecimal("1000000.00"));
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test WebhookRequestDTO with default values.
     *
     * @return a new WebhookRequestDTO instance with test data
     */
    public static WebhookRequestDTO createWebhookRequestDTO() {
        return createWebhookRequestDTO(null);
    }

    /**
     * Creates a test WebhookRequestDTO with customized values.
     *
     * @param customizer a lambda to customize the WebhookRequestDTO instance
     * @return a new WebhookRequestDTO instance with test data
     */
    public static WebhookRequestDTO createWebhookRequestDTO(WebhookRequestDTOCustomizer customizer) {
        WebhookRequestDTO dto = new WebhookRequestDTO();
        dto.setEndpointUrl("https://example.com/webhooks/mca");
        dto.setSecretKey("test-webhook-secret-key");
        dto.setActive(true);
        dto.setEventType(EventType.APPLICATION_CREATED);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test WebhookResponseDTO with default values.
     *
     * @return a new WebhookResponseDTO instance with test data
     */
    public static WebhookResponseDTO createWebhookResponseDTO() {
        return createWebhookResponseDTO(null);
    }

    /**
     * Creates a test WebhookResponseDTO with customized values.
     *
     * @param customizer a lambda to customize the WebhookResponseDTO instance
     * @return a new WebhookResponseDTO instance with test data
     */
    public static WebhookResponseDTO createWebhookResponseDTO(WebhookResponseDTOCustomizer customizer) {
        WebhookResponseDTO dto = new WebhookResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setEndpointUrl("https://example.com/webhooks/mca");
        dto.setMaskedSecretKey("****-****-****-key");
        dto.setActive(true);
        dto.setEventType(EventType.APPLICATION_CREATED);
        dto.setCreatedAt(LocalDateTime.now().minusDays(7));
        dto.setUpdatedAt(LocalDateTime.now());
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test WebhookTestRequestDTO with default values.
     *
     * @return a new WebhookTestRequestDTO instance with test data
     */
    public static WebhookTestRequestDTO createWebhookTestRequestDTO() {
        return createWebhookTestRequestDTO(null);
    }

    /**
     * Creates a test WebhookTestRequestDTO with customized values.
     *
     * @param customizer a lambda to customize the WebhookTestRequestDTO instance
     * @return a new WebhookTestRequestDTO instance with test data
     */
    public static WebhookTestRequestDTO createWebhookTestRequestDTO(WebhookTestRequestDTOCustomizer customizer) {
        WebhookTestRequestDTO dto = new WebhookTestRequestDTO();
        dto.setWebhookId(UUID.randomUUID());
        
        Map<String, Object> payload = new HashMap<>();
        payload.put("event", "test_event");
        payload.put("timestamp", LocalDateTime.now().toString());
        payload.put("data", Map.of("test", true, "message", "Test webhook delivery"));
        dto.setPayload(payload);
        
        dto.setAsync(false);
        dto.setRetry(false);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test WebhookTestResponseDTO with default values.
     *
     * @return a new WebhookTestResponseDTO instance with test data
     */
    public static WebhookTestResponseDTO createWebhookTestResponseDTO() {
        return createWebhookTestResponseDTO(null);
    }

    /**
     * Creates a test WebhookTestResponseDTO with customized values.
     *
     * @param customizer a lambda to customize the WebhookTestResponseDTO instance
     * @return a new WebhookTestResponseDTO instance with test data
     */
    public static WebhookTestResponseDTO createWebhookTestResponseDTO(WebhookTestResponseDTOCustomizer customizer) {
        WebhookTestResponseDTO dto = new WebhookTestResponseDTO();
        dto.setSuccess(true);
        dto.setDeliveryTimestamp(LocalDateTime.now());
        dto.setResponseCode(200);
        dto.setResponseBody("{\"status\":\"received\",\"message\":\"Webhook received successfully\"}");
        dto.setSignatureValid(true);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test ApplicationFilterDTO with default values.
     *
     * @return a new ApplicationFilterDTO instance with test data
     */
    public static ApplicationFilterDTO createApplicationFilterDTO() {
        return createApplicationFilterDTO(null);
    }

    /**
     * Creates a test ApplicationFilterDTO with customized values.
     *
     * @param customizer a lambda to customize the ApplicationFilterDTO instance
     * @return a new ApplicationFilterDTO instance with test data
     */
    public static ApplicationFilterDTO createApplicationFilterDTO(ApplicationFilterDTOCustomizer customizer) {
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setStatus(ApplicationStatus.NEW);
        dto.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        dto.setFromDate(LocalDateTime.now().minusDays(30));
        dto.setToDate(LocalDateTime.now());
        dto.setMerchantName("Acme");
        dto.setPage(0);
        dto.setSize(10);
        dto.setSortBy("createdAt");
        dto.setSortDirection("DESC");
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test PageResponseDTO with default values.
     *
     * @param <T> the type of content in the page
     * @param content the content to include in the page
     * @return a new PageResponseDTO instance with test data
     */
    public static <T> PageResponseDTO<T> createPageResponseDTO(List<T> content) {
        return createPageResponseDTO(content, null);
    }

    /**
     * Creates a test PageResponseDTO with customized values.
     *
     * @param <T> the type of content in the page
     * @param content the content to include in the page
     * @param customizer a lambda to customize the PageResponseDTO instance
     * @return a new PageResponseDTO instance with test data
     */
    public static <T> PageResponseDTO<T> createPageResponseDTO(List<T> content, PageResponseDTOCustomizer<T> customizer) {
        PageResponseDTO<T> dto = new PageResponseDTO<>();
        dto.setContent(content);
        dto.setTotalElements(content.size());
        dto.setTotalPages(1);
        dto.setSize(10);
        dto.setNumber(0);
        dto.setFirst(true);
        dto.setLast(true);
        dto.setEmpty(content.isEmpty());
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a test ErrorResponseDTO with default values.
     *
     * @return a new ErrorResponseDTO instance with test data
     */
    public static ErrorResponseDTO createErrorResponseDTO() {
        return createErrorResponseDTO(null);
    }

    /**
     * Creates a test ErrorResponseDTO with customized values.
     *
     * @param customizer a lambda to customize the ErrorResponseDTO instance
     * @return a new ErrorResponseDTO instance with test data
     */
    public static ErrorResponseDTO createErrorResponseDTO(ErrorResponseDTOCustomizer customizer) {
        ErrorResponseDTO dto = new ErrorResponseDTO();
        dto.setTimestamp(LocalDateTime.now());
        dto.setStatus(400);
        dto.setError("Bad Request");
        dto.setMessage("Validation failed");
        dto.setPath("/api/v1/applications");
        
        Map<String, String> details = new HashMap<>();
        details.put("status", "Status must not be null");
        details.put("metadata", "Metadata must not be empty");
        dto.setDetails(details);
        
        if (customizer != null) {
            customizer.customize(dto);
        }
        
        return dto;
    }

    /**
     * Creates a list of test Application entities.
     *
     * @param count the number of entities to create
     * @return a list of Application entities with test data
     */
    public static List<Application> createApplicationList(int count) {
        return IntStream.range(0, count)
                .mapToObj(i -> createApplication(app -> {
                    app.setId(UUID.randomUUID());
                    app.setCreatedAt(LocalDateTime.now().minusDays(i));
                    app.setStatus(i % 2 == 0 ? ApplicationStatus.NEW : ApplicationStatus.PENDING);
                }))
                .collect(Collectors.toList());
    }

    /**
     * Creates a list of test Document entities.
     *
     * @param count the number of entities to create
     * @param application the application to associate with the documents
     * @return a list of Document entities with test data
     */
    public static List<Document> createDocumentList(int count, Application application) {
        return IntStream.range(0, count)
                .mapToObj(i -> createDocument(doc -> {
                    doc.setId(UUID.randomUUID());
                    doc.setApplication(application);
                    doc.setType(i % 2 == 0 ? DocumentType.BANK_STATEMENT : DocumentType.TAX_RETURN);
                }))
                .collect(Collectors.toList());
    }

    /**
     * Creates a list of test Webhook entities.
     *
     * @param count the number of entities to create
     * @return a list of Webhook entities with test data
     */
    public static List<Webhook> createWebhookList(int count) {
        return IntStream.range(0, count)
                .mapToObj(i -> createWebhook(webhook -> {
                    webhook.setId(UUID.randomUUID());
                    webhook.setEventType(i % 2 == 0 ? EventType.APPLICATION_CREATED : EventType.DOCUMENT_UPLOADED);
                    webhook.setActive(i % 3 != 0); // 2/3 are active
                }))
                .collect(Collectors.toList());
    }

    /**
     * Creates a list of test ApplicationResponseDTO objects.
     *
     * @param count the number of DTOs to create
     * @return a list of ApplicationResponseDTO objects with test data
     */
    public static List<ApplicationResponseDTO> createApplicationResponseDTOList(int count) {
        return IntStream.range(0, count)
                .mapToObj(i -> createApplicationResponseDTO(dto -> {
                    dto.setId(UUID.randomUUID());
                    dto.setCreatedAt(LocalDateTime.now().minusDays(i));
                    dto.setStatus(i % 2 == 0 ? ApplicationStatus.NEW : ApplicationStatus.PENDING);
                }))
                .collect(Collectors.toList());
    }

    /**
     * Creates a list of test DocumentResponseDTO objects.
     *
     * @param count the number of DTOs to create
     * @param applicationId the application ID to associate with the documents
     * @return a list of DocumentResponseDTO objects with test data
     */
    public static List<DocumentResponseDTO> createDocumentResponseDTOList(int count, UUID applicationId) {
        return IntStream.range(0, count)
                .mapToObj(i -> createDocumentResponseDTO(dto -> {
                    dto.setId(UUID.randomUUID());
                    dto.setApplicationId(applicationId);
                    dto.setType(i % 2 == 0 ? DocumentType.BANK_STATEMENT : DocumentType.TAX_RETURN);
                }))
                .collect(Collectors.toList());
    }

    /**
     * Creates a list of test WebhookResponseDTO objects.
     *
     * @param count the number of DTOs to create
     * @return a list of WebhookResponseDTO objects with test data
     */
    public static List<WebhookResponseDTO> createWebhookResponseDTOList(int count) {
        return IntStream.range(0, count)
                .mapToObj(i -> createWebhookResponseDTO(dto -> {
                    dto.setId(UUID.randomUUID());
                    dto.setEventType(i % 2 == 0 ? EventType.APPLICATION_CREATED : EventType.DOCUMENT_UPLOADED);
                    dto.setActive(i % 3 != 0); // 2/3 are active
                }))
                .collect(Collectors.toList());
    }

    // Customizer interfaces for entities
    
    /**
     * Functional interface for customizing Application entities.
     */
    @FunctionalInterface
    public interface ApplicationCustomizer {
        void customize(Application application);
    }

    /**
     * Functional interface for customizing Document entities.
     */
    @FunctionalInterface
    public interface DocumentCustomizer {
        void customize(Document document);
    }

    /**
     * Functional interface for customizing MerchantDetails entities.
     */
    @FunctionalInterface
    public interface MerchantDetailsCustomizer {
        void customize(MerchantDetails merchantDetails);
    }

    /**
     * Functional interface for customizing Webhook entities.
     */
    @FunctionalInterface
    public interface WebhookCustomizer {
        void customize(Webhook webhook);
    }

    // Customizer interfaces for DTOs
    
    /**
     * Functional interface for customizing ApplicationRequestDTO objects.
     */
    @FunctionalInterface
    public interface ApplicationRequestDTOCustomizer {
        void customize(ApplicationRequestDTO dto);
    }

    /**
     * Functional interface for customizing ApplicationResponseDTO objects.
     */
    @FunctionalInterface
    public interface ApplicationResponseDTOCustomizer {
        void customize(ApplicationResponseDTO dto);
    }

    /**
     * Functional interface for customizing DocumentRequestDTO objects.
     */
    @FunctionalInterface
    public interface DocumentRequestDTOCustomizer {
        void customize(DocumentRequestDTO dto);
    }

    /**
     * Functional interface for customizing DocumentResponseDTO objects.
     */
    @FunctionalInterface
    public interface DocumentResponseDTOCustomizer {
        void customize(DocumentResponseDTO dto);
    }

    /**
     * Functional interface for customizing MerchantDetailsRequestDTO objects.
     */
    @FunctionalInterface
    public interface MerchantDetailsRequestDTOCustomizer {
        void customize(MerchantDetailsRequestDTO dto);
    }

    /**
     * Functional interface for customizing MerchantDetailsResponseDTO objects.
     */
    @FunctionalInterface
    public interface MerchantDetailsResponseDTOCustomizer {
        void customize(MerchantDetailsResponseDTO dto);
    }

    /**
     * Functional interface for customizing WebhookRequestDTO objects.
     */
    @FunctionalInterface
    public interface WebhookRequestDTOCustomizer {
        void customize(WebhookRequestDTO dto);
    }

    /**
     * Functional interface for customizing WebhookResponseDTO objects.
     */
    @FunctionalInterface
    public interface WebhookResponseDTOCustomizer {
        void customize(WebhookResponseDTO dto);
    }

    /**
     * Functional interface for customizing WebhookTestRequestDTO objects.
     */
    @FunctionalInterface
    public interface WebhookTestRequestDTOCustomizer {
        void customize(WebhookTestRequestDTO dto);
    }

    /**
     * Functional interface for customizing WebhookTestResponseDTO objects.
     */
    @FunctionalInterface
    public interface WebhookTestResponseDTOCustomizer {
        void customize(WebhookTestResponseDTO dto);
    }

    /**
     * Functional interface for customizing ApplicationFilterDTO objects.
     */
    @FunctionalInterface
    public interface ApplicationFilterDTOCustomizer {
        void customize(ApplicationFilterDTO dto);
    }

    /**
     * Functional interface for customizing ErrorResponseDTO objects.
     */
    @FunctionalInterface
    public interface ErrorResponseDTOCustomizer {
        void customize(ErrorResponseDTO dto);
    }

    /**
     * Functional interface for customizing PageResponseDTO objects.
     *
     * @param <T> the type of content in the page
     */
    @FunctionalInterface
    public interface PageResponseDTOCustomizer<T> {
        void customize(PageResponseDTO<T> dto);
    }
}