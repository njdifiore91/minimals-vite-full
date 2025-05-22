package com.dollarfunding.mca.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration;
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
import javax.annotation.PostConstruct;
import java.util.List;
import java.util.Map;

/**
 * S3 Configuration for the MCA application.
 * 
 * Configures S3-compatible storage for document management with the following features:
 * - AES-256 encryption for all stored objects
 * - Signed URLs with short expiration times for secure document access
 * - Versioning enabled for document history tracking
 * - Bucket policies restricting access to authorized services only
 * - Lifecycle rules for compliant document retention
 */
@Configuration
public class S3Config {

    @Value("${aws.s3.region}")
    private String region;

    @Value("${aws.s3.bucket.production}")
    private String productionBucketName;

    @Value("${aws.s3.bucket.staging}")
    private String stagingBucketName;

    @Value("${spring.profiles.active:production}")
    private String activeProfile;

    @Value("${aws.s3.url.expiration:15}")
    private int signedUrlExpirationMinutes;

    private String bucketName;

    @PostConstruct
    public void init() {
        // Determine which bucket to use based on active profile
        bucketName = "production".equals(activeProfile) ? productionBucketName : stagingBucketName;
        
        // Ensure bucket exists and is properly configured
        configureBucket();
    }

    /**
     * Creates an S3 client with proper configuration.
     * 
     * @return Configured S3Client instance
     */
    @Bean
    public S3Client s3Client() {
        // Configure HTTP client with appropriate timeouts
        SdkHttpClient httpClient = ApacheHttpClient.builder()
                .connectionTimeout(Duration.ofSeconds(30))
                .socketTimeout(Duration.ofSeconds(30))
                .build();

        // Configure S3 client with region and credentials
        S3ClientBuilder builder = S3Client.builder()
                .region(Region.of(region))
                .credentialsProvider(DefaultCredentialsProvider.create())
                .httpClient(httpClient);

        return builder.build();
    }

    /**
     * Creates an S3 presigner for generating signed URLs.
     * 
     * @return Configured S3Presigner instance
     */
    @Bean
    public S3Presigner s3Presigner() {
        return S3Presigner.builder()
                .region(Region.of(region))
                .credentialsProvider(DefaultCredentialsProvider.create())
                .build();
    }

    /**
     * Configures the S3 bucket with appropriate settings.
     * - Ensures bucket exists
     * - Configures server-side encryption with AES-256
     * - Enables versioning for document history tracking
     * - Sets up lifecycle rules for document retention
     */
    private void configureBucket() {
        S3Client client = s3Client();

        try {
            // Check if bucket exists, create if it doesn't
            if (!bucketExists(client, bucketName)) {
                createBucket(client, bucketName);
            }

            // Configure default encryption (AES-256)
            setDefaultEncryption(client, bucketName);

            // Enable versioning
            enableVersioning(client, bucketName);

            // Configure lifecycle rules
            setLifecycleRules(client, bucketName);
            
            // Set bucket policy to restrict access
            setBucketPolicy(client, bucketName);

        } catch (S3Exception e) {
            throw new RuntimeException("Failed to configure S3 bucket: " + e.getMessage(), e);
        }
    }

    /**
     * Checks if the specified bucket exists.
     * 
     * @param client S3 client
     * @param bucketName Name of the bucket to check
     * @return true if bucket exists, false otherwise
     */
    private boolean bucketExists(S3Client client, String bucketName) {
        try {
            client.headBucket(HeadBucketRequest.builder().bucket(bucketName).build());
            return true;
        } catch (S3Exception e) {
            if (e.statusCode() == 404) {
                return false;
            }
            throw e;
        }
    }

    /**
     * Creates a new S3 bucket.
     * 
     * @param client S3 client
     * @param bucketName Name of the bucket to create
     */
    private void createBucket(S3Client client, String bucketName) {
        client.createBucket(CreateBucketRequest.builder()
                .bucket(bucketName)
                .build());
    }

    /**
     * Configures default encryption for the bucket using AES-256.
     * 
     * @param client S3 client
     * @param bucketName Name of the bucket to configure
     */
    private void setDefaultEncryption(S3Client client, String bucketName) {
        ServerSideEncryptionConfiguration encryptionConfig = ServerSideEncryptionConfiguration.builder()
                .rules(ServerSideEncryptionRule.builder()
                        .applyServerSideEncryptionByDefault(ServerSideEncryptionByDefault.builder()
                                .sseAlgorithm(ServerSideEncryption.AES256)
                                .build())
                        .build())
                .build();

        client.putBucketEncryption(PutBucketEncryptionRequest.builder()
                .bucket(bucketName)
                .serverSideEncryptionConfiguration(encryptionConfig)
                .build());
    }

