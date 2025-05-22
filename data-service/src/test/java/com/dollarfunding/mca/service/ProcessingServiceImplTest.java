package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.BusinessRuleException;
import com.dollarfunding.mca.exception.DocumentProcessingException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.messaging.DocumentProcessingMessage;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.repository.MerchantDetailsRepository;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.MockitoJUnitRunner;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the ProcessingServiceImpl class.
 * 
 * These tests verify the functionality of the ProcessingServiceImpl class, which manages
 * application processing workflows for the MCA application. The tests cover processing of
 * new applications, updates to existing applications, application lifecycle management,
 * processing status tracking, and exception handling.
 * 
 * The tests use Mockito to mock dependencies including ApplicationRepository, DocumentRepository,
 * MerchantDetailsRepository, ValidationService, DocumentService, and NotificationService.
 */
@RunWith(MockitoJUnitRunner.class)
public class ProcessingServiceImplTest {

    @Mock
    private ApplicationRepository applicationRepository;
    
    @Mock
    private DocumentRepository documentRepository;
    
    @Mock
    private MerchantDetailsRepository merchantDetailsRepository;
    
    @Mock
    private ValidationService validationService;
    
    @Mock
    private DocumentService documentService;
    
    @Mock
    private NotificationService notificationService;
    
    @InjectMocks
    private ProcessingServiceImpl processingService;
    
    // Test data
    private DocumentProcessingMessage validApplicationMessage;
    private DocumentProcessingMessage validBankStatementMessage;
    private DocumentProcessingMessage validTaxReturnMessage;
    private DocumentProcessingMessage validIdDocumentMessage;
    private DocumentProcessingMessage invalidMessage;
    private Application testApplication;
    private Document testDocument;
    private MerchantDetails testMerchantDetails;
    private String testApplicationId;
    private String testDocumentId;
    
    @Before
    public void setUp() {
        // Initialize test data
        testApplicationId = UUID.randomUUID().toString();
        testDocumentId = UUID.randomUUID().toString();
        
        // Create test application
        testApplication = new Application();
        testApplication.setId(UUID.fromString(testApplicationId));
        testApplication.setStatus(ApplicationStatus.NEW);
        testApplication.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        testApplication.setCreatedAt(LocalDateTime.now());
        testApplication.setUpdatedAt(LocalDateTime.now());
        Map<String, Object> appMetadata = new HashMap<>();
        appMetadata.put("source", "email");
        testApplication.setMetadata(appMetadata);
        
        // Create test document
        testDocument = new Document();
        testDocument.setId(UUID.fromString(testDocumentId));
        testDocument.setApplicationId(UUID.fromString(testApplicationId));
        testDocument.setType(DocumentType.APPLICATION_FORM);
        testDocument.setClassification("Application Form");
        testDocument.setStoragePath("s3://mca-documents-staging/applications/" + testDocumentId + ".pdf");
        testDocument.setUploadedAt(LocalDateTime.now());
        Map<String, Object> docMetadata = new HashMap<>();
        docMetadata.put("pageCount", 3);
        docMetadata.put("fileSize", 1024567);
        testDocument.setMetadata(docMetadata);
        
        // Create test merchant details
        testMerchantDetails = new MerchantDetails();
        testMerchantDetails.setId(UUID.randomUUID().toString());
        testMerchantDetails.setApplication(testApplication);
        testMerchantDetails.setLegalName("Acme Corporation");
        testMerchantDetails.setDbaName("Acme Corp");
        testMerchantDetails.setEin("12-3456789");
        Map<String, String> address = new HashMap<>();
        address.put("line1", "123 Main St");
        address.put("city", "Anytown");
        address.put("state", "CA");
        address.put("zip", "12345");
        testMerchantDetails.setAddress(address);
        testMerchantDetails.setIndustry("Retail");
        testMerchantDetails.setRevenue(1000000.0);
        
        // Create valid application message
        validApplicationMessage = createTestMessage(
                testDocumentId,
                DocumentProcessingMessage.DocumentType.APPLICATION_FORM,
                "Application Form",
                95.0,
                DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION,
                null,
                createTestExtractedFields());
        
        // Create valid bank statement message
        validBankStatementMessage = createTestMessage(
                UUID.randomUUID().toString(),
                DocumentProcessingMessage.DocumentType.BANK_STATEMENT,
                "Bank Statement",
                90.0,
                DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION,
                testApplicationId,
                createBankStatementExtractedFields());
        
        // Create valid tax return message
        validTaxReturnMessage = createTestMessage(
                UUID.randomUUID().toString(),
                DocumentProcessingMessage.DocumentType.TAX_RETURN,
                "Tax Return",
                85.0,
                DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION,
                testApplicationId,
                createTaxReturnExtractedFields());
        
        // Create valid ID document message
        validIdDocumentMessage = createTestMessage(
                UUID.randomUUID().toString(),
                DocumentProcessingMessage.DocumentType.IDENTITY_DOCUMENT,
                "Driver's License",
                92.0,
                DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION,
                testApplicationId,
                createIdDocumentExtractedFields());
        
        // Create invalid message (missing required fields)
        invalidMessage = new DocumentProcessingMessage();
        invalidMessage.setDocumentId(testDocumentId);
        // Missing other required fields
    }
    
