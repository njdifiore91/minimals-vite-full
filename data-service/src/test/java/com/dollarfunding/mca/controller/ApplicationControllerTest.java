package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ApplicationNotFoundException;
import com.dollarfunding.mca.exception.InvalidApplicationStateException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.service.ApplicationService;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit and integration tests for the ApplicationController class.
 * 
 * These tests verify CRUD operations, role-based access control (Operations Staff and System Admin roles),
 * request validation, pagination, filtering, and error handling. Uses Spring's MockMvc to simulate
 * HTTP requests and verify responses without requiring a full HTTP server.
 */
@WebMvcTest(ApplicationController.class)
public class ApplicationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ApplicationService applicationService;

    private UUID testId;
    private ApplicationRequestDTO validRequestDTO;
    private ApplicationResponseDTO responseDTO;

    @BeforeEach
    void setUp() {
        // Initialize test data
        testId = UUID.randomUUID();
        
        // Create a valid request DTO
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 0.95);
        
        validRequestDTO = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .metadata(metadata)
                .build();
        
        // Create a response DTO
        responseDTO = new ApplicationResponseDTO.Builder()
                .withId(testId)
                .withStatus(ApplicationStatus.NEW.name())
                .withReviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .withMetadata(metadata)
                .withCreatedAt(LocalDateTime.now())
                .withUpdatedAt(LocalDateTime.now())
                .withProcessingTimeMinutes(0L)
                .withProcessedWithinTargetTime(true)
                .withHasAllRequiredDocuments(false)
                .withIsCompleted(false)
                .withIsActive(true)
                .withIsDecided(false)
                .withRequiresReview(true)
                .build();
    }

    @Test
    @DisplayName("Create application - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void createApplication_Success() throws Exception {
        // Arrange
        when(applicationService.createApplication(any(ApplicationRequestDTO.class)))
                .thenReturn(responseDTO);

        // Act & Assert
        mockMvc.perform(post("/api/v1/applications")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(validRequestDTO)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id", is(testId.toString())))
                .andExpect(jsonPath("$.status", is(ApplicationStatus.NEW.name())))
                .andExpect(jsonPath("$.review_status", is(ReviewStatus.NOT_REVIEWED.name())))
                .andExpect(jsonPath("$.metadata.source", is("email")))
                .andExpect(jsonPath("$.metadata.confidence", is(0.95)));

        // Verify
        verify(applicationService, times(1)).createApplication(any(ApplicationRequestDTO.class));
    }

    @Test
    @DisplayName("Create application - validation error")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void createApplication_ValidationError() throws Exception {
        // Arrange
        String errorMessage = "Application status is required";
        when(applicationService.createApplication(any(ApplicationRequestDTO.class)))
                .thenThrow(new ValidationException(errorMessage));

        // Act & Assert
        mockMvc.perform(post("/api/v1/applications")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(validRequestDTO)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message", containsString(errorMessage)));

        // Verify
        verify(applicationService, times(1)).createApplication(any(ApplicationRequestDTO.class));
    }

    @Test
    @DisplayName("Create application - unauthorized")
    void createApplication_Unauthorized() throws Exception {
        // Act & Assert - No user role provided
        mockMvc.perform(post("/api/v1/applications")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(validRequestDTO)))
                .andExpect(status().isUnauthorized());

        // Verify
        verify(applicationService, never()).createApplication(any(ApplicationRequestDTO.class));
    }

    @Test
    @DisplayName("Get application by ID - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void getApplicationById_Success() throws Exception {
        // Arrange
        when(applicationService.getApplicationById(any(UUID.class)))
                .thenReturn(responseDTO);

        // Act & Assert
        mockMvc.perform(get("/api/v1/applications/{id}", testId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(testId.toString())))
                .andExpect(jsonPath("$.status", is(ApplicationStatus.NEW.name())))
                .andExpect(jsonPath("$.review_status", is(ReviewStatus.NOT_REVIEWED.name())));

        // Verify
        verify(applicationService, times(1)).getApplicationById(eq(testId));
    }

    @Test
    @DisplayName("Get application by ID - not found")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void getApplicationById_NotFound() throws Exception {
        // Arrange
        when(applicationService.getApplicationById(any(UUID.class)))
                .thenThrow(new ApplicationNotFoundException("Application not found with ID: " + testId));

        // Act & Assert
        mockMvc.perform(get("/api/v1/applications/{id}", testId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message", containsString("Application not found")));

        // Verify
        verify(applicationService, times(1)).getApplicationById(eq(testId));
    }

    @Test
    @DisplayName("Update application - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void updateApplication_Success() throws Exception {
        // Arrange
        ApplicationResponseDTO updatedResponseDTO = new ApplicationResponseDTO.Builder()
                .withId(testId)
                .withStatus(ApplicationStatus.PENDING.name())
                .withReviewStatus(ReviewStatus.IN_REVIEW.name())
                .withCreatedAt(LocalDateTime.now())
                .withUpdatedAt(LocalDateTime.now())
                .build();

        when(applicationService.updateApplication(any(UUID.class), any(ApplicationRequestDTO.class)))
                .thenReturn(updatedResponseDTO);

        // Update request DTO
        ApplicationRequestDTO updateRequestDTO = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.PENDING.name())
                .reviewStatus(ReviewStatus.IN_REVIEW.name())
                .build();

        // Act & Assert
        mockMvc.perform(put("/api/v1/applications/{id}", testId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequestDTO)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(testId.toString())))
                .andExpect(jsonPath("$.status", is(ApplicationStatus.PENDING.name())))
                .andExpect(jsonPath("$.review_status", is(ReviewStatus.IN_REVIEW.name())));

        // Verify
        verify(applicationService, times(1)).updateApplication(eq(testId), any(ApplicationRequestDTO.class));
    }

    @Test
    @DisplayName("Update application - invalid state")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void updateApplication_InvalidState() throws Exception {
        // Arrange
        String errorMessage = "Invalid status transition from NEW to COMPLETED";
        when(applicationService.updateApplication(any(UUID.class), any(ApplicationRequestDTO.class)))
                .thenThrow(new InvalidApplicationStateException(errorMessage));

        // Update request DTO with invalid state transition
        ApplicationRequestDTO updateRequestDTO = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.COMPLETED.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();

        // Act & Assert
        mockMvc.perform(put("/api/v1/applications/{id}", testId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequestDTO)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message", containsString(errorMessage)));

        // Verify
        verify(applicationService, times(1)).updateApplication(eq(testId), any(ApplicationRequestDTO.class));
    }

    @Test
    @DisplayName("Delete application - success")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void deleteApplication_Success() throws Exception {
        // Arrange
        doNothing().when(applicationService).deleteApplication(any(UUID.class));

        // Act & Assert
        mockMvc.perform(delete("/api/v1/applications/{id}", testId))
                .andExpect(status().isNoContent());

        // Verify
        verify(applicationService, times(1)).deleteApplication(eq(testId));
    }

    @Test
    @DisplayName("Delete application - forbidden for operations staff")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void deleteApplication_Forbidden() throws Exception {
        // Act & Assert - Operations staff should not be able to delete
        mockMvc.perform(delete("/api/v1/applications/{id}", testId))
                .andExpect(status().isForbidden());

        // Verify
        verify(applicationService, never()).deleteApplication(any(UUID.class));
    }

    @Test
    @DisplayName("Get applications with filtering - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void getApplications_WithFiltering_Success() throws Exception {
        // Arrange
        List<ApplicationResponseDTO> applications = new ArrayList<>();
        applications.add(responseDTO);
        Page<ApplicationResponseDTO> page = new PageImpl<>(applications);

        when(applicationService.getApplications(any(ApplicationFilterDTO.class), any(Pageable.class)))
                .thenReturn(page);

        // Act & Assert
        mockMvc.perform(get("/api/v1/applications")
                .param("status", ApplicationStatus.NEW.name())
                .param("reviewStatus", ReviewStatus.NOT_REVIEWED.name())
                .param("merchantName", "Test Merchant")
                .param("startDate", LocalDate.now().minusDays(7).toString())
                .param("endDate", LocalDate.now().toString())
                .param("searchTerm", "test")
                .param("page", "0")
                .param("size", "10")
                .param("sortBy", "createdAt")
                .param("sortDirection", "desc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].id", is(testId.toString())));

        // Verify
        verify(applicationService, times(1)).getApplications(any(ApplicationFilterDTO.class), any(Pageable.class));
    }

    @Test
    @DisplayName("Update application status - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void updateApplicationStatus_Success() throws Exception {
        // Arrange
        ApplicationResponseDTO updatedResponseDTO = new ApplicationResponseDTO.Builder()
                .withId(testId)
                .withStatus(ApplicationStatus.PROCESSING.name())
                .withReviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .withCreatedAt(LocalDateTime.now())
                .withUpdatedAt(LocalDateTime.now())
                .build();

        when(applicationService.updateApplicationStatus(any(UUID.class), any(ApplicationStatus.class)))
                .thenReturn(updatedResponseDTO);

        // Act & Assert
        mockMvc.perform(patch("/api/v1/applications/{id}/status", testId)
                .param("status", ApplicationStatus.PROCESSING.name()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(testId.toString())))
                .andExpect(jsonPath("$.status", is(ApplicationStatus.PROCESSING.name())));

        // Verify
        verify(applicationService, times(1)).updateApplicationStatus(eq(testId), eq(ApplicationStatus.PROCESSING));
    }

    @Test
    @DisplayName("Update application review status - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void updateApplicationReviewStatus_Success() throws Exception {
        // Arrange
        ApplicationResponseDTO updatedResponseDTO = new ApplicationResponseDTO.Builder()
                .withId(testId)
                .withStatus(ApplicationStatus.NEW.name())
                .withReviewStatus(ReviewStatus.IN_REVIEW.name())
                .withCreatedAt(LocalDateTime.now())
                .withUpdatedAt(LocalDateTime.now())
                .build();

        when(applicationService.updateApplicationReviewStatus(any(UUID.class), any(ReviewStatus.class)))
                .thenReturn(updatedResponseDTO);

        // Act & Assert
        mockMvc.perform(patch("/api/v1/applications/{id}/review-status", testId)
                .param("reviewStatus", ReviewStatus.IN_REVIEW.name()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(testId.toString())))
                .andExpect(jsonPath("$.review_status", is(ReviewStatus.IN_REVIEW.name())));

        // Verify
        verify(applicationService, times(1)).updateApplicationReviewStatus(eq(testId), eq(ReviewStatus.IN_REVIEW));
    }

    @Test
    @DisplayName("Process application - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void processApplication_Success() throws Exception {
        // Arrange
        ApplicationResponseDTO processedResponseDTO = new ApplicationResponseDTO.Builder()
                .withId(testId)
                .withStatus(ApplicationStatus.PROCESSING.name())
                .withReviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .withCreatedAt(LocalDateTime.now())
                .withUpdatedAt(LocalDateTime.now())
                .withProcessingTimeMinutes(2L)
                .withProcessedWithinTargetTime(true)
                .build();

        when(applicationService.processApplication(any(UUID.class)))
                .thenReturn(processedResponseDTO);

        // Act & Assert
        mockMvc.perform(post("/api/v1/applications/{id}/process", testId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(testId.toString())))
                .andExpect(jsonPath("$.status", is(ApplicationStatus.PROCESSING.name())))
                .andExpect(jsonPath("$.processing_time_minutes", is(2)));

        // Verify
        verify(applicationService, times(1)).processApplication(eq(testId));
    }

    @Test
    @DisplayName("Process application - invalid state")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void processApplication_InvalidState() throws Exception {
        // Arrange
        String errorMessage = "Application cannot be processed in its current state: COMPLETED";
        when(applicationService.processApplication(any(UUID.class)))
                .thenThrow(new InvalidApplicationStateException(errorMessage));

        // Act & Assert
        mockMvc.perform(post("/api/v1/applications/{id}/process", testId))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message", containsString(errorMessage)));

        // Verify
        verify(applicationService, times(1)).processApplication(eq(testId));
    }

    @Test
    @DisplayName("Check if application is complete - success")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void isApplicationComplete_Success() throws Exception {
        // Arrange
        when(applicationService.isApplicationComplete(any(UUID.class)))
                .thenReturn(true);

        // Act & Assert
        mockMvc.perform(get("/api/v1/applications/{id}/is-complete", testId))
                .andExpect(status().isOk())
                .andExpect(content().string("true"));

        // Verify
        verify(applicationService, times(1)).isApplicationComplete(eq(testId));
    }

    @Test
    @DisplayName("Check if application is complete - not found")
    @WithMockUser(roles = {"OPERATIONS_STAFF"})
    void isApplicationComplete_NotFound() throws Exception {
        // Arrange
        when(applicationService.isApplicationComplete(any(UUID.class)))
                .thenThrow(new ApplicationNotFoundException("Application not found with ID: " + testId));

        // Act & Assert
        mockMvc.perform(get("/api/v1/applications/{id}/is-complete", testId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message", containsString("Application not found")));

        // Verify
        verify(applicationService, times(1)).isApplicationComplete(eq(testId));
    }

    @Test
    @DisplayName("System admin can access all endpoints")
    @WithMockUser(roles = {"SYSTEM_ADMIN"})
    void systemAdmin_CanAccessAllEndpoints() throws Exception {
        // Arrange
        when(applicationService.getApplicationById(any(UUID.class)))
                .thenReturn(responseDTO);
        when(applicationService.createApplication(any(ApplicationRequestDTO.class)))
                .thenReturn(responseDTO);
        when(applicationService.updateApplication(any(UUID.class), any(ApplicationRequestDTO.class)))
                .thenReturn(responseDTO);
        doNothing().when(applicationService).deleteApplication(any(UUID.class));

        // Act & Assert - Get
        mockMvc.perform(get("/api/v1/applications/{id}", testId))
                .andExpect(status().isOk());

        // Act & Assert - Create
        mockMvc.perform(post("/api/v1/applications")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(validRequestDTO)))
                .andExpect(status().isCreated());

        // Act & Assert - Update
        mockMvc.perform(put("/api/v1/applications/{id}", testId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(validRequestDTO)))
                .andExpect(status().isOk());

        // Act & Assert - Delete
        mockMvc.perform(delete("/api/v1/applications/{id}", testId))
                .andExpect(status().isNoContent());

        // Verify
        verify(applicationService, times(1)).getApplicationById(any(UUID.class));
        verify(applicationService, times(1)).createApplication(any(ApplicationRequestDTO.class));
        verify(applicationService, times(1)).updateApplication(any(UUID.class), any(ApplicationRequestDTO.class));
        verify(applicationService, times(1)).deleteApplication(any(UUID.class));
    }
}