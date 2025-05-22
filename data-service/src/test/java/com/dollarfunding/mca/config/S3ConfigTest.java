package com.dollarfunding.mca.config;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import java.net.URL;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

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

/**
 * Unit tests for the {@link S3Config} class that configures S3-compatible storage for document management.
 * 
 * These tests verify:
 * 1. S3 client configuration with AES-256 encryption
 * 2. Bucket access policy setup for authorized services
 * 3. Signed URL generation with short expiration times
 * 4. Versioning configuration for document history tracking
 * 5. Lifecycle rule configuration for compliant document retention
 */
@ExtendWith(MockitoExtension.class)
public class S3ConfigTest {

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
    
    private S3Config s3Config;
    
    // Test constants
    private static final String TEST_REGION = "us-east-1";
    private static final String TEST_PRODUCTION_BUCKET = "mca-documents-production";
    private static final String TEST_STAGING_BUCKET = "mca-documents-staging";
    private static final String TEST_ACTIVE_PROFILE = "production";
    private static final int TEST_URL_EXPIRATION = 15;
    private static final String TEST_OBJECT_KEY = "documents/application123/bank-statement.pdf";
    private static final String TEST_CONTENT_TYPE = "application/pdf";
    
    @BeforeEach
    void setUp() {
        // Create a new S3Config instance for each test
        s3Config = new S3Config();
        
        // Set the required properties using reflection
        ReflectionTestUtils.setField(s3Config, "region", TEST_REGION);
        ReflectionTestUtils.setField(s3Config, "productionBucketName", TEST_PRODUCTION_BUCKET);
        ReflectionTestUtils.setField(s3Config, "stagingBucketName", TEST_STAGING_BUCKET);
        ReflectionTestUtils.setField(s3Config, "activeProfile", TEST_ACTIVE_PROFILE);
        ReflectionTestUtils.setField(s3Config, "signedUrlExpirationMinutes", TEST_URL_EXPIRATION);
        ReflectionTestUtils.setField(s3Config, "bucketName", TEST_PRODUCTION_BUCKET);
        
        // Mock the s3Client method to return our mock
        ReflectionTestUtils.setField(s3Config, "s3Client", s3Client);
        
        // Mock the s3Presigner method to return our mock
        ReflectionTestUtils.setField(s3Config, "s3Presigner", s3Presigner);
    }
    
    @Nested
    @DisplayName("S3 Client Configuration Tests")
    class S3ClientConfigurationTests {
        
        @Mock
        private SdkHttpClient httpClient;
        
        @Test
        @DisplayName("Should configure S3 client with correct region and credentials")
        void shouldConfigureS3ClientWithCorrectRegionAndCredentials() {
            // Given
            S3Config spyConfig = spy(s3Config);
            when(spyConfig.s3Client()).thenCallRealMethod();
            
            // Create a mock ApacheHttpClient.Builder
            ApacheHttpClient.Builder httpClientBuilder = mock(ApacheHttpClient.Builder.class);
            when(httpClientBuilder.connectionTimeout(any(Duration.class))).thenReturn(httpClientBuilder);
            when(httpClientBuilder.socketTimeout(any(Duration.class))).thenReturn(httpClientBuilder);
            when(httpClientBuilder.build()).thenReturn(httpClient);
            
            // Use mockStatic for ApacheHttpClient
            try (var mockedApacheHttpClient = mockStatic(ApacheHttpClient.class)) {
                mockedApacheHttpClient.when(ApacheHttpClient::builder).thenReturn(httpClientBuilder);
                
                // Use mockStatic for S3Client
                try (var mockedS3Client = mockStatic(S3Client.class)) {
                    mockedS3Client.when(S3Client::builder).thenReturn(s3ClientBuilder);
                    when(s3ClientBuilder.region(any(Region.class))).thenReturn(s3ClientBuilder);
                    when(s3ClientBuilder.credentialsProvider(any())).thenReturn(s3ClientBuilder);
                    when(s3ClientBuilder.httpClient(httpClient)).thenReturn(s3ClientBuilder);
                    when(s3ClientBuilder.build()).thenReturn(s3Client);
                    
                    // When
                    S3Client result = spyConfig.s3Client();
                    
                    // Then
                    assertNotNull(result, "S3Client should not be null");
                    verify(httpClientBuilder).connectionTimeout(Duration.ofSeconds(30));
                    verify(httpClientBuilder).socketTimeout(Duration.ofSeconds(30));
                    verify(s3ClientBuilder).region(Region.of(TEST_REGION));
                    verify(s3ClientBuilder).credentialsProvider(any());
                    verify(s3ClientBuilder).httpClient(httpClient);
                    verify(s3ClientBuilder).build();
                }
            }
        }
        
