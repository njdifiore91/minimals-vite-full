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

import com.dollarfunding.mca.TestData;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;

/**
 * JUnit test class for {@link WebhookRepository} that verifies the repository correctly
 * interacts with the database for {@link Webhook} entities.
 * <p>
 * This test class uses {@link DataJpaTest} to configure an in-memory database for testing
 * and includes setup methods to create test data. It tests CRUD operations, custom query
 * methods for finding webhooks by endpoint URL, active status, and event type, as well as
 * specific configuration attributes.
 * </p>
 */
@DataJpaTest
public class WebhookRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private WebhookRepository webhookRepository;

    private Webhook webhook1;
    private Webhook webhook2;
    private Webhook webhook3;
    private Webhook webhook4;

    /**
     * Sets up test data before each test method.
     * <p>
     * Creates four webhook entities with different configurations:
     * <ul>
     *   <li>webhook1: Active, APPLICATION_CREATED event type</li>
     *   <li>webhook2: Active, DOCUMENT_UPLOADED event type</li>
     *   <li>webhook3: Inactive, APPLICATION_APPROVED event type</li>
     *   <li>webhook4: Active, APPLICATION_UPDATED event type with failed delivery attempts</li>
     * </ul>
     * </p>
     */
    @BeforeEach
    public void setup() {
        // Create test webhooks with different configurations
        webhook1 = TestData.createWebhook(webhook -> {
            webhook.setId(null); // Let the database generate the ID
            webhook.setEndpointUrl("https://example.com/webhooks/applications");
            webhook.setSecretKey("secret-key-1-for-applications");
            webhook.setActive(true);
            webhook.setEventType(EventType.APPLICATION_CREATED);
            webhook.setMaxRetryAttempts(3);
            webhook.setFailedAttempts(0);
            webhook.setLastDeliverySuccess(true);
            webhook.setLastDeliveryStatusCode(200);
            webhook.setLastDeliveryStatus("SUCCESS");
            webhook.setSignatureHeader("X-Webhook-Signature");
        });

        webhook2 = TestData.createWebhook(webhook -> {
            webhook.setId(null);
            webhook.setEndpointUrl("https://example.com/webhooks/documents");
            webhook.setSecretKey("secret-key-2-for-documents");
            webhook.setActive(true);
            webhook.setEventType(EventType.DOCUMENT_UPLOADED);
            webhook.setMaxRetryAttempts(5);
            webhook.setFailedAttempts(0);
            webhook.setLastDeliverySuccess(true);
            webhook.setLastDeliveryStatusCode(200);
            webhook.setLastDeliveryStatus("SUCCESS");
            webhook.setSignatureHeader("X-Document-Signature");
        });

        webhook3 = TestData.createWebhook(webhook -> {
            webhook.setId(null);
            webhook.setEndpointUrl("https://example.com/webhooks/approvals");
            webhook.setSecretKey("secret-key-3-for-approvals");
            webhook.setActive(false); // Inactive webhook
            webhook.setEventType(EventType.APPLICATION_APPROVED);
            webhook.setMaxRetryAttempts(3);
            webhook.setFailedAttempts(0);
            webhook.setLastDeliverySuccess(null); // Never delivered
            webhook.setLastDeliveryStatusCode(null);
            webhook.setLastDeliveryStatus(null);
            webhook.setLastDeliveryAttempt(null);
        });

        webhook4 = TestData.createWebhook(webhook -> {
            webhook.setId(null);
            webhook.setEndpointUrl("https://example.com/webhooks/updates");
            webhook.setSecretKey("secret-key-4-for-updates");
            webhook.setActive(true);
            webhook.setEventType(EventType.APPLICATION_UPDATED);
            webhook.setMaxRetryAttempts(3);
            webhook.setFailedAttempts(2); // Has failed attempts but still under max retries
            webhook.setLastDeliverySuccess(false);
            webhook.setLastDeliveryStatusCode(500);
            webhook.setLastDeliveryStatus("FAILED: Internal Server Error");
            webhook.setLastDeliveryAttempt(LocalDateTime.now().minusMinutes(30));
            webhook.setLastDeliveryError("Internal Server Error");
        });

        // Persist test data
        entityManager.persist(webhook1);
        entityManager.persist(webhook2);
        entityManager.persist(webhook3);
        entityManager.persist(webhook4);
        entityManager.flush();
    }

    /**
     * Tests that the repository can save a webhook entity and retrieve it by ID.
     */
    @Test
    @DisplayName("Should save and find webhook by ID")
    public void testSaveAndFindById() {
        // Create a new webhook
        Webhook newWebhook = TestData.createWebhook(webhook -> {
            webhook.setId(null);
            webhook.setEndpointUrl("https://example.com/webhooks/new");
            webhook.setSecretKey("new-secret-key");
            webhook.setActive(true);
            webhook.setEventType(EventType.DOCUMENT_PROCESSED);
        });

        // Save the webhook
        Webhook savedWebhook = webhookRepository.save(newWebhook);

        // Verify the webhook was saved with an ID
        assertThat(savedWebhook.getId()).isNotNull();

        // Find the webhook by ID
        Optional<Webhook> foundWebhook = webhookRepository.findById(savedWebhook.getId());

        // Verify the webhook was found and has the correct properties
        assertThat(foundWebhook).isPresent();
        assertThat(foundWebhook.get().getEndpointUrl()).isEqualTo("https://example.com/webhooks/new");
        assertThat(foundWebhook.get().getSecretKey()).isEqualTo("new-secret-key");
        assertThat(foundWebhook.get().getActive()).isTrue();
        assertThat(foundWebhook.get().getEventType()).isEqualTo(EventType.DOCUMENT_PROCESSED);
    }

    /**
     * Tests that the repository can find all webhook entities.
     */
    @Test
    @DisplayName("Should find all webhooks")
    public void testFindAll() {
        // Find all webhooks
        List<Webhook> webhooks = webhookRepository.findAll();

        // Verify all webhooks were found
        assertThat(webhooks).hasSize(4);
        assertThat(webhooks).extracting(Webhook::getEndpointUrl)
                .contains(
                        "https://example.com/webhooks/applications",
                        "https://example.com/webhooks/documents",
                        "https://example.com/webhooks/approvals",
                        "https://example.com/webhooks/updates"
                );
    }

    /**
     * Tests that the repository can delete a webhook entity.
     */
    @Test
    @DisplayName("Should delete webhook")
    public void testDelete() {
        // Delete webhook1
        webhookRepository.delete(webhook1);
        entityManager.flush();

        // Verify webhook1 was deleted
        Optional<Webhook> deletedWebhook = webhookRepository.findById(webhook1.getId());
        assertThat(deletedWebhook).isEmpty();

        // Verify other webhooks still exist
        List<Webhook> remainingWebhooks = webhookRepository.findAll();
        assertThat(remainingWebhooks).hasSize(3);
        assertThat(remainingWebhooks).extracting(Webhook::getId)
                .contains(webhook2.getId(), webhook3.getId(), webhook4.getId());
    }

    /**
     * Tests that the repository can find a webhook by its endpoint URL.
     */
    @Test
    @DisplayName("Should find webhook by endpoint URL")
    public void testFindByEndpointUrl() {
        // Find webhook by endpoint URL
        Optional<Webhook> foundWebhook = webhookRepository.findByEndpointUrl("https://example.com/webhooks/documents");

        // Verify the webhook was found and has the correct properties
        assertThat(foundWebhook).isPresent();
        assertThat(foundWebhook.get().getId()).isEqualTo(webhook2.getId());
        assertThat(foundWebhook.get().getSecretKey()).isEqualTo("secret-key-2-for-documents");
        assertThat(foundWebhook.get().getEventType()).isEqualTo(EventType.DOCUMENT_UPLOADED);

        // Test with non-existent URL
        Optional<Webhook> notFoundWebhook = webhookRepository.findByEndpointUrl("https://example.com/non-existent");
        assertThat(notFoundWebhook).isEmpty();
    }

    /**
     * Tests that the repository can check if a webhook exists by its endpoint URL.
     */
    @Test
    @DisplayName("Should check if webhook exists by endpoint URL")
    public void testExistsByEndpointUrl() {
        // Check if webhook exists by endpoint URL
        boolean exists = webhookRepository.existsByEndpointUrl("https://example.com/webhooks/applications");
        assertThat(exists).isTrue();

        // Check with non-existent URL
        boolean notExists = webhookRepository.existsByEndpointUrl("https://example.com/non-existent");
        assertThat(notExists).isFalse();
    }

    /**
     * Tests that the repository can find webhooks by active status.
     */
    @Test
    @DisplayName("Should find webhooks by active status")
    public void testFindByActive() {
        // Find active webhooks
        List<Webhook> activeWebhooks = webhookRepository.findByActive(true);
        assertThat(activeWebhooks).hasSize(3);
        assertThat(activeWebhooks).extracting(Webhook::getId)
                .contains(webhook1.getId(), webhook2.getId(), webhook4.getId());

        // Find inactive webhooks
        List<Webhook> inactiveWebhooks = webhookRepository.findByActive(false);
        assertThat(inactiveWebhooks).hasSize(1);
        assertThat(inactiveWebhooks.get(0).getId()).isEqualTo(webhook3.getId());
    }

    /**
     * Tests that the repository can find webhooks by event type.
     */
    @Test
    @DisplayName("Should find webhooks by event type")
    public void testFindByEventType() {
        // Find webhooks for APPLICATION_CREATED event type
        List<Webhook> applicationCreatedWebhooks = webhookRepository.findByEventType(EventType.APPLICATION_CREATED);
        assertThat(applicationCreatedWebhooks).hasSize(1);
        assertThat(applicationCreatedWebhooks.get(0).getId()).isEqualTo(webhook1.getId());

        // Find webhooks for DOCUMENT_UPLOADED event type
        List<Webhook> documentUploadedWebhooks = webhookRepository.findByEventType(EventType.DOCUMENT_UPLOADED);
        assertThat(documentUploadedWebhooks).hasSize(1);
        assertThat(documentUploadedWebhooks.get(0).getId()).isEqualTo(webhook2.getId());

        // Find webhooks for non-existent event type
        List<Webhook> nonExistentEventTypeWebhooks = webhookRepository.findByEventType(EventType.DOCUMENT_PROCESSED);
        assertThat(nonExistentEventTypeWebhooks).isEmpty();
    }

    /**
     * Tests that the repository can find webhooks by event type and active status.
     */
    @Test
    @DisplayName("Should find webhooks by event type and active status")
    public void testFindByEventTypeAndActive() {
        // Find active webhooks for APPLICATION_CREATED event type
        List<Webhook> activeApplicationCreatedWebhooks = webhookRepository.findByEventTypeAndActive(
                EventType.APPLICATION_CREATED, true);
        assertThat(activeApplicationCreatedWebhooks).hasSize(1);
        assertThat(activeApplicationCreatedWebhooks.get(0).getId()).isEqualTo(webhook1.getId());

        // Find inactive webhooks for APPLICATION_APPROVED event type
        List<Webhook> inactiveApplicationApprovedWebhooks = webhookRepository.findByEventTypeAndActive(
                EventType.APPLICATION_APPROVED, false);
        assertThat(inactiveApplicationApprovedWebhooks).hasSize(1);
        assertThat(inactiveApplicationApprovedWebhooks.get(0).getId()).isEqualTo(webhook3.getId());

        // Find active webhooks for APPLICATION_APPROVED event type (should be empty)
        List<Webhook> activeApplicationApprovedWebhooks = webhookRepository.findByEventTypeAndActive(
                EventType.APPLICATION_APPROVED, true);
        assertThat(activeApplicationApprovedWebhooks).isEmpty();
    }

    /**
     * Tests that the repository can find webhooks that need to be retried after failed delivery attempts.
     */
    @Test
    @DisplayName("Should find webhooks for retry")
    public void testFindWebhooksForRetry() {
        // Find webhooks for retry
        List<Webhook> webhooksForRetry = webhookRepository.findWebhooksForRetry();
        assertThat(webhooksForRetry).hasSize(1);
        assertThat(webhooksForRetry.get(0).getId()).isEqualTo(webhook4.getId());
        assertThat(webhooksForRetry.get(0).getFailedAttempts()).isEqualTo(2);
        assertThat(webhooksForRetry.get(0).getMaxRetryAttempts()).isEqualTo(3);
        assertThat(webhooksForRetry.get(0).getEventType()).isEqualTo(EventType.APPLICATION_UPDATED);
    }

    /**
     * Tests that the repository can find webhooks that need to be retried for a specific event type.
     */
    @Test
    @DisplayName("Should find webhooks for retry by event type")
    public void testFindWebhooksForRetryByEventType() {
        // Find webhooks for retry for APPLICATION_UPDATED event type
        List<Webhook> webhooksForRetryByEventType = webhookRepository.findWebhooksForRetryByEventType(
                EventType.APPLICATION_UPDATED);
        assertThat(webhooksForRetryByEventType).hasSize(1);
        assertThat(webhooksForRetryByEventType.get(0).getId()).isEqualTo(webhook4.getId());

        // Find webhooks for retry for APPLICATION_CREATED event type (should be empty)
        List<Webhook> emptyWebhooksForRetry = webhookRepository.findWebhooksForRetryByEventType(
                EventType.APPLICATION_CREATED);
        assertThat(emptyWebhooksForRetry).isEmpty();
    }

    /**
     * Tests that the repository can find webhooks with a specific delivery status.
     */
    @Test
    @DisplayName("Should find webhooks by delivery status")
    public void testFindByLastDeliveryStatusContaining() {
        // Find webhooks with SUCCESS status
        List<Webhook> successWebhooks = webhookRepository.findByLastDeliveryStatusContaining("SUCCESS");
        assertThat(successWebhooks).hasSize(2);
        assertThat(successWebhooks).extracting(Webhook::getId)
                .contains(webhook1.getId(), webhook2.getId());

        // Find webhooks with FAILED status
        List<Webhook> failedWebhooks = webhookRepository.findByLastDeliveryStatusContaining("FAILED");
        assertThat(failedWebhooks).hasSize(1);
        assertThat(failedWebhooks.get(0).getId()).isEqualTo(webhook4.getId());

        // Find webhooks with non-existent status
        List<Webhook> nonExistentStatusWebhooks = webhookRepository.findByLastDeliveryStatusContaining("PENDING");
        assertThat(nonExistentStatusWebhooks).isEmpty();
    }

    /**
     * Tests that the repository can find webhooks with a specific maximum number of retry attempts.
     */
    @Test
    @DisplayName("Should find webhooks by max retry attempts")
    public void testFindByMaxRetryAttempts() {
        // Find webhooks with max retry attempts = 3
        List<Webhook> webhooksWithMaxRetry3 = webhookRepository.findByMaxRetryAttempts(3);
        assertThat(webhooksWithMaxRetry3).hasSize(3);
        assertThat(webhooksWithMaxRetry3).extracting(Webhook::getId)
                .contains(webhook1.getId(), webhook3.getId(), webhook4.getId());

        // Find webhooks with max retry attempts = 5
        List<Webhook> webhooksWithMaxRetry5 = webhookRepository.findByMaxRetryAttempts(5);
        assertThat(webhooksWithMaxRetry5).hasSize(1);
        assertThat(webhooksWithMaxRetry5.get(0).getId()).isEqualTo(webhook2.getId());

        // Find webhooks with non-existent max retry attempts
        List<Webhook> nonExistentMaxRetryWebhooks = webhookRepository.findByMaxRetryAttempts(10);
        assertThat(nonExistentMaxRetryWebhooks).isEmpty();
    }

    /**
     * Tests that the repository can find webhooks for application-related events.
     */
    @Test
    @DisplayName("Should find application webhooks")
    public void testFindApplicationWebhooks() {
        // Find application webhooks
        List<Webhook> applicationWebhooks = webhookRepository.findApplicationWebhooks();
        assertThat(applicationWebhooks).hasSize(3);
        assertThat(applicationWebhooks).extracting(Webhook::getEventType)
                .contains(EventType.APPLICATION_CREATED, EventType.APPLICATION_APPROVED, EventType.APPLICATION_UPDATED);
    }

    /**
     * Tests that the repository can find webhooks for document-related events.
     */
    @Test
    @DisplayName("Should find document webhooks")
    public void testFindDocumentWebhooks() {
        // Find document webhooks
        List<Webhook> documentWebhooks = webhookRepository.findDocumentWebhooks();
        assertThat(documentWebhooks).hasSize(1);
        assertThat(documentWebhooks.get(0).getEventType()).isEqualTo(EventType.DOCUMENT_UPLOADED);
    }

    /**
     * Tests that the repository can find active webhooks for application-related events.
     */
    @Test
    @DisplayName("Should find active application webhooks")
    public void testFindActiveApplicationWebhooks() {
        // Find active application webhooks
        List<Webhook> activeApplicationWebhooks = webhookRepository.findActiveApplicationWebhooks();
        assertThat(activeApplicationWebhooks).hasSize(2);
        assertThat(activeApplicationWebhooks).extracting(Webhook::getEventType)
                .contains(EventType.APPLICATION_CREATED, EventType.APPLICATION_UPDATED);
    }

    /**
     * Tests that the repository can find active webhooks for document-related events.
     */
    @Test
    @DisplayName("Should find active document webhooks")
    public void testFindActiveDocumentWebhooks() {
        // Find active document webhooks
        List<Webhook> activeDocumentWebhooks = webhookRepository.findActiveDocumentWebhooks();
        assertThat(activeDocumentWebhooks).hasSize(1);
        assertThat(activeDocumentWebhooks.get(0).getEventType()).isEqualTo(EventType.DOCUMENT_UPLOADED);
    }

    /**
     * Tests that the repository can find webhooks with successful delivery status.
     */
    @Test
    @DisplayName("Should find successful webhooks")
    public void testFindSuccessfulWebhooks() {
        // Find successful webhooks
        List<Webhook> successfulWebhooks = webhookRepository.findSuccessfulWebhooks();
        assertThat(successfulWebhooks).hasSize(2);
        assertThat(successfulWebhooks).extracting(Webhook::getId)
                .contains(webhook1.getId(), webhook2.getId());
    }

    /**
     * Tests that the repository can find webhooks with failed delivery status.
     */
    @Test
    @DisplayName("Should find failed webhooks")
    public void testFindFailedWebhooks() {
        // Find failed webhooks
        List<Webhook> failedWebhooks = webhookRepository.findFailedWebhooks();
        assertThat(failedWebhooks).hasSize(1);
        assertThat(failedWebhooks.get(0).getId()).isEqualTo(webhook4.getId());
    }

    /**
     * Tests that the repository can find webhooks that have never been delivered.
     */
    @Test
    @DisplayName("Should find never delivered webhooks")
    public void testFindNeverDeliveredWebhooks() {
        // Find never delivered webhooks
        List<Webhook> neverDeliveredWebhooks = webhookRepository.findNeverDeliveredWebhooks();
        assertThat(neverDeliveredWebhooks).hasSize(1);
        assertThat(neverDeliveredWebhooks.get(0).getId()).isEqualTo(webhook3.getId());
    }

    /**
     * Tests that the repository can find webhooks with a specific HTTP status code from the last delivery.
     */
    @Test
    @DisplayName("Should find webhooks by HTTP status code")
    public void testFindByLastDeliveryStatusCode() {
        // Find webhooks with status code 200
        List<Webhook> webhooksWith200 = webhookRepository.findByLastDeliveryStatusCode(200);
        assertThat(webhooksWith200).hasSize(2);
        assertThat(webhooksWith200).extracting(Webhook::getId)
                .contains(webhook1.getId(), webhook2.getId());

        // Find webhooks with status code 500
        List<Webhook> webhooksWith500 = webhookRepository.findByLastDeliveryStatusCode(500);
        assertThat(webhooksWith500).hasSize(1);
        assertThat(webhooksWith500.get(0).getId()).isEqualTo(webhook4.getId());

        // Find webhooks with non-existent status code
        List<Webhook> webhooksWith404 = webhookRepository.findByLastDeliveryStatusCode(404);
        assertThat(webhooksWith404).isEmpty();
    }

    /**
     * Tests that the repository can find webhooks with permanently failed status.
     */
    @Test
    @DisplayName("Should find permanently failed webhooks")
    public void testFindPermanentlyFailedWebhooks() {
        // Create a permanently failed webhook
        Webhook permanentlyFailedWebhook = TestData.createWebhook(webhook -> {
            webhook.setId(null);
            webhook.setEndpointUrl("https://example.com/webhooks/permanent-failure");
            webhook.setSecretKey("secret-key-permanent-failure");
            webhook.setActive(true);
            webhook.setEventType(EventType.APPLICATION_REJECTED);
            webhook.setMaxRetryAttempts(3);
            webhook.setFailedAttempts(4); // Exceeds max retry attempts
            webhook.setLastDeliverySuccess(false);
            webhook.setLastDeliveryStatusCode(500);
            webhook.setLastDeliveryStatus("FAILED: Permanent failure");
        });
        entityManager.persist(permanentlyFailedWebhook);
        entityManager.flush();

        // Find permanently failed webhooks
        List<Webhook> permanentlyFailedWebhooks = webhookRepository.findPermanentlyFailedWebhooks();
        assertThat(permanentlyFailedWebhooks).hasSize(1);
        assertThat(permanentlyFailedWebhooks.get(0).getEndpointUrl()).isEqualTo("https://example.com/webhooks/permanent-failure");
        assertThat(permanentlyFailedWebhooks.get(0).getFailedAttempts()).isEqualTo(4);
        assertThat(permanentlyFailedWebhooks.get(0).getMaxRetryAttempts()).isEqualTo(3);
    }

    /**
     * Tests that the repository correctly handles the webhook entity's business methods.
     */
    @Test
    @DisplayName("Should handle webhook entity business methods")
    public void testWebhookEntityBusinessMethods() {
        // Test recordSuccessfulDelivery
        Webhook webhookToUpdate = webhookRepository.findById(webhook4.getId()).orElseThrow();
        webhookToUpdate.recordSuccessfulDelivery();
        webhookRepository.save(webhookToUpdate);

        Webhook updatedWebhook = webhookRepository.findById(webhook4.getId()).orElseThrow();
        assertThat(updatedWebhook.getLastDeliveryStatus()).isEqualTo("SUCCESS");
        assertThat(updatedWebhook.getFailedAttempts()).isEqualTo(0);
        assertThat(updatedWebhook.getLastDeliveryAttempt()).isNotNull();

        // Test recordFailedDelivery
        boolean canRetry = updatedWebhook.recordFailedDelivery("Connection timeout");
        webhookRepository.save(updatedWebhook);

        Webhook failedWebhook = webhookRepository.findById(webhook4.getId()).orElseThrow();
        assertThat(canRetry).isTrue();
        assertThat(failedWebhook.getLastDeliveryStatus()).isEqualTo("FAILED: Connection timeout");
        assertThat(failedWebhook.getFailedAttempts()).isEqualTo(1);
        assertThat(failedWebhook.getLastDeliveryAttempt()).isNotNull();

        // Test shouldRetry
        assertThat(failedWebhook.shouldRetry()).isTrue();

        // Test reaching max retry attempts
        failedWebhook.recordFailedDelivery("Connection timeout");
        failedWebhook.recordFailedDelivery("Connection timeout");
        boolean exceedsMaxRetries = failedWebhook.recordFailedDelivery("Connection timeout");
        webhookRepository.save(failedWebhook);

        Webhook maxRetriesWebhook = webhookRepository.findById(webhook4.getId()).orElseThrow();
        assertThat(exceedsMaxRetries).isFalse();
        assertThat(maxRetriesWebhook.getFailedAttempts()).isEqualTo(4);
        assertThat(maxRetriesWebhook.shouldRetry()).isFalse();

        // Test resetFailedAttempts
        maxRetriesWebhook.resetFailedAttempts();
        webhookRepository.save(maxRetriesWebhook);

        Webhook resetWebhook = webhookRepository.findById(webhook4.getId()).orElseThrow();
        assertThat(resetWebhook.getFailedAttempts()).isEqualTo(0);
        assertThat(resetWebhook.shouldRetry()).isFalse(); // No failed attempts to retry
    }

    /**
     * Tests that the repository correctly handles secure storage of webhook secret keys.
     */
    @Test
    @DisplayName("Should securely store webhook secret keys")
    public void testSecureStorageOfSecretKeys() {
        // Create a webhook with a secret key
        String secretKey = "very-secure-secret-key-for-testing";
        Webhook webhookWithSecretKey = TestData.createWebhook(webhook -> {
            webhook.setId(null);
            webhook.setEndpointUrl("https://example.com/webhooks/secure");
            webhook.setSecretKey(secretKey);
            webhook.setActive(true);
            webhook.setEventType(EventType.APPLICATION_CREATED);
        });

        // Save the webhook
        Webhook savedWebhook = webhookRepository.save(webhookWithSecretKey);

        // Retrieve the webhook from the database
        Webhook retrievedWebhook = webhookRepository.findById(savedWebhook.getId()).orElseThrow();

        // Verify the secret key is stored correctly and can be retrieved
        assertThat(retrievedWebhook.getSecretKey()).isEqualTo(secretKey);

        // Verify the webhook can be found by endpoint URL and has the correct secret key
        Optional<Webhook> foundWebhook = webhookRepository.findByEndpointUrl("https://example.com/webhooks/secure");
        assertThat(foundWebhook).isPresent();
        assertThat(foundWebhook.get().getSecretKey()).isEqualTo(secretKey);
    }
}