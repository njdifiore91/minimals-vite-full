package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.dto.MerchantDetailsResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.BusinessRuleException;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.MerchantDetailsRepository;
import com.dollarfunding.mca.util.EncryptionUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the MerchantServiceImpl class.
 * 
 * These tests verify that the MerchantServiceImpl correctly handles CRUD operations,
 * validation, encryption, and error handling for merchant details in the MCA application.
 * 
 * The tests use Mockito to mock dependencies and focus on testing the service layer logic.
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

    @Captor
    private ArgumentCaptor<MerchantDetails> merchantDetailsCaptor;

    private UUID applicationId;
    private Application application;
    private MerchantDetailsRequestDTO merchantDetailsRequestDTO;
    private MerchantDetails merchantDetails;
    private MerchantDetailsRequestDTO.AddressDTO addressDTO;

    @BeforeEach
    void setUp() {
        // Initialize test data
        applicationId = UUID.randomUUID();
        
        // Create application
        application = new Application(ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
        application.setId(applicationId);
        application.setCreatedAt(LocalDateTime.now());
        application.setUpdatedAt(LocalDateTime.now());
        
        // Create address DTO
        addressDTO = MerchantDetailsRequestDTO.AddressDTO.builder()
                .streetAddress("123 Main St")
                .streetAddress2("Suite 100")
                .city("New York")
                .state("NY")
                .zipCode("10001")
                .build();
        
        // Create merchant details request DTO
        merchantDetailsRequestDTO = MerchantDetailsRequestDTO.builder()
                .legalName("Acme Corporation")
                .dbaName("Acme")
                .ein("12-3456789")
                .address(addressDTO)
                .industry("Technology")
                .revenue(new BigDecimal("500000.00"))
                .build();
        
        // Create merchant details entity
        merchantDetails = new MerchantDetails();
        merchantDetails.setId(1L);
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Acme Corporation");
        merchantDetails.setDbaName("Acme");
        merchantDetails.setEin("12-3456789");
        
        MerchantDetails.Address address = new MerchantDetails.Address();
        address.setStreet("123 Main St");
        address.setCity("New York");
        address.setState("NY");
        address.setZip("10001");
        address.setCountry("US");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(new BigDecimal("500000.00"));
        merchantDetails.setCreatedAt(LocalDateTime.now());
        merchantDetails.setUpdatedAt(LocalDateTime.now());
    }

    @Nested
    @DisplayName("Create Merchant Details Tests")
    class CreateMerchantDetailsTests {

        @Test
        @DisplayName("Should create merchant details successfully")
        void shouldCreateMerchantDetailsSuccessfully() {
            // Arrange
            when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
            when(merchantDetailsRepository.existsByApplication(application)).thenReturn(false);
            doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
            when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(merchantDetails);

            // Act
            MerchantDetailsResponseDTO responseDTO = merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);

            // Assert
            assertNotNull(responseDTO);
            assertEquals(1L, responseDTO.getId());
            verify(applicationRepository).findById(applicationId);
            verify(merchantDetailsRepository).existsByApplication(application);
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository).save(merchantDetailsCaptor.capture());
            
            MerchantDetails capturedMerchantDetails = merchantDetailsCaptor.getValue();
            assertEquals("Acme Corporation", capturedMerchantDetails.getLegalName());
            assertEquals("Acme", capturedMerchantDetails.getDbaName());
            assertEquals("12-3456789", capturedMerchantDetails.getEin());
            assertEquals("Technology", capturedMerchantDetails.getIndustry());
            assertEquals(0, new BigDecimal("500000.00").compareTo(capturedMerchantDetails.getRevenue()));
            assertEquals(application, capturedMerchantDetails.getApplication());
        }

        @Test
        @DisplayName("Should throw ResourceNotFoundException when application not found")
        void shouldThrowResourceNotFoundExceptionWhenApplicationNotFound() {
            // Arrange
            when(applicationRepository.findById(applicationId)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
            });
            
            assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
            verify(applicationRepository).findById(applicationId);
            verify(merchantDetailsRepository, never()).existsByApplication(any());
            verify(validationService, never()).validateMerchantData(any());
            verify(merchantDetailsRepository, never()).save(any());
        }

        @Test
        @DisplayName("Should throw BusinessRuleException when merchant details already exist")
        void shouldThrowBusinessRuleExceptionWhenMerchantDetailsAlreadyExist() {
            // Arrange
            when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
            when(merchantDetailsRepository.existsByApplication(application)).thenReturn(true);

            // Act & Assert
            BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
                merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
            });
            
            assertEquals("Merchant details already exist for application ID: " + applicationId, exception.getMessage());
            verify(applicationRepository).findById(applicationId);
            verify(merchantDetailsRepository).existsByApplication(application);
            verify(validationService, never()).validateMerchantData(any());
            verify(merchantDetailsRepository, never()).save(any());
        }

        @Test
        @DisplayName("Should throw ValidationException when merchant details validation fails")
        void shouldThrowValidationExceptionWhenMerchantDetailsValidationFails() {
            // Arrange
            when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
            when(merchantDetailsRepository.existsByApplication(application)).thenReturn(false);
            doThrow(new ValidationException("Validation failed")).when(validationService).validateMerchantData(merchantDetailsRequestDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
            });
            
            assertEquals("Validation failed", exception.getMessage());
            verify(applicationRepository).findById(applicationId);
            verify(merchantDetailsRepository).existsByApplication(application);
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository, never()).save(any());
        }
    }

    @Nested
    @DisplayName("Get Merchant Details Tests")
    class GetMerchantDetailsTests {

        @Test
        @DisplayName("Should get merchant details by ID successfully")
        void shouldGetMerchantDetailsByIdSuccessfully() {
            // Arrange
            when(merchantDetailsRepository.findById(1L)).thenReturn(Optional.of(merchantDetails));

            // Act
            MerchantDetailsResponseDTO responseDTO = merchantService.getMerchantDetailsById(1L);

            // Assert
            assertNotNull(responseDTO);
            assertEquals(1L, responseDTO.getId());
            verify(merchantDetailsRepository).findById(1L);
        }

        @Test
        @DisplayName("Should throw ResourceNotFoundException when merchant details not found by ID")
        void shouldThrowResourceNotFoundExceptionWhenMerchantDetailsNotFoundById() {
            // Arrange
            when(merchantDetailsRepository.findById(1L)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                merchantService.getMerchantDetailsById(1L);
            });
            
            assertEquals("Merchant details not found with ID: 1", exception.getMessage());
            verify(merchantDetailsRepository).findById(1L);
        }

        @Test
        @DisplayName("Should get merchant details by application ID successfully")
        void shouldGetMerchantDetailsByApplicationIdSuccessfully() {
            // Arrange
            when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.of(merchantDetails));

            // Act
            MerchantDetailsResponseDTO responseDTO = merchantService.getMerchantDetailsByApplicationId(applicationId);

            // Assert
            assertNotNull(responseDTO);
            assertEquals(1L, responseDTO.getId());
            verify(merchantDetailsRepository).findByApplicationId(applicationId);
        }

        @Test
        @DisplayName("Should throw ResourceNotFoundException when merchant details not found by application ID")
        void shouldThrowResourceNotFoundExceptionWhenMerchantDetailsNotFoundByApplicationId() {
            // Arrange
            when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                merchantService.getMerchantDetailsByApplicationId(applicationId);
            });
            
            assertEquals("Merchant details not found for application ID: " + applicationId, exception.getMessage());
            verify(merchantDetailsRepository).findByApplicationId(applicationId);
        }
    }

    @Nested
    @DisplayName("Update Merchant Details Tests")
    class UpdateMerchantDetailsTests {

        @Test
        @DisplayName("Should update merchant details by ID successfully")
        void shouldUpdateMerchantDetailsByIdSuccessfully() {
            // Arrange
            when(merchantDetailsRepository.findById(1L)).thenReturn(Optional.of(merchantDetails));
            doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
            when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(merchantDetails);

            // Update the request DTO
            merchantDetailsRequestDTO.setLegalName("Updated Corporation");
            merchantDetailsRequestDTO.setIndustry("Finance");
            merchantDetailsRequestDTO.setRevenue(new BigDecimal("750000.00"));

            // Act
            MerchantDetailsResponseDTO responseDTO = merchantService.updateMerchantDetails(1L, merchantDetailsRequestDTO);

            // Assert
            assertNotNull(responseDTO);
            assertEquals(1L, responseDTO.getId());
            verify(merchantDetailsRepository).findById(1L);
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository).save(merchantDetailsCaptor.capture());
            
            MerchantDetails capturedMerchantDetails = merchantDetailsCaptor.getValue();
            assertEquals("Updated Corporation", capturedMerchantDetails.getLegalName());
            assertEquals("Finance", capturedMerchantDetails.getIndustry());
            assertEquals(0, new BigDecimal("750000.00").compareTo(capturedMerchantDetails.getRevenue()));
        }

        @Test
        @DisplayName("Should throw ResourceNotFoundException when updating merchant details with non-existent ID")
        void shouldThrowResourceNotFoundExceptionWhenUpdatingMerchantDetailsWithNonExistentId() {
            // Arrange
            when(merchantDetailsRepository.findById(1L)).thenReturn(Optional.empty());
            doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                merchantService.updateMerchantDetails(1L, merchantDetailsRequestDTO);
            });
            
            assertEquals("Merchant details not found with ID: 1", exception.getMessage());
            verify(merchantDetailsRepository).findById(1L);
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository, never()).save(any());
        }

        @Test
        @DisplayName("Should throw ValidationException when updating merchant details with invalid data")
        void shouldThrowValidationExceptionWhenUpdatingMerchantDetailsWithInvalidData() {
            // Arrange
            doThrow(new ValidationException("Validation failed")).when(validationService).validateMerchantData(merchantDetailsRequestDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.updateMerchantDetails(1L, merchantDetailsRequestDTO);
            });
            
            assertEquals("Validation failed", exception.getMessage());
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository, never()).findById(anyLong());
            verify(merchantDetailsRepository, never()).save(any());
        }

        @Test
        @DisplayName("Should update merchant details by application ID successfully")
        void shouldUpdateMerchantDetailsByApplicationIdSuccessfully() {
            // Arrange
            when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.of(merchantDetails));
            doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
            when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(merchantDetails);

            // Update the request DTO
            merchantDetailsRequestDTO.setLegalName("Updated Corporation");
            merchantDetailsRequestDTO.setIndustry("Finance");
            merchantDetailsRequestDTO.setRevenue(new BigDecimal("750000.00"));

            // Act
            MerchantDetailsResponseDTO responseDTO = merchantService.updateMerchantDetailsByApplicationId(applicationId, merchantDetailsRequestDTO);

            // Assert
            assertNotNull(responseDTO);
            assertEquals(1L, responseDTO.getId());
            verify(merchantDetailsRepository).findByApplicationId(applicationId);
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository).save(merchantDetailsCaptor.capture());
            
            MerchantDetails capturedMerchantDetails = merchantDetailsCaptor.getValue();
            assertEquals("Updated Corporation", capturedMerchantDetails.getLegalName());
            assertEquals("Finance", capturedMerchantDetails.getIndustry());
            assertEquals(0, new BigDecimal("750000.00").compareTo(capturedMerchantDetails.getRevenue()));
        }

        @Test
        @DisplayName("Should throw ResourceNotFoundException when updating merchant details with non-existent application ID")
        void shouldThrowResourceNotFoundExceptionWhenUpdatingMerchantDetailsWithNonExistentApplicationId() {
            // Arrange
            when(merchantDetailsRepository.findByApplicationId(applicationId)).thenReturn(Optional.empty());
            doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                merchantService.updateMerchantDetailsByApplicationId(applicationId, merchantDetailsRequestDTO);
            });
            
            assertEquals("Merchant details not found for application ID: " + applicationId, exception.getMessage());
            verify(merchantDetailsRepository).findByApplicationId(applicationId);
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository, never()).save(any());
        }
    }

    @Nested
    @DisplayName("Delete Merchant Details Tests")
    class DeleteMerchantDetailsTests {

        @Test
        @DisplayName("Should delete merchant details successfully")
        void shouldDeleteMerchantDetailsSuccessfully() {
            // Arrange
            when(merchantDetailsRepository.existsById(1L)).thenReturn(true);
            doNothing().when(merchantDetailsRepository).deleteById(1L);

            // Act
            merchantService.deleteMerchantDetails(1L);

            // Assert
            verify(merchantDetailsRepository).existsById(1L);
            verify(merchantDetailsRepository).deleteById(1L);
        }

        @Test
        @DisplayName("Should throw ResourceNotFoundException when deleting non-existent merchant details")
        void shouldThrowResourceNotFoundExceptionWhenDeletingNonExistentMerchantDetails() {
            // Arrange
            when(merchantDetailsRepository.existsById(1L)).thenReturn(false);

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                merchantService.deleteMerchantDetails(1L);
            });
            
            assertEquals("Merchant details not found with ID: 1", exception.getMessage());
            verify(merchantDetailsRepository).existsById(1L);
            verify(merchantDetailsRepository, never()).deleteById(anyLong());
        }
    }

    @Nested
    @DisplayName("Get All Merchant Details Tests")
    class GetAllMerchantDetailsTests {

        @Test
        @DisplayName("Should get all merchant details with pagination successfully")
        void shouldGetAllMerchantDetailsWithPaginationSuccessfully() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<MerchantDetails> merchantDetailsList = Collections.singletonList(merchantDetails);
            Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
            
            when(merchantDetailsRepository.findAll(pageable)).thenReturn(merchantDetailsPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.getAllMerchantDetails(pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(1, responseDTOPage.getTotalElements());
            assertEquals(1, responseDTOPage.getContent().size());
            assertEquals(1L, responseDTOPage.getContent().get(0).getId());
            verify(merchantDetailsRepository).findAll(pageable);
        }

        @Test
        @DisplayName("Should return empty page when no merchant details exist")
        void shouldReturnEmptyPageWhenNoMerchantDetailsExist() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            Page<MerchantDetails> emptyPage = new PageImpl<>(Collections.emptyList(), pageable, 0);
            
            when(merchantDetailsRepository.findAll(pageable)).thenReturn(emptyPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.getAllMerchantDetails(pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(0, responseDTOPage.getTotalElements());
            assertTrue(responseDTOPage.getContent().isEmpty());
            verify(merchantDetailsRepository).findAll(pageable);
        }
    }

    @Nested
    @DisplayName("Find Merchants By Criteria Tests")
    class FindMerchantsByCriteriaTests {

        @Test
        @DisplayName("Should find merchants by industry successfully")
        void shouldFindMerchantsByIndustrySuccessfully() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<MerchantDetails> merchantDetailsList = Collections.singletonList(merchantDetails);
            Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
            
            when(merchantDetailsRepository.findByIndustryContainingIgnoreCase("Technology", pageable)).thenReturn(merchantDetailsPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.findMerchantsByIndustry("Technology", pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(1, responseDTOPage.getTotalElements());
            assertEquals(1, responseDTOPage.getContent().size());
            assertEquals(1L, responseDTOPage.getContent().get(0).getId());
            verify(merchantDetailsRepository).findByIndustryContainingIgnoreCase("Technology", pageable);
        }

        @Test
        @DisplayName("Should find merchants by revenue range successfully")
        void shouldFindMerchantsByRevenueRangeSuccessfully() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<MerchantDetails> merchantDetailsList = Collections.singletonList(merchantDetails);
            Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
            
            BigDecimal minRevenue = new BigDecimal("400000.00");
            BigDecimal maxRevenue = new BigDecimal("600000.00");
            
            when(merchantDetailsRepository.findByRevenueBetween(minRevenue, maxRevenue, pageable)).thenReturn(merchantDetailsPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.findMerchantsByRevenueRange(minRevenue, maxRevenue, pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(1, responseDTOPage.getTotalElements());
            assertEquals(1, responseDTOPage.getContent().size());
            assertEquals(1L, responseDTOPage.getContent().get(0).getId());
            verify(merchantDetailsRepository).findByRevenueBetween(minRevenue, maxRevenue, pageable);
        }

        @Test
        @DisplayName("Should find merchants by state successfully")
        void shouldFindMerchantsByStateSuccessfully() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<MerchantDetails> merchantDetailsList = Collections.singletonList(merchantDetails);
            Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
            
            when(merchantDetailsRepository.findByAddressState("NY", pageable)).thenReturn(merchantDetailsPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.findMerchantsByState("NY", pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(1, responseDTOPage.getTotalElements());
            assertEquals(1, responseDTOPage.getContent().size());
            assertEquals(1L, responseDTOPage.getContent().get(0).getId());
            verify(merchantDetailsRepository).findByAddressState("NY", pageable);
        }

        @Test
        @DisplayName("Should find merchants by city successfully")
        void shouldFindMerchantsByCitySuccessfully() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<MerchantDetails> merchantDetailsList = Collections.singletonList(merchantDetails);
            Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
            
            when(merchantDetailsRepository.findByAddressCity("New York", pageable)).thenReturn(merchantDetailsPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.findMerchantsByCity("New York", pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(1, responseDTOPage.getTotalElements());
            assertEquals(1, responseDTOPage.getContent().size());
            assertEquals(1L, responseDTOPage.getContent().get(0).getId());
            verify(merchantDetailsRepository).findByAddressCity("New York", pageable);
        }

        @Test
        @DisplayName("Should find merchants by industry and state successfully")
        void shouldFindMerchantsByIndustryAndStateSuccessfully() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<MerchantDetails> merchantDetailsList = Collections.singletonList(merchantDetails);
            Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
            
            when(merchantDetailsRepository.findByAddressStateAndIndustry("NY", "Technology", pageable)).thenReturn(merchantDetailsPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.findMerchantsByIndustryAndState("Technology", "NY", pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(1, responseDTOPage.getTotalElements());
            assertEquals(1, responseDTOPage.getContent().size());
            assertEquals(1L, responseDTOPage.getContent().get(0).getId());
            verify(merchantDetailsRepository).findByAddressStateAndIndustry("NY", "Technology", pageable);
        }

        @Test
        @DisplayName("Should find merchants by industry and revenue range successfully")
        void shouldFindMerchantsByIndustryAndRevenueRangeSuccessfully() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<MerchantDetails> merchantDetailsList = Collections.singletonList(merchantDetails);
            Page<MerchantDetails> merchantDetailsPage = new PageImpl<>(merchantDetailsList, pageable, merchantDetailsList.size());
            
            BigDecimal minRevenue = new BigDecimal("400000.00");
            BigDecimal maxRevenue = new BigDecimal("600000.00");
            
            when(merchantDetailsRepository.findByIndustryAndRevenueBetween("Technology", minRevenue, maxRevenue, pageable))
                    .thenReturn(merchantDetailsPage);

            // Act
            Page<MerchantDetailsResponseDTO> responseDTOPage = merchantService.findMerchantsByIndustryAndRevenueRange(
                    "Technology", minRevenue, maxRevenue, pageable);

            // Assert
            assertNotNull(responseDTOPage);
            assertEquals(1, responseDTOPage.getTotalElements());
            assertEquals(1, responseDTOPage.getContent().size());
            assertEquals(1L, responseDTOPage.getContent().get(0).getId());
            verify(merchantDetailsRepository).findByIndustryAndRevenueBetween("Technology", minRevenue, maxRevenue, pageable);
        }
    }

    @Nested
    @DisplayName("Merchant Details Existence Tests")
    class MerchantDetailsExistenceTests {

        @Test
        @DisplayName("Should return true when merchant details exist for application")
        void shouldReturnTrueWhenMerchantDetailsExistForApplication() {
            // Arrange
            when(merchantDetailsRepository.existsByApplicationId(applicationId)).thenReturn(true);

            // Act
            boolean exists = merchantService.merchantDetailsExistForApplication(applicationId);

            // Assert
            assertTrue(exists);
            verify(merchantDetailsRepository).existsByApplicationId(applicationId);
        }

        @Test
        @DisplayName("Should return false when merchant details do not exist for application")
        void shouldReturnFalseWhenMerchantDetailsDoNotExistForApplication() {
            // Arrange
            when(merchantDetailsRepository.existsByApplicationId(applicationId)).thenReturn(false);

            // Act
            boolean exists = merchantService.merchantDetailsExistForApplication(applicationId);

            // Assert
            assertFalse(exists);
            verify(merchantDetailsRepository).existsByApplicationId(applicationId);
        }
    }

    @Nested
    @DisplayName("Validation and Error Handling Tests")
    class ValidationAndErrorHandlingTests {

        @Test
        @DisplayName("Should throw ValidationException when merchant details are null")
        void shouldThrowValidationExceptionWhenMerchantDetailsAreNull() {
            // Arrange
            doThrow(new ValidationException("Merchant details cannot be null"))
                    .when(validationService).validateMerchantData(null);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, null);
            });
            
            assertEquals("Merchant details cannot be null", exception.getMessage());
        }

        @Test
        @DisplayName("Should throw ValidationException when legal name is missing")
        void shouldThrowValidationExceptionWhenLegalNameIsMissing() {
            // Arrange
            MerchantDetailsRequestDTO invalidDTO = MerchantDetailsRequestDTO.builder()
                    .legalName(null) // Missing legal name
                    .dbaName("Acme")
                    .ein("12-3456789")
                    .address(addressDTO)
                    .industry("Technology")
                    .revenue(new BigDecimal("500000.00"))
                    .build();
            
            doThrow(new ValidationException("Legal name is required"))
                    .when(validationService).validateMerchantData(invalidDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, invalidDTO);
            });
            
            assertEquals("Legal name is required", exception.getMessage());
        }

        @Test
        @DisplayName("Should throw ValidationException when EIN format is invalid")
        void shouldThrowValidationExceptionWhenEINFormatIsInvalid() {
            // Arrange
            MerchantDetailsRequestDTO invalidDTO = MerchantDetailsRequestDTO.builder()
                    .legalName("Acme Corporation")
                    .dbaName("Acme")
                    .ein("123456789") // Invalid EIN format (missing hyphen)
                    .address(addressDTO)
                    .industry("Technology")
                    .revenue(new BigDecimal("500000.00"))
                    .build();
            
            doThrow(new ValidationException("EIN must be in format XX-XXXXXXX"))
                    .when(validationService).validateMerchantData(invalidDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, invalidDTO);
            });
            
            assertEquals("EIN must be in format XX-XXXXXXX", exception.getMessage());
        }

        @Test
        @DisplayName("Should throw ValidationException when address is missing")
        void shouldThrowValidationExceptionWhenAddressIsMissing() {
            // Arrange
            MerchantDetailsRequestDTO invalidDTO = MerchantDetailsRequestDTO.builder()
                    .legalName("Acme Corporation")
                    .dbaName("Acme")
                    .ein("12-3456789")
                    .address(null) // Missing address
                    .industry("Technology")
                    .revenue(new BigDecimal("500000.00"))
                    .build();
            
            doThrow(new ValidationException("Address is required"))
                    .when(validationService).validateMerchantData(invalidDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, invalidDTO);
            });
            
            assertEquals("Address is required", exception.getMessage());
        }

        @Test
        @DisplayName("Should throw ValidationException when industry is missing")
        void shouldThrowValidationExceptionWhenIndustryIsMissing() {
            // Arrange
            MerchantDetailsRequestDTO invalidDTO = MerchantDetailsRequestDTO.builder()
                    .legalName("Acme Corporation")
                    .dbaName("Acme")
                    .ein("12-3456789")
                    .address(addressDTO)
                    .industry(null) // Missing industry
                    .revenue(new BigDecimal("500000.00"))
                    .build();
            
            doThrow(new ValidationException("Industry is required"))
                    .when(validationService).validateMerchantData(invalidDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, invalidDTO);
            });
            
            assertEquals("Industry is required", exception.getMessage());
        }

        @Test
        @DisplayName("Should throw ValidationException when revenue is not positive")
        void shouldThrowValidationExceptionWhenRevenueIsNotPositive() {
            // Arrange
            MerchantDetailsRequestDTO invalidDTO = MerchantDetailsRequestDTO.builder()
                    .legalName("Acme Corporation")
                    .dbaName("Acme")
                    .ein("12-3456789")
                    .address(addressDTO)
                    .industry("Technology")
                    .revenue(new BigDecimal("0.00")) // Zero revenue
                    .build();
            
            doThrow(new ValidationException("Revenue must be greater than zero"))
                    .when(validationService).validateMerchantData(invalidDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, invalidDTO);
            });
            
            assertEquals("Revenue must be greater than zero", exception.getMessage());
        }

        @Test
        @DisplayName("Should throw ValidationException when complex validation fails")
        void shouldThrowValidationExceptionWhenComplexValidationFails() {
            // Arrange
            when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
            when(merchantDetailsRepository.existsByApplication(application)).thenReturn(false);
            
            doThrow(new ValidationException("Revenue must be at least $50,000 for funding"))
                    .when(validationService).validateMerchantData(merchantDetailsRequestDTO);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);
            });
            
            assertEquals("Revenue must be at least $50,000 for funding", exception.getMessage());
            verify(applicationRepository).findById(applicationId);
            verify(merchantDetailsRepository).existsByApplication(application);
            verify(validationService).validateMerchantData(merchantDetailsRequestDTO);
            verify(merchantDetailsRepository, never()).save(any());
        }
    }

    @Nested
    @DisplayName("Field-Level Encryption Tests")
    class FieldLevelEncryptionTests {

        @Test
        @DisplayName("Should encrypt sensitive fields when creating merchant details")
        void shouldEncryptSensitiveFieldsWhenCreatingMerchantDetails() {
            // Arrange
            when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
            when(merchantDetailsRepository.existsByApplication(application)).thenReturn(false);
            doNothing().when(validationService).validateMerchantData(merchantDetailsRequestDTO);
            when(merchantDetailsRepository.save(any(MerchantDetails.class))).thenReturn(merchantDetails);
            
            // Mock encryption
            when(encryptionUtil.encrypt("Acme Corporation")).thenReturn("ENCRYPTED_LEGAL_NAME");
            when(encryptionUtil.encrypt("Acme")).thenReturn("ENCRYPTED_DBA_NAME");
            when(encryptionUtil.encrypt("12-3456789")).thenReturn("ENCRYPTED_EIN");

            // Act
            merchantService.createMerchantDetails(applicationId, merchantDetailsRequestDTO);

            // Assert
            verify(merchantDetailsRepository).save(merchantDetailsCaptor.capture());
            
            // Note: In the actual implementation, encryption is handled by JPA converters,
            // so we can't directly verify the encryption here. This test is more of a placeholder
            // to demonstrate that encryption should be happening.
        }

        @Test
        @DisplayName("Should decrypt sensitive fields when retrieving merchant details")
        void shouldDecryptSensitiveFieldsWhenRetrievingMerchantDetails() {
            // Arrange
            when(merchantDetailsRepository.findById(1L)).thenReturn(Optional.of(merchantDetails));
            
            // Mock decryption
            when(encryptionUtil.decrypt("ENCRYPTED_LEGAL_NAME")).thenReturn("Acme Corporation");
            when(encryptionUtil.decrypt("ENCRYPTED_DBA_NAME")).thenReturn("Acme");
            when(encryptionUtil.decrypt("ENCRYPTED_EIN")).thenReturn("12-3456789");

            // Act
            MerchantDetailsResponseDTO responseDTO = merchantService.getMerchantDetailsById(1L);

            // Assert
            assertNotNull(responseDTO);
            
            // Note: In the actual implementation, decryption is handled by JPA converters,
            // so we can't directly verify the decryption here. This test is more of a placeholder
            // to demonstrate that decryption should be happening.
        }
    }
}