package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ApplicationNotFoundException;
import com.dollarfunding.mca.exception.InvalidApplicationStateException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.service.ValidationService.ValidationResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.Caching;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Implementation of the ApplicationService interface that manages the core business logic
 * for MCA applications. It handles CRUD operations, status updates, validation, and processing
 * workflows for applications.
 * 
 * This class interacts with ApplicationRepository for data persistence, ValidationService for
 * business rule validation, and NotificationService for status updates. It implements transaction
 * management to ensure data consistency across operations.
 */
@Service
public class ApplicationServiceImpl implements ApplicationService {

    private static final Logger logger = LoggerFactory.getLogger(ApplicationServiceImpl.class);
    
    private final ApplicationRepository applicationRepository;
    private final ValidationService validationService;
    private final NotificationService notificationService;
    
    /**
     * Constructor with required dependencies.
     * 
     * @param applicationRepository Repository for application data persistence
     * @param validationService Service for validating application data
     * @param notificationService Service for sending notifications about application events
     */
    @Autowired
    public ApplicationServiceImpl(ApplicationRepository applicationRepository,
                                 ValidationService validationService,
                                 NotificationService notificationService) {
        this.applicationRepository = applicationRepository;
        this.validationService = validationService;
        this.notificationService = notificationService;
    }
    
    /**
     * Creates a new application with the provided data.
     * 
     * @param applicationDTO The application data to create
     * @return The created application
     * @throws ValidationException if the application data is invalid
     */
    @Override
    @Transactional
    public Application createApplication(ApplicationRequestDTO applicationDTO) {
        logger.info("Creating new application");
        
        // Validate application data
        ValidationResult validationResult = validationService.validateApplicationData(applicationDTO);
        if (!validationResult.isValid()) {
            logger.warn("Application data validation failed: {}", validationResult.getErrors());
            throw new ValidationException("Invalid application data", validationResult.getErrors());
        }
        
        // Create new application entity
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        // Set metadata from DTO
        Map<String, Object> metadata = new HashMap<>();
        if (applicationDTO.getMetadata() != null) {
            metadata.putAll(applicationDTO.getMetadata());
        }
        
        // Add processing metadata
        metadata.put("source", "api");
        metadata.put("processingStartTime", LocalDateTime.now().toString());
        application.setMetadata(metadata);
        
        // Save application
        application = applicationRepository.save(application);
        logger.info("Created new application with ID: {}", application.getId());
        
        // Send notification
        notificationService.sendApplicationCreatedNotification(application);
        
        return application;
    }
    
    /**
     * Retrieves an application by its ID.
     * 
     * @param id The application ID
     * @return The application
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(value = "applications", key = "#id")
    public Application getApplicationById(UUID id) {
        logger.debug("Retrieving application with ID: {}", id);
        return applicationRepository.findById(id)
                .orElseThrow(() -> {
                    logger.warn("Application not found with ID: {}", id);
                    return new ApplicationNotFoundException("Application not found with ID: " + id);
                });
    }
    
    /**
     * Retrieves all applications with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getAllApplications(Pageable pageable) {
        logger.debug("Retrieving all applications with pagination: {}", pageable);
        return applicationRepository.findAll(pageable);
    }
    
    /**
     * Retrieves applications by status with pagination.
     * 
     * @param status The application status to filter by
     * @param pageable The pagination information
     * @return Page of applications with the specified status
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsByStatus(ApplicationStatus status, Pageable pageable) {
        logger.debug("Retrieving applications with status: {} and pagination: {}", status, pageable);
        return applicationRepository.findByStatus(status, pageable);
    }
    
    /**
     * Retrieves applications by review status with pagination.
     * 
     * @param reviewStatus The review status to filter by
     * @param pageable The pagination information
     * @return Page of applications with the specified review status
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsByReviewStatus(ReviewStatus reviewStatus, Pageable pageable) {
        logger.debug("Retrieving applications with review status: {} and pagination: {}", reviewStatus, pageable);
        return applicationRepository.findByReviewStatus(reviewStatus, pageable);
    }
    
    /**
     * Retrieves applications created within a date range with pagination.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable The pagination information
     * @return Page of applications created within the specified date range
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsByCreationDateRange(LocalDateTime startDate, 
                                                              LocalDateTime endDate, 
                                                              Pageable pageable) {
        logger.debug("Retrieving applications created between {} and {} with pagination: {}", 
                    startDate, endDate, pageable);
        return applicationRepository.findByCreatedAtBetween(startDate, endDate, pageable);
    }
    
    /**
     * Updates an existing application with the provided data.
     * 
     * @param id The application ID
     * @param applicationDTO The updated application data
     * @return The updated application
     * @throws ApplicationNotFoundException if the application is not found
     * @throws ValidationException if the application data is invalid
     */
    @Override
    @Transactional
    @Caching(evict = {
        @CacheEvict(value = "applications", key = "#id"),
        @CacheEvict(value = "applicationDocuments", key = "#id")
    })
    public Application updateApplication(UUID id, ApplicationRequestDTO applicationDTO) {
        logger.info("Updating application with ID: {}", id);
        
        // Validate application data
        ValidationResult validationResult = validationService.validateApplicationData(applicationDTO);
        if (!validationResult.isValid()) {
            logger.warn("Application data validation failed: {}", validationResult.getErrors());
            throw new ValidationException("Invalid application data", validationResult.getErrors());
        }
        
        // Retrieve existing application
        Application application = getApplicationById(id);
        
        // Update metadata
        if (applicationDTO.getMetadata() != null) {
            Map<String, Object> metadata = application.getMetadata();
            metadata.putAll(applicationDTO.getMetadata());
            metadata.put("lastUpdated", LocalDateTime.now().toString());
            application.setMetadata(metadata);
        }
        
        // Update application
        application.setUpdatedAt(LocalDateTime.now());
        application = applicationRepository.save(application);
        logger.info("Updated application with ID: {}", id);
        
        return application;
    }
    
