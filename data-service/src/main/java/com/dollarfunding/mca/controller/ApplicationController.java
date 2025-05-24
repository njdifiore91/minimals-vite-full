package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ApplicationNotFoundException;
import com.dollarfunding.mca.exception.InvalidApplicationStateException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.service.ApplicationService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.UUID;

/**
 * REST controller that manages MCA application data through the /api/v1/applications endpoint.
 * 
 * This controller provides CRUD operations for applications with role-based access control,
 * allowing Operations Staff to read all applications and modify application data, while
 * System Admins have full access. It validates incoming requests, delegates business logic
 * to the ApplicationService, and formats responses according to API contracts.
 *
 * @author MCA Application Team
 */
@RestController
@RequestMapping("/api/v1/applications")
@Validated
public class ApplicationController {

    private static final Logger logger = LoggerFactory.getLogger(ApplicationController.class);

    private final ApplicationService applicationService;

    /**
     * Constructor with required dependencies
     * 
     * @param applicationService Service for application business logic
     */
    @Autowired
    public ApplicationController(ApplicationService applicationService) {
        this.applicationService = applicationService;
    }

    /**
     * Creates a new MCA application
     * 
     * @param requestDTO DTO containing application data
     * @return ResponseEntity with the created application data
     */
    @PostMapping
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<ApplicationResponseDTO> createApplication(
            @Valid @RequestBody ApplicationRequestDTO requestDTO) {
        
        logger.info("Creating new application with status: {}", requestDTO.getStatus());
        
        try {
            ApplicationResponseDTO responseDTO = applicationService.createApplication(requestDTO);
            return new ResponseEntity<>(responseDTO, HttpStatus.CREATED);
        } catch (ValidationException e) {
            logger.error("Validation error creating application: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error creating application: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Retrieves an application by its ID
     * 
     * @param id Application ID
     * @return ResponseEntity with the application data
     */
    @GetMapping("/{id}")
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<ApplicationResponseDTO> getApplicationById(
            @PathVariable("id") UUID id) {
        
        logger.info("Retrieving application with ID: {}", id);
        
        try {
            ApplicationResponseDTO responseDTO = applicationService.getApplicationById(id);
            return ResponseEntity.ok(responseDTO);
        } catch (ApplicationNotFoundException e) {
            logger.error("Application not found: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error retrieving application: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Updates an existing application
     * 
     * @param id Application ID
     * @param requestDTO DTO containing updated application data
     * @return ResponseEntity with the updated application data
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<ApplicationResponseDTO> updateApplication(
            @PathVariable("id") UUID id,
            @Valid @RequestBody ApplicationRequestDTO requestDTO) {
        
        logger.info("Updating application with ID: {}", id);
        
        try {
            ApplicationResponseDTO responseDTO = applicationService.updateApplication(id, requestDTO);
            return ResponseEntity.ok(responseDTO);
        } catch (ApplicationNotFoundException e) {
            logger.error("Application not found: {}", e.getMessage());
            throw e;
        } catch (ValidationException e) {
            logger.error("Validation error updating application: {}", e.getMessage());
            throw e;
        } catch (InvalidApplicationStateException e) {
            logger.error("Invalid application state: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error updating application: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Deletes an application by its ID
     * 
     * @param id Application ID
     * @return ResponseEntity with no content
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<Void> deleteApplication(
            @PathVariable("id") UUID id) {
        
        logger.info("Deleting application with ID: {}", id);
        
        try {
            applicationService.deleteApplication(id);
            return ResponseEntity.noContent().build();
        } catch (ApplicationNotFoundException e) {
            logger.error("Application not found: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error deleting application: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Retrieves a paginated list of applications based on filter criteria
     * 
     * @param status Application status filter
     * @param reviewStatus Review status filter
     * @param merchantName Merchant name filter
     * @param startDate Start date for date range filter
     * @param endDate End date for date range filter
     * @param searchTerm General search term for text fields
     * @param page Page number (zero-based)
     * @param size Page size
     * @param sortBy Field to sort by
     * @param sortDirection Sort direction (asc or desc)
     * @return ResponseEntity with a page of applications
     */
    @GetMapping
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<Page<ApplicationResponseDTO>> getApplications(
            @RequestParam(required = false) ApplicationStatus status,
            @RequestParam(required = false) ReviewStatus reviewStatus,
            @RequestParam(required = false) String merchantName,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate,
            @RequestParam(required = false) String searchTerm,
            @RequestParam(defaultValue = "0") Integer page,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(defaultValue = "createdAt") String sortBy,
            @RequestParam(defaultValue = "desc") String sortDirection) {
        
        logger.info("Retrieving applications with filters: status={}, reviewStatus={}, page={}, size={}", 
                   status, reviewStatus, page, size);
        
        try {
            // Convert string dates to LocalDate if provided
            java.time.LocalDate startLocalDate = startDate != null ? 
                    java.time.LocalDate.parse(startDate) : null;
            java.time.LocalDate endLocalDate = endDate != null ? 
                    java.time.LocalDate.parse(endDate) : null;
            
            // Create filter DTO
            ApplicationFilterDTO filterDTO = new ApplicationFilterDTO(
                    status, reviewStatus, merchantName, startLocalDate, endLocalDate,
                    searchTerm, page, size, sortBy, sortDirection);
            
            // Get pageable from filter DTO
            Pageable pageable = filterDTO.toPageable();
            
            // Get applications
            Page<ApplicationResponseDTO> applications = 
                    applicationService.getApplications(filterDTO, pageable);
            
            return ResponseEntity.ok(applications);
        } catch (Exception e) {
            logger.error("Error retrieving applications: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Updates the status of an application
     * 
     * @param id Application ID
     * @param status New application status
     * @return ResponseEntity with the updated application data
     */
    @PatchMapping("/{id}/status")
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<ApplicationResponseDTO> updateApplicationStatus(
            @PathVariable("id") UUID id,
            @RequestParam ApplicationStatus status) {
        
        logger.info("Updating status of application with ID: {} to {}", id, status);
        
        try {
            ApplicationResponseDTO responseDTO = applicationService.updateApplicationStatus(id, status);
            return ResponseEntity.ok(responseDTO);
        } catch (ApplicationNotFoundException e) {
            logger.error("Application not found: {}", e.getMessage());
            throw e;
        } catch (InvalidApplicationStateException e) {
            logger.error("Invalid application state transition: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error updating application status: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Updates the review status of an application
     * 
     * @param id Application ID
     * @param reviewStatus New review status
     * @return ResponseEntity with the updated application data
     */
    @PatchMapping("/{id}/review-status")
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<ApplicationResponseDTO> updateApplicationReviewStatus(
            @PathVariable("id") UUID id,
            @RequestParam ReviewStatus reviewStatus) {
        
        logger.info("Updating review status of application with ID: {} to {}", id, reviewStatus);
        
        try {
            ApplicationResponseDTO responseDTO = 
                    applicationService.updateApplicationReviewStatus(id, reviewStatus);
            return ResponseEntity.ok(responseDTO);
        } catch (ApplicationNotFoundException e) {
            logger.error("Application not found: {}", e.getMessage());
            throw e;
        } catch (InvalidApplicationStateException e) {
            logger.error("Invalid review status transition: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error updating application review status: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Processes an application by applying business rules and updating its status
     * 
     * @param id Application ID
     * @return ResponseEntity with the processed application data
     */
    @PostMapping("/{id}/process")
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<ApplicationResponseDTO> processApplication(
            @PathVariable("id") UUID id) {
        
        logger.info("Processing application with ID: {}", id);
        
        try {
            ApplicationResponseDTO responseDTO = applicationService.processApplication(id);
            return ResponseEntity.ok(responseDTO);
        } catch (ApplicationNotFoundException e) {
            logger.error("Application not found: {}", e.getMessage());
            throw e;
        } catch (InvalidApplicationStateException e) {
            logger.error("Invalid application state for processing: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error processing application: {}", e.getMessage());
            throw e;
        }
    }

    /**
     * Checks if an application is complete based on business rules
     * 
     * @param id Application ID
     * @return ResponseEntity with the completeness status
     */
    @GetMapping("/{id}/is-complete")
    @PreAuthorize("hasAnyRole('OPERATIONS_STAFF', 'SYSTEM_ADMIN')")
    public ResponseEntity<Boolean> isApplicationComplete(
            @PathVariable("id") UUID id) {
        
        logger.info("Checking completeness of application with ID: {}", id);
        
        try {
            boolean isComplete = applicationService.isApplicationComplete(id);
            return ResponseEntity.ok(isComplete);
        } catch (ApplicationNotFoundException e) {
            logger.error("Application not found: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            logger.error("Error checking application completeness: {}", e.getMessage());
            throw e;
        }
    }
}