package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Data Transfer Object for filtering and searching MCA applications.
 * This class defines the structure for filter criteria including status, review status,
 * date range, merchant name, and other searchable fields.
 * 
 * It supports pagination, sorting, and conversion to Spring Pageable and Specification
 * objects for efficient database queries.
 */
public class ApplicationFilterDTO {

    // Filter fields
    private ApplicationStatus status;
    private ReviewStatus reviewStatus;
    private String merchantName;
    private LocalDate startDate;
    private LocalDate endDate;
    private String searchTerm;
    
    // Pagination fields
    private Integer page = 0;
    private Integer size = 10;
    
    // Sorting fields
    private String sortBy = "createdAt";
    private String sortDirection = "desc";
    
    /**
     * Default constructor
     */
    public ApplicationFilterDTO() {
    }
    
    /**
     * Constructor with filter parameters
     * 
     * @param status Application status filter
     * @param reviewStatus Review status filter
     * @param merchantName Merchant name filter
     * @param startDate Start date for date range filter
     * @param endDate End date for date range filter
     * @param searchTerm General search term for text fields
     * @param page Page number (zero-based)
     * @param size Page size
     * @param sortBy Field to sort by
     * @param sortDirection Sort direction (asc or desc)
     */
    public ApplicationFilterDTO(ApplicationStatus status, ReviewStatus reviewStatus, 
                               String merchantName, LocalDate startDate, LocalDate endDate,
                               String searchTerm, Integer page, Integer size,
                               String sortBy, String sortDirection) {
        this.status = status;
        this.reviewStatus = reviewStatus;
        this.merchantName = merchantName;
        this.startDate = startDate;
        this.endDate = endDate;
        this.searchTerm = searchTerm;
        this.page = page != null ? page : 0;
        this.size = size != null ? size : 10;
        this.sortBy = sortBy != null ? sortBy : "createdAt";
        this.sortDirection = sortDirection != null ? sortDirection : "desc";
    }
    
    /**
     * Converts this filter DTO to a Spring Pageable object for pagination and sorting
     * 
     * @return Pageable object configured with this DTO's pagination and sorting parameters
     */
    public Pageable toPageable() {
        Sort sort = Sort.by(Sort.Direction.fromString(sortDirection), sortBy);
        return PageRequest.of(page, size, sort);
    }
    
    /**
     * Creates a JPA Specification for filtering applications based on this DTO's criteria
     * 
     * @return Specification object for filtering applications
     */
    public Specification<?> toSpecification() {
        return (root, query, criteriaBuilder) -> {
            List<javax.persistence.criteria.Predicate> predicates = new ArrayList<>();
            
            // Filter by application status
            if (status != null) {
                predicates.add(criteriaBuilder.equal(root.get("status"), status));
            }
            
            // Filter by review status
            if (reviewStatus != null) {
                predicates.add(criteriaBuilder.equal(root.get("reviewStatus"), reviewStatus));
            }
            
            // Filter by date range
            if (startDate != null) {
                LocalDateTime startDateTime = startDate.atStartOfDay();
                predicates.add(criteriaBuilder.greaterThanOrEqualTo(
                    root.get("createdAt"), startDateTime));
            }
            
            if (endDate != null) {
                LocalDateTime endDateTime = endDate.atTime(LocalTime.MAX);
                predicates.add(criteriaBuilder.lessThanOrEqualTo(
                    root.get("createdAt"), endDateTime));
            }
            
            // Filter by merchant name (requires join with MerchantDetails)
            if (merchantName != null && !merchantName.trim().isEmpty()) {
                javax.persistence.criteria.Join<?, ?> merchantJoin = root.join("merchantDetails");
                predicates.add(criteriaBuilder.or(
                    criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("legalName")), 
                                         "%" + merchantName.toLowerCase() + "%"),
                    criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("dbaName")), 
                                         "%" + merchantName.toLowerCase() + "%")
                ));
            }
            
            // General search term (searches across multiple fields)
            if (searchTerm != null && !searchTerm.trim().isEmpty()) {
                String searchPattern = "%" + searchTerm.toLowerCase() + "%";
                javax.persistence.criteria.Join<?, ?> merchantJoin = root.join("merchantDetails", javax.persistence.criteria.JoinType.LEFT);
                
                predicates.add(criteriaBuilder.or(
                    criteriaBuilder.like(criteriaBuilder.lower(root.get("id").as(String.class)), searchPattern),
                    criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("legalName")), searchPattern),
                    criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("dbaName")), searchPattern),
                    criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("ein")), searchPattern),
                    criteriaBuilder.like(criteriaBuilder.lower(merchantJoin.get("industry")), searchPattern)
                ));
            }
            
            return criteriaBuilder.and(predicates.toArray(new javax.persistence.criteria.Predicate[0]));
        };
    }

    // Getters and Setters
    
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

    public String getMerchantName() {
        return merchantName;
    }

    public void setMerchantName(String merchantName) {
        this.merchantName = merchantName;
    }

    public LocalDate getStartDate() {
        return startDate;
    }

    public void setStartDate(LocalDate startDate) {
        this.startDate = startDate;
    }

    public LocalDate getEndDate() {
        return endDate;
    }

    public void setEndDate(LocalDate endDate) {
        this.endDate = endDate;
    }

    public String getSearchTerm() {
        return searchTerm;
    }

    public void setSearchTerm(String searchTerm) {
        this.searchTerm = searchTerm;
    }

    public Integer getPage() {
        return page;
    }

    public void setPage(Integer page) {
        this.page = page != null ? page : 0;
    }

    public Integer getSize() {
        return size;
    }

    public void setSize(Integer size) {
        this.size = size != null ? size : 10;
    }

    public String getSortBy() {
        return sortBy;
    }

    public void setSortBy(String sortBy) {
        this.sortBy = sortBy != null ? sortBy : "createdAt";
    }

    public String getSortDirection() {
        return sortDirection;
    }

    public void setSortDirection(String sortDirection) {
        this.sortDirection = sortDirection != null ? sortDirection : "desc";
    }
    
    @Override
    public String toString() {
        return "ApplicationFilterDTO{" +
                "status=" + status +
                ", reviewStatus=" + reviewStatus +
                ", merchantName='" + merchantName + '\'' +
                ", startDate=" + startDate +
                ", endDate=" + endDate +
                ", searchTerm='" + searchTerm + '\'' +
                ", page=" + page +
                ", size=" + size +
                ", sortBy='" + sortBy + '\'' +
                ", sortDirection='" + sortDirection + '\'' +
                '}';
    }
}