    /**
     * Updates the status of an application.
     * 
     * @param id The application ID
     * @param newStatus The new status to set
     * @return The updated application
     * @throws ApplicationNotFoundException if the application is not found
     * @throws InvalidApplicationStateException if the status transition is invalid
     */
    @Override
    @Transactional
    @CacheEvict(value = "applications", key = "#id")
    public Application updateApplicationStatus(UUID id, ApplicationStatus newStatus) {
        logger.info("Updating status of application with ID: {} to {}", id, newStatus);
        
        // Retrieve existing application
        Application application = getApplicationById(id);
        String previousStatus = application.getStatus().toString();
        
        // Update status if transition is valid
        if (!application.updateStatus(newStatus)) {
            logger.warn("Invalid status transition from {} to {} for application ID: {}", 
                       application.getStatus(), newStatus, id);
            throw new InvalidApplicationStateException(
                    "Invalid status transition from " + application.getStatus() + " to " + newStatus);
        }
        
        // Save application
        application = applicationRepository.save(application);
        logger.info("Updated status of application with ID: {} from {} to {}", 
                   id, previousStatus, newStatus);
        
        // Send notification
        notificationService.sendApplicationStatusNotification(application, previousStatus, newStatus.toString());
        
        // Send specific notifications for certain status changes
        if (newStatus == ApplicationStatus.APPROVED) {
            notificationService.sendApplicationApprovedNotification(application);
        } else if (newStatus == ApplicationStatus.REJECTED) {
            notificationService.sendApplicationRejectedNotification(application, 
                    (String) application.getMetadataValue("rejectionReason"));
        }
        
        return application;
    }
    
    /**
     * Updates the review status of an application.
     * 
     * @param id The application ID
     * @param newReviewStatus The new review status to set
     * @return The updated application
     * @throws ApplicationNotFoundException if the application is not found
     * @throws InvalidApplicationStateException if the review status transition is invalid
     */
    @Override
    @Transactional
    @CacheEvict(value = "applications", key = "#id")
    public Application updateApplicationReviewStatus(UUID id, ReviewStatus newReviewStatus) {
        logger.info("Updating review status of application with ID: {} to {}", id, newReviewStatus);
        
        // Retrieve existing application
        Application application = getApplicationById(id);
        String previousReviewStatus = application.getReviewStatus().toString();
        
        // Update review status if transition is valid
        if (!application.updateReviewStatus(newReviewStatus)) {
            logger.warn("Invalid review status transition from {} to {} for application ID: {}", 
                       application.getReviewStatus(), newReviewStatus, id);
            throw new InvalidApplicationStateException(
                    "Invalid review status transition from " + application.getReviewStatus() + 
                    " to " + newReviewStatus);
        }
        
        // Save application
        application = applicationRepository.save(application);
        logger.info("Updated review status of application with ID: {} from {} to {}", 
                   id, previousReviewStatus, newReviewStatus);
        
        // Send notification
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", application.getId().toString());
        payload.put("previousReviewStatus", previousReviewStatus);
        payload.put("newReviewStatus", newReviewStatus.toString());
        notificationService.sendSystemEventNotification(EventType.APPLICATION_UPDATED, payload);
        
        return application;
    }
    
