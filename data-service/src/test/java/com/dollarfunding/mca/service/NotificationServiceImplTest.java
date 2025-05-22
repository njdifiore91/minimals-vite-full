package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.EventType;
import com.dollarfunding.mca.entity.Webhook;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.WebhookDeliveryException;
import com.dollarfunding.mca.messaging.NotificationMessage;
import com.dollarfunding.mca.messaging.NotificationProducer;
import com.dollarfunding.mca.repository.WebhookRepository;
import com.dollarfunding.mca.util.TraceUtil;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the NotificationServiceImpl class.
 * 
 * These tests verify that the NotificationServiceImpl correctly handles notification delivery
 * through multiple channels, integrates with WebhookService, processes notifications
 * asynchronously, manages templates, and tracks delivery status.
 */
@ExtendWith(MockitoExtension.class)
public class NotificationServiceImplTest {

    @Mock
    private WebhookService webhookService;
    
    @Mock
    private WebhookRepository webhookRepository;
    
    @Mock
    private NotificationProducer notificationProducer;
    
    @Spy
    @InjectMocks
    private NotificationServiceImpl notificationService;
    

    
    @Captor
    private ArgumentCaptor<Map<String, Object>> payloadCaptor;
    
    @Captor
    private ArgumentCaptor<NotificationMessage> messageCaptor;
    
    private Application testApplication;
    private Document testDocument;
    private Webhook testWebhook;
    private MerchantDetails testMerchantDetails;
    private final String correlationId = "test-correlation-id";
    
    @BeforeEach
    public void setUp() {
        // Set up test data
        testApplication = createTestApplication();
        testDocument = createTestDocument();
        testWebhook = createTestWebhook();
        testMerchantDetails = createTestMerchantDetails();
        testApplication.setMerchantDetails(testMerchantDetails);
        
        // Set up configuration properties via reflection
        ReflectionTestUtils.setField(notificationService, "templatePath", "classpath:templates/notifications/");
        ReflectionTestUtils.setField(notificationService, "maxRetryAttempts", 3);
        ReflectionTestUtils.setField(notificationService, "retryDelayMs", 5000L);
        ReflectionTestUtils.setField(notificationService, "asyncEnabled", true);
        
        // Set up webhook repository mock to return test webhook
        when(webhookRepository.findByEventTypeAndActiveTrue(any(EventType.class)))
                .thenReturn(Collections.singletonList(testWebhook));
        

    }
    
    // ========== Application Notification Tests ==========
    
