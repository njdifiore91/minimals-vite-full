package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ApplicationNotFoundException;
import com.dollarfunding.mca.exception.InvalidApplicationStateException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.util.ValidationResult;

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
import org.springframework.data.jpa.domain.Specification;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the ApplicationServiceImpl class.
 * 
 * These tests verify that the ApplicationService correctly processes application data,
 * applies business rules and validation logic, manages transactions across PostgreSQL and Redis,
 * validates application completeness, integrates with ValidationService for business rule application,
 * and verifies notification delivery for application status changes.
 */
@ExtendWith(MockitoExtension.class)
public class ApplicationServiceImplTest {

    @Mock
    private ApplicationRepository applicationRepository;
    
    @Mock
    private ValidationService validationService;
    
    @Mock
    private NotificationService notificationService;
    
    @InjectMocks
    private ApplicationServiceImpl applicationService;
    
    private UUID applicationId;
    private Application application;
    private ApplicationRequestDTO applicationRequestDTO;
    private Map<String, Object> metadata;
    
    @BeforeEach
    void setUp() {
        // Initialize test data
        applicationId = UUID.randomUUID();
        metadata = new HashMap<>();
        metadata.put("businessName", "Test Business");
        metadata.put("requestedAmount", 50000);
        metadata.put("industry", "Retail");
        
        // Create application entity
        application = new Application();
        application.setId(applicationId);
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        application.setMetadata(metadata);
        application.setCreatedAt(LocalDateTime.now());
        application.setUpdatedAt(LocalDateTime.now());
        
        // Create application request DTO
        applicationRequestDTO = new ApplicationRequestDTO();
        applicationRequestDTO.setMetadata(metadata);
    }
    
