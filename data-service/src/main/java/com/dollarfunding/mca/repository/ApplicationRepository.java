package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository interface for Application entities.
 * 
 * This repository provides database access methods for MCA applications. It extends JpaRepository
 * to inherit standard CRUD operations and adds custom query methods for filtering applications by
 * status, review status, and date ranges.
 * 
 * The repository is designed to support the requirement of processing applications in under 5 minutes
 * from receipt to completion and maintaining 99% data extraction accuracy through AI and machine learning.
 */
@Repository
public interface ApplicationRepository extends JpaRepository<Application, UUID> {
    
    /**
     * Find an application by its ID.
     * 
     * @param id The application ID
     * @return Optional containing the application if found, empty otherwise
     */
    Optional<Application> findById(UUID id);
    
    /**
     * Find all applications with a specific status.
     * 
     * @param status The application status to filter by
     * @return List of applications with the specified status
     */
    List<Application> findByStatus(ApplicationStatus status);
    
    /**
     * Find all applications with a specific status, with pagination.
     * 
     * @param status The application status to filter by
     * @param pageable The pagination information
     * @return Page of applications with the specified status
     */
    Page<Application> findByStatus(ApplicationStatus status, Pageable pageable);
    
    /**
     * Find all applications with a specific review status.
     * 
     * @param reviewStatus The review status to filter by
     * @return List of applications with the specified review status
     */
    List<Application> findByReviewStatus(ReviewStatus reviewStatus);
    
    /**
     * Find all applications with a specific review status, with pagination.
     * 
     * @param reviewStatus The review status to filter by
     * @param pageable The pagination information
     * @return Page of applications with the specified review status
     */
    Page<Application> findByReviewStatus(ReviewStatus reviewStatus, Pageable pageable);
    
    /**
     * Find all applications with a specific status and review status.
     * 
     * @param status The application status to filter by
     * @param reviewStatus The review status to filter by
     * @return List of applications with the specified status and review status
     */
    List<Application> findByStatusAndReviewStatus(ApplicationStatus status, ReviewStatus reviewStatus);
    
    /**
     * Find all applications with a specific status and review status, with pagination.
     * 
     * @param status The application status to filter by
     * @param reviewStatus The review status to filter by
     * @param pageable The pagination information
     * @return Page of applications with the specified status and review status
     */
    Page<Application> findByStatusAndReviewStatus(ApplicationStatus status, ReviewStatus reviewStatus, Pageable pageable);
    
    /**
     * Find all applications created within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of applications created within the specified date range
     */
    List<Application> findByCreatedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications created within a specific date range, with pagination.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable The pagination information
     * @return Page of applications created within the specified date range
     */
    Page<Application> findByCreatedAtBetween(LocalDateTime startDate, LocalDateTime endDate, Pageable pageable);
    
    /**
     * Find all applications updated within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of applications updated within the specified date range
     */
    List<Application> findByUpdatedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications updated within a specific date range, with pagination.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable The pagination information
     * @return Page of applications updated within the specified date range
     */
    Page<Application> findByUpdatedAtBetween(LocalDateTime startDate, LocalDateTime endDate, Pageable pageable);
    
    /**
     * Find all applications created after a specific date.
     * 
     * @param date The date after which applications were created
     * @return List of applications created after the specified date
     */
    List<Application> findByCreatedAtAfter(LocalDateTime date);
    
    /**
     * Find all applications created before a specific date.
     * 
     * @param date The date before which applications were created
     * @return List of applications created before the specified date
     */
    List<Application> findByCreatedAtBefore(LocalDateTime date);
    
    /**
     * Find all applications updated after a specific date.
     * 
     * @param date The date after which applications were updated
     * @return List of applications updated after the specified date
     */
    List<Application> findByUpdatedAtAfter(LocalDateTime date);
    
    /**
     * Find all applications updated before a specific date.
     * 
     * @param date The date before which applications were updated
     * @return List of applications updated before the specified date
     */
    List<Application> findByUpdatedAtBefore(LocalDateTime date);
    
