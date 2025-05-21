package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.dto.MerchantDetailsResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.exception.BusinessRuleException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.MerchantDetailsRepository;
import com.dollarfunding.mca.util.EncryptionUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Implementation of the MerchantService interface that manages merchant details for the MCA application.
 * Handles CRUD operations, validation, and encryption of merchant information associated with applications.
 * <p>
 * This class interacts with MerchantRepository for data persistence, ValidationService for data validation,
 * and implements field-level encryption for sensitive merchant data.
 * </p>
 */
@Service
@Slf4j
public class MerchantServiceImpl implements MerchantService {

    private final MerchantDetailsRepository merchantDetailsRepository;
    private final ApplicationRepository applicationRepository;
    private final ValidationService validationService;
    private final EncryptionUtil encryptionUtil;

    /**
     * Constructor for dependency injection.
     *
     * @param merchantDetailsRepository Repository for merchant details persistence
     * @param applicationRepository Repository for application persistence
     * @param validationService Service for validating merchant data
     * @param encryptionUtil Utility for encrypting sensitive merchant data
     */
    @Autowired
    public MerchantServiceImpl(MerchantDetailsRepository merchantDetailsRepository,
                              ApplicationRepository applicationRepository,
                              ValidationService validationService,
                              EncryptionUtil encryptionUtil) {
        this.merchantDetailsRepository = merchantDetailsRepository;
        this.applicationRepository = applicationRepository;
        this.validationService = validationService;
        this.encryptionUtil = encryptionUtil;
    }

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
    @Override
    @Transactional
    public MerchantDetailsResponseDTO createMerchantDetails(UUID applicationId, MerchantDetailsRequestDTO merchantDetailsRequestDTO) {
        log.info("Creating merchant details for application ID: {}", applicationId);
        
        // Validate the application exists
        Application application = applicationRepository.findById(applicationId)
                .orElseThrow(() -> new ResourceNotFoundException("Application not found with ID: " + applicationId));
        
        // Check if merchant details already exist for this application
        if (merchantDetailsRepository.existsByApplication(application)) {
            throw new BusinessRuleException("Merchant details already exist for application ID: " + applicationId);
        }
        
        // Validate merchant details
        validateMerchantDetails(merchantDetailsRequestDTO);
        
        // Convert DTO to entity
        MerchantDetails merchantDetails = convertToEntity(merchantDetailsRequestDTO);
        merchantDetails.setApplication(application);
        
        // Save the merchant details
        MerchantDetails savedMerchantDetails = merchantDetailsRepository.save(merchantDetails);
        log.info("Merchant details created successfully for application ID: {}", applicationId);
        
        // Convert entity to response DTO
        return new MerchantDetailsResponseDTO(savedMerchantDetails);
    }

    /**
     * Retrieves merchant details by ID.
     *
     * @param id The ID of the merchant details to retrieve
     * @return The merchant details
     * @throws ResourceNotFoundException if the merchant details are not found
     */
    @Override
    @Transactional(readOnly = true)
    public MerchantDetailsResponseDTO getMerchantDetailsById(Long id) {
        log.info("Retrieving merchant details with ID: {}", id);
        
        MerchantDetails merchantDetails = merchantDetailsRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Merchant details not found with ID: " + id));
        
        return new MerchantDetailsResponseDTO(merchantDetails);
    }

    /**
     * Retrieves merchant details by application ID.
     *
     * @param applicationId The ID of the application
     * @return The merchant details associated with the application
     * @throws ResourceNotFoundException if the merchant details are not found
     */
    @Override
    @Transactional(readOnly = true)
    public MerchantDetailsResponseDTO getMerchantDetailsByApplicationId(UUID applicationId) {
        log.info("Retrieving merchant details for application ID: {}", applicationId);
        
        MerchantDetails merchantDetails = merchantDetailsRepository.findByApplicationId(applicationId)
                .orElseThrow(() -> new ResourceNotFoundException("Merchant details not found for application ID: " + applicationId));
        
        return new MerchantDetailsResponseDTO(merchantDetails);
    }