    /**
     * Enables versioning for the bucket to track document history.
     * 
     * @param client S3 client
     * @param bucketName Name of the bucket to configure
     */
    private void enableVersioning(S3Client client, String bucketName) {
        client.putBucketVersioning(PutBucketVersioningRequest.builder()
                .bucket(bucketName)
                .versioningConfiguration(VersioningConfiguration.builder()
                        .status(BucketVersioningStatus.ENABLED)
                        .build())
                .build());
    }

    /**
     * Sets up lifecycle rules for document retention.
     * - Transitions older versions to Glacier after 30 days
     * - Expires noncurrent versions after 7 years (2555 days)
     * - Deletes expired object delete markers
     * 
     * @param client S3 client
     * @param bucketName Name of the bucket to configure
     */
    private void setLifecycleRules(S3Client client, String bucketName) {
        // Rule 1: Transition noncurrent versions to Glacier after 30 days
        LifecycleRule transitionRule = LifecycleRule.builder()
                .id("TransitionToGlacierRule")
                .status(ExpirationStatus.ENABLED)
                .noncurrentVersionTransitions(NoncurrentVersionTransition.builder()
                        .noncurrentDays(30)
                        .storageClass(StorageClass.GLACIER)
                        .build())
                .build();

        // Rule 2: Expire noncurrent versions after 7 years (2555 days)
        LifecycleRule expirationRule = LifecycleRule.builder()
                .id("ExpireNoncurrentVersionsRule")
                .status(ExpirationStatus.ENABLED)
                .noncurrentVersionExpiration(NoncurrentVersionExpiration.builder()
                        .noncurrentDays(2555) // 7 years retention
                        .build())
                .build();

        // Rule 3: Delete expired object delete markers
        LifecycleRule deleteMarkersRule = LifecycleRule.builder()
                .id("DeleteExpiredMarkersRule")
                .status(ExpirationStatus.ENABLED)
                .expiration(LifecycleExpiration.builder()
                        .expiredObjectDeleteMarker(true)
                        .build())
                .build();

        // Apply all rules
        client.putBucketLifecycleConfiguration(PutBucketLifecycleConfigurationRequest.builder()
                .bucket(bucketName)
                .lifecycleConfiguration(BucketLifecycleConfiguration.builder()
                        .rules(transitionRule, expirationRule, deleteMarkersRule)
                        .build())
                .build());
    }

    /**
     * Generates a signed URL for securely accessing an object.
     * 
     * @param objectKey The key of the object to generate a URL for
     * @return A pre-signed URL with a short expiration time
     */
    public URL generateSignedUrl(String objectKey) {
        S3Presigner presigner = s3Presigner();

        GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                .bucket(bucketName)
                .key(objectKey)
                .build();

        GetObjectPresignRequest presignRequest = GetObjectPresignRequest.builder()
                .signatureDuration(Duration.ofMinutes(signedUrlExpirationMinutes))
                .getObjectRequest(getObjectRequest)
                .build();

        PresignedGetObjectRequest presignedRequest = presigner.presignGetObject(presignRequest);
        return presignedRequest.url();
    }

    /**
     * Gets the current bucket name being used by the application.
     * 
     * @return The active bucket name
     */
    public String getBucketName() {
        return bucketName;
    }
    
    /**
     * Retrieves metadata for a document.
     * 
     * @param objectKey The key of the object
     * @return HeadObjectResponse containing metadata
     */
    public HeadObjectResponse getDocumentMetadata(String objectKey) {
        S3Client client = s3Client();
        
        return client.headObject(HeadObjectRequest.builder()
                .bucket(bucketName)
                .key(objectKey)
                .build());
    }
    
    /**
     * Checks the restoration status of a document from Glacier.
     * 
     * @param objectKey The key of the object to check
     * @return true if restoration is complete, false if in progress, null if not being restored
     */
    public Boolean checkRestoreStatus(String objectKey) {
        S3Client client = s3Client();
        
        HeadObjectResponse response = client.headObject(HeadObjectRequest.builder()
                .bucket(bucketName)
                .key(objectKey)
                .build());
        
        // Check if object is in Glacier
        if (response.storageClass() != StorageClass.GLACIER) {
            return null; // Not in Glacier, no restoration needed
        }
        
        // Check restore status
        String restoreStatus = response.restore();
        if (restoreStatus == null) {
            return null; // No restoration in progress or completed
        }
        
        // Parse restore status
        if (restoreStatus.contains("ongoing-request=\"false\"")) {
            return true; // Restoration complete
        } else if (restoreStatus.contains("ongoing-request=\"true\"")) {
            return false; // Restoration in progress
        }
        
        return null; // No restoration in progress
    }
    
