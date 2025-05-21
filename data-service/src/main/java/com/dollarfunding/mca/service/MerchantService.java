package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.dto.MerchantDetailsResponseDTO;
import com.dollarfunding.mca.exception.BusinessRuleException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * Service interface that defines the contract for managing merchant details in the MCA application.
 * <p>
 * Provides methods for creating, retrieving, updating, and validating merchant information
 * associated with applications. This interface is implemented by MerchantServiceImpl and used
 * by ApplicationService to handle merchant-related operations.
 * </p>
 * <p>
 * The service handles field-level encryption for sensitive merchant data (PII) and provides
 * methods for filtering and retrieving merchant details with various criteria.
 * </p>
 */
public interface MerchantService {

    /**
     * Creates a new merchant details record associated with an application.
     *
     * @param applicationId The ID of the application to associate the merchant with
     * @param merchantDetailsRequestDTO The merchant details data
     * @return The created merchant details
     * @throws ResourceNotFoundException if the application is not found
     * @throws ValidationException if the merchant data fails validation
     * @throws BusinessRuleException if a merchant already exists for the application
     */
    MerchantDetailsResponseDTO createMerchantDetails(UUID applicationId, MerchantDetailsRequestDTO merchantDetailsRequestDTO);

    /**
     * Retrieves merchant details by ID.
     *
     * @param id The ID of the merchant details to retrieve
     * @return The merchant details
     * @throws ResourceNotFoundException if the merchant details are not found
     */
    MerchantDetailsResponseDTO getMerchantDetailsById(Long id);

    /**
     * Retrieves merchant details by application ID.
     *
     * @param applicationId The ID of the application
     * @return The merchant details associated with the application
     * @throws ResourceNotFoundException if the merchant details are not found
     */
    MerchantDetailsResponseDTO getMerchantDetailsByApplicationId(UUID applicationId);

    /**
     * Updates existing merchant details.
     *
     * @param id The ID of the merchant details to update
     * @param merchantDetailsRequestDTO The updated merchant details data
     * @return The updated merchant details
     * @throws ResourceNotFoundException if the merchant details are not found
     * @throws ValidationException if the merchant data fails validation
     */
    MerchantDetailsResponseDTO updateMerchantDetails(Long id, MerchantDetailsRequestDTO merchantDetailsRequestDTO);

    /**
     * Updates merchant details for a specific application.
     *
     * @param applicationId The ID of the application
     * @param merchantDetailsRequestDTO The updated merchant details data
     * @return The updated merchant details
     * @throws ResourceNotFoundException if the merchant details are not found
     * @throws ValidationException if the merchant data fails validation
     */
    MerchantDetailsResponseDTO updateMerchantDetailsByApplicationId(UUID applicationId, MerchantDetailsRequestDTO merchantDetailsRequestDTO);

    /**
     * Deletes merchant details by ID.
     *
     * @param id The ID of the merchant details to delete
     * @throws ResourceNotFoundException if the merchant details are not found
     */
    void deleteMerchantDetails(Long id);

    /**
     * Retrieves all merchant details with pagination.
     *
     * @param pageable Pagination information
     * @return A page of merchant details
     */
    Page<MerchantDetailsResponseDTO> getAllMerchantDetails(Pageable pageable);

    /**
     * Finds merchants by industry with pagination.
     *
     * @param industry The industry to filter by
     * @param pageable Pagination information
     * @return A page of merchant details in the specified industry
     */
    Page<MerchantDetailsResponseDTO> findMerchantsByIndustry(String industry, Pageable pageable);

    /**
     * Finds merchants by revenue range with pagination.
     *
     * @param minRevenue The minimum revenue
     * @param maxRevenue The maximum revenue
     * @param pageable Pagination information
     * @return A page of merchant details within the specified revenue range
     */
    Page<MerchantDetailsResponseDTO> findMerchantsByRevenueRange(BigDecimal minRevenue, BigDecimal maxRevenue, Pageable pageable);

    /**
     * Finds merchants by state with pagination.
     *
     * @param state The state to filter by (2-letter code)
     * @param pageable Pagination information
     * @return A page of merchant details in the specified state
     */
    Page<MerchantDetailsResponseDTO> findMerchantsByState(String state, Pageable pageable);

    /**
     * Finds merchants by city with pagination.
     *
     * @param city The city to filter by
     * @param pageable Pagination information
     * @return A page of merchant details in the specified city
     */
    Page<MerchantDetailsResponseDTO> findMerchantsByCity(String city, Pageable pageable);

    /**
     * Finds merchants by industry and state with pagination.
     *
     * @param industry The industry to filter by
     * @param state The state to filter by (2-letter code)
     * @param pageable Pagination information
     * @return A page of merchant details in the specified industry and state
     */
    Page<MerchantDetailsResponseDTO> findMerchantsByIndustryAndState(String industry, String state, Pageable pageable);

    /**
     * Finds merchants by industry and revenue range with pagination.
     *
     * @param industry The industry to filter by
     * @param minRevenue The minimum revenue
     * @param maxRevenue The maximum revenue
     * @param pageable Pagination information
     * @return A page of merchant details in the specified industry and revenue range
     */
    Page<MerchantDetailsResponseDTO> findMerchantsByIndustryAndRevenueRange(
            String industry, BigDecimal minRevenue, BigDecimal maxRevenue, Pageable pageable);

    /**
     * Checks if merchant details exist for an application.
     *
     * @param applicationId The ID of the application
     * @return true if merchant details exist, false otherwise
     */
    boolean merchantDetailsExistForApplication(UUID applicationId);
}