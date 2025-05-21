package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.dto.MerchantDetailsResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;

import java.util.List;

/**
 * Service interface that defines the contract for managing Merchant Cash Advance (MCA) applications.
 * It provides methods for creating, retrieving, updating, and processing applications,
 * as well as managing application status and workflow.
 * 
 * This interface is implemented by ApplicationServiceImpl and used by ApplicationController
 * to handle application-related business logic.
 */
public interface ApplicationService {
    
    /**
     * Creates a new MCA application with the provided data.
     *
     * @param applicationRequestDTO The DTO containing application data
     * @return The created application as a response DTO
     */
    ApplicationResponseDTO createApplication(ApplicationRequestDTO applicationRequestDTO);
    
    /**
     * Retrieves an application by its ID.
     *
     * @param id The application ID
     * @return The application as a response DTO
     */
    ApplicationResponseDTO getApplicationById(Long id);
    
    /**
     * Updates an existing application with the provided data.
     *
     * @param id The application ID
     * @param applicationRequestDTO The DTO containing updated application data
     * @return The updated application as a response DTO
     */
    ApplicationResponseDTO updateApplication(Long id, ApplicationRequestDTO applicationRequestDTO);
    
    /**
     * Deletes an application by its ID.
     *
     * @param id The application ID
     * @return true if the application was successfully deleted, false otherwise
     */
    boolean deleteApplication(Long id);
    
    /**
     * Retrieves a paginated list of applications based on filter criteria.
     *
     * @param filterDTO The DTO containing filter criteria
     * @return A paginated response containing applications that match the filter criteria
     */
    PageResponseDTO<ApplicationResponseDTO> getApplications(ApplicationFilterDTO filterDTO);
    
    /**
     * Updates the status of an application.
     *
     * @param id The application ID
     * @param status The new application status
     * @return The updated application as a response DTO
     */
    ApplicationResponseDTO updateApplicationStatus(Long id, ApplicationStatus status);
    
    /**
     * Updates the review status of an application.
     *
     * @param id The application ID
     * @param reviewStatus The new review status
     * @return The updated application as a response DTO
     */
    ApplicationResponseDTO updateReviewStatus(Long id, ReviewStatus reviewStatus);
    
    /**
     * Processes an application with extracted document data.
     * This method applies business rules, validates data, and updates the application status.
     *
     * @param id The application ID
     * @param documentId The ID of the document containing extracted data
     * @return The processed application as a response DTO
     */
    ApplicationResponseDTO processApplication(Long id, Long documentId);
    
    /**
     * Evaluates the completeness of an application based on required documents and data.
     *
     * @param id The application ID
     * @return true if the application is complete, false otherwise
     */
    boolean isApplicationComplete(Long id);
    
    /**
     * Associates a document with an application.
     *
     * @param applicationId The application ID
     * @param documentId The document ID
     * @return The updated application as a response DTO
     */
    ApplicationResponseDTO associateDocument(Long applicationId, Long documentId);
    
    /**
     * Retrieves all documents associated with an application.
     *
     * @param applicationId The application ID
     * @return A list of document response DTOs
     */
    List<DocumentResponseDTO> getApplicationDocuments(Long applicationId);
    
    /**
     * Retrieves merchant details associated with an application.
     *
     * @param applicationId The application ID
     * @return The merchant details as a response DTO
     */
    MerchantDetailsResponseDTO getMerchantDetails(Long applicationId);
    
    /**
     * Validates an application against business rules and data requirements.
     * This method checks if the application data meets all validation criteria.
     *
     * @param id The application ID
     * @return true if the application is valid, false otherwise
     */
    boolean validateApplication(Long id);
    
    /**
     * Counts applications by status.
     * This method is useful for dashboard statistics and reporting.
     *
     * @return A map of application status to count
     */
    java.util.Map<ApplicationStatus, Long> countApplicationsByStatus();
    
    /**
     * Counts applications by review status.
     * This method is useful for dashboard statistics and reporting.
     *
     * @return A map of review status to count
     */
    java.util.Map<ReviewStatus, Long> countApplicationsByReviewStatus();
    
    /**
     * Retrieves applications that require attention based on business rules.
     * This includes applications with exceptions, missing documents, or other issues.
     *
     * @return A list of applications that require attention
     */
    List<ApplicationResponseDTO> getApplicationsRequiringAttention();
    
    /**
     * Processes a batch of applications in bulk.
     * This method is useful for background processing and batch operations.
     *
     * @param applicationIds A list of application IDs to process
     * @return The number of successfully processed applications
     */
    int processBatchApplications(List<Long> applicationIds);
}