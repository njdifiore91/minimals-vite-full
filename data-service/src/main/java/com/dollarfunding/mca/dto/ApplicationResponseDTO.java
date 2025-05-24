package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * DTO class for returning MCA application data to clients.
 * 
 * This class includes all application fields (id, status, metadata, created_at, updated_at, review_status)
 * along with associated merchant details and document references. It provides a complete view of an
 * application with appropriate serialization for API responses.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApplicationResponseDTO {

    /**
     * Unique identifier for the application
     */
    @JsonProperty("id")
    private UUID id;

    /**
     * Current status of the application in its lifecycle
     */
    @JsonProperty("status")
    private String status;

    /**
     * Current review status of the application
     */
    @JsonProperty("review_status")
    private String reviewStatus;

    /**
     * Application metadata including processing details, confidence scores, etc.
     */
    @JsonProperty("metadata")
    private Map<String, Object> metadata;

    /**
     * Timestamp when the application was created
     */
    @JsonProperty("created_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime createdAt;

    /**
     * Timestamp when the application was last updated
     */
    @JsonProperty("updated_at")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime updatedAt;

    /**
     * Associated merchant details
     */
    @JsonProperty("merchant_details")
    private MerchantDetailsResponseDTO merchantDetails;

    /**
     * Associated documents
     */
    @JsonProperty("documents")
    private List<DocumentResponseDTO> documents;

    /**
     * Processing time in minutes
     */
    @JsonProperty("processing_time_minutes")
    private Long processingTimeMinutes;

    /**
     * Flag indicating if the application was processed within the target time (5 minutes)
     */
    @JsonProperty("processed_within_target_time")
    private Boolean processedWithinTargetTime;

    /**
     * Flag indicating if the application has all required documents
     */
    @JsonProperty("has_all_required_documents")
    private Boolean hasAllRequiredDocuments;

    /**
     * Flag indicating if the application is completed
     */
    @JsonProperty("is_completed")
    private Boolean isCompleted;

    /**
     * Flag indicating if the application is active
     */
    @JsonProperty("is_active")
    private Boolean isActive;

    /**
     * Flag indicating if the application has been decided upon
     */
    @JsonProperty("is_decided")
    private Boolean isDecided;

    /**
     * Flag indicating if the application requires review
     */
    @JsonProperty("requires_review")
    private Boolean requiresReview;

    /**
     * Default constructor
     */
    public ApplicationResponseDTO() {
        this.metadata = new HashMap<>();
        this.documents = new ArrayList<>();
    }

    /**
     * Constructor from Application entity
     * 
     * @param application The Application entity to convert
     * @param includeMerchantDetails Flag indicating whether to include merchant details
     * @param includeDocuments Flag indicating whether to include documents
     * @param maskPii Flag indicating whether to mask PII data
     */
    public ApplicationResponseDTO(Application application, boolean includeMerchantDetails, 
                                 boolean includeDocuments, boolean maskPii) {
        this.id = application.getId();
        this.status = application.getStatus() != null ? application.getStatus().name() : null;
        this.reviewStatus = application.getReviewStatus() != null ? application.getReviewStatus().name() : null;
        this.metadata = application.getMetadata();
        this.createdAt = application.getCreatedAt();
        this.updatedAt = application.getUpdatedAt();
        
        // Calculate derived fields
        this.processingTimeMinutes = application.getProcessingTimeMinutes() >= 0 ? 
                                    application.getProcessingTimeMinutes() : null;
        this.processedWithinTargetTime = application.isProcessedWithinTargetTime();
        this.hasAllRequiredDocuments = application.hasAllRequiredDocuments();
        this.isCompleted = application.isCompleted();
        this.isActive = application.isActive();
        this.isDecided = application.isDecided();
        this.requiresReview = application.requiresReview();
        
        // Include merchant details if requested
        if (includeMerchantDetails && application.getMerchantDetails() != null) {
            this.merchantDetails = maskPii ? 
                MerchantDetailsResponseDTO.fromEntityWithMaskedPii(application.getMerchantDetails()) :
                MerchantDetailsResponseDTO.fromEntityWithFullPii(application.getMerchantDetails());
        }
        
        // Include documents if requested
        if (includeDocuments && application.getDocuments() != null && !application.getDocuments().isEmpty()) {
            this.documents = new ArrayList<>();
            for (Document document : application.getDocuments()) {
                // Generate a pre-signed URL for document access
                // This would typically be done by a service that generates time-limited URLs
                String downloadUrl = generateDownloadUrl(document);
                LocalDateTime urlExpiresAt = LocalDateTime.now().plusHours(1); // URL valid for 1 hour
                
                DocumentResponseDTO documentDTO = DocumentResponseDTO.fromEntity(document, downloadUrl, urlExpiresAt);
                if (documentDTO != null) {
                    this.documents.add(documentDTO);
                }
            }
        } else {
            this.documents = new ArrayList<>();
        }
    }

    /**
     * Static factory method to create a DTO from an Application entity
     * 
     * @param application The Application entity to convert
     * @param includeMerchantDetails Flag indicating whether to include merchant details
     * @param includeDocuments Flag indicating whether to include documents
     * @param maskPii Flag indicating whether to mask PII data
     * @return A new ApplicationResponseDTO instance
     */
    public static ApplicationResponseDTO fromEntity(Application application, boolean includeMerchantDetails, 
                                                  boolean includeDocuments, boolean maskPii) {
        if (application == null) {
            return null;
        }
        return new ApplicationResponseDTO(application, includeMerchantDetails, includeDocuments, maskPii);
    }

    /**
     * Static factory method to create a DTO from an Application entity with all details
     * 
     * @param application The Application entity to convert
     * @param maskPii Flag indicating whether to mask PII data
     * @return A new ApplicationResponseDTO instance with all details
     */
    public static ApplicationResponseDTO fromEntityWithAllDetails(Application application, boolean maskPii) {
        return fromEntity(application, true, true, maskPii);
    }

    /**
     * Static factory method to create a DTO from an Application entity with minimal details
     * 
     * @param application The Application entity to convert
     * @return A new ApplicationResponseDTO instance with minimal details
     */
    public static ApplicationResponseDTO fromEntityWithMinimalDetails(Application application) {
        return fromEntity(application, false, false, true);
    }

    /**
     * Static factory method to create a list of DTOs from a list of Application entities
     * 
     * @param applications The list of Application entities to convert
     * @param includeMerchantDetails Flag indicating whether to include merchant details
     * @param includeDocuments Flag indicating whether to include documents
     * @param maskPii Flag indicating whether to mask PII data
     * @return A list of ApplicationResponseDTO instances
     */
    public static List<ApplicationResponseDTO> fromEntities(List<Application> applications, boolean includeMerchantDetails, 
                                                          boolean includeDocuments, boolean maskPii) {
        if (applications == null) {
            return new ArrayList<>();
        }
        return applications.stream()
                .map(application -> fromEntity(application, includeMerchantDetails, includeDocuments, maskPii))
                .collect(Collectors.toList());
    }

    /**
     * Generates a pre-signed URL for document access
     * This is a placeholder method that would typically be implemented by a service
     * 
     * @param document The document to generate a URL for
     * @return A pre-signed URL for document access
     */
    private String generateDownloadUrl(Document document) {
        // This is a placeholder implementation
        // In a real implementation, this would generate a pre-signed URL using AWS SDK or similar
        if (document == null || document.getStoragePath() == null) {
            return null;
        }
        
        // Extract bucket and key from storage path
        String bucketName = document.getBucketName();
        String objectKey = document.getObjectKey();
        
        if (bucketName == null || objectKey == null) {
            return null;
        }
        
        // This is just a placeholder URL format
        // In a real implementation, this would be a properly signed URL
        return String.format("/api/v1/documents/%s/download", document.getId());
    }

    /**
     * @return the application ID
     */
    public UUID getId() {
        return id;
    }

    /**
     * @param id the application ID to set
     */
    public void setId(UUID id) {
        this.id = id;
    }

    /**
     * @return the application status as a string
     */
    public String getStatus() {
        return status;
    }

    /**
     * @param status the application status to set as a string
     */
    public void setStatus(String status) {
        this.status = status;
    }

    /**
     * @param status the application status to set as enum
     */
    public void setStatus(ApplicationStatus status) {
        this.status = status != null ? status.name() : null;
    }

    /**
     * @return the review status as a string
     */
    public String getReviewStatus() {
        return reviewStatus;
    }

    /**
     * @param reviewStatus the review status to set as a string
     */
    public void setReviewStatus(String reviewStatus) {
        this.reviewStatus = reviewStatus;
    }

    /**
     * @param reviewStatus the review status to set as enum
     */
    public void setReviewStatus(ReviewStatus reviewStatus) {
        this.reviewStatus = reviewStatus != null ? reviewStatus.name() : null;
    }

    /**
     * @return the application metadata
     */
    public Map<String, Object> getMetadata() {
        return metadata;
    }

    /**
     * @param metadata the application metadata to set
     */
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata != null ? metadata : new HashMap<>();
    }

    /**
     * @return the creation timestamp
     */
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    /**
     * @param createdAt the creation timestamp to set
     */
    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    /**
     * @return the update timestamp
     */
    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    /**
     * @param updatedAt the update timestamp to set
     */
    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    /**
     * @return the merchant details
     */
    public MerchantDetailsResponseDTO getMerchantDetails() {
        return merchantDetails;
    }

    /**
     * @param merchantDetails the merchant details to set
     */
    public void setMerchantDetails(MerchantDetailsResponseDTO merchantDetails) {
        this.merchantDetails = merchantDetails;
    }

    /**
     * @return the list of documents
     */
    public List<DocumentResponseDTO> getDocuments() {
        return documents;
    }

    /**
     * @param documents the list of documents to set
     */
    public void setDocuments(List<DocumentResponseDTO> documents) {
        this.documents = documents != null ? documents : new ArrayList<>();
    }

    /**
     * @return the processing time in minutes
     */
    public Long getProcessingTimeMinutes() {
        return processingTimeMinutes;
    }

    /**
     * @param processingTimeMinutes the processing time to set
     */
    public void setProcessingTimeMinutes(Long processingTimeMinutes) {
        this.processingTimeMinutes = processingTimeMinutes;
    }

    /**
     * @return whether the application was processed within the target time
     */
    public Boolean getProcessedWithinTargetTime() {
        return processedWithinTargetTime;
    }

    /**
     * @param processedWithinTargetTime the processed within target time flag to set
     */
    public void setProcessedWithinTargetTime(Boolean processedWithinTargetTime) {
        this.processedWithinTargetTime = processedWithinTargetTime;
    }

    /**
     * @return whether the application has all required documents
     */
    public Boolean getHasAllRequiredDocuments() {
        return hasAllRequiredDocuments;
    }

    /**
     * @param hasAllRequiredDocuments the has all required documents flag to set
     */
    public void setHasAllRequiredDocuments(Boolean hasAllRequiredDocuments) {
        this.hasAllRequiredDocuments = hasAllRequiredDocuments;
    }

    /**
     * @return whether the application is completed
     */
    public Boolean getIsCompleted() {
        return isCompleted;
    }

    /**
     * @param isCompleted the is completed flag to set
     */
    public void setIsCompleted(Boolean isCompleted) {
        this.isCompleted = isCompleted;
    }

    /**
     * @return whether the application is active
     */
    public Boolean getIsActive() {
        return isActive;
    }

    /**
     * @param isActive the is active flag to set
     */
    public void setIsActive(Boolean isActive) {
        this.isActive = isActive;
    }

    /**
     * @return whether the application has been decided upon
     */
    public Boolean getIsDecided() {
        return isDecided;
    }

    /**
     * @param isDecided the is decided flag to set
     */
    public void setIsDecided(Boolean isDecided) {
        this.isDecided = isDecided;
    }

    /**
     * @return whether the application requires review
     */
    public Boolean getRequiresReview() {
        return requiresReview;
    }

    /**
     * @param requiresReview the requires review flag to set
     */
    public void setRequiresReview(Boolean requiresReview) {
        this.requiresReview = requiresReview;
    }

    /**
     * Gets a specific metadata value
     * 
     * @param key the metadata key
     * @param <T> the expected type of the metadata value
     * @return the metadata value, or null if not available
     */
    @SuppressWarnings("unchecked")
    public <T> T getMetadataValue(String key) {
        if (metadata == null) {
            return null;
        }
        return (T) metadata.get(key);
    }

    /**
     * Gets the count of documents by type
     * 
     * @return a map of document types to counts
     */
    public Map<String, Integer> getDocumentCountsByType() {
        if (documents == null || documents.isEmpty()) {
            return new HashMap<>();
        }
        
        Map<String, Integer> counts = new HashMap<>();
        for (DocumentResponseDTO document : documents) {
            String type = document.getType();
            if (type != null) {
                counts.put(type, counts.getOrDefault(type, 0) + 1);
            }
        }
        
        return counts;
    }

    /**
     * Gets documents of a specific type
     * 
     * @param type the document type to filter by
     * @return a list of documents of the specified type
     */
    public List<DocumentResponseDTO> getDocumentsByType(String type) {
        if (documents == null || documents.isEmpty() || type == null) {
            return new ArrayList<>();
        }
        
        return documents.stream()
                .filter(doc -> type.equals(doc.getType()))
                .collect(Collectors.toList());
    }

    /**
     * Checks if this application has merchant details
     * 
     * @return true if the application has merchant details
     */
    public boolean hasMerchantDetails() {
        return merchantDetails != null;
    }

    /**
     * Checks if this application has documents
     * 
     * @return true if the application has documents
     */
    public boolean hasDocuments() {
        return documents != null && !documents.isEmpty();
    }

    /**
     * Builder class for creating ApplicationResponseDTO instances
     */
    public static class Builder {
        private UUID id;
        private String status;
        private String reviewStatus;
        private Map<String, Object> metadata;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private MerchantDetailsResponseDTO merchantDetails;
        private List<DocumentResponseDTO> documents;
        private Long processingTimeMinutes;
        private Boolean processedWithinTargetTime;
        private Boolean hasAllRequiredDocuments;
        private Boolean isCompleted;
        private Boolean isActive;
        private Boolean isDecided;
        private Boolean requiresReview;

        public Builder() {
            this.metadata = new HashMap<>();
            this.documents = new ArrayList<>();
        }

        public Builder(Application application) {
            this.id = application.getId();
            this.status = application.getStatus() != null ? application.getStatus().name() : null;
            this.reviewStatus = application.getReviewStatus() != null ? application.getReviewStatus().name() : null;
            this.metadata = application.getMetadata();
            this.createdAt = application.getCreatedAt();
            this.updatedAt = application.getUpdatedAt();
            this.processingTimeMinutes = application.getProcessingTimeMinutes() >= 0 ? 
                                        application.getProcessingTimeMinutes() : null;
            this.processedWithinTargetTime = application.isProcessedWithinTargetTime();
            this.hasAllRequiredDocuments = application.hasAllRequiredDocuments();
            this.isCompleted = application.isCompleted();
            this.isActive = application.isActive();
            this.isDecided = application.isDecided();
            this.requiresReview = application.requiresReview();
            this.documents = new ArrayList<>();
        }

        public Builder withId(UUID id) {
            this.id = id;
            return this;
        }

        public Builder withStatus(String status) {
            this.status = status;
            return this;
        }

        public Builder withStatus(ApplicationStatus status) {
            this.status = status != null ? status.name() : null;
            return this;
        }

        public Builder withReviewStatus(String reviewStatus) {
            this.reviewStatus = reviewStatus;
            return this;
        }

        public Builder withReviewStatus(ReviewStatus reviewStatus) {
            this.reviewStatus = reviewStatus != null ? reviewStatus.name() : null;
            return this;
        }

        public Builder withMetadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Builder withCreatedAt(LocalDateTime createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        public Builder withUpdatedAt(LocalDateTime updatedAt) {
            this.updatedAt = updatedAt;
            return this;
        }

        public Builder withMerchantDetails(MerchantDetailsResponseDTO merchantDetails) {
            this.merchantDetails = merchantDetails;
            return this;
        }

        public Builder withDocuments(List<DocumentResponseDTO> documents) {
            this.documents = documents;
            return this;
        }

        public Builder withProcessingTimeMinutes(Long processingTimeMinutes) {
            this.processingTimeMinutes = processingTimeMinutes;
            return this;
        }

        public Builder withProcessedWithinTargetTime(Boolean processedWithinTargetTime) {
            this.processedWithinTargetTime = processedWithinTargetTime;
            return this;
        }

        public Builder withHasAllRequiredDocuments(Boolean hasAllRequiredDocuments) {
            this.hasAllRequiredDocuments = hasAllRequiredDocuments;
            return this;
        }

        public Builder withIsCompleted(Boolean isCompleted) {
            this.isCompleted = isCompleted;
            return this;
        }

        public Builder withIsActive(Boolean isActive) {
            this.isActive = isActive;
            return this;
        }

        public Builder withIsDecided(Boolean isDecided) {
            this.isDecided = isDecided;
            return this;
        }

        public Builder withRequiresReview(Boolean requiresReview) {
            this.requiresReview = requiresReview;
            return this;
        }

        public Builder addDocument(DocumentResponseDTO document) {
            if (this.documents == null) {
                this.documents = new ArrayList<>();
            }
            this.documents.add(document);
            return this;
        }

        public ApplicationResponseDTO build() {
            ApplicationResponseDTO dto = new ApplicationResponseDTO();
            dto.setId(id);
            dto.setStatus(status);
            dto.setReviewStatus(reviewStatus);
            dto.setMetadata(metadata);
            dto.setCreatedAt(createdAt);
            dto.setUpdatedAt(updatedAt);
            dto.setMerchantDetails(merchantDetails);
            dto.setDocuments(documents);
            dto.setProcessingTimeMinutes(processingTimeMinutes);
            dto.setProcessedWithinTargetTime(processedWithinTargetTime);
            dto.setHasAllRequiredDocuments(hasAllRequiredDocuments);
            dto.setIsCompleted(isCompleted);
            dto.setIsActive(isActive);
            dto.setIsDecided(isDecided);
            dto.setRequiresReview(requiresReview);
            return dto;
        }
    }
}