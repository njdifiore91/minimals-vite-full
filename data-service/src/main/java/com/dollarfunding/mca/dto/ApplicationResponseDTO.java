package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Data Transfer Object for returning MCA application data to clients.
 * Includes all application fields along with associated merchant details and document references.
 * This class provides a complete view of an application with appropriate serialization for API responses.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApplicationResponseDTO {

    @JsonProperty("id")
    private UUID id;
    
    @JsonProperty("status")
    private ApplicationStatus status;
    
    @JsonProperty("review_status")
    private ReviewStatus reviewStatus;
    
    @JsonProperty("metadata")
    private Map<String, Object> metadata;
    
    @JsonProperty("created_at")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")
    private LocalDateTime createdAt;
    
    @JsonProperty("updated_at")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")
    private LocalDateTime updatedAt;
    
    @JsonProperty("merchant_details")
    private MerchantDetailsResponseDTO merchantDetails;
    
    @JsonProperty("documents")
    private List<DocumentResponseDTO> documents;

    // Default constructor
    public ApplicationResponseDTO() {
    }

    /**
     * Creates a DTO from an Application entity
     * @param application The Application entity to convert
     * @return A new ApplicationResponseDTO
     */
    public static ApplicationResponseDTO fromEntity(Application application) {
        if (application == null) {
            return null;
        }
        
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        dto.setId(application.getId());
        dto.setStatus(application.getStatus());
        dto.setReviewStatus(application.getReviewStatus());
        dto.setMetadata(application.getMetadata());
        dto.setCreatedAt(application.getCreatedAt());
        dto.setUpdatedAt(application.getUpdatedAt());
        
        // Convert merchant details if present
        if (application.getMerchantDetails() != null) {
            dto.setMerchantDetails(MerchantDetailsResponseDTO.fromEntity(application.getMerchantDetails()));
        }
        
        // Convert documents if present
        if (application.getDocuments() != null && !application.getDocuments().isEmpty()) {
            dto.setDocuments(application.getDocuments().stream()
                    .map(DocumentResponseDTO::fromEntity)
                    .collect(Collectors.toList()));
        }
        
        return dto;
    }
    
    /**
     * Creates a list of DTOs from a list of Application entities
     * @param applications The list of Application entities to convert
     * @return A list of ApplicationResponseDTOs
     */
    public static List<ApplicationResponseDTO> fromEntities(List<Application> applications) {
        if (applications == null) {
            return null;
        }
        
        return applications.stream()
                .map(ApplicationResponseDTO::fromEntity)
                .collect(Collectors.toList());
    }

    // Getters and Setters
    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public ApplicationStatus getStatus() {
        return status;
    }

    public void setStatus(ApplicationStatus status) {
        this.status = status;
    }

    public ReviewStatus getReviewStatus() {
        return reviewStatus;
    }

    public void setReviewStatus(ReviewStatus reviewStatus) {
        this.reviewStatus = reviewStatus;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public MerchantDetailsResponseDTO getMerchantDetails() {
        return merchantDetails;
    }

    public void setMerchantDetails(MerchantDetailsResponseDTO merchantDetails) {
        this.merchantDetails = merchantDetails;
    }

    public List<DocumentResponseDTO> getDocuments() {
        return documents;
    }

    public void setDocuments(List<DocumentResponseDTO> documents) {
        this.documents = documents;
    }

    /**
     * Returns a summary of the application status and associated data
     * @return A string representation of the application status
     */
    public String getStatusSummary() {
        StringBuilder summary = new StringBuilder();
        summary.append("Application ").append(id).append(" is ").append(status);
        summary.append(" (Review: ").append(reviewStatus).append(")");
        
        if (merchantDetails != null) {
            summary.append(" for merchant ").append(merchantDetails.getLegalName());
        }
        
        if (documents != null) {
            summary.append(" with ").append(documents.size()).append(" document(s)");
        }
        
        return summary.toString();
    }
    
    @Override
    public String toString() {
        return "ApplicationResponseDTO{" +
                "id=" + id +
                ", status=" + status +
                ", reviewStatus=" + reviewStatus +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                ", merchantDetails=" + (merchantDetails != null ? "present" : "null") +
                ", documents=" + (documents != null ? documents.size() + " documents" : "null") +
                '}';
    }
}