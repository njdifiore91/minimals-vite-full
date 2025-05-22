package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the Document entity class.
 * 
 * These tests verify JPA mapping, field validation, and relationships for the Document entity.
 * Tests include validation of required fields, proper mapping of enum values for document type
 * and classification, JSON conversion for the metadata field, and the Many-to-One relationship
 * with the Application entity.
 */
@DisplayName("Document Entity Tests")
class DocumentTest {

    private UUID applicationId;
    private DocumentType documentType;
    private String storagePath;
    private String classification;
    private LocalDateTime uploadedAt;
    private Map<String, Object> metadata;

    @BeforeEach
    void setUp() {
        applicationId = UUID.randomUUID();
        documentType = DocumentType.BANK_STATEMENT;
        storagePath = "s3://mca-documents-production/applications/" + applicationId + "/bank-statement.pdf";
        classification = "Monthly Bank Statement";
        uploadedAt = LocalDateTime.now();
        metadata = new HashMap<>();
        metadata.put("pageCount", 5);
        metadata.put("fileSize", 1024567);
        metadata.put("mimeType", "application/pdf");
        
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("accountNumber", 0.95);
        confidenceScores.put("accountName", 0.98);
        confidenceScores.put("bankName", 0.99);
        metadata.put("confidenceScores", confidenceScores);
    }

    @Nested
    @DisplayName("Constructor Tests")
    class ConstructorTests {

        @Test
        @DisplayName("Default constructor creates empty metadata map")
        void defaultConstructorCreatesEmptyMetadataMap() {
            Document document = new Document();
            assertNotNull(document.getMetadata());
            assertTrue(document.getMetadata().isEmpty());
        }

        @Test
        @DisplayName("Required fields constructor sets fields correctly")
        void requiredFieldsConstructorSetsFieldsCorrectly() {
            Document document = new Document(applicationId, documentType, storagePath);
            
            assertEquals(applicationId, document.getApplicationId());
            assertEquals(documentType, document.getType());
            assertEquals(storagePath, document.getStoragePath());
            assertNotNull(document.getUploadedAt());
            assertNotNull(document.getMetadata());
            assertTrue(document.getMetadata().isEmpty());
        }

        @Test
        @DisplayName("Full constructor sets all fields correctly")
        void fullConstructorSetsAllFieldsCorrectly() {
            Document document = new Document(applicationId, documentType, storagePath, 
                                           classification, uploadedAt, metadata);
            
            assertEquals(applicationId, document.getApplicationId());
            assertEquals(documentType, document.getType());
            assertEquals(storagePath, document.getStoragePath());
            assertEquals(classification, document.getClassification());
            assertEquals(uploadedAt, document.getUploadedAt());
            assertEquals(metadata, document.getMetadata());
        }

        @Test
        @DisplayName("Builder creates document with all fields correctly")
        void builderCreatesDocumentWithAllFieldsCorrectly() {
            Document document = new Document.Builder(applicationId, documentType, storagePath)
                    .withClassification(classification)
                    .withUploadedAt(uploadedAt)
                    .withMetadata(metadata)
                    .build();
            
            assertEquals(applicationId, document.getApplicationId());
            assertEquals(documentType, document.getType());
            assertEquals(storagePath, document.getStoragePath());
            assertEquals(classification, document.getClassification());
            assertEquals(uploadedAt, document.getUploadedAt());
            assertEquals(metadata, document.getMetadata());
        }
    }

    @Nested
    @DisplayName("Field Validation Tests")
    class FieldValidationTests {

        @Test
        @DisplayName("Document with null applicationId is invalid for processing")
        void documentWithNullApplicationIdIsInvalidForProcessing() {
            Document document = new Document(null, documentType, storagePath);
            assertFalse(document.isValidForProcessing());
        }

        @Test
        @DisplayName("Document with null type is invalid for processing")
        void documentWithNullTypeIsInvalidForProcessing() {
            Document document = new Document(applicationId, null, storagePath);
            assertFalse(document.isValidForProcessing());
        }

        @Test
        @DisplayName("Document with null storagePath is invalid for processing")
        void documentWithNullStoragePathIsInvalidForProcessing() {
            Document document = new Document(applicationId, documentType, null);
            assertFalse(document.isValidForProcessing());
        }

        @Test
        @DisplayName("Document with empty storagePath is invalid for processing")
        void documentWithEmptyStoragePathIsInvalidForProcessing() {
            Document document = new Document(applicationId, documentType, "");
            assertFalse(document.isValidForProcessing());
        }

        @Test
        @DisplayName("Document with null uploadedAt is invalid for processing")
        void documentWithNullUploadedAtIsInvalidForProcessing() {
            Document document = new Document(applicationId, documentType, storagePath);
            document.setUploadedAt(null);
            assertFalse(document.isValidForProcessing());
        }

