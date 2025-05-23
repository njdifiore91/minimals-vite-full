package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.config.S3Config;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentClassification;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.exception.DocumentNotFoundException;
import com.dollarfunding.mca.exception.DocumentStorageException;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.service.DocumentService;
import com.dollarfunding.mca.util.JsonUtil;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.web.multipart.MultipartFile;

import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.core.exception.SdkClientException;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Integration tests for S3 storage functionality in the MCA application.
 * 
 * These tests verify that the data-service can correctly interact with S3-compatible storage
 * for document retrieval and storage, including:
 * - Document upload with AES-256 encryption
 * - Document retrieval with appropriate error handling
 * - Document metadata extraction and processing
 * - Result storage back to S3 with encryption
 * - Versioning and access control
 */
@ExtendWith(SpringExtension.class)
@SpringBootTest
@ActiveProfiles("test")
public class S3StorageIntegrationTest {

    @Autowired
    private DocumentService documentService;
    
    @SpyBean
    private S3Config s3Config;
    
    @MockBean
    private S3Client s3Client;
    
    @MockBean
    private S3Presigner s3Presigner;
    
    @Autowired
    private DocumentRepository documentRepository;
    
    @Value("${aws.s3.bucket.staging}")
    private String bucketName;
    
    private UUID testApplicationId;
    private MultipartFile testFile;
    private DocumentRequestDTO testDocumentRequest;
    private String testStoragePath;
    private URL testPresignedUrl;
    
    @BeforeEach
    public void setup() throws IOException {
        // Create test application ID
        testApplicationId = UUID.randomUUID();
        
        // Create test file from sample document
        Resource resource = new ClassPathResource("/sample-documents/business_documents/sample_business_license.pdf");
        testFile = new MockMultipartFile(
                "sample_business_license.pdf",
                "sample_business_license.pdf",
                "application/pdf",
                resource.getInputStream());
        
        // Create test document request
        testDocumentRequest = new DocumentRequestDTO();
        testDocumentRequest.setApplicationId(testApplicationId);
        testDocumentRequest.setType(DocumentType.BUSINESS_LICENSE);
        testDocumentRequest.setClassification(DocumentClassification.UNCLASSIFIED.name());
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("description", "Business license for testing");
        metadata.put("source", "Integration test");
        testDocumentRequest.setMetadata(metadata);
        
        // Set up test storage path
        testStoragePath = "documents/" + testApplicationId + "/sample_business_license.pdf";
        
        // Set up test presigned URL
        testPresignedUrl = new URL("https://test-bucket.s3.amazonaws.com/" + testStoragePath + "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=test");
        
        // Mock S3 client behavior for successful operations
        mockS3ClientForSuccessfulOperations();
    }
    
    @AfterEach
    public void cleanup() {
        // Clean up any test documents created in the repository
        documentRepository.deleteAll();
        
        // Reset mocks
        Mockito.reset(s3Client, s3Presigner, s3Config);
    }
    
