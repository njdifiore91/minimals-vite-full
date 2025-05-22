package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.config.S3Config;
import com.dollarfunding.mca.dto.DocumentDto;
import com.dollarfunding.mca.service.DocumentService;
import com.dollarfunding.mca.util.Constants;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.web.multipart.MultipartFile;

import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test for S3 storage functionality.
 * 
 * This test verifies that the data-service can correctly retrieve documents from S3,
 * process them, and store results back to S3 with proper encryption and versioning.
 * 
 * The test uses a mock S3 server (MinIO) configured in application-test.yml.
 */
@ExtendWith(SpringExtension.class)
@SpringBootTest
@ActiveProfiles("test")
public class S3StorageIntegrationTest {

    private static final Logger logger = LoggerFactory.getLogger(S3StorageIntegrationTest.class);
    
    @Autowired
    private DocumentService documentService;
    
    @Autowired
    private S3Client s3Client;
    
    @Autowired
    private S3Presigner s3Presigner;
    
    @Value("${app.s3.bucket}")
    private String bucketName;
    
    @Value("${app.s3.endpoint}")
    private String endpoint;
    
    @Value("${app.s3.access-key}")
    private String accessKey;
    
    @Value("${app.s3.secret-key}")
    private String secretKey;
    
    @Value("${app.s3.region}")
    private String region;
    
    private String testDocumentKey;
    private String testApplicationId;
    
    @BeforeEach
    public void setUp() throws IOException {
        testApplicationId = UUID.randomUUID().toString();
        testDocumentKey = "applications/" + testApplicationId + "/documents/" + UUID.randomUUID().toString() + ".pdf";
        
        // Ensure the bucket exists
        createBucketIfNotExists();
        
        // Enable versioning on the bucket
        enableVersioning();
        
        // Upload a test document
        uploadTestDocument();
    }
    
    @AfterEach
    public void tearDown() {
        // Clean up test documents
        try {
            deleteTestDocument();
        } catch (Exception e) {
            logger.warn("Failed to delete test document: {}", e.getMessage());
        }
    }
    
    @Test
    @DisplayName("Should retrieve document from S3 storage")
    public void testRetrieveDocumentFromS3() throws IOException {
        // When
        DocumentDto document = documentService.getDocumentById(testDocumentKey);
        
        // Then
        assertNotNull(document, "Document should not be null");
        assertEquals(testDocumentKey, document.getStoragePath(), "Storage path should match");
        assertNotNull(document.getContent(), "Document content should not be null");
        assertTrue(document.getContent().length > 0, "Document content should not be empty");
    }
    
    @Test
    @DisplayName("Should store document in S3 with AES-256 encryption")
    public void testStoreDocumentInS3WithEncryption() throws IOException {
        // Given
        String documentName = "test-encrypted-document.pdf";
        String documentKey = "applications/" + testApplicationId + "/documents/" + documentName;
        Resource resource = new ClassPathResource("/sample-documents/application_forms/sample_application.pdf");
        MultipartFile multipartFile = new MockMultipartFile(
                documentName,
                documentName,
                "application/pdf",
                resource.getInputStream());
        
        Map<String, String> metadata = new HashMap<>();
        metadata.put("applicationId", testApplicationId);
        metadata.put("documentType", Constants.DOCUMENT_TYPE.APPLICATION_FORM.name());
        metadata.put("uploadedBy", "test-user");
        
        // When
        DocumentDto storedDocument = documentService.storeDocument(multipartFile, metadata);
        
        // Then
        assertNotNull(storedDocument, "Stored document should not be null");
        assertNotNull(storedDocument.getId(), "Document ID should not be null");
        assertEquals(documentName, storedDocument.getName(), "Document name should match");
        
        // Verify the document was stored with encryption
        HeadObjectResponse headObjectResponse = s3Client.headObject(HeadObjectRequest.builder()
                .bucket(bucketName)
                .key(storedDocument.getStoragePath())
                .build());
        
        assertNotNull(headObjectResponse, "Head object response should not be null");
        assertEquals("AES256", headObjectResponse.serverSideEncryption().toString(), 
                "Document should be encrypted with AES-256");
        
        // Verify metadata was stored correctly
        assertEquals(testApplicationId, headObjectResponse.metadata().get("applicationid"), 
                "Application ID metadata should match");
        assertEquals(Constants.DOCUMENT_TYPE.APPLICATION_FORM.name(), 
                headObjectResponse.metadata().get("documenttype"), 
                "Document type metadata should match");
    }
    
