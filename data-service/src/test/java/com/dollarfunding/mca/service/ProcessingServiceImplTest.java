package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ProcessingException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.service.ValidationService.ValidationResult;
import com.dollarfunding.mca.service.ValidationService.ValidationSeverity;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the ProcessingServiceImpl class.
 * 
 * These tests verify the orchestration of the application processing pipeline,
 * application of business rules, management of interactions between services,
 * tracking of processing status, and handling of exceptions.
 */
@ExtendWith(MockitoExtension.class)
public class ProcessingServiceImplTest {

    @Mock
    private ApplicationRepository applicationRepository;
    
    @Mock
    private DocumentRepository documentRepository;
    
    @Mock
    private ValidationService validationService;
    
    @Mock
    private DocumentService documentService;
    
    @Mock
    private NotificationService notificationService;
    
    @InjectMocks
    private ProcessingServiceImpl processingService;
    
    @Captor
    private ArgumentCaptor<Application> applicationCaptor;
    
    @Captor
    private ArgumentCaptor<Document> documentCaptor;
    
    private UUID applicationId;
    private UUID documentId;
    private Application application;
    private Document document;
    private MerchantDetails merchantDetails;
    private Map<String, Object> extractedData;
    private ValidationResult validValidationResult;
    private ValidationResult invalidValidationResult;
    private ValidationResult warningValidationResult;
    
    @BeforeEach
    void setUp() {
        // Initialize test data
        applicationId = UUID.randomUUID();
        documentId = UUID.randomUUID();
        
        // Create application
        application = new Application(ApplicationStatus.PROCESSING);
        application.setId(applicationId);
        application.setCreatedAt(LocalDateTime.now());
        application.setUpdatedAt(LocalDateTime.now());
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        // Create merchant details
        merchantDetails = new MerchantDetails();
        merchantDetails.setLegalName("Test Business LLC");
        merchantDetails.setDbaName("Test Business");
        merchantDetails.setEin("12-3456789");
        merchantDetails.setAddress("123 Test St, Test City, TS 12345");
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(500000.0);
        merchantDetails.setApplication(application);
        application.setMerchantDetails(merchantDetails);
        
        // Create document
        document = new Document();
        document.setId(documentId);
        document.setType(DocumentType.BANK_STATEMENT);
        document.setClassification("Bank Statement");
        document.setStoragePath("s3://mca-documents-staging/" + documentId);
        document.setUploadedAt(LocalDateTime.now());
        
        // Create extracted data
        extractedData = new HashMap<>();
        extractedData.put("accountNumber", "123456789");
        extractedData.put("bankName", "Test Bank");
        extractedData.put("statementDate", "2023-01-01");
        extractedData.put("balance", "50000.00");
        extractedData.put("averageBalance", "45000.00");
        
        Map<String, Object> merchantData = new HashMap<>();
        merchantData.put("legalName", "Test Business LLC");
        merchantData.put("dbaName", "Test Business");
        merchantData.put("ein", "12-3456789");
        merchantData.put("address", "123 Test St, Test City, TS 12345");
        merchantData.put("industry", "Technology");
        merchantData.put("revenue", "500000.00");
        extractedData.put("merchantDetails", merchantData);
        
        // Create validation results
        validValidationResult = new ValidationResult(true, ValidationSeverity.NONE, new ArrayList<>());
        
        List<String> errors = new ArrayList<>();
        errors.add("Missing required field: revenue");
        invalidValidationResult = new ValidationResult(false, ValidationSeverity.ERROR, errors);
        
        List<String> warnings = new ArrayList<>();
        warnings.add("Low confidence on field: accountNumber");
        warningValidationResult = new ValidationResult(false, ValidationSeverity.WARNING, warnings);
    }
    
