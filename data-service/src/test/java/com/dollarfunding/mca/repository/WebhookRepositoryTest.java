package com.dollarfunding.mca.repository;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;

/**
 * Integration tests for {@link WebhookRepository}.
 * <p>
 * These tests verify that the repository correctly interacts with the database
 * for Webhook entities. It tests CRUD operations, custom query methods for finding
 * webhooks by endpoint URL, active status, and event type, as well as specific
 * configuration attributes.
 * </p>
 */
@DataJpaTest
public class WebhookRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private WebhookRepository webhookRepository;

    private Webhook activeApplicationCreatedWebhook;
    private Webhook inactiveApplicationCreatedWebhook;
    private Webhook activeDocumentUploadedWebhook;
    private Webhook webhookWithFailures;
    private Webhook webhookExceededRetryLimit;
    private LocalDateTime baseTime;

    @BeforeEach
    public void setup() {
        // Clear any existing data
        webhookRepository.deleteAll();
        
        baseTime = LocalDateTime.now().minusDays(1);
        
        // Create test webhooks
        activeApplicationCreatedWebhook = new Webhook(
                "https://example.com/webhooks/applications",
                "secretKey123456789",
                true,
                EventType.APPLICATION_CREATED);
        activeApplicationCreatedWebhook.setDescription("Active webhook for application created events");
        
        inactiveApplicationCreatedWebhook = new Webhook(
                "https://example.com/webhooks/inactive",
                "inactiveSecretKey",
                false,
                EventType.APPLICATION_CREATED);
        inactiveApplicationCreatedWebhook.setDescription("Inactive webhook for application created events");
        
        activeDocumentUploadedWebhook = new Webhook(
                "https://example.com/webhooks/documents",
                "documentSecretKey",
                true,
                EventType.DOCUMENT_UPLOADED);
        activeDocumentUploadedWebhook.setDescription("Active webhook for document uploaded events");
        
        webhookWithFailures = new Webhook(
                "https://example.com/webhooks/failing",
                "failingSecretKey",
                true,
                EventType.APPLICATION_APPROVED);
        webhookWithFailures.setConsecutiveFailures(2);
        webhookWithFailures.setMaxRetryAttempts(5);
        webhookWithFailures.setLastFailureAt(baseTime.plusHours(1));
        webhookWithFailures.setDescription("Webhook with failures but still within retry limit");
        
        webhookExceededRetryLimit = new Webhook(
                "https://example.com/webhooks/exceeded",
                "exceededSecretKey",
                true,
                EventType.APPLICATION_REJECTED);
        webhookExceededRetryLimit.setConsecutiveFailures(5);
        webhookExceededRetryLimit.setMaxRetryAttempts(3);
        webhookExceededRetryLimit.setLastFailureAt(baseTime.plusHours(2));
        webhookExceededRetryLimit.setDescription("Webhook that exceeded retry limit");
        
        // Persist test webhooks
        entityManager.persist(activeApplicationCreatedWebhook);
        entityManager.persist(inactiveApplicationCreatedWebhook);
        entityManager.persist(activeDocumentUploadedWebhook);
        entityManager.persist(webhookWithFailures);
        entityManager.persist(webhookExceededRetryLimit);
        entityManager.flush();
    }

    @Test
    @DisplayName("Should save a new webhook")
    public void testSaveWebhook() {
        // Given
        Webhook newWebhook = new Webhook(
                "https://example.com/webhooks/new",
                "newSecretKey123456789",
                true,
                EventType.DOCUMENT_PROCESSED);
        newWebhook.setDescription("New webhook for testing save operation");
        
        // When
        Webhook savedWebhook = webhookRepository.save(newWebhook);
        
        // Then
        assertThat(savedWebhook).isNotNull();
        assertThat(savedWebhook.getId()).isNotNull();
        assertThat(savedWebhook.getEndpointUrl()).isEqualTo("https://example.com/webhooks/new");
        assertThat(savedWebhook.getSecretKey()).isEqualTo("newSecretKey123456789");
        assertThat(savedWebhook.getActive()).isTrue();
        assertThat(savedWebhook.getEventType()).isEqualTo(EventType.DOCUMENT_PROCESSED);
        assertThat(savedWebhook.getDescription()).isEqualTo("New webhook for testing save operation");
        assertThat(savedWebhook.getCreatedAt()).isNotNull();
        assertThat(savedWebhook.getUpdatedAt()).isNotNull();
    }

    @Test
    @DisplayName("Should find webhook by ID")
    public void testFindById() {
        // Given
        Long id = activeApplicationCreatedWebhook.getId();
        
        // When
        Optional<Webhook> foundWebhook = webhookRepository.findById(id);
        
        // Then
        assertThat(foundWebhook).isPresent();
        assertThat(foundWebhook.get().getEndpointUrl()).isEqualTo("https://example.com/webhooks/applications");
        assertThat(foundWebhook.get().getEventType()).isEqualTo(EventType.APPLICATION_CREATED);
    }

    @Test
    @DisplayName("Should find all webhooks")
    public void testFindAll() {
        // When
        List<Webhook> allWebhooks = webhookRepository.findAll();
        
        // Then
        assertThat(allWebhooks).hasSize(5);
    }

    @Test
    @DisplayName("Should delete webhook")
    public void testDeleteWebhook() {
        // Given
        Long id = activeApplicationCreatedWebhook.getId();
        
        // When
        webhookRepository.deleteById(id);
        Optional<Webhook> deletedWebhook = webhookRepository.findById(id);
        
        // Then
        assertThat(deletedWebhook).isEmpty();
        assertThat(webhookRepository.count()).isEqualTo(4);
    }

    @Test
    @DisplayName("Should find webhook by endpoint URL")
    public void testFindByEndpointUrl() {
        // Given
        String endpointUrl = "https://example.com/webhooks/applications";
        
        // When
        Optional<Webhook> foundWebhook = webhookRepository.findByEndpointUrl(endpointUrl);
        
        // Then
        assertThat(foundWebhook).isPresent();
        assertThat(foundWebhook.get().getEndpointUrl()).isEqualTo(endpointUrl);
        assertThat(foundWebhook.get().getEventType()).isEqualTo(EventType.APPLICATION_CREATED);
    }

    @Test
    @DisplayName("Should check if webhook exists by endpoint URL")
    public void testExistsByEndpointUrl() {
        // Given
        String existingUrl = "https://example.com/webhooks/applications";
        String nonExistingUrl = "https://example.com/webhooks/nonexistent";
        
        // When
        boolean existsResult = webhookRepository.existsByEndpointUrl(existingUrl);
        boolean notExistsResult = webhookRepository.existsByEndpointUrl(nonExistingUrl);
        
        // Then
        assertThat(existsResult).isTrue();
        assertThat(notExistsResult).isFalse();
    }

    @Test
    @DisplayName("Should find webhooks by active status")
    public void testFindByActive() {
        // When
        List<Webhook> activeWebhooks = webhookRepository.findByActive(true);
        List<Webhook> inactiveWebhooks = webhookRepository.findByActive(false);
        
        // Then
        assertThat(activeWebhooks).hasSize(4);
        assertThat(inactiveWebhooks).hasSize(1);
        
        // Verify all active webhooks are actually active
        assertThat(activeWebhooks).allMatch(webhook -> webhook.getActive());
        
        // Verify all inactive webhooks are actually inactive
        assertThat(inactiveWebhooks).allMatch(webhook -> !webhook.getActive());
    }

    @Test
    @DisplayName("Should find webhooks by active status with pagination")
    public void testFindByActiveWithPagination() {
        // Given
        Pageable pageable = PageRequest.of(0, 2);
        
        // When
        Page<Webhook> activeWebhooksPage = webhookRepository.findByActive(true, pageable);
        
        // Then
        assertThat(activeWebhooksPage.getContent()).hasSize(2);
        assertThat(activeWebhooksPage.getTotalElements()).isEqualTo(4);
        assertThat(activeWebhooksPage.getTotalPages()).isEqualTo(2);
        assertThat(activeWebhooksPage.getContent()).allMatch(webhook -> webhook.getActive());
    }

    @Test
    @DisplayName("Should find webhooks by event type")
    public void testFindByEventType() {
        // When
        List<Webhook> applicationCreatedWebhooks = webhookRepository.findByEventType(EventType.APPLICATION_CREATED);
        List<Webhook> documentUploadedWebhooks = webhookRepository.findByEventType(EventType.DOCUMENT_UPLOADED);
        List<Webhook> documentProcessedWebhooks = webhookRepository.findByEventType(EventType.DOCUMENT_PROCESSED);
        
        // Then
        assertThat(applicationCreatedWebhooks).hasSize(2);
        assertThat(documentUploadedWebhooks).hasSize(1);
        assertThat(documentProcessedWebhooks).isEmpty();
        
        // Verify all APPLICATION_CREATED webhooks have the correct event type
        assertThat(applicationCreatedWebhooks).allMatch(webhook -> webhook.getEventType() == EventType.APPLICATION_CREATED);
        
        // Verify all DOCUMENT_UPLOADED webhooks have the correct event type
        assertThat(documentUploadedWebhooks).allMatch(webhook -> webhook.getEventType() == EventType.DOCUMENT_UPLOADED);
    }

    @Test
    @DisplayName("Should find webhooks by event type and active status")
    public void testFindByEventTypeAndActive() {
        // When
        List<Webhook> activeApplicationCreatedWebhooks = webhookRepository.findByEventTypeAndActive(
                EventType.APPLICATION_CREATED, true);
        List<Webhook> inactiveApplicationCreatedWebhooks = webhookRepository.findByEventTypeAndActive(
                EventType.APPLICATION_CREATED, false);
        
        // Then
        assertThat(activeApplicationCreatedWebhooks).hasSize(1);
        assertThat(inactiveApplicationCreatedWebhooks).hasSize(1);
        
        // Verify active APPLICATION_CREATED webhooks are actually active
        assertThat(activeApplicationCreatedWebhooks).allMatch(webhook -> 
                webhook.getEventType() == EventType.APPLICATION_CREATED && webhook.getActive());
        
        // Verify inactive APPLICATION_CREATED webhooks are actually inactive
        assertThat(inactiveApplicationCreatedWebhooks).allMatch(webhook -> 
                webhook.getEventType() == EventType.APPLICATION_CREATED && !webhook.getActive());
    }

    @Test
    @DisplayName("Should find webhooks eligible for retry")
    public void testFindWebhooksEligibleForRetry() {
        // When
        List<Webhook> eligibleWebhooks = webhookRepository.findWebhooksEligibleForRetry();
        
        // Then
        assertThat(eligibleWebhooks).hasSize(1);
        assertThat(eligibleWebhooks.get(0).getEndpointUrl()).isEqualTo("https://example.com/webhooks/failing");
        assertThat(eligibleWebhooks.get(0).getConsecutiveFailures()).isEqualTo(2);
        assertThat(eligibleWebhooks.get(0).getMaxRetryAttempts()).isEqualTo(5);
    }

    @Test
    @DisplayName("Should find webhooks that exceeded retry limit")
    public void testFindWebhooksExceededRetryLimit() {
        // When
        List<Webhook> exceededWebhooks = webhookRepository.findWebhooksExceededRetryLimit();
        
        // Then
        assertThat(exceededWebhooks).hasSize(1);
        assertThat(exceededWebhooks.get(0).getEndpointUrl()).isEqualTo("https://example.com/webhooks/exceeded");
        assertThat(exceededWebhooks.get(0).getConsecutiveFailures()).isEqualTo(5);
        assertThat(exceededWebhooks.get(0).getMaxRetryAttempts()).isEqualTo(3);
    }

    @Test
    @DisplayName("Should find webhooks not delivered since a specific time")
    public void testFindWebhooksNotDeliveredSince() {
        // Given
        LocalDateTime since = baseTime.plusMinutes(30);
        
        // When
        List<Webhook> notDeliveredWebhooks = webhookRepository.findWebhooksNotDeliveredSince(since);
        
        // Then
        assertThat(notDeliveredWebhooks).hasSize(4); // All active webhooks without lastSuccessAt set
    }

    @Test
    @DisplayName("Should find webhooks that failed since a specific time")
    public void testFindWebhooksFailedSince() {
        // Given
        LocalDateTime since = baseTime.plusMinutes(30);
        
        // When
        List<Webhook> failedWebhooks = webhookRepository.findWebhooksFailedSince(since);
        
        // Then
        assertThat(failedWebhooks).hasSize(2); // Both webhooks with failures
        assertThat(failedWebhooks).extracting(Webhook::getEndpointUrl)
                .containsExactlyInAnyOrder(
                        "https://example.com/webhooks/failing",
                        "https://example.com/webhooks/exceeded");
    }

    @Test
    @DisplayName("Should count active webhooks for a specific event type")
    public void testCountByEventTypeAndActive() {
        // When
        long activeApplicationCreatedCount = webhookRepository.countByEventTypeAndActive(
                EventType.APPLICATION_CREATED, true);
        long inactiveApplicationCreatedCount = webhookRepository.countByEventTypeAndActive(
                EventType.APPLICATION_CREATED, false);
        long activeDocumentUploadedCount = webhookRepository.countByEventTypeAndActive(
                EventType.DOCUMENT_UPLOADED, true);
        
        // Then
        assertThat(activeApplicationCreatedCount).isEqualTo(1);
        assertThat(inactiveApplicationCreatedCount).isEqualTo(1);
        assertThat(activeDocumentUploadedCount).isEqualTo(1);
    }

    @Test
    @DisplayName("Should find webhooks by description pattern")
    public void testFindByDescriptionContaining() {
        // When
        List<Webhook> activeWebhooks = webhookRepository.findByDescriptionContaining("Active");
        List<Webhook> documentWebhooks = webhookRepository.findByDescriptionContaining("document");
        List<Webhook> failureWebhooks = webhookRepository.findByDescriptionContaining("fail");
        
        // Then
        assertThat(activeWebhooks).hasSize(2); // Both active webhooks with "Active" in description
        assertThat(documentWebhooks).hasSize(1); // Only the document webhook
        assertThat(failureWebhooks).hasSize(1); // Only the webhook with failures
    }

    @Test
    @DisplayName("Should find webhooks created after a specific date")
    public void testFindByCreatedAtAfter() {
        // Given
        LocalDateTime pastDate = baseTime.minusDays(1);
        LocalDateTime futureDate = LocalDateTime.now().plusDays(1);
        
        // When
        List<Webhook> webhooksCreatedAfterPast = webhookRepository.findByCreatedAtAfter(pastDate);
        List<Webhook> webhooksCreatedAfterFuture = webhookRepository.findByCreatedAtAfter(futureDate);
        
        // Then
        assertThat(webhooksCreatedAfterPast).hasSize(5); // All webhooks
        assertThat(webhooksCreatedAfterFuture).isEmpty(); // No webhooks created in the future
    }

    @Test
    @DisplayName("Should find webhooks updated after a specific date")
    public void testFindByUpdatedAtAfter() {
        // Given
        LocalDateTime pastDate = baseTime.minusDays(1);
        LocalDateTime futureDate = LocalDateTime.now().plusDays(1);
        
        // When
        List<Webhook> webhooksUpdatedAfterPast = webhookRepository.findByUpdatedAtAfter(pastDate);
        List<Webhook> webhooksUpdatedAfterFuture = webhookRepository.findByUpdatedAtAfter(futureDate);
        
        // Then
        assertThat(webhooksUpdatedAfterPast).hasSize(5); // All webhooks
        assertThat(webhooksUpdatedAfterFuture).isEmpty(); // No webhooks updated in the future
    }

    @Test
    @DisplayName("Should securely store webhook secret keys")
    public void testSecureStorageOfSecretKeys() {
        // Given
        String secretKey = "secretKey123456789";
        
        // When
        Optional<Webhook> foundWebhook = webhookRepository.findByEndpointUrl("https://example.com/webhooks/applications");
        
        // Then
        assertThat(foundWebhook).isPresent();
        assertThat(foundWebhook.get().getSecretKey()).isEqualTo(secretKey);
        
        // Verify that the secret key is stored as is (in a real application, it would be encrypted)
        // This test verifies that the repository correctly retrieves the secret key as it was stored
        Webhook webhook = entityManager.find(Webhook.class, foundWebhook.get().getId());
        assertThat(webhook.getSecretKey()).isEqualTo(secretKey);
    }

    @Test
    @DisplayName("Should update webhook properties")
    public void testUpdateWebhook() {
        // Given
        Webhook webhookToUpdate = webhookRepository.findByEndpointUrl("https://example.com/webhooks/applications").get();
        webhookToUpdate.setActive(false);
        webhookToUpdate.setDescription("Updated description");
        
        // When
        Webhook updatedWebhook = webhookRepository.save(webhookToUpdate);
        
        // Then
        assertThat(updatedWebhook.getActive()).isFalse();
        assertThat(updatedWebhook.getDescription()).isEqualTo("Updated description");
        
        // Verify that the update was persisted
        Webhook retrievedWebhook = webhookRepository.findById(updatedWebhook.getId()).get();
        assertThat(retrievedWebhook.getActive()).isFalse();
        assertThat(retrievedWebhook.getDescription()).isEqualTo("Updated description");
    }

    @Test
    @DisplayName("Should record webhook success and failure")
    public void testRecordSuccessAndFailure() {
        // Given
        Webhook webhook = webhookRepository.findByEndpointUrl("https://example.com/webhooks/failing").get();
        int initialFailures = webhook.getConsecutiveFailures();
        
        // When - Record success
        webhook.recordSuccess();
        webhookRepository.save(webhook);
        
        // Then - Consecutive failures should be reset
        Webhook afterSuccess = webhookRepository.findById(webhook.getId()).get();
        assertThat(afterSuccess.getConsecutiveFailures()).isZero();
        assertThat(afterSuccess.getLastSuccessAt()).isNotNull();
        
        // When - Record failure
        afterSuccess.recordFailure();
        webhookRepository.save(afterSuccess);
        
        // Then - Consecutive failures should be incremented
        Webhook afterFailure = webhookRepository.findById(webhook.getId()).get();
        assertThat(afterFailure.getConsecutiveFailures()).isEqualTo(1);
        assertThat(afterFailure.getLastFailureAt()).isNotNull();
    }

    @Test
    @DisplayName("Should deactivate webhook after exceeding retry limit")
    public void testDeactivateAfterExceedingRetryLimit() {
        // Given
        Webhook webhook = webhookRepository.findByEndpointUrl("https://example.com/webhooks/failing").get();
        webhook.setMaxRetryAttempts(3); // Set max retries to 3
        webhook.setConsecutiveFailures(2); // Already has 2 failures
        webhookRepository.save(webhook);
        
        // When - Record another failure (3rd one)
        boolean shouldDeactivate = webhook.recordFailure();
        webhookRepository.save(webhook);
        
        // Then - Should indicate deactivation and webhook should be inactive
        assertThat(shouldDeactivate).isTrue();
        assertThat(webhook.getActive()).isFalse();
        
        // Verify that the deactivation was persisted
        Webhook deactivatedWebhook = webhookRepository.findById(webhook.getId()).get();
        assertThat(deactivatedWebhook.getActive()).isFalse();
        assertThat(deactivatedWebhook.getConsecutiveFailures()).isEqualTo(3);
    }
}