    /**
     * Deletes an application by its ID.
     * 
     * @param id The application ID
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional
    @Caching(evict = {
        @CacheEvict(value = "applications", key = "#id"),
        @CacheEvict(value = "applicationDocuments", key = "#id")
    })
    public void deleteApplication(UUID id) {
        logger.info("Deleting application with ID: {}", id);
        
        // Check if application exists
        if (!applicationRepository.existsById(id)) {
            logger.warn("Application not found with ID: {}", id);
            throw new ApplicationNotFoundException("Application not found with ID: " + id);
        }
        
        // Delete application
        applicationRepository.deleteById(id);
        logger.info("Deleted application with ID: {}", id);
    }
    
    /**
     * Adds a document to an application.
     * 
     * @param applicationId The application ID
     * @param document The document to add
     * @return The updated application
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional
    @Caching(evict = {
        @CacheEvict(value = "applications", key = "#applicationId"),
        @CacheEvict(value = "applicationDocuments", key = "#applicationId")
    })
    public Application addDocumentToApplication(UUID applicationId, Document document) {
        logger.info("Adding document to application with ID: {}", applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        // Add document to application
        application.addDocument(document);
        
        // Update application
        application.setUpdatedAt(LocalDateTime.now());
        application = applicationRepository.save(application);
        logger.info("Added document to application with ID: {}", applicationId);
        
        // Send notification
        notificationService.sendDocumentUploadedNotification(document, applicationId);
        
        // Re-evaluate application status based on new document
        evaluateApplicationStatus(applicationId);
        
        return application;
    }
    
    /**
     * Retrieves all documents associated with an application.
     * 
     * @param applicationId The application ID
     * @return List of documents associated with the application
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(value = "applicationDocuments", key = "#applicationId")
    public List<Document> getApplicationDocuments(UUID applicationId) {
        logger.debug("Retrieving documents for application with ID: {}", applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        return application.getDocuments();
    }
    
    /**
     * Retrieves documents of a specific type associated with an application.
     * 
     * @param applicationId The application ID
     * @param documentType The document type to filter by
     * @return List of documents of the specified type associated with the application
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional(readOnly = true)
    public List<Document> getApplicationDocumentsByType(UUID applicationId, DocumentType documentType) {
        logger.debug("Retrieving documents of type {} for application with ID: {}", documentType, applicationId);
        
        // Retrieve all documents for the application
        List<Document> documents = getApplicationDocuments(applicationId);
        
        // Filter by document type
        return documents.stream()
                .filter(doc -> doc.getType() == documentType)
                .collect(Collectors.toList());
    }
    
    /**
     * Processes a document for an application.
     * 
     * @param applicationId The application ID
     * @param documentId The document ID
     * @param extractedData The data extracted from the document
     * @param confidenceScores The confidence scores for the extracted data
     * @return The updated application
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional
    @Caching(evict = {
        @CacheEvict(value = "applications", key = "#applicationId"),
        @CacheEvict(value = "applicationDocuments", key = "#applicationId")
    })
    public Application processDocument(UUID applicationId, UUID documentId, 
                                     Map<String, Object> extractedData,
                                     Map<String, Double> confidenceScores) {
        logger.info("Processing document with ID: {} for application with ID: {}", documentId, applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        // Find the document
        Optional<Document> optionalDocument = application.getDocuments().stream()
                .filter(doc -> doc.getId().equals(documentId))
                .findFirst();
        
        if (!optionalDocument.isPresent()) {
            logger.warn("Document not found with ID: {} for application with ID: {}", documentId, applicationId);
            throw new IllegalArgumentException("Document not found with ID: " + documentId);
        }
        
        Document document = optionalDocument.get();
        
        // Validate extracted data
        ValidationResult validationResult = validationService.validateExtractedDataWithConfidence(
                document.getType(), extractedData, confidenceScores);
        
        // Update document metadata with extracted data and validation results
        Map<String, Object> metadata = document.getMetadata();
        metadata.put("extractedData", extractedData);
        metadata.put("confidenceScores", confidenceScores);
        metadata.put("validationResult", validationResult.isValid());
        metadata.put("processingTimestamp", LocalDateTime.now().toString());
        
        if (!validationResult.isValid()) {
            metadata.put("validationErrors", validationResult.getErrors());
            metadata.put("validationSeverity", validationResult.getSeverity().toString());
        }
        
        document.setMetadata(metadata);
        
        // Update application metadata with document processing information
        Map<String, Object> appMetadata = application.getMetadata();
        appMetadata.put("lastProcessedDocumentId", documentId.toString());
        appMetadata.put("lastProcessedDocumentType", document.getType().toString());
        appMetadata.put("lastProcessedTimestamp", LocalDateTime.now().toString());
        application.setMetadata(appMetadata);
        
        // Save application
        application.setUpdatedAt(LocalDateTime.now());
        application = applicationRepository.save(application);
        logger.info("Processed document with ID: {} for application with ID: {}", documentId, applicationId);
        
        // Send notification
        notificationService.sendDocumentProcessedNotification(document, applicationId, extractedData);
        
        // Re-evaluate application status based on processed document
        evaluateApplicationStatus(applicationId);
        
        return application;
    }
    
    /**
     * Evaluates the status of an application based on its documents and validation rules.
     * 
     * @param applicationId The application ID
     * @return The updated application
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional
    @CacheEvict(value = "applications", key = "#applicationId")
    public Application evaluateApplicationStatus(UUID applicationId) {
        logger.info("Evaluating status of application with ID: {}", applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        // Evaluate application completeness
        ValidationResult completenessResult = validationService.evaluateApplicationCompleteness(application);
        
        // Determine appropriate application status based on business rules
        ApplicationStatus recommendedStatus = validationService.determineApplicationStatus(application);
        
        // Determine appropriate review status based on business rules
        ReviewStatus recommendedReviewStatus = validationService.determineReviewStatus(application);
        
        // Update application metadata with evaluation results
        Map<String, Object> metadata = application.getMetadata();
        metadata.put("completenessEvaluation", completenessResult.isValid());
        metadata.put("lastEvaluationTimestamp", LocalDateTime.now().toString());
        
        if (!completenessResult.isValid()) {
            metadata.put("completenessErrors", completenessResult.getErrors());
        }
        
        application.setMetadata(metadata);
        
        // Update application status if different from current status
        boolean statusChanged = false;
        if (recommendedStatus != application.getStatus()) {
            statusChanged = application.updateStatus(recommendedStatus);
            if (statusChanged) {
                logger.info("Updated status of application with ID: {} to {}", 
                           applicationId, recommendedStatus);
            }
        }
        
        // Update review status if different from current review status
        boolean reviewStatusChanged = false;
        if (recommendedReviewStatus != application.getReviewStatus()) {
            reviewStatusChanged = application.updateReviewStatus(recommendedReviewStatus);
            if (reviewStatusChanged) {
                logger.info("Updated review status of application with ID: {} to {}", 
                           applicationId, recommendedReviewStatus);
            }
        }
        
        // Save application if status or review status changed
        if (statusChanged || reviewStatusChanged) {
            application.setUpdatedAt(LocalDateTime.now());
            application = applicationRepository.save(application);
        }
        
        return application;
    }
    
    /**
     * Validates an application against business rules.
     * 
     * @param applicationId The application ID
     * @return The validation result
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional(readOnly = true)
    public ValidationResult validateApplication(UUID applicationId) {
        logger.info("Validating application with ID: {}", applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        // Validate application
        return validationService.validateApplication(application);
    }
    
    /**
     * Checks if an application has all required documents.
     * 
     * @param applicationId The application ID
     * @return true if the application has all required documents, false otherwise
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional(readOnly = true)
    public boolean hasAllRequiredDocuments(UUID applicationId) {
        logger.debug("Checking if application with ID: {} has all required documents", applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        return application.hasAllRequiredDocuments();
    }
    
    /**
     * Calculates the processing time of an application in minutes.
     * 
     * @param applicationId The application ID
     * @return The processing time in minutes, or -1 if the application is not completed
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional(readOnly = true)
    public long getApplicationProcessingTime(UUID applicationId) {
        logger.debug("Calculating processing time for application with ID: {}", applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        return application.getProcessingTimeMinutes();
    }
    
    /**
     * Checks if an application was processed within the target time (5 minutes).
     * 
     * @param applicationId The application ID
     * @return true if the application was processed within the target time, false otherwise
     * @throws ApplicationNotFoundException if the application is not found
     */
    @Override
    @Transactional(readOnly = true)
    public boolean isApplicationProcessedWithinTargetTime(UUID applicationId) {
        logger.debug("Checking if application with ID: {} was processed within target time", applicationId);
        
        // Retrieve existing application
        Application application = getApplicationById(applicationId);
        
        return application.isProcessedWithinTargetTime();
    }
    
