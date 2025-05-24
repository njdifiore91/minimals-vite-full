package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.MerchantDetails;

import java.util.Map;
import java.util.List;

/**
 * Service interface that defines the contract for data validation and business rule application
 * in the MCA application. It provides methods for validating application data, document data,
 * and merchant details against predefined schemas and business rules.
 */
public interface ValidationService {

    /**
     * Validates application data against predefined schemas.
     *
     * @param applicationRequestDTO The application data to validate
     * @return Map containing validation results with field names as keys and error messages as values.
     *         Empty map indicates successful validation.
     */
    Map<String, String> validateApplicationData(ApplicationRequestDTO applicationRequestDTO);

    /**
     * Validates document data against predefined schemas based on document type.
     *
     * @param documentRequestDTO The document data to validate
     * @return Map containing validation results with field names as keys and error messages as values.
     *         Empty map indicates successful validation.
     */
    Map<String, String> validateDocumentData(DocumentRequestDTO documentRequestDTO);

    /**
     * Validates merchant details against predefined schemas.
     *
     * @param merchantDetailsRequestDTO The merchant details to validate
     * @return Map containing validation results with field names as keys and error messages as values.
     *         Empty map indicates successful validation.
     */
    Map<String, String> validateMerchantDetails(MerchantDetailsRequestDTO merchantDetailsRequestDTO);

    /**
     * Applies business rules to determine application status based on application data,
     * associated documents, and merchant details.
     *
     * @param application The application entity
     * @param documents List of associated document entities
     * @param merchantDetails The merchant details entity
     * @return Map containing business rule results with rule identifiers as keys and result messages as values.
     *         Empty map indicates all business rules passed.
     */
    Map<String, String> applyBusinessRules(Application application, List<Document> documents, MerchantDetails merchantDetails);

    /**
     * Validates the completeness of an application by checking if all required documents
     * and merchant details are present and valid.
     *
     * @param application The application entity
     * @param documents List of associated document entities
     * @param merchantDetails The merchant details entity
     * @return true if the application is complete, false otherwise
     */
    boolean isApplicationComplete(Application application, List<Document> documents, MerchantDetails merchantDetails);

    /**
     * Validates document classification confidence scores against threshold values.
     *
     * @param document The document entity containing classification metadata
     * @return true if the classification confidence is above the threshold, false otherwise
     */
    boolean isDocumentClassificationValid(Document document);

    /**
     * Validates OCR extraction confidence scores against threshold values.
     *
     * @param document The document entity containing OCR extraction metadata
     * @return Map containing field names as keys and boolean values indicating if the extraction
     *         confidence is above the threshold for each field
     */
    Map<String, Boolean> validateOcrExtractionConfidence(Document document);

    /**
     * Validates the consistency of merchant details across multiple documents.
     *
     * @param merchantDetails The merchant details entity
     * @param documents List of documents containing merchant information
     * @return Map containing field names as keys and consistency status as values.
     *         Empty map indicates all fields are consistent.
     */
    Map<String, String> validateMerchantConsistency(MerchantDetails merchantDetails, List<Document> documents);

    /**
     * Generates a detailed validation report for an application, including all validation results
     * and business rule applications.
     *
     * @param application The application entity
     * @param documents List of associated document entities
     * @param merchantDetails The merchant details entity
     * @return Map containing validation report sections as keys and detailed results as values
     */
    Map<String, Object> generateValidationReport(Application application, List<Document> documents, MerchantDetails merchantDetails);

    /**
     * Validates the transition of an application from one status to another based on business rules.
     *
     * @param application The application entity
     * @param newStatus The target status for the application
     * @return true if the status transition is valid, false otherwise
     */
    boolean isStatusTransitionValid(Application application, String newStatus);

    /**
     * Validates the transition of an application from one review status to another based on business rules.
     *
     * @param application The application entity
     * @param newReviewStatus The target review status for the application
     * @return true if the review status transition is valid, false otherwise
     */
    boolean isReviewStatusTransitionValid(Application application, String newReviewStatus);

    /**
     * Validates if a document type is required for a specific application based on business rules.
     *
     * @param application The application entity
     * @param documentType The document type to check
     * @return true if the document type is required, false otherwise
     */
    boolean isDocumentTypeRequired(Application application, String documentType);

    /**
     * Validates if all required document types are present for an application.
     *
     * @param application The application entity
     * @param documents List of associated document entities
     * @return Map containing missing document types as keys and requirement messages as values.
     *         Empty map indicates all required document types are present.
     */
    Map<String, String> validateRequiredDocuments(Application application, List<Document> documents);

    /**
     * Validates if the merchant revenue meets the minimum threshold for approval.
     *
     * @param merchantDetails The merchant details entity
     * @return true if the revenue meets the minimum threshold, false otherwise
     */
    boolean isRevenueThresholdMet(MerchantDetails merchantDetails);

    /**
     * Validates if the merchant industry is eligible for funding based on business rules.
     *
     * @param merchantDetails The merchant details entity
     * @return true if the industry is eligible, false otherwise
     */
    boolean isIndustryEligible(MerchantDetails merchantDetails);

    /**
     * Validates if the application meets all criteria for automatic approval.
     *
     * @param application The application entity
     * @param documents List of associated document entities
     * @param merchantDetails The merchant details entity
     * @return true if the application can be automatically approved, false otherwise
     */
    boolean canAutoApprove(Application application, List<Document> documents, MerchantDetails merchantDetails);

    /**
     * Validates if the application requires manual review based on business rules.
     *
     * @param application The application entity
     * @param documents List of associated document entities
     * @param merchantDetails The merchant details entity
     * @return true if manual review is required, false otherwise
     */
    boolean requiresManualReview(Application application, List<Document> documents, MerchantDetails merchantDetails);
}