    /**
     * Helper method to create a test DocumentProcessingMessage.
     */
    private DocumentProcessingMessage createTestMessage(
            String documentId,
            DocumentProcessingMessage.DocumentType documentType,
            String classification,
            Double classificationConfidence,
            DocumentProcessingMessage.ProcessingAction processingAction,
            String applicationId,
            Map<String, DocumentProcessingMessage.ExtractedField> extractedFields) {
        
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setId(UUID.randomUUID().toString());
        message.setDocumentId(documentId);
        message.setDocumentType(documentType);
        message.setClassification(classification);
        message.setClassificationConfidence(classificationConfidence);
        message.setProcessingAction(processingAction);
        message.setApplicationId(applicationId);
        message.setTimestamp(LocalDateTime.now());
        message.setStoragePath("s3://mca-documents-staging/documents/" + documentId + ".pdf");
        message.setExtractedFields(extractedFields);
        
        DocumentProcessingMessage.ProcessingMetadata metadata = new DocumentProcessingMessage.ProcessingMetadata();
        metadata.setProcessingTimeMs(1234L);
        metadata.setOcrEngine("TesseractOCR");
        metadata.setOcrEngineVersion("5.0.1");
        metadata.setClassificationModel("DocumentClassifier-v2");
        metadata.setClassificationModelVersion("2.1.0");
        metadata.setProcessingNode("ocr-service-pod-1");
        metadata.setRetryCount(0);
        metadata.setProcessingNotes(Arrays.asList("Processed successfully"));
        message.setProcessingMetadata(metadata);
        
        return message;
    }
    
    /**
     * Helper method to create extracted fields for an application form.
     */
    private Map<String, DocumentProcessingMessage.ExtractedField> createTestExtractedFields() {
        Map<String, DocumentProcessingMessage.ExtractedField> fields = new HashMap<>();
        
        fields.put("legal_name", new DocumentProcessingMessage.ExtractedField("Acme Corporation", 95.0));
        fields.put("dba_name", new DocumentProcessingMessage.ExtractedField("Acme Corp", 92.0));
        fields.put("ein", new DocumentProcessingMessage.ExtractedField("12-3456789", 98.0));
        fields.put("address_line1", new DocumentProcessingMessage.ExtractedField("123 Main St", 90.0));
        fields.put("city", new DocumentProcessingMessage.ExtractedField("Anytown", 94.0));
        fields.put("state", new DocumentProcessingMessage.ExtractedField("CA", 99.0));
        fields.put("zip_code", new DocumentProcessingMessage.ExtractedField("12345", 97.0));
        fields.put("industry", new DocumentProcessingMessage.ExtractedField("Retail", 85.0));
        fields.put("annual_revenue", new DocumentProcessingMessage.ExtractedField("1000000", 80.0));
        fields.put("years_in_business", new DocumentProcessingMessage.ExtractedField("5", 90.0));
        fields.put("requested_amount", new DocumentProcessingMessage.ExtractedField("250000", 88.0));
        
        return fields;
    }
    
    /**
     * Helper method to create extracted fields for a bank statement.
     */
    private Map<String, DocumentProcessingMessage.ExtractedField> createBankStatementExtractedFields() {
        Map<String, DocumentProcessingMessage.ExtractedField> fields = new HashMap<>();
        
        fields.put("account_holder", new DocumentProcessingMessage.ExtractedField("Acme Corporation", 92.0));
        fields.put("account_number", new DocumentProcessingMessage.ExtractedField("XXXX1234", 95.0));
        fields.put("bank_name", new DocumentProcessingMessage.ExtractedField("First National Bank", 98.0));
        fields.put("statement_date", new DocumentProcessingMessage.ExtractedField("2023-05-31", 96.0));
        fields.put("opening_balance", new DocumentProcessingMessage.ExtractedField("125000.45", 90.0));
        fields.put("closing_balance", new DocumentProcessingMessage.ExtractedField("142567.89", 91.0));
        fields.put("total_deposits", new DocumentProcessingMessage.ExtractedField("87500.00", 88.0));
        fields.put("total_withdrawals", new DocumentProcessingMessage.ExtractedField("69932.56", 89.0));
        fields.put("average_daily_balance", new DocumentProcessingMessage.ExtractedField("135245.67", 85.0));
        
        return fields;
    }
    
    /**
     * Helper method to create extracted fields for a tax return.
     */
    private Map<String, DocumentProcessingMessage.ExtractedField> createTaxReturnExtractedFields() {
        Map<String, DocumentProcessingMessage.ExtractedField> fields = new HashMap<>();
        
        fields.put("taxpayer_name", new DocumentProcessingMessage.ExtractedField("Acme Corporation", 94.0));
        fields.put("ein", new DocumentProcessingMessage.ExtractedField("12-3456789", 97.0));
        fields.put("tax_year", new DocumentProcessingMessage.ExtractedField("2022", 99.0));
        fields.put("gross_receipts", new DocumentProcessingMessage.ExtractedField("1250000.00", 92.0));
        fields.put("total_income", new DocumentProcessingMessage.ExtractedField("1250000.00", 93.0));
        fields.put("total_deductions", new DocumentProcessingMessage.ExtractedField("850000.00", 91.0));
        fields.put("taxable_income", new DocumentProcessingMessage.ExtractedField("400000.00", 90.0));
        fields.put("total_tax", new DocumentProcessingMessage.ExtractedField("84000.00", 95.0));
        
        return fields;
    }
    
