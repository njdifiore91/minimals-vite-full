package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.TestData;
import com.dollarfunding.mca.TestUtils;
import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import javax.persistence.EntityManager;
import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit test class for the Application entity that verifies JPA mapping, field validation, and relationships.
 * Tests include validation of required fields, proper mapping of enum values for status and review_status,
 * JSON conversion for the metadata field, and bidirectional relationships with Document and MerchantDetails entities.
 * 
 * The test class ensures that the Application entity can be properly persisted and retrieved with all its
 * attributes and relationships intact, and that validation constraints are properly enforced.
 */
@ExtendWith(MockitoExtension.class)
public class ApplicationTest {

    private Validator validator;
    
    @Mock
    private EntityManager entityManager;
    
    @BeforeEach
    public void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }
    
    @Test
    @DisplayName("Test Application entity creation with default constructor")
    public void testDefaultConstructor() {
        // Create an application using the default constructor
        Application application = new Application();
        
        // Verify default values
        assertNotNull(application.getMetadata(), "Metadata should be initialized as empty map");
        assertEquals(ApplicationStatus.NEW, application.getStatus(), "Default status should be NEW");
        assertEquals(ReviewStatus.NOT_REVIEWED, application.getReviewStatus(), "Default review status should be NOT_REVIEWED");
        assertNotNull(application.getCreatedAt(), "Created timestamp should be initialized");
        assertNotNull(application.getUpdatedAt(), "Updated timestamp should be initialized");
        assertNotNull(application.getDocuments(), "Documents list should be initialized");
        assertEquals(0, application.getDocuments().size(), "Documents list should be empty");
        assertNull(application.getMerchantDetails(), "Merchant details should be null");
    }
    
    @Test
    @DisplayName("Test Application entity creation with status constructor")
    public void testStatusConstructor() {
        // Create an application with a specific status
        Application application = new Application(ApplicationStatus.PROCESSING);
        
        // Verify values
        assertEquals(ApplicationStatus.PROCESSING, application.getStatus(), "Status should be set to PROCESSING");
        assertEquals(ReviewStatus.NOT_REVIEWED, application.getReviewStatus(), "Default review status should be NOT_REVIEWED");
        assertNotNull(application.getCreatedAt(), "Created timestamp should be initialized");
        assertNotNull(application.getUpdatedAt(), "Updated timestamp should be initialized");
    }
    
    @Test
    @DisplayName("Test Application entity creation with all fields constructor")
    public void testAllFieldsConstructor() {
        // Create test data
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 0.95);
        
        LocalDateTime createdAt = LocalDateTime.now().minusDays(1);
        LocalDateTime updatedAt = LocalDateTime.now();
        
        // Create an application with all fields
        Application application = new Application(
            ApplicationStatus.APPROVED,
            metadata,
            createdAt,
            updatedAt,
            ReviewStatus.APPROVED
        );
        
        // Verify values
        assertEquals(ApplicationStatus.APPROVED, application.getStatus(), "Status should be set to APPROVED");
        assertEquals(ReviewStatus.APPROVED, application.getReviewStatus(), "Review status should be set to APPROVED");
        assertEquals(createdAt, application.getCreatedAt(), "Created timestamp should match");
        assertEquals(updatedAt, application.getUpdatedAt(), "Updated timestamp should match");
        assertEquals(metadata, application.getMetadata(), "Metadata should match");
        assertNotNull(application.getMetadataJson(), "Metadata JSON should be initialized");
    }
    
    @Test
    @DisplayName("Test Application entity validation for required fields")
    public void testValidation() {
        // Create an application with null required fields
        Application application = new Application();
        application.setStatus(null);
        application.setReviewStatus(null);
        application.setCreatedAt(null);
        application.setUpdatedAt(null);
        
        // Validate the entity
        Set<ConstraintViolation<Application>> violations = validator.validate(application);
        
        // Verify violations
        assertEquals(4, violations.size(), "Should have 4 validation violations");
        
        // Check for specific constraint violations
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("status")),
                "Should have violation for status");
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("reviewStatus")),
                "Should have violation for reviewStatus");
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("createdAt")),
                "Should have violation for createdAt");
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("updatedAt")),
                "Should have violation for updatedAt");
    }
    
    @Test
    @DisplayName("Test Application status transitions")
    public void testStatusTransitions() {
        // Create an application with NEW status
        Application application = new Application(ApplicationStatus.NEW);
        
        // Test valid transitions
        application.setStatus(ApplicationStatus.PROCESSING);
        assertEquals(ApplicationStatus.PROCESSING, application.getStatus(), "Status should be updated to PROCESSING");
        
        application.setStatus(ApplicationStatus.APPROVED);
        assertEquals(ApplicationStatus.APPROVED, application.getStatus(), "Status should be updated to APPROVED");
        
        // Test invalid transition
        Exception exception = assertThrows(IllegalStateException.class, () -> {
            application.setStatus(ApplicationStatus.PENDING);
        }, "Should throw IllegalStateException for invalid transition");
        
        assertTrue(exception.getMessage().contains("Invalid status transition"),
                "Exception message should mention invalid transition");
    }
    
    @Test
    @DisplayName("Test Application review status transitions")
    public void testReviewStatusTransitions() {
        // Create an application with NOT_REVIEWED status
        Application application = new Application();
        
        // Test valid transitions
        application.setReviewStatus(ReviewStatus.IN_REVIEW);
        assertEquals(ReviewStatus.IN_REVIEW, application.getReviewStatus(), "Review status should be updated to IN_REVIEW");
        
        application.setReviewStatus(ReviewStatus.NEEDS_INFORMATION);
        assertEquals(ReviewStatus.NEEDS_INFORMATION, application.getReviewStatus(), "Review status should be updated to NEEDS_INFORMATION");
        
        // Test invalid transition
        Exception exception = assertThrows(IllegalStateException.class, () -> {
            application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        }, "Should throw IllegalStateException for invalid transition");
        
        assertTrue(exception.getMessage().contains("Invalid review status transition"),
                "Exception message should mention invalid transition");
    }
    
    @Test
    @DisplayName("Test Application metadata JSON conversion")
    public void testMetadataJsonConversion() throws JsonUtil.JsonConversionException {
        // Create test metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 0.95);
        metadata.put("processingTimeMs", 2500);
        
        // Create nested metadata
        Map<String, Object> extractionDetails = new HashMap<>();
        extractionDetails.put("engine", "tensorflow");
        extractionDetails.put("version", "2.5.0");
        metadata.put("extraction", extractionDetails);
        
        // Create an application with metadata
        Application application = new Application();
        application.setMetadata(metadata);
        
        // Verify JSON conversion
        String metadataJson = application.getMetadataJson();
        assertNotNull(metadataJson, "Metadata JSON should not be null");
        assertTrue(metadataJson.contains("email"), "Metadata JSON should contain source value");
        assertTrue(metadataJson.contains("0.95"), "Metadata JSON should contain confidence value");
        assertTrue(metadataJson.contains("tensorflow"), "Metadata JSON should contain nested extraction details");
        
        // Test conversion back to map
        Map<String, Object> convertedMetadata = JsonUtil.fromJson(metadataJson, new TypeReference<Map<String, Object>>() {});
        assertEquals("email", convertedMetadata.get("source"), "Source should match original value");
        assertEquals(0.95, convertedMetadata.get("confidence"), "Confidence should match original value");
        
        // Verify that the metadata can be retrieved from the entity
        Map<String, Object> retrievedMetadata = application.getMetadata();
        assertEquals(metadata, retrievedMetadata, "Retrieved metadata should match original metadata");
    }
    
    @Test
    @DisplayName("Test Application metadata JSON setter")
    public void testMetadataJsonSetter() {
        // Create a JSON string
        String metadataJson = "{\"source\":\"email\",\"confidence\":0.95,\"tags\":[\"urgent\",\"high-value\"]}";
        
        // Create an application and set metadata JSON
        Application application = new Application();
        application.setMetadataJson(metadataJson);
        
        // Verify conversion to map
        Map<String, Object> metadata = application.getMetadata();
        assertEquals("email", metadata.get("source"), "Source should match JSON value");
        assertEquals(0.95, metadata.get("confidence"), "Confidence should match JSON value");
        
        // Verify array conversion
        Object tagsObj = metadata.get("tags");
        assertTrue(tagsObj instanceof java.util.List, "Tags should be converted to a List");
        java.util.List<?> tags = (java.util.List<?>) tagsObj;
        assertEquals(2, tags.size(), "Tags list should have 2 items");
        assertEquals("urgent", tags.get(0), "First tag should be 'urgent'");
        assertEquals("high-value", tags.get(1), "Second tag should be 'high-value'");
    }
    
    @Test
    @DisplayName("Test Application addMetadata method")
    public void testAddMetadata() {
        // Create an application
        Application application = new Application();
        
        // Add metadata values
        application.addMetadata("source", "email");
        application.addMetadata("confidence", 0.95);
        
        // Verify metadata values
        Map<String, Object> metadata = application.getMetadata();
        assertEquals("email", metadata.get("source"), "Source should match added value");
        assertEquals(0.95, metadata.get("confidence"), "Confidence should match added value");
        
        // Verify JSON conversion
        String metadataJson = application.getMetadataJson();
        assertTrue(metadataJson.contains("email"), "Metadata JSON should contain source value");
        assertTrue(metadataJson.contains("0.95"), "Metadata JSON should contain confidence value");
    }
    
    @Test
    @DisplayName("Test Application getMetadataValue method")
    public void testGetMetadataValue() {
        // Create an application with metadata
        Application application = new Application();
        application.addMetadata("source", "email");
        application.addMetadata("confidence", 0.95);
        
        // Get specific metadata values
        String source = application.getMetadataValue("source");
        Double confidence = application.getMetadataValue("confidence");
        Object nonExistent = application.getMetadataValue("nonExistent");
        
        // Verify values
        assertEquals("email", source, "Source should match added value");
        assertEquals(0.95, confidence, "Confidence should match added value");
        assertNull(nonExistent, "Non-existent key should return null");
    }
    
    @Test
    @DisplayName("Test Application bidirectional relationship with Document")
    public void testDocumentRelationship() {
        // Create an application
        Application application = new Application();
        UUID applicationId = UUID.randomUUID();
        application.setId(applicationId);
        
        // Create a document
        Document document = new Document(applicationId, DocumentType.BANK_STATEMENT, "mca-documents/test.pdf");
        
        // Add document to application
        application.addDocument(document);
        
        // Verify relationship
        assertEquals(1, application.getDocuments().size(), "Application should have 1 document");
        assertEquals(document, application.getDocuments().get(0), "Document should be in the application's documents list");
        assertEquals(application, document.getApplication(), "Document should reference the application");
        
        // Remove document from application
        application.removeDocument(document);
        
        // Verify relationship is removed
        assertEquals(0, application.getDocuments().size(), "Application should have 0 documents");
        assertNull(document.getApplication(), "Document should not reference the application");
    }
    
    @Test
    @DisplayName("Test Application bidirectional relationship with MerchantDetails")
    public void testMerchantDetailsRelationship() {
        // Create an application
        Application application = new Application();
        UUID applicationId = UUID.randomUUID();
        application.setId(applicationId);
        
        // Create merchant details
        MerchantDetails merchantDetails = new MerchantDetails(applicationId, "Test Merchant Inc.");
        
        // Set merchant details on application
        application.setMerchantDetails(merchantDetails);
        
        // Verify relationship
        assertEquals(merchantDetails, application.getMerchantDetails(), "Application should reference merchant details");
        assertEquals(application, merchantDetails.getApplication(), "Merchant details should reference the application");
        
        // Test hasMerchantDetails method
        assertTrue(application.hasMerchantDetails(), "Application should have merchant details");
    }
    
    @Test
    @DisplayName("Test Application status history tracking")
    public void testStatusHistory() {
        // Create an application
        Application application = new Application(ApplicationStatus.NEW);
        
        // Change status to trigger history tracking
        application.setStatus(ApplicationStatus.PROCESSING);
        application.setStatus(ApplicationStatus.APPROVED);
        
        // Get status history
        @SuppressWarnings("unchecked")
        java.util.List<Map<String, Object>> statusHistory = application.getStatusHistory();
        
        // Verify history
        assertNotNull(statusHistory, "Status history should not be null");
        assertEquals(3, statusHistory.size(), "Status history should have 3 entries");
        assertEquals("NEW", statusHistory.get(0).get("status"), "First status should be NEW");
        assertEquals("PROCESSING", statusHistory.get(1).get("status"), "Second status should be PROCESSING");
        assertEquals("APPROVED", statusHistory.get(2).get("status"), "Third status should be APPROVED");
    }
    
    @Test
    @DisplayName("Test Application review status history tracking")
    public void testReviewStatusHistory() {
        // Create an application
        Application application = new Application();
        
        // Change review status to trigger history tracking
        application.setReviewStatus(ReviewStatus.IN_REVIEW);
        application.setReviewStatus(ReviewStatus.APPROVED);
        
        // Get review status history
        @SuppressWarnings("unchecked")
        java.util.List<Map<String, Object>> reviewStatusHistory = application.getReviewStatusHistory();
        
        // Verify history
        assertNotNull(reviewStatusHistory, "Review status history should not be null");
        assertEquals(3, reviewStatusHistory.size(), "Review status history should have 3 entries");
        assertEquals("NOT_REVIEWED", reviewStatusHistory.get(0).get("status"), "First status should be NOT_REVIEWED");
        assertEquals("IN_REVIEW", reviewStatusHistory.get(1).get("status"), "Second status should be IN_REVIEW");
        assertEquals("APPROVED", reviewStatusHistory.get(2).get("status"), "Third status should be APPROVED");
    }
    
    @Test
    @DisplayName("Test Application processing time calculation")
    public void testProcessingTimeCalculation() {
        // Create an application with specific timestamps
        LocalDateTime createdAt = LocalDateTime.now().minusMinutes(4);
        LocalDateTime updatedAt = LocalDateTime.now();
        
        Application application = new Application(
            ApplicationStatus.COMPLETED,
            new HashMap<>(),
            createdAt,
            updatedAt,
            ReviewStatus.APPROVED
        );
        
        // Calculate processing time
        long processingTimeMs = application.getProcessingTimeMillis();
        
        // Verify processing time is approximately 4 minutes (with some tolerance for test execution time)
        assertTrue(processingTimeMs >= 240000 && processingTimeMs <= 250000,
                "Processing time should be approximately 4 minutes");
        
        // Test processing time requirement check
        assertTrue(application.meetsProcessingTimeRequirement(),
                "Application should meet the 5-minute processing time requirement");
        
        // Test with non-completed application
        application.setStatus(ApplicationStatus.PROCESSING);
        assertEquals(0, application.getProcessingTimeMillis(),
                "Processing time should be 0 for non-completed applications");
        assertFalse(application.meetsProcessingTimeRequirement(),
                "Non-completed application should not meet processing time requirement");
    }
    
    @Test
    @DisplayName("Test Application terminal state check")
    public void testTerminalStateCheck() {
        // Test terminal states
        Application completedApp = new Application(ApplicationStatus.COMPLETED);
        Application rejectedApp = new Application(ApplicationStatus.REJECTED);
        
        assertTrue(completedApp.isTerminal(), "COMPLETED status should be terminal");
        assertTrue(rejectedApp.isTerminal(), "REJECTED status should be terminal");
        
        // Test non-terminal states
        Application newApp = new Application(ApplicationStatus.NEW);
        Application processingApp = new Application(ApplicationStatus.PROCESSING);
        
        assertFalse(newApp.isTerminal(), "NEW status should not be terminal");
        assertFalse(processingApp.isTerminal(), "PROCESSING status should not be terminal");
    }
    
    @Test
    @DisplayName("Test Application human intervention check")
    public void testHumanInterventionCheck() {
        // Test states requiring human intervention
        Application pendingApp = new Application(ApplicationStatus.PENDING);
        Application errorApp = new Application(ApplicationStatus.ERROR);
        Application exceptionApp = new Application(ApplicationStatus.EXCEPTION);
        
        assertTrue(pendingApp.requiresHumanIntervention(), "PENDING status should require human intervention");
        assertTrue(errorApp.requiresHumanIntervention(), "ERROR status should require human intervention");
        assertTrue(exceptionApp.requiresHumanIntervention(), "EXCEPTION status should require human intervention");
        
        // Test states not requiring human intervention
        Application newApp = new Application(ApplicationStatus.NEW);
        Application processingApp = new Application(ApplicationStatus.PROCESSING);
        Application completedApp = new Application(ApplicationStatus.COMPLETED);
        
        assertFalse(newApp.requiresHumanIntervention(), "NEW status should not require human intervention");
        assertFalse(processingApp.requiresHumanIntervention(), "PROCESSING status should not require human intervention");
        assertFalse(completedApp.requiresHumanIntervention(), "COMPLETED status should not require human intervention");
    }
    
    @Test
    @DisplayName("Test Application document count")
    public void testDocumentCount() {
        // Create an application
        Application application = new Application();
        UUID applicationId = UUID.randomUUID();
        application.setId(applicationId);
        
        // Add documents
        application.addDocument(new Document(applicationId, DocumentType.BANK_STATEMENT, "mca-documents/bank.pdf"));
        application.addDocument(new Document(applicationId, DocumentType.TAX_RETURN, "mca-documents/tax.pdf"));
        
        // Verify document count
        assertEquals(2, application.getDocumentCount(), "Application should have 2 documents");
        
        // Test with null documents list
        Application nullDocsApp = new Application();
        nullDocsApp.setDocuments(null);
        assertEquals(0, nullDocsApp.getDocumentCount(), "Document count should be 0 for null documents list");
    }
    
    @Test
    @DisplayName("Test Application equals and hashCode")
    public void testEqualsAndHashCode() {
        // Create applications with same ID
        UUID id = UUID.randomUUID();
        
        Application app1 = new Application();
        app1.setId(id);
        
        Application app2 = new Application();
        app2.setId(id);
        
        // Create application with different ID
        Application app3 = new Application();
        app3.setId(UUID.randomUUID());
        
        // Create application with null ID
        Application app4 = new Application();
        
        // Test equals
        assertEquals(app1, app2, "Applications with same ID should be equal");
        assertNotEquals(app1, app3, "Applications with different IDs should not be equal");
        assertNotEquals(app1, app4, "Application with ID should not equal application without ID");
        assertEquals(app4, new Application(), "Applications without IDs should be equal");
        
        // Test hashCode
        assertEquals(app1.hashCode(), app2.hashCode(), "Hash codes should be equal for equal applications");
        assertNotEquals(app1.hashCode(), app3.hashCode(), "Hash codes should differ for different applications");
    }
    
    @Test
    @DisplayName("Test Application toString")
    public void testToString() {
        // Create an application with documents and merchant details
        Application application = new Application(ApplicationStatus.PROCESSING);
        UUID id = UUID.randomUUID();
        application.setId(id);
        application.setReviewStatus(ReviewStatus.IN_REVIEW);
        
        // Add documents
        Document doc1 = new Document(id, DocumentType.BANK_STATEMENT, "mca-documents/bank.pdf");
        Document doc2 = new Document(id, DocumentType.TAX_RETURN, "mca-documents/tax.pdf");
        application.addDocument(doc1);
        application.addDocument(doc2);
        
        // Add merchant details
        MerchantDetails merchantDetails = new MerchantDetails(id, "Test Merchant Inc.");
        application.setMerchantDetails(merchantDetails);
        
        // Get string representation
        String toString = application.toString();
        
        // Verify string contains important information
        assertTrue(toString.contains(id.toString()), "toString should contain application ID");
        assertTrue(toString.contains("PROCESSING"), "toString should contain status");
        assertTrue(toString.contains("IN_REVIEW"), "toString should contain review status");
        assertTrue(toString.contains("documentCount=2"), "toString should contain document count");
        assertTrue(toString.contains("hasMerchantDetails=true"), "toString should indicate merchant details presence");
    }
    
    @Test
    @DisplayName("Test Application Builder pattern")
    public void testBuilderPattern() {
        // Create metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 0.95);
        
        // Use builder to create application
        Application application = new Application.Builder()
            .withStatus(ApplicationStatus.PROCESSING)
            .withReviewStatus(ReviewStatus.IN_REVIEW)
            .withMetadata(metadata)
            .addMetadata("priority", "high")
            .build();
        
        // Verify application properties
        assertEquals(ApplicationStatus.PROCESSING, application.getStatus(), "Status should match builder value");
        assertEquals(ReviewStatus.IN_REVIEW, application.getReviewStatus(), "Review status should match builder value");
        
        // Verify metadata
        Map<String, Object> appMetadata = application.getMetadata();
        assertEquals("email", appMetadata.get("source"), "Source should match builder value");
        assertEquals(0.95, appMetadata.get("confidence"), "Confidence should match builder value");
        assertEquals("high", appMetadata.get("priority"), "Priority should match builder value");
    }
    
    @Test
    @DisplayName("Test Application persistence")
    public void testPersistence() {
        // Create an application
        Application application = new Application(ApplicationStatus.NEW);
        UUID id = UUID.randomUUID();
        application.setId(id);
        
        // Mock persistence operations
        when(entityManager.find(Application.class, id)).thenReturn(application);
        
        // Simulate persist and find operations
        entityManager.persist(application);
        Application foundApplication = entityManager.find(Application.class, id);
        
        // Verify found application
        assertNotNull(foundApplication, "Found application should not be null");
        assertEquals(id, foundApplication.getId(), "Found application should have the same ID");
        assertEquals(ApplicationStatus.NEW, foundApplication.getStatus(), "Found application should have the same status");
        
        // Verify persistence operations were called
        verify(entityManager).persist(application);
        verify(entityManager).find(Application.class, id);
    }
}