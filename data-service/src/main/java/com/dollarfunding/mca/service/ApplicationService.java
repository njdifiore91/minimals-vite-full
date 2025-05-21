package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.service.ValidationService.ValidationResult;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

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
     * Creates a new application with the provided data.
     * 
     * @param applicationDTO The application data to create
     * @return The created application
     */
    Application createApplication(ApplicationRequestDTO applicationDTO);
    
    /**
     * Retrieves an application by its ID.
     * 
     * @param id The application ID
     * @return The application
     */
    Application getApplicationById(UUID id);
    
    /**
     * Retrieves all applications with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications
     */
    Page<Application> getAllApplications(Pageable pageable);
    
    /**
     * Retrieves applications by status with pagination.
     * 
     * @param status The application status to filter by
     * @param pageable The pagination information
     * @return Page of applications with the specified status
     */
    Page<Application> getApplicationsByStatus(ApplicationStatus status, Pageable pageable);
    
    /**
     * Retrieves applications by review status with pagination.
     * 
     * @param reviewStatus The review status to filter by
     * @param pageable The pagination information
     * @return Page of applications with the specified review status
     */
    Page<Application> getApplicationsByReviewStatus(ReviewStatus reviewStatus, Pageable pageable);
    
    /**
     * Retrieves applications created within a date range with pagination.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable The pagination information
     * @return Page of applications created within the specified date range
     */
    Page<Application> getApplicationsByCreationDateRange(LocalDateTime startDate, 
                                                       LocalDateTime endDate, 
                                                       Pageable pageable);
    
    /**
     * Updates an existing application with the provided data.
     * 
     * @param id The application ID
     * @param applicationDTO The updated application data
     * @return The updated application
     */
    Application updateApplication(UUID id, ApplicationRequestDTO applicationDTO);
    
    /**
     * Updates the status of an application.
     * 
     * @param id The application ID
     * @param newStatus The new status to set
     * @return The updated application
     */
    Application updateApplicationStatus(UUID id, ApplicationStatus newStatus);
    
    /**
     * Updates the review status of an application.
     * 
     * @param id The application ID
     * @param newReviewStatus The new review status to set
     * @return The updated application
     */
    Application updateApplicationReviewStatus(UUID id, ReviewStatus newReviewStatus);
    
    /**
     * Deletes an application by its ID.
     * 
     * @param id The application ID
     */
    void deleteApplication(UUID id);
    
    /**
     * Adds a document to an application.
     * 
     * @param applicationId The application ID
     * @param document The document to add
     * @return The updated application
     */
    Application addDocumentToApplication(UUID applicationId, Document document);
    
    /**
     * Retrieves all documents associated with an application.
     * 
     * @param applicationId The application ID
     * @return List of documents associated with the application
     */
    List<Document> getApplicationDocuments(UUID applicationId);
    
    /**
     * Retrieves documents of a specific type associated with an application.
     * 
     * @param applicationId The application ID
     * @param documentType The document type to filter by
     * @return List of documents of the specified type associated with the application
     */
    List<Document> getApplicationDocumentsByType(UUID applicationId, DocumentType documentType);
    
    /**
     * Processes a document for an application.
     * 
     * @param applicationId The application ID
     * @param documentId The document ID
     * @param extractedData The data extracted from the document
     * @param confidenceScores The confidence scores for the extracted data
     * @return The updated application
     */
    Application processDocument(UUID applicationId, UUID documentId, 
                              Map<String, Object> extractedData,
                              Map<String, Double> confidenceScores);
    
    /**
     * Evaluates the status of an application based on its documents and validation rules.
     * 
     * @param applicationId The application ID
     * @return The updated application
     */
    Application evaluateApplicationStatus(UUID applicationId);
    
    /**
     * Validates an application against business rules.
     * 
     * @param applicationId The application ID
     * @return The validation result
     */
    ValidationResult validateApplication(UUID applicationId);
    
    /**
     * Checks if an application has all required documents.
     * 
     * @param applicationId The application ID
     * @return true if the application has all required documents, false otherwise
     */
    boolean hasAllRequiredDocuments(UUID applicationId);
    
    /**
     * Calculates the processing time of an application in minutes.
     * 
     * @param applicationId The application ID
     * @return The processing time in minutes, or -1 if the application is not completed
     */
    long getApplicationProcessingTime(UUID applicationId);
    
    /**
     * Checks if an application was processed within the target time (5 minutes).
     * 
     * @param applicationId The application ID
     * @return true if the application was processed within the target time, false otherwise
     */
    boolean isApplicationProcessedWithinTargetTime(UUID applicationId);
    
    /**
     * Counts the number of applications with a specific status.
     * 
     * @param status The application status to count
     * @return The number of applications with the specified status
     */
    long countApplicationsByStatus(ApplicationStatus status);
    
    /**
     * Counts the number of applications with a specific review status.
     * 
     * @param reviewStatus The review status to count
     * @return The number of applications with the specified review status
     */
    long countApplicationsByReviewStatus(ReviewStatus reviewStatus);
    
    /**
     * Calculates the average processing time (in minutes) for completed applications.
     * 
     * @return The average processing time in minutes
     */
    double calculateAverageProcessingTime();
    
    /**
     * Calculates the average processing time (in minutes) for completed applications within a date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return The average processing time in minutes
     */
    double calculateAverageProcessingTime(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Retrieves applications that require review with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications that require review
     */
    Page<Application> getApplicationsRequiringReview(Pageable pageable);
    
    /**
     * Retrieves active applications with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of active applications
     */
    Page<Application> getActiveApplications(Pageable pageable);
    
    /**
     * Retrieves applications that have been decided upon with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of decided applications
     */
    Page<Application> getDecidedApplications(Pageable pageable);
    
    /**
     * Retrieves applications that were processed within the target time (5 minutes) with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications processed within the target time
     */
    Page<Application> getApplicationsProcessedWithinTargetTime(Pageable pageable);
    
    /**
     * Retrieves applications that exceeded the target processing time (5 minutes) with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications that exceeded the target processing time
     */
    Page<Application> getApplicationsExceedingTargetTime(Pageable pageable);
    
    /**
     * Retrieves applications with merchant details in a specific industry with pagination.
     * 
     * @param industry The industry to filter by
     * @param pageable The pagination information
     * @return Page of applications with merchant details in the specified industry
     */
    Page<Application> getApplicationsByMerchantIndustry(String industry, Pageable pageable);
    
    /**
     * Retrieves applications with merchant details in a specific state with pagination.
     * 
     * @param state The state to filter by (2-letter code)
     * @param pageable The pagination information
     * @return Page of applications with merchant details in the specified state
     */
    Page<Application> getApplicationsByMerchantState(String state, Pageable pageable);
    
    /**
     * Retrieves applications with metadata containing a specific key-value pair with pagination.
     * 
     * @param key The metadata key
     * @param value The metadata value
     * @param pageable The pagination information
     * @return Page of applications with metadata containing the specified key-value pair
     */
    Page<Application> getApplicationsByMetadata(String key, Object value, Pageable pageable);
}