    /**
     * Helper method to create extracted fields for an ID document.
     */
    private Map<String, DocumentProcessingMessage.ExtractedField> createIdDocumentExtractedFields() {
        Map<String, DocumentProcessingMessage.ExtractedField> fields = new HashMap<>();
        
        fields.put("document_type", new DocumentProcessingMessage.ExtractedField("Driver's License", 98.0));
        fields.put("id_number", new DocumentProcessingMessage.ExtractedField("D1234567", 95.0));
        fields.put("full_name", new DocumentProcessingMessage.ExtractedField("John A. Smith", 96.0));
        fields.put("address", new DocumentProcessingMessage.ExtractedField("123 Main St, Anytown, CA 12345", 90.0));
        fields.put("date_of_birth", new DocumentProcessingMessage.ExtractedField("1980-05-15", 94.0));
        fields.put("issue_date", new DocumentProcessingMessage.ExtractedField("2020-06-01", 93.0));
        fields.put("expiration_date", new DocumentProcessingMessage.ExtractedField("2028-06-01", 92.0));
        fields.put("issuing_state", new DocumentProcessingMessage.ExtractedField("CA", 99.0));
        
        return fields;
    }
    
    /**
     * Helper method to set up mocks for processing a new application.
     */
    private void setupMocksForNewApplication() {
        // Mock application repository save
        when(applicationRepository.save(any(Application.class))).thenAnswer(invocation -> {
            Application app = invocation.getArgument(0);
            if (app.getId() == null) {
                app.setId(UUID.fromString(testApplicationId));
            }
            return app;
        });
        
        // Mock document repository save
        when(documentRepository.save(any(Document.class))).thenAnswer(invocation -> {
            Document doc = invocation.getArgument(0);
            if (doc.getId() == null) {
                doc.setId(UUID.fromString(testDocumentId));
            }
            return doc;
        });
        
        // Mock merchant details repository save
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenAnswer(invocation -> {
            MerchantDetails merchant = invocation.getArgument(0);
            if (merchant.getId() == null) {
                merchant.setId(UUID.randomUUID().toString());
            }
            return merchant;
        });
        
        // Mock validation service
        when(validationService.validateApplication(anyString())).thenReturn(true);
        
        // Mock notification service
        when(notificationService.sendApplicationStatusNotification(anyString(), anyString())).thenReturn(true);
    }
    
    /**
     * Helper method to set up mocks for updating an existing application.
     */
    private void setupMocksForExistingApplication() {
        // Mock application repository findById
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.of(testApplication));
        
        // Mock document repository save
        when(documentRepository.save(any(Document.class))).thenAnswer(invocation -> {
            Document doc = invocation.getArgument(0);
            if (doc.getId() == null) {
                doc.setId(UUID.randomUUID());
            }
            return doc;
        });
        
        // Mock merchant details repository findByApplicationId
        when(merchantDetailsRepository.findByApplicationId(any(UUID.class))).thenReturn(Optional.of(testMerchantDetails));
        
        // Mock merchant details repository save
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(testMerchantDetails);
        
        // Mock validation service
        when(validationService.validateApplication(anyString())).thenReturn(true);
        
