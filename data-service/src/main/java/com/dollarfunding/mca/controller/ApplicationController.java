package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.ApplicationDto;
import com.dollarfunding.mca.security.RoleConstants;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;
import java.util.List;

/**
 * REST controller for managing application data.
 * <p>
 * This controller provides endpoints for creating, retrieving, updating, and deleting
 * application data. It enforces role-based access control to ensure that only authorized
 * users can access the endpoints.
 * </p>
 */
@RestController
@RequestMapping("/api/v1/applications")
public class ApplicationController {

    /**
     * Retrieves all applications.
     * <p>
     * This endpoint is accessible to both Operations Staff and System Admin roles.
     * </p>
     *
     * @return A list of all applications
     */
    @GetMapping
    public ResponseEntity<List<ApplicationDto>> getAllApplications() {
        // Implementation would retrieve applications from the service
        return ResponseEntity.ok(List.of());
    }

    /**
     * Retrieves an application by ID.
     * <p>
     * This endpoint is accessible to both Operations Staff and System Admin roles.
     * </p>
     *
     * @param id The application ID
     * @return The application with the specified ID
     */
    @GetMapping("/{id}")
    public ResponseEntity<ApplicationDto> getApplicationById(@PathVariable Long id) {
        // Implementation would retrieve the application from the service
        return ResponseEntity.ok(new ApplicationDto());
    }

    /**
     * Creates a new application.
     * <p>
     * This endpoint is accessible to both Operations Staff and System Admin roles.
     * </p>
     *
     * @param applicationDto The application data to create
     * @return The created application
     */
    @PostMapping
    public ResponseEntity<ApplicationDto> createApplication(@Valid @RequestBody ApplicationDto applicationDto) {
        // Implementation would create the application using the service
        return ResponseEntity.status(HttpStatus.CREATED).body(applicationDto);
    }

    /**
     * Updates an existing application.
     * <p>
     * This endpoint is accessible to both Operations Staff and System Admin roles.
     * </p>
     *
     * @param id             The application ID
     * @param applicationDto The updated application data
     * @return The updated application
     */
    @PutMapping("/{id}")
    public ResponseEntity<ApplicationDto> updateApplication(@PathVariable Long id,
                                                          @Valid @RequestBody ApplicationDto applicationDto) {
        // Implementation would update the application using the service
        return ResponseEntity.ok(applicationDto);
    }

    /**
     * Deletes an application.
     * <p>
     * This endpoint is accessible only to System Admin role.
     * </p>
     *
     * @param id The application ID
     * @return No content response
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteApplication(@PathVariable Long id) {
        // Implementation would delete the application using the service
        return ResponseEntity.ok().build();
    }

    /**
     * Generates application reports.
     * <p>
     * This endpoint is accessible to both Operations Staff and System Admin roles.
     * It uses method-level security annotation for authorization.
     * </p>
     *
     * @return The application reports
     */
    @GetMapping("/reports")
    @PreAuthorize("hasAnyAuthority('" + RoleConstants.ROLE_OPERATIONS_STAFF + "', '" + RoleConstants.ROLE_SYSTEM_ADMIN + "')")
    public ResponseEntity<String> generateReports() {
        // Implementation would generate reports using the service
        return ResponseEntity.ok("Reports generated successfully");
    }
}