        @Test
        @DisplayName("Document with all required fields is valid for processing")
        void documentWithAllRequiredFieldsIsValidForProcessing() {
            Document document = new Document(applicationId, documentType, storagePath);
            assertTrue(document.isValidForProcessing());
        }

        @Test
        @DisplayName("Document with invalid storage path format is detected")
        void documentWithInvalidStoragePathFormatIsDetected() {
            Document document = new Document(applicationId, documentType, "invalid-path");
            assertFalse(document.hasValidStorage());
        }

        @Test
        @DisplayName("Document with valid S3 storage path is detected")
        void documentWithValidS3StoragePathIsDetected() {
            Document document = new Document(applicationId, documentType, storagePath);
            assertTrue(document.hasValidStorage());
        }
    }

    @Nested
    @DisplayName("Enum Mapping Tests")
    class EnumMappingTests {

        @Test
        @DisplayName("Document type is correctly mapped")
        void documentTypeIsCorrectlyMapped() {
            Document document = new Document(applicationId, DocumentType.BANK_STATEMENT, storagePath);
            assertEquals(DocumentType.BANK_STATEMENT, document.getType());
            assertEquals("Bank Statement", document.getType().getDescription());
        }

        @Test
        @DisplayName("Financial document is correctly identified")
        void financialDocumentIsCorrectlyIdentified() {
            Document bankStatement = new Document(applicationId, DocumentType.BANK_STATEMENT, storagePath);
            Document taxReturn = new Document(applicationId, DocumentType.TAX_RETURN, storagePath);
            Document invoice = new Document(applicationId, DocumentType.INVOICE, storagePath);
            Document license = new Document(applicationId, DocumentType.BUSINESS_LICENSE, storagePath);
            
            assertTrue(bankStatement.isFinancialDocument());
            assertTrue(taxReturn.isFinancialDocument());
            assertTrue(invoice.isFinancialDocument());
            assertFalse(license.isFinancialDocument());
        }

        @Test
        @DisplayName("Document with PII is correctly identified")
        void documentWithPIIIsCorrectlyIdentified() {
            Document idVerification = new Document(applicationId, DocumentType.ID_VERIFICATION, storagePath);
            Document taxReturn = new Document(applicationId, DocumentType.TAX_RETURN, storagePath);
            Document bankStatement = new Document(applicationId, DocumentType.BANK_STATEMENT, storagePath);
            
            assertTrue(idVerification.containsPII());
            assertTrue(taxReturn.containsPII());
            assertFalse(bankStatement.containsPII());
        }

        @Test
        @DisplayName("OCR confidence threshold is correctly determined by document type")
        void ocrConfidenceThresholdIsCorrectlyDeterminedByDocumentType() {
            Document bankStatement = new Document(applicationId, DocumentType.BANK_STATEMENT, storagePath);
            Document taxReturn = new Document(applicationId, DocumentType.TAX_RETURN, storagePath);
            Document idVerification = new Document(applicationId, DocumentType.ID_VERIFICATION, storagePath);
            Document misc = new Document(applicationId, DocumentType.MISCELLANEOUS, storagePath);
            
            assertEquals(0.85, bankStatement.getOcrConfidenceThreshold());
            assertEquals(0.80, taxReturn.getOcrConfidenceThreshold());
            assertEquals(0.90, idVerification.getOcrConfidenceThreshold());
            assertEquals(0.65, misc.getOcrConfidenceThreshold());
        }
    }

    @Nested
    @DisplayName("JSON Metadata Tests")
    class JsonMetadataTests {

        @Test
        @DisplayName("Metadata is correctly converted to JSON")
        void metadataIsCorrectlyConvertedToJson() throws JsonUtil.JsonConversionException {
            Document document = new Document(applicationId, documentType, storagePath);
            document.setMetadata(metadata);
            
            String metadataJson = document.getMetadataJson();
            assertNotNull(metadataJson);
            assertTrue(JsonUtil.isValidJson(metadataJson));
            
            Map<String, Object> deserializedMetadata = JsonUtil.fromJson(metadataJson, new TypeReference<Map<String, Object>>() {});
            assertEquals(metadata.size(), deserializedMetadata.size());
            assertEquals(metadata.get("pageCount"), deserializedMetadata.get("pageCount"));
            assertEquals(metadata.get("fileSize"), deserializedMetadata.get("fileSize"));
            assertEquals(metadata.get("mimeType"), deserializedMetadata.get("mimeType"));
        }

