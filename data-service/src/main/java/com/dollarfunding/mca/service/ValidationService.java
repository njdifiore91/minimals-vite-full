package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;

import java.util.List;
import java.util.Map;

/**
 * Service interface that defines the contract for data validation and business rule application
 * in the MCA application. It provides methods for validating application data, document data,
 * and merchant details against predefined schemas and business rules.
 * 
 * This service is responsible for:
 * 1. Validating data against predefined schemas
 * 2. Applying business rules to determine application status
 * 3. Validating document data for completeness and accuracy
 * 4. Ensuring data integrity across the application
 * 5. Reporting validation results with detailed error messages
 */
public interface ValidationService {

    /**
     * Validates application data against predefined schemas and business rules.
     *
     * @param applicationDTO The application data to validate
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateApplicationData(ApplicationRequestDTO applicationDTO);

    /**
     * Validates document data against predefined schemas and business rules.
     *
     * @param documentDTO The document data to validate
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateDocumentData(DocumentRequestDTO documentDTO);

    /**
     * Validates merchant details against predefined schemas and business rules.
     *
     * @param merchantDetailsDTO The merchant details to validate
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateMerchantDetails(MerchantDetailsRequestDTO merchantDetailsDTO);

    /**
     * Validates an existing application entity against business rules.
     *
     * @param application The application entity to validate
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateApplication(Application application);

    /**
     * Validates an existing document entity against business rules.
     *
     * @param document The document entity to validate
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateDocument(Document document);

    /**
     * Validates existing merchant details entity against business rules.
     *
     * @param merchantDetails The merchant details entity to validate
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateMerchant(MerchantDetails merchantDetails);

    /**
     * Applies business rules to determine if an application is complete and ready for processing.
     *
     * @param application The application to evaluate
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult evaluateApplicationCompleteness(Application application);

    /**
     * Applies business rules to determine the appropriate application status based on
     * the current application data and associated documents.
     *
     * @param application The application to evaluate
     * @return The recommended application status based on business rules
     */
    ApplicationStatus determineApplicationStatus(Application application);
    
    /**
     * Applies business rules to determine the appropriate review status based on
     * the current application data and associated documents.
     *
     * @param application The application to evaluate
     * @return The recommended review status based on business rules
     */
    ReviewStatus determineReviewStatus(Application application);

    /**
     * Validates OCR-extracted data against expected schemas for the given document type.
     *
     * @param documentType The type of document being validated
     * @param extractedData The data extracted from the document by OCR
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateExtractedData(DocumentType documentType, Map<String, Object> extractedData);
    
    /**
     * Validates OCR-extracted data against expected schemas for the given document type,
     * with confidence scores for each extracted field.
     *
     * @param documentType The type of document being validated
     * @param extractedData The data extracted from the document by OCR
     * @param confidenceScores Map of field names to confidence scores (0.0-1.0)
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateExtractedDataWithConfidence(DocumentType documentType, 
                                                       Map<String, Object> extractedData,
                                                       Map<String, Double> confidenceScores);
    
    /**
     * Validates a set of documents to ensure all required document types are present
     * for a complete application.
     *
     * @param documents List of documents associated with an application
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateRequiredDocuments(List<Document> documents);

    /**
     * Validates business rules for a merchant cash advance application.
     * 
     * @param application The application to validate
     * @param merchantDetails The merchant details associated with the application
     * @param documents The documents associated with the application
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateBusinessRules(Application application, 
                                         MerchantDetails merchantDetails,
                                         List<Document> documents);
                                         
    /**
     * Validates that the application meets the minimum requirements for approval.
     * 
     * @param application The application to validate
     * @param merchantDetails The merchant details associated with the application
     * @param documents The documents associated with the application
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateApprovalRequirements(Application application,
                                                MerchantDetails merchantDetails,
                                                List<Document> documents);
                                                
    /**
     * Validates that the application data is consistent with the data extracted from documents.
     * 
     * @param application The application to validate
     * @param extractedDataMap Map of document types to their extracted data
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateApplicationDataConsistency(Application application,
                                                      Map<DocumentType, Map<String, Object>> extractedDataMap);
    
    /**
     * Validates that the extracted data from documents is consistent with the
     * merchant details provided in the application.
     *
     * @param merchantDetails The merchant details to validate
     * @param extractedDataMap Map of document types to their extracted data
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateDataConsistency(MerchantDetails merchantDetails,
                                           Map<DocumentType, Map<String, Object>> extractedDataMap);
                                           
    /**
     * Validates the quality and confidence of OCR-extracted data.
     * 
     * @param extractedDataMap Map of document types to their extracted data
     * @param confidenceScoresMap Map of document types to confidence scores for each field
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateDataQuality(Map<DocumentType, Map<String, Object>> extractedDataMap,
                                        Map<DocumentType, Map<String, Double>> confidenceScoresMap);
                                        
    /**
     * Validates that the document classification is correct based on the document content.
     * 
     * @param document The document to validate
     * @param extractedData The data extracted from the document
     * @return ValidationResult containing validation status and error messages if any
     */
    ValidationResult validateDocumentClassification(Document document, Map<String, Object> extractedData);
    
    /**
     * Gets the validation schema for a specific document type.
     * 
     * @param documentType The document type to get the schema for
     * @return The validation schema as a Map of field names to validation rules
     */
    Map<String, Object> getDocumentValidationSchema(DocumentType documentType);
    
    /**
     * Represents the result of a validation operation, including validation status and error messages.
     */
    class ValidationResult {
        private final boolean valid;
        private final Map<String, String> errors;
        private final ValidationSeverity severity;

        /**
         * Creates a new ValidationResult with the specified validation status and error messages.
         *
         * @param valid Whether the validation passed (true) or failed (false)
         * @param errors Map of field names to error messages, empty if validation passed
         */
        public ValidationResult(boolean valid, Map<String, String> errors) {
            this.valid = valid;
            this.errors = errors;
            this.severity = valid ? ValidationSeverity.NONE : ValidationSeverity.ERROR;
        }
        
        /**
         * Creates a new ValidationResult with the specified validation status, error messages, and severity.
         *
         * @param valid Whether the validation passed (true) or failed (false)
         * @param errors Map of field names to error messages, empty if validation passed
         * @param severity The severity of the validation result
         */
        public ValidationResult(boolean valid, Map<String, String> errors, ValidationSeverity severity) {
            this.valid = valid;
            this.errors = errors;
            this.severity = severity;
        }

        /**
         * Returns whether the validation passed.
         *
         * @return true if validation passed, false otherwise
         */
        public boolean isValid() {
            return valid;
        }

        /**
         * Returns the map of field names to error messages.
         *
         * @return Map of field names to error messages, empty if validation passed
         */
        public Map<String, String> getErrors() {
            return errors;
        }
        
        /**
         * Returns the severity of the validation result.
         *
         * @return The severity of the validation result
         */
        public ValidationSeverity getSeverity() {
            return severity;
        }

        /**
         * Returns a string representation of the validation result.
         *
         * @return String representation of the validation result
         */
        @Override
        public String toString() {
            return "ValidationResult{" +
                    "valid=" + valid +
                    ", errors=" + errors +
                    ", severity=" + severity +
                    '}';
        }
    }
    
    /**
     * Enum representing the severity of a validation result.
     */
    enum ValidationSeverity {
        /**
         * No validation issues.
         */
        NONE,
        
        /**
         * Warning-level validation issues that don't prevent processing.
         */
        WARNING,
        
        /**
         * Error-level validation issues that prevent processing.
         */
        ERROR,
        
        /**
         * Critical validation issues that require immediate attention.
         */
        CRITICAL
    }
}