    /**
     * Updates existing merchant details.
     *
     * @param id The ID of the merchant details to update
     * @param merchantDetailsRequestDTO The updated merchant details data
     * @return The updated merchant details
     * @throws ResourceNotFoundException if the merchant details are not found
     * @throws ValidationException if the merchant data fails validation
     */
    @Override
    @Transactional
    public MerchantDetailsResponseDTO updateMerchantDetails(Long id, MerchantDetailsRequestDTO merchantDetailsRequestDTO) {
        log.info("Updating merchant details with ID: {}", id);
        
        // Validate merchant details
        validateMerchantDetails(merchantDetailsRequestDTO);
        
        // Retrieve existing merchant details
        MerchantDetails existingMerchantDetails = merchantDetailsRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Merchant details not found with ID: " + id));
        
        // Update fields
        updateEntityFromDTO(existingMerchantDetails, merchantDetailsRequestDTO);
        
        // Save the updated merchant details
        MerchantDetails updatedMerchantDetails = merchantDetailsRepository.save(existingMerchantDetails);
        log.info("Merchant details updated successfully for ID: {}", id);
        
        // Convert entity to response DTO
        return new MerchantDetailsResponseDTO(updatedMerchantDetails);
    }

    /**
     * Updates merchant details for a specific application.
     *
     * @param applicationId The ID of the application
     * @param merchantDetailsRequestDTO The updated merchant details data
     * @return The updated merchant details
     * @throws ResourceNotFoundException if the merchant details are not found
     * @throws ValidationException if the merchant data fails validation
     */
    @Override
    @Transactional
    public MerchantDetailsResponseDTO updateMerchantDetailsByApplicationId(UUID applicationId, MerchantDetailsRequestDTO merchantDetailsRequestDTO) {
        log.info("Updating merchant details for application ID: {}", applicationId);
        
        // Validate merchant details
        validateMerchantDetails(merchantDetailsRequestDTO);
        
        // Retrieve existing merchant details
        MerchantDetails existingMerchantDetails = merchantDetailsRepository.findByApplicationId(applicationId)
                .orElseThrow(() -> new ResourceNotFoundException("Merchant details not found for application ID: " + applicationId));
        
        // Update fields
        updateEntityFromDTO(existingMerchantDetails, merchantDetailsRequestDTO);
        
        // Save the updated merchant details
        MerchantDetails updatedMerchantDetails = merchantDetailsRepository.save(existingMerchantDetails);
        log.info("Merchant details updated successfully for application ID: {}", applicationId);
        
        // Convert entity to response DTO
        return new MerchantDetailsResponseDTO(updatedMerchantDetails);
    }

    /**
     * Deletes merchant details by ID.
     *
     * @param id The ID of the merchant details to delete
     * @throws ResourceNotFoundException if the merchant details are not found
     */
    @Override
    @Transactional
    public void deleteMerchantDetails(Long id) {
        log.info("Deleting merchant details with ID: {}", id);
        
        // Check if merchant details exist
        if (!merchantDetailsRepository.existsById(id)) {
            throw new ResourceNotFoundException("Merchant details not found with ID: " + id);
        }
        
        // Delete the merchant details
        merchantDetailsRepository.deleteById(id);
        log.info("Merchant details deleted successfully for ID: {}", id);
    }

    /**
     * Retrieves all merchant details with pagination.
     *
     * @param pageable Pagination information
     * @return A page of merchant details
     */
    @Override
    @Transactional(readOnly = true)
    public Page<MerchantDetailsResponseDTO> getAllMerchantDetails(Pageable pageable) {
        log.info("Retrieving all merchant details with pagination: {}", pageable);
        
        Page<MerchantDetails> merchantDetailsPage = merchantDetailsRepository.findAll(pageable);
        
        return merchantDetailsPage.map(MerchantDetailsResponseDTO::new);
    }

    /**
     * Finds merchants by industry with pagination.
     *
     * @param industry The industry to filter by
     * @param pageable Pagination information
     * @return A page of merchant details in the specified industry
     */
    @Override
    @Transactional(readOnly = true)
    public Page<MerchantDetailsResponseDTO> findMerchantsByIndustry(String industry, Pageable pageable) {
        log.info("Finding merchants by industry: {} with pagination: {}", industry, pageable);
        
        Page<MerchantDetails> merchantDetailsPage = merchantDetailsRepository.findByIndustryContainingIgnoreCase(industry, pageable);
        
        return merchantDetailsPage.map(MerchantDetailsResponseDTO::new);
    }