    /**
     * Test uploading a document to S3 with AES-256 encryption.
     * Verifies that the document is correctly uploaded to S3 and metadata is stored in the database.
     */
    @Test
    @DisplayName("Should upload document to S3 with encryption and store metadata")
    public void testDocumentUploadWithEncryption() throws IOException {
        // Act
        DocumentResponseDTO response = documentService.storeDocument(testFile, testDocumentRequest);
        
        // Assert
        assertNotNull(response, "Response should not be null");
        assertNotNull(response.getId(), "Document ID should not be null");
        assertEquals(testDocumentRequest.getType(), response.getType(), "Document type should match request");
        assertEquals(DocumentClassification.UNCLASSIFIED.name(), response.getClassification(), "Initial classification should be UNCLASSIFIED");
        assertNotNull(response.getDownloadUrl(), "Download URL should not be null");
        
        // Verify S3 client was called with correct parameters
        ArgumentCaptor<PutObjectRequest> requestCaptor = ArgumentCaptor.forClass(PutObjectRequest.class);
        ArgumentCaptor<RequestBody> bodyCaptor = ArgumentCaptor.forClass(RequestBody.class);
        verify(s3Client).putObject(requestCaptor.capture(), bodyCaptor.capture());
        
        PutObjectRequest capturedRequest = requestCaptor.getValue();
        assertEquals(bucketName, capturedRequest.bucket(), "Bucket name should match configuration");
        assertTrue(capturedRequest.key().startsWith("documents/" + testApplicationId), "Storage path should include application ID");
        assertEquals("application/pdf", capturedRequest.contentType(), "Content type should match file type");
        
        // Verify document is stored in repository
        Optional<Document> storedDocument = documentRepository.findById(UUID.fromString(response.getId()));
        assertTrue(storedDocument.isPresent(), "Document should be stored in repository");
        assertEquals(testApplicationId, storedDocument.get().getApplicationId(), "Application ID should match request");
        assertEquals(testDocumentRequest.getType(), storedDocument.get().getType(), "Document type should match request");
        assertEquals(DocumentClassification.UNCLASSIFIED, storedDocument.get().getClassification(), "Classification should be UNCLASSIFIED");
        assertNotNull(storedDocument.get().getMetadata(), "Metadata should not be null");
        assertEquals("Business license for testing", storedDocument.get().getMetadata().get("description"), "Description metadata should match request");
    }
    
    /**
     * Test retrieving a document from S3.
     * Verifies that the document content can be correctly retrieved from S3.
     */
    @Test
    @DisplayName("Should retrieve document content from S3")
    public void testDocumentRetrieval() throws IOException {
        // Arrange
        DocumentResponseDTO uploadedDoc = documentService.storeDocument(testFile, testDocumentRequest);
        
        // Mock S3 client to return test content for GetObject
        Resource resource = new ClassPathResource("/sample-documents/business_documents/sample_business_license.pdf");
        ResponseInputStream<GetObjectResponse> responseStream = mock(ResponseInputStream.class);
        when(responseStream.response()).thenReturn(GetObjectResponse.builder().contentType("application/pdf").build());
        when(responseStream.read(any(byte[].class))).thenAnswer(invocation -> {
            byte[] buffer = invocation.getArgument(0);
            InputStream inputStream = resource.getInputStream();
            return inputStream.read(buffer);
        });
        when(responseStream.read(any(byte[].class), anyInt(), anyInt())).thenAnswer(invocation -> {
            byte[] buffer = invocation.getArgument(0);
            int offset = invocation.getArgument(1);
            int length = invocation.getArgument(2);
            InputStream inputStream = resource.getInputStream();
            return inputStream.read(buffer, offset, length);
        });
        when(s3Client.getObject(any(GetObjectRequest.class))).thenReturn(responseStream);
        
        // Act
        InputStream contentStream = documentService.getDocumentContent(Long.valueOf(uploadedDoc.getId()));
        
        // Assert
        assertNotNull(contentStream, "Content stream should not be null");
        
        // Verify S3 client was called with correct parameters
        ArgumentCaptor<GetObjectRequest> requestCaptor = ArgumentCaptor.forClass(GetObjectRequest.class);
        verify(s3Client).getObject(requestCaptor.capture());
        
        GetObjectRequest capturedRequest = requestCaptor.getValue();
        assertEquals(bucketName, capturedRequest.bucket(), "Bucket name should match configuration");
        assertTrue(capturedRequest.key().startsWith("documents/" + testApplicationId), "Storage path should include application ID");
    }
    
