package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.StorageException;
import com.dollarfunding.mca.util.EncryptionUtil;
import com.dollarfunding.mca.util.JsonUtil;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;

import java.io.IOException;
import java.net.URL;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the DocumentServiceImpl class.
 * 
 * These tests verify the functionality of the DocumentServiceImpl class, which manages document storage,
 * retrieval, and metadata for the MCA application. The tests use Mockito to mock dependencies and focus
 * on testing the service's business logic.
 */
@ExtendWith(MockitoExtension.class)
public class DocumentServiceImplTest {

    @Mock
    private DocumentRepository documentRepository;

    @Mock
    private ApplicationRepository applicationRepository;

    @Mock
    private S3Client s3Client;

    @Mock
    private S3Presigner s3Presigner;

    @Mock
    private EncryptionUtil encryptionUtil;

    @Mock
    private JsonUtil jsonUtil;

    @Mock
    private PresignedGetObjectRequest presignedGetObjectRequest;

    @InjectMocks
    private DocumentServiceImpl documentService;

    // Test data
    private Long documentId;
    private Long applicationId;
    private Document document;
    private Application application;
    private DocumentRequestDTO documentRequest;
    private MultipartFile multipartFile;
    private Map<String, Object> metadata;
    private Map<String, Double> confidenceScores;
    private String storagePath;
    private String signedUrl;
    private String bucketName;
    private String metadataJson;

    @BeforeEach
    void setUp() {
        // Set up test data
        documentId = 1L;
        applicationId = 100L;
        storagePath = "applications/100/bank_statement/abc-123-xyz";
        signedUrl = "https://s3.example.com/documents/abc-123-xyz?signature=xyz";
        bucketName = "mca-documents-production";
        metadataJson = "{\"originalFilename\":\"bank_statement.pdf\",\"contentType\":\"application/pdf\",\"size\":12345,\"classification\":\"bank_statement\"}";

        // Set up test objects
        application = new Application();
        application.setId(applicationId);

        document = new Document();
        document.setId(documentId);
        document.setApplication(application);
        document.setType(DocumentType.BANK_STATEMENT);
        document.setStoragePath(storagePath);
        document.setClassification("bank_statement");
        document.setUploadedAt(LocalDateTime.now());
        document.setMetadataJson(metadataJson);

        metadata = new HashMap<>();
        metadata.put("originalFilename", "bank_statement.pdf");
        metadata.put("contentType", "application/pdf");
        metadata.put("size", 12345L);
        metadata.put("classification", "bank_statement");

        confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.95);
        confidenceScores.put("account_number", 0.87);
        confidenceScores.put("balance", 0.92);

        documentRequest = new DocumentRequestDTO();
        documentRequest.setApplicationId(applicationId);
        documentRequest.setType(DocumentType.BANK_STATEMENT);
        documentRequest.setClassification("bank_statement");
        documentRequest.setMetadata(metadata);
        documentRequest.setConfidenceScores(confidenceScores);

        multipartFile = new MockMultipartFile(
            "file", 
            "bank_statement.pdf", 
            "application/pdf", 
            "test content".getBytes()
        );

        // Set up reflection to access private fields
        try {
            java.lang.reflect.Field bucketNameField = DocumentServiceImpl.class.getDeclaredField("bucketName");
            bucketNameField.setAccessible(true);
            bucketNameField.set(documentService, bucketName);

            java.lang.reflect.Field urlExpirationSecondsField = DocumentServiceImpl.class.getDeclaredField("urlExpirationSeconds");
            urlExpirationSecondsField.setAccessible(true);
            urlExpirationSecondsField.set(documentService, 300L);
        } catch (Exception e) {
            fail("Failed to set up test: " + e.getMessage());
        }