    /**
     * Finds merchants by revenue range with pagination.
     *
     * @param minRevenue The minimum revenue
     * @param maxRevenue The maximum revenue
     * @param pageable Pagination information
     * @return A page of merchant details within the specified revenue range
     */
    @Override
    @Transactional(readOnly = true)
    public Page<MerchantDetailsResponseDTO> findMerchantsByRevenueRange(BigDecimal minRevenue, BigDecimal maxRevenue, Pageable pageable) {
        log.info("Finding merchants by revenue range: {} - {} with pagination: {}", minRevenue, maxRevenue, pageable);
        
        Page<MerchantDetails> merchantDetailsPage = merchantDetailsRepository.findByRevenueBetween(minRevenue, maxRevenue, pageable);
        
        return merchantDetailsPage.map(MerchantDetailsResponseDTO::new);
    }

    /**
     * Finds merchants by state with pagination.
     *
     * @param state The state to filter by (2-letter code)
     * @param pageable Pagination information
     * @return A page of merchant details in the specified state
     */
    @Override
    @Transactional(readOnly = true)
    public Page<MerchantDetailsResponseDTO> findMerchantsByState(String state, Pageable pageable) {
        log.info("Finding merchants by state: {} with pagination: {}", state, pageable);
        
        Page<MerchantDetails> merchantDetailsPage = merchantDetailsRepository.findByAddressState(state, pageable);
        
        return merchantDetailsPage.map(MerchantDetailsResponseDTO::new);
    }

    /**
     * Finds merchants by city with pagination.
     *
     * @param city The city to filter by
     * @param pageable Pagination information
     * @return A page of merchant details in the specified city
     */
    @Override
    @Transactional(readOnly = true)
    public Page<MerchantDetailsResponseDTO> findMerchantsByCity(String city, Pageable pageable) {
        log.info("Finding merchants by city: {} with pagination: {}", city, pageable);
        
        Page<MerchantDetails> merchantDetailsPage = merchantDetailsRepository.findByAddressCity(city, pageable);
        
        return merchantDetailsPage.map(MerchantDetailsResponseDTO::new);
    }

    /**
     * Finds merchants by industry and state with pagination.
     *
     * @param industry The industry to filter by
     * @param state The state to filter by (2-letter code)
     * @param pageable Pagination information
     * @return A page of merchant details in the specified industry and state
     */
    @Override
    @Transactional(readOnly = true)
    public Page<MerchantDetailsResponseDTO> findMerchantsByIndustryAndState(String industry, String state, Pageable pageable) {
        log.info("Finding merchants by industry: {} and state: {} with pagination: {}", industry, state, pageable);
        
        Page<MerchantDetails> merchantDetailsPage = merchantDetailsRepository.findByAddressStateAndIndustry(state, industry, pageable);
        
        return merchantDetailsPage.map(MerchantDetailsResponseDTO::new);
    }

    /**
     * Finds merchants by industry and revenue range with pagination.
     *
     * @param industry The industry to filter by
     * @param minRevenue The minimum revenue
     * @param maxRevenue The maximum revenue
     * @param pageable Pagination information
     * @return A page of merchant details in the specified industry and revenue range
     */
    @Override
    @Transactional(readOnly = true)
    public Page<MerchantDetailsResponseDTO> findMerchantsByIndustryAndRevenueRange(
            String industry, BigDecimal minRevenue, BigDecimal maxRevenue, Pageable pageable) {
        log.info("Finding merchants by industry: {} and revenue range: {} - {} with pagination: {}", 
                industry, minRevenue, maxRevenue, pageable);
        
        Page<MerchantDetails> merchantDetailsPage = merchantDetailsRepository.findByIndustryAndRevenueBetween(
                industry, minRevenue, maxRevenue, pageable);
        
        return merchantDetailsPage.map(MerchantDetailsResponseDTO::new);
    }

