package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Repository interface for {@link Webhook} entities.
 * <p>
 * This repository provides database access methods for webhook configurations,
 * including custom query methods for finding webhooks by endpoint URL, active status,
 * and event type. It is used by the WebhookService to manage webhook configurations
 * for notification delivery to external systems.
 * </p>
 */
@Repository
public interface WebhookRepository extends JpaRepository<Webhook, Long> {

    /**
     * Finds a webhook by its endpoint URL.
     *
     * @param endpointUrl the URL of the webhook endpoint
     * @return an Optional containing the webhook if found, or empty if not found
     */
    Optional<Webhook> findByEndpointUrl(String endpointUrl);

    /**
     * Checks if a webhook exists with the given endpoint URL.
     *
     * @param endpointUrl the URL of the webhook endpoint
     * @return true if a webhook with the given URL exists, false otherwise
     */
    boolean existsByEndpointUrl(String endpointUrl);

    /**
     * Finds all webhooks with the given active status.
     *
     * @param active the active status to filter by
     * @return a list of webhooks with the given active status
     */
    List<Webhook> findByActive(Boolean active);

    /**
     * Finds all webhooks with the given active status, with pagination.
     *
     * @param active the active status to filter by
     * @param pageable pagination information
     * @return a page of webhooks with the given active status
     */
    Page<Webhook> findByActive(Boolean active, Pageable pageable);

    /**
     * Finds all webhooks configured for the given event type.
     *
     * @param eventType the event type to filter by
     * @return a list of webhooks configured for the given event type
     */
    List<Webhook> findByEventType(EventType eventType);

    /**
     * Finds all active webhooks configured for the given event type.
     *
     * @param eventType the event type to filter by
     * @param active the active status to filter by
     * @return a list of active webhooks configured for the given event type
     */
    List<Webhook> findByEventTypeAndActive(EventType eventType, Boolean active);

    /**
     * Finds all webhooks that have failed but are still eligible for retry.
     * These are webhooks that are active, have at least one failure, but have not
     * exceeded their maximum retry attempts.
     *
     * @return a list of webhooks eligible for retry
     */
    @Query("SELECT w FROM Webhook w WHERE w.active = true AND w.consecutiveFailures > 0 AND w.consecutiveFailures < w.maxRetryAttempts")
    List<Webhook> findWebhooksEligibleForRetry();

    /**
     * Finds all webhooks that have failed and exceeded their maximum retry attempts.
     * These are webhooks that are active but have reached their retry limit.
     *
     * @return a list of webhooks that have exceeded their retry limit
     */
    @Query("SELECT w FROM Webhook w WHERE w.active = true AND w.consecutiveFailures >= w.maxRetryAttempts")
    List<Webhook> findWebhooksExceededRetryLimit();

    /**
     * Finds all webhooks that have not been successfully delivered since the given time.
     *
     * @param since the time threshold for last successful delivery
     * @return a list of webhooks that have not been successfully delivered since the given time
     */
    @Query("SELECT w FROM Webhook w WHERE w.active = true AND (w.lastSuccessAt IS NULL OR w.lastSuccessAt < :since)")
    List<Webhook> findWebhooksNotDeliveredSince(@Param("since") LocalDateTime since);

    /**
     * Finds all webhooks that have failed since the given time.
     *
     * @param since the time threshold for last failure
     * @return a list of webhooks that have failed since the given time
     */
    @Query("SELECT w FROM Webhook w WHERE w.lastFailureAt IS NOT NULL AND w.lastFailureAt >= :since")
    List<Webhook> findWebhooksFailedSince(@Param("since") LocalDateTime since);

    /**
     * Counts the number of active webhooks for the given event type.
     *
     * @param eventType the event type to count
     * @return the number of active webhooks for the given event type
     */
    long countByEventTypeAndActive(EventType eventType, Boolean active);

    /**
     * Finds all webhooks with the given description pattern.
     *
     * @param descriptionPattern the pattern to match in the description field
     * @return a list of webhooks with descriptions matching the given pattern
     */
    @Query("SELECT w FROM Webhook w WHERE w.description LIKE %:pattern%")
    List<Webhook> findByDescriptionContaining(@Param("pattern") String descriptionPattern);

    /**
     * Finds all webhooks created after the given date.
     *
     * @param createdAfter the date after which webhooks were created
     * @return a list of webhooks created after the given date
     */
    List<Webhook> findByCreatedAtAfter(LocalDateTime createdAfter);

    /**
     * Finds all webhooks updated after the given date.
     *
     * @param updatedAfter the date after which webhooks were updated
     * @return a list of webhooks updated after the given date
     */
    List<Webhook> findByUpdatedAtAfter(LocalDateTime updatedAfter);
}