package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentClassification;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.messaging.MessagingException;
import com.dollarfunding.mca.messaging.NotificationMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the NotificationServiceImpl class that manages notification delivery
 * for the MCA application. Tests verify notification delivery through multiple channels,
 * integration with NotificationProducer for RabbitMQ, asynchronous notification processing,
 * template management, and delivery status tracking.
 */
@ExtendWith(MockitoExtension.class)
public class NotificationServiceImplTest {

    @Mock
    private NotificationProducer notificationProducer;

    @Mock
    private ResourceLoader resourceLoader;

    @Mock
    private Resource mockResource;

    @InjectMocks
    private NotificationServiceImpl notificationService;

    @Captor
    private ArgumentCaptor<NotificationMessage> notificationCaptor;

    @Captor
    private ArgumentCaptor<List<NotificationMessage.Recipient>> recipientsCaptor;

    @Captor
    private ArgumentCaptor<Map<String, Object>> payloadCaptor;

    private Application testApplication;
    private Document testDocument;
    private MerchantDetails testMerchantDetails;
    private final String testTemplateContent = "<html><body>Test notification template</body></html>";
    private final String testNotificationId = "test-notification-id";

    @BeforeEach
    void setUp() {
        // Set up test application
        testApplication = new Application(ApplicationStatus.PENDING);
        testApplication.setId(UUID.randomUUID());
        testApplication.setCreatedAt(LocalDateTime.now().minusHours(1));
        testApplication.setUpdatedAt(LocalDateTime.now());
        testApplication.setReviewStatus(ReviewStatus.IN_REVIEW);
        
        // Set up test merchant details
        testMerchantDetails = new MerchantDetails();
        testMerchantDetails.setId(UUID.randomUUID());
        testMerchantDetails.setLegalName("Test Business LLC");
        testMerchantDetails.setDbaName("Test Business");
        testMerchantDetails.setIndustry("Retail");
        testApplication.setMerchantDetails(testMerchantDetails);
        
        // Set up test document
        testDocument = new Document();
        testDocument.setId(UUID.randomUUID());
        testDocument.setApplicationId(testApplication.getId());
        testDocument.setType(DocumentType.BANK_STATEMENT);
        testDocument.setClassification(DocumentClassification.HIGH_CONFIDENCE);
        testDocument.setStoragePath("mca-documents-test/test-application/bank-statement.pdf");
        testDocument.setUploadedAt(LocalDateTime.now());
        testDocument.setConfidenceScore(0.95);
        
        // Configure NotificationServiceImpl properties
        ReflectionTestUtils.setField(notificationService, "templatesPath", "classpath:templates/notifications/");
        ReflectionTestUtils.setField(notificationService, "defaultRetryCount", 3);
        ReflectionTestUtils.setField(notificationService, "webhookEnabled", true);
        ReflectionTestUtils.setField(notificationService, "emailEnabled", true);
        
        // Mock resource loader behavior
        try {
            when(mockResource.exists()).thenReturn(true);
            when(mockResource.getInputStream()).thenReturn(new ByteArrayInputStream(testTemplateContent.getBytes(StandardCharsets.UTF_8)));
            when(resourceLoader.getResource(contains("templates/notifications/"))).thenReturn(mockResource);
        } catch (IOException e) {
            fail("Failed to set up mock resource: " + e.getMessage());
        }
        
        // Mock NotificationProducer behavior
        try {
            when(notificationProducer.publishStatusUpdate(anyString(), anyString(), anyMap(), anyList()))
                    .thenReturn(testNotificationId);
            when(notificationProducer.publishNotification(any(NotificationMessage.NotificationType.class),
                    any(NotificationMessage.NotificationPriority.class), anyMap(), anyList()))
                    .thenReturn(testNotificationId);
            when(notificationProducer.publishCompletionNotification(anyString(), anyString(), anyMap(), anyList()))
                    .thenReturn(testNotificationId);
            when(notificationProducer.publishErrorNotification(anyString(), anyString(), anyString(), anyList()))
                    .thenReturn(testNotificationId);
        } catch (MessagingException e) {
            fail("Failed to set up mock notification producer: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending application status notification successfully")
    void testSendApplicationStatusNotification() {
        // Arrange
        String previousStatus = ApplicationStatus.NEW.name();
        String newStatus = ApplicationStatus.PENDING.name();
        
        // Act
        boolean result = notificationService.sendApplicationStatusNotification(testApplication, previousStatus, newStatus);
        
        // Assert
        assertTrue(result, "Notification should be sent successfully");
        try {
            verify(notificationProducer).publishStatusUpdate(
                    eq(testApplication.getId().toString()),
                    eq(newStatus),
                    anyMap(),
                    recipientsCaptor.capture());
            
            List<NotificationMessage.Recipient> recipients = recipientsCaptor.getValue();
            assertNotNull(recipients, "Recipients list should not be null");
            assertFalse(recipients.isEmpty(), "Recipients list should not be empty");
            
            // Verify webhook recipient is included
            assertTrue(recipients.stream()
                    .anyMatch(r -> r.getType() == NotificationMessage.RecipientType.WEBHOOK),
                    "Webhook recipient should be included");
            
            // Verify email recipient is included
            assertTrue(recipients.stream()
                    .anyMatch(r -> r.getType() == NotificationMessage.RecipientType.EMAIL),
                    "Email recipient should be included");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending application status notification with null application")
    void testSendApplicationStatusNotificationWithNullApplication() {
        // Arrange
        String previousStatus = ApplicationStatus.NEW.name();
        String newStatus = ApplicationStatus.PENDING.name();
        
        // Act
        boolean result = notificationService.sendApplicationStatusNotification(null, previousStatus, newStatus);
        
        // Assert
        assertFalse(result, "Notification should not be sent with null application");
        try {
            verify(notificationProducer, never()).publishStatusUpdate(anyString(), anyString(), anyMap(), anyList());
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending application status notification with messaging exception")
    void testSendApplicationStatusNotificationWithMessagingException() throws MessagingException {
        // Arrange
        String previousStatus = ApplicationStatus.NEW.name();
        String newStatus = ApplicationStatus.PENDING.name();
        
        // Mock NotificationProducer to throw MessagingException
        when(notificationProducer.publishStatusUpdate(anyString(), anyString(), anyMap(), anyList()))
                .thenThrow(new MessagingException("Test messaging exception", 
                        MessagingException.ErrorType.DELIVERY, 
                        org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR));
        
        // Act
        boolean result = notificationService.sendApplicationStatusNotification(testApplication, previousStatus, newStatus);
        
        // Assert
        assertFalse(result, "Notification should not be sent when MessagingException occurs");
    }

    @Test
    @DisplayName("Test sending application created notification successfully")
    void testSendApplicationCreatedNotification() {
        // Act
        boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
        
        // Assert
        assertTrue(result, "Notification should be sent successfully");
        try {
            verify(notificationProducer).publishNotification(
                    eq(NotificationMessage.NotificationType.APPLICATION_CREATED),
                    eq(NotificationMessage.NotificationPriority.HIGH),
                    payloadCaptor.capture(),
                    anyList());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertNotNull(payload, "Payload should not be null");
            assertEquals(testApplication.getId().toString(), payload.get("applicationId"), 
                    "Payload should contain correct application ID");
            assertEquals(testApplication.getStatus().name(), payload.get("status"), 
                    "Payload should contain correct status");
            assertNotNull(payload.get("createdAt"), "Payload should contain creation timestamp");
            
            // Verify merchant details are included
            assertNotNull(payload.get("merchant"), "Payload should contain merchant details");
            @SuppressWarnings("unchecked")
            Map<String, Object> merchantData = (Map<String, Object>) payload.get("merchant");
            assertEquals(testMerchantDetails.getLegalName(), merchantData.get("legalName"), 
                    "Merchant data should contain correct legal name");
            assertEquals(testMerchantDetails.getDbaName(), merchantData.get("dbaName"), 
                    "Merchant data should contain correct DBA name");
            assertEquals(testMerchantDetails.getIndustry(), merchantData.get("industry"), 
                    "Merchant data should contain correct industry");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending application approved notification successfully")
    void testSendApplicationApprovedNotification() {
        // Act
        boolean result = notificationService.sendApplicationApprovedNotification(testApplication);
        
        // Assert
        assertTrue(result, "Notification should be sent successfully");
        try {
            verify(notificationProducer).publishCompletionNotification(
                    eq(testApplication.getId().toString()),
                    eq("APPROVED"),
                    anyMap(),
                    anyList());
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending application rejected notification successfully")
    void testSendApplicationRejectedNotification() {
        // Arrange
        String rejectionReason = "Insufficient documentation provided";
        
        // Act
        boolean result = notificationService.sendApplicationRejectedNotification(testApplication, rejectionReason);
        
        // Assert
        assertTrue(result, "Notification should be sent successfully");
        try {
            verify(notificationProducer).publishCompletionNotification(
                    eq(testApplication.getId().toString()),
                    eq("REJECTED"),
                    payloadCaptor.capture(),
                    anyList());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertNotNull(payload, "Payload should not be null");
            assertEquals(rejectionReason, payload.get("reason"), 
                    "Payload should contain correct rejection reason");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending document uploaded notification successfully")
    void testSendDocumentUploadedNotification() {
        // Act
        boolean result = notificationService.sendDocumentUploadedNotification(testDocument, testApplication.getId());
        
        // Assert
        assertTrue(result, "Notification should be sent successfully");
        try {
            verify(notificationProducer).publishNotification(
                    eq(NotificationMessage.NotificationType.DOCUMENT_RECEIVED),
                    eq(NotificationMessage.NotificationPriority.MEDIUM),
                    payloadCaptor.capture(),
                    anyList());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertNotNull(payload, "Payload should not be null");
            assertEquals(testDocument.getId().toString(), payload.get("documentId"), 
                    "Payload should contain correct document ID");
            assertEquals(testDocument.getApplicationId().toString(), payload.get("applicationId"), 
                    "Payload should contain correct application ID");
            assertEquals(testDocument.getType().name(), payload.get("documentType"), 
                    "Payload should contain correct document type");
            assertEquals(testDocument.getClassification().name(), payload.get("classification"), 
                    "Payload should contain correct classification");
            assertEquals(testDocument.getConfidenceScore(), payload.get("confidenceScore"), 
                    "Payload should contain correct confidence score");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending document processed notification successfully")
    void testSendDocumentProcessedNotification() {
        // Arrange
        Map<String, Object> extractionResults = new HashMap<>();
        extractionResults.put("accountNumber", "*****1234");
        extractionResults.put("bankName", "Test Bank");
        extractionResults.put("statementDate", "2023-01-15");
        extractionResults.put("accountBalance", 12345.67);
        
        // Act
        boolean result = notificationService.sendDocumentProcessedNotification(
                testDocument, testApplication.getId(), extractionResults);
        
        // Assert
        assertTrue(result, "Notification should be sent successfully");
        try {
            verify(notificationProducer).publishNotification(
                    eq(NotificationMessage.NotificationType.DOCUMENT_PROCESSED),
                    eq(NotificationMessage.NotificationPriority.MEDIUM),
                    payloadCaptor.capture(),
                    anyList());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertNotNull(payload, "Payload should not be null");
            assertEquals(testDocument.getId().toString(), payload.get("documentId"), 
                    "Payload should contain correct document ID");
            assertEquals(testDocument.getApplicationId().toString(), payload.get("applicationId"), 
                    "Payload should contain correct application ID");
            
            // Verify extraction results are included
            assertNotNull(payload.get("extractionResults"), "Payload should contain extraction results");
            @SuppressWarnings("unchecked")
            Map<String, Object> results = (Map<String, Object>) payload.get("extractionResults");
            assertEquals("*****1234", results.get("accountNumber"), 
                    "Extraction results should contain correct account number");
            assertEquals("Test Bank", results.get("bankName"), 
                    "Extraction results should contain correct bank name");
            assertEquals("2023-01-15", results.get("statementDate"), 
                    "Extraction results should contain correct statement date");
            assertEquals(12345.67, results.get("accountBalance"), 
                    "Extraction results should contain correct account balance");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending system event notification successfully")
    void testSendSystemEventNotification() {
        // Arrange
        EventType eventType = EventType.APPLICATION_APPROVED;
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", testApplication.getId().toString());
        payload.put("approvedBy", "test-user");
        payload.put("approvedAt", LocalDateTime.now().toString());
        
        // Act
        boolean result = notificationService.sendSystemEventNotification(eventType, payload);
        
        // Assert
        assertTrue(result, "Notification should be sent successfully");
        try {
            verify(notificationProducer).publishNotification(
                    eq(NotificationMessage.NotificationType.SYSTEM),
                    any(NotificationMessage.NotificationPriority.class),
                    payloadCaptor.capture(),
                    anyList());
            
            Map<String, Object> capturedPayload = payloadCaptor.getValue();
            assertNotNull(capturedPayload, "Payload should not be null");
            assertEquals(eventType.name(), capturedPayload.get("eventType"), 
                    "Payload should contain correct event type");
            assertNotNull(capturedPayload.get("eventId"), "Payload should contain event ID");
            assertNotNull(capturedPayload.get("timestamp"), "Payload should contain timestamp");
            
            // Verify custom payload is included
            assertNotNull(capturedPayload.get("data"), "Payload should contain data");
            @SuppressWarnings("unchecked")
            Map<String, Object> data = (Map<String, Object>) capturedPayload.get("data");
            assertEquals(testApplication.getId().toString(), data.get("applicationId"), 
                    "Data should contain correct application ID");
            assertEquals("test-user", data.get("approvedBy"), 
                    "Data should contain correct approvedBy value");
            assertNotNull(data.get("approvedAt"), "Data should contain approvedAt timestamp");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test sending system event notification with null event type")
    void testSendSystemEventNotificationWithNullEventType() {
        // Arrange
        Map<String, Object> payload = new HashMap<>();
        payload.put("applicationId", testApplication.getId().toString());
        
        // Act
        boolean result = notificationService.sendSystemEventNotification(null, payload);
        
        // Assert
        assertFalse(result, "Notification should not be sent with null event type");
        try {
            verify(notificationProducer, never()).publishNotification(
                    any(NotificationMessage.NotificationType.class),
                    any(NotificationMessage.NotificationPriority.class),
                    anyMap(),
                    anyList());
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test getting notification template successfully")
    void testGetNotificationTemplate() {
        // Act
        String template = notificationService.getNotificationTemplate("application-status-change");
        
        // Assert
        assertNotNull(template, "Template should not be null");
        assertEquals(testTemplateContent, template, "Template content should match expected content");
    }

    @Test
    @DisplayName("Test getting notification template with null template name")
    void testGetNotificationTemplateWithNullTemplateName() {
        // Act
        String template = notificationService.getNotificationTemplate(null);
        
        // Assert
        assertNull(template, "Template should be null for null template name");
    }

    @Test
    @DisplayName("Test getting notification template with non-existent template")
    void testGetNotificationTemplateWithNonExistentTemplate() throws IOException {
        // Arrange
        when(mockResource.exists()).thenReturn(false);
        
        // Act
        String template = notificationService.getNotificationTemplate("non-existent-template");
        
        // Assert
        assertNull(template, "Template should be null for non-existent template");
    }

    @Test
    @DisplayName("Test refreshing notification templates")
    void testRefreshNotificationTemplates() {
        // Act
        notificationService.refreshNotificationTemplates(null);
        
        // Assert - verify that templates are reloaded
        try {
            verify(resourceLoader, atLeastOnce()).getResource(contains("templates/notifications/"));
        } catch (Exception e) {
            fail("Should not throw exception: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test refreshing specific notification template")
    void testRefreshSpecificNotificationTemplate() {
        // Arrange
        String templateName = "application-status-change";
        
        // Act
        notificationService.refreshNotificationTemplates(templateName);
        
        // Assert - verify that specific template is reloaded
        try {
            verify(resourceLoader).getResource(contains("templates/notifications/" + templateName));
        } catch (Exception e) {
            fail("Should not throw exception: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test tracking notification delivery status")
    void testTrackNotificationDeliveryStatus() {
        // Arrange
        String notificationId = "test-notification-id";
        String status = "DELIVERED";
        Map<String, Object> details = new HashMap<>();
        details.put("deliveredAt", LocalDateTime.now().toString());
        details.put("recipientType", "WEBHOOK");
        details.put("recipientAddress", "https://example.com/webhook");
        
        // Act
        notificationService.trackNotificationDeliveryStatus(notificationId, status, details);
        
        // Assert - verify that status is tracked correctly
        // This is an internal state change, so we can't directly verify it
        // We would need to expose a method to retrieve the status for testing
    }

    @Test
    @DisplayName("Test tracking notification delivery status with null notification ID")
    void testTrackNotificationDeliveryStatusWithNullNotificationId() {
        // Arrange
        String status = "DELIVERED";
        Map<String, Object> details = new HashMap<>();
        
        // Act - should not throw exception
        notificationService.trackNotificationDeliveryStatus(null, status, details);
        
        // No assertion needed - method should simply return without error
    }

    @Test
    @DisplayName("Test retrying failed notification")
    void testRetryFailedNotification() {
        // Arrange
        String notificationId = "test-notification-id";
        int maxAttempts = 3;
        
        // Set up notification status map with a failed notification
        Map<String, Object> statusEntry = new HashMap<>();
        statusEntry.put("status", "FAILED");
        statusEntry.put("attemptCount", 1);
        statusEntry.put("lastAttemptAt", LocalDateTime.now().minusMinutes(5).toString());
        statusEntry.put("errorMessage", "Connection refused");
        
        // Use reflection to access and modify the private notificationStatusMap
        @SuppressWarnings("unchecked")
        Map<String, Map<String, Object>> statusMap = (Map<String, Map<String, Object>>) 
                ReflectionTestUtils.getField(notificationService, "notificationStatusMap");
        statusMap.put(notificationId, statusEntry);
        
        // Act
        boolean result = notificationService.retryFailedNotification(notificationId, maxAttempts);
        
        // Assert
        assertTrue(result, "Retry should be successful");
        
        // Verify status is updated to RETRYING
        assertEquals("RETRYING", statusMap.get(notificationId).get("status"), 
                "Status should be updated to RETRYING");
        
        // Verify attempt count is incremented
        assertEquals(2, statusMap.get(notificationId).get("attemptCount"), 
                "Attempt count should be incremented");
        
        // Verify lastRetryAt is updated
        assertNotNull(statusMap.get(notificationId).get("lastRetryAt"), 
                "lastRetryAt should be updated");
    }

    @Test
    @DisplayName("Test retrying failed notification with max attempts reached")
    void testRetryFailedNotificationWithMaxAttemptsReached() {
        // Arrange
        String notificationId = "test-notification-id";
        int maxAttempts = 3;
        
        // Set up notification status map with a failed notification that has reached max attempts
        Map<String, Object> statusEntry = new HashMap<>();
        statusEntry.put("status", "FAILED");
        statusEntry.put("attemptCount", 3);
        statusEntry.put("lastAttemptAt", LocalDateTime.now().minusMinutes(5).toString());
        statusEntry.put("errorMessage", "Connection refused");
        
        // Use reflection to access and modify the private notificationStatusMap
        @SuppressWarnings("unchecked")
        Map<String, Map<String, Object>> statusMap = (Map<String, Map<String, Object>>) 
                ReflectionTestUtils.getField(notificationService, "notificationStatusMap");
        statusMap.put(notificationId, statusEntry);
        
        // Act
        boolean result = notificationService.retryFailedNotification(notificationId, maxAttempts);
        
        // Assert
        assertFalse(result, "Retry should fail when max attempts reached");
        
        // Verify status is not updated
        assertEquals("FAILED", statusMap.get(notificationId).get("status"), 
                "Status should remain FAILED");
        
        // Verify attempt count is not incremented
        assertEquals(3, statusMap.get(notificationId).get("attemptCount"), 
                "Attempt count should not be incremented");
    }

    @Test
    @DisplayName("Test retrying notification with non-failed status")
    void testRetryNotificationWithNonFailedStatus() {
        // Arrange
        String notificationId = "test-notification-id";
        int maxAttempts = 3;
        
        // Set up notification status map with a delivered notification
        Map<String, Object> statusEntry = new HashMap<>();
        statusEntry.put("status", "DELIVERED");
        statusEntry.put("attemptCount", 1);
        statusEntry.put("deliveredAt", LocalDateTime.now().minusMinutes(5).toString());
        
        // Use reflection to access and modify the private notificationStatusMap
        @SuppressWarnings("unchecked")
        Map<String, Map<String, Object>> statusMap = (Map<String, Map<String, Object>>) 
                ReflectionTestUtils.getField(notificationService, "notificationStatusMap");
        statusMap.put(notificationId, statusEntry);
        
        // Act
        boolean result = notificationService.retryFailedNotification(notificationId, maxAttempts);
        
        // Assert
        assertFalse(result, "Retry should fail for non-failed notification");
        
        // Verify status is not updated
        assertEquals("DELIVERED", statusMap.get(notificationId).get("status"), 
                "Status should remain DELIVERED");
    }

    @Test
    @DisplayName("Test retrying unknown notification")
    void testRetryUnknownNotification() {
        // Arrange
        String notificationId = "unknown-notification-id";
        int maxAttempts = 3;
        
        // Act
        boolean result = notificationService.retryFailedNotification(notificationId, maxAttempts);
        
        // Assert
        assertFalse(result, "Retry should fail for unknown notification");
    }

    @Test
    @DisplayName("Test error handling in notification delivery")
    void testErrorHandlingInNotificationDelivery() throws MessagingException {
        // Arrange
        when(notificationProducer.publishStatusUpdate(anyString(), anyString(), anyMap(), anyList()))
                .thenThrow(new RuntimeException("Unexpected error"));
        
        // Act
        boolean result = notificationService.sendApplicationStatusNotification(
                testApplication, ApplicationStatus.NEW.name(), ApplicationStatus.PENDING.name());
        
        // Assert
        assertFalse(result, "Notification should not be sent when unexpected error occurs");
    }

    @Test
    @DisplayName("Test notification delivery with disabled channels")
    void testNotificationDeliveryWithDisabledChannels() {
        // Arrange - disable webhook and email channels
        ReflectionTestUtils.setField(notificationService, "webhookEnabled", false);
        ReflectionTestUtils.setField(notificationService, "emailEnabled", false);
        
        // Act
        boolean result = notificationService.sendApplicationStatusNotification(
                testApplication, ApplicationStatus.NEW.name(), ApplicationStatus.PENDING.name());
        
        // Assert
        assertTrue(result, "Notification should be sent successfully even with disabled channels");
        try {
            verify(notificationProducer).publishStatusUpdate(
                    eq(testApplication.getId().toString()),
                    eq(ApplicationStatus.PENDING.name()),
                    anyMap(),
                    recipientsCaptor.capture());
            
            List<NotificationMessage.Recipient> recipients = recipientsCaptor.getValue();
            assertNotNull(recipients, "Recipients list should not be null");
            assertTrue(recipients.isEmpty(), "Recipients list should be empty when channels are disabled");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Test notification template loading with IO exception")
    void testNotificationTemplateLoadingWithIOException() throws IOException {
        // Arrange
        when(mockResource.getInputStream()).thenThrow(new IOException("Test IO exception"));
        
        // Act
        String template = notificationService.getNotificationTemplate("application-status-change");
        
        // Assert
        assertNull(template, "Template should be null when IO exception occurs");
    }

    @Test
    @DisplayName("Test notification delivery with null merchant details")
    void testNotificationDeliveryWithNullMerchantDetails() {
        // Arrange
        testApplication.setMerchantDetails(null);
        
        // Act
        boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
        
        // Assert
        assertTrue(result, "Notification should be sent successfully even with null merchant details");
        try {
            verify(notificationProducer).publishNotification(
                    eq(NotificationMessage.NotificationType.APPLICATION_CREATED),
                    eq(NotificationMessage.NotificationPriority.HIGH),
                    payloadCaptor.capture(),
                    anyList());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertNotNull(payload, "Payload should not be null");
            assertFalse(payload.containsKey("merchant"), "Payload should not contain merchant details when null");
            
        } catch (MessagingException e) {
            fail("Should not throw MessagingException: " + e.getMessage());
        }
    }
}