    /**
     * Checks if merchant details exist for an application.
     *
     * @param applicationId The ID of the application
     * @return true if merchant details exist, false otherwise
     */
    @Override
    @Transactional(readOnly = true)
    public boolean merchantDetailsExistForApplication(UUID applicationId) {
        log.debug("Checking if merchant details exist for application ID: {}", applicationId);
        
        return merchantDetailsRepository.existsByApplicationId(applicationId);
    }

    /**
     * Validates merchant details data.
     *
     * @param merchantDetailsRequestDTO The merchant details data to validate
     * @throws ValidationException if validation fails
     */
    private void validateMerchantDetails(MerchantDetailsRequestDTO merchantDetailsRequestDTO) {
        log.debug("Validating merchant details");
        
        // Basic validation
        if (merchantDetailsRequestDTO == null) {
            throw new ValidationException("Merchant details cannot be null");
        }
        
        // Validate legal name
        if (merchantDetailsRequestDTO.getLegalName() == null || merchantDetailsRequestDTO.getLegalName().trim().isEmpty()) {
            throw new ValidationException("Legal name is required");
        }
        
        // Validate EIN format
        if (merchantDetailsRequestDTO.getEin() == null || !merchantDetailsRequestDTO.getEin().matches("^\\d{2}-\\d{7}$")) {
            throw new ValidationException("EIN must be in format XX-XXXXXXX");
        }
        
        // Validate address
        if (merchantDetailsRequestDTO.getAddress() == null) {
            throw new ValidationException("Address is required");
        }
        
        // Validate industry
        if (merchantDetailsRequestDTO.getIndustry() == null || merchantDetailsRequestDTO.getIndustry().trim().isEmpty()) {
            throw new ValidationException("Industry is required");
        }
        
        // Validate revenue
        if (merchantDetailsRequestDTO.getRevenue() == null || merchantDetailsRequestDTO.getRevenue().compareTo(BigDecimal.ZERO) <= 0) {
            throw new ValidationException("Revenue must be greater than zero");
        }
        
        // Use validation service for more complex validation
        validationService.validateMerchantData(merchantDetailsRequestDTO);
    }

    /**
     * Converts a DTO to an entity with encryption for sensitive fields.
     *
     * @param dto The DTO to convert
     * @return The converted entity
     */
    private MerchantDetails convertToEntity(MerchantDetailsRequestDTO dto) {
        MerchantDetails entity = new MerchantDetails();
        
        // Set fields with encryption for sensitive data
        entity.setLegalName(dto.getLegalName()); // Encryption handled by JPA converter
        entity.setDbaName(dto.getDbaName()); // Encryption handled by JPA converter
        entity.setEin(dto.getEin()); // Encryption handled by JPA converter
        
        // Convert address DTO to entity address
        MerchantDetails.Address address = new MerchantDetails.Address();
        address.setStreet(dto.getAddress().getStreetAddress());
        address.setCity(dto.getAddress().getCity());
        address.setState(dto.getAddress().getState());
        address.setZip(dto.getAddress().getZipCode());
        address.setCountry("US"); // Default to US for now
        entity.setAddress(address);
        
        // Set non-sensitive fields
        entity.setIndustry(dto.getIndustry());
        entity.setRevenue(dto.getRevenue());
        
        return entity;
    }

    /**
     * Updates an entity from a DTO.
     *
     * @param entity The entity to update
     * @param dto The DTO with updated data
     */
    private void updateEntityFromDTO(MerchantDetails entity, MerchantDetailsRequestDTO dto) {
        // Update fields with encryption for sensitive data
        entity.setLegalName(dto.getLegalName()); // Encryption handled by JPA converter
        entity.setDbaName(dto.getDbaName()); // Encryption handled by JPA converter
        entity.setEin(dto.getEin()); // Encryption handled by JPA converter
        
        // Update address
        MerchantDetails.Address address = entity.getAddress();
        if (address == null) {
            address = new MerchantDetails.Address();
        }
        address.setStreet(dto.getAddress().getStreetAddress());
        address.setCity(dto.getAddress().getCity());
        address.setState(dto.getAddress().getState());
        address.setZip(dto.getAddress().getZipCode());
        address.setCountry("US"); // Default to US for now
        entity.setAddress(address);
        
        // Update non-sensitive fields
        entity.setIndustry(dto.getIndustry());
        entity.setRevenue(dto.getRevenue());
    }
}