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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link MerchantServiceImpl} class.
 * 
 * These tests verify CRUD operations, validation, encryption, and filtering
 * functionality for merchant details management.
 */
@ExtendWith(MockitoExtension.class)
public class MerchantServiceImplTest {

    @Mock
    private MerchantDetailsRepository merchantDetailsRepository;

    @Mock
    private ApplicationRepository applicationRepository;

    @Mock
    private ValidationService validationService;

    @Mock
    private EncryptionUtil encryptionUtil;

    @InjectMocks
    private MerchantServiceImpl merchantService;

    private UUID applicationId;
    private MerchantDetailsRequestDTO merchantDetailsRequestDTO;
    private MerchantDetails merchantDetails;
    private Application application;

    @BeforeEach
    void setUp() {
        // Initialize test data
        applicationId = UUID.randomUUID();
        
        // Create application
        application = new Application();
        application.setId(applicationId);
        
        // Create merchant details request DTO
        merchantDetailsRequestDTO = new MerchantDetailsRequestDTO();
        merchantDetailsRequestDTO.setLegalName("Test Merchant Inc.");
        merchantDetailsRequestDTO.setDbaName("Test Merchant");
        merchantDetailsRequestDTO.setEin("12-3456789");
        merchantDetailsRequestDTO.setIndustry("Retail");
        merchantDetailsRequestDTO.setRevenue(new BigDecimal("500000.00"));
        
        // Create merchant details entity
        merchantDetails = new MerchantDetails();
        merchantDetails.setId(UUID.randomUUID());
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Test Merchant Inc.");
        merchantDetails.setDbaName("Test Merchant");
        merchantDetails.setEin("12-3456789");
        merchantDetails.setIndustry("Retail");
        merchantDetails.setRevenue(new BigDecimal("500000.00"));
    }

    @Test
    @DisplayName("Should create merchant details successfully")
    void createMerchantDetails_Success() {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(merchantDetailsRepository.existsByApplicationId(applicationId)).thenReturn(false);
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(merchantDetails);
        doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act
        MerchantDetailsResponseDTO result = merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
        
        // Assert
        assertNotNull(result);
        assertEquals(merchantDetails.getId(), result.getId());
        assertEquals(merchantDetails.getLegalName(), result.getLegalName());
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(applicationRepository).findById(applicationId);
        verify(merchantDetailsRepository).existsByApplicationId(applicationId);
        verify(merchantDetailsRepository).save(any(MerchantDetails.class));
    }

