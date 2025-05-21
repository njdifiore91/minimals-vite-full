package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.ApplicationFilterDTO;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.ApplicationResponseDTO;
import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.service.ApplicationService;
import com.dollarfunding.mca.service.ValidationService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import javax.validation.Valid;
import java.net.URI;
import java.util.List;
import java.util.Map;

/**
 * REST controller that manages MCA application data through the /api/v1/applications endpoint.
 * It provides CRUD operations for applications with role-based access control, allowing
 * Operations Staff to read all applications and modify application data, while System Admins
 * have full access. The controller validates incoming requests, delegates business logic to
 * the ApplicationService, and formats responses according to API contracts.
 */
@RestController
@RequestMapping("/api/v1/applications")
@Validated
@Tag(name = "Applications", description = "API for MCA application management operations")
public class ApplicationController {

    private static final Logger logger = LoggerFactory.getLogger(ApplicationController.class);

    private final ApplicationService applicationService;
    private final ValidationService validationService;

    @Autowired
    public ApplicationController(ApplicationService applicationService, ValidationService validationService) {
        this.applicationService = applicationService;
        this.validationService = validationService;
    }

    /**
     * Create a new MCA application
     * 
     * @param applicationRequestDTO Application data
     * @return ResponseEntity containing the created application
     */
    @PostMapping
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Create a new application", description = "Creates a new MCA application with the provided data")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Application created successfully",
                    content = @Content(schema = @Schema(implementation = ApplicationResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid request data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<ApplicationResponseDTO> createApplication(
            @Parameter(description = "Application data", required = true)
            @Valid @RequestBody ApplicationRequestDTO applicationRequestDTO) {
        
        logger.info("Creating new MCA application");
        
        // Validate application data
        validationService.validateApplicationData(applicationRequestDTO);
        
        // Create application
        ApplicationResponseDTO createdApplication = applicationService.createApplication(applicationRequestDTO);
        
        // Create URI for the new resource
        URI location = ServletUriComponentsBuilder
                .fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(createdApplication.getId())
                .toUri();
        
        return ResponseEntity.created(location).body(createdApplication);
    }

    /**
     * Get application by ID
     * 
     * @param id Application ID
     * @return ResponseEntity containing the application data
     */
    @GetMapping("/{id}")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Get application by ID", description = "Retrieves application data by its ID")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Application found",
                    content = @Content(schema = @Schema(implementation = ApplicationResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Application not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<ApplicationResponseDTO> getApplicationById(
            @Parameter(description = "Application ID", required = true)
            @PathVariable("id") Long id) {
        
        logger.info("Retrieving application with ID: {}", id);
        ApplicationResponseDTO application = applicationService.getApplicationById(id);
        return ResponseEntity.ok(application);
    }

    /**
     * Get applications with filtering and pagination
     * 
     * @param filterDTO Filter criteria
     * @return ResponseEntity containing a page of applications
     */
    @GetMapping
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Get applications", description = "Retrieves applications with filtering and pagination")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Applications retrieved successfully",
                    content = @Content(schema = @Schema(implementation = PageResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid filter criteria",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<PageResponseDTO<ApplicationResponseDTO>> getApplications(
            @Parameter(description = "Filter criteria")
            @Valid ApplicationFilterDTO filterDTO) {
        
        logger.info("Retrieving applications with filters: {}", filterDTO);
        Page<ApplicationResponseDTO> applications = applicationService.getApplications(filterDTO);
        PageResponseDTO<ApplicationResponseDTO> response = new PageResponseDTO<>(applications);
        return ResponseEntity.ok(response);
    }

    /**
     * Update application
     * 
     * @param id Application ID
     * @param applicationRequestDTO Updated application data
     * @return ResponseEntity containing the updated application
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Update application", description = "Updates an existing application with the provided data")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Application updated successfully",
                    content = @Content(schema = @Schema(implementation = ApplicationResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid request data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Application not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<ApplicationResponseDTO> updateApplication(
            @Parameter(description = "Application ID", required = true)
            @PathVariable("id") Long id,
            @Parameter(description = "Updated application data", required = true)
            @Valid @RequestBody ApplicationRequestDTO applicationRequestDTO) {
        
        logger.info("Updating application with ID: {}", id);
        
        // Validate application data
        validationService.validateApplicationData(applicationRequestDTO);
        
        // Update application
        ApplicationResponseDTO updatedApplication = applicationService.updateApplication(id, applicationRequestDTO);
        return ResponseEntity.ok(updatedApplication);
    }

    /**
     * Delete application
     * 
     * @param id Application ID
     * @return ResponseEntity with no content
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "Delete application", description = "Deletes an application by its ID (System Admin only)")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "204", description = "Application deleted successfully"),
        @ApiResponse(responseCode = "404", description = "Application not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<Void> deleteApplication(
            @Parameter(description = "Application ID", required = true)
            @PathVariable("id") Long id) {
        
        logger.info("Deleting application with ID: {}", id);
        applicationService.deleteApplication(id);
        return ResponseEntity.noContent().build();
    }

    /**
     * Update application status
     * 
     * @param id Application ID
     * @param status New application status
     * @return ResponseEntity containing the updated application
     */
    @PatchMapping("/{id}/status")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Update application status", description = "Updates the status of an existing application")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Application status updated successfully",
                    content = @Content(schema = @Schema(implementation = ApplicationResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid status transition",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Application not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<ApplicationResponseDTO> updateApplicationStatus(
            @Parameter(description = "Application ID", required = true)
            @PathVariable("id") Long id,
            @Parameter(description = "New application status", required = true)
            @RequestParam("status") ApplicationStatus status) {
        
        logger.info("Updating status for application ID: {} to {}", id, status);
        ApplicationResponseDTO updatedApplication = applicationService.updateApplicationStatus(id, status);
        return ResponseEntity.ok(updatedApplication);
    }

    /**
     * Update application review status
     * 
     * @param id Application ID
     * @param reviewStatus New review status
     * @return ResponseEntity containing the updated application
     */
    @PatchMapping("/{id}/review-status")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Update application review status", description = "Updates the review status of an existing application")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Application review status updated successfully",
                    content = @Content(schema = @Schema(implementation = ApplicationResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid review status transition",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Application not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<ApplicationResponseDTO> updateApplicationReviewStatus(
            @Parameter(description = "Application ID", required = true)
            @PathVariable("id") Long id,
            @Parameter(description = "New review status", required = true)
            @RequestParam("reviewStatus") ReviewStatus reviewStatus) {
        
        logger.info("Updating review status for application ID: {} to {}", id, reviewStatus);
        ApplicationResponseDTO updatedApplication = applicationService.updateApplicationReviewStatus(id, reviewStatus);
        return ResponseEntity.ok(updatedApplication);
    }

    /**
     * Process application
     * 
     * @param id Application ID
     * @return ResponseEntity containing the processed application
     */
    @PostMapping("/{id}/process")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Process application", description = "Triggers processing for an existing application")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Application processed successfully",
                    content = @Content(schema = @Schema(implementation = ApplicationResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Application cannot be processed",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Application not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<ApplicationResponseDTO> processApplication(
            @Parameter(description = "Application ID", required = true)
            @PathVariable("id") Long id) {
        
        logger.info("Processing application with ID: {}", id);
        ApplicationResponseDTO processedApplication = applicationService.processApplication(id);
        return ResponseEntity.ok(processedApplication);
    }

    /**
     * Get application statuses
     * 
     * @return ResponseEntity containing a list of available application statuses
     */
    @GetMapping("/statuses")
    @Operation(summary = "Get application statuses", description = "Retrieves all available application statuses")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Application statuses retrieved successfully")
    })
    public ResponseEntity<List<Map<String, String>>> getApplicationStatuses() {
        logger.info("Retrieving all application statuses");
        List<Map<String, String>> applicationStatuses = applicationService.getApplicationStatuses();
        return ResponseEntity.ok(applicationStatuses);
    }

    /**
     * Get application review statuses
     * 
     * @return ResponseEntity containing a list of available review statuses
     */
    @GetMapping("/review-statuses")
    @Operation(summary = "Get application review statuses", description = "Retrieves all available application review statuses")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Application review statuses retrieved successfully")
    })
    public ResponseEntity<List<Map<String, String>>> getApplicationReviewStatuses() {
        logger.info("Retrieving all application review statuses");
        List<Map<String, String>> reviewStatuses = applicationService.getApplicationReviewStatuses();
        return ResponseEntity.ok(reviewStatuses);
    }
}