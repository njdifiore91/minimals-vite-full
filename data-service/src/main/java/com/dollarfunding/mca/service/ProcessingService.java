package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.exception.ProcessingException;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Service interface that defines the contract for application processing workflows in the MCA application.
 * This service orchestrates the processing of new applications, updates to existing applications with new documents,
 * and manages the application lifecycle from submission to completion.
 */
public interface ProcessingService {

    /**
     * Process a new application with the provided document data.
     * This method creates a new application record, associates the document data,
     * applies business rules, and initiates the application workflow.
     *
     * @param documentId The ID of the document that triggered the new application
     * @param extractedData Map containing the extracted data from the document
     * @return The created application response DTO
     * @throws ProcessingException if an error occurs during processing
     */
    ApplicationResponseDTO processNewApplication(UUID documentId, Map<String, Object> extractedData) throws ProcessingException;

    /**
     * Update an existing application with new document data.
     * This method associates the new document with the application,
     * updates the application data based on the document content,
     * and advances the application workflow as appropriate.
     *
     * @param applicationId The ID of the application to update
     * @param documentId The ID of the new document
     * @param extractedData Map containing the extracted data from the document
     * @return The updated application response DTO
     * @throws ProcessingException if an error occurs during processing
     */
    ApplicationResponseDTO updateApplicationWithDocument(UUID applicationId, UUID documentId, Map<String, Object> extractedData) throws ProcessingException;

    /**
     * Process a document and determine if it belongs to an existing application or requires a new application.
     * This method analyzes the document content, attempts to match it with existing applications,
     * and either creates a new application or updates an existing one.
     *
     * @param documentId The ID of the document to process
     * @param extractedData Map containing the extracted data from the document
     * @return The application response DTO (either new or updated)
     * @throws ProcessingException if an error occurs during processing
     */
    ApplicationResponseDTO processDocument(UUID documentId, Map<String, Object> extractedData) throws ProcessingException;

    /**
     * Update the status of an application and perform any required actions for the new status.
     * This method validates the status transition, updates the application record,
     * and triggers any necessary notifications or follow-up actions.
     *
     * @param applicationId The ID of the application to update
     * @param newStatus The new status to set
     * @param metadata Optional metadata related to the status change
     * @return The updated application response DTO
     * @throws ProcessingException if the status transition is invalid or an error occurs
     */
    ApplicationResponseDTO updateApplicationStatus(UUID applicationId, ApplicationStatus newStatus, Map<String, Object> metadata) throws ProcessingException;

    /**
     * Check if an application is complete based on required documents and data.
     * This method evaluates the application against business rules to determine
     * if all required information has been provided.
     *
     * @param applicationId The ID of the application to check
     * @return true if the application is complete, false otherwise
     * @throws ProcessingException if an error occurs during the check
     */
    boolean isApplicationComplete(UUID applicationId) throws ProcessingException;

    /**
     * Get the processing status of an application, including any pending requirements.
     * This method provides detailed information about the current processing state,
     * including validation results and missing information.
     *
     * @param applicationId The ID of the application to check
     * @return Map containing the processing status details
     * @throws ProcessingException if an error occurs during the check
     */
    Map<String, Object> getProcessingStatus(UUID applicationId) throws ProcessingException;

    /**
     * Get a list of documents required for an application to be considered complete.
     * This method evaluates the application's current state and returns a list of
     * document types that are still needed.
     *
     * @param applicationId The ID of the application to check
     * @return List of required document types that are still needed
     * @throws ProcessingException if an error occurs during the check
     */
    List<String> getRequiredDocuments(UUID applicationId) throws ProcessingException;

    /**
     * Reprocess an application to apply updated business rules or fix processing errors.
     * This method reevaluates all documents and data associated with the application
     * and updates the application state accordingly.
     *
     * @param applicationId The ID of the application to reprocess
     * @return The updated application response DTO
     * @throws ProcessingException if an error occurs during reprocessing
     */
    ApplicationResponseDTO reprocessApplication(UUID applicationId) throws ProcessingException;

    /**
     * Handle an exception that occurred during document processing.
     * This method logs the error, updates the application status if applicable,
     * and triggers any necessary notifications or recovery actions.
     *
     * @param documentId The ID of the document being processed when the error occurred
     * @param applicationId The ID of the associated application, if any
     * @param exception The exception that occurred
     * @param metadata Additional metadata about the processing context
     * @throws ProcessingException if an error occurs while handling the exception
     */
    void handleProcessingException(UUID documentId, UUID applicationId, Exception exception, Map<String, Object> metadata) throws ProcessingException;

    /**
     * Get all documents associated with an application.
     * This method retrieves the complete list of documents linked to the application,
     * including their metadata and processing status.
     *
     * @param applicationId The ID of the application
     * @return List of document response DTOs
     * @throws ProcessingException if an error occurs during retrieval
     */
    List<DocumentResponseDTO> getApplicationDocuments(UUID applicationId) throws ProcessingException;

    /**
     * Apply business rules to an application and update its status accordingly.
     * This method evaluates the application against configured business rules
     * and updates the application status based on the evaluation results.
     *
     * @param applicationId The ID of the application to evaluate
     * @return The updated application response DTO
     * @throws ProcessingException if an error occurs during rule application
     */
    ApplicationResponseDTO applyBusinessRules(UUID applicationId) throws ProcessingException;
}