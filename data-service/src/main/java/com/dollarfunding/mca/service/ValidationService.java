package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.exception.ValidationException;

/**
 * Service interface that defines the contract for data validation and business rule application
 * in the MCA application.
 * <p>
 * Provides methods for validating application data, document data, and merchant details against
 * predefined schemas and business rules. This interface is implemented by ValidationServiceImpl
 * and used by other services to ensure data integrity and business rule compliance.
 * </p>
 */
public interface ValidationService {

    /**
     * Validates merchant data against predefined schemas and business rules.
     *
     * @param merchantDetailsRequestDTO The merchant data to validate
     * @throws ValidationException if validation fails
     */
    void validateMerchantData(MerchantDetailsRequestDTO merchantDetailsRequestDTO) throws ValidationException;

    /**
     * Validates application data against predefined schemas and business rules.
     *
     * @param applicationData The application data to validate
     * @throws ValidationException if validation fails
     */
    void validateApplicationData(Object applicationData) throws ValidationException;

    /**
     * Validates document data against predefined schemas and business rules.
     *
     * @param documentData The document data to validate
     * @throws ValidationException if validation fails
     */
    void validateDocumentData(Object documentData) throws ValidationException;

    /**
     * Applies business rules to determine if an application is complete and ready for processing.
     *
     * @param applicationId The ID of the application to check
     * @return true if the application is complete, false otherwise
     */
    boolean isApplicationComplete(Object applicationId);

    /**
     * Validates that all required documents are present for an application.
     *
     * @param applicationId The ID of the application to check
     * @return true if all required documents are present, false otherwise
     */
    boolean hasRequiredDocuments(Object applicationId);
}