    /**
     * Find all applications with a specific status created within a date range.
     * 
     * @param status The application status to filter by
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of applications with the specified status created within the date range
     */
    List<Application> findByStatusAndCreatedAtBetween(
            ApplicationStatus status, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications with a specific status updated within a date range.
     * 
     * @param status The application status to filter by
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of applications with the specified status updated within the date range
     */
    List<Application> findByStatusAndUpdatedAtBetween(
            ApplicationStatus status, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Count the number of applications with a specific status.
     * 
     * @param status The application status to count
     * @return The number of applications with the specified status
     */
    long countByStatus(ApplicationStatus status);
    
    /**
     * Count the number of applications with a specific review status.
     * 
     * @param reviewStatus The review status to count
     * @return The number of applications with the specified review status
     */
    long countByReviewStatus(ReviewStatus reviewStatus);
    
    /**
     * Count the number of applications with a specific status and review status.
     * 
     * @param status The application status to count
     * @param reviewStatus The review status to count
     * @return The number of applications with the specified status and review status
     */
    long countByStatusAndReviewStatus(ApplicationStatus status, ReviewStatus reviewStatus);
    
    /**
     * Count the number of applications created within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return The number of applications created within the specified date range
     */
    long countByCreatedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Count the number of applications updated within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return The number of applications updated within the specified date range
     */
    long countByUpdatedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications with metadata containing a specific key.
     * 
     * @param key The metadata key to search for
     * @return List of applications with metadata containing the specified key
     */
    @Query(value = "SELECT a FROM Application a WHERE a.metadataJson @> CAST(:jsonPath AS jsonb)")
    List<Application> findByMetadataContainsKey(@Param("jsonPath") String key);
    
    /**
     * Find all applications with metadata containing a specific key-value pair.
     * 
     * @param keyValueJson The JSON string representing the key-value pair to search for
     * @return List of applications with metadata containing the specified key-value pair
     */
    @Query(value = "SELECT a FROM Application a WHERE a.metadataJson @> CAST(:keyValueJson AS jsonb)")
    List<Application> findByMetadataContains(@Param("keyValueJson") String keyValueJson);
    
    /**
     * Find all applications with metadata containing a specific key-value pair, with pagination.
     * 
     * @param keyValueJson The JSON string representing the key-value pair to search for
     * @param pageable The pagination information
     * @return Page of applications with metadata containing the specified key-value pair
     */
    @Query(value = "SELECT a FROM Application a WHERE a.metadataJson @> CAST(:keyValueJson AS jsonb)")
    Page<Application> findByMetadataContains(@Param("keyValueJson") String keyValueJson, Pageable pageable);
    
    /**
     * Find all applications that require review.
     * Applications require review if their review status is NOT_REVIEWED or NEEDS_INFORMATION.
     * 
     * @return List of applications that require review
     */
    @Query("SELECT a FROM Application a WHERE a.reviewStatus.requiresAction = true")
    List<Application> findApplicationsRequiringReview();
    
    /**
     * Find all applications that require review, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications that require review
     */
    @Query("SELECT a FROM Application a WHERE a.reviewStatus.requiresAction = true")
    Page<Application> findApplicationsRequiringReview(Pageable pageable);
    
    /**
     * Find all applications that are in an active state.
     * Applications are active if their status is NEW, PENDING, or PROCESSING.
     * 
     * @return List of active applications
     */
    @Query("SELECT a FROM Application a WHERE a.status.isActiveStatus = true")
    List<Application> findActiveApplications();
    
    /**
     * Find all applications that are in an active state, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of active applications
     */
    @Query("SELECT a FROM Application a WHERE a.status.isActiveStatus = true")
    Page<Application> findActiveApplications(Pageable pageable);
    
    /**
     * Find all applications that have been decided upon.
     * Applications are decided upon if their status is APPROVED, REJECTED, or COMPLETED.
     * 
     * @return List of decided applications
     */
    @Query("SELECT a FROM Application a WHERE a.status.isDecidedStatus = true")
    List<Application> findDecidedApplications();
    
    /**
     * Find all applications that have been decided upon, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of decided applications
     */
    @Query("SELECT a FROM Application a WHERE a.status.isDecidedStatus = true")
    Page<Application> findDecidedApplications(Pageable pageable);
    
    /**
     * Find all applications that have been completed.
     * Applications are completed if their status is COMPLETED.
     * 
     * @return List of completed applications
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED'")
    List<Application> findCompletedApplications();
    
    /**
     * Find all applications that have been completed, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of completed applications
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED'")
    Page<Application> findCompletedApplications(Pageable pageable);
    
    /**
     * Find all applications that were processed within the target time (5 minutes).
     * 
     * @return List of applications processed within the target time
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND FUNCTION('EXTRACT', EPOCH FROM a.updatedAt - a.createdAt) / 60 <= 5")
    List<Application> findApplicationsProcessedWithinTargetTime();
    
    /**
     * Find all applications that were processed within the target time (5 minutes), with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications processed within the target time
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND FUNCTION('EXTRACT', EPOCH FROM a.updatedAt - a.createdAt) / 60 <= 5")
    Page<Application> findApplicationsProcessedWithinTargetTime(Pageable pageable);
    
    /**
     * Find all applications that exceeded the target processing time (5 minutes).
     * 
     * @return List of applications that exceeded the target processing time
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND FUNCTION('EXTRACT', EPOCH FROM a.updatedAt - a.createdAt) / 60 > 5")
    List<Application> findApplicationsExceedingTargetTime();
    
    /**
     * Find all applications that exceeded the target processing time (5 minutes), with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications that exceeded the target processing time
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND FUNCTION('EXTRACT', EPOCH FROM a.updatedAt - a.createdAt) / 60 > 5")
    Page<Application> findApplicationsExceedingTargetTime(Pageable pageable);
    
    /**
     * Calculate the average processing time (in minutes) for completed applications.
     * 
     * @return The average processing time in minutes
     */
    @Query("SELECT AVG(FUNCTION('EXTRACT', EPOCH FROM a.updatedAt - a.createdAt) / 60) FROM Application a WHERE a.status = 'COMPLETED'")
    Double calculateAverageProcessingTimeMinutes();
    
    /**
     * Calculate the average processing time (in minutes) for completed applications within a date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return The average processing time in minutes
     */
    @Query("SELECT AVG(FUNCTION('EXTRACT', EPOCH FROM a.updatedAt - a.createdAt) / 60) FROM Application a " +
           "WHERE a.status = 'COMPLETED' AND a.updatedAt BETWEEN :startDate AND :endDate")
    Double calculateAverageProcessingTimeMinutes(
            @Param("startDate") LocalDateTime startDate, @Param("endDate") LocalDateTime endDate);
    
    /**
     * Find all applications that have all required documents.
     * 
     * @return List of applications that have all required documents
     */
    @Query("SELECT a FROM Application a WHERE EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND d.type = 'ID_VERIFICATION') AND EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND (d.type = 'BANK_STATEMENT' OR d.type = 'TAX_RETURN')) AND EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND (d.type = 'BUSINESS_LICENSE' OR d.type = 'INVOICE'))")
    List<Application> findApplicationsWithAllRequiredDocuments();
    
    /**
     * Find all applications that are missing required documents.
     * 
     * @return List of applications that are missing required documents
     */
    @Query("SELECT a FROM Application a WHERE NOT EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND d.type = 'ID_VERIFICATION') OR NOT EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND (d.type = 'BANK_STATEMENT' OR d.type = 'TAX_RETURN')) OR NOT EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND (d.type = 'BUSINESS_LICENSE' OR d.type = 'INVOICE'))")
    List<Application> findApplicationsMissingRequiredDocuments();
    
    /**
     * Find all applications that are missing required documents, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of applications that are missing required documents
     */
    @Query("SELECT a FROM Application a WHERE NOT EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND d.type = 'ID_VERIFICATION') OR NOT EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND (d.type = 'BANK_STATEMENT' OR d.type = 'TAX_RETURN')) OR NOT EXISTS (" +
           "SELECT 1 FROM Document d WHERE d.applicationId = a.id AND (d.type = 'BUSINESS_LICENSE' OR d.type = 'INVOICE'))")
    Page<Application> findApplicationsMissingRequiredDocuments(Pageable pageable);
    
    /**
     * Find all applications with merchant details in a specific industry.
     * 
     * @param industry The industry to filter by
     * @return List of applications with merchant details in the specified industry
     */
    @Query("SELECT a FROM Application a JOIN a.merchantDetails m WHERE m.industry = :industry")
    List<Application> findByMerchantIndustry(@Param("industry") String industry);
    
    /**
     * Find all applications with merchant details in a specific industry, with pagination.
     * 
     * @param industry The industry to filter by
     * @param pageable The pagination information
     * @return Page of applications with merchant details in the specified industry
     */
    @Query("SELECT a FROM Application a JOIN a.merchantDetails m WHERE m.industry = :industry")
    Page<Application> findByMerchantIndustry(@Param("industry") String industry, Pageable pageable);
    
    /**
     * Find all applications with merchant details in a specific state.
     * 
     * @param state The state to filter by (2-letter code)
     * @return List of applications with merchant details in the specified state
     */
    @Query("SELECT a FROM Application a JOIN a.merchantDetails m WHERE m.address.state = :state")
    List<Application> findByMerchantState(@Param("state") String state);
    
    /**
     * Find all applications with merchant details in a specific state, with pagination.
     * 
     * @param state The state to filter by (2-letter code)
     * @param pageable The pagination information
     * @return Page of applications with merchant details in the specified state
     */
    @Query("SELECT a FROM Application a JOIN a.merchantDetails m WHERE m.address.state = :state")
    Page<Application> findByMerchantState(@Param("state") String state, Pageable pageable);
}