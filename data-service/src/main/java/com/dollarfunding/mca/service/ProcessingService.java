package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.exception.ProcessingException;

import java.util.List;
import java.util.Map;

/**
 * Service interface that defines the contract for application processing workflows in the MCA application.
 * It provides methods for processing new applications, updating existing applications with new documents,
 * and managing the application lifecycle from submission to completion.
 */
public interface ProcessingService {

    /**
     * Processes a new application with the provided document data.
     * This method orchestrates the complete workflow for a new application:
     * - Validates document data
     * - Creates a new application record
     * - Associates documents with the application
     * - Applies business rules to determine application status
     * - Sends appropriate notifications
     *
     * @param documentId The ID of the initial document that triggered the application creation
     * @param extractedData Map containing the extracted data from the document
     * @return The created application with processing results
     * @throws ProcessingException if an error occurs during processing
     */
    ApplicationResponseDTO processNewApplication(Long documentId, Map<String, Object> extractedData) throws ProcessingException;

    /**
     * Updates an existing application with new document data.
     * This method handles the workflow for adding new documents to an existing application:
     * - Validates the new document data
     * - Associates the document with the existing application
     * - Updates application data based on the new document
     * - Re-evaluates application status based on business rules
     * - Sends appropriate notifications
     *
     * @param applicationId The ID of the existing application
     * @param documentId The ID of the new document
     * @param extractedData Map containing the extracted data from the document
     * @return The updated application with processing results
     * @throws ProcessingException if an error occurs during processing
     */
    ApplicationResponseDTO updateApplicationWithDocument(Long applicationId, Long documentId, Map<String, Object> extractedData) throws ProcessingException;

    /**
     * Processes a document that has been classified and had data extracted.
     * This method determines if the document belongs to a new or existing application
     * and routes it to the appropriate processing method.
     *
     * @param documentId The ID of the document to process
     * @param extractedData Map containing the extracted data from the document
     * @return The application associated with the document after processing
     * @throws ProcessingException if an error occurs during processing
     */
    ApplicationResponseDTO processDocument(Long documentId, Map<String, Object> extractedData) throws ProcessingException;

    /**
     * Updates the status of an application and performs any necessary actions based on the new status.
     * This method handles the application lifecycle transitions:
     * - Validates the status transition is allowed
     * - Updates the application status
     * - Performs any status-specific processing
     * - Sends appropriate notifications
     *
     * @param applicationId The ID of the application to update
     * @param newStatus The new status to set
     * @param statusMetadata Additional metadata related to the status change
     * @return The updated application
     * @throws ProcessingException if the status transition is invalid or processing fails
     */
    ApplicationResponseDTO updateApplicationStatus(Long applicationId, ApplicationStatus newStatus, Map<String, Object> statusMetadata) throws ProcessingException;

    /**
     * Retrieves the current processing status of an application.
     * This method provides detailed information about the application's processing state,
     * including any pending tasks, validation results, and processing history.
     *
     * @param applicationId The ID of the application
     * @return Map containing the processing status details
     * @throws ProcessingException if the application is not found or status retrieval fails
     */
    Map<String, Object> getApplicationProcessingStatus(Long applicationId) throws ProcessingException;

    /**
     * Handles an exception that occurred during application processing.
     * This method provides a standardized way to handle and recover from processing errors:
     * - Logs the exception details
     * - Updates the application status to reflect the error
     * - Attempts recovery if possible
     * - Notifies administrators of critical errors
     *
     * @param applicationId The ID of the application where the exception occurred
     * @param exception The exception that occurred
     * @param processingContext Additional context about the processing stage where the exception occurred
     * @return The updated application with error handling results
     */
    ApplicationResponseDTO handleProcessingException(Long applicationId, Exception exception, Map<String, Object> processingContext);

    /**
     * Reprocesses an application that previously encountered errors or requires manual intervention.
     * This method allows for recovery from processing failures:
     * - Identifies the failed processing step
     * - Restarts processing from that step
     * - Applies any manual corrections or overrides
     * - Updates the application status based on reprocessing results
     *
     * @param applicationId The ID of the application to reprocess
     * @param overrideData Optional data to override extracted values during reprocessing
     * @return The reprocessed application
     * @throws ProcessingException if reprocessing fails
     */
    ApplicationResponseDTO reprocessApplication(Long applicationId, Map<String, Object> overrideData) throws ProcessingException;

    /**
     * Validates an application against business rules and data requirements.
     * This method performs comprehensive validation:
     * - Schema validation of all application data
     * - Business rule application
     * - Document completeness checks
     * - Required field validation
     *
     * @param applicationId The ID of the application to validate
     * @return Validation results with any errors or warnings
     * @throws ProcessingException if validation processing fails
     */
    Map<String, Object> validateApplication(Long applicationId) throws ProcessingException;

    /**
     * Checks if an application is complete and ready for final processing.
     * This method evaluates application completeness based on:
     * - Required documents presence
     * - Required data fields completion
     * - Business rule satisfaction
     * - Validation status
     *
     * @param applicationId The ID of the application to check
     * @return true if the application is complete, false otherwise with reasons in the metadata
     * @throws ProcessingException if completeness check fails
     */
    boolean isApplicationComplete(Long applicationId, Map<String, Object> metadata) throws ProcessingException;

    /**
     * Retrieves all documents associated with an application.
     * This method provides a comprehensive view of all documents related to an application,
     * including their processing status and extracted data.
     *
     * @param applicationId The ID of the application
     * @return List of documents associated with the application
     * @throws ProcessingException if document retrieval fails
     */
    List<DocumentResponseDTO> getApplicationDocuments(Long applicationId) throws ProcessingException;
}