        // Mock notification service
        when(notificationService.sendApplicationStatusNotification(anyString(), anyString())).thenReturn(true);
    }
    
    /**
     * Helper method to set up mocks for evaluating application completeness.
     */
    private void setupMocksForCompleteness(boolean hasAllDocuments) {
        // Mock application repository findById
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.of(testApplication));
        
        // Create test documents
        List<Document> documents = new ArrayList<>();
        
        // Always add application form
        Document applicationForm = new Document();
        applicationForm.setId(UUID.randomUUID());
        applicationForm.setApplicationId(UUID.fromString(testApplicationId));
        applicationForm.setType(DocumentType.APPLICATION_FORM);
        documents.add(applicationForm);
        
        if (hasAllDocuments) {
            // Add ID verification document
            Document idDocument = new Document();
            idDocument.setId(UUID.randomUUID());
            idDocument.setApplicationId(UUID.fromString(testApplicationId));
            idDocument.setType(DocumentType.ID_VERIFICATION);
            documents.add(idDocument);
            
            // Add bank statement
            Document bankStatement = new Document();
            bankStatement.setId(UUID.randomUUID());
            bankStatement.setApplicationId(UUID.fromString(testApplicationId));
            bankStatement.setType(DocumentType.BANK_STATEMENT);
            documents.add(bankStatement);
            
            // Add tax return
            Document taxReturn = new Document();
            taxReturn.setId(UUID.randomUUID());
            taxReturn.setApplicationId(UUID.fromString(testApplicationId));
            taxReturn.setType(DocumentType.TAX_RETURN);
            documents.add(taxReturn);
            
            // Add business license
            Document businessLicense = new Document();
            businessLicense.setId(UUID.randomUUID());
            businessLicense.setApplicationId(UUID.fromString(testApplicationId));
            businessLicense.setType(DocumentType.BUSINESS_LICENSE);
            documents.add(businessLicense);
        }
        
        // Mock document repository findByApplicationId
        when(documentRepository.findByApplicationId(any(UUID.class))).thenReturn(documents);
        
        // Mock merchant details repository findByApplicationId
        when(merchantDetailsRepository.findByApplicationId(any(UUID.class))).thenReturn(Optional.of(testMerchantDetails));
    }
    
    /*
     * Tests for processing new applications
     */
    
    @Test
    public void testProcessNewApplication_Success() {
        // Setup
        setupMocksForNewApplication();
        
        // Execute
        String applicationId = processingService.processNewApplication(validApplicationMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        assertEquals("Application ID should match test ID", testApplicationId, applicationId);
        
        // Verify application was saved
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository, times(2)).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertEquals("Application status should be PENDING", ApplicationStatus.PENDING, savedApplication.getStatus());
        
        // Verify document was created and saved
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        Document savedDocument = documentCaptor.getValue();
        assertEquals("Document type should match", DocumentType.APPLICATION_FORM, savedDocument.getType());
        assertEquals("Document classification should match", "Application Form", savedDocument.getClassification());
        
        // Verify merchant details were created and saved
        ArgumentCaptor<MerchantDetails> merchantCaptor = ArgumentCaptor.forClass(MerchantDetails.class);
        verify(merchantDetailsRepository).save(merchantCaptor.capture());
        MerchantDetails savedMerchant = merchantCaptor.getValue();
        assertEquals("Merchant legal name should match", "Acme Corporation", savedMerchant.getLegalName());
        
        // Verify validation was performed
        verify(validationService).validateApplication(applicationId);
        
        // Verify notification was sent
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.NEW.name());
    }
    
    @Test(expected = ValidationException.class)
    public void testProcessNewApplication_InvalidMessage() {
        // Execute with invalid message
        processingService.processNewApplication(invalidMessage);
        
        // Should throw ValidationException
    }
    
    @Test(expected = ValidationException.class)
    public void testProcessNewApplication_WrongDocumentType() {
        // Execute with wrong document type
        processingService.processNewApplication(validBankStatementMessage);
        
        // Should throw ValidationException
    }
    
    @Test
    public void testProcessNewApplication_ValidationFailed() {
        // Setup
        setupMocksForNewApplication();
        when(validationService.validateApplication(anyString())).thenReturn(false);
        
        // Execute
        String applicationId = processingService.processNewApplication(validApplicationMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        
        // Verify application status was updated to PENDING
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository, times(2)).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertEquals("Application status should be PENDING", ApplicationStatus.PENDING, savedApplication.getStatus());
        
        // Verify notification was sent
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.NEW.name());
    }
    
    @Test
    public void testProcessNewApplication_WithLowConfidenceFields() {
        // Setup
        setupMocksForNewApplication();
        
        // Modify message to have low confidence fields
        Map<String, DocumentProcessingMessage.ExtractedField> fields = validApplicationMessage.getExtractedFields();
        fields.put("industry", new DocumentProcessingMessage.ExtractedField("Retail", 65.0)); // Below threshold
        fields.put("annual_revenue", new DocumentProcessingMessage.ExtractedField("1000000", 70.0)); // Below threshold
        validApplicationMessage.setExtractedFields(fields);
        
        // Execute
        String applicationId = processingService.processNewApplication(validApplicationMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        
        // Verify application was saved with low confidence fields in metadata
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository, times(2)).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        Map<String, Object> metadata = savedApplication.getMetadata();
        assertTrue("Metadata should contain low_confidence_fields", metadata.containsKey("low_confidence_fields"));
        
        @SuppressWarnings("unchecked")
        Map<String, Object> lowConfidenceFields = (Map<String, Object>) metadata.get("low_confidence_fields");
        assertTrue("Low confidence fields should include industry", lowConfidenceFields.containsKey("industry"));
        assertTrue("Low confidence fields should include annual_revenue", lowConfidenceFields.containsKey("annual_revenue"));
    }
    
    /*
     * Tests for updating existing applications
     */
    
    @Test
    public void testUpdateExistingApplication_Success() {
        // Setup
        setupMocksForExistingApplication();
        
        // Execute
        String applicationId = processingService.updateExistingApplication(validBankStatementMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        assertEquals("Application ID should match test ID", testApplicationId, applicationId);
        
        // Verify application was retrieved and saved
        verify(applicationRepository).findById(UUID.fromString(testApplicationId));
        verify(applicationRepository).save(any(Application.class));
        
        // Verify document was created and saved
        verify(documentRepository).save(any(Document.class));
        
        // Verify merchant details were retrieved and updated
        verify(merchantDetailsRepository).findByApplicationId(UUID.fromString(testApplicationId));
        verify(merchantDetailsRepository).save(any(MerchantDetails.class));
        
        // Verify validation was performed
        verify(validationService).validateApplication(applicationId);
        
        // Verify notification was sent
        verify(notificationService).sendApplicationStatusNotification(eq(applicationId), anyString());
    }
    
    @Test(expected = ValidationException.class)
    public void testUpdateExistingApplication_MissingApplicationId() {
        // Create message without application ID
        DocumentProcessingMessage message = createTestMessage(
                UUID.randomUUID().toString(),
                DocumentProcessingMessage.DocumentType.BANK_STATEMENT,
                "Bank Statement",
                90.0,
                DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION,
                null, // Missing application ID
                createBankStatementExtractedFields());
        
        // Execute
        processingService.updateExistingApplication(message);
        
        // Should throw ValidationException
    }
    
    @Test(expected = ResourceNotFoundException.class)
    public void testUpdateExistingApplication_ApplicationNotFound() {
        // Setup
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.empty());
        
        // Execute
        processingService.updateExistingApplication(validBankStatementMessage);
        
        // Should throw ResourceNotFoundException
    }
    
    @Test
    public void testUpdateExistingApplication_WithLowConfidenceFields() {
        // Setup
        setupMocksForExistingApplication();
        
        // Modify message to have low confidence fields
        Map<String, DocumentProcessingMessage.ExtractedField> fields = validBankStatementMessage.getExtractedFields();
        fields.put("opening_balance", new DocumentProcessingMessage.ExtractedField("125000.45", 65.0)); // Below threshold
        fields.put("closing_balance", new DocumentProcessingMessage.ExtractedField("142567.89", 70.0)); // Below threshold
        validBankStatementMessage.setExtractedFields(fields);
        
        // Execute
        String applicationId = processingService.updateExistingApplication(validBankStatementMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        
        // Verify application was saved with low confidence fields in metadata
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        Map<String, Object> metadata = savedApplication.getMetadata();
        assertTrue("Metadata should contain low_confidence_fields", metadata.containsKey("low_confidence_fields"));
        
        @SuppressWarnings("unchecked")
        Map<String, Object> lowConfidenceFields = (Map<String, Object>) metadata.get("low_confidence_fields");
        assertTrue("Low confidence fields should include opening_balance", lowConfidenceFields.containsKey("opening_balance"));
        assertTrue("Low confidence fields should include closing_balance", lowConfidenceFields.containsKey("closing_balance"));
    }
    
    @Test
    public void testUpdateExistingApplication_StatusChangeToProcessing() {
        // Setup
        setupMocksForExistingApplication();
        when(validationService.validateApplication(anyString())).thenReturn(true);
        
        // Set up for completeness check to return true
        setupMocksForCompleteness(true);
        
        // Execute
        String applicationId = processingService.updateExistingApplication(validBankStatementMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        
        // Verify application status was updated to PROCESSING
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertEquals("Application status should be PROCESSING", ApplicationStatus.PROCESSING, savedApplication.getStatus());
    }
    
    /*
     * Tests for processing supporting documents
     */
    
    @Test
    public void testProcessSupportingDocument_Success() {
        // Setup
        setupMocksForExistingApplication();
        
        // Execute
        String applicationId = processingService.processSupportingDocument(validIdDocumentMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        assertEquals("Application ID should match test ID", testApplicationId, applicationId);
        
        // Verify application was retrieved and saved
        verify(applicationRepository).findById(UUID.fromString(testApplicationId));
        verify(applicationRepository).save(any(Application.class));
        
        // Verify document was created and saved
        verify(documentRepository).save(any(Document.class));
    }
    
    @Test(expected = ValidationException.class)
    public void testProcessSupportingDocument_MissingApplicationId() {
        // Create message without application ID
        DocumentProcessingMessage message = createTestMessage(
                UUID.randomUUID().toString(),
                DocumentProcessingMessage.DocumentType.IDENTITY_DOCUMENT,
                "Driver's License",
                92.0,
                DocumentProcessingMessage.ProcessingAction.UPDATE_EXISTING_APPLICATION,
                null, // Missing application ID
                createIdDocumentExtractedFields());
        
        // Execute
        processingService.processSupportingDocument(message);
        
        // Should throw ValidationException
    }
    
    @Test(expected = ResourceNotFoundException.class)
    public void testProcessSupportingDocument_ApplicationNotFound() {
        // Setup
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.empty());
        
        // Execute
        processingService.processSupportingDocument(validIdDocumentMessage);
        
        // Should throw ResourceNotFoundException
    }
    
    @Test
    public void testProcessSupportingDocument_CompletesApplication() {
        // Setup
        setupMocksForExistingApplication();
        
        // Set application status to PENDING
        testApplication.setStatus(ApplicationStatus.PENDING);
        
        // Set up for completeness check to return true
        setupMocksForCompleteness(true);
        
        // Execute
        String applicationId = processingService.processSupportingDocument(validIdDocumentMessage);
        
        // Verify
        assertNotNull("Application ID should not be null", applicationId);
        
        // Verify application status was updated to PROCESSING
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertEquals("Application status should be PROCESSING", ApplicationStatus.PROCESSING, savedApplication.getStatus());
        
        // Verify notification was sent
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.PROCESSING.name());
    }
    
    /*
     * Tests for evaluating application completeness
     */
    
    @Test
    public void testEvaluateApplicationCompleteness_Complete() {
        // Setup
        setupMocksForCompleteness(true);
        
        // Execute
        boolean isComplete = processingService.evaluateApplicationCompleteness(testApplicationId);
        
        // Verify
        assertTrue("Application should be complete", isComplete);
        
        // Verify application metadata was updated
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        Map<String, Object> metadata = savedApplication.getMetadata();
        assertEquals("Completeness status should be 'complete'", "complete", metadata.get("completeness_status"));
        
        @SuppressWarnings("unchecked")
        Map<String, Boolean> missingDocuments = (Map<String, Boolean>) metadata.get("missing_documents");
        assertFalse("Should not be missing identity document", missingDocuments.get("identity_document"));
        assertFalse("Should not be missing bank statement", missingDocuments.get("bank_statement"));
        assertFalse("Should not be missing tax return", missingDocuments.get("tax_return"));
    }
    
    @Test
    public void testEvaluateApplicationCompleteness_Incomplete() {
        // Setup
        setupMocksForCompleteness(false);
        
        // Execute
        boolean isComplete = processingService.evaluateApplicationCompleteness(testApplicationId);
        
        // Verify
        assertFalse("Application should be incomplete", isComplete);
        
        // Verify application metadata was updated
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        Map<String, Object> metadata = savedApplication.getMetadata();
        assertEquals("Completeness status should be 'incomplete'", "incomplete", metadata.get("completeness_status"));
        
        @SuppressWarnings("unchecked")
        Map<String, Boolean> missingDocuments = (Map<String, Boolean>) metadata.get("missing_documents");
        assertTrue("Should be missing identity document", missingDocuments.get("identity_document"));
        assertTrue("Should be missing bank statement", missingDocuments.get("bank_statement"));
        assertTrue("Should be missing tax return", missingDocuments.get("tax_return"));
    }
    
    @Test(expected = ResourceNotFoundException.class)
    public void testEvaluateApplicationCompleteness_ApplicationNotFound() {
        // Setup
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.empty());
        
        // Execute
        processingService.evaluateApplicationCompleteness(testApplicationId);
        
        // Should throw ResourceNotFoundException
    }
    
    @Test
    public void testEvaluateApplicationCompleteness_NoMerchantDetails() {
        // Setup
        setupMocksForCompleteness(true);
        when(merchantDetailsRepository.findByApplicationId(any(UUID.class))).thenReturn(Optional.empty());
        
        // Execute
        boolean isComplete = processingService.evaluateApplicationCompleteness(testApplicationId);
        
        // Verify
        assertFalse("Application should be incomplete without merchant details", isComplete);
    }
    
    /*
     * Tests for updating application status
     */
    
    @Test
    public void testUpdateApplicationStatus_ValidTransition() {
        // Setup
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.of(testApplication));
        when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
        when(notificationService.sendApplicationStatusNotification(anyString(), anyString())).thenReturn(true);
        
        // Execute
        boolean result = processingService.updateApplicationStatus(testApplicationId, ApplicationStatus.PENDING.name(), "Initial review complete");
        
        // Verify
        assertTrue("Update should be successful", result);
        
        // Verify application was retrieved and saved
        verify(applicationRepository).findById(UUID.fromString(testApplicationId));
        verify(applicationRepository).save(any(Application.class));
        
        // Verify notification was sent
        verify(notificationService).sendApplicationStatusNotification(testApplicationId, ApplicationStatus.PENDING.name());
    }
    
    @Test(expected = ValidationException.class)
    public void testUpdateApplicationStatus_InvalidStatus() {
        // Execute with invalid status
        processingService.updateApplicationStatus(testApplicationId, "INVALID_STATUS", "Test reason");
        
        // Should throw ValidationException
    }
    
    @Test(expected = BusinessRuleException.class)
    public void testUpdateApplicationStatus_InvalidTransition() {
        // Setup
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.of(testApplication));
        
        // Try to transition from NEW to COMPLETED (invalid)
        processingService.updateApplicationStatus(testApplicationId, ApplicationStatus.COMPLETED.name(), "Invalid transition");
        
        // Should throw BusinessRuleException
    }
    
    @Test(expected = ResourceNotFoundException.class)
    public void testUpdateApplicationStatus_ApplicationNotFound() {
        // Setup
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.empty());
        
        // Execute
        processingService.updateApplicationStatus(testApplicationId, ApplicationStatus.PENDING.name(), "Test reason");
        
        // Should throw ResourceNotFoundException
    }
    
    @Test
    public void testUpdateApplicationStatus_StatusHistoryTracked() {
        // Setup
        when(applicationRepository.findById(any(UUID.class))).thenReturn(Optional.of(testApplication));
        when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
        when(notificationService.sendApplicationStatusNotification(anyString(), anyString())).thenReturn(true);
        
        // Execute
        processingService.updateApplicationStatus(testApplicationId, ApplicationStatus.PENDING.name(), "Initial review complete");
        
        // Verify status history was updated in metadata
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        Map<String, Object> metadata = savedApplication.getMetadata();
        assertTrue("Metadata should contain status_history", metadata.containsKey("status_history"));
        
        @SuppressWarnings("unchecked")
        List<Map<String, String>> statusHistory = (List<Map<String, String>>) metadata.get("status_history");
        assertFalse("Status history should not be empty", statusHistory.isEmpty());
        
        Map<String, String> lastStatusChange = statusHistory.get(statusHistory.size() - 1);
        assertEquals("From status should be NEW", ApplicationStatus.NEW.name(), lastStatusChange.get("from"));
        assertEquals("To status should be PENDING", ApplicationStatus.PENDING.name(), lastStatusChange.get("to"));
        assertEquals("Reason should match", "Initial review complete", lastStatusChange.get("reason"));
    }
    
    /*
     * Tests for validation and error handling
     */
    
    @Test(expected = ValidationException.class)
    public void testValidateProcessingMessage_NullMessage() {
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateProcessingMessage", DocumentProcessingMessage.class);
            method.setAccessible(true);
            method.invoke(processingService, (DocumentProcessingMessage) null);
        } catch (Exception e) {
            if (e.getCause() instanceof ValidationException) {
                throw (ValidationException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test(expected = ValidationException.class)
    public void testValidateProcessingMessage_MissingDocumentId() {
        // Create message without document ID
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setDocumentType(DocumentProcessingMessage.DocumentType.APPLICATION_FORM);
        message.setClassification("Application Form");
        message.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        message.setExtractedFields(createTestExtractedFields());
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateProcessingMessage", DocumentProcessingMessage.class);
            method.setAccessible(true);
            method.invoke(processingService, message);
        } catch (Exception e) {
            if (e.getCause() instanceof ValidationException) {
                throw (ValidationException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test(expected = ValidationException.class)
    public void testValidateProcessingMessage_MissingDocumentType() {
        // Create message without document type
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setDocumentId(testDocumentId);
        message.setClassification("Application Form");
        message.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        message.setExtractedFields(createTestExtractedFields());
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateProcessingMessage", DocumentProcessingMessage.class);
            method.setAccessible(true);
            method.invoke(processingService, message);
        } catch (Exception e) {
            if (e.getCause() instanceof ValidationException) {
                throw (ValidationException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test(expected = ValidationException.class)
    public void testValidateProcessingMessage_MissingClassification() {
        // Create message without classification
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setDocumentId(testDocumentId);
        message.setDocumentType(DocumentProcessingMessage.DocumentType.APPLICATION_FORM);
        message.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        message.setExtractedFields(createTestExtractedFields());
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateProcessingMessage", DocumentProcessingMessage.class);
            method.setAccessible(true);
            method.invoke(processingService, message);
        } catch (Exception e) {
            if (e.getCause() instanceof ValidationException) {
                throw (ValidationException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test(expected = ValidationException.class)
    public void testValidateProcessingMessage_MissingProcessingAction() {
        // Create message without processing action
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setDocumentId(testDocumentId);
        message.setDocumentType(DocumentProcessingMessage.DocumentType.APPLICATION_FORM);
        message.setClassification("Application Form");
        message.setExtractedFields(createTestExtractedFields());
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateProcessingMessage", DocumentProcessingMessage.class);
            method.setAccessible(true);
            method.invoke(processingService, message);
        } catch (Exception e) {
            if (e.getCause() instanceof ValidationException) {
                throw (ValidationException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test(expected = ValidationException.class)
    public void testValidateProcessingMessage_MissingExtractedFields() {
        // Create message without extracted fields
        DocumentProcessingMessage message = new DocumentProcessingMessage();
        message.setDocumentId(testDocumentId);
        message.setDocumentType(DocumentProcessingMessage.DocumentType.APPLICATION_FORM);
        message.setClassification("Application Form");
        message.setProcessingAction(DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION);
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateProcessingMessage", DocumentProcessingMessage.class);
            method.setAccessible(true);
            method.invoke(processingService, message);
        } catch (Exception e) {
            if (e.getCause() instanceof ValidationException) {
                throw (ValidationException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testCreateDocumentFromMessage_Success() {
        // Setup
        when(documentRepository.save(any(Document.class))).thenAnswer(invocation -> {
            Document doc = invocation.getArgument(0);
            if (doc.getId() == null) {
                doc.setId(UUID.randomUUID());
            }
            return doc;
        });
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "createDocumentFromMessage", DocumentProcessingMessage.class, Application.class);
            method.setAccessible(true);
            Document result = (Document) method.invoke(processingService, validApplicationMessage, testApplication);
            
            // Verify
            assertNotNull("Document should not be null", result);
            assertEquals("Document type should match", DocumentType.APPLICATION_FORM, result.getType());
            assertEquals("Document classification should match", "Application Form", result.getClassification());
            assertEquals("Document storage path should match", validApplicationMessage.getStoragePath(), result.getStoragePath());
            assertNotNull("Document metadata should not be null", result.getMetadata());
        } catch (Exception e) {
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test(expected = DocumentProcessingException.class)
    public void testCreateDocumentFromMessage_Exception() {
        // Setup to throw exception
        when(documentRepository.save(any(Document.class))).thenThrow(new RuntimeException("Database error"));
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "createDocumentFromMessage", DocumentProcessingMessage.class, Application.class);
            method.setAccessible(true);
            method.invoke(processingService, validApplicationMessage, testApplication);
        } catch (Exception e) {
            if (e.getCause() instanceof DocumentProcessingException) {
                throw (DocumentProcessingException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testMapDocumentType_AllTypes() {
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "mapDocumentType", DocumentProcessingMessage.DocumentType.class);
            method.setAccessible(true);
            
            // Test mapping for all document types
            assertEquals(DocumentType.APPLICATION_FORM, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.APPLICATION_FORM));
            assertEquals(DocumentType.BANK_STATEMENT, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.BANK_STATEMENT));
            assertEquals(DocumentType.TAX_RETURN, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.TAX_RETURN));
            assertEquals(DocumentType.ID_VERIFICATION, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.IDENTITY_DOCUMENT));
            assertEquals(DocumentType.BUSINESS_LICENSE, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.BUSINESS_LICENSE));
            assertEquals(DocumentType.MISCELLANEOUS, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.CREDIT_CARD_STATEMENT));
            assertEquals(DocumentType.MISCELLANEOUS, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.INVOICE));
            assertEquals(DocumentType.MISCELLANEOUS, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.UTILITY_BILL));
            assertEquals(DocumentType.MISCELLANEOUS, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.LEASE_AGREEMENT));
            assertEquals(DocumentType.MISCELLANEOUS, 
                    method.invoke(processingService, DocumentProcessingMessage.DocumentType.OTHER));
        } catch (Exception e) {
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testValidateStatusTransition_ValidTransitions() {
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateStatusTransition", ApplicationStatus.class, ApplicationStatus.class);
            method.setAccessible(true);
            
            // Test valid transitions
            method.invoke(processingService, ApplicationStatus.NEW, ApplicationStatus.PENDING); // Should not throw
            method.invoke(processingService, ApplicationStatus.NEW, ApplicationStatus.REJECTED); // Should not throw
            method.invoke(processingService, ApplicationStatus.PENDING, ApplicationStatus.PROCESSING); // Should not throw
            method.invoke(processingService, ApplicationStatus.PROCESSING, ApplicationStatus.APPROVED); // Should not throw
            method.invoke(processingService, ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED); // Should not throw
        } catch (Exception e) {
            fail("Unexpected exception for valid transition: " + e);
        }
    }
    
    @Test(expected = BusinessRuleException.class)
    public void testValidateStatusTransition_InvalidTransition() {
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "validateStatusTransition", ApplicationStatus.class, ApplicationStatus.class);
            method.setAccessible(true);
            
            // Test invalid transition (NEW to COMPLETED)
            method.invoke(processingService, ApplicationStatus.NEW, ApplicationStatus.COMPLETED);
        } catch (Exception e) {
            if (e.getCause() instanceof BusinessRuleException) {
                throw (BusinessRuleException) e.getCause();
            }
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testCreateMerchantDetailsIfAvailable_Success() {
        // Setup
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenAnswer(invocation -> {
            MerchantDetails merchant = invocation.getArgument(0);
            if (merchant.getId() == null) {
                merchant.setId(UUID.randomUUID().toString());
            }
            return merchant;
        });
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "createMerchantDetailsIfAvailable", DocumentProcessingMessage.class, Application.class);
            method.setAccessible(true);
            method.invoke(processingService, validApplicationMessage, testApplication);
            
            // Verify merchant details were saved
            verify(merchantDetailsRepository).save(any(MerchantDetails.class));
        } catch (Exception e) {
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testCreateMerchantDetailsIfAvailable_NoMerchantData() {
        // Create message without merchant data
        DocumentProcessingMessage message = createTestMessage(
                testDocumentId,
                DocumentProcessingMessage.DocumentType.APPLICATION_FORM,
                "Application Form",
                95.0,
                DocumentProcessingMessage.ProcessingAction.CREATE_NEW_APPLICATION,
                null,
                new HashMap<>()); // Empty extracted fields
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "createMerchantDetailsIfAvailable", DocumentProcessingMessage.class, Application.class);
            method.setAccessible(true);
            method.invoke(processingService, message, testApplication);
            
            // Verify merchant details were not saved
            verify(merchantDetailsRepository, never()).save(any(MerchantDetails.class));
        } catch (Exception e) {
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testUpdateMerchantDetailsIfAvailable_ExistingMerchant() {
        // Setup
        when(merchantDetailsRepository.findByApplicationId(any(UUID.class))).thenReturn(Optional.of(testMerchantDetails));
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(testMerchantDetails);
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "updateMerchantDetailsIfAvailable", DocumentProcessingMessage.class, Application.class);
            method.setAccessible(true);
            method.invoke(processingService, validApplicationMessage, testApplication);
            
            // Verify merchant details were updated
            verify(merchantDetailsRepository).save(any(MerchantDetails.class));
        } catch (Exception e) {
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testUpdateMerchantDetailsIfAvailable_NewMerchant() {
        // Setup
        when(merchantDetailsRepository.findByApplicationId(any(UUID.class))).thenReturn(Optional.empty());
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenAnswer(invocation -> {
            MerchantDetails merchant = invocation.getArgument(0);
            if (merchant.getId() == null) {
                merchant.setId(UUID.randomUUID().toString());
            }
            return merchant;
        });
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "updateMerchantDetailsIfAvailable", DocumentProcessingMessage.class, Application.class);
            method.setAccessible(true);
            method.invoke(processingService, validApplicationMessage, testApplication);
            
            // Verify new merchant details were created and saved
            verify(merchantDetailsRepository).save(any(MerchantDetails.class));
        } catch (Exception e) {
            fail("Unexpected exception: " + e);
        }
    }
    
    @Test
    public void testUpdateMerchantDetailsIfAvailable_LowConfidenceFields() {
        // Setup
        when(merchantDetailsRepository.findByApplicationId(any(UUID.class))).thenReturn(Optional.of(testMerchantDetails));
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(testMerchantDetails);
        
        // Modify message to have low confidence fields
        Map<String, DocumentProcessingMessage.ExtractedField> fields = new HashMap<>(validApplicationMessage.getExtractedFields());
        fields.put("industry", new DocumentProcessingMessage.ExtractedField("Retail", 65.0)); // Below threshold
        validApplicationMessage.setExtractedFields(fields);
        
        // Use reflection to access private method
        try {
            java.lang.reflect.Method method = ProcessingServiceImpl.class.getDeclaredMethod(
                    "updateMerchantDetailsIfAvailable", DocumentProcessingMessage.class, Application.class);
            method.setAccessible(true);
            method.invoke(processingService, validApplicationMessage, testApplication);
            
            // Verify merchant details were not updated with low confidence field
            ArgumentCaptor<MerchantDetails> merchantCaptor = ArgumentCaptor.forClass(MerchantDetails.class);
            verify(merchantDetailsRepository).save(merchantCaptor.capture());
            MerchantDetails savedMerchant = merchantCaptor.getValue();
            assertNotEquals("Industry should not be updated with low confidence value", "Retail", savedMerchant.getIndustry());
        } catch (Exception e) {
            fail("Unexpected exception: " + e);
        }
    }
}