package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.Size;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Data Transfer Object for application filtering and search operations.
 * This class defines the structure for filter criteria including status, review status,
 * date range, merchant name, and other searchable fields.
 * 
 * It is used by the application listing endpoint to filter results based on user-specified criteria
 * and supports pagination, sorting, and ordering of results.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApplicationFilterDTO {

    /**
     * Filter by application status
     */
    private ApplicationStatus status;
    
    /**
     * Filter by application review status
     */
    private ReviewStatus reviewStatus;
    
    /**
     * Filter by merchant legal name or DBA name (case-insensitive partial match)
     */
    @Size(max = 255, message = "Merchant name search cannot exceed 255 characters")
    private String merchantName;
    
    /**
     * Filter by application creation date range - start date (inclusive)
     */
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate createdFrom;
    
    /**
     * Filter by application creation date range - end date (inclusive)
     */
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate createdTo;
    
    /**
     * Filter by minimum revenue amount
     */
    @Min(value = 0, message = "Minimum revenue cannot be negative")
    private Double minRevenue;
    
    /**
     * Filter by maximum revenue amount
     */
    @Min(value = 0, message = "Maximum revenue cannot be negative")
    private Double maxRevenue;
    
    /**
     * Filter by industry type (exact match)
     */
    @Size(max = 100, message = "Industry cannot exceed 100 characters")
    private String industry;
    
    /**
     * Page number for pagination (0-based)
     */
    @Min(value = 0, message = "Page number cannot be negative")
    @Builder.Default
    private Integer page = 0;
    
    /**
     * Page size for pagination
     */
    @Min(value = 1, message = "Page size must be at least 1")
    @Max(value = 100, message = "Page size cannot exceed 100")
    @Builder.Default
    private Integer size = 20;
    
    /**
     * Sort field name
     */
    @Builder.Default
    private String sort = "createdAt";
    
    /**
     * Sort direction (asc or desc)
     */
    @Builder.Default
    private String direction = "desc";
    
    /**
     * Converts this filter DTO to a Spring Pageable object for pagination and sorting
     * 
     * @return Pageable object configured with this DTO's pagination and sorting parameters
     */
    @JsonIgnore
    public Pageable toPageable() {
        Sort.Direction sortDirection = Sort.Direction.fromString(direction);
        return PageRequest.of(page, size, Sort.by(sortDirection, sort));
    }
    
    /**
     * Converts this filter DTO to a JPA Specification for filtering Application entities
     * 
     * @return Specification object for filtering applications based on this DTO's criteria
     */
    @JsonIgnore
    public Specification<?> toSpecification() {
        return (root, query, criteriaBuilder) -> {
            List<javax.persistence.criteria.Predicate> predicates = new ArrayList<>();
            
            // Filter by status if provided
            if (status != null) {
                predicates.add(criteriaBuilder.equal(root.get("status"), status));
            }
            
            // Filter by review status if provided
            if (reviewStatus != null) {
                predicates.add(criteriaBuilder.equal(root.get("reviewStatus"), reviewStatus));
            }
            
            // Filter by merchant name if provided (searches both legal name and DBA name)
            if (merchantName != null && !merchantName.trim().isEmpty()) {
                String searchPattern = "%" + merchantName.toLowerCase() + "%";
                javax.persistence.criteria.Join<?, ?> merchantJoin = root.join("merchantDetails");
                
                predicates.add(
                    criteriaBuilder.or(
                        criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("legalName")), searchPattern),
                        criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("dbaName")), searchPattern)
                    )
                );
            }
            
            // Filter by creation date range if provided
            if (createdFrom != null) {
                predicates.add(criteriaBuilder.greaterThanOrEqualTo(
                    root.get("createdAt").as(LocalDate.class), createdFrom));
            }
            
            if (createdTo != null) {
                predicates.add(criteriaBuilder.lessThanOrEqualTo(
                    root.get("createdAt").as(LocalDate.class), createdTo));
            }
            
            // Filter by revenue range if provided
            if (minRevenue != null || maxRevenue != null) {
                javax.persistence.criteria.Join<?, ?> merchantJoin = root.join("merchantDetails");
                
                if (minRevenue != null) {
                    predicates.add(criteriaBuilder.greaterThanOrEqualTo(
                        merchantJoin.get("revenue"), minRevenue));
                }
                
                if (maxRevenue != null) {
                    predicates.add(criteriaBuilder.lessThanOrEqualTo(
                        merchantJoin.get("revenue"), maxRevenue));
                }
            }
            
            // Filter by industry if provided
            if (industry != null && !industry.trim().isEmpty()) {
                javax.persistence.criteria.Join<?, ?> merchantJoin = root.join("merchantDetails");
                predicates.add(criteriaBuilder.equal(merchantJoin.get("industry"), industry));
            }
            
            return criteriaBuilder.and(predicates.toArray(new javax.persistence.criteria.Predicate[0]));
        };
    }
}