        @Test
        @DisplayName("Should configure S3 presigner with correct region and credentials")
        void shouldConfigureS3PresignerWithCorrectRegionAndCredentials() {
            // Given
            S3Config spyConfig = spy(s3Config);
            when(spyConfig.s3Presigner()).thenCallRealMethod();
            
            // Use mockStatic for S3Presigner
            try (var mockedS3Presigner = mockStatic(S3Presigner.class)) {
                S3Presigner.Builder presignerBuilder = mock(S3Presigner.Builder.class);
                mockedS3Presigner.when(S3Presigner::builder).thenReturn(presignerBuilder);
                
                when(presignerBuilder.region(any(Region.class))).thenReturn(presignerBuilder);
                when(presignerBuilder.credentialsProvider(any())).thenReturn(presignerBuilder);
                when(presignerBuilder.build()).thenReturn(s3Presigner);
                
                // When
                S3Presigner result = spyConfig.s3Presigner();
                
                // Then
                assertNotNull(result, "S3Presigner should not be null");
                verify(presignerBuilder).region(Region.of(TEST_REGION));
                verify(presignerBuilder).credentialsProvider(any());
                verify(presignerBuilder).build();
            }
        }
    }
    
    @Nested
    @DisplayName("Bucket Configuration Tests")
    class BucketConfigurationTests {
        
        @Test
        @DisplayName("Should initialize bucket name based on active profile")
        void shouldInitializeBucketNameBasedOnActiveProfile() {
            // Given
            S3Config testConfig = new S3Config();
            ReflectionTestUtils.setField(testConfig, "productionBucketName", TEST_PRODUCTION_BUCKET);
            ReflectionTestUtils.setField(testConfig, "stagingBucketName", TEST_STAGING_BUCKET);
            
            // When - production profile
            ReflectionTestUtils.setField(testConfig, "activeProfile", "production");
            testConfig.init();
            
            // Then
            assertEquals(TEST_PRODUCTION_BUCKET, testConfig.getBucketName(), 
                    "Should use production bucket for production profile");
            
            // When - staging profile
            ReflectionTestUtils.setField(testConfig, "activeProfile", "staging");
            testConfig.init();
            
            // Then
            assertEquals(TEST_STAGING_BUCKET, testConfig.getBucketName(), 
                    "Should use staging bucket for staging profile");
        }
        
        @Test
        @DisplayName("Should create bucket if it doesn't exist")
        void shouldCreateBucketIfItDoesntExist() {
            // Given
            S3Config spyConfig = spy(s3Config);
            doReturn(s3Client).when(spyConfig).s3Client();
            
            // Mock bucket doesn't exist
            doReturn(false).when(spyConfig).bucketExists(s3Client, TEST_PRODUCTION_BUCKET);
            
            // When
            spyConfig.configureBucket();
            
            // Then
            verify(s3Client).createBucket(any(CreateBucketRequest.class));
        }
        
        @Test
        @DisplayName("Should not create bucket if it already exists")
        void shouldNotCreateBucketIfItAlreadyExists() {
            // Given
            S3Config spyConfig = spy(s3Config);
            doReturn(s3Client).when(spyConfig).s3Client();
            
            // Mock bucket exists
            doReturn(true).when(spyConfig).bucketExists(s3Client, TEST_PRODUCTION_BUCKET);
            
            // When
            spyConfig.configureBucket();
            
            // Then
            verify(s3Client, never()).createBucket(any(CreateBucketRequest.class));
        }
        
