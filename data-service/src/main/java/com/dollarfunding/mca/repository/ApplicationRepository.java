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
 * This repository provides database access methods for MCA applications, extending
 * JpaRepository to inherit standard CRUD operations and adding custom query methods
 * for filtering applications by status, review status, and date ranges.
 * 
 * The repository is used by ApplicationService to persist and retrieve application data
 * from PostgreSQL, supporting the requirement to process applications in under 5 minutes
 * from receipt to completion with 99% data extraction accuracy.
 */
@Repository
public interface ApplicationRepository extends JpaRepository<Application, UUID> {
    
    /**
     * Find an application by its ID.
     * 
     * @param id The UUID of the application
     * @return An Optional containing the application if found, or empty if not found
     */
    Optional<Application> findById(UUID id);
    
    /**
     * Find all applications with a specific status.
     * 
     * @param status The application status to filter by
     * @return A list of applications with the specified status
     */
    List<Application> findByStatus(ApplicationStatus status);
    
    /**
     * Find all applications with a specific status, with pagination support.
     * 
     * @param status The application status to filter by
     * @param pageable Pagination information
     * @return A page of applications with the specified status
     */
    Page<Application> findByStatus(ApplicationStatus status, Pageable pageable);
    
    /**
     * Find all applications with a specific review status.
     * 
     * @param reviewStatus The review status to filter by
     * @return A list of applications with the specified review status
     */
    List<Application> findByReviewStatus(ReviewStatus reviewStatus);
    
    /**
     * Find all applications with a specific review status, with pagination support.
     * 
     * @param reviewStatus The review status to filter by
     * @param pageable Pagination information
     * @return A page of applications with the specified review status
     */
    Page<Application> findByReviewStatus(ReviewStatus reviewStatus, Pageable pageable);
    
    /**
     * Find all applications with a specific status and review status.
     * 
     * @param status The application status to filter by
     * @param reviewStatus The review status to filter by
     * @return A list of applications with the specified status and review status
     */
    List<Application> findByStatusAndReviewStatus(ApplicationStatus status, ReviewStatus reviewStatus);
    
    /**
     * Find all applications with a specific status and review status, with pagination support.
     * 
     * @param status The application status to filter by
     * @param reviewStatus The review status to filter by
     * @param pageable Pagination information
     * @return A page of applications with the specified status and review status
     */
    Page<Application> findByStatusAndReviewStatus(ApplicationStatus status, ReviewStatus reviewStatus, Pageable pageable);
    
    /**
     * Find all applications created within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return A list of applications created within the specified date range
     */
    List<Application> findByCreatedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications created within a specific date range, with pagination support.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable Pagination information
     * @return A page of applications created within the specified date range
     */
    Page<Application> findByCreatedAtBetween(LocalDateTime startDate, LocalDateTime endDate, Pageable pageable);
    
    /**
     * Find all applications updated within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return A list of applications updated within the specified date range
     */
    List<Application> findByUpdatedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications updated within a specific date range, with pagination support.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable Pagination information
     * @return A page of applications updated within the specified date range
     */
    Page<Application> findByUpdatedAtBetween(LocalDateTime startDate, LocalDateTime endDate, Pageable pageable);
    
