package com.dollarfunding.mca.service;

import com.dollarfunding.mca.cache.CacheConstants;
import com.dollarfunding.mca.cache.CacheKeyGenerator;
import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ApplicationNotFoundException;
import com.dollarfunding.mca.exception.InvalidApplicationStateException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.util.ValidationResult;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.CachePut;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Implementation of the ApplicationService interface that manages the core business logic for MCA applications.
 * It handles CRUD operations, status updates, validation, and processing workflows for applications.
 * This class interacts with ApplicationRepository for data persistence, ValidationService for business rule validation,
 * and NotificationService for status updates. It implements transaction management to ensure data consistency across operations.
 */
@Service
public class ApplicationServiceImpl implements ApplicationService {

    private static final Logger logger = LoggerFactory.getLogger(ApplicationServiceImpl.class);

    private final ApplicationRepository applicationRepository;
    private final ValidationService validationService;
    private final NotificationService notificationService;

    /**
     * Constructor for ApplicationServiceImpl with required dependencies.
     *
     * @param applicationRepository Repository for Application entity persistence
     * @param validationService Service for validating application data
     * @param notificationService Service for sending notifications about application status changes
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
     * Creates a new MCA application with the provided data.
     * Validates the application data, sets initial status, and persists to the database.
     * Sends a notification about the new application.
     *
     * @param applicationRequestDTO DTO containing application data
     * @return ApplicationResponseDTO with the created application data
     * @throws ValidationException if the application data fails validation
     */
    @Override
    @Transactional
    @CachePut(value = CacheConstants.APPLICATION_CACHE, key = "#result.id")
    public ApplicationResponseDTO createApplication(ApplicationRequestDTO applicationRequestDTO) {
        logger.info("Creating new application");
        
        // Validate application data
        ValidationResult validationResult = validationService.validateApplicationData(applicationRequestDTO);
        if (!validationResult.isValid()) {
            logger.warn("Application data validation failed: {}", validationResult.getErrors());
            throw new ValidationException("Application data validation failed", validationResult.getErrors());
        }
        
        // Create new application entity
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        application.setMetadata(applicationRequestDTO.getMetadata());
        application.setCreatedAt(LocalDateTime.now());
        application.setUpdatedAt(LocalDateTime.now());
        
        // Save to database
        Application savedApplication = applicationRepository.save(application);
        logger.info("Application created with ID: {}", savedApplication.getId());
        
        // Send notification about new application
        notificationService.sendApplicationStatusNotification(savedApplication.getId(), ApplicationStatus.NEW);
        
        // Return response DTO
        return new ApplicationResponseDTO(savedApplication);
    }

    /**
     * Retrieves an application by its ID.
     * Checks the cache first before querying the database.
     *
     * @param id Application ID
     * @return ApplicationResponseDTO with the application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    @Override
    @Transactional(readOnly = true)
    @Cacheable(value = CacheConstants.APPLICATION_CACHE, key = "#id")
    public ApplicationResponseDTO getApplicationById(Long id) {
        logger.info("Retrieving application with ID: {}", id);
        
        Application application = applicationRepository.findById(id)
                .orElseThrow(() -> new ApplicationNotFoundException("Application not found with ID: " + id));
        
        return new ApplicationResponseDTO(application);
    }

    /**
     * Updates an existing application with the provided data.
     * Validates the updated data, updates the entity, and persists to the database.
     * Sends a notification about the updated application.
     *
     * @param id Application ID
     * @param applicationRequestDTO DTO containing updated application data
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     * @throws ValidationException if the updated application data fails validation
     */
    @Override
    @Transactional
    @CachePut(value = CacheConstants.APPLICATION_CACHE, key = "#id")
    public ApplicationResponseDTO updateApplication(Long id, ApplicationRequestDTO applicationRequestDTO) {
        logger.info("Updating application with ID: {}", id);
        
        // Find existing application
        Application application = applicationRepository.findById(id)
                .orElseThrow(() -> new ApplicationNotFoundException("Application not found with ID: " + id));
        
        // Validate updated data
        ValidationResult validationResult = validationService.validateApplicationData(applicationRequestDTO);
        if (!validationResult.isValid()) {
            logger.warn("Application data validation failed: {}", validationResult.getErrors());
            throw new ValidationException("Application data validation failed", validationResult.getErrors());
        }
        
        // Update application entity
        application.setMetadata(applicationRequestDTO.getMetadata());
        application.setUpdatedAt(LocalDateTime.now());
        
        // Update status if provided and valid
        if (applicationRequestDTO.getStatus() != null) {
            validateStatusTransition(application.getStatus(), applicationRequestDTO.getStatus());
            application.setStatus(applicationRequestDTO.getStatus());
        }
        
        // Update review status if provided
        if (applicationRequestDTO.getReviewStatus() != null) {
            application.setReviewStatus(applicationRequestDTO.getReviewStatus());
        }
        
        // Save to database
        Application updatedApplication = applicationRepository.save(application);
        logger.info("Application updated with ID: {}", updatedApplication.getId());
        
        // Send notification about updated application
        notificationService.sendApplicationStatusNotification(updatedApplication.getId(), updatedApplication.getStatus());
        
        // Return response DTO
        return new ApplicationResponseDTO(updatedApplication);
    }

