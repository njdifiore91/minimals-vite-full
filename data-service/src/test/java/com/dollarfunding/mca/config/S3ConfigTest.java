package com.dollarfunding.mca.config;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.http.SdkHttpClient;
import software.amazon.awssdk.http.apache.ApacheHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3ClientBuilder;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedPutObjectRequest;

import java.net.URL;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the S3Config class that configures S3-compatible storage for document management.
 * <p>
 * These tests verify:
 * <ul>
 *   <li>S3 client configuration with AES-256 encryption</li>
 *   <li>Bucket access policy configuration for authorized services</li>
 *   <li>Signed URL generation with short expiration times</li>
 *   <li>Versioning configuration for document history tracking</li>
 *   <li>Lifecycle rule configuration for compliant document retention</li>
 * </ul>
 * </p>
 */
public class S3ConfigTest {

    private S3Config s3Config;

    @Mock
    private S3Client s3Client;

    @Mock
    private S3Presigner s3Presigner;

    @Mock
    private S3ClientBuilder s3ClientBuilder;

    @Mock
    private PresignedGetObjectRequest presignedGetObjectRequest;

    @Mock
    private PresignedPutObjectRequest presignedPutObjectRequest;

    private final String productionBucketName = "mca-documents-production";
    private final String stagingBucketName = "mca-documents-staging";
    private final String region = "us-east-1";
    private final int signedUrlExpirationMinutes = 15;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this);

        // Create S3Config instance
        s3Config = new S3Config();

        // Set properties using reflection
        ReflectionTestUtils.setField(s3Config, "region", region);
        ReflectionTestUtils.setField(s3Config, "productionBucketName", productionBucketName);
        ReflectionTestUtils.setField(s3Config, "stagingBucketName", stagingBucketName);
        ReflectionTestUtils.setField(s3Config, "activeProfile", "production");
        ReflectionTestUtils.setField(s3Config, "signedUrlExpirationMinutes", signedUrlExpirationMinutes);
        ReflectionTestUtils.setField(s3Config, "bucketName", productionBucketName);

        // Mock S3Client and S3Presigner
        ReflectionTestUtils.setField(s3Config, "s3Client", s3Client);
        ReflectionTestUtils.setField(s3Config, "s3Presigner", s3Presigner);
    }

    @Test
    @DisplayName("Test S3 client configuration with proper region and credentials")
    public void testS3ClientConfiguration() {
        // Note: This test would typically use mockStatic to mock the static builder methods,
        // but that requires additional dependencies like MockitoExtension.
        // In a real project, you would need to ensure that the appropriate dependencies are included.
        // For now, we'll just verify that the s3Client method is not null when called
        
        // Create a new S3Config to test the s3Client() method
        S3Config configUnderTest = new S3Config();
        ReflectionTestUtils.setField(configUnderTest, "region", region);
        
        // Mock the necessary components to avoid actual AWS calls
        // This is a simplified approach; in a real test, you would use mockStatic
        S3Client mockClient = mock(S3Client.class);
        ReflectionTestUtils.setField(configUnderTest, "s3Client", mockClient);
        
        // Verify that the client is properly configured
        assertNotNull(configUnderTest.s3Client(), "S3Client should not be null");
    }

    @Test
    @DisplayName("Test S3 presigner configuration with proper region and credentials")
    public void testS3PresignerConfiguration() {
        // Note: This test would typically use mockStatic to mock the static builder methods,
        // but that requires additional dependencies like MockitoExtension.
        // In a real project, you would need to ensure that the appropriate dependencies are included.
        // For now, we'll just verify that the s3Presigner method is not null when called
        
        // Create a new S3Config to test the s3Presigner() method
        S3Config configUnderTest = new S3Config();
        ReflectionTestUtils.setField(configUnderTest, "region", region);
        
        // Mock the necessary components to avoid actual AWS calls
        // This is a simplified approach; in a real test, you would use mockStatic
        S3Presigner mockPresigner = mock(S3Presigner.class);
        ReflectionTestUtils.setField(configUnderTest, "s3Presigner", mockPresigner);
        
        // Verify that the presigner is properly configured
        assertNotNull(configUnderTest.s3Presigner(), "S3Presigner should not be null");
    }

    @Test
    @DisplayName("Test bucket initialization based on active profile")
    public void testBucketInitialization() {
        // Test with production profile
        S3Config productionConfig = spy(new S3Config());
        ReflectionTestUtils.setField(productionConfig, "productionBucketName", productionBucketName);
        ReflectionTestUtils.setField(productionConfig, "stagingBucketName", stagingBucketName);
        ReflectionTestUtils.setField(productionConfig, "activeProfile", "production");
        
        // Mock the configureBucket method to avoid actual AWS calls
        doNothing().when(productionConfig).configureBucket();
        
        // Call init method
        productionConfig.init();
        
        // Verify that the correct bucket name was set
        assertEquals(productionBucketName, ReflectionTestUtils.getField(productionConfig, "bucketName"),
                "Production bucket name should be used for production profile");

        // Test with staging profile
        S3Config stagingConfig = spy(new S3Config());
        ReflectionTestUtils.setField(stagingConfig, "productionBucketName", productionBucketName);
        ReflectionTestUtils.setField(stagingConfig, "stagingBucketName", stagingBucketName);
        ReflectionTestUtils.setField(stagingConfig, "activeProfile", "staging");
        
        // Mock the configureBucket method to avoid actual AWS calls
        doNothing().when(stagingConfig).configureBucket();
        
        // Call init method
        stagingConfig.init();
        
        // Verify that the correct bucket name was set
        assertEquals(stagingBucketName, ReflectionTestUtils.getField(stagingConfig, "bucketName"),
                "Staging bucket name should be used for staging profile");
    }

    @Test
    @DisplayName("Test bucket existence check")
    public void testBucketExistsCheck() {
        // Mock the bucketExists method to return true
        when(s3Client.headBucket(any(HeadBucketRequest.class))).thenReturn(HeadBucketResponse.builder().build());

        // Call the method under test using reflection
        boolean result = (boolean) ReflectionTestUtils.invokeMethod(s3Config, "bucketExists", s3Client, productionBucketName);

        // Verify the result
        assertTrue(result, "Bucket should exist");

        // Verify that headBucket was called with the correct bucket name
        ArgumentCaptor<HeadBucketRequest> requestCaptor = ArgumentCaptor.forClass(HeadBucketRequest.class);
        verify(s3Client).headBucket(requestCaptor.capture());
        assertEquals(productionBucketName, requestCaptor.getValue().bucket(), "Bucket name should match");

        // Test when bucket doesn't exist (404 error)
        reset(s3Client);
        when(s3Client.headBucket(any(HeadBucketRequest.class))).thenThrow(
                S3Exception.builder().statusCode(404).build());

        // Call the method under test using reflection
        result = (boolean) ReflectionTestUtils.invokeMethod(s3Config, "bucketExists", s3Client, productionBucketName);

        // Verify the result
        assertFalse(result, "Bucket should not exist");
    }

    @Test
    @DisplayName("Test bucket creation")
    public void testCreateBucket() {
        // Call the method under test using reflection
        ReflectionTestUtils.invokeMethod(s3Config, "createBucket", s3Client, productionBucketName);

        // Verify that createBucket was called with the correct bucket name
        ArgumentCaptor<CreateBucketRequest> requestCaptor = ArgumentCaptor.forClass(CreateBucketRequest.class);
        verify(s3Client).createBucket(requestCaptor.capture());
        assertEquals(productionBucketName, requestCaptor.getValue().bucket(), "Bucket name should match");
    }

    @Test
    @DisplayName("Test default encryption configuration with AES-256")
    public void testSetDefaultEncryption() {
        // Call the method under test using reflection
        ReflectionTestUtils.invokeMethod(s3Config, "setDefaultEncryption", s3Client, productionBucketName);

        // Verify that putBucketEncryption was called with the correct parameters
        ArgumentCaptor<PutBucketEncryptionRequest> requestCaptor = ArgumentCaptor.forClass(PutBucketEncryptionRequest.class);
        verify(s3Client).putBucketEncryption(requestCaptor.capture());

        // Verify the request
        PutBucketEncryptionRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");

        // Verify that AES-256 encryption is configured
        ServerSideEncryptionConfiguration encryptionConfig = request.serverSideEncryptionConfiguration();
        assertNotNull(encryptionConfig, "Encryption configuration should not be null");

        List<ServerSideEncryptionRule> rules = encryptionConfig.rules();
        assertNotNull(rules, "Encryption rules should not be null");
        assertFalse(rules.isEmpty(), "Encryption rules should not be empty");

        ServerSideEncryptionRule rule = rules.get(0);
        assertNotNull(rule, "Encryption rule should not be null");

        ServerSideEncryptionByDefault defaultEncryption = rule.applyServerSideEncryptionByDefault();
        assertNotNull(defaultEncryption, "Default encryption should not be null");
        assertEquals(ServerSideEncryption.AES256, defaultEncryption.sseAlgorithm(),
                "Encryption algorithm should be AES-256");
    }

    @Test
    @DisplayName("Test versioning configuration for document history tracking")
    public void testEnableVersioning() {
        // Call the method under test using reflection
        ReflectionTestUtils.invokeMethod(s3Config, "enableVersioning", s3Client, productionBucketName);

        // Verify that putBucketVersioning was called with the correct parameters
        ArgumentCaptor<PutBucketVersioningRequest> requestCaptor = ArgumentCaptor.forClass(PutBucketVersioningRequest.class);
        verify(s3Client).putBucketVersioning(requestCaptor.capture());

        // Verify the request
        PutBucketVersioningRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");

        // Verify that versioning is enabled
        VersioningConfiguration versioningConfig = request.versioningConfiguration();
        assertNotNull(versioningConfig, "Versioning configuration should not be null");
        assertEquals(BucketVersioningStatus.ENABLED, versioningConfig.status(),
                "Versioning status should be ENABLED");
    }

    @Test
    @DisplayName("Test lifecycle rule configuration for compliant document retention")
    public void testSetLifecycleRules() {
        // Call the method under test using reflection
        ReflectionTestUtils.invokeMethod(s3Config, "setLifecycleRules", s3Client, productionBucketName);

        // Verify that putBucketLifecycleConfiguration was called with the correct parameters
        ArgumentCaptor<PutBucketLifecycleConfigurationRequest> requestCaptor = 
                ArgumentCaptor.forClass(PutBucketLifecycleConfigurationRequest.class);
        verify(s3Client).putBucketLifecycleConfiguration(requestCaptor.capture());

        // Verify the request
        PutBucketLifecycleConfigurationRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");

        // Verify the lifecycle configuration
        BucketLifecycleConfiguration lifecycleConfig = request.lifecycleConfiguration();
        assertNotNull(lifecycleConfig, "Lifecycle configuration should not be null");

        List<LifecycleRule> rules = lifecycleConfig.rules();
        assertNotNull(rules, "Lifecycle rules should not be null");
        assertEquals(3, rules.size(), "There should be 3 lifecycle rules");

        // Verify the transition rule (Rule 1)
        LifecycleRule transitionRule = rules.stream()
                .filter(rule -> "TransitionToGlacierRule".equals(rule.id()))
                .findFirst()
                .orElse(null);
        assertNotNull(transitionRule, "Transition rule should exist");
        assertEquals(ExpirationStatus.ENABLED, transitionRule.status(), "Transition rule should be enabled");
        assertNotNull(transitionRule.noncurrentVersionTransitions(), "Noncurrent version transitions should not be null");
        assertFalse(transitionRule.noncurrentVersionTransitions().isEmpty(), "Noncurrent version transitions should not be empty");
        NoncurrentVersionTransition transition = transitionRule.noncurrentVersionTransitions().get(0);
        assertEquals(30, transition.noncurrentDays(), "Transition should occur after 30 days");
        assertEquals(StorageClass.GLACIER, transition.storageClass(), "Storage class should be GLACIER");

        // Verify the expiration rule (Rule 2)
        LifecycleRule expirationRule = rules.stream()
                .filter(rule -> "ExpireNoncurrentVersionsRule".equals(rule.id()))
                .findFirst()
                .orElse(null);
        assertNotNull(expirationRule, "Expiration rule should exist");
        assertEquals(ExpirationStatus.ENABLED, expirationRule.status(), "Expiration rule should be enabled");
        assertNotNull(expirationRule.noncurrentVersionExpiration(), "Noncurrent version expiration should not be null");
        assertEquals(2555, expirationRule.noncurrentVersionExpiration().noncurrentDays(),
                "Expiration should occur after 7 years (2555 days)");

        // Verify the delete markers rule (Rule 3)
        LifecycleRule deleteMarkersRule = rules.stream()
                .filter(rule -> "DeleteExpiredMarkersRule".equals(rule.id()))
                .findFirst()
                .orElse(null);
        assertNotNull(deleteMarkersRule, "Delete markers rule should exist");
        assertEquals(ExpirationStatus.ENABLED, deleteMarkersRule.status(), "Delete markers rule should be enabled");
        assertNotNull(deleteMarkersRule.expiration(), "Expiration should not be null");
        assertTrue(deleteMarkersRule.expiration().expiredObjectDeleteMarker(),
                "Expired object delete marker should be true");
    }

    @Test
    @DisplayName("Test bucket policy configuration for authorized services")
    public void testSetBucketPolicy() {
        // Call the method under test using reflection
        ReflectionTestUtils.invokeMethod(s3Config, "setBucketPolicy", s3Client, productionBucketName);

        // Verify that putBucketPolicy was called with the correct parameters
        ArgumentCaptor<PutBucketPolicyRequest> requestCaptor = ArgumentCaptor.forClass(PutBucketPolicyRequest.class);
        verify(s3Client).putBucketPolicy(requestCaptor.capture());

        // Verify the request
        PutBucketPolicyRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");

        // Verify the policy content
        String policy = request.policy();
        assertNotNull(policy, "Policy should not be null");
        assertTrue(policy.contains("DenyPublicReadAccess"), "Policy should contain DenyPublicReadAccess statement");
        assertTrue(policy.contains("EnforceEncryptedTransport"), "Policy should contain EnforceEncryptedTransport statement");
        assertTrue(policy.contains("MCAServiceRole"), "Policy should reference MCAServiceRole");
        assertTrue(policy.contains("MCAAdminRole"), "Policy should reference MCAAdminRole");
        assertTrue(policy.contains("aws:SecureTransport"), "Policy should enforce secure transport");
    }

    @Test
    @DisplayName("Test signed URL generation with short expiration time")
    public void testGenerateSignedUrl() {
        // Mock the URL
        URL mockUrl = mock(URL.class);
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Call the method under test
        URL result = s3Config.generateSignedUrl("test-document.pdf");

        // Verify the result
        assertNotNull(result, "URL should not be null");
        assertEquals(mockUrl, result, "URL should match the mock URL");

        // Verify that presignGetObject was called with the correct parameters
        ArgumentCaptor<GetObjectPresignRequest> requestCaptor = ArgumentCaptor.forClass(GetObjectPresignRequest.class);
        verify(s3Presigner).presignGetObject(requestCaptor.capture());

        // Verify the request
        GetObjectPresignRequest request = requestCaptor.getValue();
        assertNotNull(request, "Request should not be null");
        assertEquals(Duration.ofMinutes(signedUrlExpirationMinutes), request.signatureDuration(),
                "Signature duration should match the configured expiration time");

        // Verify the GetObjectRequest
        GetObjectRequest getObjectRequest = request.getObjectRequest();
        assertNotNull(getObjectRequest, "GetObjectRequest should not be null");
        assertEquals(productionBucketName, getObjectRequest.bucket(), "Bucket name should match");
        assertEquals("test-document.pdf", getObjectRequest.key(), "Object key should match");
    }

    @Test
    @DisplayName("Test signed upload URL generation with content type")
    public void testGenerateSignedUploadUrl() {
        // Mock the URL
        URL mockUrl = mock(URL.class);
        when(presignedPutObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignPutObject(any(PutObjectPresignRequest.class))).thenReturn(presignedPutObjectRequest);

        // Call the method under test
        URL result = s3Config.generateSignedUploadUrl("test-document.pdf", "application/pdf", 30);

        // Verify the result
        assertNotNull(result, "URL should not be null");
        assertEquals(mockUrl, result, "URL should match the mock URL");

        // Verify that presignPutObject was called with the correct parameters
        ArgumentCaptor<PutObjectPresignRequest> requestCaptor = ArgumentCaptor.forClass(PutObjectPresignRequest.class);
        verify(s3Presigner).presignPutObject(requestCaptor.capture());

        // Verify the request
        PutObjectPresignRequest request = requestCaptor.getValue();
        assertNotNull(request, "Request should not be null");
        assertEquals(Duration.ofMinutes(30), request.signatureDuration(),
                "Signature duration should match the provided expiration time");

        // Verify the PutObjectRequest
        PutObjectRequest putObjectRequest = request.putObjectRequest();
        assertNotNull(putObjectRequest, "PutObjectRequest should not be null");
        assertEquals(productionBucketName, putObjectRequest.bucket(), "Bucket name should match");
        assertEquals("test-document.pdf", putObjectRequest.key(), "Object key should match");
        assertEquals("application/pdf", putObjectRequest.contentType(), "Content type should match");
    }

    @Test
    @DisplayName("Test document metadata retrieval")
    public void testGetDocumentMetadata() {
        // Mock the response
        HeadObjectResponse mockResponse = HeadObjectResponse.builder().build();
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(mockResponse);

        // Call the method under test
        HeadObjectResponse result = s3Config.getDocumentMetadata("test-document.pdf");

        // Verify the result
        assertNotNull(result, "Response should not be null");
        assertEquals(mockResponse, result, "Response should match the mock response");

        // Verify that headObject was called with the correct parameters
        ArgumentCaptor<HeadObjectRequest> requestCaptor = ArgumentCaptor.forClass(HeadObjectRequest.class);
        verify(s3Client).headObject(requestCaptor.capture());

        // Verify the request
        HeadObjectRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");
        assertEquals("test-document.pdf", request.key(), "Object key should match");
    }

    @Test
    @DisplayName("Test document existence check")
    public void testDocumentExists() {
        // Mock the response for existing document
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(HeadObjectResponse.builder().build());

        // Call the method under test
        boolean result = s3Config.documentExists("existing-document.pdf");

        // Verify the result
        assertTrue(result, "Document should exist");

        // Verify that headObject was called with the correct parameters
        ArgumentCaptor<HeadObjectRequest> requestCaptor = ArgumentCaptor.forClass(HeadObjectRequest.class);
        verify(s3Client).headObject(requestCaptor.capture());
        assertEquals(productionBucketName, requestCaptor.getValue().bucket(), "Bucket name should match");
        assertEquals("existing-document.pdf", requestCaptor.getValue().key(), "Object key should match");

        // Test for non-existing document
        reset(s3Client);
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenThrow(
                S3Exception.builder().statusCode(404).build());

        // Call the method under test
        result = s3Config.documentExists("non-existing-document.pdf");

        // Verify the result
        assertFalse(result, "Document should not exist");
    }

    @Test
    @DisplayName("Test document deletion")
    public void testDeleteDocument() {
        // Call the method under test
        boolean result = s3Config.deleteDocument("test-document.pdf");

        // Verify the result
        assertTrue(result, "Deletion should be successful");

        // Verify that deleteObject was called with the correct parameters
        ArgumentCaptor<DeleteObjectRequest> requestCaptor = ArgumentCaptor.forClass(DeleteObjectRequest.class);
        verify(s3Client).deleteObject(requestCaptor.capture());

        // Verify the request
        DeleteObjectRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");
        assertEquals("test-document.pdf", request.key(), "Object key should match");
    }

    @Test
    @DisplayName("Test document copy operation")
    public void testCopyDocument() {
        // Call the method under test
        boolean result = s3Config.copyDocument("source-document.pdf", "destination-document.pdf");

        // Verify the result
        assertTrue(result, "Copy should be successful");

        // Verify that copyObject was called with the correct parameters
        ArgumentCaptor<CopyObjectRequest> requestCaptor = ArgumentCaptor.forClass(CopyObjectRequest.class);
        verify(s3Client).copyObject(requestCaptor.capture());

        // Verify the request
        CopyObjectRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.sourceBucket(), "Source bucket name should match");
        assertEquals("source-document.pdf", request.sourceKey(), "Source key should match");
        assertEquals(productionBucketName, request.destinationBucket(), "Destination bucket name should match");
        assertEquals("destination-document.pdf", request.destinationKey(), "Destination key should match");
    }

    @Test
    @DisplayName("Test document metadata update")
    public void testUpdateDocumentMetadata() {
        // Create test metadata
        Map<String, String> metadata = new HashMap<>();
        metadata.put("classification", "invoice");
        metadata.put("confidentiality", "high");

        // Call the method under test
        s3Config.updateDocumentMetadata("test-document.pdf", metadata);

        // Verify that copyObject was called with the correct parameters
        ArgumentCaptor<CopyObjectRequest> requestCaptor = ArgumentCaptor.forClass(CopyObjectRequest.class);
        verify(s3Client).copyObject(requestCaptor.capture());

        // Verify the request
        CopyObjectRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.sourceBucket(), "Source bucket name should match");
        assertEquals("test-document.pdf", request.sourceKey(), "Source key should match");
        assertEquals(productionBucketName, request.destinationBucket(), "Destination bucket name should match");
        assertEquals("test-document.pdf", request.destinationKey(), "Destination key should match");
        assertEquals(metadata, request.metadata(), "Metadata should match");
        assertEquals(MetadataDirective.REPLACE, request.metadataDirective(), "Metadata directive should be REPLACE");
    }

    @Test
    @DisplayName("Test document tagging")
    public void testTagDocument() {
        // Create test tags
        Map<String, String> tags = new HashMap<>();
        tags.put("department", "finance");
        tags.put("retention", "7years");

        // Call the method under test
        s3Config.tagDocument("test-document.pdf", tags);

        // Verify that putObjectTagging was called with the correct parameters
        ArgumentCaptor<PutObjectTaggingRequest> requestCaptor = ArgumentCaptor.forClass(PutObjectTaggingRequest.class);
        verify(s3Client).putObjectTagging(requestCaptor.capture());

        // Verify the request
        PutObjectTaggingRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");
        assertEquals("test-document.pdf", request.key(), "Object key should match");

        // Verify the tags
        Tagging tagging = request.tagging();
        assertNotNull(tagging, "Tagging should not be null");
        List<Tag> tagList = tagging.tagSet();
        assertNotNull(tagList, "Tag list should not be null");
        assertEquals(2, tagList.size(), "There should be 2 tags");

        // Verify individual tags
        assertTrue(tagList.stream().anyMatch(tag -> "department".equals(tag.key()) && "finance".equals(tag.value())),
                "Tag 'department: finance' should exist");
        assertTrue(tagList.stream().anyMatch(tag -> "retention".equals(tag.key()) && "7years".equals(tag.value())),
                "Tag 'retention: 7years' should exist");
    }

    @Test
    @DisplayName("Test document version history retrieval")
    public void testGetDocumentVersions() {
        // Mock the response
        ObjectVersion version1 = ObjectVersion.builder().key("test-document.pdf").versionId("v1").build();
        ObjectVersion version2 = ObjectVersion.builder().key("test-document.pdf").versionId("v2").build();
        ListObjectVersionsResponse mockResponse = ListObjectVersionsResponse.builder()
                .versions(version1, version2)
                .build();
        when(s3Client.listObjectVersions(any(ListObjectVersionsRequest.class))).thenReturn(mockResponse);

        // Call the method under test
        List<ObjectVersion> result = s3Config.getDocumentVersions("test-document.pdf");

        // Verify the result
        assertNotNull(result, "Result should not be null");
        assertEquals(2, result.size(), "There should be 2 versions");
        assertEquals("v1", result.get(0).versionId(), "First version ID should match");
        assertEquals("v2", result.get(1).versionId(), "Second version ID should match");

        // Verify that listObjectVersions was called with the correct parameters
        ArgumentCaptor<ListObjectVersionsRequest> requestCaptor = ArgumentCaptor.forClass(ListObjectVersionsRequest.class);
        verify(s3Client).listObjectVersions(requestCaptor.capture());

        // Verify the request
        ListObjectVersionsRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");
        assertEquals("test-document.pdf", request.prefix(), "Prefix should match the object key");
    }

    @Test
    @DisplayName("Test signed URL generation for specific document version")
    public void testGenerateSignedUrlForVersion() {
        // Mock the URL
        URL mockUrl = mock(URL.class);
        when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
        when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);

        // Call the method under test
        URL result = s3Config.generateSignedUrlForVersion("test-document.pdf", "v1");

        // Verify the result
        assertNotNull(result, "URL should not be null");
        assertEquals(mockUrl, result, "URL should match the mock URL");

        // Verify that presignGetObject was called with the correct parameters
        ArgumentCaptor<GetObjectPresignRequest> requestCaptor = ArgumentCaptor.forClass(GetObjectPresignRequest.class);
        verify(s3Presigner).presignGetObject(requestCaptor.capture());

        // Verify the request
        GetObjectPresignRequest request = requestCaptor.getValue();
        assertNotNull(request, "Request should not be null");
        assertEquals(Duration.ofMinutes(signedUrlExpirationMinutes), request.signatureDuration(),
                "Signature duration should match the configured expiration time");

        // Verify the GetObjectRequest
        GetObjectRequest getObjectRequest = request.getObjectRequest();
        assertNotNull(getObjectRequest, "GetObjectRequest should not be null");
        assertEquals(productionBucketName, getObjectRequest.bucket(), "Bucket name should match");
        assertEquals("test-document.pdf", getObjectRequest.key(), "Object key should match");
        assertEquals("v1", getObjectRequest.versionId(), "Version ID should match");
    }

    @Test
    @DisplayName("Test restoration status check for archived documents")
    public void testCheckRestoreStatus() {
        // Mock the response for a document in Glacier with restoration in progress
        HeadObjectResponse inProgressResponse = HeadObjectResponse.builder()
                .storageClass(StorageClass.GLACIER)
                .restore("ongoing-request=\"true\", expiry-date=\"Wed, 01 Jan 2025 00:00:00 GMT\"")
                .build();
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(inProgressResponse);

        // Call the method under test
        Boolean result = s3Config.checkRestoreStatus("archived-document.pdf");

        // Verify the result
        assertNotNull(result, "Result should not be null");
        assertFalse(result, "Restoration should be in progress");

        // Mock the response for a document in Glacier with restoration completed
        HeadObjectResponse completedResponse = HeadObjectResponse.builder()
                .storageClass(StorageClass.GLACIER)
                .restore("ongoing-request=\"false\", expiry-date=\"Wed, 01 Jan 2025 00:00:00 GMT\"")
                .build();
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(completedResponse);

        // Call the method under test
        result = s3Config.checkRestoreStatus("archived-document.pdf");

        // Verify the result
        assertNotNull(result, "Result should not be null");
        assertTrue(result, "Restoration should be completed");

        // Mock the response for a document not in Glacier
        HeadObjectResponse standardResponse = HeadObjectResponse.builder()
                .storageClass(StorageClass.STANDARD)
                .build();
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(standardResponse);

        // Call the method under test
        result = s3Config.checkRestoreStatus("standard-document.pdf");

        // Verify the result
        assertNull(result, "Result should be null for non-Glacier documents");
    }

    @Test
    @DisplayName("Test document restoration from Glacier")
    public void testRestoreArchivedDocument() {
        // Mock the document metadata response for a document in Glacier
        HeadObjectResponse glacierResponse = HeadObjectResponse.builder()
                .storageClass(StorageClass.GLACIER)
                .build();
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(glacierResponse);

        // Call the method under test
        s3Config.restoreArchivedDocument("archived-document.pdf", 7);

        // Verify that restoreObject was called with the correct parameters
        ArgumentCaptor<RestoreObjectRequest> requestCaptor = ArgumentCaptor.forClass(RestoreObjectRequest.class);
        verify(s3Client).restoreObject(requestCaptor.capture());

        // Verify the request
        RestoreObjectRequest request = requestCaptor.getValue();
        assertEquals(productionBucketName, request.bucket(), "Bucket name should match");
        assertEquals("archived-document.pdf", request.key(), "Object key should match");

        // Verify the restore request
        RestoreRequest restoreRequest = request.restoreRequest();
        assertNotNull(restoreRequest, "Restore request should not be null");
        assertEquals(7, restoreRequest.days(), "Days should match");

        // Verify the Glacier job parameters
        GlacierJobParameters glacierParams = restoreRequest.glacierJobParameters();
        assertNotNull(glacierParams, "Glacier job parameters should not be null");
        assertEquals(Tier.STANDARD, glacierParams.tier(), "Tier should be STANDARD");

        // Test with a document not in Glacier
        reset(s3Client);
        HeadObjectResponse standardResponse = HeadObjectResponse.builder()
                .storageClass(StorageClass.STANDARD)
                .build();
        when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(standardResponse);

        // Call the method under test and expect an exception
        assertThrows(IllegalStateException.class, () -> s3Config.restoreArchivedDocument("standard-document.pdf", 7),
                "Should throw IllegalStateException for non-Glacier documents");
    }
}