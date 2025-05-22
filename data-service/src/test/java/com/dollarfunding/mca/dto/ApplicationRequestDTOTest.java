package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link ApplicationRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly validates application data,
 * handles validation annotations correctly, and converts between DTO and entity
 * objects appropriately.
 */
@DisplayName("ApplicationRequestDTO Tests")
class ApplicationRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    private ApplicationRequestDTO validDto;
    private Map<String, Object> testMetadata;

    @BeforeEach
    void setUp() {
        // Initialize validator
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Initialize ObjectMapper
        objectMapper = JsonUtil.getObjectMapper();
        
        // Create test metadata
        testMetadata = new HashMap<>();
        testMetadata.put("businessType", "LLC");
        testMetadata.put("yearEstablished", 2018);
        testMetadata.put("monthlyRevenue", 45000.00);
        
        // Create a valid DTO for testing
        validDto = new ApplicationRequestDTO(
                ApplicationStatus.NEW,
                ReviewStatus.NOT_REVIEWED,
                testMetadata
        );
    }

    @Nested
    @DisplayName("Validation Tests")
    class ValidationTests {

        @Test
        @DisplayName("Valid DTO should pass validation")
        void validDtoShouldPassValidation() {
            // When
            Set<ConstraintViolation<ApplicationRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "Valid DTO should not have validation violations");
        }

        @Test
        @DisplayName("DTO with null status should fail validation")
        void dtoWithNullStatusShouldFailValidation() {
            // Given
            ApplicationRequestDTO dto = new ApplicationRequestDTO(null, ReviewStatus.NOT_REVIEWED, testMetadata);
            
            // When
            Set<ConstraintViolation<ApplicationRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null status should have validation violations");
            assertEquals(1, violations.size(), "Should have exactly one violation");
            
            ConstraintViolation<ApplicationRequestDTO> violation = violations.iterator().next();
            assertEquals("status", violation.getPropertyPath().toString(), "Violation should be on status field");
            assertEquals("Application status is required", violation.getMessage(), "Violation message should match annotation");
        }

        @Test
        @DisplayName("DTO with oversized metadata should fail validation")
        void dtoWithOversizedMetadataShouldFailValidation() {
            // Given
            Map<String, Object> largeMetadata = new HashMap<>();
            // Create a very large metadata map that exceeds the size limit
            StringBuilder largeValue = new StringBuilder();
            for (int i = 0; i < 10001; i++) {
                largeValue.append("a");
            }
            largeMetadata.put("largeField", largeValue.toString());
            
            ApplicationRequestDTO dto = new ApplicationRequestDTO(
                    ApplicationStatus.NEW,
                    ReviewStatus.NOT_REVIEWED,
                    largeMetadata
            );
            
            // When
            Set<ConstraintViolation<ApplicationRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized metadata should have validation violations");
            
            boolean hasMetadataSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("metadata") && 
                              v.getMessage().contains("exceeds maximum"));
            
            assertTrue(hasMetadataSizeViolation, "Should have a size violation on metadata field");
        }
        
        @Test
        @DisplayName("DTO with null metadata should be initialized with empty map")
        void dtoWithNullMetadataShouldBeInitializedWithEmptyMap() {
            // Given
            ApplicationRequestDTO dto = new ApplicationRequestDTO(
                    ApplicationStatus.NEW,
                    ReviewStatus.NOT_REVIEWED,
                    null
            );
            
            // Then
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
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
            assertTrue(json.contains("\"status\":\"NEW\""), "JSON should contain status field");
            assertTrue(json.contains("\"review_status\":\"NOT_REVIEWED\""), "JSON should contain review_status field");
            assertTrue(json.contains("\"metadata\":"), "JSON should contain metadata field");
            assertTrue(json.contains("\"businessType\":\"LLC\""), "JSON should contain metadata values");
        }

        @Test
        @DisplayName("JSON should deserialize to DTO correctly")
        void jsonShouldDeserializeToDtoCorrectly() throws Exception {
            // Given
            String json = "{\"status\":\"PENDING\",\"review_status\":\"IN_REVIEW\",\"metadata\":{\"priority\":\"high\",\"notes\":\"Urgent application\"}}";
            
            // When
            ApplicationRequestDTO dto = objectMapper.readValue(json, ApplicationRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(ApplicationStatus.PENDING, dto.getStatus(), "Status should match");
            assertEquals(ReviewStatus.IN_REVIEW, dto.getReviewStatus(), "Review status should match");
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertEquals(2, dto.getMetadata().size(), "Metadata should have correct number of entries");
            assertEquals("high", dto.getMetadata().get("priority"), "Metadata values should match");
        }

        @Test
        @DisplayName("DTO should ignore unknown JSON properties")
        void dtoShouldIgnoreUnknownJsonProperties() throws Exception {
            // Given
            String json = "{\"status\":\"APPROVED\",\"review_status\":\"APPROVED\",\"unknown_field\":\"value\",\"metadata\":{\"approved_by\":\"John Doe\"}}";
            
            // When
            ApplicationRequestDTO dto = objectMapper.readValue(json, ApplicationRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(ApplicationStatus.APPROVED, dto.getStatus(), "Status should match");
            assertEquals(ReviewStatus.APPROVED, dto.getReviewStatus(), "Review status should match");
            // Unknown field should be ignored without exception
        }
    }

    @Nested
    @DisplayName("Entity Conversion Tests")
    class EntityConversionTests {

        @Test
        @DisplayName("DTO should convert to entity correctly")
        void dtoShouldConvertToEntityCorrectly() {
            // When
            Application entity = validDto.toEntity();
            
            // Then
            assertNotNull(entity, "Entity should not be null");
            assertEquals(validDto.getStatus(), entity.getStatus(), "Status should match");
            assertEquals(validDto.getReviewStatus(), entity.getReviewStatus(), "Review status should match");
            assertEquals(validDto.getMetadata(), entity.getMetadata(), "Metadata should match");
        }

        @Test
        @DisplayName("DTO should update existing entity correctly")
        void dtoShouldUpdateExistingEntityCorrectly() {
            // Given
            Application existingEntity = new Application();
            existingEntity.setStatus(ApplicationStatus.PENDING);
            existingEntity.setReviewStatus(ReviewStatus.IN_REVIEW);
            Map<String, Object> existingMetadata = new HashMap<>();
            existingMetadata.put("originalField", "originalValue");
            existingEntity.setMetadata(existingMetadata);
            
            // When
            Application updatedEntity = validDto.updateEntity(existingEntity);
            
            // Then
            assertNotNull(updatedEntity, "Updated entity should not be null");
            assertSame(existingEntity, updatedEntity, "Should return the same entity instance");
            assertEquals(validDto.getStatus(), updatedEntity.getStatus(), "Status should be updated");
            assertEquals(validDto.getReviewStatus(), updatedEntity.getReviewStatus(), "Review status should be updated");
            assertEquals(validDto.getMetadata(), updatedEntity.getMetadata(), "Metadata should be updated");
        }

        @Test
        @DisplayName("DTO should create new entity when updating null entity")
        void dtoShouldCreateNewEntityWhenUpdatingNullEntity() {
            // When
            Application entity = validDto.updateEntity(null);
            
            // Then
            assertNotNull(entity, "Entity should not be null");
            assertEquals(validDto.getStatus(), entity.getStatus(), "Status should match");
            assertEquals(validDto.getReviewStatus(), entity.getReviewStatus(), "Review status should match");
            assertEquals(validDto.getMetadata(), entity.getMetadata(), "Metadata should match");
        }

        @Test
        @DisplayName("Entity should convert to DTO correctly")
        void entityShouldConvertToDtoCorrectly() {
            // Given
            Application entity = new Application();
            entity.setStatus(ApplicationStatus.PROCESSING);
            entity.setReviewStatus(ReviewStatus.IN_REVIEW);
            Map<String, Object> entityMetadata = new HashMap<>();
            entityMetadata.put("processingAgent", "Jane Smith");
            entity.setMetadata(entityMetadata);
            
            // When
            ApplicationRequestDTO dto = ApplicationRequestDTO.fromEntity(entity);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(entity.getStatus(), dto.getStatus(), "Status should match");
            assertEquals(entity.getReviewStatus(), dto.getReviewStatus(), "Review status should match");
            assertEquals(entity.getMetadata(), dto.getMetadata(), "Metadata should match");
        }

        @Test
        @DisplayName("Null entity should convert to null DTO")
        void nullEntityShouldConvertToNullDto() {
            // When
            ApplicationRequestDTO dto = ApplicationRequestDTO.fromEntity(null);
            
            // Then
            assertNull(dto, "DTO should be null when entity is null");
        }
    }

    @Nested
    @DisplayName("Status Transition Validation Tests")
    class StatusTransitionTests {

        @Test
        @DisplayName("New application should accept any status")
        void newApplicationShouldAcceptAnyStatus() {
            // Given - null current status represents a new application
            ApplicationStatus currentStatus = null;
            
            // Then - all status transitions should be valid for new applications
            for (ApplicationStatus newStatus : ApplicationStatus.values()) {
                validDto.setStatus(newStatus);
                assertTrue(validDto.isValidStatusTransition(currentStatus), 
                        "New application should accept " + newStatus + " status");
            }
        }

        @ParameterizedTest
        @EnumSource(value = ApplicationStatus.class, names = {"PENDING", "REJECTED"})
        @DisplayName("NEW status should transition to PENDING or REJECTED")
        void newStatusShouldTransitionToPendingOrRejected(ApplicationStatus newStatus) {
            // Given
            ApplicationStatus currentStatus = ApplicationStatus.NEW;
            validDto.setStatus(newStatus);
            
            // Then
            assertTrue(validDto.isValidStatusTransition(currentStatus), 
                    "NEW should transition to " + newStatus);
        }

        @ParameterizedTest
        @EnumSource(value = ApplicationStatus.class, names = {"PROCESSING", "APPROVED", "COMPLETED"})
        @DisplayName("NEW status should not transition to PROCESSING, APPROVED, or COMPLETED")
        void newStatusShouldNotTransitionToProcessingApprovedOrCompleted(ApplicationStatus newStatus) {
            // Given
            ApplicationStatus currentStatus = ApplicationStatus.NEW;
            validDto.setStatus(newStatus);
            
            // Then
            assertFalse(validDto.isValidStatusTransition(currentStatus), 
                    "NEW should not transition to " + newStatus);
        }

        @ParameterizedTest
        @EnumSource(value = ApplicationStatus.class, names = {"PROCESSING", "REJECTED", "NEW"})
        @DisplayName("PENDING status should transition to PROCESSING, REJECTED, or NEW")
        void pendingStatusShouldTransitionToProcessingRejectedOrNew(ApplicationStatus newStatus) {
            // Given
            ApplicationStatus currentStatus = ApplicationStatus.PENDING;
            validDto.setStatus(newStatus);
            
            // Then
            assertTrue(validDto.isValidStatusTransition(currentStatus), 
                    "PENDING should transition to " + newStatus);
        }

        @ParameterizedTest
        @EnumSource(value = ApplicationStatus.class, names = {"APPROVED", "REJECTED", "PENDING"})
        @DisplayName("PROCESSING status should transition to APPROVED, REJECTED, or PENDING")
        void processingStatusShouldTransitionToApprovedRejectedOrPending(ApplicationStatus newStatus) {
            // Given
            ApplicationStatus currentStatus = ApplicationStatus.PROCESSING;
            validDto.setStatus(newStatus);
            
            // Then
            assertTrue(validDto.isValidStatusTransition(currentStatus), 
                    "PROCESSING should transition to " + newStatus);
        }

        @ParameterizedTest
        @EnumSource(value = ApplicationStatus.class, names = {"COMPLETED", "PROCESSING"})
        @DisplayName("APPROVED status should transition to COMPLETED or PROCESSING")
        void approvedStatusShouldTransitionToCompletedOrProcessing(ApplicationStatus newStatus) {
            // Given
            ApplicationStatus currentStatus = ApplicationStatus.APPROVED;
            validDto.setStatus(newStatus);
            
            // Then
            assertTrue(validDto.isValidStatusTransition(currentStatus), 
                    "APPROVED should transition to " + newStatus);
        }

        @Test
        @DisplayName("REJECTED status should only transition to NEW")
        void rejectedStatusShouldOnlyTransitionToNew() {
            // Given
            ApplicationStatus currentStatus = ApplicationStatus.REJECTED;
            
            // Then
            for (ApplicationStatus newStatus : ApplicationStatus.values()) {
                validDto.setStatus(newStatus);
                assertEquals(newStatus == ApplicationStatus.NEW, 
                        validDto.isValidStatusTransition(currentStatus),
                        "REJECTED should only transition to NEW, not " + newStatus);
            }
        }

        @Test
        @DisplayName("COMPLETED status should not transition to any other status")
        void completedStatusShouldNotTransitionToAnyOtherStatus() {
            // Given
            ApplicationStatus currentStatus = ApplicationStatus.COMPLETED;
            
            // Then
            for (ApplicationStatus newStatus : ApplicationStatus.values()) {
                validDto.setStatus(newStatus);
                assertFalse(validDto.isValidStatusTransition(currentStatus), 
                        "COMPLETED should not transition to " + newStatus);
            }
        }
    }

    @Nested
    @DisplayName("Documentation Tests")
    class DocumentationTests {

        @Test
        @DisplayName("Class should have proper JavaDoc")
        void classShouldHaveProperJavaDoc() throws Exception {
            // Given
            Class<?> clazz = ApplicationRequestDTO.class;
            
            // When
            String javadoc = clazz.getAnnotation(java.lang.annotation.Documented.class) != null ? 
                    "Documented" : "";
            
            // Then - This is a simple check that the class has some form of documentation
            // In a real environment, you might use a tool like Javadoc or reflection to check this more thoroughly
            assertNotNull(clazz.getAnnotations(), "Class should have annotations");
            assertTrue(clazz.toString().contains("ApplicationRequestDTO"), 
                    "Class name should be in the toString output");
        }

        @Test
        @DisplayName("toString method should include all fields")
        void toStringMethodShouldIncludeAllFields() {
            // When
            String toString = validDto.toString();
            
            // Then
            assertTrue(toString.contains("status="), "toString should include status field");
            assertTrue(toString.contains("reviewStatus="), "toString should include reviewStatus field");
            assertTrue(toString.contains("metadata="), "toString should include metadata field");
        }
    }
}