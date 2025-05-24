package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentClassification;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ProcessingException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.service.ValidationService.ValidationResult;
import com.dollarfunding.mca.service.ValidationService.ValidationSeverity;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Implementation of the ProcessingService interface that manages application processing workflows
 * for the MCA application. It handles the processing of new applications, updates to existing applications,
 * and application lifecycle management.
 * 
 * This class orchestrates the interaction between ApplicationService, DocumentService, ValidationService,
 * and NotificationService to implement the complete application processing pipeline.
 */
@Service
public class ProcessingServiceImpl implements ProcessingService {

    private static final Logger logger = LoggerFactory.getLogger(ProcessingServiceImpl.class);
    
    private static final int TARGET_PROCESSING_MINUTES = 5;
    private static final double REQUIRED_CONFIDENCE_THRESHOLD = 0.75;
    private static final int MAX_RETRY_ATTEMPTS = 3;
    
    private final ApplicationRepository applicationRepository;
    private final DocumentRepository documentRepository;
    private final ValidationService validationService;
    private final DocumentService documentService;
    private final NotificationService notificationService;
    
    /**
     * Constructor with required dependencies.
     * 
     * @param applicationRepository Repository for Application entities
     * @param documentRepository Repository for Document entities
     * @param validationService Service for data validation and business rule application
     * @param documentService Service for document management
     * @param notificationService Service for notification delivery
     */
    @Autowired
    public ProcessingServiceImpl(ApplicationRepository applicationRepository,
                                DocumentRepository documentRepository,
                                ValidationService validationService,
                                DocumentService documentService,
                                NotificationService notificationService) {
        this.applicationRepository = applicationRepository;
        this.documentRepository = documentRepository;
        this.validationService = validationService;
        this.documentService = documentService;
        this.notificationService = notificationService;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public ApplicationResponseDTO processNewApplication(UUID documentId, Map<String, Object> extractedData) throws ProcessingException {
        logger.info("Processing new application from document ID: {}", documentId);
        
        try {
            // Retrieve the document
            Document document = findDocumentById(documentId);
            
            // Validate extracted data
            validateExtractedData(document.getType(), extractedData);
            
            // Create a new application
            Application application = createNewApplication(extractedData);
            
            // Associate the document with the application
            associateDocumentWithApplication(document, application);
            
            // Apply business rules
            applyBusinessRules(application.getId());
            
            // Save the application
            application = applicationRepository.save(application);
            
            // Send notification
            notificationService.sendApplicationCreatedNotification(application);
            
            logger.info("Successfully processed new application with ID: {}", application.getId());
            
            // Return the response DTO
            return ApplicationResponseDTO.fromEntityWithAllDetails(application, true);
        } catch (Exception e) {
            String errorMessage = "Failed to process new application from document ID: " + documentId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "NEW_APPLICATION_PROCESSING_ERROR", documentId, null, extractedData);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public ApplicationResponseDTO updateApplicationWithDocument(UUID applicationId, UUID documentId, Map<String, Object> extractedData) throws ProcessingException {
        logger.info("Updating application ID: {} with document ID: {}", applicationId, documentId);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Retrieve the document
            Document document = findDocumentById(documentId);
            
            // Validate extracted data
            validateExtractedData(document.getType(), extractedData);
            
            // Associate the document with the application
            associateDocumentWithApplication(document, application);
            
            // Update application data based on document content
            updateApplicationData(application, document.getType(), extractedData);
            
            // Apply business rules
            applyBusinessRules(applicationId);
            
            // Save the application
            application = applicationRepository.save(application);
            
            // Send notification
            notificationService.sendDocumentProcessedNotification(document, applicationId, extractedData);
            
            logger.info("Successfully updated application ID: {} with document ID: {}", applicationId, documentId);
            
            // Return the response DTO
            return ApplicationResponseDTO.fromEntityWithAllDetails(application, true);
        } catch (Exception e) {
            String errorMessage = "Failed to update application ID: " + applicationId + " with document ID: " + documentId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "UPDATE_APPLICATION_PROCESSING_ERROR", documentId, applicationId, extractedData);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public ApplicationResponseDTO processDocument(UUID documentId, Map<String, Object> extractedData) throws ProcessingException {
        logger.info("Processing document ID: {}", documentId);
        
        try {
            // Retrieve the document
            Document document = findDocumentById(documentId);
            
            // Validate extracted data
            validateExtractedData(document.getType(), extractedData);
            
            // Check if the document belongs to an existing application
            Optional<Application> existingApplication = findApplicationByDocumentMetadata(extractedData);
            
            if (existingApplication.isPresent()) {
                // Update existing application
                return updateApplicationWithDocument(existingApplication.get().getId(), documentId, extractedData);
            } else {
                // Create new application
                return processNewApplication(documentId, extractedData);
            }
        } catch (Exception e) {
            String errorMessage = "Failed to process document ID: " + documentId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "DOCUMENT_PROCESSING_ERROR", documentId, null, extractedData);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public ApplicationResponseDTO updateApplicationStatus(UUID applicationId, ApplicationStatus newStatus, Map<String, Object> metadata) throws ProcessingException {
        logger.info("Updating status of application ID: {} to {}", applicationId, newStatus);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Get the current status for notification
            ApplicationStatus currentStatus = application.getStatus();
            
            // Validate status transition
            if (!currentStatus.canTransitionTo(newStatus)) {
                String errorMessage = "Invalid status transition from " + currentStatus + " to " + newStatus;
                logger.error(errorMessage);
                throw new ProcessingException(errorMessage, "INVALID_STATUS_TRANSITION", null, applicationId, metadata);
            }
            
            // Update the status
            application.setStatus(newStatus);
            
            // Add metadata if provided
            if (metadata != null && !metadata.isEmpty()) {
                for (Map.Entry<String, Object> entry : metadata.entrySet()) {
                    application.addMetadata(entry.getKey(), entry.getValue());
                }
            }
            
            // Add status change timestamp
            application.addMetadata("statusChangedAt", LocalDateTime.now().toString());
            
            // If status is COMPLETED, calculate processing time
            if (newStatus == ApplicationStatus.COMPLETED) {
                calculateAndStoreProcessingTime(application);
            }
            
            // Save the application
            application = applicationRepository.save(application);
            
            // Send notification
            notificationService.sendApplicationStatusNotification(application, currentStatus.name(), newStatus.name());
            
            // If status is APPROVED or REJECTED, send specific notification
            if (newStatus == ApplicationStatus.APPROVED) {
                notificationService.sendApplicationApprovedNotification(application);
            } else if (newStatus == ApplicationStatus.REJECTED) {
                String reason = metadata != null ? (String) metadata.get("rejectionReason") : "";
                notificationService.sendApplicationRejectedNotification(application, reason);
            }
            
            logger.info("Successfully updated status of application ID: {} to {}", applicationId, newStatus);
            
            // Return the response DTO
            return ApplicationResponseDTO.fromEntityWithAllDetails(application, true);
        } catch (ProcessingException e) {
            // Rethrow ProcessingException
            throw e;
        } catch (Exception e) {
            String errorMessage = "Failed to update status of application ID: " + applicationId + " to " + newStatus;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "STATUS_UPDATE_ERROR", null, applicationId, metadata);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Cacheable(value = "applicationCompleteness", key = "#applicationId")
    public boolean isApplicationComplete(UUID applicationId) throws ProcessingException {
        logger.info("Checking if application ID: {} is complete", applicationId);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Get the validation result
            ValidationResult validationResult = validationService.evaluateApplicationCompleteness(application);
            
            // Log the result
            logger.info("Application ID: {} completeness check result: {}", applicationId, validationResult.isValid());
            
            return validationResult.isValid();
        } catch (Exception e) {
            String errorMessage = "Failed to check if application ID: " + applicationId + " is complete";
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "COMPLETENESS_CHECK_ERROR", null, applicationId, null);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Map<String, Object> getProcessingStatus(UUID applicationId) throws ProcessingException {
        logger.info("Getting processing status for application ID: {}", applicationId);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Create the status map
            Map<String, Object> statusMap = new HashMap<>();
            
            // Add basic status information
            statusMap.put("applicationId", application.getId());
            statusMap.put("status", application.getStatus().name());
            statusMap.put("reviewStatus", application.getReviewStatus().name());
            statusMap.put("createdAt", application.getCreatedAt());
            statusMap.put("updatedAt", application.getUpdatedAt());
            
            // Add document counts
            List<Document> documents = application.getDocuments();
            statusMap.put("documentCount", documents.size());
            
            // Count documents by type
            Map<DocumentType, Long> documentCountsByType = documents.stream()
                    .collect(Collectors.groupingBy(Document::getType, Collectors.counting()));
            statusMap.put("documentCountsByType", documentCountsByType);
            
            // Check if application is complete
            boolean isComplete = isApplicationComplete(applicationId);
            statusMap.put("isComplete", isComplete);
            
            // Get required documents
            List<String> requiredDocuments = getRequiredDocuments(applicationId);
            statusMap.put("requiredDocuments", requiredDocuments);
            
            // Add processing time if available
            if (application.getStatus() == ApplicationStatus.COMPLETED) {
                long processingTimeMillis = application.getProcessingTimeMillis();
                statusMap.put("processingTimeMinutes", processingTimeMillis / 60000.0);
                statusMap.put("processedWithinTarget", processingTimeMillis < (TARGET_PROCESSING_MINUTES * 60000));
            }
            
            // Add validation results if available
            ValidationResult validationResult = validationService.validateApplication(application);
            statusMap.put("validationPassed", validationResult.isValid());
            statusMap.put("validationErrors", validationResult.getErrors());
            statusMap.put("validationSeverity", validationResult.getSeverity().name());
            
            logger.info("Successfully retrieved processing status for application ID: {}", applicationId);
            
            return statusMap;
        } catch (Exception e) {
            String errorMessage = "Failed to get processing status for application ID: " + applicationId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "PROCESSING_STATUS_ERROR", null, applicationId, null);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public List<String> getRequiredDocuments(UUID applicationId) throws ProcessingException {
        logger.info("Getting required documents for application ID: {}", applicationId);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Get the documents associated with the application
            List<Document> documents = application.getDocuments();
            
            // Get the document types that are already present
            Set<DocumentType> existingDocumentTypes = documents.stream()
                    .map(Document::getType)
                    .collect(Collectors.toSet());
            
            // Define the required document types for a complete application
            // This could be configurable or determined by business rules
            List<DocumentType> requiredDocumentTypes = List.of(
                    DocumentType.BANK_STATEMENT,
                    DocumentType.TAX_RETURN,
                    DocumentType.BUSINESS_LICENSE,
                    DocumentType.ID_VERIFICATION
            );
            
            // Determine which required document types are missing
            List<String> missingDocumentTypes = requiredDocumentTypes.stream()
                    .filter(type -> !existingDocumentTypes.contains(type))
                    .map(DocumentType::getDescription)
                    .collect(Collectors.toList());
            
            logger.info("Required documents for application ID: {}: {}", applicationId, missingDocumentTypes);
            
            return missingDocumentTypes;
        } catch (Exception e) {
            String errorMessage = "Failed to get required documents for application ID: " + applicationId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "REQUIRED_DOCUMENTS_ERROR", null, applicationId, null);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    @CacheEvict(value = {"applicationCompleteness", "applicationDocuments"}, key = "#applicationId")
    public ApplicationResponseDTO reprocessApplication(UUID applicationId) throws ProcessingException {
        logger.info("Reprocessing application ID: {}", applicationId);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Update status to PROCESSING
            ApplicationStatus currentStatus = application.getStatus();
            application.setStatus(ApplicationStatus.PROCESSING);
            
            // Add reprocessing metadata
            application.addMetadata("reprocessedAt", LocalDateTime.now().toString());
            application.addMetadata("previousStatus", currentStatus.name());
            
            // Save the application
            application = applicationRepository.save(application);
            
            // Get all documents associated with the application
            List<Document> documents = application.getDocuments();
            
            // Reprocess each document
            for (Document document : documents) {
                // Get the extracted data from document metadata
                Map<String, Object> extractedData = document.getMetadata();
                
                // Update application data based on document content
                updateApplicationData(application, document.getType(), extractedData);
            }
            
            // Apply business rules
            ApplicationResponseDTO responseDTO = applyBusinessRules(applicationId);
            
            logger.info("Successfully reprocessed application ID: {}", applicationId);
            
            return responseDTO;
        } catch (Exception e) {
            String errorMessage = "Failed to reprocess application ID: " + applicationId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "REPROCESSING_ERROR", null, applicationId, null);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public void handleProcessingException(UUID documentId, UUID applicationId, Exception exception, Map<String, Object> metadata) throws ProcessingException {
        logger.error("Handling processing exception for document ID: {}, application ID: {}", documentId, applicationId, exception);
        
        try {
            // Create error metadata
            Map<String, Object> errorMetadata = new HashMap<>();
            errorMetadata.put("errorTimestamp", LocalDateTime.now().toString());
            errorMetadata.put("errorMessage", exception.getMessage());
            errorMetadata.put("errorType", exception.getClass().getName());
            
            if (metadata != null) {
                errorMetadata.putAll(metadata);
            }
            
            // If there's an application ID, update the application status
            if (applicationId != null) {
                try {
                    Application application = findApplicationById(applicationId);
                    
                    // Update status to ERROR
                    application.setStatus(ApplicationStatus.ERROR);
                    
                    // Add error metadata
                    application.addMetadata("processingError", errorMetadata);
                    
                    // Save the application
                    applicationRepository.save(application);
                    
                    // Send notification
                    Map<String, Object> notificationPayload = new HashMap<>();
                    notificationPayload.put("applicationId", applicationId);
                    notificationPayload.put("errorDetails", errorMetadata);
                    notificationService.sendSystemEventNotification(EventType.APPLICATION_PROCESSING_ERROR, notificationPayload);
                } catch (Exception e) {
                    logger.error("Failed to update application status for error handling", e);
                }
            }
            
            // If there's a document ID, update the document metadata
            if (documentId != null) {
                try {
                    Document document = findDocumentById(documentId);
                    
                    // Add error metadata
                    document.addMetadata("processingError", errorMetadata);
                    
                    // Save the document
                    documentRepository.save(document);
                    
                    // Send notification
                    Map<String, Object> notificationPayload = new HashMap<>();
                    notificationPayload.put("documentId", documentId);
                    notificationPayload.put("errorDetails", errorMetadata);
                    notificationService.sendSystemEventNotification(EventType.DOCUMENT_PROCESSING_ERROR, notificationPayload);
                } catch (Exception e) {
                    logger.error("Failed to update document metadata for error handling", e);
                }
            }
            
            logger.info("Successfully handled processing exception for document ID: {}, application ID: {}", documentId, applicationId);
        } catch (Exception e) {
            String errorMessage = "Failed to handle processing exception";
            logger.error(errorMessage, e);
            // Don't throw another exception here to avoid cascading errors
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Cacheable(value = "applicationDocuments", key = "#applicationId")
    public List<DocumentResponseDTO> getApplicationDocuments(UUID applicationId) throws ProcessingException {
        logger.info("Getting documents for application ID: {}", applicationId);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Get the documents associated with the application
            List<Document> documents = application.getDocuments();
            
            // Convert to DTOs
            List<DocumentResponseDTO> documentDTOs = new ArrayList<>();
            for (Document document : documents) {
                // Generate a secure URL for document access
                String downloadUrl = documentService.generateSecureUrl(document.getId());
                LocalDateTime urlExpiresAt = LocalDateTime.now().plusHours(1); // URL valid for 1 hour
                
                DocumentResponseDTO documentDTO = DocumentResponseDTO.fromEntity(document, downloadUrl, urlExpiresAt);
                documentDTOs.add(documentDTO);
            }
            
            logger.info("Successfully retrieved {} documents for application ID: {}", documentDTOs.size(), applicationId);
            
            return documentDTOs;
        } catch (Exception e) {
            String errorMessage = "Failed to get documents for application ID: " + applicationId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "GET_DOCUMENTS_ERROR", null, applicationId, null);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public ApplicationResponseDTO applyBusinessRules(UUID applicationId) throws ProcessingException {
        logger.info("Applying business rules to application ID: {}", applicationId);
        
        try {
            // Retrieve the application
            Application application = findApplicationById(applicationId);
            
            // Get the merchant details
            MerchantDetails merchantDetails = application.getMerchantDetails();
            
            // Get the documents
            List<Document> documents = application.getDocuments();
            
            // Validate business rules
            ValidationResult validationResult = validationService.validateBusinessRules(application, merchantDetails, documents);
            
            // Determine the appropriate application status based on validation result
            ApplicationStatus newStatus;
            Map<String, Object> statusMetadata = new HashMap<>();
            
            if (validationResult.isValid()) {
                // Check if the application is complete
                ValidationResult completenessResult = validationService.evaluateApplicationCompleteness(application);
                
                if (completenessResult.isValid()) {
                    // Application is complete and valid, determine if it should be approved or rejected
                    ValidationResult approvalResult = validationService.validateApprovalRequirements(application, merchantDetails, documents);
                    
                    if (approvalResult.isValid()) {
                        newStatus = ApplicationStatus.APPROVED;
                    } else {
                        newStatus = ApplicationStatus.REJECTED;
                        statusMetadata.put("rejectionReason", approvalResult.getErrors().toString());
                    }
                } else {
                    // Application is valid but incomplete
                    newStatus = ApplicationStatus.PENDING;
                    statusMetadata.put("pendingReason", completenessResult.getErrors().toString());
                }
            } else if (validationResult.getSeverity() == ValidationSeverity.WARNING) {
                // Application has warnings but can still be processed
                newStatus = ApplicationStatus.EXCEPTION;
                statusMetadata.put("exceptionReason", validationResult.getErrors().toString());
                statusMetadata.put("exceptionSeverity", "WARNING");
            } else {
                // Application has errors that prevent processing
                newStatus = ApplicationStatus.EXCEPTION;
                statusMetadata.put("exceptionReason", validationResult.getErrors().toString());
                statusMetadata.put("exceptionSeverity", "ERROR");
            }
            
            // Update the application status
            return updateApplicationStatus(applicationId, newStatus, statusMetadata);
        } catch (Exception e) {
            String errorMessage = "Failed to apply business rules to application ID: " + applicationId;
            logger.error(errorMessage, e);
            throw new ProcessingException(errorMessage, e, "BUSINESS_RULES_ERROR", null, applicationId, null);
        }
    }

    /**
     * Finds an application by its ID.
     * 
     * @param applicationId The application ID
     * @return The application
     * @throws ProcessingException if the application is not found
     */
    private Application findApplicationById(UUID applicationId) throws ProcessingException {
        return applicationRepository.findById(applicationId)
                .orElseThrow(() -> new ProcessingException(
                        "Application not found with ID: " + applicationId,
                        "APPLICATION_NOT_FOUND",
                        null,
                        applicationId,
                        null));
    }

    /**
     * Finds a document by its ID.
     * 
     * @param documentId The document ID
     * @return The document
     * @throws ProcessingException if the document is not found
     */
    private Document findDocumentById(UUID documentId) throws ProcessingException {
        return documentRepository.findById(documentId)
                .orElseThrow(() -> new ProcessingException(
                        "Document not found with ID: " + documentId,
                        "DOCUMENT_NOT_FOUND",
                        documentId,
                        null,
                        null));
    }

    /**
     * Validates extracted data against the expected schema for the document type.
     * 
     * @param documentType The type of document
     * @param extractedData The data extracted from the document
     * @throws ProcessingException if validation fails
     */
    private void validateExtractedData(DocumentType documentType, Map<String, Object> extractedData) throws ProcessingException {
        // Get confidence scores if available
        Map<String, Double> confidenceScores = new HashMap<>();
        if (extractedData.containsKey("confidenceScores")) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Double> scores = (Map<String, Double>) extractedData.get("confidenceScores");
                confidenceScores = scores;
            } catch (ClassCastException e) {
                logger.warn("Invalid confidence scores format", e);
            }
        }
        
        // Validate the extracted data
        ValidationResult validationResult;
        if (!confidenceScores.isEmpty()) {
            validationResult = validationService.validateExtractedDataWithConfidence(documentType, extractedData, confidenceScores);
        } else {
            validationResult = validationService.validateExtractedData(documentType, extractedData);
        }
        
        // If validation fails, throw an exception
        if (!validationResult.isValid() && validationResult.getSeverity() == ValidationSeverity.ERROR) {
            throw new ProcessingException(
                    "Extracted data validation failed for document type: " + documentType,
                    "VALIDATION_ERROR",
                    null,
                    null,
                    Map.of(
                            "documentType", documentType,
                            "validationErrors", validationResult.getErrors(),
                            "validationSeverity", validationResult.getSeverity()
                    ));
        }
    }

    /**
     * Creates a new application from extracted document data.
     * 
     * @param extractedData The data extracted from the document
     * @return The new application
     */
    private Application createNewApplication(Map<String, Object> extractedData) {
        // Create a new application with initial status
        Application application = new Application(ApplicationStatus.PROCESSING);
        
        // Set creation and update timestamps
        LocalDateTime now = LocalDateTime.now();
        application.setCreatedAt(now);
        application.setUpdatedAt(now);
        
        // Set review status
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        // Add metadata from extracted data
        application.addMetadata("sourceData", extractedData);
        application.addMetadata("processingStarted", now.toString());
        
        // Create merchant details if available in extracted data
        if (extractedData.containsKey("merchantDetails")) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> merchantData = (Map<String, Object>) extractedData.get("merchantDetails");
                
                MerchantDetails merchantDetails = new MerchantDetails();
                merchantDetails.setApplication(application);
                
                // Set merchant details fields from extracted data
                if (merchantData.containsKey("legalName")) {
                    merchantDetails.setLegalName((String) merchantData.get("legalName"));
                }
                
                if (merchantData.containsKey("dbaName")) {
                    merchantDetails.setDbaName((String) merchantData.get("dbaName"));
                }
                
                if (merchantData.containsKey("ein")) {
                    merchantDetails.setEin((String) merchantData.get("ein"));
                }
                
                if (merchantData.containsKey("address")) {
                    merchantDetails.setAddress((String) merchantData.get("address"));
                }
                
                if (merchantData.containsKey("industry")) {
                    merchantDetails.setIndustry((String) merchantData.get("industry"));
                }
                
                if (merchantData.containsKey("revenue")) {
                    try {
                        merchantDetails.setRevenue(Double.parseDouble(merchantData.get("revenue").toString()));
                    } catch (NumberFormatException e) {
                        logger.warn("Invalid revenue format", e);
                    }
                }
                
                application.setMerchantDetails(merchantDetails);
            } catch (ClassCastException e) {
                logger.warn("Invalid merchant details format", e);
            }
        }
        
        return application;
    }

    /**
     * Associates a document with an application.
     * 
     * @param document The document to associate
     * @param application The application to associate with
     */
    private void associateDocumentWithApplication(Document document, Application application) {
        // Set the application ID on the document
        document.setApplicationId(application.getId());
        
        // Add the document to the application's document list
        application.addDocument(document);
        
        // Update document metadata
        document.addMetadata("associatedAt", LocalDateTime.now().toString());
        document.addMetadata("associatedWithApplication", application.getId().toString());
        
        // Save the document
        documentRepository.save(document);
    }

    /**
     * Updates application data based on document content.
     * 
     * @param application The application to update
     * @param documentType The type of document
     * @param extractedData The data extracted from the document
     */
    private void updateApplicationData(Application application, DocumentType documentType, Map<String, Object> extractedData) {
        // Update application metadata with document data
        application.addMetadata("lastDocumentProcessed", documentType.name());
        application.addMetadata("lastDocumentProcessedAt", LocalDateTime.now().toString());
        
        // Update merchant details if available and document type is appropriate
        if (documentType == DocumentType.BUSINESS_LICENSE && extractedData.containsKey("merchantDetails")) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> merchantData = (Map<String, Object>) extractedData.get("merchantDetails");
                
                MerchantDetails merchantDetails = application.getMerchantDetails();
                if (merchantDetails == null) {
                    merchantDetails = new MerchantDetails();
                    merchantDetails.setApplication(application);
                    application.setMerchantDetails(merchantDetails);
                }
                
                // Update merchant details fields from extracted data
                if (merchantData.containsKey("legalName") && (merchantDetails.getLegalName() == null || merchantDetails.getLegalName().isEmpty())) {
                    merchantDetails.setLegalName((String) merchantData.get("legalName"));
                }
                
                if (merchantData.containsKey("dbaName") && (merchantDetails.getDbaName() == null || merchantDetails.getDbaName().isEmpty())) {
                    merchantDetails.setDbaName((String) merchantData.get("dbaName"));
                }
                
                if (merchantData.containsKey("ein") && (merchantDetails.getEin() == null || merchantDetails.getEin().isEmpty())) {
                    merchantDetails.setEin((String) merchantData.get("ein"));
                }
                
                if (merchantData.containsKey("address") && (merchantDetails.getAddress() == null || merchantDetails.getAddress().isEmpty())) {
                    merchantDetails.setAddress((String) merchantData.get("address"));
                }
                
                if (merchantData.containsKey("industry") && (merchantDetails.getIndustry() == null || merchantDetails.getIndustry().isEmpty())) {
                    merchantDetails.setIndustry((String) merchantData.get("industry"));
                }
                
                if (merchantData.containsKey("revenue") && merchantDetails.getRevenue() == null) {
                    try {
                        merchantDetails.setRevenue(Double.parseDouble(merchantData.get("revenue").toString()));
                    } catch (NumberFormatException e) {
                        logger.warn("Invalid revenue format", e);
                    }
                }
            } catch (ClassCastException e) {
                logger.warn("Invalid merchant details format", e);
            }
        }
        
