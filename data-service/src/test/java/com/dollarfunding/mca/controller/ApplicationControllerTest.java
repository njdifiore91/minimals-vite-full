package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.ApplicationDto;
import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.security.RoleConstants;
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
import org.springframework.test.web.servlet.ResultActions;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.hasSize;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultHandlers.print;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Unit and integration tests for the ApplicationController class.
 * <p>
 * This test class verifies the functionality of the ApplicationController, which manages
 * MCA application data through the /api/v1/applications endpoint. It tests CRUD operations,
 * role-based access control, pagination, filtering, and error handling.
 * </p>
 */
@WebMvcTest(ApplicationController.class)
public class ApplicationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ApplicationService applicationService;

    private ApplicationDto applicationDto;
    private ApplicationRequestDTO applicationRequestDTO;
    private ApplicationResponseDTO applicationResponseDTO;
    private Application application;
    private UUID applicationId;

    @BeforeEach
    void setUp() {
        // Initialize test data
        applicationId = UUID.randomUUID();
        
        // Setup ApplicationDto
        applicationDto = new ApplicationDto();
        applicationDto.setId(1L);
        applicationDto.setStatus("PENDING");
        applicationDto.setReviewStatus("NOT_REVIEWED");
        applicationDto.setMerchantName("Test Merchant Inc.");
        applicationDto.setMerchantDba("Test Merchant");
        applicationDto.setEin("12-3456789");
        applicationDto.setCreatedAt(LocalDateTime.now());
        applicationDto.setUpdatedAt(LocalDateTime.now());
        
        // Setup ApplicationRequestDTO
        applicationRequestDTO = new ApplicationRequestDTO();
        applicationRequestDTO.setStatus(ApplicationStatus.PENDING);
        applicationRequestDTO.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("requestedAmount", 50000);
        metadata.put("industry", "Retail");
        applicationRequestDTO.setMetadata(metadata);
        
        // Setup Application entity
        application = new Application();
        application.setId(applicationId);
        application.setStatus(ApplicationStatus.PENDING);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        application.setMetadata(metadata);
        application.setCreatedAt(LocalDateTime.now());
        application.setUpdatedAt(LocalDateTime.now());
        
        // Setup ApplicationResponseDTO
        applicationResponseDTO = new ApplicationResponseDTO();
        applicationResponseDTO.setId(applicationId);
        applicationResponseDTO.setStatus(ApplicationStatus.PENDING);
        applicationResponseDTO.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        applicationResponseDTO.setMetadata(metadata);
        applicationResponseDTO.setCreatedAt(LocalDateTime.now());
        applicationResponseDTO.setUpdatedAt(LocalDateTime.now());
    }

    @Test
    @DisplayName("Test get all applications - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testGetAllApplications() throws Exception {
        // Given
        List<ApplicationResponseDTO> applications = Arrays.asList(
                applicationResponseDTO,
                new ApplicationResponseDTO()
        );
        
        Page<ApplicationResponseDTO> page = new PageImpl<>(applications);
        PageResponseDTO<ApplicationResponseDTO> pageResponse = PageResponseDTO.fromPage(page, "/api/v1/applications");
        
        given(applicationService.findAll(any(Pageable.class))).willReturn(pageResponse);

        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(2)))
                .andExpect(jsonPath("$.page_metadata.total_elements", is(2)))
                .andDo(print());
    }

    @Test
    @DisplayName("Test get application by ID - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testGetApplicationById() throws Exception {
        // Given
        given(applicationService.findById(applicationId)).willReturn(Optional.of(applicationResponseDTO));

        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications/{id}", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(applicationId.toString())))
                .andExpect(jsonPath("$.status", is("PENDING")))
                .andExpect(jsonPath("$.review_status", is("NOT_REVIEWED")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test get application by ID - not found")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testGetApplicationByIdNotFound() throws Exception {
        // Given
        given(applicationService.findById(applicationId))
                .willThrow(new ResourceNotFoundException("Application not found with id: " + applicationId));

        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications/{id}", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message", is("Application not found with id: " + applicationId)))
                .andDo(print());
    }

    @Test
    @DisplayName("Test create application - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testCreateApplication() throws Exception {
        // Given
        given(applicationService.create(any(ApplicationRequestDTO.class))).willReturn(applicationResponseDTO);

        // When
        ResultActions response = mockMvc.perform(post("/api/v1/applications")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationRequestDTO)));

        // Then
        response.andExpect(status().isCreated())
                .andExpect(jsonPath("$.id", is(applicationId.toString())))
                .andExpect(jsonPath("$.status", is("PENDING")))
                .andExpect(jsonPath("$.review_status", is("NOT_REVIEWED")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test create application - validation error")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testCreateApplicationValidationError() throws Exception {
        // Given
        ApplicationRequestDTO invalidRequest = new ApplicationRequestDTO();
        // Status is required but not set

        // When
        ResultActions response = mockMvc.perform(post("/api/v1/applications")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalidRequest)));

        // Then
        response.andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message", is("Validation failed")))
                .andExpect(jsonPath("$.validationErrors.status", is("Application status is required")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test update application - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testUpdateApplication() throws Exception {
        // Given
        applicationRequestDTO.setStatus(ApplicationStatus.PROCESSING);
        applicationResponseDTO.setStatus(ApplicationStatus.PROCESSING);
        
        given(applicationService.update(eq(applicationId), any(ApplicationRequestDTO.class)))
                .willReturn(applicationResponseDTO);

        // When
        ResultActions response = mockMvc.perform(put("/api/v1/applications/{id}", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationRequestDTO)));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(applicationId.toString())))
                .andExpect(jsonPath("$.status", is("PROCESSING")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test update application - not found")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testUpdateApplicationNotFound() throws Exception {
        // Given
        given(applicationService.update(eq(applicationId), any(ApplicationRequestDTO.class)))
                .willThrow(new ResourceNotFoundException("Application not found with id: " + applicationId));

        // When
        ResultActions response = mockMvc.perform(put("/api/v1/applications/{id}", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(applicationRequestDTO)));

        // Then
        response.andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message", is("Application not found with id: " + applicationId)))
                .andDo(print());
    }

    @Test
    @DisplayName("Test delete application - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_SYSTEM_ADMIN})
    void testDeleteApplication() throws Exception {
        // Given
        doNothing().when(applicationService).delete(applicationId);

        // When
        ResultActions response = mockMvc.perform(delete("/api/v1/applications/{id}", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andDo(print());
        
        verify(applicationService, times(1)).delete(applicationId);
    }

    @Test
    @DisplayName("Test delete application - not found")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_SYSTEM_ADMIN})
    void testDeleteApplicationNotFound() throws Exception {
        // Given
        doThrow(new ResourceNotFoundException("Application not found with id: " + applicationId))
                .when(applicationService).delete(applicationId);

        // When
        ResultActions response = mockMvc.perform(delete("/api/v1/applications/{id}", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message", is("Application not found with id: " + applicationId)))
                .andDo(print());
    }

    @Test
    @DisplayName("Test delete application - access denied for Operations Staff")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testDeleteApplicationAccessDenied() throws Exception {
        // When
        ResultActions response = mockMvc.perform(delete("/api/v1/applications/{id}", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isForbidden())
                .andDo(print());
    }

    @Test
    @DisplayName("Test filter applications - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testFilterApplications() throws Exception {
        // Given
        ApplicationFilterDTO filterDTO = ApplicationFilterDTO.builder()
                .status(ApplicationStatus.PENDING)
                .merchantName("Test Merchant")
                .createdFrom(LocalDateTime.now().minusDays(30).toLocalDate())
                .page(0)
                .size(10)
                .build();
        
        List<ApplicationResponseDTO> applications = Arrays.asList(applicationResponseDTO);
        Page<ApplicationResponseDTO> page = new PageImpl<>(applications);
        PageResponseDTO<ApplicationResponseDTO> pageResponse = PageResponseDTO.fromPage(page, "/api/v1/applications/filter");
        
        given(applicationService.filter(any(ApplicationFilterDTO.class))).willReturn(pageResponse);

        // When
        ResultActions response = mockMvc.perform(post("/api/v1/applications/filter")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(filterDTO)));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.page_metadata.total_elements", is(1)))
                .andExpect(jsonPath("$.content[0].id", is(applicationId.toString())))
                .andDo(print());
    }

    @Test
    @DisplayName("Test update application status - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testUpdateApplicationStatus() throws Exception {
        // Given
        ApplicationStatus newStatus = ApplicationStatus.APPROVED;
        applicationResponseDTO.setStatus(newStatus);
        
        given(applicationService.updateStatus(eq(applicationId), eq(newStatus)))
                .willReturn(applicationResponseDTO);

        // When
        ResultActions response = mockMvc.perform(patch("/api/v1/applications/{id}/status", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of("status", newStatus))));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(applicationId.toString())))
                .andExpect(jsonPath("$.status", is("APPROVED")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test update application review status - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testUpdateApplicationReviewStatus() throws Exception {
        // Given
        ReviewStatus newReviewStatus = ReviewStatus.IN_REVIEW;
        applicationResponseDTO.setReviewStatus(newReviewStatus);
        
        given(applicationService.updateReviewStatus(eq(applicationId), eq(newReviewStatus)))
                .willReturn(applicationResponseDTO);

        // When
        ResultActions response = mockMvc.perform(patch("/api/v1/applications/{id}/review-status", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of("reviewStatus", newReviewStatus))));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(applicationId.toString())))
                .andExpect(jsonPath("$.review_status", is("IN_REVIEW")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test process application - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testProcessApplication() throws Exception {
        // Given
        applicationResponseDTO.setStatus(ApplicationStatus.PROCESSING);
        
        given(applicationService.processApplication(applicationId))
                .willReturn(applicationResponseDTO);

        // When
        ResultActions response = mockMvc.perform(post("/api/v1/applications/{id}/process", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(applicationId.toString())))
                .andExpect(jsonPath("$.status", is("PROCESSING")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test generate application reports - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testGenerateReports() throws Exception {
        // Given
        given(applicationService.generateReports()).willReturn("Reports generated successfully");

        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications/reports")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$", is("Reports generated successfully")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test get applications without authentication - unauthorized")
    void testGetApplicationsUnauthorized() throws Exception {
        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isUnauthorized())
                .andDo(print());
    }

    @Test
    @DisplayName("Test get application statistics - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testGetApplicationStatistics() throws Exception {
        // Given
        Map<String, Object> statistics = new HashMap<>();
        statistics.put("totalApplications", 100);
        statistics.put("pendingApplications", 25);
        statistics.put("approvedApplications", 50);
        statistics.put("rejectedApplications", 25);
        statistics.put("averageProcessingTime", "2.5 days");
        
        given(applicationService.getStatistics()).willReturn(statistics);

        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications/statistics")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.totalApplications", is(100)))
                .andExpect(jsonPath("$.pendingApplications", is(25)))
                .andExpect(jsonPath("$.approvedApplications", is(50)))
                .andExpect(jsonPath("$.rejectedApplications", is(25)))
                .andExpect(jsonPath("$.averageProcessingTime", is("2.5 days")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test assign application to user - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testAssignApplicationToUser() throws Exception {
        // Given
        String userId = "user123";
        Map<String, Object> metadata = new HashMap<>(applicationResponseDTO.getMetadata());
        metadata.put("assignedTo", userId);
        applicationResponseDTO.setMetadata(metadata);
        
        given(applicationService.assignToUser(eq(applicationId), eq(userId)))
                .willReturn(applicationResponseDTO);

        // When
        ResultActions response = mockMvc.perform(patch("/api/v1/applications/{id}/assign", applicationId)
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of("userId", userId))));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(applicationId.toString())))
                .andExpect(jsonPath("$.metadata.assignedTo", is(userId)))
                .andDo(print());
    }

    @Test
    @DisplayName("Test get applications by status - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testGetApplicationsByStatus() throws Exception {
        // Given
        List<ApplicationResponseDTO> applications = Arrays.asList(applicationResponseDTO);
        Page<ApplicationResponseDTO> page = new PageImpl<>(applications);
        PageResponseDTO<ApplicationResponseDTO> pageResponse = PageResponseDTO.fromPage(page, "/api/v1/applications/status/PENDING");
        
        given(applicationService.findByStatus(eq(ApplicationStatus.PENDING), any(Pageable.class)))
                .willReturn(pageResponse);

        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications/status/{status}", "PENDING")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].status", is("PENDING")))
                .andDo(print());
    }

    @Test
    @DisplayName("Test get applications by review status - success")
    @WithMockUser(username = "testuser", authorities = {RoleConstants.ROLE_OPERATIONS_STAFF})
    void testGetApplicationsByReviewStatus() throws Exception {
        // Given
        List<ApplicationResponseDTO> applications = Arrays.asList(applicationResponseDTO);
        Page<ApplicationResponseDTO> page = new PageImpl<>(applications);
        PageResponseDTO<ApplicationResponseDTO> pageResponse = PageResponseDTO.fromPage(page, "/api/v1/applications/review-status/NOT_REVIEWED");
        
        given(applicationService.findByReviewStatus(eq(ReviewStatus.NOT_REVIEWED), any(Pageable.class)))
                .willReturn(pageResponse);

        // When
        ResultActions response = mockMvc.perform(get("/api/v1/applications/review-status/{status}", "NOT_REVIEWED")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON));

        // Then
        response.andExpect(status().isOk())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].review_status", is("NOT_REVIEWED")))
                .andDo(print());
    }
}