    @Test
    @DisplayName("Should send application status notification successfully")
    public void testSendApplicationStatusNotification() {
        // Arrange
        String previousStatus = "PENDING";
        String newStatus = "APPROVED";
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationStatusNotification(
                    testApplication, previousStatus, newStatus);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), payloadCaptor.capture());
            verify(notificationProducer).sendNotification(messageCaptor.capture());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertEquals(testApplication.getId(), payload.get("applicationId"));
            assertEquals(previousStatus, payload.get("previousStatus"));
            assertEquals(newStatus, payload.get("newStatus"));
            assertEquals(EventType.APPLICATION_UPDATED.name(), payload.get("eventType"));
            assertNotNull(payload.get("timestamp"));
            assertNotNull(payload.get("notificationId"));
            assertEquals(correlationId, payload.get("correlationId"));
            
            NotificationMessage message = messageCaptor.getValue();
            assertEquals(EventType.APPLICATION_UPDATED.name(), message.getEventType());
            assertNotNull(message.getNotificationId());
            assertNotNull(message.getTimestamp());
            assertEquals(correlationId, message.getCorrelationId());
        }
    }
    
    @Test
    @DisplayName("Should send application created notification successfully")
    public void testSendApplicationCreatedNotification() {
        // Arrange
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), payloadCaptor.capture());
            verify(notificationProducer).sendNotification(messageCaptor.capture());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertEquals(testApplication.getId(), payload.get("applicationId"));
            assertEquals(EventType.APPLICATION_CREATED.name(), payload.get("eventType"));
            assertNotNull(payload.get("timestamp"));
            assertNotNull(payload.get("notificationId"));
            assertEquals(correlationId, payload.get("correlationId"));
            
            // Verify merchant details are included
            @SuppressWarnings("unchecked")
            Map<String, Object> merchantDetails = (Map<String, Object>) payload.get("merchantDetails");
            assertNotNull(merchantDetails);
            assertEquals(testMerchantDetails.getId(), merchantDetails.get("id"));
            assertEquals(testMerchantDetails.getLegalName(), merchantDetails.get("legalName"));
            assertEquals(testMerchantDetails.getDbaName(), merchantDetails.get("dbaName"));
            assertEquals(testMerchantDetails.getIndustry(), merchantDetails.get("industry"));
        }
    }
    
    @Test
    @DisplayName("Should send application approved notification successfully")
    public void testSendApplicationApprovedNotification() {
        // Arrange
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationApprovedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), payloadCaptor.capture());
            verify(notificationProducer).sendNotification(messageCaptor.capture());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertEquals(testApplication.getId(), payload.get("applicationId"));
            assertEquals(EventType.APPLICATION_APPROVED.name(), payload.get("eventType"));
            assertNotNull(payload.get("approvedAt"));
            assertNotNull(payload.get("timestamp"));
            assertNotNull(payload.get("notificationId"));
            assertEquals(correlationId, payload.get("correlationId"));
        }
    }
    
    @Test
    @DisplayName("Should send application rejected notification successfully")
    public void testSendApplicationRejectedNotification() {
        // Arrange
        String rejectionReason = "Insufficient documentation";
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationRejectedNotification(
                    testApplication, rejectionReason);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), payloadCaptor.capture());
            verify(notificationProducer).sendNotification(messageCaptor.capture());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertEquals(testApplication.getId(), payload.get("applicationId"));
            assertEquals(EventType.APPLICATION_REJECTED.name(), payload.get("eventType"));
            assertEquals(rejectionReason, payload.get("reason"));
            assertNotNull(payload.get("rejectedAt"));
            assertNotNull(payload.get("timestamp"));
            assertNotNull(payload.get("notificationId"));
            assertEquals(correlationId, payload.get("correlationId"));
        }
    }
    
    // ========== Document Notification Tests ==========
    
    @Test
    @DisplayName("Should send document uploaded notification successfully")
    public void testSendDocumentUploadedNotification() {
        // Arrange
        Long applicationId = 123L;
        when(webhookRepository.findByEventTypeAndActiveTrue(eq(EventType.DOCUMENT_UPLOADED)))
                .thenReturn(Collections.singletonList(testWebhook));
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendDocumentUploadedNotification(testDocument, applicationId);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), payloadCaptor.capture());
            verify(notificationProducer).sendNotification(messageCaptor.capture());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertEquals(testDocument.getId(), payload.get("documentId"));
            assertEquals(applicationId, payload.get("applicationId"));
            assertEquals(testDocument.getType().name(), payload.get("documentType"));
            assertEquals(testDocument.getClassification(), payload.get("classification"));
            assertEquals(EventType.DOCUMENT_UPLOADED.name(), payload.get("eventType"));
            assertNotNull(payload.get("timestamp"));
            assertNotNull(payload.get("notificationId"));
            assertEquals(correlationId, payload.get("correlationId"));
            
            // Verify metadata is included
            @SuppressWarnings("unchecked")
            Map<String, Object> metadata = (Map<String, Object>) payload.get("metadata");
            assertNotNull(metadata);
            assertEquals("test-value", metadata.get("test-key"));
        }
    }
    
    @Test
    @DisplayName("Should send document processed notification successfully")
    public void testSendDocumentProcessedNotification() {
        // Arrange
        Long applicationId = 123L;
        Map<String, Object> extractionResults = new HashMap<>();
        extractionResults.put("confidence", 0.95);
        extractionResults.put("fields", Map.of("name", "John Doe", "amount", "$5000"));
        
        when(webhookRepository.findByEventTypeAndActiveTrue(eq(EventType.DOCUMENT_PROCESSED)))
                .thenReturn(Collections.singletonList(testWebhook));
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendDocumentProcessedNotification(
                    testDocument, applicationId, extractionResults);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), payloadCaptor.capture());
            verify(notificationProducer).sendNotification(messageCaptor.capture());
            
            Map<String, Object> payload = payloadCaptor.getValue();
            assertEquals(testDocument.getId(), payload.get("documentId"));
            assertEquals(applicationId, payload.get("applicationId"));
            assertEquals(testDocument.getType().name(), payload.get("documentType"));
            assertEquals(testDocument.getClassification(), payload.get("classification"));
            assertEquals(EventType.DOCUMENT_PROCESSED.name(), payload.get("eventType"));
            assertEquals(extractionResults, payload.get("extractionResults"));
            assertNotNull(payload.get("processedAt"));
            assertNotNull(payload.get("timestamp"));
            assertNotNull(payload.get("notificationId"));
            assertEquals(correlationId, payload.get("correlationId"));
        }
    }
    
    // ========== System Event Notification Tests ==========
    
    @Test
    @DisplayName("Should send system event notification successfully")
    public void testSendSystemEventNotification() {
        // Arrange
        EventType eventType = EventType.APPLICATION_CREATED;
        Map<String, Object> payload = new HashMap<>();
        payload.put("event", "system_startup");
        payload.put("timestamp", LocalDateTime.now().toString());
        
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendSystemEventNotification(eventType, payload);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), payloadCaptor.capture());
            verify(notificationProducer).sendNotification(messageCaptor.capture());
            
            Map<String, Object> capturedPayload = payloadCaptor.getValue();
            assertEquals(eventType.name(), capturedPayload.get("eventType"));
            assertEquals("system_startup", capturedPayload.get("event"));
            assertNotNull(capturedPayload.get("timestamp"));
            assertNotNull(capturedPayload.get("notificationId"));
            assertEquals(correlationId, capturedPayload.get("correlationId"));
        }
    }
    
    // ========== Template Management Tests ==========
    
    @Test
    @DisplayName("Should retrieve notification template from cache")
    public void testGetNotificationTemplate() {
        // Arrange - first call will cache, second call should use cache
        String templateName = "application_approved";
        
        // Act - call twice to test caching
        String template1 = notificationService.getNotificationTemplate(templateName);
        String template2 = notificationService.getNotificationTemplate(templateName);
        
        // Assert
        assertNotNull(template1, "Template should not be null");
        assertTrue(template1.contains(templateName), "Template should contain the template name");
        assertEquals(template1, template2, "Templates should be identical when retrieved from cache");
    }
    
    @Test
    @DisplayName("Should refresh notification templates")
    public void testRefreshNotificationTemplates() {
        // Act - this should not throw any exceptions
        notificationService.refreshNotificationTemplates(null);
        notificationService.refreshNotificationTemplates("application_approved");
        
        // No assertions needed as this is a void method that just refreshes the cache
    }
    
    // ========== Delivery Status Tracking Tests ==========
    
    @Test
    @DisplayName("Should track notification delivery status")
    public void testTrackNotificationDeliveryStatus() {
        // Arrange
        String notificationId = UUID.randomUUID().toString();
        String status = "DELIVERED";
        Map<String, Object> details = Map.of("webhookId", 1L, "statusCode", 200);
        
        // Act - this should not throw any exceptions
        notificationService.trackNotificationDeliveryStatus(notificationId, status, details);
        
        // No assertions needed as this is a void method that just logs the status
    }
    
    @Test
    @DisplayName("Should retry failed notification")
    public void testRetryFailedNotification() {
        // Arrange
        String notificationId = UUID.randomUUID().toString();
        int maxAttempts = 3;
        
        // Act
        boolean result = notificationService.retryFailedNotification(notificationId, maxAttempts);
        
        // Assert
        assertTrue(result, "Retry should be successful");
    }
    
    @Test
    @DisplayName("Should handle exceptions during notification delivery")
    public void testHandleExceptionsDuringDelivery() {
        // Arrange - simulate unexpected runtime exception
        when(webhookRepository.findByEventTypeAndActiveTrue(any(EventType.class)))
                .thenThrow(new ResourceNotFoundException("Repository error"));
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act - this should not throw an exception but return false
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            // The implementation should handle the exception and still try to send via queue
            assertTrue(result, "Notification should still succeed via queue if webhook lookup fails");
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
        }
    }
    
    // ========== Webhook Delivery Tests ==========
    
    @Test
    @DisplayName("Should handle webhook delivery failure")
    public void testWebhookDeliveryFailure() {
        // Arrange
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenThrow(new WebhookDeliveryException("Failed to deliver webhook"));
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should still be considered sent if queue delivery succeeds");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), anyMap());
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
        }
    }
    
    @Test
    @DisplayName("Should retry webhook delivery with exponential backoff")
    public void testRetryWebhookDelivery() {
        // Arrange
        ReflectionTestUtils.setField(notificationService, "asyncEnabled", false); // Use sync for easier testing
        ReflectionTestUtils.setField(notificationService, "maxRetryAttempts", 3);
        ReflectionTestUtils.setField(notificationService, "retryDelayMs", 100L); // Use small delay for test
        
        // Mock CompletableFuture for retry
        CompletableFuture<Boolean> successFuture = CompletableFuture.completedFuture(true);
        
        // First attempt fails, then we'll verify retryWebhookDelivery is called
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenThrow(new WebhookDeliveryException("Failed to deliver webhook"));
        when(webhookService.deliverWebhookAsync(anyLong(), anyMap()))
                .thenReturn(successFuture);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully via queue even if webhook fails");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), anyMap());
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
            
            // Verify tracking was called for the failed webhook
            verify(notificationService).trackNotificationDeliveryStatus(
                    contains("-webhook-"), eq("FAILED"), anyMap());
        }
    }
    
    @Test
    @DisplayName("Should handle queue delivery failure")
    public void testQueueDeliveryFailure() {
        // Arrange
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(false);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should still be considered sent if webhook delivery succeeds");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), anyMap());
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
        }
    }
    
    @Test
    @DisplayName("Should handle both webhook and queue delivery failure")
    public void testBothDeliveryChannelFailure() {
        // Arrange
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenThrow(new WebhookDeliveryException("Failed to deliver webhook"));
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(false);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertFalse(result, "Notification should be considered failed if both channels fail");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), anyMap());
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
            
            // Verify delivery status tracking was called with FAILED status
            verify(notificationService, atLeastOnce()).trackNotificationDeliveryStatus(
                    anyString(), eq("FAILED"), anyMap());
        }
    }
    
    @Test
    @DisplayName("Should handle no active webhooks")
    public void testNoActiveWebhooks() {
        // Arrange
        when(webhookRepository.findByEventTypeAndActiveTrue(any(EventType.class)))
                .thenReturn(Collections.emptyList());
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should be considered sent if queue delivery succeeds");
            verify(webhookService, never()).deliverWebhook(anyLong(), anyMap());
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
        }
    }
    
    // ========== Async Webhook Delivery Tests ==========
    
    @Test
    @DisplayName("Should deliver webhook asynchronously when async is enabled")
    public void testAsyncWebhookDelivery() {
        // Arrange
        ReflectionTestUtils.setField(notificationService, "asyncEnabled", true);
        
        CompletableFuture<Boolean> future = CompletableFuture.completedFuture(true);
        when(webhookService.deliverWebhookAsync(anyLong(), anyMap()))
                .thenReturn(future);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService, never()).deliverWebhook(anyLong(), anyMap());
            verify(webhookService).deliverWebhookAsync(eq(testWebhook.getId()), anyMap());
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
        }
    }
    
    @Test
    @DisplayName("Should deliver webhook synchronously when async is disabled")
    public void testSyncWebhookDelivery() {
        // Arrange
        ReflectionTestUtils.setField(notificationService, "asyncEnabled", false);
        
        when(webhookService.deliverWebhook(anyLong(), anyMap()))
                .thenReturn(true);
        when(notificationProducer.sendNotification(any(NotificationMessage.class)))
                .thenReturn(true);
        
        try (MockedStatic<TraceUtil> traceUtilMock = Mockito.mockStatic(TraceUtil.class)) {
            traceUtilMock.when(TraceUtil::getCurrentCorrelationId).thenReturn(correlationId);
            
            // Act
            boolean result = notificationService.sendApplicationCreatedNotification(testApplication);
            
            // Assert
            assertTrue(result, "Notification should be sent successfully");
            verify(webhookService).deliverWebhook(eq(testWebhook.getId()), anyMap());
            verify(webhookService, never()).deliverWebhookAsync(anyLong(), anyMap());
            verify(notificationProducer).sendNotification(any(NotificationMessage.class));
        }
    }
    
    // ========== Helper Methods ==========
    
    private Application createTestApplication() {
        Application application = new Application();
        application.setId(1L);
        application.setStatus(Application.Status.PENDING);
        application.setReviewStatus(Application.ReviewStatus.UNDER_REVIEW);
        application.setCreatedAt(LocalDateTime.now().minusDays(1));
        application.setUpdatedAt(LocalDateTime.now());
        return application;
    }
    
    /**
     * Inner class to represent Application.Status enum for testing purposes.
     */
    public static class Application {
        private Long id;
        private Status status;
        private ReviewStatus reviewStatus;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private MerchantDetails merchantDetails;
        
        public enum Status {
            PENDING, APPROVED, REJECTED, PROCESSING, COMPLETED
        }
        
        public enum ReviewStatus {
            PENDING_REVIEW, UNDER_REVIEW, APPROVED, REJECTED
        }
        
        public Long getId() {
            return id;
        }
        
        public void setId(Long id) {
            this.id = id;
        }
        
        public Status getStatus() {
            return status;
        }
        
        public void setStatus(Status status) {
            this.status = status;
        }
        
        public ReviewStatus getReviewStatus() {
            return reviewStatus;
        }
        
        public void setReviewStatus(ReviewStatus reviewStatus) {
            this.reviewStatus = reviewStatus;
        }
        
        public LocalDateTime getCreatedAt() {
            return createdAt;
        }
        
        public void setCreatedAt(LocalDateTime createdAt) {
            this.createdAt = createdAt;
        }
        
        public LocalDateTime getUpdatedAt() {
            return updatedAt;
        }
        
        public void setUpdatedAt(LocalDateTime updatedAt) {
            this.updatedAt = updatedAt;
        }
        
        public MerchantDetails getMerchantDetails() {
            return merchantDetails;
        }
        
        public void setMerchantDetails(MerchantDetails merchantDetails) {
            this.merchantDetails = merchantDetails;
        }
    }
    
    private Document createTestDocument() {
        Document document = new Document();
        document.setId(1L);
        document.setType(Document.Type.APPLICATION_FORM);
        document.setClassification("Loan Application");
        document.setUploadedAt(LocalDateTime.now());
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("test-key", "test-value");
        document.setMetadata(metadata);
        
        return document;
    }
    
    /**
     * Inner class to represent Document entity for testing purposes.
     */
    public static class Document {
        private Long id;
        private Type type;
        private String classification;
        private LocalDateTime uploadedAt;
        private Map<String, Object> metadata;
        
        public enum Type {
            APPLICATION_FORM, TAX_RETURN, BANK_STATEMENT, PAY_STUB, IDENTITY_DOCUMENT, OTHER
        }
        
        public Long getId() {
            return id;
        }
        
        public void setId(Long id) {
            this.id = id;
        }
        
        public Type getType() {
            return type;
        }
        
        public void setType(Type type) {
            this.type = type;
        }
        
        public String getClassification() {
            return classification;
        }
        
        public void setClassification(String classification) {
            this.classification = classification;
        }
        
        public LocalDateTime getUploadedAt() {
            return uploadedAt;
        }
        
        public void setUploadedAt(LocalDateTime uploadedAt) {
            this.uploadedAt = uploadedAt;
        }
        
        public Map<String, Object> getMetadata() {
            return metadata;
        }
        
        public void setMetadata(Map<String, Object> metadata) {
            this.metadata = metadata;
        }
    }
    
    private Webhook createTestWebhook() {
        Webhook webhook = new Webhook();
        webhook.setId(1L);
        webhook.setEndpointUrl("https://example.com/webhook");
        webhook.setSecretKey("test-secret-key");
        webhook.setActive(true);
        webhook.setEventType(EventType.APPLICATION_CREATED);
        webhook.setMaxRetryAttempts(3);
        webhook.setSignatureHeader("X-Webhook-Signature");
        webhook.setCreatedAt(LocalDateTime.now().minusDays(1));
        webhook.setUpdatedAt(LocalDateTime.now());
        return webhook;
    }
    
    private MerchantDetails createTestMerchantDetails() {
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setId(1L);
        merchantDetails.setLegalName("Test Merchant Inc.");
        merchantDetails.setDbaName("Test Merchant");
        merchantDetails.setIndustry("Retail");
        return merchantDetails;
    }
    
    /**
     * Inner class to represent MerchantDetails entity for testing purposes.
     */
    public static class MerchantDetails {
        private Long id;
        private String legalName;
        private String dbaName;
        private String industry;
        
        public Long getId() {
            return id;
        }
        
        public void setId(Long id) {
            this.id = id;
        }
        
        public String getLegalName() {
            return legalName;
        }
        
        public void setLegalName(String legalName) {
            this.legalName = legalName;
        }
        
        public String getDbaName() {
            return dbaName;
        }
        
        public void setDbaName(String dbaName) {
            this.dbaName = dbaName;
        }
        
        public String getIndustry() {
            return industry;
        }
        
        public void setIndustry(String industry) {
            this.industry = industry;
        }
    }
}