    @Test
    @DisplayName("Should throw ValidationException when merchant data is invalid")
    void createMerchantDetails_ValidationFailure() {
        // Arrange
        doThrow(new ValidationException("Invalid merchant data")).when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act & Assert
        ValidationException exception = assertThrows(ValidationException.class, () -> {
            merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
        });
        
        assertEquals("Invalid merchant data", exception.getMessage());
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(applicationRepository, never()).findById(any());
        verify(merchantDetailsRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when application is not found")
    void createMerchantDetails_ApplicationNotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.empty());
        doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
        });
        
        assertTrue(exception.getMessage().contains("Application not found"));
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(applicationRepository).findById(applicationId);
        verify(merchantDetailsRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should throw BusinessRuleException when merchant details already exist for application")
    void createMerchantDetails_MerchantDetailsAlreadyExist() {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(merchantDetailsRepository.existsByApplicationId(applicationId)).thenReturn(true);
        doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act & Assert
        BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
            merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
        });
        
        assertEquals("Merchant details already exist for this application", exception.getMessage());
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(applicationRepository).findById(applicationId);
        verify(merchantDetailsRepository).existsByApplicationId(applicationId);
        verify(merchantDetailsRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should get merchant details by ID successfully")
    void getMerchantDetailsById_Success() {
        // Arrange
        Long id = 1L;
        UUID uuid = UUID.randomUUID();
        when(merchantDetailsRepository.findById(any(UUID.class))).thenReturn(Optional.of(merchantDetails));
        
        // Act
        MerchantDetailsResponseDTO result = merchantService.getMerchantDetailsById(id);
        
        // Assert
        assertNotNull(result);
        assertEquals(merchantDetails.getId(), result.getId());
        assertEquals(merchantDetails.getLegalName(), result.getLegalName());
        
        // Verify interactions
        verify(merchantDetailsRepository).findById(any(UUID.class));
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when merchant details are not found by ID")
    void getMerchantDetailsById_NotFound() {
        // Arrange
        Long id = 1L;
        when(merchantDetailsRepository.findById(any(UUID.class))).thenReturn(Optional.empty());
        
        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            merchantService.getMerchantDetailsById(id);
        });
        
        assertTrue(exception.getMessage().contains("Merchant details not found"));
        
        // Verify interactions
        verify(merchantDetailsRepository).findById(any(UUID.class));
    }

    @Test
    @DisplayName("Should get merchant details by application ID successfully")
    void getMerchantDetailsByApplicationId_Success() {
        // Arrange
        when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.of(merchantDetails));
        
        // Act
        MerchantDetailsResponseDTO result = merchantService.getMerchantDetailsByApplicationId(applicationId);
        
        // Assert
        assertNotNull(result);
        assertEquals(merchantDetails.getId(), result.getId());
        assertEquals(merchantDetails.getLegalName(), result.getLegalName());
        
        // Verify interactions
        verify(merchantDetailsRepository).findByApplicationId(applicationId);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when merchant details are not found by application ID")
    void getMerchantDetailsByApplicationId_NotFound() {
        // Arrange
        when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.empty());
        
        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            merchantService.getMerchantDetailsByApplicationId(applicationId);
        });
        
        assertTrue(exception.getMessage().contains("Merchant details not found for application"));
        
        // Verify interactions
        verify(merchantDetailsRepository).findByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should update merchant details successfully")
    void updateMerchantDetails_Success() {
        // Arrange
        Long id = 1L;
        UUID uuid = UUID.randomUUID();
        
        // Updated merchant details
        MerchantDetailsRequestDTO updatedDTO = new MerchantDetailsRequestDTO();
        updatedDTO.setLegalName("Updated Merchant Inc.");
        updatedDTO.setDbaName("Updated Merchant");
        updatedDTO.setEin("98-7654321");
        updatedDTO.setIndustry("Technology");
        updatedDTO.setRevenue(new BigDecimal("1000000.00"));
        
        when(merchantDetailsRepository.findById(any(UUID.class))).thenReturn(Optional.of(merchantDetails));
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(merchantDetails);
        doNothing().when(validationService).validateMerchantData(updatedDTO);
        
        // Act
        MerchantDetailsResponseDTO result = merchantService.updateMerchantDetails(id, updatedDTO);
        
        // Assert
        assertNotNull(result);
        
        // Verify interactions
        verify(validationService).validateMerchantData(updatedDTO);
        verify(merchantDetailsRepository).findById(any(UUID.class));
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
        verify(merchantDetailsRepository).save(merchantDetails);
    }

    @Test
    @DisplayName("Should throw ValidationException when updating with invalid merchant data")
    void updateMerchantDetails_ValidationFailure() {
        // Arrange
        Long id = 1L;
        doThrow(new ValidationException("Invalid merchant data")).when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act & Assert
        ValidationException exception = assertThrows(ValidationException.class, () -> {
            merchantService.updateMerchantDetails(id, merchantDetailsRequestDTO);
        });
        
        assertEquals("Invalid merchant data", exception.getMessage());
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(merchantDetailsRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when updating non-existent merchant details")
    void updateMerchantDetails_NotFound() {
        // Arrange
        Long id = 1L;
        when(merchantDetailsRepository.findById(any(UUID.class))).thenReturn(Optional.empty());
        doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            merchantService.updateMerchantDetails(id, merchantDetailsRequestDTO);
        });
        
        assertTrue(exception.getMessage().contains("Merchant details not found"));
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(merchantDetailsRepository).findById(any(UUID.class));
        verify(merchantDetailsRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should update merchant details by application ID successfully")
    void updateMerchantDetailsByApplicationId_Success() {
        // Arrange
        // Updated merchant details
        MerchantDetailsRequestDTO updatedDTO = new MerchantDetailsRequestDTO();
        updatedDTO.setLegalName("Updated Merchant Inc.");
        updatedDTO.setDbaName("Updated Merchant");
        updatedDTO.setEin("98-7654321");
        updatedDTO.setIndustry("Technology");
        updatedDTO.setRevenue(new BigDecimal("1000000.00"));
        
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.of(merchantDetails));
        when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(merchantDetails);
        doNothing().when(validationService).validateMerchantData(updatedDTO);
        
        // Act
        MerchantDetailsResponseDTO result = merchantService.updateMerchantDetailsByApplicationId(applicationId, updatedDTO);
        
        // Assert
        assertNotNull(result);
        
        // Verify interactions
        verify(validationService).validateMerchantData(updatedDTO);
        verify(applicationRepository).findById(applicationId);
        verify(merchantDetailsRepository).findByApplicationId(applicationId);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
        verify(merchantDetailsRepository).save(merchantDetails);
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when application is not found during update by application ID")
    void updateMerchantDetailsByApplicationId_ApplicationNotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.empty());
        doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            merchantService.updateMerchantDetailsByApplicationId(applicationId, merchantDetailsRequestDTO);
        });
        
        assertTrue(exception.getMessage().contains("Application not found"));
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(applicationRepository).findById(applicationId);
        verify(merchantDetailsRepository, never()).findByApplicationId(any());
        verify(merchantDetailsRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when merchant details are not found during update by application ID")
    void updateMerchantDetailsByApplicationId_MerchantDetailsNotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.empty());
        doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
        
        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            merchantService.updateMerchantDetailsByApplicationId(applicationId, merchantDetailsRequestDTO);
        });
        
        assertTrue(exception.getMessage().contains("Merchant details not found for application"));
        
        // Verify interactions
        verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
        verify(applicationRepository).findById(applicationId);
        verify(merchantDetailsRepository).findByApplicationId(applicationId);
        verify(merchantDetailsRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should delete merchant details successfully")
    void deleteMerchantDetails_Success() {
        // Arrange
        Long id = 1L;
        when(merchantDetailsRepository.existsById(any(UUID.class))).thenReturn(true);
        doNothing().when(merchantDetailsRepository).deleteById(any(UUID.class));
        
        // Act
        merchantService.deleteMerchantDetails(id);
        
        // Verify interactions
        verify(merchantDetailsRepository).existsById(any(UUID.class));
        verify(merchantDetailsRepository).deleteById(any(UUID.class));
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when deleting non-existent merchant details")
    void deleteMerchantDetails_NotFound() {
        // Arrange
        Long id = 1L;
        when(merchantDetailsRepository.existsById(any(UUID.class))).thenReturn(false);
        
        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            merchantService.deleteMerchantDetails(id);
        });
        
        assertTrue(exception.getMessage().contains("Merchant details not found"));
        
        // Verify interactions
        verify(merchantDetailsRepository).existsById(any(UUID.class));
        verify(merchantDetailsRepository, never()).deleteById(any());
    }

    @Test
    @DisplayName("Should get all merchant details with pagination successfully")
    void getAllMerchantDetails_Success() {
        // Arrange
        Pageable pageable = PageRequest.of(0, 10);
        List<MerchantDetails> merchantDetailsList = new ArrayList<>();
        merchantDetailsList.add(merchantDetails);
        
        Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
        
        when(merchantDetailsRepository.findAll(pageable)).thenReturn(merchantDetailsPage);
        
        // Act
        Page<MerchantDetailsResponseDTO> result = merchantService.getAllMerchantDetails(pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        
        // Verify interactions
        verify(merchantDetailsRepository).findAll(pageable);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should find merchants by industry with pagination successfully")
    void findMerchantsByIndustry_Success() {
        // Arrange
        String industry = "Retail";
        Pageable pageable = PageRequest.of(0, 10);
        List<MerchantDetails> merchantDetailsList = new ArrayList<>();
        merchantDetailsList.add(merchantDetails);
        
        Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
        
        when(merchantDetailsRepository.findByIndustry(industry, pageable)).thenReturn(merchantDetailsPage);
        
        // Act
        Page<MerchantDetailsResponseDTO> result = merchantService.findMerchantsByIndustry(industry, pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        assertEquals("Retail", merchantDetails.getIndustry());
        
        // Verify interactions
        verify(merchantDetailsRepository).findByIndustry(industry, pageable);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should find merchants by revenue range with pagination successfully")
    void findMerchantsByRevenueRange_Success() {
        // Arrange
        BigDecimal minRevenue = new BigDecimal("100000.00");
        BigDecimal maxRevenue = new BigDecimal("1000000.00");
        Pageable pageable = PageRequest.of(0, 10);
        List<MerchantDetails> merchantDetailsList = new ArrayList<>();
        merchantDetailsList.add(merchantDetails);
        
        Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
        
        when(merchantDetailsRepository.findByRevenueBetween(minRevenue, maxRevenue, pageable)).thenReturn(merchantDetailsPage);
        
        // Act
        Page<MerchantDetailsResponseDTO> result = merchantService.findMerchantsByRevenueRange(minRevenue, maxRevenue, pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        assertTrue(merchantDetails.getRevenue().compareTo(minRevenue) >= 0);
        assertTrue(merchantDetails.getRevenue().compareTo(maxRevenue) <= 0);
        
        // Verify interactions
        verify(merchantDetailsRepository).findByRevenueBetween(minRevenue, maxRevenue, pageable);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should find merchants by state with pagination successfully")
    void findMerchantsByState_Success() {
        // Arrange
        String state = "CA";
        Pageable pageable = PageRequest.of(0, 10);
        List<MerchantDetails> merchantDetailsList = new ArrayList<>();
        merchantDetailsList.add(merchantDetails);
        
        Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
        
        when(merchantDetailsRepository.findByState(state, pageable)).thenReturn(merchantDetailsPage);
        
        // Act
        Page<MerchantDetailsResponseDTO> result = merchantService.findMerchantsByState(state, pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        
        // Verify interactions
        verify(merchantDetailsRepository).findByState(state, pageable);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should find merchants by city with pagination successfully")
    void findMerchantsByCity_Success() {
        // Arrange
        String city = "San Francisco";
        Pageable pageable = PageRequest.of(0, 10);
        List<MerchantDetails> merchantDetailsList = new ArrayList<>();
        merchantDetailsList.add(merchantDetails);
        
        Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
        
        when(merchantDetailsRepository.findByCity(city, pageable)).thenReturn(merchantDetailsPage);
        
        // Act
        Page<MerchantDetailsResponseDTO> result = merchantService.findMerchantsByCity(city, pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        
        // Verify interactions
        verify(merchantDetailsRepository).findByCity(city, pageable);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should find merchants by industry and state with pagination successfully")
    void findMerchantsByIndustryAndState_Success() {
        // Arrange
        String industry = "Retail";
        String state = "CA";
        Pageable pageable = PageRequest.of(0, 10);
        List<MerchantDetails> merchantDetailsList = new ArrayList<>();
        merchantDetailsList.add(merchantDetails);
        
        Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
        
        when(merchantDetailsRepository.findByStateAndIndustry(state, industry, pageable)).thenReturn(merchantDetailsPage);
        
        // Act
        Page<MerchantDetailsResponseDTO> result = merchantService.findMerchantsByIndustryAndState(industry, state, pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        assertEquals("Retail", merchantDetails.getIndustry());
        
        // Verify interactions
        verify(merchantDetailsRepository).findByStateAndIndustry(state, industry, pageable);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should find merchants by industry and revenue range with pagination successfully")
    void findMerchantsByIndustryAndRevenueRange_Success() {
        // Arrange
        String industry = "Retail";
        BigDecimal minRevenue = new BigDecimal("100000.00");
        BigDecimal maxRevenue = new BigDecimal("1000000.00");
        Pageable pageable = PageRequest.of(0, 10);
        List<MerchantDetails> merchantDetailsList = new ArrayList<>();
        merchantDetailsList.add(merchantDetails);
        
        Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
        
        when(merchantDetailsRepository.findByIndustryAndRevenueGreaterThanEqual(industry, minRevenue, pageable)).thenReturn(merchantDetailsPage);
        
        // Act
        Page<MerchantDetailsResponseDTO> result = merchantService.findMerchantsByIndustryAndRevenueRange(industry, minRevenue, maxRevenue, pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        assertEquals("Retail", merchantDetails.getIndustry());
        assertTrue(merchantDetails.getRevenue().compareTo(minRevenue) >= 0);
        assertTrue(merchantDetails.getRevenue().compareTo(maxRevenue) <= 0);
        
        // Verify interactions
        verify(merchantDetailsRepository).findByIndustryAndRevenueGreaterThanEqual(industry, minRevenue, pageable);
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should check if merchant details exist for application successfully")
    void merchantDetailsExistForApplication_Success() {
        // Arrange
        when(merchantDetailsRepository.existsByApplicationId(applicationId)).thenReturn(true);
        
        // Act
        boolean result = merchantService.merchantDetailsExistForApplication(applicationId);
        
        // Assert
        assertTrue(result);
        
        // Verify interactions
        verify(merchantDetailsRepository).existsByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should handle field-level encryption for sensitive merchant data")
    void handleFieldLevelEncryption_Success() {
        // Arrange
        Long id = 1L;
        UUID uuid = UUID.randomUUID();
        
        // Set up encryption expectations
        when(encryptionUtil.encrypt("Test Merchant Inc.")).thenReturn("ENCRYPTED_LEGAL_NAME");
        when(encryptionUtil.encrypt("Test Merchant")).thenReturn("ENCRYPTED_DBA_NAME");
        when(encryptionUtil.encrypt("12-3456789")).thenReturn("ENCRYPTED_EIN");
        
        when(encryptionUtil.decrypt("ENCRYPTED_LEGAL_NAME")).thenReturn("Test Merchant Inc.");
        when(encryptionUtil.decrypt("ENCRYPTED_DBA_NAME")).thenReturn("Test Merchant");
        when(encryptionUtil.decrypt("ENCRYPTED_EIN")).thenReturn("12-3456789");
        
        when(merchantDetailsRepository.findById(any(UUID.class))).thenReturn(Optional.of(merchantDetails));
        
        // Act
        MerchantDetailsResponseDTO result = merchantService.getMerchantDetailsById(id);
        
        // Assert
        assertNotNull(result);
        
        // Verify encryption utility was set on the entity
        verify(merchantDetails).setEncryptionUtil(encryptionUtil);
    }

    @Test
    @DisplayName("Should handle error when converting ID to UUID")
    void convertToUUID_Error() {
        // Arrange
        Long id = null;
        
        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            merchantService.getMerchantDetailsById(id);
        });
        
        assertTrue(exception.getMessage().contains("ID cannot be null"));
    }
}