    /**
     * Deletes an application by its ID.
     * Removes the application from the database and cache.
     *
     * @param id Application ID
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    @Override
    @Transactional
    @CacheEvict(value = CacheConstants.APPLICATION_CACHE, key = "#id")
    public void deleteApplication(Long id) {
        logger.info("Deleting application with ID: {}", id);
        
        // Check if application exists
        if (!applicationRepository.existsById(id)) {
            throw new ApplicationNotFoundException("Application not found with ID: " + id);
        }
        
        // Delete application
        applicationRepository.deleteById(id);
        logger.info("Application deleted with ID: {}", id);
    }

    /**
     * Retrieves a paginated list of applications based on filter criteria.
     * Supports filtering by status, review status, date range, and other criteria.
     *
     * @param filterDTO DTO containing filter criteria
     * @param pageable Pagination information
     * @return Page of ApplicationResponseDTO objects
     */
    @Override
    @Transactional(readOnly = true)
    public Page<ApplicationResponseDTO> getApplications(ApplicationFilterDTO filterDTO, Pageable pageable) {
        logger.info("Retrieving applications with filter: {}", filterDTO);
        
        // Create specification from filter criteria
        Specification<Application> spec = createSpecificationFromFilter(filterDTO);
        
        // Query database with specification and pagination
        Page<Application> applications = applicationRepository.findAll(spec, pageable);
        
        // Convert to response DTOs
        return applications.map(ApplicationResponseDTO::new);
    }

    /**
     * Updates the status of an application.
     * Validates the status transition, updates the entity, and persists to the database.
     * Sends a notification about the status change.
     *
     * @param id Application ID
     * @param status New application status
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     * @throws InvalidApplicationStateException if the status transition is invalid
     */
    @Override
    @Transactional
    @CachePut(value = CacheConstants.APPLICATION_CACHE, key = "#id")
    public ApplicationResponseDTO updateApplicationStatus(Long id, ApplicationStatus status) {
        logger.info("Updating status of application with ID: {} to {}", id, status);
        
        // Find existing application
        Application application = applicationRepository.findById(id)
                .orElseThrow(() -> new ApplicationNotFoundException("Application not found with ID: " + id));
        
        // Validate status transition
        validateStatusTransition(application.getStatus(), status);
        
        // Update status
        application.setStatus(status);
        application.setUpdatedAt(LocalDateTime.now());
        
        // Save to database
        Application updatedApplication = applicationRepository.save(application);
        logger.info("Application status updated with ID: {} to {}", updatedApplication.getId(), status);
        
        // Send notification about status change
        notificationService.sendApplicationStatusNotification(updatedApplication.getId(), status);
        
        // Return response DTO
        return new ApplicationResponseDTO(updatedApplication);
    }

