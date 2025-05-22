package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;

import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.Join;
import javax.persistence.criteria.Path;
import javax.persistence.criteria.Predicate;
import javax.persistence.criteria.Root;
import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.time.LocalDate;
import java.util.Set;

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
@DisplayName("ApplicationFilterDTO Tests")
class ApplicationFilterDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    private ApplicationFilterDTO validDto;

    @BeforeEach
    void setUp() {
        // Initialize validator
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Initialize ObjectMapper
        objectMapper = JsonUtil.getObjectMapper();
        
        // Create a valid DTO for testing
        validDto = ApplicationFilterDTO.builder()
                .status(ApplicationStatus.PROCESSING)
                .reviewStatus(ReviewStatus.IN_REVIEW)
                .merchantName("Acme Corp")
                .createdFrom(LocalDate.now().minusDays(30))
                .createdTo(LocalDate.now())
                .minRevenue(10000.0)
                .maxRevenue(100000.0)
                .industry("Technology")
                .page(0)
                .size(20)
                .sort("createdAt")
                .direction("desc")
                .build();
    }

    @Nested
    @DisplayName("Validation Tests")
    class ValidationTests {

        @Test
        @DisplayName("Valid DTO should pass validation")
        void validDtoShouldPassValidation() {
            // When
            Set<ConstraintViolation<ApplicationFilterDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "Valid DTO should not have validation violations");
        }

        @Test
        @DisplayName("DTO with oversized merchant name should fail validation")
        void dtoWithOversizedMerchantNameShouldFailValidation() {
            // Given
            StringBuilder largeName = new StringBuilder();
            for (int i = 0; i < 256; i++) {
                largeName.append("a");
            }
            
            ApplicationFilterDTO dto = ApplicationFilterDTO.builder()
                    .merchantName(largeName.toString())
                    .build();
            
            // When
            Set<ConstraintViolation<ApplicationFilterDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized merchant name should have validation violations");
            
            boolean hasMerchantNameSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("merchantName") && 
                              v.getMessage().contains("cannot exceed 255 characters"));
            
            assertTrue(hasMerchantNameSizeViolation, "Should have a size violation on merchantName field");
        }

        @Test
        @DisplayName("DTO with oversized industry should fail validation")
        void dtoWithOversizedIndustryShouldFailValidation() {
            // Given
            StringBuilder largeIndustry = new StringBuilder();
            for (int i = 0; i < 101; i++) {
                largeIndustry.append("a");
            }
            
            ApplicationFilterDTO dto = ApplicationFilterDTO.builder()
                    .industry(largeIndustry.toString())
                    .build();
            
            // When
            Set<ConstraintViolation<ApplicationFilterDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized industry should have validation violations");
            
            boolean hasIndustrySizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("industry") && 
                              v.getMessage().contains("cannot exceed 100 characters"));
            
            assertTrue(hasIndustrySizeViolation, "Should have a size violation on industry field");
        }

        @Test
        @DisplayName("DTO with negative page should fail validation")
        void dtoWithNegativePageShouldFailValidation() {
            // Given
            ApplicationFilterDTO dto = ApplicationFilterDTO.builder()
                    .page(-1)
                    .build();
            
            // When
            Set<ConstraintViolation<ApplicationFilterDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with negative page should have validation violations");
            
            boolean hasPageMinViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("page") && 
                              v.getMessage().contains("cannot be negative"));
            
            assertTrue(hasPageMinViolation, "Should have a min violation on page field");
        }

        @Test
        @DisplayName("DTO with invalid size should fail validation")
        void dtoWithInvalidSizeShouldFailValidation() {
            // Test size < 1
            ApplicationFilterDTO dtoWithSmallSize = ApplicationFilterDTO.builder()
                    .size(0)
                    .build();
            
            Set<ConstraintViolation<ApplicationFilterDTO>> smallSizeViolations = validator.validate(dtoWithSmallSize);
            
            assertFalse(smallSizeViolations.isEmpty(), "DTO with size < 1 should have validation violations");
            
            boolean hasMinSizeViolation = smallSizeViolations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("size") && 
                              v.getMessage().contains("must be at least 1"));
            
            assertTrue(hasMinSizeViolation, "Should have a min violation on size field");
            
            // Test size > 100
            ApplicationFilterDTO dtoWithLargeSize = ApplicationFilterDTO.builder()
                    .size(101)
                    .build();
            
            Set<ConstraintViolation<ApplicationFilterDTO>> largeSizeViolations = validator.validate(dtoWithLargeSize);
            
            assertFalse(largeSizeViolations.isEmpty(), "DTO with size > 100 should have validation violations");
            
            boolean hasMaxSizeViolation = largeSizeViolations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("size") && 
                              v.getMessage().contains("cannot exceed 100"));
            
            assertTrue(hasMaxSizeViolation, "Should have a max violation on size field");
        }

        @Test
        @DisplayName("DTO with negative revenue values should fail validation")
        void dtoWithNegativeRevenueValuesShouldFailValidation() {
            // Test negative minRevenue
            ApplicationFilterDTO dtoWithNegativeMinRevenue = ApplicationFilterDTO.builder()
                    .minRevenue(-1.0)
                    .build();
            
            Set<ConstraintViolation<ApplicationFilterDTO>> minRevenueViolations = validator.validate(dtoWithNegativeMinRevenue);
            
            assertFalse(minRevenueViolations.isEmpty(), "DTO with negative minRevenue should have validation violations");
            
            boolean hasMinRevenueViolation = minRevenueViolations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("minRevenue") && 
                              v.getMessage().contains("cannot be negative"));
            
            assertTrue(hasMinRevenueViolation, "Should have a min violation on minRevenue field");
            
            // Test negative maxRevenue
            ApplicationFilterDTO dtoWithNegativeMaxRevenue = ApplicationFilterDTO.builder()
                    .maxRevenue(-1.0)
                    .build();
            
            Set<ConstraintViolation<ApplicationFilterDTO>> maxRevenueViolations = validator.validate(dtoWithNegativeMaxRevenue);
            
            assertFalse(maxRevenueViolations.isEmpty(), "DTO with negative maxRevenue should have validation violations");
            
            boolean hasMaxRevenueViolation = maxRevenueViolations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("maxRevenue") && 
                              v.getMessage().contains("cannot be negative"));
            
            assertTrue(hasMaxRevenueViolation, "Should have a min violation on maxRevenue field");
        }

        @Test
        @DisplayName("DTO with invalid date range should be valid but logically incorrect")
        void dtoWithInvalidDateRangeShouldBeValidButLogicallyIncorrect() {
            // Given - createdFrom after createdTo (validation annotations don't check this logic)
            ApplicationFilterDTO dto = ApplicationFilterDTO.builder()
                    .createdFrom(LocalDate.now())
                    .createdTo(LocalDate.now().minusDays(30))
                    .build();
            
            // When
            Set<ConstraintViolation<ApplicationFilterDTO>> violations = validator.validate(dto);
            
            // Then - should pass validation but be logically incorrect
            assertTrue(violations.isEmpty(), "DTO with invalid date range should pass bean validation");
            
            // Note: In a real application, this logical validation would typically be handled
            // in a service layer or custom validator, not in the bean validation annotations
        }
    }

    @Nested
    @DisplayName("JSON Serialization/Deserialization Tests")
    class JsonTests {

        @Test
        @DisplayName("DTO should serialize to JSON correctly")
        void dtoShouldSerializeToJsonCorrectly() throws Exception {
            // When
            String json = objectMapper.writeValueAsString(validDto);
            
            // Then
            assertNotNull(json, "JSON should not be null");
            assertTrue(json.contains("\"status\":\"PROCESSING\""), "JSON should contain status field");
            assertTrue(json.contains("\"reviewStatus\":\"IN_REVIEW\""), "JSON should contain reviewStatus field");
            assertTrue(json.contains("\"merchantName\":\"Acme Corp\""), "JSON should contain merchantName field");
            assertTrue(json.contains("\"minRevenue\":10000.0"), "JSON should contain minRevenue field");
            assertTrue(json.contains("\"maxRevenue\":100000.0"), "JSON should contain maxRevenue field");
            assertTrue(json.contains("\"industry\":\"Technology\""), "JSON should contain industry field");
            assertTrue(json.contains("\"page\":0"), "JSON should contain page field");
            assertTrue(json.contains("\"size\":20"), "JSON should contain size field");
            assertTrue(json.contains("\"sort\":\"createdAt\""), "JSON should contain sort field");
            assertTrue(json.contains("\"direction\":\"desc\""), "JSON should contain direction field");
            
            // Check date format
            String expectedDateFormat = validDto.getCreatedFrom().toString();
            assertTrue(json.contains("\"createdFrom\":\"" + expectedDateFormat + "\""), 
                    "JSON should contain createdFrom field in ISO format");
        }

        @Test
        @DisplayName("JSON should deserialize to DTO correctly")
        void jsonShouldDeserializeToDtoCorrectly() throws Exception {
            // Given
            String json = "{\"status\":\"APPROVED\",\"reviewStatus\":\"APPROVED\",\"merchantName\":\"XYZ Inc\"," +
                    "\"createdFrom\":\"2023-01-01\",\"createdTo\":\"2023-12-31\"," +
                    "\"minRevenue\":50000.0,\"maxRevenue\":500000.0,\"industry\":\"Retail\"," +
                    "\"page\":1,\"size\":50,\"sort\":\"status\",\"direction\":\"asc\"}"; 
            
            // When
            ApplicationFilterDTO dto = objectMapper.readValue(json, ApplicationFilterDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(ApplicationStatus.APPROVED, dto.getStatus(), "Status should match");
            assertEquals(ReviewStatus.APPROVED, dto.getReviewStatus(), "Review status should match");
            assertEquals("XYZ Inc", dto.getMerchantName(), "Merchant name should match");
            assertEquals(LocalDate.of(2023, 1, 1), dto.getCreatedFrom(), "Created from date should match");
            assertEquals(LocalDate.of(2023, 12, 31), dto.getCreatedTo(), "Created to date should match");
            assertEquals(50000.0, dto.getMinRevenue(), "Min revenue should match");
            assertEquals(500000.0, dto.getMaxRevenue(), "Max revenue should match");
            assertEquals("Retail", dto.getIndustry(), "Industry should match");
            assertEquals(1, dto.getPage(), "Page should match");
            assertEquals(50, dto.getSize(), "Size should match");
            assertEquals("status", dto.getSort(), "Sort should match");
            assertEquals("asc", dto.getDirection(), "Direction should match");
        }

        @Test
        @DisplayName("DTO should handle null values correctly during serialization")
        void dtoShouldHandleNullValuesCorrectlyDuringSerialization() throws Exception {
            // Given
            ApplicationFilterDTO dto = new ApplicationFilterDTO(); // All fields null except defaults
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertNotNull(json, "JSON should not be null");
            assertFalse(json.contains("\"status\":"), "JSON should not contain null status field");
            assertFalse(json.contains("\"reviewStatus\":"), "JSON should not contain null reviewStatus field");
            assertFalse(json.contains("\"merchantName\":"), "JSON should not contain null merchantName field");
            assertFalse(json.contains("\"createdFrom\":"), "JSON should not contain null createdFrom field");
            assertFalse(json.contains("\"createdTo\":"), "JSON should not contain null createdTo field");
            assertFalse(json.contains("\"minRevenue\":"), "JSON should not contain null minRevenue field");
            assertFalse(json.contains("\"maxRevenue\":"), "JSON should not contain null maxRevenue field");
            assertFalse(json.contains("\"industry\":"), "JSON should not contain null industry field");
            
            // Default values should be included
            assertTrue(json.contains("\"page\":0"), "JSON should contain default page field");
            assertTrue(json.contains("\"size\":20"), "JSON should contain default size field");
            assertTrue(json.contains("\"sort\":\"createdAt\""), "JSON should contain default sort field");
            assertTrue(json.contains("\"direction\":\"desc\""), "JSON should contain default direction field");
        }

        @Test
        @DisplayName("DTO should ignore unknown JSON properties")
        void dtoShouldIgnoreUnknownJsonProperties() throws Exception {
            // Given
            String json = "{\"status\":\"NEW\",\"unknown_field\":\"value\",\"page\":2}"; 
            
            // When
            ApplicationFilterDTO dto = objectMapper.readValue(json, ApplicationFilterDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(ApplicationStatus.NEW, dto.getStatus(), "Status should match");
            assertEquals(2, dto.getPage(), "Page should match");
            // Unknown field should be ignored without exception
        }

        @ParameterizedTest
        @ValueSource(strings = {"asc", "ASC", "desc", "DESC"})
        @DisplayName("DTO should handle different sort direction formats")
        void dtoShouldHandleDifferentSortDirectionFormats(String direction) throws Exception {
            // Given
            String json = "{\"direction\":\"" + direction + "\"}"; 
            
            // When
            ApplicationFilterDTO dto = objectMapper.readValue(json, ApplicationFilterDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertNotNull(dto.getDirection(), "Direction should not be null");
            // Direction should be normalized to lowercase in the DTO or handled correctly in toPageable()
        }
    }

    @Nested
    @DisplayName("Conversion Tests")
    class ConversionTests {

        @Test
        @DisplayName("DTO should convert to Pageable correctly")
        void dtoShouldConvertToPageableCorrectly() {
            // When
            Pageable pageable = validDto.toPageable();
            
            // Then
            assertNotNull(pageable, "Pageable should not be null");
            assertEquals(0, pageable.getPageNumber(), "Page number should match");
            assertEquals(20, pageable.getPageSize(), "Page size should match");
            assertEquals(Sort.Direction.DESC, pageable.getSort().getOrderFor("createdAt").getDirection(), 
                    "Sort direction should match");
            assertEquals("createdAt", pageable.getSort().getOrderFor("createdAt").getProperty(), 
                    "Sort property should match");
        }

        @Test
        @DisplayName("DTO with custom pagination should convert to Pageable correctly")
        void dtoWithCustomPaginationShouldConvertToPageableCorrectly() {
            // Given
            ApplicationFilterDTO dto = ApplicationFilterDTO.builder()
                    .page(2)
                    .size(50)
                    .sort("status")
                    .direction("asc")
                    .build();
            
            // When
            Pageable pageable = dto.toPageable();
            
            // Then
            assertNotNull(pageable, "Pageable should not be null");
            assertEquals(2, pageable.getPageNumber(), "Page number should match");
            assertEquals(50, pageable.getPageSize(), "Page size should match");
            assertEquals(Sort.Direction.ASC, pageable.getSort().getOrderFor("status").getDirection(), 
                    "Sort direction should match");
            assertEquals("status", pageable.getSort().getOrderFor("status").getProperty(), 
                    "Sort property should match");
        }

        @Test
        @DisplayName("DTO should convert to Specification correctly")
        void dtoShouldConvertToSpecificationCorrectly() {
            // Given
            // We need to mock the JPA infrastructure for testing Specification
            Root<?> root = mock(Root.class);
            CriteriaQuery<?> query = mock(CriteriaQuery.class);
            CriteriaBuilder cb = mock(CriteriaBuilder.class);
            Join<?, ?> merchantJoin = mock(Join.class);
            Path<?> statusPath = mock(Path.class);
            Path<?> reviewStatusPath = mock(Path.class);
            Path<?> createdAtPath = mock(Path.class);
            Path<?> legalNamePath = mock(Path.class);
            Path<?> dbaNamePath = mock(Path.class);
            Path<?> revenuePath = mock(Path.class);
            Path<?> industryPath = mock(Path.class);
            
            // Setup mocks
            when(root.get("status")).thenReturn(statusPath);
            when(root.get("reviewStatus")).thenReturn(reviewStatusPath);
            when(root.get("createdAt")).thenReturn(createdAtPath);
            when(createdAtPath.as(LocalDate.class)).thenReturn(createdAtPath);
            when(root.join("merchantDetails")).thenReturn(merchantJoin);
            when(merchantJoin.get("legalName")).thenReturn(legalNamePath);
            when(merchantJoin.get("dbaName")).thenReturn(dbaNamePath);
            when(merchantJoin.get("revenue")).thenReturn(revenuePath);
            when(merchantJoin.get("industry")).thenReturn(industryPath);
            
            // Mock predicates
            Predicate statusPredicate = mock(Predicate.class);
            Predicate reviewStatusPredicate = mock(Predicate.class);
            Predicate legalNamePredicate = mock(Predicate.class);
            Predicate dbaNamePredicate = mock(Predicate.class);
            Predicate merchantNamePredicate = mock(Predicate.class);
            Predicate createdFromPredicate = mock(Predicate.class);
            Predicate createdToPredicate = mock(Predicate.class);
            Predicate minRevenuePredicate = mock(Predicate.class);
            Predicate maxRevenuePredicate = mock(Predicate.class);
            Predicate industryPredicate = mock(Predicate.class);
            Predicate finalPredicate = mock(Predicate.class);
            
            when(cb.equal(statusPath, ApplicationStatus.PROCESSING)).thenReturn(statusPredicate);
            when(cb.equal(reviewStatusPath, ReviewStatus.IN_REVIEW)).thenReturn(reviewStatusPredicate);
            when(cb.lower(legalNamePath)).thenReturn(legalNamePath);
            when(cb.lower(dbaNamePath)).thenReturn(dbaNamePath);
            when(cb.like(legalNamePath, "%acme corp%")).thenReturn(legalNamePredicate);
            when(cb.like(dbaNamePath, "%acme corp%")).thenReturn(dbaNamePredicate);
            when(cb.or(legalNamePredicate, dbaNamePredicate)).thenReturn(merchantNamePredicate);
            when(cb.greaterThanOrEqualTo(createdAtPath, validDto.getCreatedFrom())).thenReturn(createdFromPredicate);
            when(cb.lessThanOrEqualTo(createdAtPath, validDto.getCreatedTo())).thenReturn(createdToPredicate);
            when(cb.greaterThanOrEqualTo(revenuePath, validDto.getMinRevenue())).thenReturn(minRevenuePredicate);
            when(cb.lessThanOrEqualTo(revenuePath, validDto.getMaxRevenue())).thenReturn(maxRevenuePredicate);
            when(cb.equal(industryPath, "Technology")).thenReturn(industryPredicate);
            
            // Mock final predicate
            Predicate[] predicates = {
                statusPredicate, reviewStatusPredicate, merchantNamePredicate,
                createdFromPredicate, createdToPredicate, minRevenuePredicate,
                maxRevenuePredicate, industryPredicate
            };
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            Specification<?> specification = validDto.toSpecification();
            Predicate result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions
            verify(root).get("status");
            verify(root).get("reviewStatus");
            verify(root).get("createdAt");
            verify(root).join("merchantDetails");
        }

        @Test
        @DisplayName("DTO with minimal filters should convert to Specification correctly")
        void dtoWithMinimalFiltersShouldConvertToSpecificationCorrectly() {
            // Given
            ApplicationFilterDTO dto = ApplicationFilterDTO.builder()
                    .status(ApplicationStatus.NEW)
                    .build();
            
            // Mock JPA infrastructure
            Root<?> root = mock(Root.class);
            CriteriaQuery<?> query = mock(CriteriaQuery.class);
            CriteriaBuilder cb = mock(CriteriaBuilder.class);
            Path<?> statusPath = mock(Path.class);
            Predicate statusPredicate = mock(Predicate.class);
            Predicate finalPredicate = mock(Predicate.class);
            
            when(root.get("status")).thenReturn(statusPath);
            when(cb.equal(statusPath, ApplicationStatus.NEW)).thenReturn(statusPredicate);
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            Specification<?> specification = dto.toSpecification();
            Predicate result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions
            verify(root).get("status");
            verify(cb).equal(statusPath, ApplicationStatus.NEW);
            verify(cb).and(any(Predicate[].class));
        }
    }

    @Nested
    @DisplayName("Edge Case Tests")
    class EdgeCaseTests {

        @Test
        @DisplayName("DTO with null values should handle conversion to Pageable correctly")
        void dtoWithNullValuesShouldHandleConversionToPageableCorrectly() {
            // Given
            ApplicationFilterDTO dto = new ApplicationFilterDTO(); // All fields null except defaults
            
            // When
            Pageable pageable = dto.toPageable();
            
            // Then
            assertNotNull(pageable, "Pageable should not be null");
            assertEquals(0, pageable.getPageNumber(), "Page number should match default");
            assertEquals(20, pageable.getPageSize(), "Page size should match default");
            assertEquals(Sort.Direction.DESC, pageable.getSort().getOrderFor("createdAt").getDirection(), 
                    "Sort direction should match default");
            assertEquals("createdAt", pageable.getSort().getOrderFor("createdAt").getProperty(), 
                    "Sort property should match default");
        }

        @Test
        @DisplayName("DTO with null values should handle conversion to Specification correctly")
        void dtoWithNullValuesShouldHandleConversionToSpecificationCorrectly() {
            // Given
            ApplicationFilterDTO dto = new ApplicationFilterDTO(); // All fields null except defaults
            
            // Mock JPA infrastructure
            Root<?> root = mock(Root.class);
            CriteriaQuery<?> query = mock(CriteriaQuery.class);
            CriteriaBuilder cb = mock(CriteriaBuilder.class);
            Predicate finalPredicate = mock(Predicate.class);
            
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            Specification<?> specification = dto.toSpecification();
            Predicate result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions - no filters should be applied
            verify(cb).and(any(Predicate[].class));
        }

        @Test
        @DisplayName("DTO with empty strings should handle conversion to Specification correctly")
        void dtoWithEmptyStringsShouldHandleConversionToSpecificationCorrectly() {
            // Given
            ApplicationFilterDTO dto = ApplicationFilterDTO.builder()
                    .merchantName("")
                    .industry("")
                    .build();
            
            // Mock JPA infrastructure
            Root<?> root = mock(Root.class);
            CriteriaQuery<?> query = mock(CriteriaQuery.class);
            CriteriaBuilder cb = mock(CriteriaBuilder.class);
            Predicate finalPredicate = mock(Predicate.class);
            
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            Specification<?> specification = dto.toSpecification();
            Predicate result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions - empty strings should be ignored
            verify(cb).and(any(Predicate[].class));
        }

        @Test
        @DisplayName("DTO with only one date in range should handle conversion to Specification correctly")
        void dtoWithOnlyOneDateInRangeShouldHandleConversionToSpecificationCorrectly() {
            // Given - only createdFrom
            ApplicationFilterDTO dtoWithFromOnly = ApplicationFilterDTO.builder()
                    .createdFrom(LocalDate.now().minusDays(30))
                    .build();
            
            // Mock JPA infrastructure
            Root<?> root = mock(Root.class);
            CriteriaQuery<?> query = mock(CriteriaQuery.class);
            CriteriaBuilder cb = mock(CriteriaBuilder.class);
            Path<?> createdAtPath = mock(Path.class);
            Predicate createdFromPredicate = mock(Predicate.class);
            Predicate finalPredicate = mock(Predicate.class);
            
            when(root.get("createdAt")).thenReturn(createdAtPath);
            when(createdAtPath.as(LocalDate.class)).thenReturn(createdAtPath);
            when(cb.greaterThanOrEqualTo(createdAtPath, dtoWithFromOnly.getCreatedFrom())).thenReturn(createdFromPredicate);
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            Specification<?> specification = dtoWithFromOnly.toSpecification();
            Predicate result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions - only createdFrom predicate should be applied
            verify(root).get("createdAt");
            verify(cb).greaterThanOrEqualTo(createdAtPath, dtoWithFromOnly.getCreatedFrom());
            verify(cb).and(any(Predicate[].class));
            
            // Given - only createdTo
            ApplicationFilterDTO dtoWithToOnly = ApplicationFilterDTO.builder()
                    .createdTo(LocalDate.now())
                    .build();
            
            // Reset mocks
            reset(root, cb, createdAtPath);
            Predicate createdToPredicate = mock(Predicate.class);
            
            when(root.get("createdAt")).thenReturn(createdAtPath);
            when(createdAtPath.as(LocalDate.class)).thenReturn(createdAtPath);
            when(cb.lessThanOrEqualTo(createdAtPath, dtoWithToOnly.getCreatedTo())).thenReturn(createdToPredicate);
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            specification = dtoWithToOnly.toSpecification();
            result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions - only createdTo predicate should be applied
            verify(root).get("createdAt");
            verify(cb).lessThanOrEqualTo(createdAtPath, dtoWithToOnly.getCreatedTo());
            verify(cb).and(any(Predicate[].class));
        }

        @Test
        @DisplayName("DTO with only one revenue value should handle conversion to Specification correctly")
        void dtoWithOnlyOneRevenueValueShouldHandleConversionToSpecificationCorrectly() {
            // Given - only minRevenue
            ApplicationFilterDTO dtoWithMinOnly = ApplicationFilterDTO.builder()
                    .minRevenue(10000.0)
                    .build();
            
            // Mock JPA infrastructure
            Root<?> root = mock(Root.class);
            CriteriaQuery<?> query = mock(CriteriaQuery.class);
            CriteriaBuilder cb = mock(CriteriaBuilder.class);
            Join<?, ?> merchantJoin = mock(Join.class);
            Path<?> revenuePath = mock(Path.class);
            Predicate minRevenuePredicate = mock(Predicate.class);
            Predicate finalPredicate = mock(Predicate.class);
            
            when(root.join("merchantDetails")).thenReturn(merchantJoin);
            when(merchantJoin.get("revenue")).thenReturn(revenuePath);
            when(cb.greaterThanOrEqualTo(revenuePath, dtoWithMinOnly.getMinRevenue())).thenReturn(minRevenuePredicate);
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            Specification<?> specification = dtoWithMinOnly.toSpecification();
            Predicate result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions - only minRevenue predicate should be applied
            verify(root).join("merchantDetails");
            verify(merchantJoin).get("revenue");
            verify(cb).greaterThanOrEqualTo(revenuePath, dtoWithMinOnly.getMinRevenue());
            verify(cb).and(any(Predicate[].class));
            
            // Given - only maxRevenue
            ApplicationFilterDTO dtoWithMaxOnly = ApplicationFilterDTO.builder()
                    .maxRevenue(100000.0)
                    .build();
            
            // Reset mocks
            reset(root, merchantJoin, cb, revenuePath);
            Predicate maxRevenuePredicate = mock(Predicate.class);
            
            when(root.join("merchantDetails")).thenReturn(merchantJoin);
            when(merchantJoin.get("revenue")).thenReturn(revenuePath);
            when(cb.lessThanOrEqualTo(revenuePath, dtoWithMaxOnly.getMaxRevenue())).thenReturn(maxRevenuePredicate);
            when(cb.and(any(Predicate[].class))).thenReturn(finalPredicate);
            
            // When
            specification = dtoWithMaxOnly.toSpecification();
            result = specification.toPredicate(root, query, cb);
            
            // Then
            assertNotNull(specification, "Specification should not be null");
            assertNotNull(result, "Predicate result should not be null");
            
            // Verify interactions - only maxRevenue predicate should be applied
            verify(root).join("merchantDetails");
            verify(merchantJoin).get("revenue");
            verify(cb).lessThanOrEqualTo(revenuePath, dtoWithMaxOnly.getMaxRevenue());
            verify(cb).and(any(Predicate[].class));
        }
    }
}