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

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

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
    
    private final ApplicationRepository applicationRepository;
    private final DocumentRepository documentRepository;
    private final MerchantDetailsRepository merchantDetailsRepository;
    private final ValidationService validationService;
    private final DocumentService documentService;
    private final NotificationService notificationService;
    
    /**
     * Confidence threshold for document classification and field extraction.
     * Fields with confidence below this threshold will be flagged for review.
     */
    private static final double CONFIDENCE_THRESHOLD = 75.0;
    
    /**
     * Constructor with required dependencies.
     * 
     * @param applicationRepository Repository for Application entities
     * @param documentRepository Repository for Document entities
     * @param merchantDetailsRepository Repository for MerchantDetails entities
     * @param validationService Service for data validation and business rule application
     * @param documentService Service for document management
     * @param notificationService Service for notification delivery
     */
    @Autowired
    public ProcessingServiceImpl(ApplicationRepository applicationRepository,
                               DocumentRepository documentRepository,
                               MerchantDetailsRepository merchantDetailsRepository,
                               ValidationService validationService,
                               DocumentService documentService,
                               NotificationService notificationService) {
        this.applicationRepository = applicationRepository;
        this.documentRepository = documentRepository;
        this.merchantDetailsRepository = merchantDetailsRepository;
        this.validationService = validationService;
        this.documentService = documentService;
        this.notificationService = notificationService;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public String processNewApplication(DocumentProcessingMessage message) {
        logger.info("Processing new application from document: {}", message.getDocumentId());
        
        // Validate the message
        validateProcessingMessage(message);
        
        // Check if the document type is valid for creating a new application
        if (message.getDocumentType() != DocumentProcessingMessage.DocumentType.APPLICATION_FORM) {
            throw new ValidationException("Cannot create new application from document type: " + message.getDocumentType());
        }
        
        // Create a new application
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        // Extract metadata from the document
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("creation_timestamp", LocalDateTime.now().toString());
        metadata.put("document_id", message.getDocumentId());
        metadata.put("classification_confidence", message.getClassificationConfidence());
        
        // Add any low confidence fields to metadata for review
        Map<String, Object> lowConfidenceFields = new HashMap<>();
        message.getExtractedFields().forEach((fieldName, field) -> {
            if (field.getConfidence() < CONFIDENCE_THRESHOLD) {
                lowConfidenceFields.put(fieldName, field.getValue());
            }
        });
        
        if (!lowConfidenceFields.isEmpty()) {
            metadata.put("low_confidence_fields", lowConfidenceFields);
        }
        
        application.setMetadata(metadata);
        
        // Save the application
        application = applicationRepository.save(application);
        logger.info("Created new application with ID: {}", application.getId());
        
        // Create and associate the document
        Document document = createDocumentFromMessage(message, application);
        
        // Create merchant details if available in the document
        createMerchantDetailsIfAvailable(message, application);
        
        // Validate the application data
        boolean isValid = validationService.validateApplication(application.getId());
        
        // Update application status based on validation
        if (isValid) {
            updateApplicationStatus(application.getId(), ApplicationStatus.PENDING.name(), "Initial validation passed");
        } else {
            updateApplicationStatus(application.getId(), ApplicationStatus.PENDING.name(), "Needs additional information");
        }
        
        // Evaluate completeness
        evaluateApplicationCompleteness(application.getId());
        
        // Send notification
        notificationService.sendApplicationStatusNotification(application.getId(), ApplicationStatus.NEW.name());
        
        return application.getId();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public String updateExistingApplication(DocumentProcessingMessage message) {
        logger.info("Updating existing application: {} with document: {}", 
                message.getApplicationId(), message.getDocumentId());
        
        // Validate the message
        validateProcessingMessage(message);
        
        // Check if application ID is provided
        if (message.getApplicationId() == null || message.getApplicationId().isEmpty()) {
            throw new ValidationException("Application ID is required for updating an existing application");
        }
        
        // Find the application
        Application application = applicationRepository.findById(message.getApplicationId())
                .orElseThrow(() -> new ResourceNotFoundException("Application not found with ID: " + message.getApplicationId()));
        
        // Create and associate the document
        Document document = createDocumentFromMessage(message, application);
        
        // Update application metadata
        Map<String, Object> metadata = application.getMetadata();
        if (metadata == null) {
            metadata = new HashMap<>();
        }
        
        // Add document to the list of associated documents
        @SuppressWarnings("unchecked")
        List<String> documentIds = (List<String>) metadata.getOrDefault("document_ids", new java.util.ArrayList<String>());
        documentIds.add(document.getId());
        metadata.put("document_ids", documentIds);
        
        // Add last update information
        metadata.put("last_updated_timestamp", LocalDateTime.now().toString());
        metadata.put("last_document_id", message.getDocumentId());
        
        // Add any low confidence fields to metadata for review
        Map<String, Object> lowConfidenceFields = new HashMap<>();
        message.getExtractedFields().forEach((fieldName, field) -> {
            if (field.getConfidence() < CONFIDENCE_THRESHOLD) {
                lowConfidenceFields.put(fieldName, field.getValue());
            }
        });
        
        if (!lowConfidenceFields.isEmpty()) {
            metadata.put("low_confidence_fields", lowConfidenceFields);
        }
        
        application.setMetadata(metadata);
        
        // Update merchant details if available in the document
        updateMerchantDetailsIfAvailable(message, application);
        
        // Save the updated application
        application = applicationRepository.save(application);
        
        // Validate the application data
        boolean isValid = validationService.validateApplication(application.getId());
        
        // Evaluate completeness
        boolean isComplete = evaluateApplicationCompleteness(application.getId());
        
        // Update application status based on validation and completeness
        if (isComplete && isValid) {
            updateApplicationStatus(application.getId(), ApplicationStatus.PROCESSING.name(), "Application complete and valid");
        } else if (!isValid) {
            updateApplicationStatus(application.getId(), ApplicationStatus.PENDING.name(), "Validation failed");
        }
        
        // Send notification
        notificationService.sendApplicationStatusNotification(application.getId(), application.getStatus().name());
        
        return application.getId();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public String processSupportingDocument(DocumentProcessingMessage message) {
        logger.info("Processing supporting document: {} for application: {}", 
                message.getDocumentId(), message.getApplicationId());
        
        // Validate the message
        validateProcessingMessage(message);
        
        // Check if application ID is provided
        if (message.getApplicationId() == null || message.getApplicationId().isEmpty()) {
            throw new ValidationException("Application ID is required for processing a supporting document");
        }
        
        // Find the application
        Application application = applicationRepository.findById(message.getApplicationId())
                .orElseThrow(() -> new ResourceNotFoundException("Application not found with ID: " + message.getApplicationId()));
        
        // Create and associate the document
        Document document = createDocumentFromMessage(message, application);
        
        // Update application metadata
        Map<String, Object> metadata = application.getMetadata();
        if (metadata == null) {
            metadata = new HashMap<>();
        }
        
        // Add document to the list of associated documents
        @SuppressWarnings("unchecked")
        List<String> documentIds = (List<String>) metadata.getOrDefault("document_ids", new java.util.ArrayList<String>());
        documentIds.add(document.getId());
        metadata.put("document_ids", documentIds);
        
        // Add last update information
        metadata.put("last_updated_timestamp", LocalDateTime.now().toString());
        metadata.put("last_document_id", message.getDocumentId());
        
        application.setMetadata(metadata);
        
        // Save the updated application
        application = applicationRepository.save(application);
        
        // Evaluate completeness
        boolean isComplete = evaluateApplicationCompleteness(application.getId());
        
        // Update application status if complete
        if (isComplete && application.getStatus() == ApplicationStatus.PENDING) {
            updateApplicationStatus(application.getId(), ApplicationStatus.PROCESSING.name(), "Application complete with supporting documents");
            
            // Send notification
            notificationService.sendApplicationStatusNotification(application.getId(), ApplicationStatus.PROCESSING.name());
        }
        
        return application.getId();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public boolean evaluateApplicationCompleteness(String applicationId) {
        logger.info("Evaluating completeness of application: {}", applicationId);
        
        // Find the application
        Application application = applicationRepository.findById(applicationId)
                .orElseThrow(() -> new ResourceNotFoundException("Application not found with ID: " + applicationId));
        
        // Find all documents associated with the application
        List<Document> documents = documentRepository.findByApplicationId(applicationId);
        
        // Check if application form exists
        boolean hasApplicationForm = documents.stream()
                .anyMatch(doc -> doc.getType() == DocumentType.APPLICATION_FORM);
        
        if (!hasApplicationForm) {
            logger.info("Application {} is incomplete: Missing application form", applicationId);
            return false;
        }
        
        // Check if merchant details exist
        Optional<MerchantDetails> merchantDetails = merchantDetailsRepository.findByApplicationId(applicationId);
        if (!merchantDetails.isPresent()) {
            logger.info("Application {} is incomplete: Missing merchant details", applicationId);
            return false;
        }
        
        // Check for required supporting documents based on business rules
        // This is a simplified example - actual implementation would have more complex rules
        boolean hasIdentityDocument = documents.stream()
                .anyMatch(doc -> doc.getType() == DocumentType.IDENTITY_DOCUMENT);
                
        boolean hasBankStatement = documents.stream()
                .anyMatch(doc -> doc.getType() == DocumentType.BANK_STATEMENT);
                
        boolean hasTaxReturn = documents.stream()
                .anyMatch(doc -> doc.getType() == DocumentType.TAX_RETURN);
        
        boolean isComplete = hasIdentityDocument && hasBankStatement && hasTaxReturn;
        
        // Update application metadata with completeness status
        Map<String, Object> metadata = application.getMetadata();
        if (metadata == null) {
            metadata = new HashMap<>();
        }
        
        metadata.put("completeness_status", isComplete ? "complete" : "incomplete");
        metadata.put("completeness_timestamp", LocalDateTime.now().toString());
        metadata.put("missing_documents", new HashMap<String, Boolean>() {{
            put("identity_document", !hasIdentityDocument);
            put("bank_statement", !hasBankStatement);
            put("tax_return", !hasTaxReturn);
        }});
        
        application.setMetadata(metadata);
        applicationRepository.save(application);
        
        logger.info("Application {} completeness evaluation result: {}", applicationId, isComplete);
        return isComplete;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public boolean updateApplicationStatus(String applicationId, String status, String reason) {
        logger.info("Updating status of application: {} to {} with reason: {}", applicationId, status, reason);
        
        // Find the application
        Application application = applicationRepository.findById(applicationId)
                .orElseThrow(() -> new ResourceNotFoundException("Application not found with ID: " + applicationId));
        
        // Validate the status
        ApplicationStatus newStatus;
        try {
            newStatus = ApplicationStatus.valueOf(status);
        } catch (IllegalArgumentException e) {
            throw new ValidationException("Invalid application status: " + status);
        }
        
        // Check if the status transition is valid
        validateStatusTransition(application.getStatus(), newStatus);
        
        // Update the status
        application.setStatus(newStatus);
        
        // Update metadata with status change history
        Map<String, Object> metadata = application.getMetadata();
        if (metadata == null) {
            metadata = new HashMap<>();
        }
        
        @SuppressWarnings("unchecked")
        List<Map<String, String>> statusHistory = (List<Map<String, String>>) 
                metadata.getOrDefault("status_history", new java.util.ArrayList<Map<String, String>>());
        
        Map<String, String> statusChange = new HashMap<>();
        statusChange.put("from", application.getStatus().name());
        statusChange.put("to", newStatus.name());
        statusChange.put("timestamp", LocalDateTime.now().toString());
        statusChange.put("reason", reason);
        
        statusHistory.add(statusChange);
        metadata.put("status_history", statusHistory);
        
        application.setMetadata(metadata);
        
        // Save the updated application
        applicationRepository.save(application);
        
        // Send notification about status change
        notificationService.sendApplicationStatusNotification(applicationId, newStatus.name());
        
        logger.info("Successfully updated status of application: {} to {}", applicationId, newStatus);
        return true;
    }
    
    /**
     * Validates a document processing message for required fields and data integrity.
     * 
     * @param message The document processing message to validate
     * @throws ValidationException if the message is invalid
     */
    private void validateProcessingMessage(DocumentProcessingMessage message) {
        if (message == null) {
            throw new ValidationException("Document processing message cannot be null");
        }
        
        if (message.getDocumentId() == null || message.getDocumentId().isEmpty()) {
            throw new ValidationException("Document ID is required");
        }
        
        if (message.getDocumentType() == null) {
            throw new ValidationException("Document type is required");
        }
        
        if (message.getClassification() == null || message.getClassification().isEmpty()) {
            throw new ValidationException("Document classification is required");
        }
        
        if (message.getProcessingAction() == null) {
            throw new ValidationException("Processing action is required");
        }
        
        if (message.getExtractedFields() == null || message.getExtractedFields().isEmpty()) {
            throw new ValidationException("Extracted fields are required");
        }
    }
    
    /**
     * Creates a Document entity from a document processing message and associates it with an application.
     * 
     * @param message The document processing message containing document data
     * @param application The application to associate the document with
     * @return The created Document entity
     */
    private Document createDocumentFromMessage(DocumentProcessingMessage message, Application application) {
        try {
            // Convert DocumentProcessingMessage.DocumentType to entity.DocumentType
            DocumentType documentType = mapDocumentType(message.getDocumentType());
            
            // Create document metadata
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("classification_confidence", message.getClassificationConfidence());
            metadata.put("processing_time_ms", message.getProcessingMetadata() != null ? 
                    message.getProcessingMetadata().getProcessingTimeMs() : null);
            metadata.put("ocr_engine", message.getProcessingMetadata() != null ? 
                    message.getProcessingMetadata().getOcrEngine() : null);
            metadata.put("extracted_field_count", message.getExtractedFields().size());
            
            // Add low confidence fields to metadata
            Map<String, Object> lowConfidenceFields = new HashMap<>();
            message.getExtractedFields().forEach((fieldName, field) -> {
                if (field.getConfidence() < CONFIDENCE_THRESHOLD) {
                    lowConfidenceFields.put(fieldName, Map.of(
                            "value", field.getValue(),
                            "confidence", field.getConfidence()
                    ));
                }
            });
            
            if (!lowConfidenceFields.isEmpty()) {
                metadata.put("low_confidence_fields", lowConfidenceFields);
            }
            
            // Create the document
            Document document = new Document();
            document.setId(UUID.randomUUID().toString());
            document.setApplication(application);
            document.setType(documentType);
            document.setClassification(message.getClassification());
            document.setStoragePath(message.getStoragePath());
            document.setUploadedAt(message.getTimestamp());
            document.setMetadata(metadata);
            
            // Save the document
            document = documentRepository.save(document);
            logger.info("Created document with ID: {} for application: {}", document.getId(), application.getId());
            
            return document;
        } catch (Exception e) {
            throw new DocumentProcessingException("Failed to create document from message", e);
        }
    }
    
    /**
     * Maps DocumentProcessingMessage.DocumentType to entity.DocumentType.
     * 
     * @param messageType The document type from the processing message
     * @return The corresponding entity document type
     */
    private DocumentType mapDocumentType(DocumentProcessingMessage.DocumentType messageType) {
        switch (messageType) {
            case APPLICATION_FORM:
                return DocumentType.APPLICATION_FORM;
            case BANK_STATEMENT:
                return DocumentType.BANK_STATEMENT;
            case TAX_RETURN:
                return DocumentType.TAX_RETURN;
            case IDENTITY_DOCUMENT:
                return DocumentType.ID_VERIFICATION;
            case BUSINESS_LICENSE:
                return DocumentType.BUSINESS_LICENSE;
            case CREDIT_CARD_STATEMENT:
            case INVOICE:
            case UTILITY_BILL:
            case LEASE_AGREEMENT:
                return DocumentType.MISCELLANEOUS;
            default:
                return DocumentType.MISCELLANEOUS;
        }
    }
    
    /**
     * Creates merchant details from document data if available.
     * 
     * @param message The document processing message containing extracted data
     * @param application The application to associate the merchant details with
     */
    private void createMerchantDetailsIfAvailable(DocumentProcessingMessage message, Application application) {
        // Check if we have the necessary fields for merchant details
        Map<String, DocumentProcessingMessage.ExtractedField> fields = message.getExtractedFields();
        
        boolean hasMerchantData = fields.containsKey("legal_name") || 
                                 fields.containsKey("dba_name") || 
                                 fields.containsKey("ein");
        
        if (!hasMerchantData) {
            logger.info("No merchant data available in document: {}", message.getDocumentId());
            return;
        }
        
        try {
            // Create merchant details
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setId(UUID.randomUUID().toString());
            merchantDetails.setApplication(application);
            
            // Set fields if available
            if (fields.containsKey("legal_name")) {
                merchantDetails.setLegalName(fields.get("legal_name").getValue().toString());
            }
            
            if (fields.containsKey("dba_name")) {
                merchantDetails.setDbaName(fields.get("dba_name").getValue().toString());
            }
            
            if (fields.containsKey("ein")) {
                merchantDetails.setEin(fields.get("ein").getValue().toString());
            }
            
            // Handle address as a complex object
            Map<String, String> address = new HashMap<>();
            if (fields.containsKey("address_line1")) {
                address.put("line1", fields.get("address_line1").getValue().toString());
            }
            
            if (fields.containsKey("address_line2")) {
                address.put("line2", fields.get("address_line2").getValue().toString());
            }
            
            if (fields.containsKey("city")) {
                address.put("city", fields.get("city").getValue().toString());
            }
            
            if (fields.containsKey("state")) {
                address.put("state", fields.get("state").getValue().toString());
            }
            
            if (fields.containsKey("zip_code")) {
                address.put("zip", fields.get("zip_code").getValue().toString());
            }
            
            if (!address.isEmpty()) {
                merchantDetails.setAddress(address);
            }
            
            if (fields.containsKey("industry")) {
                merchantDetails.setIndustry(fields.get("industry").getValue().toString());
            }
            
            if (fields.containsKey("annual_revenue")) {
                Object revenueObj = fields.get("annual_revenue").getValue();
                if (revenueObj instanceof Number) {
                    merchantDetails.setRevenue(((Number) revenueObj).doubleValue());
                } else if (revenueObj instanceof String) {
                    try {
                        // Remove any non-numeric characters except decimal point
                        String revenueStr = ((String) revenueObj).replaceAll("[^\\d.]", "");
                        merchantDetails.setRevenue(Double.parseDouble(revenueStr));
                    } catch (NumberFormatException e) {
                        logger.warn("Could not parse revenue value: {}", revenueObj);
                    }
                }
            }
            
            // Save the merchant details
            merchantDetailsRepository.save(merchantDetails);
            logger.info("Created merchant details for application: {}", application.getId());
            
        } catch (Exception e) {
            logger.error("Failed to create merchant details from document data", e);
            // Don't throw exception here, as we can still proceed with application processing
        }
    }
    
    /**
     * Updates merchant details from document data if available.
     * 
     * @param message The document processing message containing extracted data
     * @param application The application associated with the merchant details
     */
    private void updateMerchantDetailsIfAvailable(DocumentProcessingMessage message, Application application) {
        // Check if we have the necessary fields for merchant details
        Map<String, DocumentProcessingMessage.ExtractedField> fields = message.getExtractedFields();
        
        boolean hasMerchantData = fields.containsKey("legal_name") || 
                                 fields.containsKey("dba_name") || 
                                 fields.containsKey("ein") ||
                                 fields.containsKey("address_line1") ||
                                 fields.containsKey("industry") ||
                                 fields.containsKey("annual_revenue");
        
        if (!hasMerchantData) {
            logger.info("No merchant data available in document: {}", message.getDocumentId());
            return;
        }
        
        try {
            // Find existing merchant details or create new ones
            MerchantDetails merchantDetails = merchantDetailsRepository.findByApplicationId(application.getId())
                    .orElseGet(() -> {
                        MerchantDetails newDetails = new MerchantDetails();
                        newDetails.setId(UUID.randomUUID().toString());
                        newDetails.setApplication(application);
                        return newDetails;
                    });
            
            // Update fields if available and if confidence is high enough
            if (fields.containsKey("legal_name") && 
                    fields.get("legal_name").getConfidence() >= CONFIDENCE_THRESHOLD) {
                merchantDetails.setLegalName(fields.get("legal_name").getValue().toString());
            }
            
            if (fields.containsKey("dba_name") && 
                    fields.get("dba_name").getConfidence() >= CONFIDENCE_THRESHOLD) {
                merchantDetails.setDbaName(fields.get("dba_name").getValue().toString());
            }
            
            if (fields.containsKey("ein") && 
                    fields.get("ein").getConfidence() >= CONFIDENCE_THRESHOLD) {
                merchantDetails.setEin(fields.get("ein").getValue().toString());
            }
            
            // Handle address as a complex object
            Map<String, String> address = merchantDetails.getAddress();
            if (address == null) {
                address = new HashMap<>();
            }
            
            boolean addressUpdated = false;
            
            if (fields.containsKey("address_line1") && 
                    fields.get("address_line1").getConfidence() >= CONFIDENCE_THRESHOLD) {
                address.put("line1", fields.get("address_line1").getValue().toString());
                addressUpdated = true;
            }
            
            if (fields.containsKey("address_line2") && 
                    fields.get("address_line2").getConfidence() >= CONFIDENCE_THRESHOLD) {
                address.put("line2", fields.get("address_line2").getValue().toString());
                addressUpdated = true;
            }
            
            if (fields.containsKey("city") && 
                    fields.get("city").getConfidence() >= CONFIDENCE_THRESHOLD) {
                address.put("city", fields.get("city").getValue().toString());
                addressUpdated = true;
            }
            
            if (fields.containsKey("state") && 
                    fields.get("state").getConfidence() >= CONFIDENCE_THRESHOLD) {
                address.put("state", fields.get("state").getValue().toString());
                addressUpdated = true;
            }
            
            if (fields.containsKey("zip_code") && 
                    fields.get("zip_code").getConfidence() >= CONFIDENCE_THRESHOLD) {
                address.put("zip", fields.get("zip_code").getValue().toString());
                addressUpdated = true;
            }
            
            if (addressUpdated) {
                merchantDetails.setAddress(address);
            }
            
            if (fields.containsKey("industry") && 
                    fields.get("industry").getConfidence() >= CONFIDENCE_THRESHOLD) {
                merchantDetails.setIndustry(fields.get("industry").getValue().toString());
            }
            
            if (fields.containsKey("annual_revenue") && 
                    fields.get("annual_revenue").getConfidence() >= CONFIDENCE_THRESHOLD) {
                Object revenueObj = fields.get("annual_revenue").getValue();
                if (revenueObj instanceof Number) {
                    merchantDetails.setRevenue(((Number) revenueObj).doubleValue());
                } else if (revenueObj instanceof String) {
                    try {
                        // Remove any non-numeric characters except decimal point
                        String revenueStr = ((String) revenueObj).replaceAll("[^\\d.]", "");
                        merchantDetails.setRevenue(Double.parseDouble(revenueStr));
                    } catch (NumberFormatException e) {
                        logger.warn("Could not parse revenue value: {}", revenueObj);
                    }
                }
            }
            
            // Save the updated merchant details
            merchantDetailsRepository.save(merchantDetails);
            logger.info("Updated merchant details for application: {}", application.getId());
            
        } catch (Exception e) {
            logger.error("Failed to update merchant details from document data", e);
            // Don't throw exception here, as we can still proceed with application processing
        }
    }
    
    /**
     * Validates if a status transition is allowed based on business rules.
     * 
     * @param currentStatus The current application status
     * @param newStatus The new application status
     * @throws BusinessRuleException if the transition is not allowed
     */
    private void validateStatusTransition(ApplicationStatus currentStatus, ApplicationStatus newStatus) {
        // Define valid transitions
        boolean isValid = false;
        
        switch (currentStatus) {
            case NEW:
                // NEW can transition to PENDING or REJECTED
                isValid = newStatus == ApplicationStatus.PENDING || 
                          newStatus == ApplicationStatus.REJECTED;
                break;
                
            case PENDING:
                // PENDING can transition to PROCESSING, REJECTED, or back to NEW
                isValid = newStatus == ApplicationStatus.PROCESSING || 
                          newStatus == ApplicationStatus.REJECTED || 
                          newStatus == ApplicationStatus.NEW;
                break;
                
            case PROCESSING:
                // PROCESSING can transition to APPROVED, REJECTED, or back to PENDING
                isValid = newStatus == ApplicationStatus.APPROVED || 
                          newStatus == ApplicationStatus.REJECTED || 
                          newStatus == ApplicationStatus.PENDING;
                break;
                
            case APPROVED:
                // APPROVED can transition to COMPLETED or back to PROCESSING
                isValid = newStatus == ApplicationStatus.COMPLETED || 
                          newStatus == ApplicationStatus.PROCESSING;
                break;
                
            case REJECTED:
                // REJECTED is a terminal state, but can go back to PENDING for reconsideration
                isValid = newStatus == ApplicationStatus.PENDING;
                break;
                
            case COMPLETED:
                // COMPLETED is a terminal state
                isValid = false;
                break;
        }
        
        if (!isValid) {
            throw new BusinessRuleException("Invalid status transition from " + 
                    currentStatus + " to " + newStatus);
        }
    }
}