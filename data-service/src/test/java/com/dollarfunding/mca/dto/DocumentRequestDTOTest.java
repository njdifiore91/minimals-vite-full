package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.DocumentType;
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
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link DocumentRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and multipart file handling.
 * 
 * This test suite ensures that the DTO properly validates document uploads,
 * handles document classification metadata correctly, and supports multipart
 * file uploads appropriately.
 */
@DisplayName("Document Request DTO Tests")
public class DocumentRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    private UUID testApplicationId;
    
    @BeforeEach
    void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        objectMapper = new ObjectMapper();
        testApplicationId = UUID.randomUUID();
    }
    
    /**
     * Test data provider for invalid document request scenarios.
     */
    static Stream<Arguments> invalidDocumentRequestProvider() {
        return Stream.of(
            Arguments.of(null, DocumentType.BANK_STATEMENT, "applicationId", "Application ID is required"),
            Arguments.of(UUID.randomUUID(), null, "type", "Document type is required")
        );
    }
    
    /**
     * Test data provider for invalid content type values.
     */
    static Stream<Arguments> invalidContentTypeProvider() {
        return Stream.of(
            Arguments.of("invalid content type with spaces", "contentType", "Invalid content type format"),
            Arguments.of("invalid@content#type", "contentType", "Invalid content type format")
        );
    }

    @Test
    @DisplayName("Should create a valid DTO with all required fields")
    void shouldCreateValidDTO() {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        
        // When
        Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertTrue(violations.isEmpty(), "No validation violations should be present");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate required fields")
    @MethodSource("invalidDocumentRequestProvider")
    void shouldValidateRequiredFields(UUID applicationId, DocumentType type, String fieldName, String expectedMessage) {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO();
        dto.setApplicationId(applicationId);
        dto.setType(type);
        
        // When
        Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        ConstraintViolation<DocumentRequestDTO> violation = violations.iterator().next();
        assertEquals(fieldName, violation.getPropertyPath().toString(), "Violation should be for the correct field");
        assertEquals(expectedMessage, violation.getMessage(), "Violation message should match expected");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate content type format")
    @MethodSource("invalidContentTypeProvider")
    void shouldValidateContentTypeFormat(String contentType, String fieldName, String expectedMessage) {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        dto.setContentType(contentType);
        
        // When
        Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        ConstraintViolation<DocumentRequestDTO> violation = violations.iterator().next();
        assertEquals(fieldName, violation.getPropertyPath().toString(), "Violation should be for the correct field");
        assertEquals(expectedMessage, violation.getMessage(), "Violation message should match expected");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate filename length")
    @ValueSource(strings = {
        "This is an extremely long filename that exceeds the maximum allowed length of 255 characters. It contains a lot of unnecessary text just to make it longer than the limit. This is an extremely long filename that exceeds the maximum allowed length of 255 characters. It contains a lot of unnecessary text just to make it longer than the limit."
    })
    void shouldValidateFilenameLength(String filename) {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        dto.setFilename(filename);
        
        // When
        Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
        
        // Then
        assertFalse(violations.isEmpty(), "Validation violations should be present");
        ConstraintViolation<DocumentRequestDTO> violation = violations.iterator().next();
        assertEquals("filename", violation.getPropertyPath().toString(), "Violation should be for the filename field");
        assertEquals("Filename cannot exceed 255 characters", violation.getMessage(), "Violation message should match expected");
    }
    
    @Test
    @DisplayName("Should serialize to JSON correctly")
    void shouldSerializeToJsonCorrectly() throws Exception {
        // Given
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("pageCount", 5);
        metadata.put("documentDate", "2023-01-15");
        
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("accountNumber", 0.95);
        confidenceScores.put("bankName", 0.98);
        
        DocumentRequestDTO dto = new DocumentRequestDTO.Builder(testApplicationId, DocumentType.BANK_STATEMENT)
                .withClassification("bank_statement")
                .withContentType("application/pdf")
                .withFilename("bank_statement_jan_2023.pdf")
                .withContainsPii(true)
                .withIsFinancial(true)
                .withClassificationConfidence(0.97)
                .withMetadata(metadata)
                .addConfidenceScores(confidenceScores)
                .build();
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertTrue(json.contains("\"application_id\":\"" + testApplicationId + "\""), "JSON should contain application_id field");
        assertTrue(json.contains("\"type\":\"BANK_STATEMENT\""), "JSON should contain type field");
        assertTrue(json.contains("\"classification\":\"bank_statement\""), "JSON should contain classification field");
        assertTrue(json.contains("\"content_type\":\"application/pdf\""), "JSON should contain content_type field");
        assertTrue(json.contains("\"filename\":\"bank_statement_jan_2023.pdf\""), "JSON should contain filename field");
        assertTrue(json.contains("\"contains_pii\":true"), "JSON should contain contains_pii field");
        assertTrue(json.contains("\"is_financial\":true"), "JSON should contain is_financial field");
        assertTrue(json.contains("\"classification_confidence\":0.97"), "JSON should contain classification_confidence field");
        assertTrue(json.contains("\"metadata\":"), "JSON should contain metadata field");
        assertTrue(json.contains("\"pageCount\":5"), "JSON should contain metadata pageCount field");
        assertTrue(json.contains("\"documentDate\":\"2023-01-15\""), "JSON should contain metadata documentDate field");
        assertTrue(json.contains("\"confidenceScores\":"), "JSON should contain confidenceScores in metadata");
        assertTrue(json.contains("\"accountNumber\":0.95"), "JSON should contain accountNumber confidence score");
        assertTrue(json.contains("\"bankName\":0.98"), "JSON should contain bankName confidence score");
    }
    
    @Test
    @DisplayName("Should deserialize from JSON correctly")
    void shouldDeserializeFromJsonCorrectly() throws Exception {
        // Given
        String uuid = UUID.randomUUID().toString();
        String json = String.format("{\"application_id\":\"%s\",\"type\":\"BANK_STATEMENT\",\"classification\":\"bank_statement\",\"content_type\":\"application/pdf\",\"filename\":\"bank_statement_jan_2023.pdf\",\"contains_pii\":true,\"is_financial\":true,\"classification_confidence\":0.97,\"metadata\":{\"pageCount\":5,\"documentDate\":\"2023-01-15\",\"confidenceScores\":{\"accountNumber\":0.95,\"bankName\":0.98}}}", uuid);
        
        // When
        DocumentRequestDTO dto = objectMapper.readValue(json, DocumentRequestDTO.class);
        
        // Then
        assertEquals(UUID.fromString(uuid), dto.getApplicationId(), "Application ID should be deserialized correctly");
        assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Document type should be deserialized correctly");
        assertEquals("bank_statement", dto.getClassification(), "Classification should be deserialized correctly");
        assertEquals("application/pdf", dto.getContentType(), "Content type should be deserialized correctly");
        assertEquals("bank_statement_jan_2023.pdf", dto.getFilename(), "Filename should be deserialized correctly");
        assertTrue(dto.getContainsPii(), "Contains PII flag should be deserialized correctly");
        assertTrue(dto.getIsFinancial(), "Is financial flag should be deserialized correctly");
        assertEquals(0.97, dto.getClassificationConfidence(), "Classification confidence should be deserialized correctly");
        assertNotNull(dto.getMetadata(), "Metadata should not be null");
        assertEquals(5, dto.getMetadataValue("pageCount"), "Metadata pageCount should be deserialized correctly");
        assertEquals("2023-01-15", dto.getMetadataValue("documentDate"), "Metadata documentDate should be deserialized correctly");
        
        Map<String, Double> confidenceScores = dto.getConfidenceScores();
        assertNotNull(confidenceScores, "Confidence scores should not be null");
        assertEquals(0.95, confidenceScores.get("accountNumber"), "accountNumber confidence score should be deserialized correctly");
        assertEquals(0.98, confidenceScores.get("bankName"), "bankName confidence score should be deserialized correctly");
    }
    
    @Test
    @DisplayName("Should handle multipart file upload")
    void shouldHandleMultipartFileUpload() {
        // Given
        byte[] content = "Sample PDF content".getBytes();
        MockMultipartFile file = new MockMultipartFile(
                "document",
                "bank_statement.pdf",
                "application/pdf",
                content);
        
        // When
        DocumentRequestDTO dto = createDtoFromMultipartFile(file, testApplicationId, DocumentType.BANK_STATEMENT);
        
        // Then
        assertEquals(testApplicationId, dto.getApplicationId(), "Application ID should be set correctly");
        assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Document type should be set correctly");
        assertEquals("bank_statement.pdf", dto.getFilename(), "Filename should be set from multipart file");
        assertEquals("application/pdf", dto.getContentType(), "Content type should be set from multipart file");
        assertNotNull(dto.getBase64Content(), "Base64 content should be set");
        assertTrue(dto.hasBase64Content(), "hasBase64Content() should return true");
    }
    
    @Test
    @DisplayName("Should handle document classification metadata")
    void shouldHandleDocumentClassificationMetadata() {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        dto.setClassification("bank_statement");
        dto.setClassificationConfidence(0.97);
        
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("accountNumber", 0.95);
        confidenceScores.put("bankName", 0.98);
        dto.addConfidenceScores(confidenceScores);
        
        // Then
        assertEquals("bank_statement", dto.getClassification(), "Classification should be set correctly");
        assertEquals(0.97, dto.getClassificationConfidence(), "Classification confidence should be set correctly");
        
        Map<String, Double> retrievedScores = dto.getConfidenceScores();
        assertNotNull(retrievedScores, "Confidence scores should not be null");
        assertEquals(0.95, retrievedScores.get("accountNumber"), "accountNumber confidence score should be set correctly");
        assertEquals(0.98, retrievedScores.get("bankName"), "bankName confidence score should be set correctly");
    }
    
    @Test
    @DisplayName("Should handle null confidence scores")
    void shouldHandleNullConfidenceScores() {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        
        // When
        dto.addConfidenceScores(null);
        
        // Then
        Map<String, Double> retrievedScores = dto.getConfidenceScores();
        assertNotNull(retrievedScores, "Confidence scores should not be null even when adding null");
        assertTrue(retrievedScores.isEmpty(), "Confidence scores should be empty when adding null");
    }
    
    @Test
    @DisplayName("Should handle empty confidence scores")
    void shouldHandleEmptyConfidenceScores() {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        
        // When
        dto.addConfidenceScores(new HashMap<>());
        
        // Then
        Map<String, Double> retrievedScores = dto.getConfidenceScores();
        assertNotNull(retrievedScores, "Confidence scores should not be null even when adding empty map");
        assertTrue(retrievedScores.isEmpty(), "Confidence scores should be empty when adding empty map");
    }
    
    @Test
    @DisplayName("Should check if request is valid for creation")
    void shouldCheckIfRequestIsValidForCreation() {
        // Given
        DocumentRequestDTO validDto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        DocumentRequestDTO invalidDto1 = new DocumentRequestDTO(null, DocumentType.BANK_STATEMENT);
        DocumentRequestDTO invalidDto2 = new DocumentRequestDTO(testApplicationId, null);
        DocumentRequestDTO invalidDto3 = new DocumentRequestDTO(null, null);
        
        // Then
        assertTrue(validDto.isValidForCreation(), "DTO with all required fields should be valid for creation");
        assertFalse(invalidDto1.isValidForCreation(), "DTO without application ID should not be valid for creation");
        assertFalse(invalidDto2.isValidForCreation(), "DTO without document type should not be valid for creation");
        assertFalse(invalidDto3.isValidForCreation(), "DTO without any required fields should not be valid for creation");
    }
    
    @Test
    @DisplayName("Should check if document has metadata")
    void shouldCheckIfDocumentHasMetadata() {
        // Given
        DocumentRequestDTO dtoWithMetadata = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        dtoWithMetadata.addMetadata("key", "value");
        
        DocumentRequestDTO dtoWithEmptyMetadata = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        dtoWithEmptyMetadata.setMetadata(new HashMap<>());
        
        DocumentRequestDTO dtoWithNullMetadata = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        dtoWithNullMetadata.setMetadata(null);
        
        // Then
        assertTrue(dtoWithMetadata.hasMetadata(), "DTO with metadata should return true for hasMetadata()");
        assertFalse(dtoWithEmptyMetadata.hasMetadata(), "DTO with empty metadata should return false for hasMetadata()");
        assertFalse(dtoWithNullMetadata.hasMetadata(), "DTO with null metadata should return false for hasMetadata()");
    }
    
    @Test
    @DisplayName("Should get and add metadata correctly")
    void shouldGetAndAddMetadataCorrectly() {
        // Given
        DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
        
        // When
        dto.addMetadata("stringKey", "stringValue");
        dto.addMetadata("intKey", 123);
        dto.addMetadata("boolKey", true);
        
        // Then
        assertEquals("stringValue", dto.getMetadataValue("stringKey"), "Should get string metadata correctly");
        assertEquals(123, dto.getMetadataValue("intKey"), "Should get integer metadata correctly");
        assertEquals(true, dto.getMetadataValue("boolKey"), "Should get boolean metadata correctly");
        assertNull(dto.getMetadataValue("nonexistent"), "Should return null for nonexistent metadata");
        
        // When metadata is null
        DocumentRequestDTO nullMetadataDto = new DocumentRequestDTO();
        nullMetadataDto.setMetadata(null);
        
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
        DocumentRequestDTO dto = new DocumentRequestDTO.Builder(testApplicationId, DocumentType.BANK_STATEMENT)
                .withClassification("bank_statement")
                .withContentType("application/pdf")
                .withFilename("bank_statement.pdf")
                .withContainsPii(true)
                .withIsFinancial(true)
                .withClassificationConfidence(0.97)
                .withBase64Content("base64content")
                .addMetadata("key", "value")
                .build();
        
        // Then
        assertEquals(testApplicationId, dto.getApplicationId(), "Builder should set application ID correctly");
        assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Builder should set document type correctly");
        assertEquals("bank_statement", dto.getClassification(), "Builder should set classification correctly");
        assertEquals("application/pdf", dto.getContentType(), "Builder should set content type correctly");
        assertEquals("bank_statement.pdf", dto.getFilename(), "Builder should set filename correctly");
        assertTrue(dto.getContainsPii(), "Builder should set contains PII flag correctly");
        assertTrue(dto.getIsFinancial(), "Builder should set is financial flag correctly");
        assertEquals(0.97, dto.getClassificationConfidence(), "Builder should set classification confidence correctly");
        assertEquals("base64content", dto.getBase64Content(), "Builder should set base64 content correctly");
        assertEquals("value", dto.getMetadataValue("key"), "Builder should set metadata correctly");
    }
    
    /**
     * Helper method to create a DocumentRequestDTO from a MultipartFile.
     * This simulates what would happen in a controller when handling file uploads.
     */
    private DocumentRequestDTO createDtoFromMultipartFile(MultipartFile file, UUID applicationId, DocumentType type) {
        try {
            DocumentRequestDTO dto = new DocumentRequestDTO(applicationId, type);
            dto.setFilename(file.getOriginalFilename());
            dto.setContentType(file.getContentType());
            
            // Convert file content to Base64 (simplified for test)
            String base64Content = java.util.Base64.getEncoder().encodeToString(file.getBytes());
            dto.setBase64Content(base64Content);
            
            return dto;
        } catch (Exception e) {
            throw new RuntimeException("Failed to create DTO from multipart file", e);
        }
    }
}