        @Test
        @DisplayName("Should configure default encryption with AES-256")
        void shouldConfigureDefaultEncryptionWithAes256() {
            // Given
            S3Config spyConfig = spy(s3Config);
            doReturn(s3Client).when(spyConfig).s3Client();
            doReturn(true).when(spyConfig).bucketExists(s3Client, TEST_PRODUCTION_BUCKET);
            
            // When
            spyConfig.configureBucket();
            
            // Then
            ArgumentCaptor<PutBucketEncryptionRequest> encryptionCaptor = 
                    ArgumentCaptor.forClass(PutBucketEncryptionRequest.class);
            verify(s3Client).putBucketEncryption(encryptionCaptor.capture());
            
            PutBucketEncryptionRequest encryptionRequest = encryptionCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, encryptionRequest.bucket(), 
                    "Bucket name should match");
            
            ServerSideEncryptionConfiguration encryptionConfig = encryptionRequest.serverSideEncryptionConfiguration();
            assertNotNull(encryptionConfig, "Encryption configuration should not be null");
            
            List<ServerSideEncryptionRule> rules = encryptionConfig.rules();
            assertNotNull(rules, "Encryption rules should not be null");
            assertFalse(rules.isEmpty(), "Encryption rules should not be empty");
            
            ServerSideEncryptionByDefault encryptionByDefault = rules.get(0).applyServerSideEncryptionByDefault();
            assertNotNull(encryptionByDefault, "Default encryption should not be null");
            assertEquals(ServerSideEncryption.AES256, encryptionByDefault.sseAlgorithm(), 
                    "Encryption algorithm should be AES256");
        }
        
        @Test
        @DisplayName("Should enable versioning for document history tracking")
        void shouldEnableVersioningForDocumentHistoryTracking() {
            // Given
            S3Config spyConfig = spy(s3Config);
            doReturn(s3Client).when(spyConfig).s3Client();
            doReturn(true).when(spyConfig).bucketExists(s3Client, TEST_PRODUCTION_BUCKET);
            
            // When
            spyConfig.configureBucket();
            
            // Then
            ArgumentCaptor<PutBucketVersioningRequest> versioningCaptor = 
                    ArgumentCaptor.forClass(PutBucketVersioningRequest.class);
            verify(s3Client).putBucketVersioning(versioningCaptor.capture());
            
            PutBucketVersioningRequest versioningRequest = versioningCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, versioningRequest.bucket(), 
                    "Bucket name should match");
            