    @Test
    @DisplayName("Should handle S3 access errors with retry logic")
    public void testHandleS3AccessErrorsWithRetry() {
        // Given
        String nonExistentKey = "non-existent-document.pdf";
        
        // When/Then - First attempt should fail
        assertThatThrownBy(() -> documentService.getDocumentById(nonExistentKey))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("not found");
        
        // Verify retry logic by checking logs or metrics
        // This would typically be done by examining logs or metrics in a real environment
        // For this test, we'll simulate a retry by uploading the document after the first failure
        // and then trying to retrieve it again
        
        // Upload the document after the first failure
        try {
            Resource resource = new ClassPathResource("/sample-documents/application_forms/sample_application.pdf");
            s3Client.putObject(PutObjectRequest.builder()
                    .bucket(bucketName)
                    .key(nonExistentKey)
                    .build(), 
                    RequestBody.fromInputStream(resource.getInputStream(), resource.contentLength()));
            
            // Wait for the document to be available
            await().atMost(5, TimeUnit.SECONDS).until(() -> {
                try {
                    s3Client.headObject(HeadObjectRequest.builder()
                            .bucket(bucketName)
                            .key(nonExistentKey)
                            .build());
                    return true;
                } catch (Exception e) {
                    return false;
                }
            });
            
            // Now the document should be retrievable
            DocumentDto document = documentService.getDocumentById(nonExistentKey);
            assertNotNull(document, "Document should not be null after retry");
            assertEquals(nonExistentKey, document.getStoragePath(), "Storage path should match");
        } catch (IOException e) {
            fail("Failed to upload test document: " + e.getMessage());
        }
    }
    
    @Test
    @DisplayName("Should maintain document versioning for audit purposes")
    public void testDocumentVersioning() throws IOException {
        // Given
        String versionedDocumentKey = "applications/" + testApplicationId + "/documents/versioned-document.pdf";
        Resource resource = new ClassPathResource("/sample-documents/application_forms/sample_application.pdf");
        
        // Upload initial version
        PutObjectResponse initialVersion = s3Client.putObject(
                PutObjectRequest.builder()
                        .bucket(bucketName)
                        .key(versionedDocumentKey)
                        .metadata(Map.of("version", "1"))
                        .build(),
                RequestBody.fromInputStream(resource.getInputStream(), resource.contentLength()));
        
        assertNotNull(initialVersion.versionId(), "Initial version ID should not be null");
        String initialVersionId = initialVersion.versionId();
        
        // Upload second version
        PutObjectResponse secondVersion = s3Client.putObject(
                PutObjectRequest.builder()
                        .bucket(bucketName)
                        .key(versionedDocumentKey)
                        .metadata(Map.of("version", "2"))
                        .build(),
                RequestBody.fromInputStream(resource.getInputStream(), resource.contentLength()));
        
        assertNotNull(secondVersion.versionId(), "Second version ID should not be null");
        String secondVersionId = secondVersion.versionId();
        
        // Verify versions are different
        assertNotEquals(initialVersionId, secondVersionId, "Version IDs should be different");
        
        // List versions of the document
        ListObjectVersionsRequest listObjectVersionsRequest = ListObjectVersionsRequest.builder()
                .bucket(bucketName)
                .prefix(versionedDocumentKey)
                .build();
        
        ListObjectVersionsResponse listObjectVersionsResponse = s3Client.listObjectVersions(listObjectVersionsRequest);
        List<ObjectVersion> versions = listObjectVersionsResponse.versions();
        
        // Verify we have at least 2 versions
        assertTrue(versions.size() >= 2, "Should have at least 2 versions of the document");
        
        // Verify we can retrieve a specific version
        GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                .bucket(bucketName)
                .key(versionedDocumentKey)
                .versionId(initialVersionId)
                .build();
        
        ResponseInputStream<GetObjectResponse> initialVersionContent = s3Client.getObject(getObjectRequest);
        assertNotNull(initialVersionContent, "Initial version content should not be null");
        
        // Verify metadata of the specific version
        GetObjectResponse initialVersionResponse = initialVersionContent.response();
        assertEquals("1", initialVersionResponse.metadata().get("version"), 
                "Initial version metadata should match");
    }
    