        // Set up common mocks
        when(jsonUtil.toJson(any())).thenReturn(metadataJson);
        when(jsonUtil.fromJson(metadataJson, Map.class)).thenReturn(metadata);
    }

    @Test
    @DisplayName("Should store document successfully with AES-256 encryption")
    void storeDocumentSuccessfully() throws IOException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        when(documentRepository.save(any(Document.class))).thenReturn(document);
        
        // Mock S3 presigner
        URL mockUrl = new URL("https", "s3.example.com", "/documents/abc-123-xyz?signature=xyz");
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Act
        DocumentResponseDTO result = documentService.storeDocument(multipartFile, documentRequest);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(documentId, result.getId(), "Document ID should match");
        assertEquals(applicationId, result.getApplicationId(), "Application ID should match");
        assertEquals(DocumentType.BANK_STATEMENT, result.getType(), "Document type should match");
        assertEquals("bank_statement", result.getClassification(), "Classification should match");
        assertEquals(signedUrl, result.getSignedUrl(), "Signed URL should match");

        // Verify S3 client was called with AES-256 encryption
        ArgumentCaptor<PutObjectRequest> putRequestCaptor = ArgumentCaptor.forClass(PutObjectRequest.class);
        verify(s3Client).putObject(putRequestCaptor.capture(), any(RequestBody.class));
        PutObjectRequest capturedRequest = putRequestCaptor.getValue();
        assertEquals(bucketName, capturedRequest.bucket(), "Bucket name should match");
        assertEquals("AES256", capturedRequest.serverSideEncryption(), "Server-side encryption should be AES256");
        
        // Verify document was saved to repository
        verify(documentRepository).save(any(Document.class));
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when application not found")
    void storeDocumentApplicationNotFound() {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(ResourceNotFoundException.class, () -> {
            documentService.storeDocument(multipartFile, documentRequest);
        }, "Should throw ResourceNotFoundException when application not found");

        // Verify S3 client was not called
        verify(s3Client, never()).putObject(any(PutObjectRequest.class), any(RequestBody.class));
        
        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Should throw StorageException when S3 storage fails")
    void storeDocumentS3StorageFails() throws IOException {
        // Arrange
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(application));
        doThrow(new RuntimeException("S3 error")).when(s3Client).putObject(any(PutObjectRequest.class), any(RequestBody.class));

        // Act & Assert
        assertThrows(StorageException.class, () -> {
            documentService.storeDocument(multipartFile, documentRequest);
        }, "Should throw StorageException when S3 storage fails");

        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Should retrieve document by ID with signed URL")
    void getDocumentByIdSuccessfully() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        
        // Mock S3 presigner
        URL mockUrl = new URL("https", "s3.example.com", "/documents/abc-123-xyz?signature=xyz");
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Act
        DocumentResponseDTO result = documentService.getDocumentById(documentId);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(documentId, result.getId(), "Document ID should match");
        assertEquals(applicationId, result.getApplicationId(), "Application ID should match");
        assertEquals(DocumentType.BANK_STATEMENT, result.getType(), "Document type should match");
        assertEquals("bank_statement", result.getClassification(), "Classification should match");
        assertEquals(signedUrl, result.getSignedUrl(), "Signed URL should match");

        // Verify S3 presigner was called with correct parameters
        ArgumentCaptor<GetObjectPresignRequest> presignRequestCaptor = ArgumentCaptor.forClass(GetObjectPresignRequest.class);
        verify(s3Presigner).presignGetObject(presignRequestCaptor.capture());
        GetObjectPresignRequest capturedRequest = presignRequestCaptor.getValue();
        assertEquals(Duration.ofSeconds(300), capturedRequest.signatureDuration(), "Signature duration should match");
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when document not found")
    void getDocumentByIdNotFound() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(ResourceNotFoundException.class, () -> {
            documentService.getDocumentById(documentId);
        }, "Should throw ResourceNotFoundException when document not found");

        // Verify S3 presigner was not called
        verify(s3Presigner, never()).presignGetObject(any(GetObjectPresignRequest.class));
    }

    @Test
    @DisplayName("Should retrieve documents by application ID with pagination")
    void getDocumentsByApplicationIdSuccessfully() {
        // Arrange
        Pageable pageable = PageRequest.of(0, 10);
        List<Document> documentList = Collections.singletonList(document);
        Page<Document> documentPage = new PageImpl<>(documentList, pageable, 1);
        
        when(applicationRepository.existsById(applicationId)).thenReturn(true);
        when(documentRepository.findByApplicationId(applicationId, pageable)).thenReturn(documentPage);
        
        // Mock S3 presigner
        URL mockUrl = new URL("https", "s3.example.com", "/documents/abc-123-xyz?signature=xyz");
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Act
        Page<DocumentResponseDTO> result = documentService.getDocumentsByApplicationId(applicationId, pageable);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(1, result.getTotalElements(), "Total elements should match");
        assertEquals(1, result.getContent().size(), "Content size should match");
        
        DocumentResponseDTO dto = result.getContent().get(0);
        assertEquals(documentId, dto.getId(), "Document ID should match");
        assertEquals(applicationId, dto.getApplicationId(), "Application ID should match");
        assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Document type should match");
        assertEquals(signedUrl, dto.getSignedUrl(), "Signed URL should match");

        // Verify repository was called
        verify(documentRepository).findByApplicationId(applicationId, pageable);
        
        // Verify S3 presigner was called
        verify(s3Presigner).presignGetObject(any(GetObjectPresignRequest.class));
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when application not found for document retrieval")
    void getDocumentsByApplicationIdApplicationNotFound() {
        // Arrange
        Pageable pageable = PageRequest.of(0, 10);
        when(applicationRepository.existsById(applicationId)).thenReturn(false);

        // Act & Assert
        assertThrows(ResourceNotFoundException.class, () -> {
            documentService.getDocumentsByApplicationId(applicationId, pageable);
        }, "Should throw ResourceNotFoundException when application not found");

        // Verify repository was not called
        verify(documentRepository, never()).findByApplicationId(anyLong(), any(Pageable.class));
    }

    @Test
    @DisplayName("Should retrieve documents by application ID and type")
    void getDocumentsByApplicationIdAndTypeSuccessfully() {
        // Arrange
        List<Document> documentList = Collections.singletonList(document);
        
        when(applicationRepository.existsById(applicationId)).thenReturn(true);
        when(documentRepository.findByApplicationIdAndType(applicationId, DocumentType.BANK_STATEMENT)).thenReturn(documentList);
        
        // Mock S3 presigner
        URL mockUrl = new URL("https", "s3.example.com", "/documents/abc-123-xyz?signature=xyz");
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Act
        List<DocumentResponseDTO> result = documentService.getDocumentsByApplicationIdAndType(applicationId, DocumentType.BANK_STATEMENT);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(1, result.size(), "Result size should match");
        
        DocumentResponseDTO dto = result.get(0);
        assertEquals(documentId, dto.getId(), "Document ID should match");
        assertEquals(applicationId, dto.getApplicationId(), "Application ID should match");
        assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Document type should match");
        assertEquals(signedUrl, dto.getSignedUrl(), "Signed URL should match");

        // Verify repository was called
        verify(documentRepository).findByApplicationIdAndType(applicationId, DocumentType.BANK_STATEMENT);
        
        // Verify S3 presigner was called
        verify(s3Presigner).presignGetObject(any(GetObjectPresignRequest.class));
    }

    @Test
    @DisplayName("Should update document metadata successfully")
    void updateDocumentMetadataSuccessfully() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        when(documentRepository.save(any(Document.class))).thenReturn(document);
        
        // Mock S3 presigner
        URL mockUrl = new URL("https", "s3.example.com", "/documents/abc-123-xyz?signature=xyz");
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Create updated request
        DocumentRequestDTO updateRequest = new DocumentRequestDTO();
        updateRequest.setType(DocumentType.BANK_STATEMENT);
        updateRequest.setClassification("updated_classification");
        
        Map<String, Object> updatedMetadata = new HashMap<>();
        updatedMetadata.put("newField", "newValue");
        updateRequest.setMetadata(updatedMetadata);

        // Act
        DocumentResponseDTO result = documentService.updateDocumentMetadata(documentId, updateRequest);

        // Assert
        assertNotNull(result, "Result should not be null");
        assertEquals(documentId, result.getId(), "Document ID should match");
        assertEquals(applicationId, result.getApplicationId(), "Application ID should match");
        assertEquals(DocumentType.BANK_STATEMENT, result.getType(), "Document type should match");
        assertEquals(signedUrl, result.getSignedUrl(), "Signed URL should match");

        // Verify document was saved to repository
        verify(documentRepository).save(any(Document.class));
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when document not found for update")
    void updateDocumentMetadataDocumentNotFound() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.empty());

        // Create updated request
        DocumentRequestDTO updateRequest = new DocumentRequestDTO();
        updateRequest.setClassification("updated_classification");

        // Act & Assert
        assertThrows(ResourceNotFoundException.class, () -> {
            documentService.updateDocumentMetadata(documentId, updateRequest);
        }, "Should throw ResourceNotFoundException when document not found");

        // Verify document was not saved to repository
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    @DisplayName("Should delete document successfully")
    void deleteDocumentSuccessfully() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));

        // Act
        documentService.deleteDocument(documentId);

        // Assert
        // Verify S3 client was called to delete object
        ArgumentCaptor<DeleteObjectRequest> deleteRequestCaptor = ArgumentCaptor.forClass(DeleteObjectRequest.class);
        verify(s3Client).deleteObject(deleteRequestCaptor.capture());
        DeleteObjectRequest capturedRequest = deleteRequestCaptor.getValue();
        assertEquals(bucketName, capturedRequest.bucket(), "Bucket name should match");
        assertEquals(storagePath, capturedRequest.key(), "Storage path should match");
        
        // Verify document was deleted from repository
        verify(documentRepository).delete(document);
    }

    @Test
    @DisplayName("Should throw ResourceNotFoundException when document not found for deletion")
    void deleteDocumentNotFound() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(ResourceNotFoundException.class, () -> {
            documentService.deleteDocument(documentId);
        }, "Should throw ResourceNotFoundException when document not found");

        // Verify S3 client was not called
        verify(s3Client, never()).deleteObject(any(DeleteObjectRequest.class));
        
        // Verify document was not deleted from repository
        verify(documentRepository, never()).delete(any(Document.class));
    }

    @Test
    @DisplayName("Should throw StorageException when S3 deletion fails")
    void deleteDocumentS3DeletionFails() {
        // Arrange
        when(documentRepository.findById(documentId)).thenReturn(Optional.of(document));
        doThrow(new RuntimeException("S3 error")).when(s3Client).deleteObject(any(DeleteObjectRequest.class));

        // Act & Assert
        assertThrows(StorageException.class, () -> {
            documentService.deleteDocument(documentId);
        }, "Should throw StorageException when S3 deletion fails");

        // Verify document was not deleted from repository
        verify(documentRepository, never()).delete(any(Document.class));
    }

    @Test
    @DisplayName("Should generate signed URL with correct expiration time")
    void generateSignedUrlWithCorrectExpiration() {
        // Arrange
        // Mock S3 presigner
        URL mockUrl = new URL("https", "s3.example.com", "/documents/abc-123-xyz?signature=xyz");
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Use reflection to access private method
        try {
            java.lang.reflect.Method generateSignedUrlMethod = DocumentServiceImpl.class.getDeclaredMethod(
                "generateSignedUrl", String.class);
            generateSignedUrlMethod.setAccessible(true);

            // Act
            String result = (String) generateSignedUrlMethod.invoke(documentService, storagePath);

            // Assert
            assertEquals(signedUrl, result, "Signed URL should match");

            // Verify S3 presigner was called with correct parameters
            ArgumentCaptor<GetObjectPresignRequest> presignRequestCaptor = ArgumentCaptor.forClass(GetObjectPresignRequest.class);
            verify(s3Presigner).presignGetObject(presignRequestCaptor.capture());
            GetObjectPresignRequest capturedRequest = presignRequestCaptor.getValue();
            assertEquals(Duration.ofSeconds(300), capturedRequest.signatureDuration(), "Signature duration should match");

            // Verify GetObjectRequest was built correctly
            ArgumentCaptor<GetObjectRequest> getRequestCaptor = ArgumentCaptor.forClass(GetObjectRequest.class);
            verify(presignRequestCaptor.getValue()).getObjectRequest();
            // Note: We can't directly capture the GetObjectRequest since it's built inside the method
            // But we can verify the presigner was called with the correct parameters
        } catch (Exception e) {
            fail("Failed to test generateSignedUrl: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Should create DocumentResponseDTO with correct fields")
    void createDocumentResponseDTOWithCorrectFields() {
        // Use reflection to access private method
        try {
            java.lang.reflect.Method createDocumentResponseDTOMethod = DocumentServiceImpl.class.getDeclaredMethod(
                "createDocumentResponseDTO", Document.class, String.class);
            createDocumentResponseDTOMethod.setAccessible(true);

            // Act
            DocumentResponseDTO result = (DocumentResponseDTO) createDocumentResponseDTOMethod.invoke(
                documentService, document, signedUrl);

            // Assert
            assertNotNull(result, "Result should not be null");
            assertEquals(documentId, result.getId(), "Document ID should match");
            assertEquals(applicationId, result.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.BANK_STATEMENT, result.getType(), "Document type should match");
            assertEquals("bank_statement", result.getClassification(), "Classification should match");
            assertEquals(signedUrl, result.getSignedUrl(), "Signed URL should match");
            assertEquals(metadataJson, result.getMetadata(), "Metadata should match");
        } catch (Exception e) {
            fail("Failed to test createDocumentResponseDTO: " + e.getMessage());
        }
    }

    @Test
    @DisplayName("Should generate unique storage path with correct format")
    void generateStoragePathWithCorrectFormat() {
        // Use reflection to access private method
        try {
            java.lang.reflect.Method generateStoragePathMethod = DocumentServiceImpl.class.getDeclaredMethod(
                "generateStoragePath", Long.class, DocumentType.class);
            generateStoragePathMethod.setAccessible(true);

            // Act
            String result = (String) generateStoragePathMethod.invoke(
                documentService, applicationId, DocumentType.BANK_STATEMENT);

            // Assert
            assertNotNull(result, "Result should not be null");
            assertTrue(result.startsWith("applications/100/bank_statement/"), 
                "Storage path should start with correct prefix");
            assertTrue(result.length() > "applications/100/bank_statement/".length(), 
                "Storage path should include a UUID");
        } catch (Exception e) {
            fail("Failed to test generateStoragePath: " + e.getMessage());
        }
    }
}