            VersioningConfiguration versioningConfig = versioningRequest.versioningConfiguration();
            assertNotNull(versioningConfig, "Versioning configuration should not be null");
            assertEquals(BucketVersioningStatus.ENABLED, versioningConfig.status(), 
                    "Versioning should be enabled");
        }
        
        @Test
        @DisplayName("Should configure lifecycle rules for document retention")
        void shouldConfigureLifecycleRulesForDocumentRetention() {
            // Given
            S3Config spyConfig = spy(s3Config);
            doReturn(s3Client).when(spyConfig).s3Client();
            doReturn(true).when(spyConfig).bucketExists(s3Client, TEST_PRODUCTION_BUCKET);
            
            // When
            spyConfig.configureBucket();
            
            // Then
            ArgumentCaptor<PutBucketLifecycleConfigurationRequest> lifecycleCaptor = 
                    ArgumentCaptor.forClass(PutBucketLifecycleConfigurationRequest.class);
            verify(s3Client).putBucketLifecycleConfiguration(lifecycleCaptor.capture());
            
            PutBucketLifecycleConfigurationRequest lifecycleRequest = lifecycleCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, lifecycleRequest.bucket(), 
                    "Bucket name should match");
            
            BucketLifecycleConfiguration lifecycleConfig = lifecycleRequest.lifecycleConfiguration();
            assertNotNull(lifecycleConfig, "Lifecycle configuration should not be null");
            
            List<LifecycleRule> rules = lifecycleConfig.rules();
            assertNotNull(rules, "Lifecycle rules should not be null");
            assertEquals(3, rules.size(), "Should have 3 lifecycle rules");
            
            // Verify transition rule
            LifecycleRule transitionRule = rules.stream()
                    .filter(r -> "TransitionToGlacierRule".equals(r.id()))
                    .findFirst()
                    .orElse(null);
            assertNotNull(transitionRule, "Transition rule should exist");
            assertEquals(ExpirationStatus.ENABLED, transitionRule.status(), 
                    "Transition rule should be enabled");
            assertNotNull(transitionRule.noncurrentVersionTransitions(), 
                    "Noncurrent version transitions should not be null");
            assertEquals(30, transitionRule.noncurrentVersionTransitions().get(0).noncurrentDays(), 
                    "Transition should occur after 30 days");
            assertEquals(StorageClass.GLACIER, transitionRule.noncurrentVersionTransitions().get(0).storageClass(), 
                    "Transition should be to Glacier storage class");
            
            // Verify expiration rule
            LifecycleRule expirationRule = rules.stream()
                    .filter(r -> "ExpireNoncurrentVersionsRule".equals(r.id()))
                    .findFirst()
                    .orElse(null);
            assertNotNull(expirationRule, "Expiration rule should exist");
            assertEquals(ExpirationStatus.ENABLED, expirationRule.status(), 
                    "Expiration rule should be enabled");
            assertNotNull(expirationRule.noncurrentVersionExpiration(), 
                    "Noncurrent version expiration should not be null");
            assertEquals(2555, expirationRule.noncurrentVersionExpiration().noncurrentDays(), 
                    "Expiration should occur after 2555 days (7 years)");
            
            // Verify delete markers rule
            LifecycleRule deleteMarkersRule = rules.stream()
                    .filter(r -> "DeleteExpiredMarkersRule".equals(r.id()))
                    .findFirst()
                    .orElse(null);
            assertNotNull(deleteMarkersRule, "Delete markers rule should exist");
            assertEquals(ExpirationStatus.ENABLED, deleteMarkersRule.status(), 
                    "Delete markers rule should be enabled");
            assertTrue(deleteMarkersRule.expiration().expiredObjectDeleteMarker(), 
                    "Expired object delete marker should be true");
        }
        
        @Test
        @DisplayName("Should set bucket policy to restrict access to authorized services")
        void shouldSetBucketPolicyToRestrictAccessToAuthorizedServices() {
            // Given
            S3Config spyConfig = spy(s3Config);
            doReturn(s3Client).when(spyConfig).s3Client();
            doReturn(true).when(spyConfig).bucketExists(s3Client, TEST_PRODUCTION_BUCKET);
            
            // When
            spyConfig.configureBucket();
            
            // Then
            ArgumentCaptor<PutBucketPolicyRequest> policyCaptor = 
                    ArgumentCaptor.forClass(PutBucketPolicyRequest.class);
            verify(s3Client).putBucketPolicy(policyCaptor.capture());
            
            PutBucketPolicyRequest policyRequest = policyCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, policyRequest.bucket(), 
                    "Bucket name should match");
            
            String policy = policyRequest.policy();
            assertNotNull(policy, "Policy should not be null");
            assertTrue(policy.contains("DenyPublicReadAccess"), 
                    "Policy should deny public read access");
            assertTrue(policy.contains("EnforceEncryptedTransport"), 
                    "Policy should enforce encrypted transport");
            assertTrue(policy.contains("MCAServiceRole"), 
                    "Policy should allow access to MCA service role");
            assertTrue(policy.contains("MCAAdminRole"), 
                    "Policy should allow access to MCA admin role");
        }
    }
    
    @Nested
    @DisplayName("Signed URL Generation Tests")
    class SignedUrlGenerationTests {
        
        @Test
        @DisplayName("Should generate signed URL with correct expiration time")
        void shouldGenerateSignedUrlWithCorrectExpirationTime() throws Exception {
            // Given
            URL mockUrl = new URL("https://mca-documents-production.s3.amazonaws.com/" + TEST_OBJECT_KEY);
            when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
            when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);
            
            // When
            URL signedUrl = s3Config.generateSignedUrl(TEST_OBJECT_KEY);
            
            // Then
            assertNotNull(signedUrl, "Signed URL should not be null");
            assertEquals(mockUrl, signedUrl, "Signed URL should match mock URL");
            
            // Verify presign request
            ArgumentCaptor<GetObjectPresignRequest> presignCaptor = 
                    ArgumentCaptor.forClass(GetObjectPresignRequest.class);
            verify(s3Presigner).presignGetObject(presignCaptor.capture());
            
            GetObjectPresignRequest presignRequest = presignCaptor.getValue();
            assertEquals(Duration.ofMinutes(TEST_URL_EXPIRATION), presignRequest.signatureDuration(), 
                    "Signature duration should match configured expiration time");
            
            // Verify get object request
            GetObjectRequest getObjectRequest = presignRequest.getObjectRequest();
            assertEquals(TEST_PRODUCTION_BUCKET, getObjectRequest.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, getObjectRequest.key(), 
                    "Object key should match");
        }
        
        @Test
        @DisplayName("Should generate signed upload URL with correct content type")
        void shouldGenerateSignedUploadUrlWithCorrectContentType() throws Exception {
            // Given
            URL mockUrl = new URL("https://mca-documents-production.s3.amazonaws.com/" + TEST_OBJECT_KEY);
            when(presignedPutObjectRequest.url()).thenReturn(mockUrl);
            when(s3Presigner.presignPutObject(any(PutObjectPresignRequest.class))).thenReturn(presignedPutObjectRequest);
            
            // When
            URL signedUrl = s3Config.generateSignedUploadUrl(TEST_OBJECT_KEY, TEST_CONTENT_TYPE, null);
            
            // Then
            assertNotNull(signedUrl, "Signed upload URL should not be null");
            assertEquals(mockUrl, signedUrl, "Signed upload URL should match mock URL");
            
            // Verify presign request
            ArgumentCaptor<PutObjectPresignRequest> presignCaptor = 
                    ArgumentCaptor.forClass(PutObjectPresignRequest.class);
            verify(s3Presigner).presignPutObject(presignCaptor.capture());
            
            PutObjectPresignRequest presignRequest = presignCaptor.getValue();
            assertEquals(Duration.ofMinutes(TEST_URL_EXPIRATION), presignRequest.signatureDuration(), 
                    "Signature duration should match configured expiration time");
            
            // Verify put object request
            PutObjectRequest putObjectRequest = presignRequest.putObjectRequest();
            assertEquals(TEST_PRODUCTION_BUCKET, putObjectRequest.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, putObjectRequest.key(), 
                    "Object key should match");
            assertEquals(TEST_CONTENT_TYPE, putObjectRequest.contentType(), 
                    "Content type should match");
        }
        
        @Test
        @DisplayName("Should generate signed upload URL with custom expiration time")
        void shouldGenerateSignedUploadUrlWithCustomExpirationTime() throws Exception {
            // Given
            URL mockUrl = new URL("https://mca-documents-production.s3.amazonaws.com/" + TEST_OBJECT_KEY);
            when(presignedPutObjectRequest.url()).thenReturn(mockUrl);
            when(s3Presigner.presignPutObject(any(PutObjectPresignRequest.class))).thenReturn(presignedPutObjectRequest);
            
            int customExpiration = 5; // 5 minutes
            
            // When
            URL signedUrl = s3Config.generateSignedUploadUrl(TEST_OBJECT_KEY, TEST_CONTENT_TYPE, customExpiration);
            
            // Then
            assertNotNull(signedUrl, "Signed upload URL should not be null");
            
            // Verify presign request
            ArgumentCaptor<PutObjectPresignRequest> presignCaptor = 
                    ArgumentCaptor.forClass(PutObjectPresignRequest.class);
            verify(s3Presigner).presignPutObject(presignCaptor.capture());
            
            PutObjectPresignRequest presignRequest = presignCaptor.getValue();
            assertEquals(Duration.ofMinutes(customExpiration), presignRequest.signatureDuration(), 
                    "Signature duration should match custom expiration time");
        }
        
        @Test
        @DisplayName("Should generate signed URL for specific document version")
        void shouldGenerateSignedUrlForSpecificDocumentVersion() throws Exception {
            // Given
            URL mockUrl = new URL("https://mca-documents-production.s3.amazonaws.com/" + TEST_OBJECT_KEY);
            when(presignedGetObjectRequest.url()).thenReturn(mockUrl);
            when(s3Presigner.presignGetObject(any(GetObjectPresignRequest.class))).thenReturn(presignedGetObjectRequest);
            
            String versionId = "v1234567890";
            
            // When
            URL signedUrl = s3Config.generateSignedUrlForVersion(TEST_OBJECT_KEY, versionId);
            
            // Then
            assertNotNull(signedUrl, "Signed URL should not be null");
            
            // Verify presign request
            ArgumentCaptor<GetObjectPresignRequest> presignCaptor = 
                    ArgumentCaptor.forClass(GetObjectPresignRequest.class);
            verify(s3Presigner).presignGetObject(presignCaptor.capture());
            
            GetObjectPresignRequest presignRequest = presignCaptor.getValue();
            
            // Verify get object request
            GetObjectRequest getObjectRequest = presignRequest.getObjectRequest();
            assertEquals(TEST_PRODUCTION_BUCKET, getObjectRequest.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, getObjectRequest.key(), 
                    "Object key should match");
            assertEquals(versionId, getObjectRequest.versionId(), 
                    "Version ID should match");
        }
    }
    
    @Nested
    @DisplayName("Document Management Tests")
    class DocumentManagementTests {
        
        @Test
        @DisplayName("Should retrieve document metadata")
        void shouldRetrieveDocumentMetadata() {
            // Given
            HeadObjectResponse mockResponse = HeadObjectResponse.builder().build();
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(mockResponse);
            
            // When
            HeadObjectResponse metadata = s3Config.getDocumentMetadata(TEST_OBJECT_KEY);
            
            // Then
            assertNotNull(metadata, "Document metadata should not be null");
            
            // Verify head object request
            ArgumentCaptor<HeadObjectRequest> requestCaptor = 
                    ArgumentCaptor.forClass(HeadObjectRequest.class);
            verify(s3Client).headObject(requestCaptor.capture());
            
            HeadObjectRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.key(), 
                    "Object key should match");
        }
        
        @Test
        @DisplayName("Should check if document exists")
        void shouldCheckIfDocumentExists() {
            // Given
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(HeadObjectResponse.builder().build());
            
            // When
            boolean exists = s3Config.documentExists(TEST_OBJECT_KEY);
            
            // Then
            assertTrue(exists, "Document should exist");
            
            // Verify head object request
            ArgumentCaptor<HeadObjectRequest> requestCaptor = 
                    ArgumentCaptor.forClass(HeadObjectRequest.class);
            verify(s3Client).headObject(requestCaptor.capture());
            
            HeadObjectRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.key(), 
                    "Object key should match");
        }
        
        @Test
        @DisplayName("Should return false when document does not exist")
        void shouldReturnFalseWhenDocumentDoesNotExist() {
            // Given
            S3Exception notFoundException = S3Exception.builder().statusCode(404).build();
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenThrow(notFoundException);
            
            // When
            boolean exists = s3Config.documentExists(TEST_OBJECT_KEY);
            
            // Then
            assertFalse(exists, "Document should not exist");
        }
        
        @Test
        @DisplayName("Should delete document")
        void shouldDeleteDocument() {
            // Given
            when(s3Client.deleteObject(any(DeleteObjectRequest.class))).thenReturn(DeleteObjectResponse.builder().build());
            
            // When
            boolean deleted = s3Config.deleteDocument(TEST_OBJECT_KEY);
            
            // Then
            assertTrue(deleted, "Document should be deleted");
            
            // Verify delete object request
            ArgumentCaptor<DeleteObjectRequest> requestCaptor = 
                    ArgumentCaptor.forClass(DeleteObjectRequest.class);
            verify(s3Client).deleteObject(requestCaptor.capture());
            
            DeleteObjectRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.key(), 
                    "Object key should match");
        }
        
        @Test
        @DisplayName("Should copy document to new location")
        void shouldCopyDocumentToNewLocation() {
            // Given
            when(s3Client.copyObject(any(CopyObjectRequest.class))).thenReturn(CopyObjectResponse.builder().build());
            
            String destinationKey = "documents/application123/archived/bank-statement.pdf";
            
            // When
            boolean copied = s3Config.copyDocument(TEST_OBJECT_KEY, destinationKey);
            
            // Then
            assertTrue(copied, "Document should be copied");
            
            // Verify copy object request
            ArgumentCaptor<CopyObjectRequest> requestCaptor = 
                    ArgumentCaptor.forClass(CopyObjectRequest.class);
            verify(s3Client).copyObject(requestCaptor.capture());
            
            CopyObjectRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.sourceBucket(), 
                    "Source bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.sourceKey(), 
                    "Source object key should match");
            assertEquals(TEST_PRODUCTION_BUCKET, request.destinationBucket(), 
                    "Destination bucket name should match");
            assertEquals(destinationKey, request.destinationKey(), 
                    "Destination object key should match");
        }
        
        @Test
        @DisplayName("Should update document metadata")
        void shouldUpdateDocumentMetadata() {
            // Given
            when(s3Client.copyObject(any(CopyObjectRequest.class))).thenReturn(CopyObjectResponse.builder().build());
            
            Map<String, String> metadata = new HashMap<>();
            metadata.put("classification", "bank-statement");
            metadata.put("confidence", "0.95");
            
            // When
            s3Config.updateDocumentMetadata(TEST_OBJECT_KEY, metadata);
            
            // Then
            // Verify copy object request
            ArgumentCaptor<CopyObjectRequest> requestCaptor = 
                    ArgumentCaptor.forClass(CopyObjectRequest.class);
            verify(s3Client).copyObject(requestCaptor.capture());
            
            CopyObjectRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.sourceBucket(), 
                    "Source bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.sourceKey(), 
                    "Source object key should match");
            assertEquals(TEST_PRODUCTION_BUCKET, request.destinationBucket(), 
                    "Destination bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.destinationKey(), 
                    "Destination object key should match");
            assertEquals(metadata, request.metadata(), 
                    "Metadata should match");
            assertEquals(MetadataDirective.REPLACE, request.metadataDirective(), 
                    "Metadata directive should be REPLACE");
        }
        
        @Test
        @DisplayName("Should tag document for categorization")
        void shouldTagDocumentForCategorization() {
            // Given
            when(s3Client.putObjectTagging(any(PutObjectTaggingRequest.class)))
                    .thenReturn(PutObjectTaggingResponse.builder().build());
            
            Map<String, String> tags = new HashMap<>();
            tags.put("category", "financial");
            tags.put("retention", "7years");
            
            // When
            s3Config.tagDocument(TEST_OBJECT_KEY, tags);
            
            // Then
            // Verify put object tagging request
            ArgumentCaptor<PutObjectTaggingRequest> requestCaptor = 
                    ArgumentCaptor.forClass(PutObjectTaggingRequest.class);
            verify(s3Client).putObjectTagging(requestCaptor.capture());
            
            PutObjectTaggingRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.key(), 
                    "Object key should match");
            
            Tagging tagging = request.tagging();
            assertNotNull(tagging, "Tagging should not be null");
            
            List<Tag> tagList = tagging.tagSet();
            assertNotNull(tagList, "Tag list should not be null");
            assertEquals(2, tagList.size(), "Should have 2 tags");
            
            // Verify tag values
            assertTrue(tagList.stream().anyMatch(tag -> 
                    "category".equals(tag.key()) && "financial".equals(tag.value())), 
                    "Should have category tag with value financial");
            
            assertTrue(tagList.stream().anyMatch(tag -> 
                    "retention".equals(tag.key()) && "7years".equals(tag.value())), 
                    "Should have retention tag with value 7years");
        }
        
        @Test
        @DisplayName("Should retrieve document versions")
        void shouldRetrieveDocumentVersions() {
            // Given
            ObjectVersion version1 = ObjectVersion.builder()
                    .key(TEST_OBJECT_KEY)
                    .versionId("v1")
                    .lastModified(java.time.Instant.now())
                    .build();
            
            ObjectVersion version2 = ObjectVersion.builder()
                    .key(TEST_OBJECT_KEY)
                    .versionId("v2")
                    .lastModified(java.time.Instant.now().minusSeconds(3600))
                    .build();
            
            ListObjectVersionsResponse mockResponse = ListObjectVersionsResponse.builder()
                    .versions(version1, version2)
                    .build();
            
            when(s3Client.listObjectVersions(any(ListObjectVersionsRequest.class))).thenReturn(mockResponse);
            
            // When
            List<ObjectVersion> versions = s3Config.getDocumentVersions(TEST_OBJECT_KEY);
            
            // Then
            assertNotNull(versions, "Document versions should not be null");
            assertEquals(2, versions.size(), "Should have 2 versions");
            
            // Verify list object versions request
            ArgumentCaptor<ListObjectVersionsRequest> requestCaptor = 
                    ArgumentCaptor.forClass(ListObjectVersionsRequest.class);
            verify(s3Client).listObjectVersions(requestCaptor.capture());
            
            ListObjectVersionsRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.prefix(), 
                    "Object key prefix should match");
        }
        
        @Test
        @DisplayName("Should check restoration status of archived document")
        void shouldCheckRestorationStatusOfArchivedDocument() {
            // Given - document in Glacier with restoration in progress
            HeadObjectResponse inProgressResponse = HeadObjectResponse.builder()
                    .storageClass(StorageClass.GLACIER)
                    .restore("ongoing-request=\"true\", expiry-date=\"Wed, 01 Jan 2025 00:00:00 GMT\"")
                    .build();
            
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(inProgressResponse);
            
            // When
            Boolean inProgressStatus = s3Config.checkRestoreStatus(TEST_OBJECT_KEY);
            
            // Then
            assertNotNull(inProgressStatus, "Restoration status should not be null");
            assertFalse(inProgressStatus, "Restoration should be in progress");
            
            // Given - document in Glacier with restoration complete
            HeadObjectResponse completeResponse = HeadObjectResponse.builder()
                    .storageClass(StorageClass.GLACIER)
                    .restore("ongoing-request=\"false\", expiry-date=\"Wed, 01 Jan 2025 00:00:00 GMT\"")
                    .build();
            
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(completeResponse);
            
            // When
            Boolean completeStatus = s3Config.checkRestoreStatus(TEST_OBJECT_KEY);
            
            // Then
            assertNotNull(completeStatus, "Restoration status should not be null");
            assertTrue(completeStatus, "Restoration should be complete");
            
            // Given - document not in Glacier
            HeadObjectResponse standardResponse = HeadObjectResponse.builder()
                    .storageClass(StorageClass.STANDARD)
                    .build();
            
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(standardResponse);
            
            // When
            Boolean standardStatus = s3Config.checkRestoreStatus(TEST_OBJECT_KEY);
            
            // Then
            assertNull(standardStatus, "Restoration status should be null for standard storage");
        }
        
        @Test
        @DisplayName("Should initiate restoration of archived document")
        void shouldInitiateRestorationOfArchivedDocument() {
            // Given
            HeadObjectResponse glacierResponse = HeadObjectResponse.builder()
                    .storageClass(StorageClass.GLACIER)
                    .build();
            
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(glacierResponse);
            when(s3Client.restoreObject(any(RestoreObjectRequest.class))).thenReturn(RestoreObjectResponse.builder().build());
            
            int expirationDays = 7;
            
            // When
            s3Config.restoreArchivedDocument(TEST_OBJECT_KEY, expirationDays);
            
            // Then
            // Verify restore object request
            ArgumentCaptor<RestoreObjectRequest> requestCaptor = 
                    ArgumentCaptor.forClass(RestoreObjectRequest.class);
            verify(s3Client).restoreObject(requestCaptor.capture());
            
            RestoreObjectRequest request = requestCaptor.getValue();
            assertEquals(TEST_PRODUCTION_BUCKET, request.bucket(), 
                    "Bucket name should match");
            assertEquals(TEST_OBJECT_KEY, request.key(), 
                    "Object key should match");
            
            RestoreRequest restoreRequest = request.restoreRequest();
            assertNotNull(restoreRequest, "Restore request should not be null");
            assertEquals(expirationDays, restoreRequest.days(), 
                    "Expiration days should match");
            
            GlacierJobParameters glacierParams = restoreRequest.glacierJobParameters();
            assertNotNull(glacierParams, "Glacier job parameters should not be null");
            assertEquals(Tier.STANDARD, glacierParams.tier(), 
                    "Tier should be STANDARD");
        }
        
        @Test
        @DisplayName("Should throw exception when trying to restore non-archived document")
        void shouldThrowExceptionWhenTryingToRestoreNonArchivedDocument() {
            // Given
            HeadObjectResponse standardResponse = HeadObjectResponse.builder()
                    .storageClass(StorageClass.STANDARD)
                    .build();
            
            when(s3Client.headObject(any(HeadObjectRequest.class))).thenReturn(standardResponse);
            
            // When & Then
            Exception exception = assertThrows(IllegalStateException.class, () -> {
                s3Config.restoreArchivedDocument(TEST_OBJECT_KEY, 7);
            }, "Should throw IllegalStateException for non-archived document");
            
            assertTrue(exception.getMessage().contains("Document is not archived in Glacier"), 
                    "Exception message should indicate document is not archived");
        }
    }
}