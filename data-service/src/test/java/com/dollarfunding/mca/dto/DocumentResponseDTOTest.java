package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentClassification;
import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.ValueSource;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link DocumentResponseDTO} that validates the document metadata structure,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly represents document metadata,
 * generates secure access URLs correctly, and includes document classification information.
 */
@DisplayName("Document Response DTO Tests")
public class DocumentResponseDTOTest {

    private ObjectMapper objectMapper;
    private UUID testId;
    private UUID testApplicationId;
    private LocalDateTime testUploadedAt;
    private LocalDateTime testUrlExpiresAt;
    
    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        // Configure ObjectMapper for LocalDateTime serialization
        objectMapper.findAndRegisterModules();
        
        testId = UUID.randomUUID();
        testApplicationId = UUID.randomUUID();
        testUploadedAt = LocalDateTime.now().truncatedTo(ChronoUnit.SECONDS);
        testUrlExpiresAt = testUploadedAt.plusHours(1);
    }
    
    /**
     * Test data provider for document classification confidence levels.
     */
    static Stream<Arguments> confidenceLevelProvider() {
        return Stream.of(
            Arguments.of(0.95, true, false, false),  // High confidence
            Arguments.of(0.85, false, true, false),   // Medium confidence
            Arguments.of(0.65, false, false, true)    // Low confidence
        );
    }
    
    /**
     * Test data provider for URL validity scenarios.
     */
    static Stream<Arguments> urlValidityProvider() {
        LocalDateTime now = LocalDateTime.now();
        return Stream.of(
            // Valid URL (not null, not empty, expiry in future)
            Arguments.of("https://example.com/document.pdf", now.plusMinutes(30), true),
            // Invalid URL (null)
            Arguments.of(null, now.plusMinutes(30), false),
            // Invalid URL (empty)
            Arguments.of("", now.plusMinutes(30), false),
            // Invalid URL (expiry in past)
            Arguments.of("https://example.com/document.pdf", now.minusMinutes(30), false),
            // Invalid URL (null expiry)
            Arguments.of("https://example.com/document.pdf", null, false)
        );
    }

    @Test
    @DisplayName("Should create a valid DTO with default constructor")
    void shouldCreateValidDTOWithDefaultConstructor() {
        // Given/When
        DocumentResponseDTO dto = new DocumentResponseDTO();
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertNotNull(dto.getMetadata(), "Metadata should be initialized as empty map");
        assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
    }
    
    @Test
    @DisplayName("Should create a valid DTO from Document entity")
    void shouldCreateValidDTOFromDocumentEntity() {
        // Given
        Document document = createTestDocument();
        String downloadUrl = "https://example.com/documents/test.pdf";
        
        // When
        DocumentResponseDTO dto = new DocumentResponseDTO(document, downloadUrl, testUrlExpiresAt);
        
        // Then
        assertEquals(testId, dto.getId(), "ID should match entity ID");
        assertEquals(testApplicationId, dto.getApplicationId(), "Application ID should match entity application ID");
        assertEquals(DocumentType.BANK_STATEMENT.name(), dto.getType(), "Type should match entity type");
        assertEquals("mca-documents-production/test-application/bank-statement.pdf", dto.getStoragePath(), "Storage path should match entity storage path");
        assertEquals(DocumentClassification.VERIFIED.name(), dto.getClassification(), "Classification should match entity classification");
        assertEquals(testUploadedAt, dto.getUploadedAt(), "Uploaded at should match entity uploaded at");
        assertEquals(downloadUrl, dto.getDownloadUrl(), "Download URL should match provided URL");
        assertEquals(testUrlExpiresAt, dto.getUrlExpiresAt(), "URL expiry should match provided expiry");
        assertEquals(0.97, dto.getClassificationConfidence(), "Classification confidence should match entity confidence score");
        
        // Verify metadata
        assertNotNull(dto.getMetadata(), "Metadata should not be null");
        assertEquals(3, dto.getMetadata().size(), "Metadata should have correct number of entries");
        assertEquals(5, dto.getMetadataValue("pageCount"), "Page count metadata should match");
        assertEquals("2023-01-15", dto.getMetadataValue("documentDate"), "Document date metadata should match");
    }
    
    @Test
    @DisplayName("Should create a valid DTO using static factory method")
    void shouldCreateValidDTOUsingStaticFactoryMethod() {
        // Given
        Document document = createTestDocument();
        String downloadUrl = "https://example.com/documents/test.pdf";
        
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document, downloadUrl, testUrlExpiresAt);
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertEquals(testId, dto.getId(), "ID should match entity ID");
        assertEquals(testApplicationId, dto.getApplicationId(), "Application ID should match entity application ID");
    }
    
    @Test
    @DisplayName("Should return null from static factory method when document is null")
    void shouldReturnNullFromStaticFactoryMethodWhenDocumentIsNull() {
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(null, "url", testUrlExpiresAt);
        
        // Then
        assertNull(dto, "DTO should be null when document is null");
    }
    
    @Test
    @DisplayName("Should serialize to JSON correctly")
    void shouldSerializeToJsonCorrectly() throws Exception {
        // Given
        Document document = createTestDocument();
        String downloadUrl = "https://example.com/documents/test.pdf";
        DocumentResponseDTO dto = new DocumentResponseDTO(document, downloadUrl, testUrlExpiresAt);
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertTrue(json.contains("\"id\":\"" + testId + "\""), "JSON should contain id field");
        assertTrue(json.contains("\"application_id\":\"" + testApplicationId + "\""), "JSON should contain application_id field");
        assertTrue(json.contains("\"type\":\"BANK_STATEMENT\""), "JSON should contain type field");
        assertTrue(json.contains("\"storage_path\":"), "JSON should contain storage_path field");
        assertTrue(json.contains("\"classification\":\"VERIFIED\""), "JSON should contain classification field");
        assertTrue(json.contains("\"uploaded_at\":"), "JSON should contain uploaded_at field");
        assertTrue(json.contains("\"download_url\":\"https://example.com/documents/test.pdf\""), "JSON should contain download_url field");
        assertTrue(json.contains("\"url_expires_at\":"), "JSON should contain url_expires_at field");
        assertTrue(json.contains("\"classification_confidence\":0.97"), "JSON should contain classification_confidence field");
        assertTrue(json.contains("\"metadata\":"), "JSON should contain metadata field");
        assertTrue(json.contains("\"pageCount\":5"), "JSON should contain pageCount in metadata");
        assertTrue(json.contains("\"documentDate\":\"2023-01-15\""), "JSON should contain documentDate in metadata");
    }
    
    @Test
    @DisplayName("Should deserialize from JSON correctly")
    void shouldDeserializeFromJsonCorrectly() throws Exception {
        // Given
        String documentId = UUID.randomUUID().toString();
        String applicationId = UUID.randomUUID().toString();
        String uploadedAt = "2023-01-20T10:15:30.000Z";
        String urlExpiresAt = "2023-01-20T11:15:30.000Z";
        
        String json = String.format("{\"id\":\"%s\",\"application_id\":\"%s\",\"type\":\"BANK_STATEMENT\",\"storage_path\":\"mca-documents-production/test-application/bank-statement.pdf\",\"classification\":\"VERIFIED\",\"uploaded_at\":\"%s\",\"metadata\":{\"pageCount\":5,\"documentDate\":\"2023-01-15\",\"confidenceScores\":{\"accountNumber\":0.95,\"bankName\":0.98}},\"download_url\":\"https://example.com/documents/test.pdf\",\"url_expires_at\":\"%s\",\"classification_confidence\":0.97}", 
                documentId, applicationId, uploadedAt, urlExpiresAt);
        
        // When
        DocumentResponseDTO dto = objectMapper.readValue(json, DocumentResponseDTO.class);
        
        // Then
        assertEquals(UUID.fromString(documentId), dto.getId(), "ID should be deserialized correctly");
        assertEquals(UUID.fromString(applicationId), dto.getApplicationId(), "Application ID should be deserialized correctly");
        assertEquals("BANK_STATEMENT", dto.getType(), "Type should be deserialized correctly");
        assertEquals("mca-documents-production/test-application/bank-statement.pdf", dto.getStoragePath(), "Storage path should be deserialized correctly");
        assertEquals("VERIFIED", dto.getClassification(), "Classification should be deserialized correctly");
        assertEquals("https://example.com/documents/test.pdf", dto.getDownloadUrl(), "Download URL should be deserialized correctly");
        assertEquals(0.97, dto.getClassificationConfidence(), "Classification confidence should be deserialized correctly");
        
        // Verify metadata
        assertNotNull(dto.getMetadata(), "Metadata should not be null");
        assertEquals(5, dto.getMetadataValue("pageCount"), "Page count metadata should be deserialized correctly");
        assertEquals("2023-01-15", dto.getMetadataValue("documentDate"), "Document date metadata should be deserialized correctly");
        
        // Verify confidence scores
        Map<String, Double> confidenceScores = dto.getConfidenceScores();
        assertNotNull(confidenceScores, "Confidence scores should not be null");
        assertEquals(0.95, confidenceScores.get("accountNumber"), "Account number confidence score should be deserialized correctly");
        assertEquals(0.98, confidenceScores.get("bankName"), "Bank name confidence score should be deserialized correctly");
    }
    
    @ParameterizedTest
    @DisplayName("Should validate URL validity correctly")
    @MethodSource("urlValidityProvider")
    void shouldValidateUrlValidityCorrectly(String downloadUrl, LocalDateTime urlExpiresAt, boolean expectedValidity) {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        dto.setDownloadUrl(downloadUrl);
        dto.setUrlExpiresAt(urlExpiresAt);
        
        // When/Then
        assertEquals(expectedValidity, dto.hasValidDownloadUrl(), "URL validity should be determined correctly");
    }
    
    @ParameterizedTest
    @DisplayName("Should determine classification confidence level correctly")
    @MethodSource("confidenceLevelProvider")
    void shouldDetermineClassificationConfidenceLevelCorrectly(Double confidence, boolean isHigh, boolean isMedium, boolean isLow) {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        dto.setClassificationConfidence(confidence);
        
        // When/Then
        assertEquals(isHigh, dto.hasHighClassificationConfidence(), "High confidence should be determined correctly");
        assertEquals(isMedium, dto.hasMediumClassificationConfidence(), "Medium confidence should be determined correctly");
        assertEquals(isLow, dto.hasLowClassificationConfidence(), "Low confidence should be determined correctly");
    }
    
    @Test
    @DisplayName("Should handle null classification confidence")
    void shouldHandleNullClassificationConfidence() {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        dto.setClassificationConfidence(null);
        
        // When/Then
        assertFalse(dto.hasHighClassificationConfidence(), "High confidence should be false for null");
        assertFalse(dto.hasMediumClassificationConfidence(), "Medium confidence should be false for null");
        assertFalse(dto.hasLowClassificationConfidence(), "Low confidence should be false for null");
    }
    
    @Test
    @DisplayName("Should get metadata values correctly")
    void shouldGetMetadataValuesCorrectly() {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("stringKey", "stringValue");
        metadata.put("intKey", 123);
        metadata.put("boolKey", true);
        dto.setMetadata(metadata);
        
        // When/Then
        assertEquals("stringValue", dto.getMetadataValue("stringKey"), "Should get string metadata correctly");
        assertEquals(123, dto.getMetadataValue("intKey"), "Should get integer metadata correctly");
        assertEquals(true, dto.getMetadataValue("boolKey"), "Should get boolean metadata correctly");
        assertNull(dto.getMetadataValue("nonexistent"), "Should return null for nonexistent metadata");
    }
    
    @Test
    @DisplayName("Should handle null metadata when getting values")
    void shouldHandleNullMetadataWhenGettingValues() {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        dto.setMetadata(null);
        
        // When/Then
        assertNull(dto.getMetadataValue("key"), "Should return null when metadata is null");
    }
    
    @Test
    @DisplayName("Should get confidence scores correctly")
    void shouldGetConfidenceScoresCorrectly() {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        Map<String, Object> metadata = new HashMap<>();
        
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("field1", 0.95);
        confidenceScores.put("field2", 0.85);
        
        metadata.put("confidenceScores", confidenceScores);
        dto.setMetadata(metadata);
        
        // When
        Map<String, Double> retrievedScores = dto.getConfidenceScores();
        
        // Then
        assertNotNull(retrievedScores, "Confidence scores should not be null");
        assertEquals(2, retrievedScores.size(), "Confidence scores should have correct number of entries");
        assertEquals(0.95, retrievedScores.get("field1"), "Field1 confidence score should be correct");
        assertEquals(0.85, retrievedScores.get("field2"), "Field2 confidence score should be correct");
    }
    
    @Test
    @DisplayName("Should handle missing confidence scores in metadata")
    void shouldHandleMissingConfidenceScoresInMetadata() {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("otherKey", "value");
        dto.setMetadata(metadata);
        
        // When
        Map<String, Double> retrievedScores = dto.getConfidenceScores();
        
        // Then
        assertNotNull(retrievedScores, "Confidence scores should not be null even when missing");
        assertTrue(retrievedScores.isEmpty(), "Confidence scores should be empty when missing");
    }
    
    @Test
    @DisplayName("Should get confidence score for specific field correctly")
    void shouldGetConfidenceScoreForSpecificFieldCorrectly() {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        Map<String, Object> metadata = new HashMap<>();
        
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("field1", 0.95);
        confidenceScores.put("field2", 0.85);
        
        metadata.put("confidenceScores", confidenceScores);
        dto.setMetadata(metadata);
        
        // When/Then
        assertEquals(0.95, dto.getConfidenceScore("field1"), "Field1 confidence score should be correct");
        assertEquals(0.85, dto.getConfidenceScore("field2"), "Field2 confidence score should be correct");
        assertNull(dto.getConfidenceScore("nonexistent"), "Should return null for nonexistent field");
    }
    
    @Test
    @DisplayName("Should handle missing confidence scores when getting specific field")
    void shouldHandleMissingConfidenceScoresWhenGettingSpecificField() {
        // Given
        DocumentResponseDTO dto = new DocumentResponseDTO();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("otherKey", "value");
        dto.setMetadata(metadata);
        
        // When/Then
        assertNull(dto.getConfidenceScore("field"), "Should return null when confidence scores are missing");
    }
    
    @Test
    @DisplayName("Should create a valid DTO using builder pattern")
    void shouldCreateValidDTOUsingBuilderPattern() {
        // Given/When
        DocumentResponseDTO dto = new DocumentResponseDTO.Builder()
                .withId(testId)
                .withApplicationId(testApplicationId)
                .withType("BANK_STATEMENT")
                .withStoragePath("mca-documents-production/test-application/bank-statement.pdf")
                .withClassification("VERIFIED")
                .withUploadedAt(testUploadedAt)
                .withDownloadUrl("https://example.com/documents/test.pdf")
                .withUrlExpiresAt(testUrlExpiresAt)
                .withClassificationConfidence(0.97)
                .withMetadata(createTestMetadata())
                .build();
        
        // Then
        assertEquals(testId, dto.getId(), "Builder should set ID correctly");
        assertEquals(testApplicationId, dto.getApplicationId(), "Builder should set application ID correctly");
        assertEquals("BANK_STATEMENT", dto.getType(), "Builder should set type correctly");
        assertEquals("mca-documents-production/test-application/bank-statement.pdf", dto.getStoragePath(), "Builder should set storage path correctly");
        assertEquals("VERIFIED", dto.getClassification(), "Builder should set classification correctly");
        assertEquals(testUploadedAt, dto.getUploadedAt(), "Builder should set uploaded at correctly");
        assertEquals("https://example.com/documents/test.pdf", dto.getDownloadUrl(), "Builder should set download URL correctly");
        assertEquals(testUrlExpiresAt, dto.getUrlExpiresAt(), "Builder should set URL expiry correctly");
        assertEquals(0.97, dto.getClassificationConfidence(), "Builder should set classification confidence correctly");
        assertNotNull(dto.getMetadata(), "Builder should set metadata correctly");
        assertEquals(5, dto.getMetadataValue("pageCount"), "Builder should set metadata values correctly");
    }
    
    @Test
    @DisplayName("Should create a valid DTO using builder from Document entity")
    void shouldCreateValidDTOUsingBuilderFromDocumentEntity() {
        // Given
        Document document = createTestDocument();
        
        // When
        DocumentResponseDTO dto = new DocumentResponseDTO.Builder(document)
                .withDownloadUrl("https://example.com/documents/test.pdf")
                .withUrlExpiresAt(testUrlExpiresAt)
                .build();
        
        // Then
        assertEquals(testId, dto.getId(), "Builder should set ID from document");
        assertEquals(testApplicationId, dto.getApplicationId(), "Builder should set application ID from document");
        assertEquals("BANK_STATEMENT", dto.getType(), "Builder should set type from document");
        assertEquals("mca-documents-production/test-application/bank-statement.pdf", dto.getStoragePath(), "Builder should set storage path from document");
        assertEquals("VERIFIED", dto.getClassification(), "Builder should set classification from document");
        assertEquals(testUploadedAt, dto.getUploadedAt(), "Builder should set uploaded at from document");
        assertEquals("https://example.com/documents/test.pdf", dto.getDownloadUrl(), "Builder should set download URL correctly");
        assertEquals(testUrlExpiresAt, dto.getUrlExpiresAt(), "Builder should set URL expiry correctly");
        assertEquals(0.97, dto.getClassificationConfidence(), "Builder should set classification confidence from document");
    }
    
    @Test
    @DisplayName("Should handle DocumentType enum in builder")
    void shouldHandleDocumentTypeEnumInBuilder() {
        // Given/When
        DocumentResponseDTO dto = new DocumentResponseDTO.Builder()
                .withType(DocumentType.BANK_STATEMENT)
                .build();
        
        // Then
        assertEquals("BANK_STATEMENT", dto.getType(), "Builder should handle DocumentType enum correctly");
    }
    
    /**
     * Creates a test Document entity with sample data.
     * 
     * @return A Document entity with test data
     */
    private Document createTestDocument() {
        Document document = new Document();
        document.setId(testId);
        document.setApplicationId(testApplicationId);
        document.setType(DocumentType.BANK_STATEMENT);
        document.setStoragePath("mca-documents-production/test-application/bank-statement.pdf");
        document.setClassification(DocumentClassification.VERIFIED);
        document.setUploadedAt(testUploadedAt);
        document.setMetadata(createTestMetadata());
        
        // Add confidence score
        document.addMetadata("confidenceScore", 0.97);
        
        return document;
    }
    
    /**
     * Creates test metadata for document.
     * 
     * @return A map with test metadata
     */
    private Map<String, Object> createTestMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("pageCount", 5);
        metadata.put("documentDate", "2023-01-15");
        
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("accountNumber", 0.95);
        confidenceScores.put("bankName", 0.98);
        metadata.put("confidenceScores", confidenceScores);
        
        return metadata;
    }
}