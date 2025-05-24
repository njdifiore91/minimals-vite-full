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
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the Document entity.
 * 
 * These tests verify JPA mapping, field validation, and relationships for the Document entity.
 * The test suite ensures that the Document entity can be properly persisted and retrieved
 * with all its attributes and relationships intact, and that validation constraints are properly enforced.
 */
@ExtendWith(SpringExtension.class)
@DataJpaTest
public class DocumentTest {

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
        @DisplayName("Should create document with default constructor")
        void shouldCreateDocumentWithDefaultConstructor() {
            // When
            Document document = new Document();
            
            // Then
            assertNotNull(document);
            assertNull(document.getId());
            assertNull(document.getApplicationId());
            assertNull(document.getApplication());
            assertNull(document.getType());
            assertNull(document.getStoragePath());
            assertEquals(DocumentClassification.UNCLASSIFIED, document.getClassification());
            assertNotNull(document.getUploadedAt());
            assertNotNull(document.getMetadata());
            assertTrue(document.getMetadata().isEmpty());
        }
        
        @Test
        @DisplayName("Should create document with required fields constructor")
        void shouldCreateDocumentWithRequiredFieldsConstructor() {
            // Given
            UUID applicationId = UUID.randomUUID();
            DocumentType type = DocumentType.BANK_STATEMENT;
            String storagePath = "mca-documents-production/applications/123/bank-statement.pdf";
            
            // When
            Document document = new Document(applicationId, type, storagePath);
            
            // Then
            assertNotNull(document);
            assertNull(document.getId());
            assertEquals(applicationId, document.getApplicationId());
            assertNull(document.getApplication());
            assertEquals(type, document.getType());
            assertEquals(storagePath, document.getStoragePath());
            assertEquals(DocumentClassification.UNCLASSIFIED, document.getClassification());
            assertNotNull(document.getUploadedAt());
            assertNotNull(document.getMetadata());
            assertTrue(document.getMetadata().isEmpty());
        }
        
        @Test
        @DisplayName("Should create document with all fields constructor")
        void shouldCreateDocumentWithAllFieldsConstructor() {
            // Given
            UUID applicationId = UUID.randomUUID();
            DocumentType type = DocumentType.TAX_RETURN;
            String storagePath = "mca-documents-production/applications/123/tax-return.pdf";
            DocumentClassification classification = DocumentClassification.VERIFIED;
            LocalDateTime uploadedAt = LocalDateTime.now().minusHours(1);
            
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("confidenceScore", 0.97);
            metadata.put("pageCount", 5);
            metadata.put("fileSize", 1024567);
            
            // When
            Document document = new Document(applicationId, type, storagePath, classification, uploadedAt, metadata);
            
            // Then
            assertNotNull(document);
            assertNull(document.getId());
            assertEquals(applicationId, document.getApplicationId());
            assertNull(document.getApplication());
            assertEquals(type, document.getType());
            assertEquals(storagePath, document.getStoragePath());
            assertEquals(classification, document.getClassification());
            assertEquals(uploadedAt, document.getUploadedAt());
            assertNotNull(document.getMetadata());
            assertEquals(3, document.getMetadata().size());
            assertEquals(0.97, document.getMetadata().get("confidenceScore"));
            assertEquals(5, document.getMetadata().get("pageCount"));
            assertEquals(1024567, document.getMetadata().get("fileSize"));
        }
        
