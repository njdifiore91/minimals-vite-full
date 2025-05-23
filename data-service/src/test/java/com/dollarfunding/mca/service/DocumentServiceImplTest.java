package com.dollarfunding.mca.service;

import com.dollarfunding.mca.config.S3Config;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentClassification;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.exception.DocumentNotFoundException;
import com.dollarfunding.mca.exception.DocumentStorageException;
import com.dollarfunding.mca.exception.InvalidDocumentException;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.util.JsonUtil;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the DocumentServiceImpl class that manages document storage, retrieval, and metadata.
 * 
 * Tests verify S3 integration, document classification metadata management, secure URL generation,
 * and document association with applications. Uses Mockito to mock dependencies including S3 client,
 * DocumentRepository, and encryption utilities.
 * 
 * Includes tests for normal operation, edge cases, and error handling to ensure the service
 * functions correctly under all conditions.
 */
@ExtendWith(MockitoExtension.class)
public class DocumentServiceImplTest {

    @Mock
    private DocumentRepository documentRepository;

    @Mock
    private S3Config s3Config;

    @Mock
    private S3Client s3Client;

    @Mock
    private S3Presigner s3Presigner;

    @InjectMocks
    private DocumentServiceImpl documentService;

    private UUID testApplicationId;
    private UUID testDocumentId;
    private Document testDocument;
    private DocumentRequestDTO testDocumentRequest;
    private MultipartFile testFile;
    private URL testSignedUrl;

    @BeforeEach
    void setUp() throws Exception {
        // Initialize test data
        testApplicationId = UUID.randomUUID();
        testDocumentId = UUID.randomUUID();
        
        // Create test document
        testDocument = new Document();
        testDocument.setId(testDocumentId);
        testDocument.setApplicationId(testApplicationId);
        testDocument.setType(DocumentType.BANK_STATEMENT);
        testDocument.setStoragePath("documents/" + testApplicationId + "/test-document.pdf");
        testDocument.setClassification(DocumentClassification.VERIFIED);
        testDocument.setUploadedAt(LocalDateTime.now());
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("originalFilename", "test-document.pdf");
        metadata.put("contentType", "application/pdf");
        metadata.put("fileSize", 1024L);
        metadata.put("confidenceScore", 0.95);
        testDocument.setMetadata(metadata);

        // Create test document request
        testDocumentRequest = new DocumentRequestDTO();
        testDocumentRequest.setApplicationId(testApplicationId);
        testDocumentRequest.setType(DocumentType.BANK_STATEMENT);
        testDocumentRequest.setClassification("VERIFIED");
        testDocumentRequest.setClassificationConfidence(0.95);
        Map<String, Object> requestMetadata = new HashMap<>();
        requestMetadata.put("accountNumber", "XXXX1234");
        requestMetadata.put("bankName", "Test Bank");
        testDocumentRequest.setMetadata(requestMetadata);

        // Create test file
        byte[] fileContent = "Test file content".getBytes();
        testFile = new MockMultipartFile(
                "test-document.pdf",
                "test-document.pdf",
                "application/pdf",
                fileContent);

        // Create test signed URL
        testSignedUrl = new URL("https://test-bucket.s3.amazonaws.com/documents/" + testApplicationId + "/test-document.pdf?signature=abc123");

        // Configure mocks
        when(s3Config.getBucketName()).thenReturn("test-bucket");
        when(s3Config.generateSignedUrl(anyString())).thenReturn(testSignedUrl);
    }

    @Test
    @DisplayName("Test storing document with valid data")
    void testStoreDocument() throws IOException {
        // Arrange
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);

