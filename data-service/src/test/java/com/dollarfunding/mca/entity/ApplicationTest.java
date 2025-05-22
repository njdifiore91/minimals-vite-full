package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the Application entity.
 * 
 * These tests verify JPA mapping, field validation, and relationships for the Application entity.
 * The test suite ensures that the Application entity can be properly persisted and retrieved
 * with all its attributes and relationships intact, and that validation constraints are properly enforced.
 */
@ExtendWith(SpringExtension.class)
@DataJpaTest
public class ApplicationTest {

    @Autowired
    private TestEntityManager entityManager;
    
    private Validator validator;
    
    @BeforeEach
    void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }
    
    /**
     * Tests for basic entity properties and validation.
     */
    @Nested
    @DisplayName("Basic Entity Tests")
    class BasicEntityTests {
        
        @Test
        @DisplayName("Should create application with default constructor")
        void shouldCreateApplicationWithDefaultConstructor() {
            // When
            Application application = new Application();
            
            // Then
            assertNotNull(application);
            assertEquals(ApplicationStatus.NEW, application.getStatus());
            assertEquals(ReviewStatus.NOT_REVIEWED, application.getReviewStatus());
            assertNotNull(application.getCreatedAt());
            assertNotNull(application.getUpdatedAt());
            assertNotNull(application.getMetadata());
            assertTrue(application.getMetadata().isEmpty());
            assertNotNull(application.getDocuments());
            assertTrue(application.getDocuments().isEmpty());
        }
        
        @Test
        @DisplayName("Should create application with required fields constructor")
        void shouldCreateApplicationWithRequiredFieldsConstructor() {
            // When
            Application application = new Application(ApplicationStatus.PROCESSING, ReviewStatus.IN_REVIEW);
            
            // Then
            assertNotNull(application);
            assertEquals(ApplicationStatus.PROCESSING, application.getStatus());
            assertEquals(ReviewStatus.IN_REVIEW, application.getReviewStatus());
            assertNotNull(application.getCreatedAt());
            assertNotNull(application.getUpdatedAt());
            assertNotNull(application.getMetadata());
            assertTrue(application.getMetadata().isEmpty());
            assertNotNull(application.getDocuments());
            assertTrue(application.getDocuments().isEmpty());
        }
        
        @Test
        @DisplayName("Should create application with all fields constructor")
        void shouldCreateApplicationWithAllFieldsConstructor() {
            // Given
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("source", "email");
            metadata.put("confidence", 0.95);
            
            LocalDateTime createdAt = LocalDateTime.now().minusDays(1);
            LocalDateTime updatedAt = LocalDateTime.now();
            
            // When
            Application application = new Application(
                ApplicationStatus.APPROVED, 
                ReviewStatus.APPROVED, 
                metadata, 
                createdAt, 
                updatedAt
            );
            
            // Then
            assertNotNull(application);
            assertEquals(ApplicationStatus.APPROVED, application.getStatus());
            assertEquals(ReviewStatus.APPROVED, application.getReviewStatus());
            assertEquals(createdAt, application.getCreatedAt());
            assertEquals(updatedAt, application.getUpdatedAt());
            assertNotNull(application.getMetadata());
            assertEquals(2, application.getMetadata().size());
            assertEquals("email", application.getMetadata().get("source"));
            assertEquals(0.95, application.getMetadata().get("confidence"));
            assertNotNull(application.getDocuments());
            assertTrue(application.getDocuments().isEmpty());
        }
        
        @Test
        @DisplayName("Should validate required fields")
        void shouldValidateRequiredFields() {
            // Given
            Application application = new Application();
            application.setStatus(null);
            application.setReviewStatus(null);
            
            // When
            Set<ConstraintViolation<Application>> violations = validator.validate(application);
            
            // Then
            assertEquals(2, violations.size());
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("status")));
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("reviewStatus")));
        }
        
        @Test
        @DisplayName("Should create application with builder")
        void shouldCreateApplicationWithBuilder() {
            // Given
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("source", "email");
            
            // When
            Application application = new Application.Builder()
                .withStatus(ApplicationStatus.PENDING)
                .withReviewStatus(ReviewStatus.NEEDS_INFORMATION)
                .withMetadata(metadata)
                .addMetadata("priority", "high")
                .build();
            
            // Then
            assertNotNull(application);
            assertEquals(ApplicationStatus.PENDING, application.getStatus());
            assertEquals(ReviewStatus.NEEDS_INFORMATION, application.getReviewStatus());
            assertNotNull(application.getMetadata());
            assertEquals(2, application.getMetadata().size());
            assertEquals("email", application.getMetadata().get("source"));
            assertEquals("high", application.getMetadata().get("priority"));
        }
    }
    
    /**
     * Tests for enum mapping and status transitions.
     */
    @Nested
    @DisplayName("Enum Mapping Tests")
    class EnumMappingTests {
        
        @Test
        @DisplayName("Should map ApplicationStatus enum values correctly")
        void shouldMapApplicationStatusEnumValuesCorrectly() {
            // Given
            Application application = new Application();
            
            // When/Then - Test all enum values
            application.setStatus(ApplicationStatus.NEW);
            assertEquals(ApplicationStatus.NEW, application.getStatus());
            
            application.setStatus(ApplicationStatus.PENDING);
            assertEquals(ApplicationStatus.PENDING, application.getStatus());
            
            application.setStatus(ApplicationStatus.PROCESSING);
            assertEquals(ApplicationStatus.PROCESSING, application.getStatus());
            
            application.setStatus(ApplicationStatus.APPROVED);
            assertEquals(ApplicationStatus.APPROVED, application.getStatus());
            
            application.setStatus(ApplicationStatus.REJECTED);
            assertEquals(ApplicationStatus.REJECTED, application.getStatus());
            
            application.setStatus(ApplicationStatus.COMPLETED);
            assertEquals(ApplicationStatus.COMPLETED, application.getStatus());
        }
        
        @Test
        @DisplayName("Should map ReviewStatus enum values correctly")
        void shouldMapReviewStatusEnumValuesCorrectly() {
            // Given
            Application application = new Application();
            
            // When/Then - Test all enum values
            application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
            assertEquals(ReviewStatus.NOT_REVIEWED, application.getReviewStatus());
            
            application.setReviewStatus(ReviewStatus.IN_REVIEW);
            assertEquals(ReviewStatus.IN_REVIEW, application.getReviewStatus());
            
            application.setReviewStatus(ReviewStatus.NEEDS_INFORMATION);
            assertEquals(ReviewStatus.NEEDS_INFORMATION, application.getReviewStatus());
            
            application.setReviewStatus(ReviewStatus.APPROVED);
            assertEquals(ReviewStatus.APPROVED, application.getReviewStatus());
            
            application.setReviewStatus(ReviewStatus.REJECTED);
            assertEquals(ReviewStatus.REJECTED, application.getReviewStatus());
        }
        
        @Test
        @DisplayName("Should handle valid application status transitions")
        void shouldHandleValidApplicationStatusTransitions() {
            // Given
            Application application = new Application();
            assertEquals(ApplicationStatus.NEW, application.getStatus());
            
            // When/Then - Test valid transitions
            assertTrue(application.updateStatus(ApplicationStatus.PENDING));
            assertEquals(ApplicationStatus.PENDING, application.getStatus());
            
            assertTrue(application.updateStatus(ApplicationStatus.PROCESSING));
            assertEquals(ApplicationStatus.PROCESSING, application.getStatus());
            
            assertTrue(application.updateStatus(ApplicationStatus.APPROVED));
            assertEquals(ApplicationStatus.APPROVED, application.getStatus());
            
            assertTrue(application.updateStatus(ApplicationStatus.COMPLETED));
            assertEquals(ApplicationStatus.COMPLETED, application.getStatus());
        }
        
        @Test
        @DisplayName("Should reject invalid application status transitions")
        void shouldRejectInvalidApplicationStatusTransitions() {
            // Given
            Application application = new Application();
            application.setStatus(ApplicationStatus.COMPLETED);
            
            // When/Then - Test invalid transitions
            assertFalse(application.updateStatus(ApplicationStatus.NEW));
            assertEquals(ApplicationStatus.COMPLETED, application.getStatus());
            
            assertFalse(application.updateStatus(ApplicationStatus.PENDING));
            assertEquals(ApplicationStatus.COMPLETED, application.getStatus());
        }
        
        @Test
        @DisplayName("Should handle valid review status transitions")
        void shouldHandleValidReviewStatusTransitions() {
            // Given
            Application application = new Application();
            assertEquals(ReviewStatus.NOT_REVIEWED, application.getReviewStatus());
            
            // When/Then - Test valid transitions
            assertTrue(application.updateReviewStatus(ReviewStatus.IN_REVIEW));
            assertEquals(ReviewStatus.IN_REVIEW, application.getReviewStatus());
            
            assertTrue(application.updateReviewStatus(ReviewStatus.NEEDS_INFORMATION));
            assertEquals(ReviewStatus.NEEDS_INFORMATION, application.getReviewStatus());
            
            assertTrue(application.updateReviewStatus(ReviewStatus.APPROVED));
            assertEquals(ReviewStatus.APPROVED, application.getReviewStatus());
        }
        
        @Test
        @DisplayName("Should update timestamps when status changes")
        void shouldUpdateTimestampsWhenStatusChanges() {
            // Given
            Application application = new Application();
            LocalDateTime initialUpdatedAt = application.getUpdatedAt();
            
            // Wait a bit to ensure timestamp difference
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                // Ignore
            }
            
            // When
            application.setStatus(ApplicationStatus.PROCESSING);
            
            // Then
            assertTrue(application.getUpdatedAt().isAfter(initialUpdatedAt));
        }
    }
    
    /**
     * Tests for JSON metadata conversion.
     */
    @Nested
    @DisplayName("JSON Metadata Tests")
    class JsonMetadataTests {
        
        @Test
        @DisplayName("Should convert metadata map to JSON string")
        void shouldConvertMetadataMapToJsonString() throws Exception {
            // Given
            Application application = new Application();
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("source", "email");
            metadata.put("confidence", 0.95);
            metadata.put("processingTime", 120);
            
            // When
            application.setMetadata(metadata);
            
            // Then
            assertNotNull(application.getMetadataJson());
            assertTrue(JsonUtil.isValidJson(application.getMetadataJson()));
            
            // Verify the JSON contains the expected data
            Map<String, Object> parsedMetadata = JsonUtil.fromJson(
                application.getMetadataJson(), 
                new TypeReference<Map<String, Object>>() {}
            );
            assertEquals(3, parsedMetadata.size());
            assertEquals("email", parsedMetadata.get("source"));
            assertEquals(0.95, parsedMetadata.get("confidence"));
            assertEquals(120, parsedMetadata.get("processingTime"));
        }
        
        @Test
        @DisplayName("Should convert JSON string to metadata map")
        void shouldConvertJsonStringToMetadataMap() throws Exception {
            // Given
            Application application = new Application();
            String metadataJson = "{\"source\":\"email\",\"confidence\":0.95,\"processingTime\":120}";
            
            // When
            application.setMetadataJson(metadataJson);
            
            // Then
            assertNotNull(application.getMetadata());
            assertEquals(3, application.getMetadata().size());
            assertEquals("email", application.getMetadata().get("source"));
            assertEquals(0.95, application.getMetadata().get("confidence"));
            assertEquals(120, application.getMetadata().get("processingTime"));
        }
        
        @Test
        @DisplayName("Should add individual metadata values")
        void shouldAddIndividualMetadataValues() {
            // Given
            Application application = new Application();
            
            // When
            application.addMetadata("source", "email");
            application.addMetadata("confidence", 0.95);
            
            // Then
            Map<String, Object> metadata = application.getMetadata();
            assertEquals(2, metadata.size());
            assertEquals("email", metadata.get("source"));
            assertEquals(0.95, metadata.get("confidence"));
        }
        
        @Test
        @DisplayName("Should retrieve individual metadata values with correct type")
        void shouldRetrieveIndividualMetadataValuesWithCorrectType() {
            // Given
            Application application = new Application();
            application.addMetadata("source", "email");
            application.addMetadata("confidence", 0.95);
            application.addMetadata("processingTime", 120);
            
            // When/Then
            assertEquals("email", application.getMetadataValue("source"));
            assertEquals(0.95, application.<Double>getMetadataValue("confidence"));
            assertEquals(120, application.<Integer>getMetadataValue("processingTime"));
            assertNull(application.getMetadataValue("nonExistentKey"));
        }
        
        @Test
        @DisplayName("Should handle null or empty metadata")
        void shouldHandleNullOrEmptyMetadata() {
            // Given
            Application application = new Application();
            
            // When
            application.setMetadata(null);
            
            // Then
            assertNotNull(application.getMetadata());
            assertTrue(application.getMetadata().isEmpty());
            assertEquals("{}", application.getMetadataJson());
            
            // When
            application.setMetadataJson(null);
            
            // Then
            assertNotNull(application.getMetadata());
            assertTrue(application.getMetadata().isEmpty());
            
            // When
            application.setMetadataJson("");
            
            // Then
            assertNotNull(application.getMetadata());
            assertTrue(application.getMetadata().isEmpty());
        }
    }
    
    /**
     * Tests for bidirectional relationships with Document and MerchantDetails entities.
     */
    @Nested
    @DisplayName("Relationship Tests")
    class RelationshipTests {
        
        @Test
        @DisplayName("Should maintain bidirectional relationship with Document entity")
        void shouldMaintainBidirectionalRelationshipWithDocumentEntity() {
            // Given
            Application application = new Application(ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
            Document document = new Document(UUID.randomUUID(), DocumentType.BANK_STATEMENT, "s3://bucket/path/to/document");
            
            // When
            application.addDocument(document);
            
            // Then
            assertEquals(1, application.getDocuments().size());
            assertSame(document, application.getDocuments().get(0));
            assertSame(application, document.getApplication());
            
            // When - Test removing document
            application.removeDocument(document);
            
            // Then
            assertTrue(application.getDocuments().isEmpty());
            assertNull(document.getApplication());
        }
        
        @Test
        @DisplayName("Should maintain bidirectional relationship with MerchantDetails entity")
        void shouldMaintainBidirectionalRelationshipWithMerchantDetailsEntity() {
            // Given
            Application application = new Application(ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
            MerchantDetails merchantDetails = new MerchantDetails();
            
            // When
            application.setMerchantDetails(merchantDetails);
            
            // Then
            assertSame(merchantDetails, application.getMerchantDetails());
            assertSame(application, merchantDetails.getApplication());
        }
        
        @Test
        @DisplayName("Should set documents with bidirectional relationship")
        void shouldSetDocumentsWithBidirectionalRelationship() {
            // Given
            Application application = new Application();
            Document document1 = new Document(UUID.randomUUID(), DocumentType.BANK_STATEMENT, "s3://bucket/path/to/document1");
            Document document2 = new Document(UUID.randomUUID(), DocumentType.TAX_RETURN, "s3://bucket/path/to/document2");
            
            // When
            application.setDocuments(java.util.Arrays.asList(document1, document2));
            
            // Then
            assertEquals(2, application.getDocuments().size());
            assertTrue(application.getDocuments().contains(document1));
            assertTrue(application.getDocuments().contains(document2));
            assertSame(application, document1.getApplication());
            assertSame(application, document2.getApplication());
        }
    }
    
    /**
     * Tests for persistence and retrieval of Application entity.
     */
    @Nested
    @DisplayName("Persistence Tests")
    class PersistenceTests {
        
        @Test
        @DisplayName("Should persist and retrieve application with all fields")
        void shouldPersistAndRetrieveApplicationWithAllFields() {
            // Given
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("source", "email");
            metadata.put("confidence", 0.95);
            
            Application application = new Application(
                ApplicationStatus.PROCESSING,
                ReviewStatus.IN_REVIEW,
                metadata,
                LocalDateTime.now().minusDays(1),
                LocalDateTime.now()
            );
            
            // When
            Application savedApplication = entityManager.persistAndFlush(application);
            entityManager.clear();
            Application retrievedApplication = entityManager.find(Application.class, savedApplication.getId());
            
            // Then
            assertNotNull(retrievedApplication);
            assertEquals(savedApplication.getId(), retrievedApplication.getId());
            assertEquals(ApplicationStatus.PROCESSING, retrievedApplication.getStatus());
            assertEquals(ReviewStatus.IN_REVIEW, retrievedApplication.getReviewStatus());
            assertEquals(savedApplication.getCreatedAt(), retrievedApplication.getCreatedAt());
            assertEquals(savedApplication.getUpdatedAt(), retrievedApplication.getUpdatedAt());
            
            // Verify metadata was persisted correctly
            Map<String, Object> retrievedMetadata = retrievedApplication.getMetadata();
            assertEquals(2, retrievedMetadata.size());
            assertEquals("email", retrievedMetadata.get("source"));
            assertEquals(0.95, retrievedMetadata.get("confidence"));
        }
        
        @Test
        @DisplayName("Should persist and retrieve application with documents")
        void shouldPersistAndRetrieveApplicationWithDocuments() {
            // Given
            Application application = new Application(ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
            Document document1 = new Document(null, DocumentType.BANK_STATEMENT, "s3://bucket/path/to/document1");
            Document document2 = new Document(null, DocumentType.TAX_RETURN, "s3://bucket/path/to/document2");
            
            application.addDocument(document1);
            application.addDocument(document2);
            
            // When
            Application savedApplication = entityManager.persistAndFlush(application);
            entityManager.clear();
            Application retrievedApplication = entityManager.find(Application.class, savedApplication.getId());
            
            // Then
            assertNotNull(retrievedApplication);
            assertEquals(2, retrievedApplication.getDocuments().size());
            
            // Verify document types were persisted correctly
            assertTrue(retrievedApplication.getDocuments().stream()
                .anyMatch(d -> d.getType() == DocumentType.BANK_STATEMENT));
            assertTrue(retrievedApplication.getDocuments().stream()
                .anyMatch(d -> d.getType() == DocumentType.TAX_RETURN));
        }
        
        @Test
        @DisplayName("Should persist and retrieve application with merchant details")
        void shouldPersistAndRetrieveApplicationWithMerchantDetails() {
            // Given
            Application application = new Application(ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
            
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setLegalName("Acme Corporation");
            merchantDetails.setDbaName("Acme");
            merchantDetails.setEin("12-3456789");
            merchantDetails.setIndustry("Technology");
            merchantDetails.setRevenue(new BigDecimal("1000000.00"));
            
            MerchantDetails.Address address = new MerchantDetails.Address();
            address.setStreet("123 Main St");
            address.setCity("Anytown");
            address.setState("CA");
            address.setZip("12345");
            address.setCountry("USA");
            merchantDetails.setAddress(address);
            
            application.setMerchantDetails(merchantDetails);
            
            // When
            Application savedApplication = entityManager.persistAndFlush(application);
            entityManager.clear();
            Application retrievedApplication = entityManager.find(Application.class, savedApplication.getId());
            
            // Then
            assertNotNull(retrievedApplication);
            assertNotNull(retrievedApplication.getMerchantDetails());
            assertEquals("Acme Corporation", retrievedApplication.getMerchantDetails().getLegalName());
            assertEquals("Acme", retrievedApplication.getMerchantDetails().getDbaName());
            assertEquals("12-3456789", retrievedApplication.getMerchantDetails().getEin());
            assertEquals("Technology", retrievedApplication.getMerchantDetails().getIndustry());
            assertEquals(0, new BigDecimal("1000000.00").compareTo(retrievedApplication.getMerchantDetails().getRevenue()));
            
            // Verify address was persisted correctly
            MerchantDetails.Address retrievedAddress = retrievedApplication.getMerchantDetails().getAddress();
            assertEquals("123 Main St", retrievedAddress.getStreet());
            assertEquals("Anytown", retrievedAddress.getCity());
            assertEquals("CA", retrievedAddress.getState());
            assertEquals("12345", retrievedAddress.getZip());
            assertEquals("USA", retrievedAddress.getCountry());
        }
    }
    
    /**
     * Tests for utility methods in the Application entity.
     */
    @Nested
    @DisplayName("Utility Method Tests")
    class UtilityMethodTests {
        
        @Test
        @DisplayName("Should correctly determine if application is completed")
        void shouldCorrectlyDetermineIfApplicationIsCompleted() {
            // Given
            Application application = new Application();
            
            // When/Then
            application.setStatus(ApplicationStatus.NEW);
            assertFalse(application.isCompleted());
            
            application.setStatus(ApplicationStatus.PROCESSING);
            assertFalse(application.isCompleted());
            
            application.setStatus(ApplicationStatus.COMPLETED);
            assertTrue(application.isCompleted());
        }
        
        @Test
        @DisplayName("Should correctly determine if application is active")
        void shouldCorrectlyDetermineIfApplicationIsActive() {
            // Given
            Application application = new Application();
            
            // When/Then
            application.setStatus(ApplicationStatus.NEW);
            assertTrue(application.isActive());
            
            application.setStatus(ApplicationStatus.PENDING);
            assertTrue(application.isActive());
            
            application.setStatus(ApplicationStatus.PROCESSING);
            assertTrue(application.isActive());
            
            application.setStatus(ApplicationStatus.APPROVED);
            assertFalse(application.isActive());
            
            application.setStatus(ApplicationStatus.REJECTED);
            assertFalse(application.isActive());
            
            application.setStatus(ApplicationStatus.COMPLETED);
            assertFalse(application.isActive());
        }
        
        @Test
        @DisplayName("Should correctly determine if application is decided")
        void shouldCorrectlyDetermineIfApplicationIsDecided() {
            // Given
            Application application = new Application();
            
            // When/Then
            application.setStatus(ApplicationStatus.NEW);
            assertFalse(application.isDecided());
            
            application.setStatus(ApplicationStatus.PENDING);
            assertFalse(application.isDecided());
            
            application.setStatus(ApplicationStatus.PROCESSING);
            assertFalse(application.isDecided());
            
            application.setStatus(ApplicationStatus.APPROVED);
            assertTrue(application.isDecided());
            
            application.setStatus(ApplicationStatus.REJECTED);
            assertTrue(application.isDecided());
            
            application.setStatus(ApplicationStatus.COMPLETED);
            assertTrue(application.isDecided());
        }
        
        @Test
        @DisplayName("Should correctly determine if application requires review")
        void shouldCorrectlyDetermineIfApplicationRequiresReview() {
            // Given
            Application application = new Application();
            
            // When/Then
            application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
            assertTrue(application.requiresReview());
            
            application.setReviewStatus(ReviewStatus.IN_REVIEW);
            assertFalse(application.requiresReview());
            
            application.setReviewStatus(ReviewStatus.NEEDS_INFORMATION);
            assertTrue(application.requiresReview());
            
            application.setReviewStatus(ReviewStatus.APPROVED);
            assertFalse(application.requiresReview());
            
            application.setReviewStatus(ReviewStatus.REJECTED);
            assertFalse(application.requiresReview());
        }
        
        @Test
        @DisplayName("Should correctly determine if application has all required documents")
        void shouldCorrectlyDetermineIfApplicationHasAllRequiredDocuments() {
            // Given
            Application application = new Application();
            
            // When/Then - No documents
            assertFalse(application.hasAllRequiredDocuments());
            
            // When - Add one required document type
            Document idDocument = new Document(UUID.randomUUID(), DocumentType.ID_VERIFICATION, "s3://bucket/path/to/id");
            application.addDocument(idDocument);
            
            // Then
            assertFalse(application.hasAllRequiredDocuments());
            
            // When - Add second required document type
            Document financialDocument = new Document(UUID.randomUUID(), DocumentType.BANK_STATEMENT, "s3://bucket/path/to/bank");
            application.addDocument(financialDocument);
            
            // Then
            assertFalse(application.hasAllRequiredDocuments());
            
            // When - Add third required document type
            Document businessDocument = new Document(UUID.randomUUID(), DocumentType.BUSINESS_LICENSE, "s3://bucket/path/to/license");
            application.addDocument(businessDocument);
            
            // Then - Now has all required document types
            assertTrue(application.hasAllRequiredDocuments());
        }
        
        @Test
        @DisplayName("Should calculate processing time in minutes")
        void shouldCalculateProcessingTimeInMinutes() {
            // Given
            LocalDateTime createdAt = LocalDateTime.now().minusMinutes(10);
            LocalDateTime updatedAt = LocalDateTime.now();
            
            Application application = new Application();
            application.setCreatedAt(createdAt);
            application.setUpdatedAt(updatedAt);
            
            // When/Then - Not completed yet
            application.setStatus(ApplicationStatus.PROCESSING);
            assertEquals(-1, application.getProcessingTimeMinutes());
            
            // When/Then - Completed
            application.setStatus(ApplicationStatus.COMPLETED);
            assertEquals(10, application.getProcessingTimeMinutes());
        }
        
        @Test
        @DisplayName("Should determine if application was processed within target time")
        void shouldDetermineIfApplicationWasProcessedWithinTargetTime() {
            // Given
            Application fastApplication = new Application();
            fastApplication.setStatus(ApplicationStatus.COMPLETED);
            fastApplication.setCreatedAt(LocalDateTime.now().minusMinutes(3));
            fastApplication.setUpdatedAt(LocalDateTime.now());
            
            Application slowApplication = new Application();
            slowApplication.setStatus(ApplicationStatus.COMPLETED);
            slowApplication.setCreatedAt(LocalDateTime.now().minusMinutes(10));
            slowApplication.setUpdatedAt(LocalDateTime.now());
            
            Application incompleteApplication = new Application();
            incompleteApplication.setStatus(ApplicationStatus.PROCESSING);
            
            // When/Then
            assertTrue(fastApplication.isProcessedWithinTargetTime()); // 3 minutes < 5 minutes target
            assertFalse(slowApplication.isProcessedWithinTargetTime()); // 10 minutes > 5 minutes target
            assertFalse(incompleteApplication.isProcessedWithinTargetTime()); // Not completed yet
        }
        
        @Test
        @DisplayName("Should generate proper toString representation")
        void shouldGenerateProperToStringRepresentation() {
            // Given
            Application application = new Application(ApplicationStatus.PROCESSING, ReviewStatus.IN_REVIEW);
            application.setId(UUID.randomUUID());
            
            Document document = new Document(UUID.randomUUID(), DocumentType.BANK_STATEMENT, "s3://bucket/path/to/document");
            application.addDocument(document);
            
            // When
            String toString = application.toString();
            
            // Then
            assertNotNull(toString);
            assertTrue(toString.contains(application.getId().toString()));
            assertTrue(toString.contains("PROCESSING"));
            assertTrue(toString.contains("IN_REVIEW"));
            assertTrue(toString.contains("documentsCount=1"));
            assertTrue(toString.contains("hasMerchantDetails=false"));
        }
        
        @Test
        @DisplayName("Should implement equals and hashCode correctly")
        void shouldImplementEqualsAndHashCodeCorrectly() {
            // Given
            UUID id = UUID.randomUUID();
            
            Application application1 = new Application();
            application1.setId(id);
            
            Application application2 = new Application();
            application2.setId(id);
            
            Application application3 = new Application();
            application3.setId(UUID.randomUUID());
            
            // When/Then - equals
            assertEquals(application1, application1); // Same instance
            assertEquals(application1, application2); // Same ID
            assertNotEquals(application1, application3); // Different ID
            assertNotEquals(application1, null); // Null comparison
            assertNotEquals(application1, new Object()); // Different type
            
            // When/Then - hashCode
            assertEquals(application1.hashCode(), application2.hashCode()); // Same ID
            assertNotEquals(application1.hashCode(), application3.hashCode()); // Different ID
        }
    }
}