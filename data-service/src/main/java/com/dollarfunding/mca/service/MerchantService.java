package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.dto.MerchantDetailsResponseDTO;
import com.dollarfunding.mca.entity.MerchantDetails;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Service interface that defines the contract for managing merchant details in the MCA application.
 * 
 * This service provides methods for creating, retrieving, updating, and validating merchant information
 * associated with applications. It handles the encryption and decryption of sensitive merchant data
 * and provides filtering options for merchant retrieval.
 */
public interface MerchantService {

    /**
     * Creates a new merchant details record associated with an application.
     *
     * @param applicationId The ID of the application to associate with the merchant details
     * @param merchantDetailsDTO The merchant details data to create
     * @return The created merchant details as a response DTO
     * @throws com.dollarfunding.mca.exception.ResourceNotFoundException if the application is not found
     * @throws com.dollarfunding.mca.exception.ValidationException if the merchant details data is invalid
     */
    MerchantDetailsResponseDTO createMerchantDetails(UUID applicationId, MerchantDetailsRequestDTO merchantDetailsDTO);

    /**
     * Retrieves merchant details by ID.
     *
     * @param id The ID of the merchant details to retrieve
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return An Optional containing the merchant details if found, or empty if not found
     */
    Optional<MerchantDetailsResponseDTO> getMerchantDetailsById(UUID id, boolean includeSensitiveData);

    /**
     * Retrieves merchant details by application ID.
     *
     * @param applicationId The ID of the application associated with the merchant details
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return An Optional containing the merchant details if found, or empty if not found
     */
    Optional<MerchantDetailsResponseDTO> getMerchantDetailsByApplicationId(UUID applicationId, boolean includeSensitiveData);

    /**
     * Updates an existing merchant details record.
     *
     * @param id The ID of the merchant details to update
     * @param merchantDetailsDTO The updated merchant details data
     * @return The updated merchant details as a response DTO
     * @throws com.dollarfunding.mca.exception.ResourceNotFoundException if the merchant details are not found
     * @throws com.dollarfunding.mca.exception.ValidationException if the updated merchant details data is invalid
     */
    MerchantDetailsResponseDTO updateMerchantDetails(UUID id, MerchantDetailsRequestDTO merchantDetailsDTO);

    /**
     * Validates merchant details data for completeness and accuracy.
     *
     * @param merchantDetailsDTO The merchant details data to validate
     * @return A map of validation errors, empty if validation passes
     */
    Map<String, String> validateMerchantDetails(MerchantDetailsRequestDTO merchantDetailsDTO);

    /**
     * Associates merchant details with an application.
     *
     * @param merchantId The ID of the merchant details to associate
     * @param applicationId The ID of the application to associate with
     * @return The updated merchant details as a response DTO
     * @throws com.dollarfunding.mca.exception.ResourceNotFoundException if either resource is not found
     */
    MerchantDetailsResponseDTO associateMerchantWithApplication(UUID merchantId, UUID applicationId);

    /**
     * Retrieves merchant details with filtering options.
     *
     * @param filters A map of filter criteria (e.g., industry, revenue range)
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return A list of merchant details matching the filter criteria
     */
    List<MerchantDetailsResponseDTO> getMerchantDetailsWithFilters(Map<String, Object> filters, boolean includeSensitiveData);

    /**
     * Encrypts sensitive merchant data.
     *
     * @param merchantDetails The merchant details entity containing data to encrypt
     * @return The merchant details entity with encrypted sensitive data
     */
    MerchantDetails encryptSensitiveData(MerchantDetails merchantDetails);

    /**
     * Decrypts sensitive merchant data.
     *
     * @param merchantDetails The merchant details entity containing data to decrypt
     * @return The merchant details entity with decrypted sensitive data
     */
    MerchantDetails decryptSensitiveData(MerchantDetails merchantDetails);

    /**
     * Checks if merchant details exist for an application.
     *
     * @param applicationId The ID of the application to check
     * @return true if merchant details exist for the application, false otherwise
     */
    boolean merchantDetailsExistForApplication(UUID applicationId);

    /**
     * Deletes merchant details by ID.
     *
     * @param id The ID of the merchant details to delete
     * @throws com.dollarfunding.mca.exception.ResourceNotFoundException if the merchant details are not found
     */
    void deleteMerchantDetails(UUID id);

    /**
     * Retrieves all merchant details.
     *
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return A list of all merchant details
     */
    List<MerchantDetailsResponseDTO> getAllMerchantDetails(boolean includeSensitiveData);

    /**
     * Searches for merchant details by legal name or DBA name.
     *
     * @param searchTerm The search term to match against legal name or DBA name
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return A list of merchant details matching the search term
     */
    List<MerchantDetailsResponseDTO> searchMerchantDetailsByName(String searchTerm, boolean includeSensitiveData);

    /**
     * Validates the address of a merchant for completeness and format.
     *
     * @param address The address map to validate
     * @return A map of validation errors, empty if validation passes
     */
    Map<String, String> validateAddress(Map<String, Object> address);

    /**
     * Retrieves merchant details by EIN (Employer Identification Number).
     *
     * @param ein The EIN to search for
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return A list of merchant details matching the EIN
     */
    List<MerchantDetailsResponseDTO> getMerchantDetailsByEin(String ein, boolean includeSensitiveData);

    /**
     * Retrieves merchant details by industry.
     *
     * @param industry The industry to search for
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return A list of merchant details in the specified industry
     */
    List<MerchantDetailsResponseDTO> getMerchantDetailsByIndustry(String industry, boolean includeSensitiveData);

    /**
     * Retrieves merchant details by revenue range.
     *
     * @param minRevenue The minimum revenue (inclusive)
     * @param maxRevenue The maximum revenue (inclusive)
     * @param includeSensitiveData Whether to include sensitive (decrypted) data in the response
     * @return A list of merchant details within the specified revenue range
     */
    List<MerchantDetailsResponseDTO> getMerchantDetailsByRevenueRange(Double minRevenue, Double maxRevenue, boolean includeSensitiveData);
}