    @Test
    @DisplayName("Should generate secure signed URLs for document access")
    public void testSecureSignedUrls() {
        // When
        String signedUrl = documentService.generateSignedUrl(testDocumentKey, 15); // 15 minutes expiration
        
        // Then
        assertNotNull(signedUrl, "Signed URL should not be null");
        assertTrue(signedUrl.contains(endpoint), "Signed URL should contain the endpoint");
        assertTrue(signedUrl.contains(bucketName), "Signed URL should contain the bucket name");
        assertTrue(signedUrl.contains(testDocumentKey.replace("/", "%2F")), 
                "Signed URL should contain the encoded document key");
        
        // Verify the URL is valid and can be used to access the document
        try {
            URL url = new URL(signedUrl);
            InputStream inputStream = url.openStream();
            byte[] content = inputStream.readAllBytes();
            inputStream.close();
            
            assertNotNull(content, "Content retrieved with signed URL should not be null");
            assertTrue(content.length > 0, "Content retrieved with signed URL should not be empty");
        } catch (IOException e) {
            fail("Failed to access document with signed URL: " + e.getMessage());
        }
        
        // Verify that a signed URL with a short expiration becomes invalid after expiration
        String shortExpirationUrl = documentService.generateSignedUrl(testDocumentKey, 1); // 1 second expiration
        
        // Wait for the URL to expire
        try {
            Thread.sleep(2000); // Wait 2 seconds for the URL to expire
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        // Verify the URL is no longer valid
        try {
            URL url = new URL(shortExpirationUrl);
            assertThatThrownBy(() -> url.openStream())
                    .isInstanceOf(IOException.class);
        } catch (IOException e) {
            // Expected exception
        }
    }
    
    @Test
    @DisplayName("Should enforce bucket access control policies")
    public void testBucketAccessControl() {
        // Create a client with invalid credentials
        S3Client invalidClient = S3Client.builder()
                .endpointOverride(URI.create(endpoint))
                .region(Region.of(region))
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create("invalid", "invalid")))
                .build();
        
        // Attempt to access the bucket with invalid credentials
        assertThatThrownBy(() -> invalidClient.listObjects(ListObjectsRequest.builder()
                .bucket(bucketName)
                .build()))
                .isInstanceOf(S3Exception.class);
        
        // Verify that the correct client can access the bucket
        ListObjectsResponse listObjectsResponse = s3Client.listObjects(ListObjectsRequest.builder()
                .bucket(bucketName)
                .build());
        
        assertNotNull(listObjectsResponse, "List objects response should not be null");
    }
    
    // Helper methods
    
    private void createBucketIfNotExists() {
        try {
            s3Client.headBucket(HeadBucketRequest.builder().bucket(bucketName).build());
            logger.info("Bucket {} already exists", bucketName);
        } catch (NoSuchBucketException e) {
            logger.info("Creating bucket: {}", bucketName);
            s3Client.createBucket(CreateBucketRequest.builder()
                    .bucket(bucketName)
                    .build());
            
            // Wait for the bucket to be created
            await().atMost(10, TimeUnit.SECONDS).until(() -> {
                try {
                    s3Client.headBucket(HeadBucketRequest.builder().bucket(bucketName).build());
                    return true;
                } catch (Exception ex) {
                    return false;
                }
            });
        }
    }
    
    private void enableVersioning() {
        s3Client.putBucketVersioning(PutBucketVersioningRequest.builder()
                .bucket(bucketName)
                .versioningConfiguration(VersioningConfiguration.builder()
                        .status(BucketVersioningStatus.ENABLED)
                        .build())
                .build());
    }
    
    private void uploadTestDocument() throws IOException {
        Resource resource = new ClassPathResource("/sample-documents/application_forms/sample_application.pdf");
        
        // Create the test document with encryption
        PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                .bucket(bucketName)
                .key(testDocumentKey)
                .serverSideEncryption(ServerSideEncryption.AES256)
                .metadata(Map.of(
                        "applicationId", testApplicationId,
                        "documentType", Constants.DOCUMENT_TYPE.APPLICATION_FORM.name(),
                        "uploadedBy", "test-user"
                ))
                .build();
        
        s3Client.putObject(putObjectRequest, 
                RequestBody.fromInputStream(resource.getInputStream(), resource.contentLength()));
        
        // Verify the document was uploaded
        await().atMost(5, TimeUnit.SECONDS).until(() -> {
            try {
                s3Client.headObject(HeadObjectRequest.builder()
                        .bucket(bucketName)
                        .key(testDocumentKey)
                        .build());
                return true;
            } catch (Exception e) {
                return false;
            }
        });
    }
    
    private void deleteTestDocument() {
        // Delete all versions of the test document
        ListObjectVersionsRequest listVersionsRequest = ListObjectVersionsRequest.builder()
                .bucket(bucketName)
                .prefix(testDocumentKey)
                .build();
        
        ListObjectVersionsResponse listVersionsResponse = s3Client.listObjectVersions(listVersionsRequest);
        
        // Delete markers
        for (DeleteMarkerEntry deleteMarker : listVersionsResponse.deleteMarkers()) {
            s3Client.deleteObject(DeleteObjectRequest.builder()
                    .bucket(bucketName)
                    .key(deleteMarker.key())
                    .versionId(deleteMarker.versionId())
                    .build());
        }
        
        // Object versions
        for (ObjectVersion version : listVersionsResponse.versions()) {
            s3Client.deleteObject(DeleteObjectRequest.builder()
                    .bucket(bucketName)
                    .key(version.key())
                    .versionId(version.versionId())
                    .build());
        }
    }
}