    /**
     * Updates the review status of an application.
     * Updates the entity and persists to the database.
     * Sends a notification about the review status change.
     *
     * @param id Application ID
     * @param reviewStatus New review status
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    @Override
    @Transactional
    @CachePut(value = CacheConstants.APPLICATION_CACHE, key = "#id")
    public ApplicationResponseDTO updateApplicationReviewStatus(Long id, ReviewStatus reviewStatus) {
        logger.info("Updating review status of application with ID: {} to {}", id, reviewStatus);
        
        // Find existing application
        Application application = applicationRepository.findById(id)
                .orElseThrow(() -> new ApplicationNotFoundException("Application not found with ID: " + id));
        
        // Update review status
        application.setReviewStatus(reviewStatus);
        application.setUpdatedAt(LocalDateTime.now());
        
        // Save to database
        Application updatedApplication = applicationRepository.save(application);
        logger.info("Application review status updated with ID: {} to {}", updatedApplication.getId(), reviewStatus);
        
        // Send notification about review status change
        notificationService.sendApplicationReviewStatusNotification(updatedApplication.getId(), reviewStatus);
        
        // Return response DTO
        return new ApplicationResponseDTO(updatedApplication);
    }

    /**
     * Adds a document to an application.
     * Updates the application entity with the new document reference.
     *
     * @param applicationId Application ID
     * @param document Document entity to add
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    @Override
    @Transactional
    @CachePut(value = CacheConstants.APPLICATION_CACHE, key = "#applicationId")
    public ApplicationResponseDTO addDocumentToApplication(Long applicationId, Document document) {
        logger.info("Adding document to application with ID: {}", applicationId);
        
        // Find existing application
        Application application = applicationRepository.findById(applicationId)
                .orElseThrow(() -> new ApplicationNotFoundException("Application not found with ID: " + applicationId));
        
        // Add document to application
        document.setApplication(application);
        application.getDocuments().add(document);
        application.setUpdatedAt(LocalDateTime.now());
        
        // Save to database
        Application updatedApplication = applicationRepository.save(application);
        logger.info("Document added to application with ID: {}", updatedApplication.getId());
        
        // Return response DTO
        return new ApplicationResponseDTO(updatedApplication);
    }

    /**
     * Evaluates the completeness of an application based on business rules.
     * Checks if all required documents are present and valid.
     *
     * @param id Application ID
     * @return true if the application is complete, false otherwise
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    @Override
    @Transactional(readOnly = true)
    public boolean isApplicationComplete(Long id) {
        logger.info("Evaluating completeness of application with ID: {}", id);
        
        // Find existing application
        Application application = applicationRepository.findById(id)
                .orElseThrow(() -> new ApplicationNotFoundException("Application not found with ID: " + id));
        
        // Validate application completeness using validation service
        ValidationResult validationResult = validationService.validateApplicationCompleteness(application);
        
        return validationResult.isValid();
    }

    /**
     * Processes an application by applying business rules and updating its status.
     * Validates the application data, evaluates completeness, and updates status accordingly.
     *
     * @param id Application ID
     * @return ApplicationResponseDTO with the processed application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    @Override
    @Transactional
    @CachePut(value = CacheConstants.APPLICATION_CACHE, key = "#id")
    public ApplicationResponseDTO processApplication(Long id) {
        logger.info("Processing application with ID: {}", id);
        
        // Find existing application
        Application application = applicationRepository.findById(id)
                .orElseThrow(() -> new ApplicationNotFoundException("Application not found with ID: " + id));
        
        // Update status to PROCESSING
        application.setStatus(ApplicationStatus.PROCESSING);
        application.setUpdatedAt(LocalDateTime.now());
        applicationRepository.save(application);
        
        // Apply business rules and validate application
        ValidationResult validationResult = validationService.validateApplication(application);
        
        // Update status based on validation result
        if (validationResult.isValid()) {
            // Check if application is complete
            if (isApplicationComplete(id)) {
                application.setStatus(ApplicationStatus.COMPLETED);
            } else {
                application.setStatus(ApplicationStatus.PENDING);
            }
        } else {
            // Application has validation errors
            application.setStatus(ApplicationStatus.REJECTED);
            logger.warn("Application processing failed: {}", validationResult.getErrors());
        }
        
        // Save updated status
        application.setUpdatedAt(LocalDateTime.now());
        Application processedApplication = applicationRepository.save(application);
        
        // Send notification about status change
        notificationService.sendApplicationStatusNotification(processedApplication.getId(), processedApplication.getStatus());
        
        // Return response DTO
        return new ApplicationResponseDTO(processedApplication);
    }

    /**
     * Creates a specification from filter criteria for querying applications.
     *
     * @param filterDTO DTO containing filter criteria
     * @return Specification for querying applications
     */
    private Specification<Application> createSpecificationFromFilter(ApplicationFilterDTO filterDTO) {
        Specification<Application> spec = Specification.where(null);
        
        // Add status filter if provided
        if (filterDTO.getStatus() != null) {
            spec = spec.and((root, query, cb) -> cb.equal(root.get("status"), filterDTO.getStatus()));
        }
        
        // Add review status filter if provided
        if (filterDTO.getReviewStatus() != null) {
            spec = spec.and((root, query, cb) -> cb.equal(root.get("reviewStatus"), filterDTO.getReviewStatus()));
        }
        
        // Add date range filter if provided
        if (filterDTO.getStartDate() != null && filterDTO.getEndDate() != null) {
            spec = spec.and((root, query, cb) -> cb.between(root.get("createdAt"), 
                    filterDTO.getStartDate(), filterDTO.getEndDate()));
        }
        
        // Add merchant name filter if provided
        if (filterDTO.getMerchantName() != null && !filterDTO.getMerchantName().isEmpty()) {
            spec = spec.and((root, query, cb) -> cb.like(cb.lower(
                    root.join("merchantDetails").get("legalName")), 
                    "%" + filterDTO.getMerchantName().toLowerCase() + "%"));
        }
        
        return spec;
    }

    /**
     * Validates if a status transition is allowed based on business rules.
     *
     * @param currentStatus Current application status
     * @param newStatus New application status
     * @throws InvalidApplicationStateException if the status transition is invalid
     */
    private void validateStatusTransition(ApplicationStatus currentStatus, ApplicationStatus newStatus) {
        // Define valid status transitions
        boolean isValidTransition = switch (currentStatus) {
            case NEW -> newStatus == ApplicationStatus.PROCESSING || newStatus == ApplicationStatus.REJECTED;
            case PROCESSING -> newStatus == ApplicationStatus.PENDING || 
                              newStatus == ApplicationStatus.COMPLETED || 
                              newStatus == ApplicationStatus.REJECTED;
            case PENDING -> newStatus == ApplicationStatus.PROCESSING || 
                           newStatus == ApplicationStatus.COMPLETED || 
                           newStatus == ApplicationStatus.REJECTED;
            case COMPLETED -> newStatus == ApplicationStatus.PROCESSING; // Allow reopening completed applications
            case REJECTED -> newStatus == ApplicationStatus.PROCESSING; // Allow reprocessing rejected applications
            default -> false;
        };
        
        if (!isValidTransition) {
            String errorMessage = String.format("Invalid status transition from %s to %s", currentStatus, newStatus);
            logger.warn(errorMessage);
            throw new InvalidApplicationStateException(errorMessage);
        }
    }
}