        // Update application metadata with document-specific data
        switch (documentType) {
            case BANK_STATEMENT:
                updateBankStatementData(application, extractedData);
                break;
            case TAX_RETURN:
                updateTaxReturnData(application, extractedData);
                break;
            case BUSINESS_LICENSE:
                updateBusinessLicenseData(application, extractedData);
                break;
            case ID_VERIFICATION:
                updateIdVerificationData(application, extractedData);
                break;
            default:
                // For other document types, just store the extracted data
                application.addMetadata("extractedData_" + documentType.name(), extractedData);
        }
        
        // Update the application's update timestamp
        application.setUpdatedAt(LocalDateTime.now());
    }

    /**
     * Updates application data with bank statement information.
     * 
     * @param application The application to update
     * @param extractedData The data extracted from the bank statement
     */
    private void updateBankStatementData(Application application, Map<String, Object> extractedData) {
        Map<String, Object> bankData = new HashMap<>();
        
        // Extract relevant fields from the bank statement
        if (extractedData.containsKey("accountNumber")) {
            bankData.put("accountNumber", extractedData.get("accountNumber"));
        }
        
        if (extractedData.containsKey("bankName")) {
            bankData.put("bankName", extractedData.get("bankName"));
        }
        
        if (extractedData.containsKey("statementDate")) {
            bankData.put("statementDate", extractedData.get("statementDate"));
        }
        
        if (extractedData.containsKey("balance")) {
            bankData.put("balance", extractedData.get("balance"));
        }
        
        if (extractedData.containsKey("averageBalance")) {
            bankData.put("averageBalance", extractedData.get("averageBalance"));
        }
        
        if (extractedData.containsKey("transactions")) {
            bankData.put("transactions", extractedData.get("transactions"));
        }
        
        // Add the bank data to the application metadata
        application.addMetadata("bankStatementData", bankData);
    }

    /**
     * Updates application data with tax return information.
     * 
     * @param application The application to update
     * @param extractedData The data extracted from the tax return
     */
    private void updateTaxReturnData(Application application, Map<String, Object> extractedData) {
        Map<String, Object> taxData = new HashMap<>();
        
        // Extract relevant fields from the tax return
        if (extractedData.containsKey("taxYear")) {
            taxData.put("taxYear", extractedData.get("taxYear"));
        }
        
        if (extractedData.containsKey("ein")) {
            taxData.put("ein", extractedData.get("ein"));
        }
        
        if (extractedData.containsKey("grossIncome")) {
            taxData.put("grossIncome", extractedData.get("grossIncome"));
        }
        
        if (extractedData.containsKey("netIncome")) {
            taxData.put("netIncome", extractedData.get("netIncome"));
        }
        
        if (extractedData.containsKey("taxesPaid")) {
            taxData.put("taxesPaid", extractedData.get("taxesPaid"));
        }
        
        // Add the tax data to the application metadata
        application.addMetadata("taxReturnData", taxData);
    }

    /**
     * Updates application data with business license information.
     * 
     * @param application The application to update
     * @param extractedData The data extracted from the business license
     */
    private void updateBusinessLicenseData(Application application, Map<String, Object> extractedData) {
        Map<String, Object> licenseData = new HashMap<>();
        
        // Extract relevant fields from the business license
        if (extractedData.containsKey("licenseNumber")) {
            licenseData.put("licenseNumber", extractedData.get("licenseNumber"));
        }
        
        if (extractedData.containsKey("issueDate")) {
            licenseData.put("issueDate", extractedData.get("issueDate"));
        }
        
        if (extractedData.containsKey("expirationDate")) {
            licenseData.put("expirationDate", extractedData.get("expirationDate"));
        }
        
        if (extractedData.containsKey("businessType")) {
            licenseData.put("businessType", extractedData.get("businessType"));
        }
        
        if (extractedData.containsKey("issuingAuthority")) {
            licenseData.put("issuingAuthority", extractedData.get("issuingAuthority"));
        }
        
        // Add the license data to the application metadata
        application.addMetadata("businessLicenseData", licenseData);
    }

    /**
     * Updates application data with ID verification information.
     * 
     * @param application The application to update
     * @param extractedData The data extracted from the ID verification document
     */
    private void updateIdVerificationData(Application application, Map<String, Object> extractedData) {
        Map<String, Object> idData = new HashMap<>();
        
        // Extract relevant fields from the ID verification document
        if (extractedData.containsKey("idType")) {
            idData.put("idType", extractedData.get("idType"));
        }
        
        if (extractedData.containsKey("idNumber")) {
            idData.put("idNumber", extractedData.get("idNumber"));
        }
        
        if (extractedData.containsKey("name")) {
            idData.put("name", extractedData.get("name"));
        }
        
        if (extractedData.containsKey("address")) {
            idData.put("address", extractedData.get("address"));
        }
        
        if (extractedData.containsKey("dateOfBirth")) {
            idData.put("dateOfBirth", extractedData.get("dateOfBirth"));
        }
        
        if (extractedData.containsKey("expirationDate")) {
            idData.put("expirationDate", extractedData.get("expirationDate"));
        }
        
        // Add the ID data to the application metadata
        application.addMetadata("idVerificationData", idData);
    }

    /**
     * Calculates and stores the processing time for an application.
     * 
     * @param application The application to calculate processing time for
     */
    private void calculateAndStoreProcessingTime(Application application) {
        LocalDateTime createdAt = application.getCreatedAt();
        LocalDateTime completedAt = LocalDateTime.now();
        
        // Calculate processing time in milliseconds
        long processingTimeMillis = Duration.between(createdAt, completedAt).toMillis();
        
        // Store processing time in metadata
        application.addMetadata("processingTimeMillis", processingTimeMillis);
        application.addMetadata("processingTimeMinutes", processingTimeMillis / 60000.0);
        application.addMetadata("completedAt", completedAt.toString());
        
        // Check if processing time meets the target
        boolean meetsTarget = processingTimeMillis < (TARGET_PROCESSING_MINUTES * 60000);
        application.addMetadata("processedWithinTarget", meetsTarget);
        
        logger.info("Application ID: {} processing time: {} ms ({} minutes)", 
                application.getId(), processingTimeMillis, processingTimeMillis / 60000.0);
    }

    /**
     * Finds an application based on document metadata.
     * This method attempts to match a document with an existing application
     * based on identifying information in the extracted data.
     * 
     * @param extractedData The data extracted from the document
     * @return An optional containing the matching application, or empty if no match is found
     */
    private Optional<Application> findApplicationByDocumentMetadata(Map<String, Object> extractedData) {
        // Check if the extracted data contains merchant details
        if (!extractedData.containsKey("merchantDetails")) {
            return Optional.empty();
        }
        
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> merchantData = (Map<String, Object>) extractedData.get("merchantDetails");
            
            // Try to match by EIN if available
            if (merchantData.containsKey("ein")) {
                String ein = (String) merchantData.get("ein");
                if (ein != null && !ein.isEmpty()) {
                    List<Application> applications = applicationRepository.findByMerchantDetailsEin(ein);
                    if (!applications.isEmpty()) {
                        // Return the most recently updated application
                        return applications.stream()
                                .max((a1, a2) -> a1.getUpdatedAt().compareTo(a2.getUpdatedAt()));
                    }
                }
            }
            
            // Try to match by legal name if available
            if (merchantData.containsKey("legalName")) {
                String legalName = (String) merchantData.get("legalName");
                if (legalName != null && !legalName.isEmpty()) {
                    List<Application> applications = applicationRepository.findByMerchantDetailsLegalName(legalName);
                    if (!applications.isEmpty()) {
                        // Return the most recently updated application
                        return applications.stream()
                                .max((a1, a2) -> a1.getUpdatedAt().compareTo(a2.getUpdatedAt()));
                    }
                }
            }
            
            // Try to match by DBA name if available
            if (merchantData.containsKey("dbaName")) {
                String dbaName = (String) merchantData.get("dbaName");
                if (dbaName != null && !dbaName.isEmpty()) {
                    List<Application> applications = applicationRepository.findByMerchantDetailsDbaName(dbaName);
                    if (!applications.isEmpty()) {
                        // Return the most recently updated application
                        return applications.stream()
                                .max((a1, a2) -> a1.getUpdatedAt().compareTo(a2.getUpdatedAt()));
                    }
                }
            }
        } catch (ClassCastException e) {
            logger.warn("Invalid merchant details format", e);
        }
        
        return Optional.empty();
    }
}