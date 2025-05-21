package com.dollarfunding.mca.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;

/**
 * Repository interface for {@link Webhook} entities.
 * <p>
 * This repository provides database access methods for webhook configurations,
 * including standard CRUD operations inherited from JpaRepository and custom
 * query methods for finding webhooks by endpoint URL, active status, and event type.
 * </p>
 * <p>
 * It is used by the WebhookService to manage webhook configurations for notification
 * delivery to external systems.
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
     * Finds all webhooks with the specified active status.
     *
     * @param active the active status to filter by
     * @return a list of webhooks with the specified active status
     */
    List<Webhook> findByActive(Boolean active);

    /**
     * Finds all webhooks configured for the specified event type.
     *
     * @param eventType the event type to filter by
     * @return a list of webhooks configured for the specified event type
     */
    List<Webhook> findByEventType(EventType eventType);

    /**
     * Finds all active webhooks configured for the specified event type.
     *
     * @param eventType the event type to filter by
     * @param active the active status to filter by
     * @return a list of active webhooks configured for the specified event type
     */
    List<Webhook> findByEventTypeAndActive(EventType eventType, Boolean active);

    /**
     * Finds all webhooks that need to be retried after failed delivery attempts.
     * <p>
     * A webhook needs to be retried if it is active and has failed attempts greater than 0
     * but less than or equal to its maximum retry attempts.
     * </p>
     *
     * @return a list of webhooks that need to be retried
     */
    @Query("SELECT w FROM Webhook w WHERE w.active = true AND w.failedAttempts > 0 AND w.failedAttempts <= w.maxRetryAttempts")
    List<Webhook> findWebhooksForRetry();

    /**
     * Finds all webhooks that need to be retried for a specific event type.
     *
     * @param eventType the event type to filter by
     * @return a list of webhooks that need to be retried for the specified event type
     */
    @Query("SELECT w FROM Webhook w WHERE w.active = true AND w.eventType = :eventType AND w.failedAttempts > 0 AND w.failedAttempts <= w.maxRetryAttempts")
    List<Webhook> findWebhooksForRetryByEventType(@Param("eventType") EventType eventType);

    /**
     * Finds all webhooks with a specific delivery status.
     *
     * @param status the delivery status to filter by
     * @return a list of webhooks with the specified delivery status
     */
    List<Webhook> findByLastDeliveryStatusContaining(String status);

    /**
     * Checks if a webhook with the specified endpoint URL already exists.
     *
     * @param endpointUrl the URL of the webhook endpoint
     * @return true if a webhook with the specified endpoint URL exists, false otherwise
     */
    boolean existsByEndpointUrl(String endpointUrl);

    /**
     * Finds all webhooks with failed attempts exceeding their maximum retry attempts.
     * <p>
     * These webhooks have permanently failed and require manual intervention.
     * </p>
     *
     * @return a list of webhooks that have permanently failed
     */
    @Query("SELECT w FROM Webhook w WHERE w.failedAttempts > w.maxRetryAttempts")
    List<Webhook> findPermanentlyFailedWebhooks();

    /**
     * Finds all webhooks with a specific maximum number of retry attempts.
     *
     * @param maxRetryAttempts the maximum number of retry attempts to filter by
     * @return a list of webhooks with the specified maximum number of retry attempts
     */
    List<Webhook> findByMaxRetryAttempts(Integer maxRetryAttempts);

    /**
     * Finds all webhooks for application-related events.
     * <p>
     * Application-related events include APPLICATION_CREATED, APPLICATION_UPDATED,
     * APPLICATION_APPROVED, and APPLICATION_REJECTED.
     * </p>
     *
     * @return a list of webhooks for application-related events
     */
    @Query("SELECT w FROM Webhook w WHERE w.eventType IN ('APPLICATION_CREATED', 'APPLICATION_UPDATED', 'APPLICATION_APPROVED', 'APPLICATION_REJECTED')")
    List<Webhook> findApplicationWebhooks();

    /**
     * Finds all webhooks for document-related events.
     * <p>
     * Document-related events include DOCUMENT_UPLOADED and DOCUMENT_PROCESSED.
     * </p>
     *
     * @return a list of webhooks for document-related events
     */
    @Query("SELECT w FROM Webhook w WHERE w.eventType IN ('DOCUMENT_UPLOADED', 'DOCUMENT_PROCESSED')")
    List<Webhook> findDocumentWebhooks();

    /**
     * Finds all active webhooks for application-related events.
     *
     * @return a list of active webhooks for application-related events
     */
    @Query("SELECT w FROM Webhook w WHERE w.active = true AND w.eventType IN ('APPLICATION_CREATED', 'APPLICATION_UPDATED', 'APPLICATION_APPROVED', 'APPLICATION_REJECTED')")
    List<Webhook> findActiveApplicationWebhooks();

    /**
     * Finds all active webhooks for document-related events.
     *
     * @return a list of active webhooks for document-related events
     */
    @Query("SELECT w FROM Webhook w WHERE w.active = true AND w.eventType IN ('DOCUMENT_UPLOADED', 'DOCUMENT_PROCESSED')")
    List<Webhook> findActiveDocumentWebhooks();
    
    /**
     * Finds all webhooks with successful delivery status.
     *
     * @return a list of webhooks with successful delivery status
     */
    @Query("SELECT w FROM Webhook w WHERE w.lastDeliverySuccess = true")
    List<Webhook> findSuccessfulWebhooks();
    
    /**
     * Finds all webhooks with failed delivery status.
     *
     * @return a list of webhooks with failed delivery status
     */
    @Query("SELECT w FROM Webhook w WHERE w.lastDeliverySuccess = false")
    List<Webhook> findFailedWebhooks();
    
    /**
     * Finds all webhooks that have never been delivered.
     *
     * @return a list of webhooks that have never been delivered
     */
    @Query("SELECT w FROM Webhook w WHERE w.lastDeliveryAttempt IS NULL")
    List<Webhook> findNeverDeliveredWebhooks();
    
    /**
     * Finds all webhooks with a specific HTTP status code from the last delivery.
     *
     * @param statusCode the HTTP status code to filter by
     * @return a list of webhooks with the specified HTTP status code
     */
    List<Webhook> findByLastDeliveryStatusCode(Integer statusCode);
}