    /**
     * Counts the number of applications with a specific status.
     * 
     * @param status The application status to count
     * @return The number of applications with the specified status
     */
    @Override
    @Transactional(readOnly = true)
    public long countApplicationsByStatus(ApplicationStatus status) {
        logger.debug("Counting applications with status: {}", status);
        return applicationRepository.countByStatus(status);
    }
    
    /**
     * Counts the number of applications with a specific review status.
     * 
     * @param reviewStatus The review status to count
     * @return The number of applications with the specified review status
     */
    @Override
    @Transactional(readOnly = true)
    public long countApplicationsByReviewStatus(ReviewStatus reviewStatus) {
        logger.debug("Counting applications with review status: {}", reviewStatus);
        return applicationRepository.countByReviewStatus(reviewStatus);
    }
    
    /**
     * Calculates the average processing time (in minutes) for completed applications.
     * 
     * @return The average processing time in minutes
     */
    @Override
    @Transactional(readOnly = true)
    public double calculateAverageProcessingTime() {
        logger.debug("Calculating average processing time for completed applications");
        Double avgTime = applicationRepository.calculateAverageProcessingTimeMinutes();
        return avgTime != null ? avgTime : 0.0;
    }
    
    /**
     * Calculates the average processing time (in minutes) for completed applications within a date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return The average processing time in minutes
     */
    @Override
    @Transactional(readOnly = true)
    public double calculateAverageProcessingTime(LocalDateTime startDate, LocalDateTime endDate) {
        logger.debug("Calculating average processing time for completed applications between {} and {}", 
                    startDate, endDate);
        Double avgTime = applicationRepository.calculateAverageProcessingTimeMinutes(startDate, endDate);
        return avgTime != null ? avgTime : 0.0;
    }
    
