package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ApplicationNotFoundException;
import com.dollarfunding.mca.exception.InvalidApplicationStateException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.service.ValidationService.ValidationResult;
import com.dollarfunding.mca.service.ValidationService.ValidationSeverity;
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

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the ApplicationServiceImpl class.
 * 
 * This test suite verifies that the ApplicationServiceImpl correctly processes application data,
 * applies business rules and validation logic, manages transactions across PostgreSQL and Redis,
 * evaluates application completeness, integrates with ValidationService for business rule application,
 * and delivers notifications for application status changes.
 * 
 * The tests use Mockito to mock dependencies including ApplicationRepository, ValidationService,
 * and NotificationService, allowing for isolated testing of the service's functionality.
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

    @Captor
    private ArgumentCaptor<Application> applicationCaptor;

    private UUID testId;
    private Application testApplication;
    private ApplicationRequestDTO testApplicationDTO;
    private Map<String, Object> testMetadata;
    private ValidationResult validValidationResult;
    private ValidationResult invalidValidationResult;
    private Document testDocument;

    @BeforeEach
    void setUp() {
        // Initialize test data
        testId = UUID.randomUUID();
        testMetadata = new HashMap<>();
        testMetadata.put("source", "api");
        testMetadata.put("processingStartTime", LocalDateTime.now().toString());
        
        // Create test application
        testApplication = new Application();
        testApplication.setId(testId);
        testApplication.setStatus(ApplicationStatus.NEW);
        testApplication.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        testApplication.setMetadata(testMetadata);
        testApplication.setCreatedAt(LocalDateTime.now());
        testApplication.setUpdatedAt(LocalDateTime.now());
        
        // Create test application DTO
        testApplicationDTO = new ApplicationRequestDTO();
        testApplicationDTO.setMetadata(testMetadata);
        
        // Create validation results
        Map<String, String> noErrors = Collections.emptyMap();
        validValidationResult = new ValidationResult(true, noErrors);
        
        Map<String, String> errors = new HashMap<>();
        errors.put("field1", "Error message 1");
        errors.put("field2", "Error message 2");
        invalidValidationResult = new ValidationResult(false, errors, ValidationSeverity.ERROR);
        
        // Create test document
        testDocument = new Document(testId, DocumentType.BANK_STATEMENT, "s3://mca-documents-production/test-document.pdf");
        testDocument.setId(UUID.randomUUID());
        testDocument.setClassification("Bank Statement");
        testDocument.setUploadedAt(LocalDateTime.now());
        
        Map<String, Object> docMetadata = new HashMap<>();
        docMetadata.put("pageCount", 5);
        docMetadata.put("fileSize", 1024);
        testDocument.setMetadata(docMetadata);
    }
    
    @Nested
    @DisplayName("Create Application Tests")
    class CreateApplicationTests {
        
        @Test
        @DisplayName("Should create application successfully")
        void shouldCreateApplicationSuccessfully() {
            // Arrange
            when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                    .thenReturn(validValidationResult);
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
            when(notificationService.sendApplicationCreatedNotification(any(Application.class)))
                    .thenReturn(true);

            // Act
            Application result = applicationService.createApplication(testApplicationDTO);

            // Assert
            assertNotNull(result);
            assertEquals(testId, result.getId());
            assertEquals(ApplicationStatus.NEW, result.getStatus());
            assertEquals(ReviewStatus.NOT_REVIEWED, result.getReviewStatus());
            assertTrue(result.getMetadata().containsKey("source"));
            assertTrue(result.getMetadata().containsKey("processingStartTime"));

            // Verify interactions
            verify(validationService).validateApplicationData(testApplicationDTO);
            verify(applicationRepository).save(any(Application.class));
            verify(notificationService).sendApplicationCreatedNotification(any(Application.class));
        }

        @Test
        @DisplayName("Should throw ValidationException when validation fails")
        void shouldThrowValidationExceptionWhenValidationFails() {
            // Arrange
            when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                    .thenReturn(invalidValidationResult);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                applicationService.createApplication(testApplicationDTO);
            });

            // Verify exception details
            assertEquals("Invalid application data", exception.getMessage());
            assertEquals(2, exception.getErrors().size());
            assertTrue(exception.getErrors().containsKey("field1"));
            assertTrue(exception.getErrors().containsKey("field2"));

            // Verify interactions
            verify(validationService).validateApplicationData(testApplicationDTO);
            verify(applicationRepository, never()).save(any(Application.class));
            verify(notificationService, never()).sendApplicationCreatedNotification(any(Application.class));
        }
    }
    
    @Nested
    @DisplayName("Get Application Tests")
    class GetApplicationTests {
        
        @Test
        @DisplayName("Should retrieve application by ID successfully")
        void shouldRetrieveApplicationByIdSuccessfully() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));

            // Act
            Application result = applicationService.getApplicationById(testId);

            // Assert
            assertNotNull(result);
            assertEquals(testId, result.getId());
            assertEquals(ApplicationStatus.NEW, result.getStatus());
            assertEquals(ReviewStatus.NOT_REVIEWED, result.getReviewStatus());

            // Verify interactions
            verify(applicationRepository).findById(testId);
        }

        @Test
        @DisplayName("Should throw ApplicationNotFoundException when application not found")
        void shouldThrowApplicationNotFoundExceptionWhenApplicationNotFound() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.empty());

            // Act & Assert
            ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
                applicationService.getApplicationById(testId);
            });

            // Verify exception details
            assertEquals("Application not found with ID: " + testId, exception.getMessage());

            // Verify interactions
            verify(applicationRepository).findById(testId);
        }
        
        @Test
        @DisplayName("Should retrieve all applications with pagination")
        void shouldRetrieveAllApplicationsWithPagination() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<Application> applications = Arrays.asList(testApplication);
            Page<Application> applicationPage = new PageImpl<>(applications, pageable, applications.size());
            
            when(applicationRepository.findAll(pageable)).thenReturn(applicationPage);

            // Act
            Page<Application> result = applicationService.getAllApplications(pageable);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getTotalElements());
            assertEquals(testId, result.getContent().get(0).getId());

            // Verify interactions
            verify(applicationRepository).findAll(pageable);
        }
        
        @Test
        @DisplayName("Should retrieve applications by status with pagination")
        void shouldRetrieveApplicationsByStatusWithPagination() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<Application> applications = Arrays.asList(testApplication);
            Page<Application> applicationPage = new PageImpl<>(applications, pageable, applications.size());
            
            when(applicationRepository.findByStatus(ApplicationStatus.NEW, pageable)).thenReturn(applicationPage);

            // Act
            Page<Application> result = applicationService.getApplicationsByStatus(ApplicationStatus.NEW, pageable);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getTotalElements());
            assertEquals(testId, result.getContent().get(0).getId());
            assertEquals(ApplicationStatus.NEW, result.getContent().get(0).getStatus());

            // Verify interactions
            verify(applicationRepository).findByStatus(ApplicationStatus.NEW, pageable);
        }
        
        @Test
        @DisplayName("Should retrieve applications by review status with pagination")
        void shouldRetrieveApplicationsByReviewStatusWithPagination() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<Application> applications = Arrays.asList(testApplication);
            Page<Application> applicationPage = new PageImpl<>(applications, pageable, applications.size());
            
            when(applicationRepository.findByReviewStatus(ReviewStatus.NOT_REVIEWED, pageable)).thenReturn(applicationPage);

            // Act
            Page<Application> result = applicationService.getApplicationsByReviewStatus(ReviewStatus.NOT_REVIEWED, pageable);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getTotalElements());
            assertEquals(testId, result.getContent().get(0).getId());
            assertEquals(ReviewStatus.NOT_REVIEWED, result.getContent().get(0).getReviewStatus());

            // Verify interactions
            verify(applicationRepository).findByReviewStatus(ReviewStatus.NOT_REVIEWED, pageable);
        }
    }
    
    @Nested
    @DisplayName("Update Application Tests")
    class UpdateApplicationTests {
        
        @Test
        @DisplayName("Should update application successfully")
        void shouldUpdateApplicationSuccessfully() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                    .thenReturn(validValidationResult);
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);

            // Update metadata in DTO
            Map<String, Object> updatedMetadata = new HashMap<>(testMetadata);
            updatedMetadata.put("additionalField", "value");
            testApplicationDTO.setMetadata(updatedMetadata);

            // Act
            Application result = applicationService.updateApplication(testId, testApplicationDTO);

            // Assert
            assertNotNull(result);
            assertEquals(testId, result.getId());
            assertTrue(result.getMetadata().containsKey("additionalField"));
            assertTrue(result.getMetadata().containsKey("lastUpdated"));

            // Verify interactions
            verify(applicationRepository).findById(testId);
            verify(validationService).validateApplicationData(testApplicationDTO);
            verify(applicationRepository).save(any(Application.class));
        }

        @Test
        @DisplayName("Should throw ApplicationNotFoundException when updating non-existent application")
        void shouldThrowApplicationNotFoundExceptionWhenUpdatingNonExistentApplication() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.empty());
            when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                    .thenReturn(validValidationResult);

            // Act & Assert
            ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
                applicationService.updateApplication(testId, testApplicationDTO);
            });

            // Verify exception details
            assertEquals("Application not found with ID: " + testId, exception.getMessage());

            // Verify interactions
            verify(applicationRepository).findById(testId);
            verify(validationService).validateApplicationData(testApplicationDTO);
            verify(applicationRepository, never()).save(any(Application.class));
        }

        @Test
        @DisplayName("Should throw ValidationException when update validation fails")
        void shouldThrowValidationExceptionWhenUpdateValidationFails() {
            // Arrange
            when(validationService.validateApplicationData(any(ApplicationRequestDTO.class)))
                    .thenReturn(invalidValidationResult);

            // Act & Assert
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                applicationService.updateApplication(testId, testApplicationDTO);
            });

            // Verify exception details
            assertEquals("Invalid application data", exception.getMessage());
            assertEquals(2, exception.getErrors().size());

            // Verify interactions
            verify(validationService).validateApplicationData(testApplicationDTO);
            verify(applicationRepository, never()).findById(testId);
            verify(applicationRepository, never()).save(any(Application.class));
        }
    }
    
    @Nested
    @DisplayName("Status Update Tests")
    class StatusUpdateTests {
        
        @Test
        @DisplayName("Should update application status successfully")
        void shouldUpdateApplicationStatusSuccessfully() {
            // Arrange
            testApplication.setStatus(ApplicationStatus.NEW);
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
            when(notificationService.sendApplicationStatusNotification(any(Application.class), anyString(), anyString()))
                    .thenReturn(true);

            // Act
            Application result = applicationService.updateApplicationStatus(testId, ApplicationStatus.PROCESSING);

            // Assert
            assertNotNull(result);
            assertEquals(ApplicationStatus.PROCESSING, result.getStatus());

            // Verify interactions
            verify(applicationRepository).findById(testId);
            verify(applicationRepository).save(any(Application.class));
            verify(notificationService).sendApplicationStatusNotification(
                    any(Application.class), eq("NEW"), eq("PROCESSING"));
        }

        @Test
        @DisplayName("Should throw InvalidApplicationStateException for invalid status transition")
        void shouldThrowInvalidApplicationStateExceptionForInvalidStatusTransition() {
            // Arrange
            testApplication.setStatus(ApplicationStatus.COMPLETED);
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));

            // Act & Assert
            InvalidApplicationStateException exception = assertThrows(InvalidApplicationStateException.class, () -> {
                applicationService.updateApplicationStatus(testId, ApplicationStatus.PROCESSING);
            });

            // Verify exception details
            assertEquals("Invalid status transition from COMPLETED to PROCESSING", exception.getMessage());

            // Verify interactions
            verify(applicationRepository).findById(testId);
            verify(applicationRepository, never()).save(any(Application.class));
            verify(notificationService, never()).sendApplicationStatusNotification(any(Application.class), anyString(), anyString());
        }

        @Test
        @DisplayName("Should send specific notification for approved status")
        void shouldSendSpecificNotificationForApprovedStatus() {
            // Arrange
            testApplication.setStatus(ApplicationStatus.PROCESSING);
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
            when(notificationService.sendApplicationStatusNotification(any(Application.class), anyString(), anyString()))
                    .thenReturn(true);
            when(notificationService.sendApplicationApprovedNotification(any(Application.class)))
                    .thenReturn(true);

            // Act
            Application result = applicationService.updateApplicationStatus(testId, ApplicationStatus.APPROVED);

            // Assert
            assertNotNull(result);
            assertEquals(ApplicationStatus.APPROVED, result.getStatus());

            // Verify interactions
            verify(applicationRepository).findById(testId);
            verify(applicationRepository).save(any(Application.class));
            verify(notificationService).sendApplicationStatusNotification(
                    any(Application.class), eq("PROCESSING"), eq("APPROVED"));
            verify(notificationService).sendApplicationApprovedNotification(any(Application.class));
        }
        
        @Test
        @DisplayName("Should update application review status successfully")
        void shouldUpdateApplicationReviewStatusSuccessfully() {
            // Arrange
            testApplication.setReviewStatus(ReviewStatus.NOT_REVIEWED);
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
            when(notificationService.sendSystemEventNotification(any(EventType.class), anyMap()))
                    .thenReturn(true);

            // Act
            Application result = applicationService.updateApplicationReviewStatus(testId, ReviewStatus.IN_REVIEW);

            // Assert
            assertNotNull(result);
            assertEquals(ReviewStatus.IN_REVIEW, result.getReviewStatus());

            // Verify interactions
            verify(applicationRepository).findById(testId);
            verify(applicationRepository).save(any(Application.class));
            verify(notificationService).sendSystemEventNotification(eq(EventType.APPLICATION_UPDATED), anyMap());
        }

        @Test
        @DisplayName("Should throw InvalidApplicationStateException for invalid review status transition")
        void shouldThrowInvalidApplicationStateExceptionForInvalidReviewStatusTransition() {
            // Arrange
            testApplication.setReviewStatus(ReviewStatus.APPROVED);
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));

            // Act & Assert
            InvalidApplicationStateException exception = assertThrows(InvalidApplicationStateException.class, () -> {
                applicationService.updateApplicationReviewStatus(testId, ReviewStatus.NEEDS_INFORMATION);
            });

            // Verify exception details
            assertEquals("Invalid review status transition from APPROVED to NEEDS_INFORMATION", exception.getMessage());

            // Verify interactions
            verify(applicationRepository).findById(testId);
            verify(applicationRepository, never()).save(any(Application.class));
            verify(notificationService, never()).sendSystemEventNotification(any(EventType.class), anyMap());
        }
    }
    
    @Nested
    @DisplayName("Delete Application Tests")
    class DeleteApplicationTests {
        
        @Test
        @DisplayName("Should delete application successfully")
        void shouldDeleteApplicationSuccessfully() {
            // Arrange
            when(applicationRepository.existsById(testId)).thenReturn(true);
            doNothing().when(applicationRepository).deleteById(testId);

            // Act
            applicationService.deleteApplication(testId);

            // Verify interactions
            verify(applicationRepository).existsById(testId);
            verify(applicationRepository).deleteById(testId);
        }

        @Test
        @DisplayName("Should throw ApplicationNotFoundException when deleting non-existent application")
        void shouldThrowApplicationNotFoundExceptionWhenDeletingNonExistentApplication() {
            // Arrange
            when(applicationRepository.existsById(testId)).thenReturn(false);

            // Act & Assert
            ApplicationNotFoundException exception = assertThrows(ApplicationNotFoundException.class, () -> {
                applicationService.deleteApplication(testId);
            });

            // Verify exception details
            assertEquals("Application not found with ID: " + testId, exception.getMessage());

            // Verify interactions
            verify(applicationRepository).existsById(testId);
            verify(applicationRepository, never()).deleteById(any());
        }
    }
    
    @Nested
    @DisplayName("Document Management Tests")
    class DocumentManagementTests {
        
        @Test
        @DisplayName("Should add document to application successfully")
        void shouldAddDocumentToApplicationSuccessfully() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
            when(notificationService.sendDocumentUploadedNotification(any(Document.class), any(UUID.class)))
                    .thenReturn(true);
            doNothing().when(applicationService).evaluateApplicationStatus(testId);

            // Act
            Application result = applicationService.addDocumentToApplication(testId, testDocument);

            // Assert
            assertNotNull(result);
            verify(applicationRepository).findById(testId);
            verify(applicationRepository).save(any(Application.class));
            verify(notificationService).sendDocumentUploadedNotification(eq(testDocument), eq(testId));
        }
        
        @Test
        @DisplayName("Should retrieve application documents successfully")
        void shouldRetrieveApplicationDocumentsSuccessfully() {
            // Arrange
            List<Document> documents = Arrays.asList(testDocument);
            testApplication.setDocuments(documents);
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));

            // Act
            List<Document> result = applicationService.getApplicationDocuments(testId);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals(testDocument.getId(), result.get(0).getId());

            // Verify interactions
            verify(applicationRepository).findById(testId);
        }
        
        @Test
        @DisplayName("Should retrieve application documents by type successfully")
        void shouldRetrieveApplicationDocumentsByTypeSuccessfully() {
            // Arrange
            List<Document> documents = Arrays.asList(testDocument);
            testApplication.setDocuments(documents);
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));

            // Act
            List<Document> result = applicationService.getApplicationDocumentsByType(testId, DocumentType.BANK_STATEMENT);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals(DocumentType.BANK_STATEMENT, result.get(0).getType());

            // Verify interactions
            verify(applicationRepository).findById(testId);
        }
        
        @Test
        @DisplayName("Should process document successfully")
        void shouldProcessDocumentSuccessfully() {
            // Arrange
            UUID documentId = UUID.randomUUID();
            testDocument.setId(documentId);
            List<Document> documents = Arrays.asList(testDocument);
            testApplication.setDocuments(documents);
            
            Map<String, Object> extractedData = new HashMap<>();
            extractedData.put("accountNumber", "123456789");
            extractedData.put("balance", "5000.00");
            
            Map<String, Double> confidenceScores = new HashMap<>();
            confidenceScores.put("accountNumber", 0.95);
            confidenceScores.put("balance", 0.90);
            
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);
            when(validationService.validateExtractedDataWithConfidence(
                    any(DocumentType.class), anyMap(), anyMap()))
                    .thenReturn(validValidationResult);
            when(notificationService.sendDocumentProcessedNotification(
                    any(Document.class), any(UUID.class), anyMap()))
                    .thenReturn(true);
            doNothing().when(applicationService).evaluateApplicationStatus(testId);

            // Act
            Application result = applicationService.processDocument(testId, documentId, extractedData, confidenceScores);

            // Assert
            assertNotNull(result);
            verify(applicationRepository).findById(testId);
            verify(validationService).validateExtractedDataWithConfidence(
                    eq(DocumentType.BANK_STATEMENT), eq(extractedData), eq(confidenceScores));
            verify(applicationRepository).save(any(Application.class));
            verify(notificationService).sendDocumentProcessedNotification(
                    eq(testDocument), eq(testId), eq(extractedData));
        }
    }
    
    @Nested
    @DisplayName("Application Evaluation Tests")
    class ApplicationEvaluationTests {
        
        @Test
        @DisplayName("Should evaluate application status successfully")
        void shouldEvaluateApplicationStatusSuccessfully() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(validationService.evaluateApplicationCompleteness(any(Application.class)))
                    .thenReturn(validValidationResult);
            when(validationService.determineApplicationStatus(any(Application.class)))
                    .thenReturn(ApplicationStatus.PROCESSING);
            when(validationService.determineReviewStatus(any(Application.class)))
                    .thenReturn(ReviewStatus.IN_REVIEW);
            when(applicationRepository.save(any(Application.class))).thenReturn(testApplication);

            // Act
            Application result = applicationService.evaluateApplicationStatus(testId);

            // Assert
            assertNotNull(result);
            verify(applicationRepository).findById(testId);
            verify(validationService).evaluateApplicationCompleteness(testApplication);
            verify(validationService).determineApplicationStatus(testApplication);
            verify(validationService).determineReviewStatus(testApplication);
            verify(applicationRepository).save(any(Application.class));
        }
        
        @Test
        @DisplayName("Should validate application successfully")
        void shouldValidateApplicationSuccessfully() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            when(validationService.validateApplication(any(Application.class)))
                    .thenReturn(validValidationResult);

            // Act
            ValidationResult result = applicationService.validateApplication(testId);

            // Assert
            assertNotNull(result);
            assertTrue(result.isValid());
            verify(applicationRepository).findById(testId);
            verify(validationService).validateApplication(testApplication);
        }
        
        @Test
        @DisplayName("Should check if application has all required documents")
        void shouldCheckIfApplicationHasAllRequiredDocuments() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            // Mock the hasAllRequiredDocuments method to return true
            doReturn(true).when(testApplication).hasAllRequiredDocuments();

            // Act
            boolean result = applicationService.hasAllRequiredDocuments(testId);

            // Assert
            assertTrue(result);
            verify(applicationRepository).findById(testId);
        }
        
        @Test
        @DisplayName("Should calculate application processing time")
        void shouldCalculateApplicationProcessingTime() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            // Mock the getProcessingTimeMinutes method to return 3 minutes
            doReturn(3L).when(testApplication).getProcessingTimeMinutes();

            // Act
            long result = applicationService.getApplicationProcessingTime(testId);

            // Assert
            assertEquals(3L, result);
            verify(applicationRepository).findById(testId);
        }
        
        @Test
        @DisplayName("Should check if application was processed within target time")
        void shouldCheckIfApplicationWasProcessedWithinTargetTime() {
            // Arrange
            when(applicationRepository.findById(testId)).thenReturn(Optional.of(testApplication));
            // Mock the isProcessedWithinTargetTime method to return true
            doReturn(true).when(testApplication).isProcessedWithinTargetTime();

            // Act
            boolean result = applicationService.isApplicationProcessedWithinTargetTime(testId);

            // Assert
            assertTrue(result);
            verify(applicationRepository).findById(testId);
        }
    }
    
    @Nested
    @DisplayName("Application Statistics Tests")
    class ApplicationStatisticsTests {
        
        @Test
        @DisplayName("Should count applications by status")
        void shouldCountApplicationsByStatus() {
            // Arrange
            when(applicationRepository.countByStatus(ApplicationStatus.NEW)).thenReturn(5L);

            // Act
            long result = applicationService.countApplicationsByStatus(ApplicationStatus.NEW);

            // Assert
            assertEquals(5L, result);
            verify(applicationRepository).countByStatus(ApplicationStatus.NEW);
        }
        
        @Test
        @DisplayName("Should count applications by review status")
        void shouldCountApplicationsByReviewStatus() {
            // Arrange
            when(applicationRepository.countByReviewStatus(ReviewStatus.NOT_REVIEWED)).thenReturn(3L);

            // Act
            long result = applicationService.countApplicationsByReviewStatus(ReviewStatus.NOT_REVIEWED);

            // Assert
            assertEquals(3L, result);
            verify(applicationRepository).countByReviewStatus(ReviewStatus.NOT_REVIEWED);
        }
        
        @Test
        @DisplayName("Should calculate average processing time")
        void shouldCalculateAverageProcessingTime() {
            // Arrange
            when(applicationRepository.calculateAverageProcessingTimeMinutes()).thenReturn(4.5);

            // Act
            double result = applicationService.calculateAverageProcessingTime();

            // Assert
            assertEquals(4.5, result, 0.001);
            verify(applicationRepository).calculateAverageProcessingTimeMinutes();
        }
        
        @Test
        @DisplayName("Should calculate average processing time for date range")
        void shouldCalculateAverageProcessingTimeForDateRange() {
            // Arrange
            LocalDateTime startDate = LocalDateTime.now().minusDays(7);
            LocalDateTime endDate = LocalDateTime.now();
            when(applicationRepository.calculateAverageProcessingTimeMinutes(startDate, endDate)).thenReturn(3.2);

            // Act
            double result = applicationService.calculateAverageProcessingTime(startDate, endDate);

            // Assert
            assertEquals(3.2, result, 0.001);
            verify(applicationRepository).calculateAverageProcessingTimeMinutes(startDate, endDate);
        }
        
        @Test
        @DisplayName("Should retrieve applications requiring review")
        void shouldRetrieveApplicationsRequiringReview() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<Application> applications = Arrays.asList(testApplication);
            Page<Application> applicationPage = new PageImpl<>(applications, pageable, applications.size());
            
            when(applicationRepository.findApplicationsRequiringReview(pageable)).thenReturn(applicationPage);

            // Act
            Page<Application> result = applicationService.getApplicationsRequiringReview(pageable);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getTotalElements());
            verify(applicationRepository).findApplicationsRequiringReview(pageable);
        }
        
        @Test
        @DisplayName("Should retrieve active applications")
        void shouldRetrieveActiveApplications() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<Application> applications = Arrays.asList(testApplication);
            Page<Application> applicationPage = new PageImpl<>(applications, pageable, applications.size());
            
            when(applicationRepository.findActiveApplications(pageable)).thenReturn(applicationPage);

            // Act
            Page<Application> result = applicationService.getActiveApplications(pageable);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getTotalElements());
            verify(applicationRepository).findActiveApplications(pageable);
        }
        
        @Test
        @DisplayName("Should retrieve decided applications")
        void shouldRetrieveDecidedApplications() {
            // Arrange
            Pageable pageable = PageRequest.of(0, 10);
            List<Application> applications = Arrays.asList(testApplication);
            Page<Application> applicationPage = new PageImpl<>(applications, pageable, applications.size());
            
            when(applicationRepository.findDecidedApplications(pageable)).thenReturn(applicationPage);

            // Act
            Page<Application> result = applicationService.getDecidedApplications(pageable);

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getTotalElements());
            verify(applicationRepository).findDecidedApplications(pageable);
        }
    }
    
    @Nested
    @DisplayName("Batch Processing Tests")
    class BatchProcessingTests {
        
        @Test
        @DisplayName("Should process batch applications successfully")
        void shouldProcessBatchApplicationsSuccessfully() {
            // Arrange
            List<Long> applicationIds = Arrays.asList(1L, 2L, 3L);
            UUID id1 = UUID.randomUUID();
            UUID id2 = UUID.randomUUID();
            UUID id3 = UUID.randomUUID();
            
            Application app1 = new Application();
            app1.setId(id1);
            app1.setStatus(ApplicationStatus.NEW);
            
            Application app2 = new Application();
            app2.setId(id2);
            app2.setStatus(ApplicationStatus.PENDING);
            
            Application app3 = new Application();
            app3.setId(id3);
            app3.setStatus(ApplicationStatus.NEW);
            
            when(applicationRepository.findById(id1)).thenReturn(Optional.of(app1));
            when(applicationRepository.findById(id2)).thenReturn(Optional.of(app2));
            when(applicationRepository.findById(id3)).thenReturn(Optional.of(app3));
            
            // Mock successful processing for app1 and app3, but app2 fails
            doNothing().when(applicationService).processApplication(id1, null);
            doThrow(new RuntimeException("Processing failed")).when(applicationService).processApplication(id2, null);
            doNothing().when(applicationService).processApplication(id3, null);

            // Act
            int successCount = applicationService.processBatchApplications(Arrays.asList(id1, id2, id3));

            // Assert
            assertEquals(2, successCount);
            verify(applicationService).processApplication(id1, null);
            verify(applicationService).processApplication(id2, null);
            verify(applicationService).processApplication(id3, null);
        }
    }
}