    @Test
    @DisplayName("Should process new application successfully")
    void processNewApplication_Success() throws ProcessingException {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        when(validationService.validateExtractedData(any(DocumentType.class), anyMap())).thenReturn(validValidationResult);
        when(applicationRepository.save(any(Application.class))).thenAnswer(invocation -> invocation.getArgument(0));
        doNothing().when(notificationService).sendApplicationCreatedNotification(any(Application.class));
        
        // Act
        ApplicationResponseDTO result = processingService.processNewApplication(documentId, extractedData);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(documentRepository).findById(documentId);
        verify(validationService).validateExtractedData(eq(DocumentType.BANK_STATEMENT), eq(extractedData));
        verify(applicationRepository).save(applicationCaptor.capture());
        verify(documentRepository).save(documentCaptor.capture());
        verify(notificationService).sendApplicationCreatedNotification(any(Application.class));
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(ApplicationStatus.PROCESSING, capturedApplication.getStatus(), "Application status should be PROCESSING");
        
        Document capturedDocument = documentCaptor.getValue();
        assertNotNull(capturedDocument.getApplicationId(), "Document should have application ID set");
    }
    
    @Test
    @DisplayName("Should throw exception when document not found during new application processing")
    void processNewApplication_DocumentNotFound() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.empty());
        
        // Act & Assert
        ProcessingException exception = assertThrows(ProcessingException.class, 
                () -> processingService.processNewApplication(documentId, extractedData));
        
        assertEquals("Failed to process new application from document ID: " + documentId, exception.getMessage());
        verify(documentRepository).findById(documentId);
        verify(applicationRepository, never()).save(any(Application.class));
        verify(notificationService, never()).sendApplicationCreatedNotification(any(Application.class));
    }
    
    @Test
    @DisplayName("Should throw exception when validation fails during new application processing")
    void processNewApplication_ValidationFails() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        when(validationService.validateExtractedData(any(DocumentType.class), anyMap())).thenReturn(invalidValidationResult);
        
        // Act & Assert
        ProcessingException exception = assertThrows(ProcessingException.class, 
                () -> processingService.processNewApplication(documentId, extractedData));
        
        assertEquals("Failed to process new application from document ID: " + documentId, exception.getMessage());
        verify(documentRepository).findById(documentId);
        verify(validationService).validateExtractedData(eq(DocumentType.BANK_STATEMENT), eq(extractedData));
        verify(applicationRepository, never()).save(any(Application.class));
        verify(notificationService, never()).sendApplicationCreatedNotification(any(Application.class));
    }
    
    @Test
    @DisplayName("Should update application with document successfully")
    void updateApplicationWithDocument_Success() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        when(validationService.validateExtractedData(any(DocumentType.class), anyMap())).thenReturn(validValidationResult);
        when(applicationRepository.save(any(Application.class))).thenAnswer(invocation -> invocation.getArgument(0));
        doNothing().when(notificationService).sendDocumentProcessedNotification(any(Document.class), any(UUID.class), anyMap());
        
        // Act
        ApplicationResponseDTO result = processingService.updateApplicationWithDocument(applicationId, documentId, extractedData);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findById(documentId);
        verify(validationService).validateExtractedData(eq(DocumentType.BANK_STATEMENT), eq(extractedData));
        verify(applicationRepository).save(applicationCaptor.capture());
        verify(documentRepository).save(documentCaptor.capture());
        verify(notificationService).sendDocumentProcessedNotification(eq(document), eq(applicationId), eq(extractedData));
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(applicationId, capturedApplication.getId(), "Application ID should match");
        
        Document capturedDocument = documentCaptor.getValue();
        assertEquals(applicationId, capturedDocument.getApplicationId(), "Document should have correct application ID");
    }
    
    @Test
    @DisplayName("Should throw exception when application not found during update")
    void updateApplicationWithDocument_ApplicationNotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.empty());
        
        // Act & Assert
        ProcessingException exception = assertThrows(ProcessingException.class, 
                () -> processingService.updateApplicationWithDocument(applicationId, documentId, extractedData));
        
        assertEquals("Failed to update application ID: " + applicationId + " with document ID: " + documentId, exception.getMessage());
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository, never()).findById(any(UUID.class));
        verify(applicationRepository, never()).save(any(Application.class));
    }
    
    @Test
    @DisplayName("Should process document and create new application when no matching application found")
    void processDocument_CreateNewApplication() throws ProcessingException {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        when(validationService.validateExtractedData(any(DocumentType.class), anyMap())).thenReturn(validValidationResult);
        when(applicationRepository.findByMerchantDetailsEin(anyString())).thenReturn(new ArrayList<>());
        when(applicationRepository.findByMerchantDetailsLegalName(anyString())).thenReturn(new ArrayList<>());
        when(applicationRepository.findByMerchantDetailsDbaName(anyString())).thenReturn(new ArrayList<>());
        when(applicationRepository.save(any(Application.class))).thenAnswer(invocation -> {
            Application app = invocation.getArgument(0);
            if (app.getId() == null) {
                app.setId(UUID.randomUUID());
            }
            return app;
        });
        doNothing().when(notificationService).sendApplicationCreatedNotification(any(Application.class));
        
        // Act
        ApplicationResponseDTO result = processingService.processDocument(documentId, extractedData);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(documentRepository).findById(documentId);
        verify(validationService).validateExtractedData(eq(DocumentType.BANK_STATEMENT), eq(extractedData));
        verify(applicationRepository).findByMerchantDetailsEin("12-3456789");
        verify(applicationRepository).save(any(Application.class));
        verify(documentRepository).save(any(Document.class));
        verify(notificationService).sendApplicationCreatedNotification(any(Application.class));
    }
    
    @Test
    @DisplayName("Should process document and update existing application when matching application found")
    void processDocument_UpdateExistingApplication() throws ProcessingException {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        when(validationService.validateExtractedData(any(DocumentType.class), anyMap())).thenReturn(validValidationResult);
        when(applicationRepository.findByMerchantDetailsEin(anyString())).thenReturn(List.of(application));
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        doNothing().when(notificationService).sendDocumentProcessedNotification(any(Document.class), any(UUID.class), anyMap());
        
        // Act
        ApplicationResponseDTO result = processingService.processDocument(documentId, extractedData);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(documentRepository).findById(documentId);
        verify(validationService).validateExtractedData(eq(DocumentType.BANK_STATEMENT), eq(extractedData));
        verify(applicationRepository).findByMerchantDetailsEin("12-3456789");
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository).save(any(Application.class));
        verify(documentRepository).save(any(Document.class));
        verify(notificationService).sendDocumentProcessedNotification(any(Document.class), any(UUID.class), anyMap());
    }
    
    @Test
    @DisplayName("Should update application status successfully")
    void updateApplicationStatus_Success() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        doNothing().when(notificationService).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("reason", "All documents verified");
        
        // Act
        ApplicationResponseDTO result = processingService.updateApplicationStatus(applicationId, ApplicationStatus.APPROVED, metadata);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository).save(applicationCaptor.capture());
        verify(notificationService).sendApplicationStatusNotification(eq(application), eq("PROCESSING"), eq("APPROVED"));
        verify(notificationService).sendApplicationApprovedNotification(application);
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(ApplicationStatus.APPROVED, capturedApplication.getStatus(), "Application status should be APPROVED");
        assertTrue(capturedApplication.getMetadata().containsKey("reason"), "Metadata should contain reason");
        assertTrue(capturedApplication.getMetadata().containsKey("statusChangedAt"), "Metadata should contain statusChangedAt");
    }
    
    @Test
    @DisplayName("Should throw exception for invalid status transition")
    void updateApplicationStatus_InvalidTransition() {
        // Arrange
        application.setStatus(ApplicationStatus.REJECTED);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("reason", "Trying to approve a rejected application");
        
        // Act & Assert
        ProcessingException exception = assertThrows(ProcessingException.class, 
                () -> processingService.updateApplicationStatus(applicationId, ApplicationStatus.APPROVED, metadata));
        
        assertTrue(exception.getMessage().contains("Invalid status transition"), "Exception should mention invalid transition");
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository, never()).save(any(Application.class));
        verify(notificationService, never()).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
    }
    
    @Test
    @DisplayName("Should calculate processing time when completing application")
    void updateApplicationStatus_CalculateProcessingTime() throws ProcessingException {
        // Arrange
        LocalDateTime creationTime = LocalDateTime.now().minusMinutes(3); // 3 minutes ago
        application.setCreatedAt(creationTime);
        
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        doNothing().when(notificationService).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        
        // Act
        ApplicationResponseDTO result = processingService.updateApplicationStatus(applicationId, ApplicationStatus.COMPLETED, null);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).save(applicationCaptor.capture());
        
        Application capturedApplication = applicationCaptor.getValue();
        assertTrue(capturedApplication.getMetadata().containsKey("processingTimeMillis"), "Metadata should contain processingTimeMillis");
        assertTrue(capturedApplication.getMetadata().containsKey("processingTimeMinutes"), "Metadata should contain processingTimeMinutes");
        assertTrue(capturedApplication.getMetadata().containsKey("completedAt"), "Metadata should contain completedAt");
        assertTrue(capturedApplication.getMetadata().containsKey("processedWithinTarget"), "Metadata should contain processedWithinTarget");
    }
    
    @Test
    @DisplayName("Should check if application is complete successfully")
    void isApplicationComplete_Success() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(validationService.evaluateApplicationCompleteness(any(Application.class))).thenReturn(validValidationResult);
        
        // Act
        boolean result = processingService.isApplicationComplete(applicationId);
        
        // Assert
        assertTrue(result, "Application should be complete");
        verify(applicationRepository).findById(applicationId);
        verify(validationService).evaluateApplicationCompleteness(application);
    }
    
    @Test
    @DisplayName("Should return false when application is not complete")
    void isApplicationComplete_Incomplete() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(validationService.evaluateApplicationCompleteness(any(Application.class))).thenReturn(invalidValidationResult);
        
        // Act
        boolean result = processingService.isApplicationComplete(applicationId);
        
        // Assert
        assertFalse(result, "Application should not be complete");
        verify(applicationRepository).findById(applicationId);
        verify(validationService).evaluateApplicationCompleteness(application);
    }
    
    @Test
    @DisplayName("Should get processing status successfully")
    void getProcessingStatus_Success() throws ProcessingException {
        // Arrange
        List<Document> documents = new ArrayList<>();
        documents.add(document);
        application.setDocuments(documents);
        
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(validationService.evaluateApplicationCompleteness(any(Application.class))).thenReturn(validValidationResult);
        when(validationService.validateApplication(any(Application.class))).thenReturn(validValidationResult);
        
        // Act
        Map<String, Object> result = processingService.getProcessingStatus(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(applicationId, result.get("applicationId"), "Application ID should match");
        assertEquals("PROCESSING", result.get("status"), "Status should match");
        assertEquals("NOT_REVIEWED", result.get("reviewStatus"), "Review status should match");
        assertEquals(1, result.get("documentCount"), "Document count should be 1");
        assertTrue((Boolean) result.get("isComplete"), "Application should be complete");
        assertTrue((Boolean) result.get("validationPassed"), "Validation should pass");
        
        verify(applicationRepository).findById(applicationId);
        verify(validationService).evaluateApplicationCompleteness(application);
        verify(validationService).validateApplication(application);
    }
    
    @Test
    @DisplayName("Should get required documents successfully")
    void getRequiredDocuments_Success() throws ProcessingException {
        // Arrange
        List<Document> documents = new ArrayList<>();
        documents.add(document); // Only has BANK_STATEMENT
        application.setDocuments(documents);
        
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        
        // Act
        List<String> result = processingService.getRequiredDocuments(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(3, result.size(), "Should have 3 required documents remaining");
        assertTrue(result.contains("Tax Return"), "Should require Tax Return");
        assertTrue(result.contains("Business License"), "Should require Business License");
        assertTrue(result.contains("ID Verification"), "Should require ID Verification");
        
        verify(applicationRepository).findById(applicationId);
    }
    
    @Test
    @DisplayName("Should reprocess application successfully")
    void reprocessApplication_Success() throws ProcessingException {
        // Arrange
        List<Document> documents = new ArrayList<>();
        documents.add(document);
        application.setDocuments(documents);
        
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        when(validationService.validateBusinessRules(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(validValidationResult);
        when(validationService.evaluateApplicationCompleteness(any(Application.class))).thenReturn(validValidationResult);
        when(validationService.validateApprovalRequirements(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(validValidationResult);
        doNothing().when(notificationService).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        doNothing().when(notificationService).sendApplicationApprovedNotification(any(Application.class));
        
        // Act
        ApplicationResponseDTO result = processingService.reprocessApplication(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository, times(2)).save(any(Application.class)); // Once for status update, once for final save
        verify(validationService).validateBusinessRules(eq(application), eq(merchantDetails), anyList());
        verify(validationService).evaluateApplicationCompleteness(application);
        verify(validationService).validateApprovalRequirements(eq(application), eq(merchantDetails), anyList());
        
        // Verify application was set to PROCESSING status during reprocessing
        verify(applicationRepository).save(applicationCaptor.capture());
        Application capturedApplication = applicationCaptor.getAllValues().get(0);
        assertEquals(ApplicationStatus.PROCESSING, capturedApplication.getStatus(), "Application status should be set to PROCESSING");
        assertTrue(capturedApplication.getMetadata().containsKey("reprocessedAt"), "Metadata should contain reprocessedAt");
    }
    
    @Test
    @DisplayName("Should handle processing exception successfully")
    void handleProcessingException_Success() {
        // Arrange
        Exception testException = new RuntimeException("Test exception");
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("processingStage", "document_validation");
        
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        when(documentRepository.save(any(Document.class))).thenReturn(document);
        doNothing().when(notificationService).sendSystemEventNotification(any(), anyMap());
        
        // Act
        processingService.handleProcessingException(documentId, applicationId, testException, metadata);
        
        // Assert
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findById(documentId);
        verify(applicationRepository).save(applicationCaptor.capture());
        verify(documentRepository).save(documentCaptor.capture());
        verify(notificationService, times(2)).sendSystemEventNotification(any(), anyMap());
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(ApplicationStatus.ERROR, capturedApplication.getStatus(), "Application status should be ERROR");
        assertTrue(capturedApplication.getMetadata().containsKey("processingError"), "Metadata should contain processingError");
        
        Document capturedDocument = documentCaptor.getValue();
        assertTrue(capturedDocument.getMetadata().containsKey("processingError"), "Document metadata should contain processingError");
    }
    
    @Test
    @DisplayName("Should get application documents successfully")
    void getApplicationDocuments_Success() throws ProcessingException {
        // Arrange
        List<Document> documents = new ArrayList<>();
        documents.add(document);
        application.setDocuments(documents);
        
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(documentService.generateSecureUrl(any(UUID.class))).thenReturn("https://example.com/secure-document-url");
        
        // Act
        List<DocumentResponseDTO> result = processingService.getApplicationDocuments(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(1, result.size(), "Should have 1 document");
        assertEquals(documentId, result.get(0).getId(), "Document ID should match");
        assertEquals("https://example.com/secure-document-url", result.get(0).getDownloadUrl(), "Download URL should match");
        
        verify(applicationRepository).findById(applicationId);
        verify(documentService).generateSecureUrl(documentId);
    }
    
    @Test
    @DisplayName("Should apply business rules and approve application")
    void applyBusinessRules_Approve() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(validationService.validateBusinessRules(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(validValidationResult);
        when(validationService.evaluateApplicationCompleteness(any(Application.class))).thenReturn(validValidationResult);
        when(validationService.validateApprovalRequirements(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(validValidationResult);
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        doNothing().when(notificationService).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        doNothing().when(notificationService).sendApplicationApprovedNotification(any(Application.class));
        
        // Act
        ApplicationResponseDTO result = processingService.applyBusinessRules(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateBusinessRules(eq(application), eq(merchantDetails), anyList());
        verify(validationService).evaluateApplicationCompleteness(application);
        verify(validationService).validateApprovalRequirements(eq(application), eq(merchantDetails), anyList());
        verify(applicationRepository).save(applicationCaptor.capture());
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(ApplicationStatus.APPROVED, capturedApplication.getStatus(), "Application status should be APPROVED");
        verify(notificationService).sendApplicationApprovedNotification(application);
    }
    
    @Test
    @DisplayName("Should apply business rules and reject application")
    void applyBusinessRules_Reject() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(validationService.validateBusinessRules(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(validValidationResult);
        when(validationService.evaluateApplicationCompleteness(any(Application.class))).thenReturn(validValidationResult);
        when(validationService.validateApprovalRequirements(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(invalidValidationResult);
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        doNothing().when(notificationService).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        doNothing().when(notificationService).sendApplicationRejectedNotification(any(Application.class), anyString());
        
        // Act
        ApplicationResponseDTO result = processingService.applyBusinessRules(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateBusinessRules(eq(application), eq(merchantDetails), anyList());
        verify(validationService).evaluateApplicationCompleteness(application);
        verify(validationService).validateApprovalRequirements(eq(application), eq(merchantDetails), anyList());
        verify(applicationRepository).save(applicationCaptor.capture());
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(ApplicationStatus.REJECTED, capturedApplication.getStatus(), "Application status should be REJECTED");
        verify(notificationService).sendApplicationRejectedNotification(eq(application), anyString());
    }
    
    @Test
    @DisplayName("Should apply business rules and set application to pending when incomplete")
    void applyBusinessRules_Pending() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(validationService.validateBusinessRules(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(validValidationResult);
        when(validationService.evaluateApplicationCompleteness(any(Application.class))).thenReturn(invalidValidationResult);
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        doNothing().when(notificationService).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        
        // Act
        ApplicationResponseDTO result = processingService.applyBusinessRules(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateBusinessRules(eq(application), eq(merchantDetails), anyList());
        verify(validationService).evaluateApplicationCompleteness(application);
        verify(validationService, never()).validateApprovalRequirements(any(Application.class), any(MerchantDetails.class), anyList());
        verify(applicationRepository).save(applicationCaptor.capture());
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(ApplicationStatus.PENDING, capturedApplication.getStatus(), "Application status should be PENDING");
        assertTrue(capturedApplication.getMetadata().containsKey("pendingReason"), "Metadata should contain pendingReason");
    }
    
    @Test
    @DisplayName("Should apply business rules and set application to exception with warnings")
    void applyBusinessRules_Exception_Warning() throws ProcessingException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(validationService.validateBusinessRules(any(Application.class), any(MerchantDetails.class), anyList()))
                .thenReturn(warningValidationResult);
        when(applicationRepository.save(any(Application.class))).thenReturn(application);
        doNothing().when(notificationService).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        
        // Act
        ApplicationResponseDTO result = processingService.applyBusinessRules(applicationId);
        
        // Assert
        assertNotNull(result, "Result should not be null");
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateBusinessRules(eq(application), eq(merchantDetails), anyList());
        verify(validationService, never()).evaluateApplicationCompleteness(any(Application.class));
        verify(applicationRepository).save(applicationCaptor.capture());
        
        Application capturedApplication = applicationCaptor.getValue();
        assertEquals(ApplicationStatus.EXCEPTION, capturedApplication.getStatus(), "Application status should be EXCEPTION");
        assertTrue(capturedApplication.getMetadata().containsKey("exceptionReason"), "Metadata should contain exceptionReason");
        assertEquals("WARNING", capturedApplication.getMetadata().get("exceptionSeverity"), "Exception severity should be WARNING");
    }
}