    @Test
    @DisplayName("Should create a new application successfully")
    void createApplication_Success() {
        // Arrange
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(true);
        
        when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                .thenReturn(validationResult);
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        // Act
        ApplicationResponseDTO result = applicationService.createApplication(applicationRequestDTO);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(ApplicationStatus.NEW, result.getStatus());
        assertEquals(ReviewStatus.NOT_REVIEWED, result.getReviewStatus());
        assertEquals(metadata, result.getMetadata());
        
        // Verify interactions
        verify(validationService).validateApplicationData(applicationRequestDTO);
        verify(applicationRepository).save(any(Application.class));
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.NEW);
    }
    
    @Test
    @DisplayName("Should throw ValidationException when application data is invalid")
    void createApplication_ValidationFailure() {
        // Arrange
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(false);
        Map<String, String> errors = new HashMap<>();
        errors.put("businessName", "Business name is required");
        validationResult.setErrors(errors);
        
        when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                .thenReturn(validationResult);
        
        // Act & Assert
        ValidationException exception = assertThrows(ValidationException.class, () -> {
            applicationService.createApplication(applicationRequestDTO);
        });
        
        // Verify exception details
        assertEquals("Application data validation failed", exception.getMessage());
        assertEquals(errors, exception.getErrors());
        
        // Verify interactions
        verify(validationService).validateApplicationData(applicationRequestDTO);
        verify(applicationRepository, never()).save(any(Application.class));
        verify(notificationService, never()).sendApplicationStatusNotification(any(UUID.class), any(ApplicationStatus.class));
    }
    
    @Test
    @DisplayName("Should retrieve an application by ID successfully")
    void getApplicationById_Success() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        
        // Act
        ApplicationResponseDTO result = applicationService.getApplicationById(applicationId);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(ApplicationStatus.NEW, result.getStatus());
        assertEquals(ReviewStatus.NOT_REVIEWED, result.getReviewStatus());
        assertEquals(metadata, result.getMetadata());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when application is not found")
    void getApplicationById_NotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.getApplicationById(applicationId);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
    }
    
    @Test
    @DisplayName("Should update an application successfully")
    void updateApplication_Success() {
        // Arrange
        Map<String, Object> updatedMetadata = new HashMap<>(metadata);
        updatedMetadata.put("requestedAmount", 75000);
        updatedMetadata.put("notes", "Updated application");
        
        ApplicationRequestDTO updateRequest = new ApplicationRequestDTO();
        updateRequest.setMetadata(updatedMetadata);
        updateRequest.setStatus(ApplicationStatus.PROCESSING);
        
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(true);
        
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                .thenReturn(validationResult);
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        // Act
        ApplicationResponseDTO result = applicationService.updateApplication(applicationId, updateRequest);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(ApplicationStatus.PROCESSING, result.getStatus());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateApplicationData(updateRequest);
        verify(applicationRepository).save(any(Application.class));
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.PROCESSING);
        
        // Verify application was updated correctly
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertEquals(updatedMetadata, savedApplication.getMetadata());
        assertEquals(ApplicationStatus.PROCESSING, savedApplication.getStatus());
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when updating non-existent application")
    void updateApplication_NotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.updateApplication(applicationId, applicationRequestDTO);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(validationService, never()).validateApplicationData(any(ApplicationRequestDTO.class));
        verify(applicationRepository, never()).save(any(Application.class));
    }
    
    @Test
    @DisplayName("Should throw ValidationException when update data is invalid")
    void updateApplication_ValidationFailure() {
        // Arrange
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(false);
        Map<String, String> errors = new HashMap<>();
        errors.put("requestedAmount", "Requested amount must be positive");
        validationResult.setErrors(errors);
        
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                .thenReturn(validationResult);
        
        // Act & Assert
        ValidationException exception = assertThrows(ValidationException.class, () -> {
            applicationService.updateApplication(applicationId, applicationRequestDTO);
        });
        
        // Verify exception details
        assertEquals("Application data validation failed", exception.getMessage());
        assertEquals(errors, exception.getErrors());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateApplicationData(applicationRequestDTO);
        verify(applicationRepository, never()).save(any(Application.class));
    }
    
    @Test
    @DisplayName("Should delete an application successfully")
    void deleteApplication_Success() {
        // Arrange
        when(applicationRepository.existsById(applicationId))
                .thenReturn(true);
        doNothing().when(applicationRepository).deleteById(applicationId);
        
        // Act
        applicationService.deleteApplication(applicationId);
        
        // Verify interactions
        verify(applicationRepository).existsById(applicationId);
        verify(applicationRepository).deleteById(applicationId);
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when deleting non-existent application")
    void deleteApplication_NotFound() {
        // Arrange
        when(applicationRepository.existsById(applicationId))
                .thenReturn(false);
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.deleteApplication(applicationId);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).existsById(applicationId);
        verify(applicationRepository, never()).deleteById(any(UUID.class));
    }
    
    @Test
    @DisplayName("Should retrieve applications with filter criteria")
    void getApplications_WithFilter() {
        // Arrange
        ApplicationFilterDTO filterDTO = new ApplicationFilterDTO();
        filterDTO.setStatus(ApplicationStatus.NEW);
        filterDTO.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        filterDTO.setStartDate(LocalDateTime.now().minusDays(7));
        filterDTO.setEndDate(LocalDateTime.now());
        
        Pageable pageable = PageRequest.of(0, 10);
        List<Application> applications = List.of(application);
        Page<Application> applicationPage = new PageImpl<>(applications, pageable, applications.size());
        
        when(applicationRepository.findAll(any(Specification.class), eq(pageable)))
                .thenReturn(applicationPage);
        
        // Act
        Page<ApplicationResponseDTO> result = applicationService.getApplications(filterDTO, pageable);
        
        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(applicationId, result.getContent().get(0).getId());
        
        // Verify interactions
        verify(applicationRepository).findAll(any(Specification.class), eq(pageable));
    }
    
    @Test
    @DisplayName("Should update application status successfully")
    void updateApplicationStatus_Success() {
        // Arrange
        ApplicationStatus newStatus = ApplicationStatus.PROCESSING;
        application.setStatus(ApplicationStatus.NEW); // Ensure initial status is set
        
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        // Act
        ApplicationResponseDTO result = applicationService.updateApplicationStatus(applicationId, newStatus);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(newStatus, result.getStatus());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository).save(any(Application.class));
        verify(notificationService).sendApplicationStatusNotification(applicationId, newStatus);
        
        // Verify application was updated correctly
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertEquals(newStatus, savedApplication.getStatus());
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when updating status of non-existent application")
    void updateApplicationStatus_NotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.updateApplicationStatus(applicationId, ApplicationStatus.PROCESSING);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository, never()).save(any(Application.class));
    }
    
    @Test
    @DisplayName("Should throw InvalidApplicationStateException for invalid status transition")
    void updateApplicationStatus_InvalidTransition() {
        // Arrange
        application.setStatus(ApplicationStatus.NEW);
        ApplicationStatus invalidStatus = ApplicationStatus.APPROVED; // Invalid direct transition from NEW to APPROVED
        
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        
        // Act & Assert
        InvalidApplicationStateException exception = assertThrows(InvalidApplicationStateException.class, () -> {
            applicationService.updateApplicationStatus(applicationId, invalidStatus);
        });
        
        // Verify exception details
        assertEquals("Invalid status transition from NEW to APPROVED", exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository, never()).save(any(Application.class));
    }
    
    @Test
    @DisplayName("Should update application review status successfully")
    void updateApplicationReviewStatus_Success() {
        // Arrange
        ReviewStatus newReviewStatus = ReviewStatus.IN_REVIEW;
        
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        // Act
        ApplicationResponseDTO result = applicationService.updateApplicationReviewStatus(applicationId, newReviewStatus);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(newReviewStatus, result.getReviewStatus());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository).save(any(Application.class));
        verify(notificationService).sendApplicationReviewStatusNotification(applicationId, newReviewStatus);
        
        // Verify application was updated correctly
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertEquals(newReviewStatus, savedApplication.getReviewStatus());
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when updating review status of non-existent application")
    void updateApplicationReviewStatus_NotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.updateApplicationReviewStatus(applicationId, ReviewStatus.IN_REVIEW);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository, never()).save(any(Application.class));
    }
    
    @Test
    @DisplayName("Should add document to application successfully")
    void addDocumentToApplication_Success() {
        // Arrange
        Document document = new Document();
        document.setId(UUID.randomUUID());
        document.setType("BANK_STATEMENT");
        document.setStoragePath("s3://mca-documents/12345.pdf");
        
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        // Act
        ApplicationResponseDTO result = applicationService.addDocumentToApplication(applicationId, document);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository).save(any(Application.class));
        
        // Verify document was added to application
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository).save(applicationCaptor.capture());
        Application savedApplication = applicationCaptor.getValue();
        assertTrue(savedApplication.getDocuments().contains(document));
        assertEquals(application, document.getApplication());
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when adding document to non-existent application")
    void addDocumentToApplication_NotFound() {
        // Arrange
        Document document = new Document();
        document.setId(UUID.randomUUID());
        
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.addDocumentToApplication(applicationId, document);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository, never()).save(any(Application.class));
    }
    
    @Test
    @DisplayName("Should evaluate application completeness correctly when complete")
    void isApplicationComplete_Complete() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(true);
        
        when(validationService.validateApplicationCompleteness(application))
                .thenReturn(validationResult);
        
        // Act
        boolean result = applicationService.isApplicationComplete(applicationId);
        
        // Assert
        assertTrue(result);
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateApplicationCompleteness(application);
    }
    
    @Test
    @DisplayName("Should evaluate application completeness correctly when incomplete")
    void isApplicationComplete_Incomplete() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(false);
        Map<String, String> errors = new HashMap<>();
        errors.put("documents", "Missing required document: Bank Statement");
        validationResult.setErrors(errors);
        
        when(validationService.validateApplicationCompleteness(application))
                .thenReturn(validationResult);
        
        // Act
        boolean result = applicationService.isApplicationComplete(applicationId);
        
        // Assert
        assertFalse(result);
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(validationService).validateApplicationCompleteness(application);
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when evaluating completeness of non-existent application")
    void isApplicationComplete_NotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.isApplicationComplete(applicationId);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(validationService, never()).validateApplicationCompleteness(any(Application.class));
    }
    
    @Test
    @DisplayName("Should process application successfully and mark as COMPLETED when valid and complete")
    void processApplication_ValidAndComplete() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(true);
        
        when(validationService.validateApplication(application))
                .thenReturn(validationResult);
        
        // Mock isApplicationComplete to return true
        doReturn(true).when(applicationService).isApplicationComplete(applicationId);
        
        // Act
        ApplicationResponseDTO result = applicationService.processApplication(applicationId);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(ApplicationStatus.COMPLETED, result.getStatus());
        
        // Verify interactions
        verify(applicationRepository, times(2)).findById(applicationId);
        verify(applicationRepository, times(2)).save(any(Application.class));
        verify(validationService).validateApplication(application);
        verify(applicationService).isApplicationComplete(applicationId);
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.COMPLETED);
        
        // Verify application status transitions
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository, times(2)).save(applicationCaptor.capture());
        List<Application> savedApplications = applicationCaptor.getAllValues();
        assertEquals(ApplicationStatus.PROCESSING, savedApplications.get(0).getStatus()); // First save: NEW -> PROCESSING
        assertEquals(ApplicationStatus.COMPLETED, savedApplications.get(1).getStatus()); // Second save: PROCESSING -> COMPLETED
    }
    
    @Test
    @DisplayName("Should process application successfully and mark as PENDING when valid but incomplete")
    void processApplication_ValidButIncomplete() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(true);
        
        when(validationService.validateApplication(application))
                .thenReturn(validationResult);
        
        // Mock isApplicationComplete to return false
        doReturn(false).when(applicationService).isApplicationComplete(applicationId);
        
        // Act
        ApplicationResponseDTO result = applicationService.processApplication(applicationId);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(ApplicationStatus.PENDING, result.getStatus());
        
        // Verify interactions
        verify(applicationRepository, times(2)).findById(applicationId);
        verify(applicationRepository, times(2)).save(any(Application.class));
        verify(validationService).validateApplication(application);
        verify(applicationService).isApplicationComplete(applicationId);
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.PENDING);
        
        // Verify application status transitions
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository, times(2)).save(applicationCaptor.capture());
        List<Application> savedApplications = applicationCaptor.getAllValues();
        assertEquals(ApplicationStatus.PROCESSING, savedApplications.get(0).getStatus()); // First save: NEW -> PROCESSING
        assertEquals(ApplicationStatus.PENDING, savedApplications.get(1).getStatus()); // Second save: PROCESSING -> PENDING
    }
    
    @Test
    @DisplayName("Should process application and mark as REJECTED when validation fails")
    void processApplication_ValidationFailure() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.of(application));
        when(applicationRepository.save(any(Application.class)))
                .thenReturn(application);
        
        ValidationResult validationResult = new ValidationResult();
        validationResult.setValid(false);
        Map<String, String> errors = new HashMap<>();
        errors.put("businessName", "Business name is required");
        validationResult.setErrors(errors);
        
        when(validationService.validateApplication(application))
                .thenReturn(validationResult);
        
        // Act
        ApplicationResponseDTO result = applicationService.processApplication(applicationId);
        
        // Assert
        assertNotNull(result);
        assertEquals(applicationId, result.getId());
        assertEquals(ApplicationStatus.REJECTED, result.getStatus());
        
        // Verify interactions
        verify(applicationRepository, times(2)).findById(applicationId);
        verify(applicationRepository, times(2)).save(any(Application.class));
        verify(validationService).validateApplication(application);
        verify(applicationService, never()).isApplicationComplete(any(UUID.class));
        verify(notificationService).sendApplicationStatusNotification(applicationId, ApplicationStatus.REJECTED);
        
        // Verify application status transitions
        ArgumentCaptor<Application> applicationCaptor = ArgumentCaptor.forClass(Application.class);
        verify(applicationRepository, times(2)).save(applicationCaptor.capture());
        List<Application> savedApplications = applicationCaptor.getAllValues();
        assertEquals(ApplicationStatus.PROCESSING, savedApplications.get(0).getStatus()); // First save: NEW -> PROCESSING
        assertEquals(ApplicationStatus.REJECTED, savedApplications.get(1).getStatus()); // Second save: PROCESSING -> REJECTED
    }
    
    @Test
    @DisplayName("Should throw ApplicationNotFoundException when processing non-existent application")
    void processApplication_NotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId))
                .thenReturn(Optional.empty());
        
        // Act & Assert
        ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
            applicationService.processApplication(applicationId);
        });
        
        // Verify exception details
        assertEquals("Application not found with ID: " + applicationId, exception.getMessage());
        
        // Verify interactions
        verify(applicationRepository).findById(applicationId);
        verify(applicationRepository, never()).save(any(Application.class));
        verify(validationService, never()).validateApplication(any(Application.class));
    }
}