    /**
     * Initiates restoration of an archived document from Glacier.
     * 
     * @param objectKey The key of the object to restore
     * @param expirationDays Number of days the restored copy will be available
     */
    public void restoreArchivedDocument(String objectKey, int expirationDays) {
        S3Client client = s3Client();
        
        // Check if the object is in Glacier storage class
        HeadObjectResponse metadata = getDocumentMetadata(objectKey);
        if (metadata.storageClass() != StorageClass.GLACIER) {
            throw new IllegalStateException("Document is not archived in Glacier: " + objectKey);
        }
        
        // Initiate restoration
        client.restoreObject(RestoreObjectRequest.builder()
                .bucket(bucketName)
                .key(objectKey)
                .restoreRequest(RestoreRequest.builder()
                        .days(expirationDays)
                        .glacierJobParameters(GlacierJobParameters.builder()
                                .tier(Tier.STANDARD)
                                .build())
                        .build())
                .build());
    }
    
    /**
     * Generates a signed URL for uploading an object.
     * 
     * @param objectKey The key of the object to upload
     * @param contentType The content type of the object
     * @param expirationMinutes Custom expiration time in minutes (optional)
     * @return A pre-signed URL for uploading
     */
    public URL generateSignedUploadUrl(String objectKey, String contentType, Integer expirationMinutes) {
        S3Presigner presigner = s3Presigner();
        
        // Use provided expiration or default
        int expiration = expirationMinutes != null ? expirationMinutes : signedUrlExpirationMinutes;
        
        PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                .bucket(bucketName)
                .key(objectKey)
                .contentType(contentType)
                .build();
                
        PutObjectPresignRequest presignRequest = PutObjectPresignRequest.builder()
                .signatureDuration(Duration.ofMinutes(expiration))
                .putObjectRequest(putObjectRequest)
                .build();
                
        return presigner.presignPutObject(presignRequest).url();
    }
    
    /**
     * Retrieves the version history for a document.
     * 
     * @param objectKey The key of the object to get versions for
     * @return List of object versions
     */
    public List<ObjectVersion> getDocumentVersions(String objectKey) {
        S3Client client = s3Client();
        
        ListObjectVersionsRequest request = ListObjectVersionsRequest.builder()
                .bucket(bucketName)
                .prefix(objectKey)
                .build();
                
        ListObjectVersionsResponse response = client.listObjectVersions(request);
        return response.versions();
    }
    
    /**
     * Generates a signed URL for a specific version of a document.
     * 
     * @param objectKey The key of the object
     * @param versionId The version ID of the object
     * @return A pre-signed URL for the specific version
     */
    public URL generateSignedUrlForVersion(String objectKey, String versionId) {
        S3Presigner presigner = s3Presigner();
        
        GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                .bucket(bucketName)
                .key(objectKey)
                .versionId(versionId)
                .build();
                
        GetObjectPresignRequest presignRequest = GetObjectPresignRequest.builder()
                .signatureDuration(Duration.ofMinutes(signedUrlExpirationMinutes))
                .getObjectRequest(getObjectRequest)
                .build();
                
        PresignedGetObjectRequest presignedRequest = presigner.presignGetObject(presignRequest);
        return presignedRequest.url();
    }
    
    /**
     * Checks if a document exists in the S3 bucket.
     * 
     * @param objectKey The key of the object to check
     * @return true if the object exists, false otherwise
     */
    public boolean documentExists(String objectKey) {
        S3Client client = s3Client();
        
        try {
            client.headObject(HeadObjectRequest.builder()
                    .bucket(bucketName)
                    .key(objectKey)
                    .build());
            return true;
        } catch (S3Exception e) {
            if (e.statusCode() == 404) {
                return false;
            }
            throw e;
        }
    }
    
    /**
     * Deletes a document from the S3 bucket.
     * 
     * @param objectKey The key of the object to delete
     * @return true if deletion was successful
     */
    public boolean deleteDocument(String objectKey) {
        S3Client client = s3Client();
        
        try {
            client.deleteObject(DeleteObjectRequest.builder()
                    .bucket(bucketName)
                    .key(objectKey)
                    .build());
            return true;
        } catch (S3Exception e) {
            throw new RuntimeException("Failed to delete document: " + e.getMessage(), e);
        }
    }
    