    /**
     * Find all applications with a specific status created within a date range.
     * 
     * @param status The application status to filter by
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return A list of applications with the specified status created within the date range
     */
    List<Application> findByStatusAndCreatedAtBetween(
            ApplicationStatus status, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications with a specific status created within a date range, with pagination support.
     * 
     * @param status The application status to filter by
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable Pagination information
     * @return A page of applications with the specified status created within the date range
     */
    Page<Application> findByStatusAndCreatedAtBetween(
            ApplicationStatus status, LocalDateTime startDate, LocalDateTime endDate, Pageable pageable);
    
    /**
     * Find all applications with a specific review status created within a date range.
     * 
     * @param reviewStatus The review status to filter by
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return A list of applications with the specified review status created within the date range
     */
    List<Application> findByReviewStatusAndCreatedAtBetween(
            ReviewStatus reviewStatus, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all applications with a specific review status created within a date range, with pagination support.
     * 
     * @param reviewStatus The review status to filter by
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable Pagination information
     * @return A page of applications with the specified review status created within the date range
     */
    Page<Application> findByReviewStatusAndCreatedAtBetween(
            ReviewStatus reviewStatus, LocalDateTime startDate, LocalDateTime endDate, Pageable pageable);
    
    /**
     * Find all applications that contain a specific metadata key.
     * 
     * @param key The metadata key to search for
     * @return A list of applications that contain the specified metadata key
     */
    @Query("SELECT a FROM Application a WHERE a.metadataJson\\:\\:jsonb ? :key")
    List<Application> findByMetadataKey(@Param("key") String key);
    
    /**
     * Find all applications that contain a specific metadata key, with pagination support.
     * 
     * @param key The metadata key to search for
     * @param pageable Pagination information
     * @return A page of applications that contain the specified metadata key
     */
    @Query("SELECT a FROM Application a WHERE a.metadataJson\\:\\:jsonb ? :key")
    Page<Application> findByMetadataKey(@Param("key") String key, Pageable pageable);
    
    /**
     * Find all applications that contain a specific metadata key-value pair.
     * 
     * @param key The metadata key to search for
     * @param value The metadata value to search for
     * @return A list of applications that contain the specified metadata key-value pair
     */
    @Query("SELECT a FROM Application a WHERE a.metadataJson\\:\\:jsonb ->> :key = :value")
    List<Application> findByMetadataKeyValue(@Param("key") String key, @Param("value") String value);
    
    /**
     * Find all applications that contain a specific metadata key-value pair, with pagination support.
     * 
     * @param key The metadata key to search for
     * @param value The metadata value to search for
     * @param pageable Pagination information
     * @return A page of applications that contain the specified metadata key-value pair
     */
    @Query("SELECT a FROM Application a WHERE a.metadataJson\\:\\:jsonb ->> :key = :value")
    Page<Application> findByMetadataKeyValue(@Param("key") String key, @Param("value") String value, Pageable pageable);
    
    /**
     * Find all applications with a specific status that contain a specific metadata key-value pair.
     * 
     * @param status The application status to filter by
     * @param key The metadata key to search for
     * @param value The metadata value to search for
     * @return A list of applications with the specified status that contain the metadata key-value pair
     */
    @Query("SELECT a FROM Application a WHERE a.status = :status AND a.metadataJson\\:\\:jsonb ->> :key = :value")
    List<Application> findByStatusAndMetadataKeyValue(
            @Param("status") ApplicationStatus status, @Param("key") String key, @Param("value") String value);
    
    /**
     * Find all applications with a specific status that contain a specific metadata key-value pair, with pagination support.
     * 
     * @param status The application status to filter by
     * @param key The metadata key to search for
     * @param value The metadata value to search for
     * @param pageable Pagination information
     * @return A page of applications with the specified status that contain the metadata key-value pair
     */
    @Query("SELECT a FROM Application a WHERE a.status = :status AND a.metadataJson\\:\\:jsonb ->> :key = :value")
    Page<Application> findByStatusAndMetadataKeyValue(
            @Param("status") ApplicationStatus status, @Param("key") String key, @Param("value") String value, Pageable pageable);
    
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
     * Find all applications that meet the 5-minute processing time requirement.
     * This query finds applications that were processed in under 5 minutes (300,000 milliseconds).
     * 
     * @return A list of applications that were processed in under 5 minutes
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND EXTRACT(EPOCH FROM (a.updatedAt - a.createdAt)) * 1000 < 300000")
    List<Application> findApplicationsProcessedUnderFiveMinutes();
    
    /**
     * Find all applications that meet the 5-minute processing time requirement, with pagination support.
     * 
     * @param pageable Pagination information
     * @return A page of applications that were processed in under 5 minutes
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND EXTRACT(EPOCH FROM (a.updatedAt - a.createdAt)) * 1000 < 300000")
    Page<Application> findApplicationsProcessedUnderFiveMinutes(Pageable pageable);
    
    /**
     * Calculate the average processing time for completed applications in milliseconds.
     * 
     * @return The average processing time in milliseconds
     */
    @Query("SELECT AVG(EXTRACT(EPOCH FROM (a.updatedAt - a.createdAt)) * 1000) FROM Application a WHERE a.status = 'COMPLETED'")
    Double calculateAverageProcessingTimeMillis();
    
    /**
     * Find all applications that require human intervention.
     * This includes applications with statuses that require manual review or intervention.
     * 
     * @return A list of applications that require human intervention
     */
    @Query("SELECT a FROM Application a WHERE a.status IN ('EXCEPTION', 'ERROR', 'PENDING')")
    List<Application> findApplicationsRequiringHumanIntervention();
    
    /**
     * Find all applications that require human intervention, with pagination support.
     * 
     * @param pageable Pagination information
     * @return A page of applications that require human intervention
     */
    @Query("SELECT a FROM Application a WHERE a.status IN ('EXCEPTION', 'ERROR', 'PENDING')")
    Page<Application> findApplicationsRequiringHumanIntervention(Pageable pageable);
    
    /**
     * Find all applications that have been automatically processed without human intervention.
     * This includes applications that were processed successfully without requiring manual review.
     * 
     * @return A list of applications that were automatically processed
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND a.status NOT IN ('EXCEPTION', 'ERROR', 'PENDING')")
    List<Application> findAutomaticallyProcessedApplications();
    
    /**
     * Find all applications that have been automatically processed without human intervention, with pagination support.
     * 
     * @param pageable Pagination information
     * @return A page of applications that were automatically processed
     */
    @Query("SELECT a FROM Application a WHERE a.status = 'COMPLETED' AND a.status NOT IN ('EXCEPTION', 'ERROR', 'PENDING')")
    Page<Application> findAutomaticallyProcessedApplications(Pageable pageable);
    
    /**
     * Calculate the automation rate as a percentage of applications that were processed automatically.
     * This is used to track the 93% automation rate requirement.
     * 
     * @return The automation rate as a decimal (e.g., 0.93 for 93%)
     */
    @Query("SELECT COUNT(a) * 1.0 / (SELECT COUNT(*) FROM Application) FROM Application a WHERE a.status = 'COMPLETED' AND a.status NOT IN ('EXCEPTION', 'ERROR', 'PENDING')")
    Double calculateAutomationRate();
    
    /**
     * Find all applications with a specific document count.
     * 
     * @param count The number of documents to filter by
     * @return A list of applications with the specified document count
     */
    @Query("SELECT a FROM Application a WHERE SIZE(a.documents) = :count")
    List<Application> findByDocumentCount(@Param("count") int count);
    
    /**
     * Find all applications with a specific document count, with pagination support.
     * 
     * @param count The number of documents to filter by
     * @param pageable Pagination information
     * @return A page of applications with the specified document count
     */
    @Query("SELECT a FROM Application a WHERE SIZE(a.documents) = :count")
    Page<Application> findByDocumentCount(@Param("count") int count, Pageable pageable);
    
    /**
     * Find all applications with merchant details.
     * 
     * @return A list of applications that have merchant details
     */
    @Query("SELECT a FROM Application a WHERE a.merchantDetails IS NOT NULL")
    List<Application> findApplicationsWithMerchantDetails();
    
    /**
     * Find all applications with merchant details, with pagination support.
     * 
     * @param pageable Pagination information
     * @return A page of applications that have merchant details
     */
    @Query("SELECT a FROM Application a WHERE a.merchantDetails IS NOT NULL")
    Page<Application> findApplicationsWithMerchantDetails(Pageable pageable);
    
    /**
     * Find all applications without merchant details.
     * 
     * @return A list of applications that do not have merchant details
     */
    @Query("SELECT a FROM Application a WHERE a.merchantDetails IS NULL")
    List<Application> findApplicationsWithoutMerchantDetails();
    
    /**
     * Find all applications without merchant details, with pagination support.
     * 
     * @param pageable Pagination information
     * @return A page of applications that do not have merchant details
     */
    @Query("SELECT a FROM Application a WHERE a.merchantDetails IS NULL")
    Page<Application> findApplicationsWithoutMerchantDetails(Pageable pageable);
}