        @Test
        @DisplayName("JSON is correctly converted to metadata")
        void jsonIsCorrectlyConvertedToMetadata() throws JsonUtil.JsonConversionException {
            Document document = new Document(applicationId, documentType, storagePath);
            String metadataJson = JsonUtil.toJson(metadata);
            document.setMetadataJson(metadataJson);
            
            Map<String, Object> retrievedMetadata = document.getMetadata();
            assertNotNull(retrievedMetadata);
            assertEquals(metadata.size(), retrievedMetadata.size());
            assertEquals(metadata.get("pageCount"), retrievedMetadata.get("pageCount"));
            assertEquals(metadata.get("fileSize"), retrievedMetadata.get("fileSize"));
            assertEquals(metadata.get("mimeType"), retrievedMetadata.get("mimeType"));
        }

        @Test
        @DisplayName("Metadata can be added incrementally")
        void metadataCanBeAddedIncrementally() {
            Document document = new Document(applicationId, documentType, storagePath);
            document.addMetadata("pageCount", 5);
            document.addMetadata("fileSize", 1024567);
            document.addMetadata("mimeType", "application/pdf");
            
            Map<String, Object> retrievedMetadata = document.getMetadata();
            assertEquals(3, retrievedMetadata.size());
            assertEquals(5, retrievedMetadata.get("pageCount"));
            assertEquals(1024567, retrievedMetadata.get("fileSize"));
            assertEquals("application/pdf", retrievedMetadata.get("mimeType"));
        }

        @Test
        @DisplayName("Specific metadata value can be retrieved")
        void specificMetadataValueCanBeRetrieved() {
            Document document = new Document(applicationId, documentType, storagePath);
            document.setMetadata(metadata);
            
            Integer pageCount = document.getMetadataValue("pageCount");
            assertEquals(5, pageCount);
            
            String mimeType = document.getMetadataValue("mimeType");
            assertEquals("application/pdf", mimeType);
        }

        @Test
        @DisplayName("Confidence scores can be added and retrieved")
        void confidenceScoresCanBeAddedAndRetrieved() {
            Document document = new Document(applicationId, documentType, storagePath);
            
            Map<String, Double> confidenceScores = new HashMap<>();
            confidenceScores.put("accountNumber", 0.95);
            confidenceScores.put("accountName", 0.98);
            confidenceScores.put("bankName", 0.99);
            
            document.addConfidenceScores(confidenceScores);
            
            Map<String, Double> retrievedScores = document.getConfidenceScores();
            assertEquals(3, retrievedScores.size());
            assertEquals(0.95, retrievedScores.get("accountNumber"));
            assertEquals(0.98, retrievedScores.get("accountName"));
            assertEquals(0.99, retrievedScores.get("bankName"));
        }

        @Test
        @DisplayName("Specific confidence score can be retrieved")
        void specificConfidenceScoreCanBeRetrieved() {
            Document document = new Document(applicationId, documentType, storagePath);
            
            Map<String, Double> confidenceScores = new HashMap<>();
            confidenceScores.put("accountNumber", 0.95);
            confidenceScores.put("accountName", 0.98);
            confidenceScores.put("bankName", 0.99);
            
            document.addConfidenceScores(confidenceScores);
            
            Double accountNumberConfidence = document.getConfidenceScore("accountNumber");
            assertEquals(0.95, accountNumberConfidence);
        }

        @Test
        @DisplayName("Document classification confidence can be checked")
        void documentClassificationConfidenceCanBeChecked() {
            Document document = new Document(applicationId, documentType, storagePath);
            
            Map<String, Double> confidenceScores = new HashMap<>();
            confidenceScores.put("classification", 0.95);
            
            document.addConfidenceScores(confidenceScores);
            
            assertTrue(document.isClassifiedWithHighConfidence());
            
            // Test with confidence below threshold
            confidenceScores.put("classification", 0.60);
            document.addConfidenceScores(confidenceScores);
            
            assertFalse(document.isClassifiedWithHighConfidence());
        }
    }

    @Nested
    @DisplayName("Storage Path Tests")
    class StoragePathTests {

        @Test
        @DisplayName("Bucket name is correctly extracted from storage path")
        void bucketNameIsCorrectlyExtractedFromStoragePath() {
            Document document = new Document(applicationId, documentType, 
                                           "s3://mca-documents-production/applications/doc.pdf");
            
            assertEquals("mca-documents-production", document.getBucketName());
        }

        @Test
        @DisplayName("Object key is correctly extracted from storage path")
        void objectKeyIsCorrectlyExtractedFromStoragePath() {
            Document document = new Document(applicationId, documentType, 
                                           "s3://mca-documents-production/applications/doc.pdf");
            
            assertEquals("applications/doc.pdf", document.getObjectKey());
        }

        @Test
        @DisplayName("Invalid storage path returns null bucket name")
        void invalidStoragePathReturnsNullBucketName() {
            Document document = new Document(applicationId, documentType, "invalid-path");
            assertNull(document.getBucketName());
        }