    /**
     * Copies a document to a new location within the same bucket.
     * 
     * @param sourceKey The source object key
     * @param destinationKey The destination object key
     * @return true if copy was successful
     */
    public boolean copyDocument(String sourceKey, String destinationKey) {
        S3Client client = s3Client();
        
        try {
            client.copyObject(CopyObjectRequest.builder()
                    .sourceBucket(bucketName)
                    .sourceKey(sourceKey)
                    .destinationBucket(bucketName)
                    .destinationKey(destinationKey)
                    .build());
            return true;
        } catch (S3Exception e) {
            throw new RuntimeException("Failed to copy document: " + e.getMessage(), e);
        }
    }
    
    /**
     * Updates metadata for an existing document.
     * 
     * @param objectKey The key of the object to update
     * @param metadata Map of metadata keys and values
     */
    public void updateDocumentMetadata(String objectKey, Map<String, String> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return;
        }
        
        S3Client client = s3Client();
        
        // To update metadata, we need to copy the object to itself with new metadata
        CopyObjectRequest copyRequest = CopyObjectRequest.builder()
                .sourceBucket(bucketName)
                .sourceKey(objectKey)
                .destinationBucket(bucketName)
                .destinationKey(objectKey)
                .metadata(metadata)
                .metadataDirective(MetadataDirective.REPLACE)
                .build();
                
        client.copyObject(copyRequest);
    }
    
    /**
     * Adds tags to a document for categorization and lifecycle management.
     * 
     * @param objectKey The key of the object to tag
     * @param tags Map of tag keys and values
     */
    public void tagDocument(String objectKey, Map<String, String> tags) {
        if (tags == null || tags.isEmpty()) {
            return;
        }
        
        S3Client client = s3Client();
        
        // Convert Map to Tagging object
        List<Tag> tagList = tags.entrySet().stream()
                .map(entry -> Tag.builder()
                        .key(entry.getKey())
                        .value(entry.getValue())
                        .build())
                .collect(java.util.stream.Collectors.toList());
        
        Tagging tagging = Tagging.builder()
                .tagSet(tagList)
                .build();
        
        client.putObjectTagging(PutObjectTaggingRequest.builder()
                .bucket(bucketName)
                .key(objectKey)
                .tagging(tagging)
                .build());
    }
    
    /**
     * Sets a bucket policy to restrict access to authorized services only.
     * 
     * @param client S3 client
     * @param bucketName Name of the bucket to configure
     */
    private void setBucketPolicy(S3Client client, String bucketName) {
        // Create a policy that restricts access to authorized services only
        // This is a basic policy that denies public access and allows only specific IAM roles
        String policy = String.format(
            "{"
            + "  \"Version\": \"2012-10-17\","
            + "  \"Statement\": ["
            + "    {"
            + "      \"Sid\": \"DenyPublicReadAccess\","
            + "      \"Effect\": \"Deny\","
            + "      \"Principal\": \"*\","
            + "      \"Action\": [\"s3:GetObject\", \"s3:ListBucket\"],"
            + "      \"Resource\": [\"arn:aws:s3:::%1$s/*\", \"arn:aws:s3:::%1$s\"],"
            + "      \"Condition\": {"
            + "        \"StringNotLike\": {"
            + "          \"aws:PrincipalArn\": ["
            + "            \"arn:aws:iam::*:role/MCAServiceRole\","
            + "            \"arn:aws:iam::*:role/MCAAdminRole\""
            + "          ]"
            + "        }"
            + "      }"
            + "    },"
            + "    {"
            + "      \"Sid\": \"EnforceEncryptedTransport\","
            + "      \"Effect\": \"Deny\","
            + "      \"Principal\": \"*\","
            + "      \"Action\": \"s3:*\","
            + "      \"Resource\": [\"arn:aws:s3:::%1$s/*\", \"arn:aws:s3:::%1$s\"],"
            + "      \"Condition\": {"
            + "        \"Bool\": {"
            + "          \"aws:SecureTransport\": \"false\""
            + "        }"
            + "      }"
            + "    }"
            + "  ]"
            + "}", bucketName);

        client.putBucketPolicy(PutBucketPolicyRequest.builder()
                .bucket(bucketName)
                .policy(policy)
                .build());
    }
}