    /**
     * Retrieves applications that require review with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications that require review
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsRequiringReview(Pageable pageable) {
        logger.debug("Retrieving applications requiring review with pagination: {}", pageable);
        return applicationRepository.findApplicationsRequiringReview(pageable);
    }
    
    /**
     * Retrieves active applications with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of active applications
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getActiveApplications(Pageable pageable) {
        logger.debug("Retrieving active applications with pagination: {}", pageable);
        return applicationRepository.findActiveApplications(pageable);
    }
    
    /**
     * Retrieves applications that have been decided upon with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of decided applications
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getDecidedApplications(Pageable pageable) {
        logger.debug("Retrieving decided applications with pagination: {}", pageable);
        return applicationRepository.findDecidedApplications(pageable);
    }
    
    /**
     * Retrieves applications that were processed within the target time (5 minutes) with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications processed within the target time
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsProcessedWithinTargetTime(Pageable pageable) {
        logger.debug("Retrieving applications processed within target time with pagination: {}", pageable);
        return applicationRepository.findApplicationsProcessedWithinTargetTime(pageable);
    }
    
    /**
     * Retrieves applications that exceeded the target processing time (5 minutes) with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications that exceeded the target processing time
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsExceedingTargetTime(Pageable pageable) {
        logger.debug("Retrieving applications exceeding target time with pagination: {}", pageable);
        return applicationRepository.findApplicationsExceedingTargetTime(pageable);
    }
    
    /**
     * Retrieves applications with merchant details in a specific industry with pagination.
     * 
     * @param industry The industry to filter by
     * @param pageable The pagination information
     * @return Page of applications with merchant details in the specified industry
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsByMerchantIndustry(String industry, Pageable pageable) {
        logger.debug("Retrieving applications with merchant industry: {} and pagination: {}", 
                    industry, pageable);
        return applicationRepository.findByMerchantIndustry(industry, pageable);
    }
    
    /**
     * Retrieves applications with merchant details in a specific state with pagination.
     * 
     * @param state The state to filter by (2-letter code)
     * @param pageable The pagination information
     * @return Page of applications with merchant details in the specified state
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsByMerchantState(String state, Pageable pageable) {
        logger.debug("Retrieving applications with merchant state: {} and pagination: {}", 
                    state, pageable);
        return applicationRepository.findByMerchantState(state, pageable);
    }
    
    /**
     * Retrieves applications with metadata containing a specific key-value pair with pagination.
     * 
     * @param key The metadata key
     * @param value The metadata value
     * @param pageable The pagination information
     * @return Page of applications with metadata containing the specified key-value pair
     */
    @Override
    @Transactional(readOnly = true)
    public Page<Application> getApplicationsByMetadata(String key, Object value, Pageable pageable) {
        logger.debug("Retrieving applications with metadata key: {}, value: {} and pagination: {}", 
                    key, value, pageable);
        
        // Create JSON string for key-value pair
        String keyValueJson = String.format("{\"%s\":\"%s\"}", key, value.toString());
        
        return applicationRepository.findByMetadataContains(keyValueJson, pageable);
    }
}