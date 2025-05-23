package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ApplicationNotFoundException;
import com.dollarfunding.mca.exception.InvalidApplicationStateException;
import com.dollarfunding.mca.exception.ValidationException;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

/**
 * Service interface that defines the contract for managing MCA applications.
 * It provides methods for creating, retrieving, updating, and processing applications.
 */
public interface ApplicationService {

    /**
     * Creates a new MCA application with the provided data.
     *
     * @param applicationRequestDTO DTO containing application data
     * @return ApplicationResponseDTO with the created application data
     * @throws ValidationException if the application data fails validation
     */
    ApplicationResponseDTO createApplication(ApplicationRequestDTO applicationRequestDTO);

    /**
     * Retrieves an application by its ID.
     *
     * @param id Application ID
     * @return ApplicationResponseDTO with the application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    ApplicationResponseDTO getApplicationById(Long id);

    /**
     * Updates an existing application with the provided data.
     *
     * @param id Application ID
     * @param applicationRequestDTO DTO containing updated application data
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     * @throws ValidationException if the updated application data fails validation
     */
    ApplicationResponseDTO updateApplication(Long id, ApplicationRequestDTO applicationRequestDTO);

    /**
     * Deletes an application by its ID.
     *
     * @param id Application ID
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    void deleteApplication(Long id);

    /**
     * Retrieves a paginated list of applications based on filter criteria.
     *
     * @param filterDTO DTO containing filter criteria
     * @param pageable Pagination information
     * @return Page of ApplicationResponseDTO objects
     */
    Page<ApplicationResponseDTO> getApplications(ApplicationFilterDTO filterDTO, Pageable pageable);

    /**
     * Updates the status of an application.
     *
     * @param id Application ID
     * @param status New application status
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     * @throws InvalidApplicationStateException if the status transition is invalid
     */
    ApplicationResponseDTO updateApplicationStatus(Long id, ApplicationStatus status);

    /**
     * Updates the review status of an application.
     *
     * @param id Application ID
     * @param reviewStatus New review status
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    ApplicationResponseDTO updateApplicationReviewStatus(Long id, ReviewStatus reviewStatus);

    /**
     * Adds a document to an application.
     *
     * @param applicationId Application ID
     * @param document Document entity to add
     * @return ApplicationResponseDTO with the updated application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    ApplicationResponseDTO addDocumentToApplication(Long applicationId, Document document);

    /**
     * Evaluates the completeness of an application based on business rules.
     *
     * @param id Application ID
     * @return true if the application is complete, false otherwise
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    boolean isApplicationComplete(Long id);

    /**
     * Processes an application by applying business rules and updating its status.
     *
     * @param id Application ID
     * @return ApplicationResponseDTO with the processed application data
     * @throws ApplicationNotFoundException if no application is found with the given ID
     */
    ApplicationResponseDTO processApplication(Long id);
}