        @Test
        @DisplayName("Invalid storage path returns null object key")
        void invalidStoragePathReturnsNullObjectKey() {
            Document document = new Document(applicationId, documentType, "invalid-path");
            assertNull(document.getObjectKey());
        }

        @Test
        @DisplayName("Storage path without object key returns empty object key")
        void storagePathWithoutObjectKeyReturnsEmptyObjectKey() {
            Document document = new Document(applicationId, documentType, "s3://mca-documents-production");
            assertEquals("", document.getObjectKey());
        }
    }

    @Nested
    @DisplayName("Application Relationship Tests")
    class ApplicationRelationshipTests {

        @Test
        @DisplayName("Application can be set and retrieved")
        void applicationCanBeSetAndRetrieved() {
            Document document = new Document(applicationId, documentType, storagePath);
            Application application = new Application();
            application.setId(applicationId);
            
            document.setApplication(application);
            
            assertSame(application, document.getApplication());
            assertEquals(applicationId, document.getApplicationId());
        }

        @Test
        @DisplayName("Setting application updates applicationId")
        void settingApplicationUpdatesApplicationId() {
            Document document = new Document();
            Application application = new Application();
            UUID newApplicationId = UUID.randomUUID();
            application.setId(newApplicationId);
            
            document.setApplication(application);
            
            assertEquals(newApplicationId, document.getApplicationId());
        }

        @Test
        @DisplayName("Setting null application does not change applicationId")
        void settingNullApplicationDoesNotChangeApplicationId() {
            Document document = new Document(applicationId, documentType, storagePath);
            UUID originalApplicationId = document.getApplicationId();
            
            document.setApplication(null);
            
            assertEquals(originalApplicationId, document.getApplicationId());
        }
    }

    @Nested
    @DisplayName("Timestamp Tests")
    class TimestampTests {

        @Test
        @DisplayName("UploadedAt is automatically set in constructor")
        void uploadedAtIsAutomaticallySetInConstructor() {
            Document document = new Document(applicationId, documentType, storagePath);
            assertNotNull(document.getUploadedAt());
            
            // Should be very close to now
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime uploadedAt = document.getUploadedAt();
            
            // Difference should be less than 1 second
            long secondsDifference = java.time.Duration.between(uploadedAt, now).getSeconds();
            assertTrue(secondsDifference < 1);
        }

        @Test
        @DisplayName("UploadedAt can be manually set")
        void uploadedAtCanBeManuallySet() {
            Document document = new Document(applicationId, documentType, storagePath);
            LocalDateTime customTime = LocalDateTime.of(2023, 1, 1, 12, 0);
            
            document.setUploadedAt(customTime);
            
            assertEquals(customTime, document.getUploadedAt());
        }
    }

    @Nested
    @DisplayName("Utility Method Tests")
    class UtilityMethodTests {

        @Test
        @DisplayName("toString returns expected format")
        void toStringReturnsExpectedFormat() {
            Document document = new Document(applicationId, documentType, storagePath, classification, uploadedAt, metadata);
            document.setId(UUID.randomUUID());
            
            String toString = document.toString();
            
            assertTrue(toString.contains("id="));
            assertTrue(toString.contains("applicationId="));
            assertTrue(toString.contains("type="));
            assertTrue(toString.contains("classification="));
            assertTrue(toString.contains("uploadedAt="));
            assertTrue(toString.contains("hasMetadata=true"));
            assertTrue(toString.contains("hasValidStorage=true"));
        }

        @Test
        @DisplayName("equals and hashCode are based on id")
        void equalsAndHashCodeAreBasedOnId() {
            Document document1 = new Document(applicationId, documentType, storagePath);
            Document document2 = new Document(applicationId, documentType, storagePath);
            
            // Different objects with null ids should not be equal
            assertNotEquals(document1, document2);
            
            // Same id should make them equal
            UUID id = UUID.randomUUID();
            document1.setId(id);
            document2.setId(id);
            
            assertEquals(document1, document2);
            assertEquals(document1.hashCode(), document2.hashCode());
            
            // Different ids should make them not equal
            document2.setId(UUID.randomUUID());
            assertNotEquals(document1, document2);
            assertNotEquals(document1.hashCode(), document2.hashCode());
        }

        @Test
        @DisplayName("hasMetadata correctly identifies documents with metadata")
        void hasMetadataCorrectlyIdentifiesDocumentsWithMetadata() {
            Document emptyDocument = new Document(applicationId, documentType, storagePath);
            assertFalse(emptyDocument.hasMetadata());
            
            Document documentWithMetadata = new Document(applicationId, documentType, storagePath);
            documentWithMetadata.addMetadata("key", "value");
            assertTrue(documentWithMetadata.hasMetadata());
        }
    }
}