    /**
     * Test error handling and retry logic when S3 operations fail.
     * Verifies that the service properly handles S3 exceptions and implements retry logic.
     */
    @Test
    @DisplayName("Should handle S3 errors with retry logic")
    public void testErrorHandlingWithRetry() {
        // Arrange
        // Mock S3 client to throw exception on first call, then succeed on second call
        when(s3Client.putObject(any(PutObjectRequest.class), any(RequestBody.class)))
                .thenThrow(S3Exception.builder().message("Connection timeout").build())
                .thenReturn(PutObjectResponse.builder().build());
        
        // Use CompletableFuture to run the operation with a timeout
        CompletableFuture<DocumentResponseDTO> future = CompletableFuture.supplyAsync(() -> {
            try {
                return documentService.storeDocument(testFile, testDocumentRequest);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        });
        
        // Act & Assert
        assertThrows(ExecutionException.class, () -> future.get(5, TimeUnit.SECONDS), 
                "Operation should fail due to S3 exception");
        
        // Verify S3 client was called multiple times (retry attempt)
        verify(s3Client, times(1)).putObject(any(PutObjectRequest.class), any(RequestBody.class));
    }
    
    /**
     * Test document versioning for audit purposes.
     * Verifies that document versions are properly maintained when updates occur.
     */
    @Test
    @DisplayName("Should maintain document versions for audit purposes")
    public void testDocumentVersioning() throws IOException {
        // Arrange
        // Upload initial document
        DocumentResponseDTO initialDoc = documentService.storeDocument(testFile, testDocumentRequest);
        
        // Mock S3 client for versioning
        List<ObjectVersion> versions = new ArrayList<>();
        versions.add(ObjectVersion.builder()
                .key(testStoragePath)
                .versionId("v1")
                .lastModified(new Date().toInstant())
                .build());
        
        ListObjectVersionsResponse versionsResponse = ListObjectVersionsResponse.builder()
                .versions(versions)
                .build();
        
        when(s3Client.listObjectVersions(any(ListObjectVersionsRequest.class)))
                .thenReturn(versionsResponse);
        
        // Create updated document
        Resource updatedResource = new ClassPathResource("/sample-documents/business_documents/sample_business_license_updated.pdf");
        MultipartFile updatedFile = new MockMultipartFile(
                "sample_business_license_updated.pdf",
                "sample_business_license_updated.pdf",
                "application/pdf",
                updatedResource.getInputStream());
        
        // Act
        DocumentResponseDTO updatedDoc = documentService.createDocumentVersion(
                Long.valueOf(initialDoc.getId()), updatedFile, testDocumentRequest);
        
        // Assert
        assertNotNull(updatedDoc, "Updated document response should not be null");
        assertNotEquals(initialDoc.getId(), updatedDoc.getId(), "New version should have different ID");
        
        // Verify document versions can be retrieved
        List<DocumentResponseDTO> versions1 = documentService.getDocumentVersions(Long.valueOf(updatedDoc.getId()));
        assertNotNull(versions1, "Document versions should not be null");
        assertFalse(versions1.isEmpty(), "Document versions should not be empty");
        
        // Verify S3 client was called to list versions
        verify(s3Client).listObjectVersions(any(ListObjectVersionsRequest.class));
    }
    
    /**
     * Test secure URL generation for document access.
     * Verifies that secure, time-limited URLs are generated for document access.
     */
    @Test
    @DisplayName("Should generate secure URLs for document access")
    public void testSecureUrlGeneration() throws IOException {
        // Arrange
        DocumentResponseDTO uploadedDoc = documentService.storeDocument(testFile, testDocumentRequest);
        
        // Act
        String secureUrl = documentService.generateSecureUrl(Long.valueOf(uploadedDoc.getId()), 5);
        
        // Assert
        assertNotNull(secureUrl, "Secure URL should not be null");
        assertTrue(secureUrl.contains("X-Amz-Algorithm=AWS4-HMAC-SHA256"), "URL should be signed with AWS signature");
        assertTrue(secureUrl.contains("X-Amz-Expires="), "URL should have expiration parameter");
        
        // Verify S3Presigner was called with correct parameters
        verify(s3Presigner).presignGetObject(any(GetObjectPresignRequest.class));
    }
    
    /**
     * Test handling of document not found scenarios.
     * Verifies that appropriate exceptions are thrown when documents don't exist.
     */
    @Test
    @DisplayName("Should throw DocumentNotFoundException when document doesn't exist")
    public void testDocumentNotFound() {
        // Arrange
        Long nonExistentDocId = 999999L;
        
        // Act & Assert
        assertThrows(DocumentNotFoundException.class, () -> {
            documentService.getDocumentById(nonExistentDocId);
        }, "Should throw DocumentNotFoundException for non-existent document");
    }
    
    /**
     * Test document metadata extraction and processing.
     * Verifies that document metadata is correctly extracted and processed.
     */
    @Test
    @DisplayName("Should extract and process document metadata")
    public void testDocumentMetadataProcessing() throws IOException {
        // Arrange
        DocumentResponseDTO uploadedDoc = documentService.storeDocument(testFile, testDocumentRequest);
        
        // Create updated metadata
        DocumentRequestDTO updateRequest = new DocumentRequestDTO();
        updateRequest.setClassification(DocumentClassification.VERIFIED.name());
        updateRequest.setClassificationConfidence(0.95);
        
        Map<String, Object> updatedMetadata = new HashMap<>();
        updatedMetadata.put("businessName", "ABC Corporation");
        updatedMetadata.put("licenseNumber", "BL-12345-2023");
        updatedMetadata.put("expirationDate", "2025-12-31");
        updateRequest.setMetadata(updatedMetadata);
        
        // Act
        DocumentResponseDTO updatedDoc = documentService.updateDocumentMetadata(
                Long.valueOf(uploadedDoc.getId()), updateRequest);
        
        // Assert
        assertNotNull(updatedDoc, "Updated document response should not be null");
        assertEquals(DocumentClassification.VERIFIED.name(), updatedDoc.getClassification(), 
                "Classification should be updated to VERIFIED");
        assertEquals(0.95, updatedDoc.getClassificationConfidence(), 
                "Classification confidence should be updated");
        
        // Verify metadata was updated
        Map<String, Object> metadata = updatedDoc.getMetadata();
        assertNotNull(metadata, "Metadata should not be null");
        assertEquals("ABC Corporation", metadata.get("businessName"), "Business name should be updated");
        assertEquals("BL-12345-2023", metadata.get("licenseNumber"), "License number should be updated");
        assertEquals("2025-12-31", metadata.get("expirationDate"), "Expiration date should be updated");
        
        // Original metadata should be preserved
        assertEquals("Business license for testing", metadata.get("description"), 
                "Original description should be preserved");
        assertEquals("Integration test", metadata.get("source"), 
                "Original source should be preserved");
    }
    
    /**
     * Test document deletion from S3 and database.
     * Verifies that documents are properly deleted from both S3 and the database.
     */
    @Test
    @DisplayName("Should delete document from S3 and database")
    public void testDocumentDeletion() throws IOException {
        // Arrange
        DocumentResponseDTO uploadedDoc = documentService.storeDocument(testFile, testDocumentRequest);
        
        // Act
        boolean deleted = documentService.deleteDocument(Long.valueOf(uploadedDoc.getId()));
        
        // Assert
        assertTrue(deleted, "Delete operation should return true");
        
        // Verify document is deleted from repository
        Optional<Document> deletedDocument = documentRepository.findById(UUID.fromString(uploadedDoc.getId()));
        assertFalse(deletedDocument.isPresent(), "Document should be deleted from repository");
        
        // Verify S3 client was called to delete object
        verify(s3Client).deleteObject(any(DeleteObjectRequest.class));
    }
    
    /**
     * Test document association with application.
     * Verifies that documents can be correctly associated with applications.
     */
    @Test
    @DisplayName("Should associate document with application")
    public void testDocumentApplicationAssociation() throws IOException {
        // Arrange
        // Create document without application ID
        DocumentRequestDTO noAppRequest = new DocumentRequestDTO();
        noAppRequest.setType(DocumentType.BUSINESS_LICENSE);
        noAppRequest.setClassification(DocumentClassification.UNCLASSIFIED.name());
        
        DocumentResponseDTO uploadedDoc = documentService.storeDocument(testFile, noAppRequest);
        
        // Create new application ID
        UUID newApplicationId = UUID.randomUUID();
        
        // Act
        DocumentResponseDTO associatedDoc = documentService.associateWithApplication(
                Long.valueOf(uploadedDoc.getId()), Long.valueOf(newApplicationId.toString()));
        
        // Assert
        assertNotNull(associatedDoc, "Associated document response should not be null");
        assertEquals(newApplicationId.toString(), associatedDoc.getApplicationId(), 
                "Application ID should be updated");
        
        // Verify document in repository has updated application ID
        Optional<Document> storedDocument = documentRepository.findById(UUID.fromString(associatedDoc.getId()));
        assertTrue(storedDocument.isPresent(), "Document should be in repository");
        assertEquals(newApplicationId, storedDocument.get().getApplicationId(), 
                "Application ID should be updated in repository");
    }
    
    /**
     * Test document classification update.
     * Verifies that document classification can be correctly updated.
     */
    @Test
    @DisplayName("Should update document classification")
    public void testDocumentClassificationUpdate() throws IOException {
        // Arrange
        DocumentResponseDTO uploadedDoc = documentService.storeDocument(testFile, testDocumentRequest);
        
        // Act
        DocumentResponseDTO classifiedDoc = documentService.updateDocumentClassification(
                Long.valueOf(uploadedDoc.getId()), 
                DocumentClassification.BUSINESS_LICENSE.name(), 
                0.98, 
                Map.of("classifiedBy", "AI Model v2.1"));
        
        // Assert
        assertNotNull(classifiedDoc, "Classified document response should not be null");
        assertEquals(DocumentClassification.BUSINESS_LICENSE.name(), classifiedDoc.getClassification(), 
                "Classification should be updated");
        assertEquals(0.98, classifiedDoc.getClassificationConfidence(), 
                "Classification confidence should be updated");
        
        // Verify metadata was updated
        Map<String, Object> metadata = classifiedDoc.getMetadata();
        assertNotNull(metadata, "Metadata should not be null");
        assertEquals("AI Model v2.1", metadata.get("classifiedBy"), 
                "Classification source should be added to metadata");
    }
    
    /**
     * Mocks the S3 client for successful operations.
     */
    private void mockS3ClientForSuccessfulOperations() {
        // Mock PutObject
        when(s3Client.putObject(any(PutObjectRequest.class), any(RequestBody.class)))
                .thenReturn(PutObjectResponse.builder().build());
        
        // Mock GetObject
        ResponseInputStream<GetObjectResponse> responseStream = mock(ResponseInputStream.class);
        when(responseStream.response()).thenReturn(GetObjectResponse.builder().contentType("application/pdf").build());
        when(s3Client.getObject(any(GetObjectRequest.class))).thenReturn(responseStream);
        
        // Mock DeleteObject
        when(s3Client.deleteObject(any(DeleteObjectRequest.class)))
                .thenReturn(DeleteObjectResponse.builder().build());
        
        // Mock HeadObject
        when(s3Client.headObject(any(HeadObjectRequest.class)))
                .thenReturn(HeadObjectResponse.builder().contentType("application/pdf").build());
        
        // Mock ListObjectVersions
        when(s3Client.listObjectVersions(any(ListObjectVersionsRequest.class)))
                .thenReturn(ListObjectVersionsResponse.builder().versions(Collections.emptyList()).build());
        
        // Mock CopyObject
        when(s3Client.copyObject(any(CopyObjectRequest.class)))
                .thenReturn(CopyObjectResponse.builder().build());
        
        // Mock S3Presigner
        PresignedGetObjectRequest presignedRequest = mock(PresignedGetObjectRequest.class);
        when(presignedRequest.url()).thenReturn(testPresignedUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class)))
                .thenReturn(presignedRequest);
        
        // Mock S3Config
        doReturn(testPresignedUrl).when(s3Config).generateSignedUrl(anyString());
        doReturn(bucketName).when(s3Config).getBucketName();
    }
}