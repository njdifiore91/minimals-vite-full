package com.dollarfunding.mca.service;

import com.dollarfunding.mca.messaging.DocumentProcessingMessage;

/**
 * Service interface that defines the contract for application processing workflows in the MCA application.
 * It provides methods for processing new applications, updating existing applications with new documents,
 * and managing the application lifecycle.
 */
public interface ProcessingService {

    /**
     * Processes a new application based on document data extracted by the OCR service.
     * This method creates a new application record, associates the document with it,
     * and applies business rules to determine the initial application status.
     *
     * @param message The document processing message containing extracted data
     * @return The ID of the created application
     */
    String processNewApplication(DocumentProcessingMessage message);

    /**
     * Updates an existing application with new document data.
     * This method associates the new document with the existing application,
     * updates application data based on the document content, and re-evaluates
     * the application status based on business rules.
     *
     * @param message The document processing message containing extracted data
     * @return The ID of the updated application
     */
    String updateExistingApplication(DocumentProcessingMessage message);

    /**
     * Processes a supporting document for an existing application.
     * This method associates the document with the application but does not
     * update the application data directly. It may trigger status changes
     * if the document completes a required document set.
     *
     * @param message The document processing message containing extracted data
     * @return The ID of the associated application
     */
    String processSupportingDocument(DocumentProcessingMessage message);

    /**
     * Evaluates the completeness of an application based on its associated documents.
     * This method applies business rules to determine if the application has all
     * required documents and data for processing.
     *
     * @param applicationId The ID of the application to evaluate
     * @return true if the application is complete, false otherwise
     */
    boolean evaluateApplicationCompleteness(String applicationId);

    /**
     * Updates the status of an application based on processing results.
     * This method applies business rules to determine the appropriate status
     * and triggers notifications for status changes.
     *
     * @param applicationId The ID of the application to update
     * @param status The new status to set
     * @param reason The reason for the status change
     * @return true if the status was updated successfully, false otherwise
     */
    boolean updateApplicationStatus(String applicationId, String status, String reason);
}