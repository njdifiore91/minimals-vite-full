package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.DocumentType;
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
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link DocumentRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and multipart file handling.
 * 
 * This test suite ensures that the DTO properly validates document uploads,
 * handles document classification metadata correctly, and supports multipart
 * file uploads appropriately.
 */
@DisplayName("DocumentRequestDTO Tests")
class DocumentRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    private DocumentRequestDTO validDto;
    private UUID testApplicationId;
    private Map<String, Object> testMetadata;
    private Map<String, Double> testConfidenceScores;

    @BeforeEach
    void setUp() {
        // Initialize validator
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Initialize ObjectMapper
        objectMapper = JsonUtil.getObjectMapper();
        
        // Create test application ID
        testApplicationId = UUID.randomUUID();
        
        // Create test metadata
        testMetadata = new HashMap<>();
        testMetadata.put("pageCount", 5);
        testMetadata.put("documentDate", "2023-01-15");
        testMetadata.put("issuer", "First National Bank");
        
        // Create test confidence scores
        testConfidenceScores = new HashMap<>();
        testConfidenceScores.put("classification", 0.95);
        testConfidenceScores.put("accountNumber", 0.87);
        testConfidenceScores.put("balance", 0.92);
        
        // Create a valid DTO for testing
        validDto = new DocumentRequestDTO(
                testApplicationId,
                DocumentType.BANK_STATEMENT,
                "bank_statement",
                testMetadata,
                testConfidenceScores,
                "bank_statement_jan_2023.pdf",
                "application/pdf"
        );
    }

    @Nested
    @DisplayName("Validation Tests")
    class ValidationTests {

        @Test
        @DisplayName("Valid DTO should pass validation")
        void validDtoShouldPassValidation() {
            // When
            Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "Valid DTO should not have validation violations");
        }

        @Test
        @DisplayName("DTO with null application ID should fail validation")
        void dtoWithNullApplicationIdShouldFailValidation() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    null,
                    DocumentType.BANK_STATEMENT,
                    "bank_statement",
                    testMetadata,
                    testConfidenceScores,
                    "bank_statement_jan_2023.pdf",
                    "application/pdf"
            );
            
            // When
            Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null application ID should have validation violations");
            assertEquals(1, violations.size(), "Should have exactly one violation");
            
            ConstraintViolation<DocumentRequestDTO> violation = violations.iterator().next();
            assertEquals("applicationId", violation.getPropertyPath().toString(), "Violation should be on applicationId field");
            assertEquals("Application ID is required", violation.getMessage(), "Violation message should match annotation");
        }

        @Test
        @DisplayName("DTO with null document type should fail validation")
        void dtoWithNullDocumentTypeShouldFailValidation() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    null,
                    "bank_statement",
                    testMetadata,
                    testConfidenceScores,
                    "bank_statement_jan_2023.pdf",
                    "application/pdf"
            );
            
            // When
            Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null document type should have validation violations");
            assertEquals(1, violations.size(), "Should have exactly one violation");
            
            ConstraintViolation<DocumentRequestDTO> violation = violations.iterator().next();
            assertEquals("type", violation.getPropertyPath().toString(), "Violation should be on type field");
            assertEquals("Document type is required", violation.getMessage(), "Violation message should match annotation");
        }

        @Test
        @DisplayName("DTO with oversized filename should fail validation")
        void dtoWithOversizedFilenameShouldFailValidation() {
            // Given
            StringBuilder largeFilename = new StringBuilder();
            for (int i = 0; i < 300; i++) {
                largeFilename.append("a");
            }
            largeFilename.append(".pdf");
            
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT,
                    "bank_statement",
                    testMetadata,
                    testConfidenceScores,
                    largeFilename.toString(),
                    "application/pdf"
            );
            
            // When
            Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized filename should have validation violations");
            
            boolean hasFilenameSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("originalFilename") && 
                              v.getMessage().contains("cannot exceed 255 characters"));
            
            assertTrue(hasFilenameSizeViolation, "Should have a size violation on originalFilename field");
        }
        
        @Test
        @DisplayName("DTO with oversized content type should fail validation")
        void dtoWithOversizedContentTypeShouldFailValidation() {
            // Given
            StringBuilder largeContentType = new StringBuilder();
            for (int i = 0; i < 150; i++) {
                largeContentType.append("a");
            }
            
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT,
                    "bank_statement",
                    testMetadata,
                    testConfidenceScores,
                    "bank_statement_jan_2023.pdf",
                    largeContentType.toString()
            );
            
            // When
            Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized content type should have validation violations");
            
            boolean hasContentTypeSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("contentType") && 
                              v.getMessage().contains("cannot exceed 100 characters"));
            
            assertTrue(hasContentTypeSizeViolation, "Should have a size violation on contentType field");
        }
        
        @Test
        @DisplayName("DTO with null metadata should be initialized with empty map")
        void dtoWithNullMetadataShouldBeInitializedWithEmptyMap() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT,
                    "bank_statement",
                    null,
                    testConfidenceScores,
                    "bank_statement_jan_2023.pdf",
                    "application/pdf"
            );
            
            // Then
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
        }
        
        @Test
        @DisplayName("DTO with null confidence scores should be initialized with empty map")
        void dtoWithNullConfidenceScoresShouldBeInitializedWithEmptyMap() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT,
                    "bank_statement",
                    testMetadata,
                    null,
                    "bank_statement_jan_2023.pdf",
                    "application/pdf"
            );
            
            // Then
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertTrue(dto.getConfidenceScores().isEmpty(), "Confidence scores should be empty");
        }
        
        @Test
        @DisplayName("isValidForCreation should return true for valid DTO")
        void isValidForCreationShouldReturnTrueForValidDto() {
            // Then
            assertTrue(validDto.isValidForCreation(), "Valid DTO should be valid for creation");
        }
        
        @Test
        @DisplayName("isValidForCreation should return false for DTO with null application ID")
        void isValidForCreationShouldReturnFalseForDtoWithNullApplicationId() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    null,
                    DocumentType.BANK_STATEMENT,
                    "bank_statement",
                    testMetadata,
                    testConfidenceScores,
                    "bank_statement_jan_2023.pdf",
                    "application/pdf"
            );
            
            // Then
            assertFalse(dto.isValidForCreation(), "DTO with null application ID should not be valid for creation");
        }
        
        @Test
        @DisplayName("isValidForCreation should return false for DTO with null document type")
        void isValidForCreationShouldReturnFalseForDtoWithNullDocumentType() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    null,
                    "bank_statement",
                    testMetadata,
                    testConfidenceScores,
                    "bank_statement_jan_2023.pdf",
                    "application/pdf"
            );
            
            // Then
            assertFalse(dto.isValidForCreation(), "DTO with null document type should not be valid for creation");
        }
        
        @Test
        @DisplayName("isValidForUpdate should return true for valid DTO and document ID")
        void isValidForUpdateShouldReturnTrueForValidDtoAndDocumentId() {
            // Given
            UUID documentId = UUID.randomUUID();
            
            // Then
            assertTrue(validDto.isValidForUpdate(documentId), "Valid DTO should be valid for update");
        }
        
        @Test
        @DisplayName("isValidForUpdate should return false for null document ID")
        void isValidForUpdateShouldReturnFalseForNullDocumentId() {
            // Then
            assertFalse(validDto.isValidForUpdate(null), "DTO with null document ID should not be valid for update");
        }
        
        @Test
        @DisplayName("isValidForUpdate should return false for DTO with null application ID")
        void isValidForUpdateShouldReturnFalseForDtoWithNullApplicationId() {
            // Given
            UUID documentId = UUID.randomUUID();
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    null,
                    DocumentType.BANK_STATEMENT,
                    "bank_statement",
                    testMetadata,
                    testConfidenceScores,
                    "bank_statement_jan_2023.pdf",
                    "application/pdf"
            );
            
            // Then
            assertFalse(dto.isValidForUpdate(documentId), "DTO with null application ID should not be valid for update");
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
            assertTrue(json.contains("\"applicationId\":\"" + testApplicationId + "\""), "JSON should contain applicationId field");
            assertTrue(json.contains("\"type\":\"BANK_STATEMENT\""), "JSON should contain type field");
            assertTrue(json.contains("\"classification\":\"bank_statement\""), "JSON should contain classification field");
            assertTrue(json.contains("\"metadata\":"), "JSON should contain metadata field");
            assertTrue(json.contains("\"confidenceScores\":"), "JSON should contain confidenceScores field");
            assertTrue(json.contains("\"originalFilename\":\"bank_statement_jan_2023.pdf\""), "JSON should contain originalFilename field");
            assertTrue(json.contains("\"contentType\":\"application/pdf\""), "JSON should contain contentType field");
        }

        @Test
        @DisplayName("JSON should deserialize to DTO correctly")
        void jsonShouldDeserializeToDtoCorrectly() throws Exception {
            // Given
            UUID testId = UUID.randomUUID();
            String json = "{\"applicationId\":\"" + testId + "\",\"type\":\"TAX_RETURN\",\"classification\":\"tax_return\",\"metadata\":{\"year\":2022,\"type\":\"1040\"},\"confidenceScores\":{\"classification\":0.98,\"ein\":0.85},\"originalFilename\":\"tax_return_2022.pdf\",\"contentType\":\"application/pdf\"}";
            
            // When
            DocumentRequestDTO dto = objectMapper.readValue(json, DocumentRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(testId, dto.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.TAX_RETURN, dto.getType(), "Document type should match");
            assertEquals("tax_return", dto.getClassification(), "Classification should match");
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertEquals(2, dto.getMetadata().size(), "Metadata should have correct number of entries");
            assertEquals(2022, dto.getMetadata().get("year"), "Metadata values should match");
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertEquals(2, dto.getConfidenceScores().size(), "Confidence scores should have correct number of entries");
            assertEquals(0.98, dto.getConfidenceScores().get("classification"), 0.001, "Confidence score values should match");
            assertEquals("tax_return_2022.pdf", dto.getOriginalFilename(), "Original filename should match");
            assertEquals("application/pdf", dto.getContentType(), "Content type should match");
        }

        @Test
        @DisplayName("DTO should ignore unknown JSON properties")
        void dtoShouldIgnoreUnknownJsonProperties() throws Exception {
            // Given
            UUID testId = UUID.randomUUID();
            String json = "{\"applicationId\":\"" + testId + "\",\"type\":\"INVOICE\",\"unknown_field\":\"value\",\"metadata\":{\"invoiceNumber\":\"INV-12345\"}}";
            
            // When
            DocumentRequestDTO dto = objectMapper.readValue(json, DocumentRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(testId, dto.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.INVOICE, dto.getType(), "Document type should match");
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertEquals("INV-12345", dto.getMetadata().get("invoiceNumber"), "Metadata values should match");
            // Unknown field should be ignored without exception
        }
        
        @Test
        @DisplayName("DTO should handle null fields correctly during serialization")
        void dtoShouldHandleNullFieldsCorrectlyDuringSerialization() throws Exception {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BUSINESS_LICENSE,
                    null,  // null classification
                    new HashMap<>(),  // empty metadata
                    new HashMap<>(),  // empty confidence scores
                    null,  // null original filename
                    null   // null content type
            );
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertNotNull(json, "JSON should not be null");
            assertTrue(json.contains("\"applicationId\":"), "JSON should contain applicationId field");
            assertTrue(json.contains("\"type\":\"BUSINESS_LICENSE\""), "JSON should contain type field");
            assertFalse(json.contains("\"classification\":"), "JSON should not contain null classification field");
            assertTrue(json.contains("\"metadata\":{}"), "JSON should contain empty metadata field");
            assertTrue(json.contains("\"confidenceScores\":{}"), "JSON should contain empty confidenceScores field");
            assertFalse(json.contains("\"originalFilename\":"), "JSON should not contain null originalFilename field");
            assertFalse(json.contains("\"contentType\":"), "JSON should not contain null contentType field");
        }
    }

    @Nested
    @DisplayName("Metadata and Confidence Score Tests")
    class MetadataAndConfidenceScoreTests {

        @Test
        @DisplayName("addMetadata should add entry to metadata map")
        void addMetadataShouldAddEntryToMetadataMap() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT
            );
            
            // When
            dto.addMetadata("accountNumber", "123456789");
            
            // Then
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertEquals(1, dto.getMetadata().size(), "Metadata should have one entry");
            assertEquals("123456789", dto.getMetadata().get("accountNumber"), "Metadata value should match");
        }

        @Test
        @DisplayName("addMetadata should initialize metadata map if null")
        void addMetadataShouldInitializeMetadataMapIfNull() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO();
            dto.setApplicationId(testApplicationId);
            dto.setType(DocumentType.BANK_STATEMENT);
            dto.setMetadata(null);  // Explicitly set to null
            
            // When
            dto.addMetadata("accountNumber", "123456789");
            
            // Then
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertEquals(1, dto.getMetadata().size(), "Metadata should have one entry");
            assertEquals("123456789", dto.getMetadata().get("accountNumber"), "Metadata value should match");
        }

        @Test
        @DisplayName("addConfidenceScore should add entry to confidence scores map")
        void addConfidenceScoreShouldAddEntryToConfidenceScoresMap() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT
            );
            
            // When
            dto.addConfidenceScore("accountNumber", 0.95);
            
            // Then
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertEquals(1, dto.getConfidenceScores().size(), "Confidence scores should have one entry");
            assertEquals(0.95, dto.getConfidenceScores().get("accountNumber"), 0.001, "Confidence score value should match");
        }

        @Test
        @DisplayName("addConfidenceScore should initialize confidence scores map if null")
        void addConfidenceScoreShouldInitializeConfidenceScoresMapIfNull() {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO();
            dto.setApplicationId(testApplicationId);
            dto.setType(DocumentType.BANK_STATEMENT);
            dto.setConfidenceScores(null);  // Explicitly set to null
            
            // When
            dto.addConfidenceScore("accountNumber", 0.95);
            
            // Then
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertEquals(1, dto.getConfidenceScores().size(), "Confidence scores should have one entry");
            assertEquals(0.95, dto.getConfidenceScores().get("accountNumber"), 0.001, "Confidence score value should match");
        }

        @Test
        @DisplayName("withAdditionalMetadata should create new DTO with combined metadata")
        void withAdditionalMetadataShouldCreateNewDtoWithCombinedMetadata() {
            // Given
            Map<String, Object> additionalMetadata = new HashMap<>();
            additionalMetadata.put("accountType", "Checking");
            additionalMetadata.put("bankName", "First National Bank");
            
            // When
            DocumentRequestDTO newDto = validDto.withAdditionalMetadata(additionalMetadata);
            
            // Then
            assertNotNull(newDto, "New DTO should not be null");
            assertNotSame(validDto, newDto, "Should return a new DTO instance");
            assertEquals(testApplicationId, newDto.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.BANK_STATEMENT, newDto.getType(), "Document type should match");
            assertEquals("bank_statement", newDto.getClassification(), "Classification should match");
            assertNotNull(newDto.getMetadata(), "Metadata should not be null");
            assertEquals(5, newDto.getMetadata().size(), "Metadata should have combined entries");
            assertEquals("Checking", newDto.getMetadata().get("accountType"), "New metadata values should be present");
            assertEquals(5, newDto.getMetadata().get("pageCount"), "Original metadata values should be preserved");
        }

        @Test
        @DisplayName("withAdditionalMetadata should return same DTO if additional metadata is null")
        void withAdditionalMetadataShouldReturnSameDtoIfAdditionalMetadataIsNull() {
            // When
            DocumentRequestDTO newDto = validDto.withAdditionalMetadata(null);
            
            // Then
            assertSame(validDto, newDto, "Should return the same DTO instance");
        }

        @Test
        @DisplayName("withAdditionalMetadata should return same DTO if additional metadata is empty")
        void withAdditionalMetadataShouldReturnSameDtoIfAdditionalMetadataIsEmpty() {
            // When
            DocumentRequestDTO newDto = validDto.withAdditionalMetadata(new HashMap<>());
            
            // Then
            assertSame(validDto, newDto, "Should return the same DTO instance");
        }

        @Test
        @DisplayName("withAdditionalConfidenceScores should create new DTO with combined confidence scores")
        void withAdditionalConfidenceScoresShouldCreateNewDtoWithCombinedConfidenceScores() {
            // Given
            Map<String, Double> additionalScores = new HashMap<>();
            additionalScores.put("accountType", 0.88);
            additionalScores.put("bankName", 0.97);
            
            // When
            DocumentRequestDTO newDto = validDto.withAdditionalConfidenceScores(additionalScores);
            
            // Then
            assertNotNull(newDto, "New DTO should not be null");
            assertNotSame(validDto, newDto, "Should return a new DTO instance");
            assertEquals(testApplicationId, newDto.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.BANK_STATEMENT, newDto.getType(), "Document type should match");
            assertEquals("bank_statement", newDto.getClassification(), "Classification should match");
            assertNotNull(newDto.getConfidenceScores(), "Confidence scores should not be null");
            assertEquals(5, newDto.getConfidenceScores().size(), "Confidence scores should have combined entries");
            assertEquals(0.88, newDto.getConfidenceScores().get("accountType"), 0.001, "New confidence score values should be present");
            assertEquals(0.95, newDto.getConfidenceScores().get("classification"), 0.001, "Original confidence score values should be preserved");
        }

        @Test
        @DisplayName("withAdditionalConfidenceScores should return same DTO if additional scores is null")
        void withAdditionalConfidenceScoresShouldReturnSameDtoIfAdditionalScoresIsNull() {
            // When
            DocumentRequestDTO newDto = validDto.withAdditionalConfidenceScores(null);
            
            // Then
            assertSame(validDto, newDto, "Should return the same DTO instance");
        }

        @Test
        @DisplayName("withAdditionalConfidenceScores should return same DTO if additional scores is empty")
        void withAdditionalConfidenceScoresShouldReturnSameDtoIfAdditionalScoresIsEmpty() {
            // When
            DocumentRequestDTO newDto = validDto.withAdditionalConfidenceScores(new HashMap<>());
            
            // Then
            assertSame(validDto, newDto, "Should return the same DTO instance");
        }
    }

    @Nested
    @DisplayName("Multipart File Tests")
    class MultipartFileTests {

        @Test
        @DisplayName("DTO should handle multipart file information correctly")
        void dtoShouldHandleMultipartFileInformationCorrectly() {
            // Given
            byte[] content = "Test file content".getBytes();
            MockMultipartFile multipartFile = new MockMultipartFile(
                    "document",
                    "test_document.pdf",
                    "application/pdf",
                    content
            );
            
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT
            );
            
            // When - simulate extracting information from MultipartFile
            dto.setOriginalFilename(multipartFile.getOriginalFilename());
            dto.setContentType(multipartFile.getContentType());
            
            // Then
            assertEquals("test_document.pdf", dto.getOriginalFilename(), "Original filename should match");
            assertEquals("application/pdf", dto.getContentType(), "Content type should match");
        }

        @Test
        @DisplayName("DTO should handle multipart file with null filename and content type")
        void dtoShouldHandleMultipartFileWithNullFilenameAndContentType() {
            // Given
            byte[] content = "Test file content".getBytes();
            MockMultipartFile multipartFile = new MockMultipartFile(
                    "document",
                    null,  // null filename
                    null,  // null content type
                    content
            );
            
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    DocumentType.BANK_STATEMENT
            );
            
            // When - simulate extracting information from MultipartFile
            dto.setOriginalFilename(multipartFile.getOriginalFilename());
            dto.setContentType(multipartFile.getContentType());
            
            // Then
            assertNull(dto.getOriginalFilename(), "Original filename should be null");
            assertNull(dto.getContentType(), "Content type should be null");
        }
    }

    @Nested
    @DisplayName("Builder Pattern Tests")
    class BuilderPatternTests {

        @Test
        @DisplayName("Builder should create valid DTO with required fields")
        void builderShouldCreateValidDtoWithRequiredFields() {
            // When
            DocumentRequestDTO dto = new DocumentRequestDTO.Builder(testApplicationId, DocumentType.BANK_STATEMENT)
                    .build();
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(testApplicationId, dto.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Document type should match");
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertTrue(dto.getConfidenceScores().isEmpty(), "Confidence scores should be empty");
        }

        @Test
        @DisplayName("Builder should create valid DTO with all fields")
        void builderShouldCreateValidDtoWithAllFields() {
            // When
            DocumentRequestDTO dto = new DocumentRequestDTO.Builder(testApplicationId, DocumentType.BANK_STATEMENT)
                    .withClassification("bank_statement")
                    .withMetadata(testMetadata)
                    .withConfidenceScores(testConfidenceScores)
                    .withOriginalFilename("bank_statement_jan_2023.pdf")
                    .withContentType("application/pdf")
                    .build();
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(testApplicationId, dto.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Document type should match");
            assertEquals("bank_statement", dto.getClassification(), "Classification should match");
            assertEquals(testMetadata, dto.getMetadata(), "Metadata should match");
            assertEquals(testConfidenceScores, dto.getConfidenceScores(), "Confidence scores should match");
            assertEquals("bank_statement_jan_2023.pdf", dto.getOriginalFilename(), "Original filename should match");
            assertEquals("application/pdf", dto.getContentType(), "Content type should match");
        }

        @Test
        @DisplayName("Builder should add metadata entries correctly")
        void builderShouldAddMetadataEntriesCorrectly() {
            // When
            DocumentRequestDTO dto = new DocumentRequestDTO.Builder(testApplicationId, DocumentType.BANK_STATEMENT)
                    .addMetadata("accountNumber", "123456789")
                    .addMetadata("accountType", "Checking")
                    .build();
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertEquals(2, dto.getMetadata().size(), "Metadata should have correct number of entries");
            assertEquals("123456789", dto.getMetadata().get("accountNumber"), "Metadata values should match");
            assertEquals("Checking", dto.getMetadata().get("accountType"), "Metadata values should match");
        }

        @Test
        @DisplayName("Builder should add confidence score entries correctly")
        void builderShouldAddConfidenceScoreEntriesCorrectly() {
            // When
            DocumentRequestDTO dto = new DocumentRequestDTO.Builder(testApplicationId, DocumentType.BANK_STATEMENT)
                    .addConfidenceScore("accountNumber", 0.95)
                    .addConfidenceScore("accountType", 0.88)
                    .build();
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertEquals(2, dto.getConfidenceScores().size(), "Confidence scores should have correct number of entries");
            assertEquals(0.95, dto.getConfidenceScores().get("accountNumber"), 0.001, "Confidence score values should match");
            assertEquals(0.88, dto.getConfidenceScores().get("accountType"), 0.001, "Confidence score values should match");
        }
    }

    @Nested
    @DisplayName("Document Type Tests")
    class DocumentTypeTests {

        @ParameterizedTest
        @EnumSource(DocumentType.class)
        @DisplayName("DTO should accept all document types")
        void dtoShouldAcceptAllDocumentTypes(DocumentType documentType) {
            // Given
            DocumentRequestDTO dto = new DocumentRequestDTO(
                    testApplicationId,
                    documentType
            );
            
            // When
            Set<ConstraintViolation<DocumentRequestDTO>> violations = validator.validate(dto);
            
            // Then
            assertTrue(violations.isEmpty(), "DTO should accept document type: " + documentType);
            assertEquals(documentType, dto.getType(), "Document type should match");
        }

        @Test
        @DisplayName("DTO should handle financial document types correctly")
        void dtoShouldHandleFinancialDocumentTypesCorrectly() {
            // Given
            DocumentType[] financialTypes = {
                    DocumentType.BANK_STATEMENT,
                    DocumentType.TAX_RETURN,
                    DocumentType.INVOICE
            };
            
            for (DocumentType type : financialTypes) {
                // When
                DocumentRequestDTO dto = new DocumentRequestDTO(
                        testApplicationId,
                        type
                );
                
                // Then
                assertTrue(type.isFinancialDocument(), "Document type should be identified as financial: " + type);
                assertEquals(type, dto.getType(), "Document type should match");
            }
        }

        @Test
        @DisplayName("DTO should handle PII document types correctly")
        void dtoShouldHandlePiiDocumentTypesCorrectly() {
            // Given
            DocumentType[] piiTypes = {
                    DocumentType.ID_VERIFICATION,
                    DocumentType.TAX_RETURN
            };
            
            for (DocumentType type : piiTypes) {
                // When
                DocumentRequestDTO dto = new DocumentRequestDTO(
                        testApplicationId,
                        type
                );
                
                // Then
                assertTrue(type.containsPII(), "Document type should be identified as containing PII: " + type);
                assertEquals(type, dto.getType(), "Document type should match");
            }
        }
    }

    @Nested
    @DisplayName("Miscellaneous Tests")
    class MiscellaneousTests {

        @Test
        @DisplayName("toString method should include all fields")
        void toStringMethodShouldIncludeAllFields() {
            // When
            String toString = validDto.toString();
            
            // Then
            assertTrue(toString.contains("applicationId="), "toString should include applicationId field");
            assertTrue(toString.contains("type="), "toString should include type field");
            assertTrue(toString.contains("classification="), "toString should include classification field");
            assertTrue(toString.contains("hasMetadata="), "toString should include hasMetadata field");
            assertTrue(toString.contains("hasConfidenceScores="), "toString should include hasConfidenceScores field");
            assertTrue(toString.contains("originalFilename="), "toString should include originalFilename field");
            assertTrue(toString.contains("contentType="), "toString should include contentType field");
        }

        @Test
        @DisplayName("Default constructor should initialize empty maps")
        void defaultConstructorShouldInitializeEmptyMaps() {
            // When
            DocumentRequestDTO dto = new DocumentRequestDTO();
            
            // Then
            assertNull(dto.getApplicationId(), "Application ID should be null");
            assertNull(dto.getType(), "Document type should be null");
            assertNull(dto.getClassification(), "Classification should be null");
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertTrue(dto.getConfidenceScores().isEmpty(), "Confidence scores should be empty");
            assertNull(dto.getOriginalFilename(), "Original filename should be null");
            assertNull(dto.getContentType(), "Content type should be null");
        }

        @Test
        @DisplayName("Required fields constructor should initialize empty maps")
        void requiredFieldsConstructorShouldInitializeEmptyMaps() {
            // When
            DocumentRequestDTO dto = new DocumentRequestDTO(testApplicationId, DocumentType.BANK_STATEMENT);
            
            // Then
            assertEquals(testApplicationId, dto.getApplicationId(), "Application ID should match");
            assertEquals(DocumentType.BANK_STATEMENT, dto.getType(), "Document type should match");
            assertNull(dto.getClassification(), "Classification should be null");
            assertNotNull(dto.getMetadata(), "Metadata should not be null");
            assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
            assertNotNull(dto.getConfidenceScores(), "Confidence scores should not be null");
            assertTrue(dto.getConfidenceScores().isEmpty(), "Confidence scores should be empty");
            assertNull(dto.getOriginalFilename(), "Original filename should be null");
            assertNull(dto.getContentType(), "Content type should be null");
        }
    }
}