        // Act
        DocumentResponseDTO result = documentService.storeDocument(testFile, testDocumentRequest);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(testDocumentId.toString(), result.getId().toString(), "Document ID should match");
        assertEquals(testApplicationId.toString(), result.getApplicationId().toString(), "Application ID should match");
        assertEquals("BANK_STATEMENT", result.getType(), "Document type should match");
        assertEquals("VERIFIED", result.getClassification(), "Document classification should match");
        assertEquals(testSignedUrl.toString(), result.getDownloadUrl(), "Download URL should match");
        assertTrue(result.getMetadata().containsKey("originalFilename"), "Metadata should contain originalFilename");
        assertTrue(result.getMetadata().containsKey("contentType"), "Metadata should contain contentType");
        assertTrue(result.getMetadata().containsKey("fileSize"), "Metadata should contain fileSize");
        assertTrue(result.getMetadata().containsKey("accountNumber"), "Metadata should contain accountNumber");
        assertTrue(result.getMetadata().containsKey("bankName"), "Metadata should contain bankName");

        // Verify S3 upload was called with correct parameters
        verify(s3Client).putObject(any(PutObjectRequest.class), any(RequestBody.class));
        
        // Verify document was saved to repository
        verify(documentRepository).save(any(Document.class));
    }

    @Test
    @DisplayName("Test storing document with empty file should throw exception")
    void testStoreDocumentWithEmptyFile() {
        // Arrange
        MockMultipartFile emptyFile = new MockMultipartFile(
                "empty-file.pdf",
                "empty-file.pdf",
                "application/pdf",
                new byte[0]);

        // Act & Assert
        assertThrows(InvalidDocumentException.class, () -> {
            documentService.storeDocument(emptyFile, testDocumentRequest);
        }, "Should throw InvalidDocumentException for empty file");

        // Verify S3 upload was not called
        verify(s3Client, never()).putObject(any(PutObjectRequest.class), any(RequestBody.class));
        
        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Test storing document with null file should throw exception")
    void testStoreDocumentWithNullFile() {
        // Act & Assert
        assertThrows(InvalidDocumentException.class, () -> {
            documentService.storeDocument(null, testDocumentRequest);
        }, "Should throw InvalidDocumentException for null file");

        // Verify S3 upload was not called
        verify(s3Client, never()).putObject(any(PutObjectRequest.class), any(RequestBody.class));
        
        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Test storing document with invalid request should throw exception")
    void testStoreDocumentWithInvalidRequest() {
        // Arrange
        DocumentRequestDTO invalidRequest = new DocumentRequestDTO();
        // Missing required fields

        // Act & Assert
        assertThrows(InvalidDocumentException.class, () -> {
            documentService.storeDocument(testFile, invalidRequest);
        }, "Should throw InvalidDocumentException for invalid request");

        // Verify S3 upload was not called
        verify(s3Client, never()).putObject(any(PutObjectRequest.class), any(RequestBody.class));
        
        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Test storing document with S3 error should throw exception")
    void testStoreDocumentWithS3Error() {
        // Arrange
        when(s3Client.putObject(any(PutObjectRequest.class), any(RequestBody.class)))
                .thenThrow(new S3Exception("S3 error"));

        // Act & Assert
        assertThrows(DocumentStorageException.class, () -> {
            documentService.storeDocument(testFile, testDocumentRequest);
        }, "Should throw DocumentStorageException for S3 error");

        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Test getting document by ID")
    void testGetDocumentById() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));

        // Act
        Optional<DocumentResponseDTO> result = documentService.getDocumentById(testDocumentId.getMostSignificantBits());

        // Assert
        assertTrue(result.isPresent(), "Result should be present");
        DocumentResponseDTO dto = result.get();
        assertEquals(testDocumentId.toString(), dto.getId().toString(), "Document ID should match");
        assertEquals(testApplicationId.toString(), dto.getApplicationId().toString(), "Application ID should match");
        assertEquals("BANK_STATEMENT", dto.getType(), "Document type should match");
        assertEquals("VERIFIED", dto.getClassification(), "Document classification should match");
        assertEquals(testSignedUrl.toString(), dto.getDownloadUrl(), "Download URL should match");
    }

    @Test
    @DisplayName("Test getting document by ID when not found")
    void testGetDocumentByIdNotFound() {
        // Arrange
        when(documentRepository.findById(any(UUID.class))).thenReturn(Optional.empty());

        // Act
        Optional<DocumentResponseDTO> result = documentService.getDocumentById(999L);

        // Assert
        assertFalse(result.isPresent(), "Result should not be present");
    }

    @Test
    @DisplayName("Test getting documents by application ID")
    void testGetDocumentsByApplicationId() {
        // Arrange
        List<Document> documents = Collections.singletonList(testDocument);
        when(documentRepository.findByApplicationId(testApplicationId)).thenReturn(documents);

        // Act
        List<DocumentResponseDTO> result = documentService.getDocumentsByApplicationId(testApplicationId.getMostSignificantBits());

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(1, result.size(), "Result should contain one document");
        DocumentResponseDTO dto = result.get(0);
        assertEquals(testDocumentId.toString(), dto.getId().toString(), "Document ID should match");
        assertEquals(testApplicationId.toString(), dto.getApplicationId().toString(), "Application ID should match");
        assertEquals("BANK_STATEMENT", dto.getType(), "Document type should match");
        assertEquals("VERIFIED", dto.getClassification(), "Document classification should match");
        assertEquals(testSignedUrl.toString(), dto.getDownloadUrl(), "Download URL should match");
    }

    @Test
    @DisplayName("Test generating secure URL for document")
    void testGenerateSecureUrl() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));

        // Act
        String result = documentService.generateSecureUrl(testDocumentId.getMostSignificantBits());

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(testSignedUrl.toString(), result, "Secure URL should match");
        
        // Verify signed URL was generated with correct parameters
        verify(s3Config).generateSignedUrl(testDocument.getStoragePath());
    }

    @Test
    @DisplayName("Test generating secure URL for document with custom expiration")
    void testGenerateSecureUrlWithCustomExpiration() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        Integer customExpiration = 30; // 30 minutes

        // Act
        String result = documentService.generateSecureUrl(testDocumentId.getMostSignificantBits(), customExpiration);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(testSignedUrl.toString(), result, "Secure URL should match");
    }

    @Test
    @DisplayName("Test generating secure URL for document that doesn't exist")
    void testGenerateSecureUrlDocumentNotFound() {
        // Arrange
        when(documentRepository.findById(any(UUID.class))).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(DocumentNotFoundException.class, () -> {
            documentService.generateSecureUrl(999L);
        }, "Should throw DocumentNotFoundException for non-existent document");
    }

    @Test
    @DisplayName("Test updating document metadata")
    void testUpdateDocumentMetadata() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);

        DocumentRequestDTO updateRequest = new DocumentRequestDTO();
        updateRequest.setType(DocumentType.TAX_RETURN); // Change type
        updateRequest.setClassification("NEEDS_REVIEW"); // Change classification
        Map<String, Object> newMetadata = new HashMap<>();
        newMetadata.put("taxYear", "2023");
        newMetadata.put("reviewComment", "Needs additional verification");
        updateRequest.setMetadata(newMetadata);

        // Act
        DocumentResponseDTO result = documentService.updateDocumentMetadata(testDocumentId.getMostSignificantBits(), updateRequest);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals("TAX_RETURN", result.getType(), "Document type should be updated");
        assertEquals("NEEDS_REVIEW", result.getClassification(), "Document classification should be updated");
        assertTrue(result.getMetadata().containsKey("taxYear"), "Metadata should contain new taxYear field");
        assertTrue(result.getMetadata().containsKey("reviewComment"), "Metadata should contain new reviewComment field");
        
        // Original metadata should be preserved
        assertTrue(result.getMetadata().containsKey("originalFilename"), "Original metadata should be preserved");
        assertTrue(result.getMetadata().containsKey("contentType"), "Original metadata should be preserved");
        assertTrue(result.getMetadata().containsKey("fileSize"), "Original metadata should be preserved");

        // Verify document was saved to repository
        verify(documentRepository).save(any(Document.class));
    }

    @Test
    @DisplayName("Test updating document metadata for non-existent document")
    void testUpdateDocumentMetadataNotFound() {
        // Arrange
        when(documentRepository.findById(any(UUID.class))).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(DocumentNotFoundException.class, () -> {
            documentService.updateDocumentMetadata(999L, testDocumentRequest);
        }, "Should throw DocumentNotFoundException for non-existent document");

        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Test deleting document")
    void testDeleteDocument() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));

        // Act
        boolean result = documentService.deleteDocument(testDocumentId.getMostSignificantBits());

        // Assert
        assertTrue(result, "Delete operation should return true");
        
        // Verify S3 delete was called with correct parameters
        verify(s3Client).deleteObject(any(DeleteObjectRequest.class));
        
        // Verify document was deleted from repository
        verify(documentRepository).delete(testDocument);
    }

    @Test
    @DisplayName("Test deleting document that doesn't exist")
    void testDeleteDocumentNotFound() {
        // Arrange
        when(documentRepository.findById(any(UUID.class))).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(DocumentNotFoundException.class, () -> {
            documentService.deleteDocument(999L);
        }, "Should throw DocumentNotFoundException for non-existent document");

        // Verify S3 delete was not called
        verify(s3Client, never()).deleteObject(any(DeleteObjectRequest.class));
        
        // Verify document was not deleted from repository
        verify(documentRepository, never()).delete(any(Document.class));
    }

    @Test
    @DisplayName("Test deleting document with S3 error")
    void testDeleteDocumentWithS3Error() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(s3Client.deleteObject(any(DeleteObjectRequest.class)))
                .thenThrow(new S3Exception("S3 error"));

        // Act & Assert
        assertThrows(DocumentStorageException.class, () -> {
            documentService.deleteDocument(testDocumentId.getMostSignificantBits());
        }, "Should throw DocumentStorageException for S3 error");

        // Verify document was not deleted from repository
        verify(documentRepository, never()).delete(any(Document.class));
    }

    @Test
    @DisplayName("Test associating document with application")
    void testAssociateWithApplication() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);
        UUID newApplicationId = UUID.randomUUID();

        // Act
        DocumentResponseDTO result = documentService.associateWithApplication(
                testDocumentId.getMostSignificantBits(), 
                newApplicationId.getMostSignificantBits());

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(newApplicationId.toString(), result.getApplicationId().toString(), "Application ID should be updated");

        // Verify document was saved to repository with new application ID
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        assertEquals(newApplicationId, documentCaptor.getValue().getApplicationId(), "Document should have new application ID");
    }

    @Test
    @DisplayName("Test associating document with application when document doesn't exist")
    void testAssociateWithApplicationDocumentNotFound() {
        // Arrange
        when(documentRepository.findById(any(UUID.class))).thenReturn(Optional.empty());
        UUID newApplicationId = UUID.randomUUID();

        // Act & Assert
        assertThrows(DocumentNotFoundException.class, () -> {
            documentService.associateWithApplication(999L, newApplicationId.getMostSignificantBits());
        }, "Should throw DocumentNotFoundException for non-existent document");

        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Test getting document content")
    void testGetDocumentContent() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        
        // Mock S3 response
        byte[] content = "Test file content".getBytes();
        ByteArrayInputStream contentStream = new ByteArrayInputStream(content);
        ResponseInputStream<GetObjectResponse> s3Response = mock(ResponseInputStream.class);
        when(s3Response.response()).thenReturn(GetObjectResponse.builder().contentType("application/pdf").build());
        when(s3Client.getObject(any(GetObjectRequest.class))).thenReturn(s3Response);

        // Act
        InputStream result = documentService.getDocumentContent(testDocumentId.getMostSignificantBits());

        // Assert
        assertNotNull(result, "Result should not be null");
        
        // Verify S3 get was called with correct parameters
        verify(s3Client).getObject(any(GetObjectRequest.class));
    }

    @Test
    @DisplayName("Test getting document content when document doesn't exist")
    void testGetDocumentContentDocumentNotFound() {
        // Arrange
        when(documentRepository.findById(any(UUID.class))).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(DocumentNotFoundException.class, () -> {
            documentService.getDocumentContent(999L);
        }, "Should throw DocumentNotFoundException for non-existent document");

        // Verify S3 get was not called
        verify(s3Client, never()).getObject(any(GetObjectRequest.class));
    }

    @Test
    @DisplayName("Test getting document content with S3 error")
    void testGetDocumentContentWithS3Error() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(s3Client.getObject(any(GetObjectRequest.class)))
                .thenThrow(new S3Exception("S3 error"));

        // Act & Assert
        assertThrows(DocumentStorageException.class, () -> {
            documentService.getDocumentContent(testDocumentId.getMostSignificantBits());
        }, "Should throw DocumentStorageException for S3 error");
    }

    @Test
    @DisplayName("Test updating document classification")
    void testUpdateDocumentClassification() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);
        String newClassification = "NEEDS_REVIEW";
        Double newConfidence = 0.75;

        // Act
        DocumentResponseDTO result = documentService.updateDocumentClassification(
                testDocumentId.getMostSignificantBits(), 
                newClassification, 
                newConfidence);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(newClassification, result.getClassification(), "Classification should be updated");
        assertEquals(newConfidence, result.getClassificationConfidence(), "Confidence score should be updated");

        // Verify document was saved to repository with new classification
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        assertEquals(DocumentClassification.fromString(newClassification), 
                documentCaptor.getValue().getClassification(), 
                "Document should have new classification");
    }

    @Test
    @DisplayName("Test updating document classification with additional metadata")
    void testUpdateDocumentClassificationWithMetadata() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);
        String newClassification = "NEEDS_REVIEW";
        Double newConfidence = 0.75;
        Map<String, Object> additionalMetadata = new HashMap<>();
        additionalMetadata.put("reviewReason", "Signature mismatch");
        additionalMetadata.put("reviewPriority", "High");

        // Act
        DocumentResponseDTO result = documentService.updateDocumentClassification(
                testDocumentId.getMostSignificantBits(), 
                newClassification, 
                newConfidence,
                additionalMetadata);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(newClassification, result.getClassification(), "Classification should be updated");
        assertEquals(newConfidence, result.getClassificationConfidence(), "Confidence score should be updated");
        assertTrue(result.getMetadata().containsKey("reviewReason"), "Metadata should contain reviewReason");
        assertTrue(result.getMetadata().containsKey("reviewPriority"), "Metadata should contain reviewPriority");

        // Verify document was saved to repository with new classification and metadata
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        Document savedDocument = documentCaptor.getValue();
        assertEquals(DocumentClassification.fromString(newClassification), 
                savedDocument.getClassification(), 
                "Document should have new classification");
        assertTrue(savedDocument.getMetadata().containsKey("reviewReason"), 
                "Document metadata should contain reviewReason");
        assertTrue(savedDocument.getMetadata().containsKey("reviewPriority"), 
                "Document metadata should contain reviewPriority");
    }

    @Test
    @DisplayName("Test updating document classification when document doesn't exist")
    void testUpdateDocumentClassificationDocumentNotFound() {
        // Arrange
        when(documentRepository.findById(any(UUID.class))).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(DocumentNotFoundException.class, () -> {
            documentService.updateDocumentClassification(999L, "NEEDS_REVIEW", 0.75);
        }, "Should throw DocumentNotFoundException for non-existent document");

        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Test searching documents by metadata")
    void testSearchDocuments() {
        // Arrange
        Map<String, Object> searchCriteria = new HashMap<>();
        searchCriteria.put("bankName", "Test Bank");
        
        // Mock JSON conversion
        String searchJson = "{\"bankName\":\"Test Bank\"}";
        
        // Mock repository response
        when(documentRepository.findByMetadataContains(eq(searchJson), any()))
                .thenReturn(new org.springframework.data.domain.PageImpl<>(Collections.singletonList(testDocument)));

        // Act
        org.springframework.data.domain.Page<DocumentResponseDTO> result = 
                documentService.searchDocuments(searchCriteria, org.springframework.data.domain.PageRequest.of(0, 10));

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(1, result.getTotalElements(), "Result should contain one document");
        DocumentResponseDTO dto = result.getContent().get(0);
        assertEquals(testDocumentId.toString(), dto.getId().toString(), "Document ID should match");
    }

    @Test
    @DisplayName("Test document exists")
    void testDocumentExists() {
        // Arrange
        when(documentRepository.existsById(testDocumentId)).thenReturn(true);

        // Act
        boolean result = documentService.documentExists(testDocumentId.getMostSignificantBits());

        // Assert
        assertTrue(result, "Document should exist");
    }

    @Test
    @DisplayName("Test document does not exist")
    void testDocumentDoesNotExist() {
        // Arrange
        when(documentRepository.existsById(any(UUID.class))).thenReturn(false);

        // Act
        boolean result = documentService.documentExists(999L);

        // Assert
        assertFalse(result, "Document should not exist");
    }

    @Test
    @DisplayName("Test count documents by type")
    void testCountDocumentsByType() {
        // Arrange
        when(documentRepository.countByType(DocumentType.BANK_STATEMENT)).thenReturn(5L);

        // Act
        long result = documentService.countDocumentsByType(DocumentType.BANK_STATEMENT);

        // Assert
        assertEquals(5L, result, "Count should match expected value");
    }

    @Test
    @DisplayName("Test count documents by application ID")
    void testCountDocumentsByApplicationId() {
        // Arrange
        when(documentRepository.countByApplicationId(testApplicationId)).thenReturn(3L);

        // Act
        long result = documentService.countDocumentsByApplicationId(testApplicationId.getMostSignificantBits());

        // Assert
        assertEquals(3L, result, "Count should match expected value");
    }

    @Test
    @DisplayName("Test validate document metadata with valid request")
    void testValidateDocumentMetadataValid() {
        // Act
        boolean result = documentService.validateDocumentMetadata(testDocumentRequest);

        // Assert
        assertTrue(result, "Validation should pass for valid request");
    }

    @Test
    @DisplayName("Test validate document metadata with null request")
    void testValidateDocumentMetadataNullRequest() {
        // Act
        boolean result = documentService.validateDocumentMetadata(null);

        // Assert
        assertFalse(result, "Validation should fail for null request");
    }

    @Test
    @DisplayName("Test validate document metadata with missing required fields")
    void testValidateDocumentMetadataMissingFields() {
        // Arrange
        DocumentRequestDTO invalidRequest = new DocumentRequestDTO();
        // Missing required fields

        // Act
        boolean result = documentService.validateDocumentMetadata(invalidRequest);

        // Assert
        assertFalse(result, "Validation should fail for request with missing fields");
    }

    @Test
    @DisplayName("Test validate document metadata with invalid classification")
    void testValidateDocumentMetadataInvalidClassification() {
        // Arrange
        DocumentRequestDTO invalidRequest = new DocumentRequestDTO();
        invalidRequest.setApplicationId(testApplicationId);
        invalidRequest.setType(DocumentType.BANK_STATEMENT);
        invalidRequest.setClassification("INVALID_CLASSIFICATION");

        // Act
        boolean result = documentService.validateDocumentMetadata(invalidRequest);

        // Assert
        assertFalse(result, "Validation should fail for request with invalid classification");
    }

    @Test
    @DisplayName("Test validate document metadata with invalid confidence score")
    void testValidateDocumentMetadataInvalidConfidenceScore() {
        // Arrange
        DocumentRequestDTO invalidRequest = new DocumentRequestDTO();
        invalidRequest.setApplicationId(testApplicationId);
        invalidRequest.setType(DocumentType.BANK_STATEMENT);
        invalidRequest.setClassificationConfidence(1.5); // Invalid: > 1.0

        // Act
        boolean result = documentService.validateDocumentMetadata(invalidRequest);

        // Assert
        assertFalse(result, "Validation should fail for request with invalid confidence score");
    }

    @Test
    @DisplayName("Test process document for extraction")
    void testProcessDocumentForExtraction() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);

        // Act
        DocumentResponseDTO result = documentService.processDocumentForExtraction(testDocumentId.getMostSignificantBits());

        // Assert
        assertNotNull(result, "Result should not be null");
        
        // Verify metadata was updated with processing information
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        Document savedDocument = documentCaptor.getValue();
        assertTrue(savedDocument.getMetadata().containsKey("processingStarted"), 
                "Document metadata should contain processingStarted");
        assertTrue(savedDocument.getMetadata().containsKey("processingStatus"), 
                "Document metadata should contain processingStatus");
        assertEquals("IN_PROGRESS", savedDocument.getMetadataValue("processingStatus"), 
                "Processing status should be IN_PROGRESS");
    }

    @Test
    @DisplayName("Test get documents requiring review")
    void testGetDocumentsRequiringReview() {
        // Arrange
        Double confidenceThreshold = 0.8;
        when(documentRepository.findByConfidenceScoreLessThan(confidenceThreshold, org.springframework.data.domain.PageRequest.of(0, 10)))
                .thenReturn(new org.springframework.data.domain.PageImpl<>(Collections.singletonList(testDocument)));

        // Act
        org.springframework.data.domain.Page<DocumentResponseDTO> result = 
                documentService.getDocumentsRequiringReview(confidenceThreshold, org.springframework.data.domain.PageRequest.of(0, 10));

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(1, result.getTotalElements(), "Result should contain one document");
        DocumentResponseDTO dto = result.getContent().get(0);
        assertEquals(testDocumentId.toString(), dto.getId().toString(), "Document ID should match");
    }

    @Test
    @DisplayName("Test mark document as reviewed and approved")
    void testMarkDocumentAsReviewedApproved() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);
        Long reviewerId = 123L;
        boolean approved = true;
        String comments = "Document looks good";

        // Act
        DocumentResponseDTO result = documentService.markDocumentAsReviewed(
                testDocumentId.getMostSignificantBits(), 
                reviewerId, 
                approved, 
                comments);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals("VERIFIED", result.getClassification(), "Classification should be VERIFIED for approved document");
        
        // Verify document was saved with review information
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        Document savedDocument = documentCaptor.getValue();
        assertTrue(savedDocument.getMetadata().containsKey("review"), 
                "Document metadata should contain review information");
        
        @SuppressWarnings("unchecked")
        Map<String, Object> reviewInfo = (Map<String, Object>) savedDocument.getMetadataValue("review");
        assertNotNull(reviewInfo, "Review info should not be null");
        assertEquals(reviewerId, reviewInfo.get("reviewerId"), "Reviewer ID should match");
        assertEquals(approved, reviewInfo.get("approved"), "Approved status should match");
        assertEquals(comments, reviewInfo.get("comments"), "Comments should match");
    }

    @Test
    @DisplayName("Test mark document as reviewed and rejected")
    void testMarkDocumentAsReviewedRejected() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);
        Long reviewerId = 123L;
        boolean approved = false;
        String comments = "Document is suspicious";

        // Act
        DocumentResponseDTO result = documentService.markDocumentAsReviewed(
                testDocumentId.getMostSignificantBits(), 
                reviewerId, 
                approved, 
                comments);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals("REJECTED", result.getClassification(), "Classification should be REJECTED for rejected document");
        
        // Verify document was saved with review information
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        Document savedDocument = documentCaptor.getValue();
        assertTrue(savedDocument.getMetadata().containsKey("review"), 
                "Document metadata should contain review information");
        
        @SuppressWarnings("unchecked")
        Map<String, Object> reviewInfo = (Map<String, Object>) savedDocument.getMetadataValue("review");
        assertNotNull(reviewInfo, "Review info should not be null");
        assertEquals(reviewerId, reviewInfo.get("reviewerId"), "Reviewer ID should match");
        assertEquals(approved, reviewInfo.get("approved"), "Approved status should match");
        assertEquals(comments, reviewInfo.get("comments"), "Comments should match");
    }

    @Test
    @DisplayName("Test get document versions")
    void testGetDocumentVersions() {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));

        // Act
        List<DocumentResponseDTO> result = documentService.getDocumentVersions(testDocumentId.getMostSignificantBits());

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(1, result.size(), "Result should contain one version");
        DocumentResponseDTO dto = result.get(0);
        assertEquals(testDocumentId.toString(), dto.getId().toString(), "Document ID should match");
    }

    @Test
    @DisplayName("Test create document version")
    void testCreateDocumentVersion() throws IOException {
        // Arrange
        when(documentRepository.findById(testDocumentId)).thenReturn(Optional.of(testDocument));
        when(documentRepository.save(any(Document.class))).thenReturn(testDocument);

        // New version file
        byte[] fileContent = "New version content".getBytes();
        MultipartFile newVersionFile = new MockMultipartFile(
                "new-version.pdf",
                "new-version.pdf",
                "application/pdf",
                fileContent);

        // Act
        DocumentResponseDTO result = documentService.createDocumentVersion(
                testDocumentId.getMostSignificantBits(), 
                newVersionFile, 
                testDocumentRequest);

        // Assert
        assertNotNull(result, "Result should not be null");
        
        // Verify S3 upload was called with correct parameters
        verify(s3Client).putObject(any(PutObjectRequest.class), any(RequestBody.class));
        
        // Verify document was saved to repository
        ArgumentCaptor<Document> documentCaptor = ArgumentCaptor.forClass(Document.class);
        verify(documentRepository).save(documentCaptor.capture());
        Document savedDocument = documentCaptor.getValue();
        assertEquals(testDocument.getApplicationId(), savedDocument.getApplicationId(), 
                "Application ID should match original document");
        assertEquals(testDocument.getType(), savedDocument.getType(), 
                "Document type should match original document");
        assertTrue(savedDocument.getMetadata().containsKey("previousVersionId"), 
                "Metadata should contain previousVersionId");
        assertTrue(savedDocument.getMetadata().containsKey("versionCreatedAt"), 
                "Metadata should contain versionCreatedAt");
    }

    @Test
    @DisplayName("Test convert to DTO")
    void testConvertToDTO() {
        // Act
        DocumentResponseDTO result = documentService.convertToDTO(testDocument);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(testDocumentId.toString(), result.getId().toString(), "Document ID should match");
        assertEquals(testApplicationId.toString(), result.getApplicationId().toString(), "Application ID should match");
        assertEquals("BANK_STATEMENT", result.getType(), "Document type should match");
        assertEquals("VERIFIED", result.getClassification(), "Document classification should match");
        assertEquals(testSignedUrl.toString(), result.getDownloadUrl(), "Download URL should match");
    }

    @Test
    @DisplayName("Test convert to entity")
    void testConvertToEntity() {
        // Act
        Document result = documentService.convertToEntity(testDocumentRequest);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(testApplicationId, result.getApplicationId(), "Application ID should match");
        assertEquals(DocumentType.BANK_STATEMENT, result.getType(), "Document type should match");
        assertEquals(DocumentClassification.VERIFIED, result.getClassification(), "Document classification should match");
        assertTrue(result.getMetadata().containsKey("accountNumber"), "Metadata should contain accountNumber");
        assertTrue(result.getMetadata().containsKey("bankName"), "Metadata should contain bankName");
    }
}