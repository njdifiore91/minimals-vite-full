package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.TestUtils;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;

import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.Predicate;
import javax.persistence.criteria.Root;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Test class for {@link ApplicationFilterDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and conversion between DTO and entity objects.
 * 
 * This test suite ensures that the DTO properly validates input data, converts between
 * different representations, and handles edge cases appropriately to maintain data
 * integrity in the API layer.
 */
@DisplayName("Application Filter DTO Tests")
public class ApplicationFilterDTOTest {

    private ObjectMapper objectMapper;
    
    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        // Configure ObjectMapper to handle Java 8 date/time types
        objectMapper.findAndRegisterModules();
    }
    
    /**
     * Test data provider for pagination parameters.
     */
    static Stream<Arguments> paginationParametersProvider() {
        return Stream.of(
            // page, size, expectedPage, expectedSize
            Arguments.of(null, null, 0, 10),  // Default values
            Arguments.of(0, 5, 0, 5),         // Custom values
            Arguments.of(2, 20, 2, 20),       // Custom values
            Arguments.of(-1, 0, 0, 10),       // Invalid values should use defaults
            Arguments.of(null, 50, 0, 50),    // Null page with custom size
            Arguments.of(5, null, 5, 10)      // Custom page with null size
        );
    }
    
    /**
     * Test data provider for sorting parameters.
     */
    static Stream<Arguments> sortingParametersProvider() {
        return Stream.of(
            // sortBy, sortDirection, expectedSortBy, expectedDirection
            Arguments.of(null, null, "createdAt", "desc"),  // Default values
            Arguments.of("status", "asc", "status", "asc"),  // Custom values
            Arguments.of("merchantName", "desc", "merchantName", "desc"),  // Custom values
            Arguments.of("", "invalid", "createdAt", "desc"),  // Invalid values should use defaults
            Arguments.of(null, "asc", "createdAt", "asc"),  // Null sortBy with valid direction
            Arguments.of("updatedAt", null, "updatedAt", "desc")  // Valid sortBy with null direction
        );
    }
    
    /**
     * Test data provider for date range parameters.
     */
    static Stream<Arguments> dateRangeParametersProvider() {
        LocalDate today = LocalDate.now();
        LocalDate yesterday = today.minusDays(1);
        LocalDate tomorrow = today.plusDays(1);
        
        return Stream.of(
            // startDate, endDate, isValid
            Arguments.of(null, null, true),  // Both null is valid
            Arguments.of(yesterday, today, true),  // Valid range
            Arguments.of(today, today, true),  // Same day is valid
            Arguments.of(tomorrow, today, false),  // Invalid: start after end
            Arguments.of(today, null, true),  // Only start date is valid
            Arguments.of(null, today, true)   // Only end date is valid
        );
    }

    @Test
    @DisplayName("Should create a valid filter DTO with default values")
    void shouldCreateValidFilterDTOWithDefaultValues() {
        // Given/When
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        
        // Then
        assertNull(dto.getStatus(), "Status should be null by default");
        assertNull(dto.getReviewStatus(), "Review status should be null by default");
        assertNull(dto.getMerchantName(), "Merchant name should be null by default");
        assertNull(dto.getStartDate(), "Start date should be null by default");
        assertNull(dto.getEndDate(), "End date should be null by default");
        assertNull(dto.getSearchTerm(), "Search term should be null by default");
        assertEquals(0, dto.getPage(), "Page should default to 0");
        assertEquals(10, dto.getSize(), "Size should default to 10");
        assertEquals("createdAt", dto.getSortBy(), "Sort by should default to createdAt");
        assertEquals("desc", dto.getSortDirection(), "Sort direction should default to desc");
    }
    
    @Test
    @DisplayName("Should create a valid filter DTO with all parameters")
    void shouldCreateValidFilterDTOWithAllParameters() {
        // Given
        ApplicationStatus status = ApplicationStatus.PROCESSING;
        ReviewStatus reviewStatus = ReviewStatus.IN_REVIEW;
        String merchantName = "Test Merchant";
        LocalDate startDate = LocalDate.now().minusDays(7);
        LocalDate endDate = LocalDate.now();
        String searchTerm = "test search";
        Integer page = 2;
        Integer size = 25;
        String sortBy = "status";
        String sortDirection = "asc";
        
        // When
        ApplicationFilterDTO dto = new ApplicationFilterDTO(
                status, reviewStatus, merchantName, startDate, endDate,
                searchTerm, page, size, sortBy, sortDirection);
        
        // Then
        assertEquals(status, dto.getStatus(), "Status should match the provided value");
        assertEquals(reviewStatus, dto.getReviewStatus(), "Review status should match the provided value");
        assertEquals(merchantName, dto.getMerchantName(), "Merchant name should match the provided value");
        assertEquals(startDate, dto.getStartDate(), "Start date should match the provided value");
        assertEquals(endDate, dto.getEndDate(), "End date should match the provided value");
        assertEquals(searchTerm, dto.getSearchTerm(), "Search term should match the provided value");
        assertEquals(page, dto.getPage(), "Page should match the provided value");
        assertEquals(size, dto.getSize(), "Size should match the provided value");
        assertEquals(sortBy, dto.getSortBy(), "Sort by should match the provided value");
        assertEquals(sortDirection, dto.getSortDirection(), "Sort direction should match the provided value");
    }
    
    @ParameterizedTest
    @DisplayName("Should handle pagination parameters correctly")
    @MethodSource("paginationParametersProvider")
    void shouldHandlePaginationParametersCorrectly(Integer page, Integer size, 
                                                 Integer expectedPage, Integer expectedSize) {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        
        // When
        dto.setPage(page);
        dto.setSize(size);
        
        // Then
        assertEquals(expectedPage, dto.getPage(), "Page should be set correctly");
        assertEquals(expectedSize, dto.getSize(), "Size should be set correctly");
    }
    
    @ParameterizedTest
    @DisplayName("Should handle sorting parameters correctly")
    @MethodSource("sortingParametersProvider")
    void shouldHandleSortingParametersCorrectly(String sortBy, String sortDirection, 
                                              String expectedSortBy, String expectedDirection) {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        
        // When
        dto.setSortBy(sortBy);
        dto.setSortDirection(sortDirection);
        
        // Then
        assertEquals(expectedSortBy, dto.getSortBy(), "Sort by should be set correctly");
        assertEquals(expectedDirection, dto.getSortDirection(), "Sort direction should be set correctly");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate date range correctly")
    @MethodSource("dateRangeParametersProvider")
    void shouldValidateDateRangeCorrectly(LocalDate startDate, LocalDate endDate, boolean isValid) {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setStartDate(startDate);
        dto.setEndDate(endDate);
        
        // When
        boolean result = isValidDateRange(dto);
        
        // Then
        assertEquals(isValid, result, "Date range validation should match expected result");
    }
    
    /**
     * Helper method to validate date range.
     * In a real implementation, this would be part of the DTO or a validator class.
     */
    private boolean isValidDateRange(ApplicationFilterDTO dto) {
        if (dto.getStartDate() == null || dto.getEndDate() == null) {
            return true; // Null dates are valid
        }
        return !dto.getStartDate().isAfter(dto.getEndDate());
    }
    
    @Test
    @DisplayName("Should convert to Pageable correctly")
    void shouldConvertToPageableCorrectly() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setPage(2);
        dto.setSize(15);
        dto.setSortBy("status");
        dto.setSortDirection("asc");
        
        // When
        Pageable pageable = dto.toPageable();
        
        // Then
        assertEquals(2, pageable.getPageNumber(), "Page number should match");
        assertEquals(15, pageable.getPageSize(), "Page size should match");
        assertEquals(Sort.Direction.ASC, pageable.getSort().getOrderFor("status").getDirection(), 
                "Sort direction should match");
        assertEquals("status", pageable.getSort().getOrderFor("status").getProperty(), 
                "Sort property should match");
    }
    
    @Test
    @DisplayName("Should convert to Pageable with default values")
    void shouldConvertToPageableWithDefaultValues() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        
        // When
        Pageable pageable = dto.toPageable();
        
        // Then
        assertEquals(0, pageable.getPageNumber(), "Default page number should be 0");
        assertEquals(10, pageable.getPageSize(), "Default page size should be 10");
        assertEquals(Sort.Direction.DESC, pageable.getSort().getOrderFor("createdAt").getDirection(), 
                "Default sort direction should be DESC");
        assertEquals("createdAt", pageable.getSort().getOrderFor("createdAt").getProperty(), 
                "Default sort property should be createdAt");
    }
    
    @Test
    @DisplayName("Should convert to Specification with status filter")
    void shouldConvertToSpecificationWithStatusFilter() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setStatus(ApplicationStatus.APPROVED);
        
        // When
        Specification<?> spec = dto.toSpecification();
        
        // Then
        assertNotNull(spec, "Specification should not be null");
        
        // Mock the JPA criteria API components to test the specification
        Root<?> root = mock(Root.class);
        CriteriaQuery<?> query = mock(CriteriaQuery.class);
        CriteriaBuilder cb = mock(CriteriaBuilder.class);
        
        // Mock the path for status
        javax.persistence.criteria.Path<Object> statusPath = mock(javax.persistence.criteria.Path.class);
        when(root.get("status")).thenReturn(statusPath);
        
        // Mock the equal predicate
        Predicate statusPredicate = mock(Predicate.class);
        when(cb.equal(statusPath, ApplicationStatus.APPROVED)).thenReturn(statusPredicate);
        
        // Mock the and predicate
        Predicate andPredicate = mock(Predicate.class);
        when(cb.and(any(Predicate[].class))).thenReturn(andPredicate);
        
        // Apply the specification
        Predicate result = spec.toPredicate(root, query, cb);
        
        // Verify the interactions
        verify(root).get("status");
        verify(cb).equal(statusPath, ApplicationStatus.APPROVED);
        verify(cb).and(any(Predicate[].class));
    }
    
    @Test
    @DisplayName("Should convert to Specification with review status filter")
    void shouldConvertToSpecificationWithReviewStatusFilter() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setReviewStatus(ReviewStatus.IN_REVIEW);
        
        // When
        Specification<?> spec = dto.toSpecification();
        
        // Then
        assertNotNull(spec, "Specification should not be null");
        
        // Mock the JPA criteria API components to test the specification
        Root<?> root = mock(Root.class);
        CriteriaQuery<?> query = mock(CriteriaQuery.class);
        CriteriaBuilder cb = mock(CriteriaBuilder.class);
        
        // Mock the path for reviewStatus
        javax.persistence.criteria.Path<Object> reviewStatusPath = mock(javax.persistence.criteria.Path.class);
        when(root.get("reviewStatus")).thenReturn(reviewStatusPath);
        
        // Mock the equal predicate
        Predicate reviewStatusPredicate = mock(Predicate.class);
        when(cb.equal(reviewStatusPath, ReviewStatus.IN_REVIEW)).thenReturn(reviewStatusPredicate);
        
        // Mock the and predicate
        Predicate andPredicate = mock(Predicate.class);
        when(cb.and(any(Predicate[].class))).thenReturn(andPredicate);
        
        // Apply the specification
        Predicate result = spec.toPredicate(root, query, cb);
        
        // Verify the interactions
        verify(root).get("reviewStatus");
        verify(cb).equal(reviewStatusPath, ReviewStatus.IN_REVIEW);
        verify(cb).and(any(Predicate[].class));
    }
    
    @Test
    @DisplayName("Should convert to Specification with date range filter")
    void shouldConvertToSpecificationWithDateRangeFilter() {
        // Given
        LocalDate startDate = LocalDate.now().minusDays(7);
        LocalDate endDate = LocalDate.now();
        
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setStartDate(startDate);
        dto.setEndDate(endDate);
        
        // When
        Specification<?> spec = dto.toSpecification();
        
        // Then
        assertNotNull(spec, "Specification should not be null");
        
        // Mock the JPA criteria API components to test the specification
        Root<?> root = mock(Root.class);
        CriteriaQuery<?> query = mock(CriteriaQuery.class);
        CriteriaBuilder cb = mock(CriteriaBuilder.class);
        
        // Mock the path for createdAt
        javax.persistence.criteria.Path<Object> createdAtPath = mock(javax.persistence.criteria.Path.class);
        when(root.get("createdAt")).thenReturn(createdAtPath);
        
        // Mock the date predicates
        LocalDateTime startDateTime = startDate.atStartOfDay();
        LocalDateTime endDateTime = endDate.atTime(LocalTime.MAX);
        
        Predicate startDatePredicate = mock(Predicate.class);
        when(cb.greaterThanOrEqualTo(eq(createdAtPath), eq(startDateTime))).thenReturn(startDatePredicate);
        
        Predicate endDatePredicate = mock(Predicate.class);
        when(cb.lessThanOrEqualTo(eq(createdAtPath), eq(endDateTime))).thenReturn(endDatePredicate);
        
        // Mock the and predicate
        Predicate andPredicate = mock(Predicate.class);
        when(cb.and(any(Predicate[].class))).thenReturn(andPredicate);
        
        // Apply the specification
        Predicate result = spec.toPredicate(root, query, cb);
        
        // Verify the interactions
        verify(root, times(2)).get("createdAt");
        verify(cb).greaterThanOrEqualTo(eq(createdAtPath), eq(startDateTime));
        verify(cb).lessThanOrEqualTo(eq(createdAtPath), eq(endDateTime));
        verify(cb).and(any(Predicate[].class));
    }
    
    @Test
    @DisplayName("Should convert to Specification with merchant name filter")
    void shouldConvertToSpecificationWithMerchantNameFilter() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setMerchantName("Test Merchant");
        
        // When
        Specification<?> spec = dto.toSpecification();
        
        // Then
        assertNotNull(spec, "Specification should not be null");
        
        // Mock the JPA criteria API components to test the specification
        Root<?> root = mock(Root.class);
        CriteriaQuery<?> query = mock(CriteriaQuery.class);
        CriteriaBuilder cb = mock(CriteriaBuilder.class);
        
        // Mock the join for merchantDetails
        javax.persistence.criteria.Join<Object, Object> merchantJoin = mock(javax.persistence.criteria.Join.class);
        when(root.join("merchantDetails")).thenReturn(merchantJoin);
        
        // Mock the paths for merchant name fields
        javax.persistence.criteria.Path<String> legalNamePath = mock(javax.persistence.criteria.Path.class);
        javax.persistence.criteria.Path<String> dbaNamePath = mock(javax.persistence.criteria.Path.class);
        when(merchantJoin.get("legalName")).thenReturn(legalNamePath);
        when(merchantJoin.get("dbaName")).thenReturn(dbaNamePath);
        
        // Mock the lower expressions
        javax.persistence.criteria.Expression<String> lowerLegalName = mock(javax.persistence.criteria.Expression.class);
        javax.persistence.criteria.Expression<String> lowerDbaName = mock(javax.persistence.criteria.Expression.class);
        when(cb.lower(legalNamePath)).thenReturn(lowerLegalName);
        when(cb.lower(dbaNamePath)).thenReturn(lowerDbaName);
        
        // Mock the like predicates
        Predicate legalNamePredicate = mock(Predicate.class);
        Predicate dbaNamePredicate = mock(Predicate.class);
        when(cb.like(lowerLegalName, "%test merchant%")).thenReturn(legalNamePredicate);
        when(cb.like(lowerDbaName, "%test merchant%")).thenReturn(dbaNamePredicate);
        
        // Mock the or predicate
        Predicate orPredicate = mock(Predicate.class);
        when(cb.or(legalNamePredicate, dbaNamePredicate)).thenReturn(orPredicate);
        
        // Mock the and predicate
        Predicate andPredicate = mock(Predicate.class);
        when(cb.and(any(Predicate[].class))).thenReturn(andPredicate);
        
        // Apply the specification
        Predicate result = spec.toPredicate(root, query, cb);
        
        // Verify the interactions
        verify(root).join("merchantDetails");
        verify(merchantJoin).get("legalName");
        verify(merchantJoin).get("dbaName");
        verify(cb).lower(legalNamePath);
        verify(cb).lower(dbaNamePath);
        verify(cb).like(lowerLegalName, "%test merchant%");
        verify(cb).like(lowerDbaName, "%test merchant%");
        verify(cb).or(any(Predicate.class), any(Predicate.class));
        verify(cb).and(any(Predicate[].class));
    }
    
    @Test
    @DisplayName("Should convert to Specification with search term filter")
    void shouldConvertToSpecificationWithSearchTermFilter() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setSearchTerm("test search");
        
        // When
        Specification<?> spec = dto.toSpecification();
        
        // Then
        assertNotNull(spec, "Specification should not be null");
        
        // Mock the JPA criteria API components to test the specification
        Root<?> root = mock(Root.class);
        CriteriaQuery<?> query = mock(CriteriaQuery.class);
        CriteriaBuilder cb = mock(CriteriaBuilder.class);
        
        // Mock the join for merchantDetails
        javax.persistence.criteria.Join<Object, Object> merchantJoin = mock(javax.persistence.criteria.Join.class);
        when(root.join(eq("merchantDetails"), any())).thenReturn(merchantJoin);
        
        // Mock the paths for search fields
        javax.persistence.criteria.Path<Object> idPath = mock(javax.persistence.criteria.Path.class);
        javax.persistence.criteria.Path<String> legalNamePath = mock(javax.persistence.criteria.Path.class);
        javax.persistence.criteria.Path<String> dbaNamePath = mock(javax.persistence.criteria.Path.class);
        javax.persistence.criteria.Path<String> einPath = mock(javax.persistence.criteria.Path.class);
        javax.persistence.criteria.Path<String> industryPath = mock(javax.persistence.criteria.Path.class);
        
        when(root.get("id")).thenReturn(idPath);
        when(merchantJoin.get("legalName")).thenReturn(legalNamePath);
        when(merchantJoin.get("dbaName")).thenReturn(dbaNamePath);
        when(merchantJoin.get("ein")).thenReturn(einPath);
        when(merchantJoin.get("industry")).thenReturn(industryPath);
        
        // Mock the as method for id
        javax.persistence.criteria.Expression<String> idAsString = mock(javax.persistence.criteria.Expression.class);
        when(idPath.as(String.class)).thenReturn(idAsString);
        
        // Mock the lower expressions
        javax.persistence.criteria.Expression<String> lowerIdAsString = mock(javax.persistence.criteria.Expression.class);
        javax.persistence.criteria.Expression<String> lowerLegalName = mock(javax.persistence.criteria.Expression.class);
        javax.persistence.criteria.Expression<String> lowerDbaName = mock(javax.persistence.criteria.Expression.class);
        javax.persistence.criteria.Expression<String> lowerEin = mock(javax.persistence.criteria.Expression.class);
        javax.persistence.criteria.Expression<String> lowerIndustry = mock(javax.persistence.criteria.Expression.class);
        
        when(cb.lower(idAsString)).thenReturn(lowerIdAsString);
        when(cb.lower(legalNamePath)).thenReturn(lowerLegalName);
        when(cb.lower(dbaNamePath)).thenReturn(lowerDbaName);
        when(cb.lower(einPath)).thenReturn(lowerEin);
        when(cb.lower(industryPath)).thenReturn(lowerIndustry);
        
        // Mock the like predicates
        Predicate idPredicate = mock(Predicate.class);
        Predicate legalNamePredicate = mock(Predicate.class);
        Predicate dbaNamePredicate = mock(Predicate.class);
        Predicate einPredicate = mock(Predicate.class);
        Predicate industryPredicate = mock(Predicate.class);
        
        when(cb.like(lowerIdAsString, "%test search%")).thenReturn(idPredicate);
        when(cb.like(lowerLegalName, "%test search%")).thenReturn(legalNamePredicate);
        when(cb.like(lowerDbaName, "%test search%")).thenReturn(dbaNamePredicate);
        when(cb.like(lowerEin, "%test search%")).thenReturn(einPredicate);
        when(cb.like(lowerIndustry, "%test search%")).thenReturn(industryPredicate);
        
        // Mock the or predicate
        Predicate orPredicate = mock(Predicate.class);
        when(cb.or(any(Predicate[].class))).thenReturn(orPredicate);
        
        // Mock the and predicate
        Predicate andPredicate = mock(Predicate.class);
        when(cb.and(any(Predicate[].class))).thenReturn(andPredicate);
        
        // Apply the specification
        Predicate result = spec.toPredicate(root, query, cb);
        
        // Verify the interactions
        verify(root).join(eq("merchantDetails"), any());
        verify(root).get("id");
        verify(merchantJoin).get("legalName");
        verify(merchantJoin).get("dbaName");
        verify(merchantJoin).get("ein");
        verify(merchantJoin).get("industry");
        verify(cb).or(any(Predicate[].class));
        verify(cb).and(any(Predicate[].class));
    }
    
    @Test
    @DisplayName("Should serialize to JSON correctly")
    void shouldSerializeToJsonCorrectly() throws Exception {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setStatus(ApplicationStatus.PROCESSING);
        dto.setReviewStatus(ReviewStatus.IN_REVIEW);
        dto.setMerchantName("Test Merchant");
        dto.setStartDate(LocalDate.of(2023, 1, 1));
        dto.setEndDate(LocalDate.of(2023, 1, 31));
        dto.setSearchTerm("test search");
        dto.setPage(2);
        dto.setSize(15);
        dto.setSortBy("status");
        dto.setSortDirection("asc");
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertTrue(json.contains("\"status\":\"PROCESSING\""), "JSON should contain status field");
        assertTrue(json.contains("\"reviewStatus\":\"IN_REVIEW\""), "JSON should contain reviewStatus field");
        assertTrue(json.contains("\"merchantName\":\"Test Merchant\""), "JSON should contain merchantName field");
        assertTrue(json.contains("\"startDate\":\"2023-01-01\""), "JSON should contain startDate field");
        assertTrue(json.contains("\"endDate\":\"2023-01-31\""), "JSON should contain endDate field");
        assertTrue(json.contains("\"searchTerm\":\"test search\""), "JSON should contain searchTerm field");
        assertTrue(json.contains("\"page\":2"), "JSON should contain page field");
        assertTrue(json.contains("\"size\":15"), "JSON should contain size field");
        assertTrue(json.contains("\"sortBy\":\"status\""), "JSON should contain sortBy field");
        assertTrue(json.contains("\"sortDirection\":\"asc\""), "JSON should contain sortDirection field");
    }
    
    @Test
    @DisplayName("Should deserialize from JSON correctly")
    void shouldDeserializeFromJsonCorrectly() throws Exception {
        // Given
        String json = "{\"status\":\"PROCESSING\",\"reviewStatus\":\"IN_REVIEW\",\"merchantName\":\"Test Merchant\",\"startDate\":\"2023-01-01\",\"endDate\":\"2023-01-31\",\"searchTerm\":\"test search\",\"page\":2,\"size\":15,\"sortBy\":\"status\",\"sortDirection\":\"asc\"}";
        
        // When
        ApplicationFilterDTO dto = objectMapper.readValue(json, ApplicationFilterDTO.class);
        
        // Then
        assertEquals(ApplicationStatus.PROCESSING, dto.getStatus(), "Status should be deserialized correctly");
        assertEquals(ReviewStatus.IN_REVIEW, dto.getReviewStatus(), "Review status should be deserialized correctly");
        assertEquals("Test Merchant", dto.getMerchantName(), "Merchant name should be deserialized correctly");
        assertEquals(LocalDate.of(2023, 1, 1), dto.getStartDate(), "Start date should be deserialized correctly");
        assertEquals(LocalDate.of(2023, 1, 31), dto.getEndDate(), "End date should be deserialized correctly");
        assertEquals("test search", dto.getSearchTerm(), "Search term should be deserialized correctly");
        assertEquals(2, dto.getPage(), "Page should be deserialized correctly");
        assertEquals(15, dto.getSize(), "Size should be deserialized correctly");
        assertEquals("status", dto.getSortBy(), "Sort by should be deserialized correctly");
        assertEquals("asc", dto.getSortDirection(), "Sort direction should be deserialized correctly");
    }
    
    @Test
    @DisplayName("Should handle null values in JSON correctly")
    void shouldHandleNullValuesInJsonCorrectly() throws Exception {
        // Given
        String json = "{\"status\":null,\"reviewStatus\":null,\"merchantName\":null,\"startDate\":null,\"endDate\":null,\"searchTerm\":null,\"page\":null,\"size\":null,\"sortBy\":null,\"sortDirection\":null}";
        
        // When
        ApplicationFilterDTO dto = objectMapper.readValue(json, ApplicationFilterDTO.class);
        
        // Then
        assertNull(dto.getStatus(), "Status should be null");
        assertNull(dto.getReviewStatus(), "Review status should be null");
        assertNull(dto.getMerchantName(), "Merchant name should be null");
        assertNull(dto.getStartDate(), "Start date should be null");
        assertNull(dto.getEndDate(), "End date should be null");
        assertNull(dto.getSearchTerm(), "Search term should be null");
        assertEquals(0, dto.getPage(), "Page should default to 0");
        assertEquals(10, dto.getSize(), "Size should default to 10");
        assertEquals("createdAt", dto.getSortBy(), "Sort by should default to createdAt");
        assertEquals("desc", dto.getSortDirection(), "Sort direction should default to desc");
    }
    
    @Test
    @DisplayName("Should handle empty string values in JSON correctly")
    void shouldHandleEmptyStringValuesInJsonCorrectly() throws Exception {
        // Given
        String json = "{\"merchantName\":\"\",\"searchTerm\":\"\",\"sortBy\":\"\",\"sortDirection\":\"\"}";
        
        // When
        ApplicationFilterDTO dto = objectMapper.readValue(json, ApplicationFilterDTO.class);
        
        // Then
        assertEquals("", dto.getMerchantName(), "Merchant name should be empty string");
        assertEquals("", dto.getSearchTerm(), "Search term should be empty string");
        assertEquals("createdAt", dto.getSortBy(), "Sort by should default to createdAt for empty string");
        assertEquals("desc", dto.getSortDirection(), "Sort direction should default to desc for empty string");
    }
    
    @Test
    @DisplayName("Should handle toString method correctly")
    void shouldHandleToStringMethodCorrectly() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setStatus(ApplicationStatus.PROCESSING);
        dto.setReviewStatus(ReviewStatus.IN_REVIEW);
        dto.setMerchantName("Test Merchant");
        dto.setStartDate(LocalDate.of(2023, 1, 1));
        dto.setEndDate(LocalDate.of(2023, 1, 31));
        
        // When
        String toString = dto.toString();
        
        // Then
        assertTrue(toString.contains("status=PROCESSING"), "toString should contain status");
        assertTrue(toString.contains("reviewStatus=IN_REVIEW"), "toString should contain reviewStatus");
        assertTrue(toString.contains("merchantName='Test Merchant'"), "toString should contain merchantName");
        assertTrue(toString.contains("startDate=2023-01-01"), "toString should contain startDate");
        assertTrue(toString.contains("endDate=2023-01-31"), "toString should contain endDate");
    }
    
    @Test
    @DisplayName("Should handle edge case with empty merchant name for specification")
    void shouldHandleEdgeCaseWithEmptyMerchantNameForSpecification() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setMerchantName(""); // Empty string
        
        // When
        Specification<?> spec = dto.toSpecification();
        
        // Then
        assertNotNull(spec, "Specification should not be null");
        
        // Mock the JPA criteria API components to test the specification
        Root<?> root = mock(Root.class);
        CriteriaQuery<?> query = mock(CriteriaQuery.class);
        CriteriaBuilder cb = mock(CriteriaBuilder.class);
        
        // Mock the and predicate
        Predicate andPredicate = mock(Predicate.class);
        when(cb.and(any(Predicate[].class))).thenReturn(andPredicate);
        
        // Apply the specification
        Predicate result = spec.toPredicate(root, query, cb);
        
        // Verify the interactions - should not try to join merchantDetails for empty string
        verify(root, never()).join("merchantDetails");
        verify(cb).and(any(Predicate[].class));
    }
    
    @Test
    @DisplayName("Should handle edge case with empty search term for specification")
    void shouldHandleEdgeCaseWithEmptySearchTermForSpecification() {
        // Given
        ApplicationFilterDTO dto = new ApplicationFilterDTO();
        dto.setSearchTerm(""); // Empty string
        
        // When
        Specification<?> spec = dto.toSpecification();
        
        // Then
        assertNotNull(spec, "Specification should not be null");
        
        // Mock the JPA criteria API components to test the specification
        Root<?> root = mock(Root.class);
        CriteriaQuery<?> query = mock(CriteriaQuery.class);
        CriteriaBuilder cb = mock(CriteriaBuilder.class);
        
        // Mock the and predicate
        Predicate andPredicate = mock(Predicate.class);
        when(cb.and(any(Predicate[].class))).thenReturn(andPredicate);
        
        // Apply the specification
        Predicate result = spec.toPredicate(root, query, cb);
        
        // Verify the interactions - should not try to join merchantDetails for empty search term
        verify(root, never()).join(eq("merchantDetails"), any());
        verify(cb).and(any(Predicate[].class));
    }
}