        @Test
        @DisplayName("Should validate required fields")
        void shouldValidateRequiredFields() {
            // Given
            Document document = new Document();
            
            // When
            Set<ConstraintViolation<Document>> violations = validator.validate(document);
            
            // Then
            assertEquals(3, violations.size());
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("applicationId")));
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("type")));
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("storagePath")));
        }
        
        @Test
        @DisplayName("Should validate storage path size constraint")
        void shouldValidateStoragePathSizeConstraint() {
            // Given
            Document document = new Document();
            document.setApplicationId(UUID.randomUUID());
            document.setType(DocumentType.BANK_STATEMENT);
            
            // Create a storage path that exceeds the 1024 character limit
            StringBuilder longPath = new StringBuilder();
            for (int i = 0; i < 1030; i++) {
                longPath.append("a");
            }
            document.setStoragePath(longPath.toString());
            
            // When
            Set<ConstraintViolation<Document>> violations = validator.validate(document);
            
            // Then
            assertEquals(1, violations.size());
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("storagePath")));
        }
        
        @Test
        @DisplayName("Should create document with builder")
        void shouldCreateDocumentWithBuilder() {
            // Given
            UUID applicationId = UUID.randomUUID();
            DocumentType type = DocumentType.INVOICE;
            String storagePath = "mca-documents-production/applications/123/invoice.pdf";
            
            // When
            Document document = new Document.Builder(applicationId, type, storagePath)
                .withClassification(DocumentClassification.NEEDS_REVIEW)
                .withConfidenceScore(0.85)
                .addMetadata("pageCount", 3)
                .build();
            
            // Then
            assertNotNull(document);
            assertEquals(applicationId, document.getApplicationId());
            assertEquals(type, document.getType());
            assertEquals(storagePath, document.getStoragePath());
            assertEquals(DocumentClassification.NEEDS_REVIEW, document.getClassification());
            assertEquals(0.85, document.getConfidenceScore());
            assertEquals(3, document.getMetadataValue("pageCount"));
        }
    }
    
    /**
     * Tests for enum mapping and classification.
     */
    @Nested
    @DisplayName("Enum Mapping Tests")
    class EnumMappingTests {
        
        @Test
        @DisplayName("Should map DocumentType enum values correctly")
        void shouldMapDocumentTypeEnumValuesCorrectly() {
            // Given
            Document document = new Document();
            
            // When/Then - Test all enum values
            document.setType(DocumentType.BANK_STATEMENT);
            assertEquals(DocumentType.BANK_STATEMENT, document.getType());
            
            document.setType(DocumentType.TAX_RETURN);
            assertEquals(DocumentType.TAX_RETURN, document.getType());
            
            document.setType(DocumentType.BUSINESS_LICENSE);
            assertEquals(DocumentType.BUSINESS_LICENSE, document.getType());
            
            document.setType(DocumentType.INVOICE);
            assertEquals(DocumentType.INVOICE, document.getType());
            
            document.setType(DocumentType.ID_VERIFICATION);
            assertEquals(DocumentType.ID_VERIFICATION, document.getType());
            
            document.setType(DocumentType.MISCELLANEOUS);
            assertEquals(DocumentType.MISCELLANEOUS, document.getType());
        }
        
        @Test
        @DisplayName("Should map DocumentClassification enum values correctly")
        void shouldMapDocumentClassificationEnumValuesCorrectly() {
            // Given
            Document document = new Document();
            
            // When/Then - Test all enum values
            document.setClassification(DocumentClassification.VERIFIED);
            assertEquals(DocumentClassification.VERIFIED, document.getClassification());
            
            document.setClassification(DocumentClassification.NEEDS_REVIEW);
            assertEquals(DocumentClassification.NEEDS_REVIEW, document.getClassification());
            
            document.setClassification(DocumentClassification.FLAGGED);
            assertEquals(DocumentClassification.FLAGGED, document.getClassification());
            
            document.setClassification(DocumentClassification.REJECTED);
            assertEquals(DocumentClassification.REJECTED, document.getClassification());
            
            document.setClassification(DocumentClassification.UNCLASSIFIED);
            assertEquals(DocumentClassification.UNCLASSIFIED, document.getClassification());
        }
        
        @Test
        @DisplayName("Should set classification based on confidence score")
        void shouldSetClassificationBasedOnConfidenceScore() {
            // Given
            Document document = new Document();
            
            // When/Then - Test classification thresholds
            document.setConfidenceScore(0.97);
            assertEquals(DocumentClassification.VERIFIED, document.getClassification());
            assertEquals(0.97, document.getConfidenceScore());
            
            document.setConfidenceScore(0.85);
            assertEquals(DocumentClassification.NEEDS_REVIEW, document.getClassification());
            assertEquals(0.85, document.getConfidenceScore());
            
            document.setConfidenceScore(0.65);
            assertEquals(DocumentClassification.FLAGGED, document.getClassification());
            assertEquals(0.65, document.getConfidenceScore());
            
            document.setConfidenceScore(0.45);
            assertEquals(DocumentClassification.REJECTED, document.getClassification());
            assertEquals(0.45, document.getConfidenceScore());
            
            document.setConfidenceScore(0.30);
            assertEquals(DocumentClassification.REJECTED, document.getClassification());
            assertEquals(0.30, document.getConfidenceScore());
        }
        
        @Test
        @DisplayName("Should identify document type from content")
        void shouldIdentifyDocumentTypeFromContent() {
            // When/Then - Test document type identification from file names
            assertEquals(DocumentType.BANK_STATEMENT, 
                DocumentType.identifyFromContent("application/pdf", "bank_statement_march_2023.pdf"));
            
            assertEquals(DocumentType.TAX_RETURN, 
                DocumentType.identifyFromContent("application/pdf", "2022_tax_return.pdf"));
            
            assertEquals(DocumentType.BUSINESS_LICENSE, 
                DocumentType.identifyFromContent("image/jpeg", "business_license.jpg"));
            
            assertEquals(DocumentType.INVOICE, 
                DocumentType.identifyFromContent("application/pdf", "invoice_123456.pdf"));
            
            assertEquals(DocumentType.ID_VERIFICATION, 
                DocumentType.identifyFromContent("image/jpeg", "drivers_license.jpg"));
            
            assertEquals(DocumentType.MISCELLANEOUS, 
                DocumentType.identifyFromContent("application/pdf", "document.pdf"));
            
            assertEquals(DocumentType.MISCELLANEOUS, 
                DocumentType.identifyFromContent("application/pdf", null));
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
            Document document = new Document();
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("confidenceScore", 0.95);
            metadata.put("pageCount", 3);
            metadata.put("extractedFields", Map.of("name", "John Doe", "amount", 5000.00));
            
            // When
            document.setMetadata(metadata);
            
            // Then
            assertNotNull(document.getMetadataJson());
            assertTrue(JsonUtil.isValidJson(document.getMetadataJson()));
            
            // Verify the JSON contains the expected data
            Map<String, Object> parsedMetadata = JsonUtil.fromJson(
                document.getMetadataJson(), 
                new TypeReference<Map<String, Object>>() {}
            );
            assertEquals(3, parsedMetadata.size());
            assertEquals(0.95, parsedMetadata.get("confidenceScore"));
            assertEquals(3, parsedMetadata.get("pageCount"));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> extractedFields = (Map<String, Object>) parsedMetadata.get("extractedFields");
            assertEquals("John Doe", extractedFields.get("name"));
            assertEquals(5000.00, extractedFields.get("amount"));
        }
        
        @Test
        @DisplayName("Should convert JSON string to metadata map")
        void shouldConvertJsonStringToMetadataMap() throws Exception {
            // Given
            Document document = new Document();
            String metadataJson = "{\"confidenceScore\":0.95,\"pageCount\":3,\"extractedFields\":{\"name\":\"John Doe\",\"amount\":5000.0}}";
            
            // When
            document.setMetadataJson(metadataJson);
            
            // Then
            assertNotNull(document.getMetadata());
            assertEquals(3, document.getMetadata().size());
            assertEquals(0.95, document.getMetadata().get("confidenceScore"));
            assertEquals(3, document.getMetadata().get("pageCount"));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> extractedFields = (Map<String, Object>) document.getMetadata().get("extractedFields");
            assertEquals("John Doe", extractedFields.get("name"));
            assertEquals(5000.0, extractedFields.get("amount"));
        }
        
        @Test
        @DisplayName("Should add individual metadata values")
        void shouldAddIndividualMetadataValues() {
            // Given
            Document document = new Document();
            
            // When
            document.addMetadata("confidenceScore", 0.95);
            document.addMetadata("pageCount", 3);
            document.addMetadata("fileName", "bank_statement.pdf");
            
            // Then
            Map<String, Object> metadata = document.getMetadata();
            assertEquals(3, metadata.size());
            assertEquals(0.95, metadata.get("confidenceScore"));
            assertEquals(3, metadata.get("pageCount"));
            assertEquals("bank_statement.pdf", metadata.get("fileName"));
        }
        
        @Test
        @DisplayName("Should retrieve individual metadata values with correct type")
        void shouldRetrieveIndividualMetadataValuesWithCorrectType() {
            // Given
            Document document = new Document();
            document.addMetadata("confidenceScore", 0.95);
            document.addMetadata("pageCount", 3);
            document.addMetadata("fileName", "bank_statement.pdf");
            
            // When/Then
            assertEquals(0.95, document.<Double>getMetadataValue("confidenceScore"));
            assertEquals(3, document.<Integer>getMetadataValue("pageCount"));
            assertEquals("bank_statement.pdf", document.<String>getMetadataValue("fileName"));
            assertNull(document.getMetadataValue("nonExistentKey"));
        }
        
        @Test
        @DisplayName("Should handle null or empty metadata")
        void shouldHandleNullOrEmptyMetadata() {
            // Given
            Document document = new Document();
            
            // When
            document.setMetadata(null);
            
            // Then
            assertNotNull(document.getMetadata());
            assertTrue(document.getMetadata().isEmpty());
            assertEquals("{}", document.getMetadataJson());
            
            // When
            document.setMetadataJson(null);
            
            // Then
            assertNotNull(document.getMetadata());
            assertTrue(document.getMetadata().isEmpty());
            
            // When
            document.setMetadataJson("");
            
            // Then
            assertNotNull(document.getMetadata());
            assertTrue(document.getMetadata().isEmpty());
        }
    }
    
    /**
     * Tests for relationship with Application entity.
     */
    @Nested
    @DisplayName("Relationship Tests")
    class RelationshipTests {
        
        @Test
        @DisplayName("Should maintain bidirectional relationship with Application entity")
        void shouldMaintainBidirectionalRelationshipWithApplicationEntity() {
            // Given
            Document document = new Document(UUID.randomUUID(), DocumentType.BANK_STATEMENT, "mca-documents-production/applications/123/bank-statement.pdf");
            Application application = new Application();
            application.setId(UUID.randomUUID());
            
            // When
            document.setApplication(application);
            
            // Then
            assertSame(application, document.getApplication());
            assertEquals(application.getId(), document.getApplicationId());
        }
        
        @Test
        @DisplayName("Should update applicationId when application is set")
        void shouldUpdateApplicationIdWhenApplicationIsSet() {
            // Given
            Document document = new Document();
            Application application = new Application();
            UUID applicationId = UUID.randomUUID();
            application.setId(applicationId);
            
            // When
            document.setApplication(application);
            
            // Then
            assertEquals(applicationId, document.getApplicationId());
        }
        
        @Test
        @DisplayName("Should not update applicationId when application has no ID")
        void shouldNotUpdateApplicationIdWhenApplicationHasNoId() {
            // Given
            UUID originalApplicationId = UUID.randomUUID();
            Document document = new Document(originalApplicationId, DocumentType.BANK_STATEMENT, "mca-documents-production/applications/123/bank-statement.pdf");
            Application application = new Application();
            
            // When
            document.setApplication(application);
            
            // Then
            assertEquals(originalApplicationId, document.getApplicationId());
        }
    }
    
    /**
     * Tests for persistence and retrieval of Document entity.
     */
    @Nested
    @DisplayName("Persistence Tests")
    class PersistenceTests {
        
        @Test
        @DisplayName("Should persist and retrieve document with all fields")
        void shouldPersistAndRetrieveDocumentWithAllFields() {
            // Given
            UUID applicationId = UUID.randomUUID();
            DocumentType type = DocumentType.BANK_STATEMENT;
            String storagePath = "mca-documents-production/applications/123/bank-statement.pdf";
            DocumentClassification classification = DocumentClassification.VERIFIED;
            LocalDateTime uploadedAt = LocalDateTime.now().minusHours(1);
            
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("confidenceScore", 0.97);
            metadata.put("pageCount", 5);
            
            Document document = new Document(applicationId, type, storagePath, classification, uploadedAt, metadata);
            
            // When
            Document savedDocument = entityManager.persistAndFlush(document);
            entityManager.clear();
            Document retrievedDocument = entityManager.find(Document.class, savedDocument.getId());
            
            // Then
            assertNotNull(retrievedDocument);
            assertEquals(savedDocument.getId(), retrievedDocument.getId());
            assertEquals(applicationId, retrievedDocument.getApplicationId());
            assertEquals(type, retrievedDocument.getType());
            assertEquals(storagePath, retrievedDocument.getStoragePath());
            assertEquals(classification, retrievedDocument.getClassification());
            assertEquals(uploadedAt, retrievedDocument.getUploadedAt());
            
            // Verify metadata was persisted correctly
            Map<String, Object> retrievedMetadata = retrievedDocument.getMetadata();
            assertEquals(2, retrievedMetadata.size());
            assertEquals(0.97, retrievedMetadata.get("confidenceScore"));
            assertEquals(5, retrievedMetadata.get("pageCount"));
        }
        
        @Test
        @DisplayName("Should persist and retrieve document with application relationship")
        void shouldPersistAndRetrieveDocumentWithApplicationRelationship() {
            // Given
            Application application = new Application();
            entityManager.persistAndFlush(application);
            
            Document document = new Document(application.getId(), DocumentType.BANK_STATEMENT, "mca-documents-production/applications/123/bank-statement.pdf");
            document.setApplication(application);
            
            // When
            Document savedDocument = entityManager.persistAndFlush(document);
            entityManager.clear();
            Document retrievedDocument = entityManager.find(Document.class, savedDocument.getId());
            
            // Then
            assertNotNull(retrievedDocument);
            assertEquals(application.getId(), retrievedDocument.getApplicationId());
            assertNotNull(retrievedDocument.getApplication());
            assertEquals(application.getId(), retrievedDocument.getApplication().getId());
        }
        
        @Test
        @DisplayName("Should persist and retrieve document with enum values")
        void shouldPersistAndRetrieveDocumentWithEnumValues() {
            // Given
            Document document = new Document(
                UUID.randomUUID(),
                DocumentType.TAX_RETURN,
                "mca-documents-production/applications/123/tax-return.pdf",
                DocumentClassification.NEEDS_REVIEW,
                LocalDateTime.now(),
                Map.of("confidenceScore", 0.85)
            );
            
            // When
            Document savedDocument = entityManager.persistAndFlush(document);
            entityManager.clear();
            Document retrievedDocument = entityManager.find(Document.class, savedDocument.getId());
            
            // Then
            assertNotNull(retrievedDocument);
            assertEquals(DocumentType.TAX_RETURN, retrievedDocument.getType());
            assertEquals(DocumentClassification.NEEDS_REVIEW, retrievedDocument.getClassification());
            assertEquals(0.85, retrievedDocument.getConfidenceScore());
        }
    }
    
    /**
     * Tests for utility methods in the Document entity.
     */
    @Nested
    @DisplayName("Utility Method Tests")
    class UtilityMethodTests {
        
        @Test
        @DisplayName("Should extract file name from storage path")
        void shouldExtractFileNameFromStoragePath() {
            // Given
            Document document = new Document();
            
            // When/Then
            document.setStoragePath("mca-documents-production/applications/123/bank-statement.pdf");
            assertEquals("bank-statement.pdf", document.getFileName());
            
            document.setStoragePath("mca-documents-production/bank-statement.pdf");
            assertEquals("bank-statement.pdf", document.getFileName());
            
            document.setStoragePath("bank-statement.pdf");
            assertEquals("bank-statement.pdf", document.getFileName());
            
            document.setStoragePath("");
            assertEquals("", document.getFileName());
            
            document.setStoragePath(null);
            assertEquals("", document.getFileName());
        }
        
        @Test
        @DisplayName("Should extract file extension from storage path")
        void shouldExtractFileExtensionFromStoragePath() {
            // Given
            Document document = new Document();
            
            // When/Then
            document.setStoragePath("mca-documents-production/applications/123/bank-statement.pdf");
            assertEquals("pdf", document.getFileExtension());
            
            document.setStoragePath("mca-documents-production/applications/123/invoice.jpg");
            assertEquals("jpg", document.getFileExtension());
            
            document.setStoragePath("mca-documents-production/applications/123/document");
            assertEquals("", document.getFileExtension());
            
            document.setStoragePath("");
            assertEquals("", document.getFileExtension());
            
            document.setStoragePath(null);
            assertEquals("", document.getFileExtension());
        }
        
        @Test
        @DisplayName("Should determine MIME type from file extension")
        void shouldDetermineMimeTypeFromFileExtension() {
            // Given
            Document document = new Document();
            
            // When/Then
            document.setStoragePath("mca-documents-production/applications/123/document.pdf");
            assertEquals("application/pdf", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/image.jpg");
            assertEquals("image/jpeg", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/image.jpeg");
            assertEquals("image/jpeg", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/image.png");
            assertEquals("image/png", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/image.tiff");
            assertEquals("image/tiff", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/document.doc");
            assertEquals("application/msword", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/document.docx");
            assertEquals("application/vnd.openxmlformats-officedocument.wordprocessingml.document", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/spreadsheet.xls");
            assertEquals("application/vnd.ms-excel", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/spreadsheet.xlsx");
            assertEquals("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", document.getMimeType());
            
            document.setStoragePath("mca-documents-production/applications/123/unknown.xyz");
            assertEquals("application/octet-stream", document.getMimeType());
        }
        
        @Test
        @DisplayName("Should determine if document requires manual review")
        void shouldDetermineIfDocumentRequiresManualReview() {
            // Given
            Document document = new Document();
            
            // When/Then
            document.setClassification(DocumentClassification.VERIFIED);
            assertFalse(document.requiresManualReview());
            
            document.setClassification(DocumentClassification.NEEDS_REVIEW);
            assertTrue(document.requiresManualReview());
            
            document.setClassification(DocumentClassification.FLAGGED);
            assertTrue(document.requiresManualReview());
            
            document.setClassification(DocumentClassification.REJECTED);
            assertFalse(document.requiresManualReview());
            
            document.setClassification(DocumentClassification.UNCLASSIFIED);
            assertFalse(document.requiresManualReview());
        }
        
        @Test
        @DisplayName("Should determine if document is acceptable")
        void shouldDetermineIfDocumentIsAcceptable() {
            // Given
            Document document = new Document();
            
            // When/Then
            document.setClassification(DocumentClassification.VERIFIED);
            assertTrue(document.isAcceptable());
            
            document.setClassification(DocumentClassification.NEEDS_REVIEW);
            assertTrue(document.isAcceptable());
            
            document.setClassification(DocumentClassification.FLAGGED);
            assertFalse(document.isAcceptable());
            
            document.setClassification(DocumentClassification.REJECTED);
            assertFalse(document.isAcceptable());
            
            document.setClassification(DocumentClassification.UNCLASSIFIED);
            assertFalse(document.isAcceptable());
        }
        
        @Test
        @DisplayName("Should extract bucket name from storage path")
        void shouldExtractBucketNameFromStoragePath() {
            // Given
            Document document = new Document();
            
            // When/Then
            document.setStoragePath("mca-documents-production/applications/123/bank-statement.pdf");
            assertEquals("mca-documents-production", document.getBucketName());
            
            document.setStoragePath("bucket/file.pdf");
            assertEquals("bucket", document.getBucketName());
            
            document.setStoragePath("file.pdf");
            assertEquals("", document.getBucketName());
            
            document.setStoragePath("");
            assertEquals("", document.getBucketName());
            
            document.setStoragePath(null);
            assertEquals("", document.getBucketName());
        }
        
        @Test
        @DisplayName("Should extract object key from storage path")
        void shouldExtractObjectKeyFromStoragePath() {
            // Given
            Document document = new Document();
            
            // When/Then
            document.setStoragePath("mca-documents-production/applications/123/bank-statement.pdf");
            assertEquals("applications/123/bank-statement.pdf", document.getObjectKey());
            
            document.setStoragePath("bucket/file.pdf");
            assertEquals("file.pdf", document.getObjectKey());
            
            document.setStoragePath("file.pdf");
            assertEquals("file.pdf", document.getObjectKey());
            
            document.setStoragePath("");
            assertEquals("", document.getObjectKey());
            
            document.setStoragePath(null);
            assertEquals("", document.getObjectKey());
        }
        
        @Test
        @DisplayName("Should generate proper toString representation")
        void shouldGenerateProperToStringRepresentation() {
            // Given
            UUID id = UUID.randomUUID();
            UUID applicationId = UUID.randomUUID();
            Document document = new Document(applicationId, DocumentType.BANK_STATEMENT, "mca-documents-production/applications/123/bank-statement.pdf");
            document.setId(id);
            document.setClassification(DocumentClassification.VERIFIED);
            document.setConfidenceScore(0.97);
            
            // When
            String toString = document.toString();
            
            // Then
            assertNotNull(toString);
            assertTrue(toString.contains(id.toString()));
            assertTrue(toString.contains(applicationId.toString()));
            assertTrue(toString.contains("BANK_STATEMENT"));
            assertTrue(toString.contains("bank-statement.pdf"));
            assertTrue(toString.contains("VERIFIED"));
            assertTrue(toString.contains("0.97"));
        }
        
        @Test
        @DisplayName("Should implement equals and hashCode correctly")
        void shouldImplementEqualsAndHashCodeCorrectly() {
            // Given
            UUID id = UUID.randomUUID();
            
            Document document1 = new Document();
            document1.setId(id);
            
            Document document2 = new Document();
            document2.setId(id);
            
            Document document3 = new Document();
            document3.setId(UUID.randomUUID());
            
            // When/Then - equals
            assertEquals(document1, document1); // Same instance
            assertEquals(document1, document2); // Same ID
            assertNotEquals(document1, document3); // Different ID
            assertNotEquals(document1, null); // Null comparison
            assertNotEquals(document1, new Object()); // Different type
            
            // When/Then - hashCode
            assertEquals(document1.hashCode(), document2.hashCode()); // Same ID
            assertNotEquals(document1.hashCode(), document3.hashCode()); // Different ID
        }
    }
}