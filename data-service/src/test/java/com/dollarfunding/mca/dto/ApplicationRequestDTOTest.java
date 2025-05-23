package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.TestUtils;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link ApplicationRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly validates application data,
 * handles validation annotations correctly, and converts between DTO and entity
 * objects appropriately.
 */
@DisplayName("Application Request DTO Tests")
public class ApplicationRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    
    @BeforeEach
    void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        objectMapper = new ObjectMapper();
    }
    
    /**
     * Test data provider for invalid status values.
     */
    static Stream<Arguments> invalidStatusProvider() {
        return Stream.of(
            Arguments.of(null, "status", "Application status is required"),
            Arguments.of("", "status", "Application status is required"),
            Arguments.of("INVALID_STATUS", "status", null) // Will be caught by isValidStatus() method
        );
    }
    
    /**
     * Test data provider for invalid review status values.
     */
    static Stream<Arguments> invalidReviewStatusProvider() {
        return Stream.of(
            Arguments.of(null, "reviewStatus", "Review status is required"),
            Arguments.of("", "reviewStatus", "Review status is required"),
            Arguments.of("INVALID_REVIEW_STATUS", "reviewStatus", null) // Will be caught by isValidReviewStatus() method
        );
    }

    @Test
    @DisplayName("Should create a valid DTO with all required fields")
    void shouldCreateValidDTO() {
        // Given
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        // When
        Set<ConstraintViolation<ApplicationRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertTrue(violations.isEmpty(), "No validation violations should be present");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate required status field")
    @MethodSource("invalidStatusProvider")
    void shouldValidateRequiredStatusField(String status, String fieldName, String expectedMessage) {
        // Given
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(status)
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        // When
        Set<ConstraintViolation<ApplicationRequestDTO>> violations = validator.validate(dto);
        
        // Then
        if (expectedMessage != null) {
            assertFalse(violations.isEmpty(), "Validation violations should be present");
            ConstraintViolation<ApplicationRequestDTO> violation = violations.iterator().next();
            assertEquals(fieldName, violation.getPropertyPath().toString(), "Violation should be for the correct field");
            assertEquals(expectedMessage, violation.getMessage(), "Violation message should match expected");
        } else {
            // For INVALID_STATUS, the validation annotation passes but isValidStatus() should fail
            assertTrue(violations.isEmpty(), "No validation violations should be present from annotations");
            assertFalse(dto.isValidStatus(), "isValidStatus() should return false for invalid status");
        }
    }
    
    @ParameterizedTest
    @DisplayName("Should validate required review status field")
    @MethodSource("invalidReviewStatusProvider")
    void shouldValidateRequiredReviewStatusField(String reviewStatus, String fieldName, String expectedMessage) {
        // Given
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(reviewStatus)
                .build();
        
        // When
        Set<ConstraintViolation<ApplicationRequestDTO>> violations = validator.validate(dto);
        
        // Then
        if (expectedMessage != null) {
            assertFalse(violations.isEmpty(), "Validation violations should be present");
            ConstraintViolation<ApplicationRequestDTO> violation = violations.iterator().next();
            assertEquals(fieldName, violation.getPropertyPath().toString(), "Violation should be for the correct field");
            assertEquals(expectedMessage, violation.getMessage(), "Violation message should match expected");
        } else {
            // For INVALID_REVIEW_STATUS, the validation annotation passes but isValidReviewStatus() should fail
            assertTrue(violations.isEmpty(), "No validation violations should be present from annotations");
            assertFalse(dto.isValidReviewStatus(), "isValidReviewStatus() should return false for invalid review status");
        }
    }
    
    @Test
    @DisplayName("Should serialize to JSON correctly")
    void shouldSerializeToJsonCorrectly() throws Exception {
        // Given
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 95.5);
        
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.PROCESSING.name())
                .reviewStatus(ReviewStatus.IN_REVIEW.name())
                .metadata(metadata)
                .build();
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertTrue(json.contains("\"status\":\"PROCESSING\""), "JSON should contain status field");
        assertTrue(json.contains("\"review_status\":\"IN_REVIEW\""), "JSON should contain review_status field");
        assertTrue(json.contains("\"metadata\":"), "JSON should contain metadata field");
        assertTrue(json.contains("\"source\":\"email\""), "JSON should contain metadata source field");
        assertTrue(json.contains("\"confidence\":95.5"), "JSON should contain metadata confidence field");
    }
    
    @Test
    @DisplayName("Should deserialize from JSON correctly")
    void shouldDeserializeFromJsonCorrectly() throws Exception {
        // Given
        String json = "{\"status\":\"APPROVED\",\"review_status\":\"APPROVED\",\"metadata\":{\"source\":\"email\",\"confidence\":95.5}}";
        
        // When
        ApplicationRequestDTO dto = objectMapper.readValue(json, ApplicationRequestDTO.class);
        
        // Then
        assertEquals("APPROVED", dto.getStatus(), "Status should be deserialized correctly");
        assertEquals("APPROVED", dto.getReviewStatus(), "Review status should be deserialized correctly");
        assertNotNull(dto.getMetadata(), "Metadata should not be null");
        assertEquals("email", dto.getMetadataValue("source"), "Metadata source should be deserialized correctly");
        assertEquals(95.5, dto.getMetadataValue("confidence"), "Metadata confidence should be deserialized correctly");
    }
    
    @Test
    @DisplayName("Should convert to entity correctly")
    void shouldConvertToEntityCorrectly() {
        // Given
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 95.5);
        
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.PROCESSING.name())
                .reviewStatus(ReviewStatus.IN_REVIEW.name())
                .metadata(metadata)
                .build();
        
        // When
        Application entity = dto.toEntity();
        
        // Then
        assertEquals(ApplicationStatus.PROCESSING, entity.getStatus(), "Entity status should match DTO status");
        assertEquals(ReviewStatus.IN_REVIEW, entity.getReviewStatus(), "Entity review status should match DTO review status");
        assertNotNull(entity.getMetadata(), "Entity metadata should not be null");
        assertEquals("email", entity.getMetadataValue("source"), "Entity metadata source should match DTO");
        assertEquals(95.5, entity.getMetadataValue("confidence"), "Entity metadata confidence should match DTO");
        assertNotNull(entity.getCreatedAt(), "Entity created at should not be null");
        assertNotNull(entity.getUpdatedAt(), "Entity updated at should not be null");
    }
    
    @Test
    @DisplayName("Should throw exception when converting with invalid status")
    void shouldThrowExceptionWhenConvertingWithInvalidStatus() {
        // Given
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status("INVALID_STATUS")
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        // When/Then
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, dto::toEntity);
        assertEquals("Invalid application status: INVALID_STATUS", exception.getMessage());
    }
    
    @Test
    @DisplayName("Should throw exception when converting with invalid review status")
    void shouldThrowExceptionWhenConvertingWithInvalidReviewStatus() {
        // Given
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus("INVALID_REVIEW_STATUS")
                .build();
        
        // When/Then
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, dto::toEntity);
        assertEquals("Invalid review status: INVALID_REVIEW_STATUS", exception.getMessage());
    }
    
    @Test
    @DisplayName("Should update entity correctly")
    void shouldUpdateEntityCorrectly() {
        // Given
        Application entity = new Application(ApplicationStatus.NEW);
        entity.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        LocalDateTime originalCreatedAt = entity.getCreatedAt();
        LocalDateTime originalUpdatedAt = entity.getUpdatedAt();
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 95.5);
        
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.PROCESSING.name())
                .reviewStatus(ReviewStatus.IN_REVIEW.name())
                .metadata(metadata)
                .build();
        
        // When
        Application updatedEntity = dto.updateEntity(entity);
        
        // Then
        assertEquals(ApplicationStatus.PROCESSING, updatedEntity.getStatus(), "Entity status should be updated");
        assertEquals(ReviewStatus.IN_REVIEW, updatedEntity.getReviewStatus(), "Entity review status should be updated");
        assertNotNull(updatedEntity.getMetadata(), "Entity metadata should not be null");
        assertEquals("email", updatedEntity.getMetadataValue("source"), "Entity metadata source should be updated");
        assertEquals(95.5, updatedEntity.getMetadataValue("confidence"), "Entity metadata confidence should be updated");
        assertEquals(originalCreatedAt, updatedEntity.getCreatedAt(), "Entity created at should not change");
        assertNotEquals(originalUpdatedAt, updatedEntity.getUpdatedAt(), "Entity updated at should change");
    }
    
    @Test
    @DisplayName("Should throw exception when updating with invalid status transition")
    void shouldThrowExceptionWhenUpdatingWithInvalidStatusTransition() {
        // Given
        Application entity = new Application(ApplicationStatus.NEW);
        entity.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        
        // Try to transition directly from NEW to COMPLETED (invalid transition)
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.COMPLETED.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        // When/Then
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> dto.updateEntity(entity));
        assertTrue(exception.getMessage().contains("Invalid status transition"), 
                "Exception message should mention invalid status transition");
    }
    
    @Test
    @DisplayName("Should throw exception when updating with null entity")
    void shouldThrowExceptionWhenUpdatingWithNullEntity() {
        // Given
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.PROCESSING.name())
                .reviewStatus(ReviewStatus.IN_REVIEW.name())
                .build();
        
        // When/Then
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> dto.updateEntity(null));
        assertEquals("Entity cannot be null", exception.getMessage());
    }
    
    @Test
    @DisplayName("Should create DTO from entity correctly")
    void shouldCreateDtoFromEntityCorrectly() {
        // Given
        Application entity = new Application(ApplicationStatus.APPROVED);
        entity.setReviewStatus(ReviewStatus.APPROVED);
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 95.5);
        entity.setMetadata(metadata);
        
        // When
        ApplicationRequestDTO dto = ApplicationRequestDTO.fromEntity(entity);
        
        // Then
        assertEquals(ApplicationStatus.APPROVED.name(), dto.getStatus(), "DTO status should match entity status");
        assertEquals(ReviewStatus.APPROVED.name(), dto.getReviewStatus(), "DTO review status should match entity review status");
        assertNotNull(dto.getMetadata(), "DTO metadata should not be null");
        assertEquals("email", dto.getMetadataValue("source"), "DTO metadata source should match entity");
        assertEquals(95.5, dto.getMetadataValue("confidence"), "DTO metadata confidence should match entity");
    }
    
    @Test
    @DisplayName("Should return null when creating DTO from null entity")
    void shouldReturnNullWhenCreatingDtoFromNullEntity() {
        // When
        ApplicationRequestDTO dto = ApplicationRequestDTO.fromEntity(null);
        
        // Then
        assertNull(dto, "DTO should be null when entity is null");
    }
    
    @Test
    @DisplayName("Should validate status correctly")
    void shouldValidateStatusCorrectly() {
        // Given
        ApplicationRequestDTO validDto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        ApplicationRequestDTO invalidDto = ApplicationRequestDTO.builder()
                .status("INVALID_STATUS")
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        ApplicationRequestDTO nullStatusDto = ApplicationRequestDTO.builder()
                .status(null)
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        // When/Then
        assertTrue(validDto.isValidStatus(), "Valid status should be validated as true");
        assertFalse(invalidDto.isValidStatus(), "Invalid status should be validated as false");
        assertFalse(nullStatusDto.isValidStatus(), "Null status should be validated as false");
    }
    
    @Test
    @DisplayName("Should validate review status correctly")
    void shouldValidateReviewStatusCorrectly() {
        // Given
        ApplicationRequestDTO validDto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        ApplicationRequestDTO invalidDto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus("INVALID_REVIEW_STATUS")
                .build();
        
        ApplicationRequestDTO nullReviewStatusDto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(null)
                .build();
        
        // When/Then
        assertTrue(validDto.isValidReviewStatus(), "Valid review status should be validated as true");
        assertFalse(invalidDto.isValidReviewStatus(), "Invalid review status should be validated as false");
        assertFalse(nullReviewStatusDto.isValidReviewStatus(), "Null review status should be validated as false");
    }
    
    @Test
    @DisplayName("Should get and add metadata correctly")
    void shouldGetAndAddMetadataCorrectly() {
        // Given
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .build();
        
        // When
        dto.addMetadata("key1", "value1");
        dto.addMetadata("key2", 123);
        
        // Then
        assertEquals("value1", dto.getMetadataValue("key1"), "Should get string metadata correctly");
        assertEquals(123, dto.getMetadataValue("key2"), "Should get integer metadata correctly");
        assertNull(dto.getMetadataValue("nonexistent"), "Should return null for nonexistent metadata");
        
        // When metadata is null
        ApplicationRequestDTO nullMetadataDto = new ApplicationRequestDTO();
        
        // Then
        assertNull(nullMetadataDto.getMetadataValue("key"), "Should return null when metadata is null");
        
        // When adding to null metadata
        nullMetadataDto.addMetadata("key", "value");
        
        // Then
        assertEquals("value", nullMetadataDto.getMetadataValue("key"), "Should initialize metadata when adding to null");
    }
    
    @Test
    @DisplayName("Should handle builder pattern correctly")
    void shouldHandleBuilderPatternCorrectly() {
        // Given/When
        ApplicationRequestDTO dto = ApplicationRequestDTO.builder()
                .status(ApplicationStatus.NEW.name())
                .reviewStatus(ReviewStatus.NOT_REVIEWED.name())
                .metadata(Map.of("key", "value"))
                .build();
        
        // Then
        assertEquals(ApplicationStatus.NEW.name(), dto.getStatus(), "Builder should set status correctly");
        assertEquals(ReviewStatus.NOT_REVIEWED.name(), dto.getReviewStatus(), "Builder should set review status correctly");
        assertEquals("value", dto.getMetadataValue("key"), "Builder should set metadata correctly");
    }
    
    @Test
    @DisplayName("Should handle lombok annotations correctly")
    void shouldHandleLombokAnnotationsCorrectly() {
        // Given
        ApplicationRequestDTO dto1 = new ApplicationRequestDTO();
        dto1.setStatus(ApplicationStatus.NEW.name());
        dto1.setReviewStatus(ReviewStatus.NOT_REVIEWED.name());
        dto1.setMetadata(Map.of("key", "value"));
        
        ApplicationRequestDTO dto2 = new ApplicationRequestDTO();
        dto2.setStatus(ApplicationStatus.NEW.name());
        dto2.setReviewStatus(ReviewStatus.NOT_REVIEWED.name());
        dto2.setMetadata(Map.of("key", "value"));
        
        ApplicationRequestDTO dto3 = new ApplicationRequestDTO();
        dto3.setStatus(ApplicationStatus.PROCESSING.name());
        dto3.setReviewStatus(ReviewStatus.NOT_REVIEWED.name());
        dto3.setMetadata(Map.of("key", "value"));
        
        // Then
        assertEquals(dto1, dto2, "Equal DTOs should be equal according to equals()");
        assertEquals(dto1.hashCode(), dto2.hashCode(), "Equal DTOs should have same hashCode()");
        assertNotEquals(dto1, dto3, "Different DTOs should not be equal");
        assertNotEquals(dto1.hashCode(), dto3.hashCode(), "Different DTOs should have different hashCodes()");
        
        // Test toString()
        String toString = dto1.toString();
        assertTrue(toString.contains("status=NEW"), "toString() should include status");
        assertTrue(toString.contains("reviewStatus=NOT_REVIEWED"), "toString() should include reviewStatus");
        assertTrue(toString.contains("metadata="), "toString() should include metadata");
    }
}