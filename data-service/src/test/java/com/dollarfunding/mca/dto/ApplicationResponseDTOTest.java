package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.TestUtils;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link ApplicationResponseDTO} that validates the application data structure,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly represents application data,
 * includes associated merchant details and document references, and formats
 * audit fields consistently.
 */
@DisplayName("Application Response DTO Tests")
public class ApplicationResponseDTOTest {

    private ObjectMapper objectMapper;
    
    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
    }
    
    /**
     * Test data provider for different application statuses.
     */
    static Stream<Arguments> applicationStatusProvider() {
        return Stream.of(
            Arguments.of(ApplicationStatus.NEW, "NEW"),
            Arguments.of(ApplicationStatus.PENDING, "PENDING"),
            Arguments.of(ApplicationStatus.PROCESSING, "PROCESSING"),
            Arguments.of(ApplicationStatus.APPROVED, "APPROVED"),
            Arguments.of(ApplicationStatus.REJECTED, "REJECTED"),
            Arguments.of(ApplicationStatus.COMPLETED, "COMPLETED"),
            Arguments.of(ApplicationStatus.ERROR, "ERROR"),
            Arguments.of(ApplicationStatus.EXCEPTION, "EXCEPTION")
        );
    }
    
    /**
     * Test data provider for different review statuses.
     */
    static Stream<Arguments> reviewStatusProvider() {
        return Stream.of(
            Arguments.of(ReviewStatus.NOT_REVIEWED, "NOT_REVIEWED"),
            Arguments.of(ReviewStatus.IN_REVIEW, "IN_REVIEW"),
            Arguments.of(ReviewStatus.NEEDS_INFORMATION, "NEEDS_INFORMATION"),
            Arguments.of(ReviewStatus.APPROVED, "APPROVED"),
            Arguments.of(ReviewStatus.REJECTED, "REJECTED")
        );
    }

    @Test
    @DisplayName("Should create a valid DTO with default constructor")
    void shouldCreateValidDTOWithDefaultConstructor() {
        // Given/When
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertNotNull(dto.getMetadata(), "Metadata should be initialized");
        assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
        assertNotNull(dto.getDocuments(), "Documents should be initialized");
        assertTrue(dto.getDocuments().isEmpty(), "Documents should be empty");
    }
    
    @Test
    @DisplayName("Should create a valid DTO from Application entity with all details")
    void shouldCreateValidDTOFromApplicationEntityWithAllDetails() {
        // Given
        Application application = TestUtils.createRandomApplication();
        MerchantDetails merchantDetails = TestUtils.createRandomMerchantDetails(application);
        application.setMerchantDetails(merchantDetails);
        
        Document document1 = TestUtils.createRandomDocument(application);
        Document document2 = TestUtils.createRandomDocument(application);
        application.addDocument(document1);
        application.addDocument(document2);
        
        // When
        ApplicationResponseDTO dto = ApplicationResponseDTO.fromEntityWithAllDetails(application, false);
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertEquals(application.getId(), dto.getId(), "ID should match");
        assertEquals(application.getStatus().name(), dto.getStatus(), "Status should match");
        assertEquals(application.getReviewStatus().name(), dto.getReviewStatus(), "Review status should match");
        assertEquals(application.getCreatedAt(), dto.getCreatedAt(), "Created at should match");
        assertEquals(application.getUpdatedAt(), dto.getUpdatedAt(), "Updated at should match");
        assertEquals(application.getMetadata(), dto.getMetadata(), "Metadata should match");
        
        // Check merchant details
        assertNotNull(dto.getMerchantDetails(), "Merchant details should not be null");
        assertEquals(merchantDetails.getLegalName(), dto.getMerchantDetails().getLegalName(), "Legal name should match");
        
        // Check documents
        assertNotNull(dto.getDocuments(), "Documents should not be null");
        assertEquals(2, dto.getDocuments().size(), "Should have 2 documents");
    }
    
    @Test
    @DisplayName("Should create a valid DTO from Application entity with minimal details")
    void shouldCreateValidDTOFromApplicationEntityWithMinimalDetails() {
        // Given
        Application application = TestUtils.createRandomApplication();
        MerchantDetails merchantDetails = TestUtils.createRandomMerchantDetails(application);
        application.setMerchantDetails(merchantDetails);
        
        Document document = TestUtils.createRandomDocument(application);
        application.addDocument(document);
        
        // When
        ApplicationResponseDTO dto = ApplicationResponseDTO.fromEntityWithMinimalDetails(application);
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertEquals(application.getId(), dto.getId(), "ID should match");
        assertEquals(application.getStatus().name(), dto.getStatus(), "Status should match");
        assertEquals(application.getReviewStatus().name(), dto.getReviewStatus(), "Review status should match");
        assertEquals(application.getCreatedAt(), dto.getCreatedAt(), "Created at should match");
        assertEquals(application.getUpdatedAt(), dto.getUpdatedAt(), "Updated at should match");
        assertEquals(application.getMetadata(), dto.getMetadata(), "Metadata should match");
        
        // Check merchant details and documents are not included
        assertNull(dto.getMerchantDetails(), "Merchant details should be null");
        assertTrue(dto.getDocuments().isEmpty(), "Documents should be empty");
    }
    
    @Test
    @DisplayName("Should create a valid DTO from Application entity with masked PII")
    void shouldCreateValidDTOFromApplicationEntityWithMaskedPII() {
        // Given
        Application application = TestUtils.createRandomApplication();
        MerchantDetails merchantDetails = TestUtils.createRandomMerchantDetails(application);
        application.setMerchantDetails(merchantDetails);
        
        // When
        ApplicationResponseDTO dto = ApplicationResponseDTO.fromEntity(application, true, false, true);
        
        // Then
        assertNotNull(dto, "DTO should not be null");
        assertNotNull(dto.getMerchantDetails(), "Merchant details should not be null");
        
        // Check PII masking
        String legalName = dto.getMerchantDetails().getLegalName();
        assertNotEquals(merchantDetails.getLegalName(), legalName, "Legal name should be masked");
        assertTrue(legalName.contains("*"), "Legal name should contain asterisks");
    }
    
    @Test
    @DisplayName("Should return null when creating DTO from null entity")
    void shouldReturnNullWhenCreatingDTOFromNullEntity() {
        // When
        ApplicationResponseDTO dto = ApplicationResponseDTO.fromEntity(null, true, true, false);
        
        // Then
        assertNull(dto, "DTO should be null when entity is null");
    }
    
    @ParameterizedTest
    @DisplayName("Should correctly set and get application status")
    @MethodSource("applicationStatusProvider")
    void shouldCorrectlySetAndGetApplicationStatus(ApplicationStatus status, String expectedString) {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        
        // When
        dto.setStatus(status);
        
        // Then
        assertEquals(expectedString, dto.getStatus(), "Status string should match enum name");
        
        // When setting as string
        dto.setStatus(expectedString);
        
        // Then
        assertEquals(expectedString, dto.getStatus(), "Status string should match");
    }
    
    @ParameterizedTest
    @DisplayName("Should correctly set and get review status")
    @MethodSource("reviewStatusProvider")
    void shouldCorrectlySetAndGetReviewStatus(ReviewStatus status, String expectedString) {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        
        // When
        dto.setReviewStatus(status);
        
        // Then
        assertEquals(expectedString, dto.getReviewStatus(), "Review status string should match enum name");
        
        // When setting as string
        dto.setReviewStatus(expectedString);
        
        // Then
        assertEquals(expectedString, dto.getReviewStatus(), "Review status string should match");
    }
    
    @Test
    @DisplayName("Should correctly set and get metadata")
    void shouldCorrectlySetAndGetMetadata() {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 95.5);
        
        // When
        dto.setMetadata(metadata);
        
        // Then
        assertEquals(metadata, dto.getMetadata(), "Metadata should match");
        assertEquals("email", dto.getMetadataValue("source"), "Metadata source should match");
        assertEquals(95.5, dto.getMetadataValue("confidence"), "Metadata confidence should match");
        assertNull(dto.getMetadataValue("nonexistent"), "Nonexistent metadata should be null");
        
        // When setting null metadata
        dto.setMetadata(null);
        
        // Then
        assertNotNull(dto.getMetadata(), "Metadata should not be null when set to null");
        assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty when set to null");
    }
    
    @Test
    @DisplayName("Should correctly set and get documents")
    void shouldCorrectlySetAndGetDocuments() {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        List<DocumentResponseDTO> documents = new ArrayList<>();
        DocumentResponseDTO doc1 = new DocumentResponseDTO();
        doc1.setId(UUID.randomUUID());
        doc1.setType("BANK_STATEMENT");
        DocumentResponseDTO doc2 = new DocumentResponseDTO();
        doc2.setId(UUID.randomUUID());
        doc2.setType("TAX_RETURN");
        documents.add(doc1);
        documents.add(doc2);
        
        // When
        dto.setDocuments(documents);
        
        // Then
        assertEquals(documents, dto.getDocuments(), "Documents should match");
        assertEquals(2, dto.getDocuments().size(), "Should have 2 documents");
        
        // Test document counts by type
        Map<String, Integer> counts = dto.getDocumentCountsByType();
        assertEquals(2, counts.size(), "Should have 2 document types");
        assertEquals(1, counts.get("BANK_STATEMENT"), "Should have 1 bank statement");
        assertEquals(1, counts.get("TAX_RETURN"), "Should have 1 tax return");
        
        // Test getting documents by type
        List<DocumentResponseDTO> bankStatements = dto.getDocumentsByType("BANK_STATEMENT");
        assertEquals(1, bankStatements.size(), "Should have 1 bank statement");
        assertEquals(doc1.getId(), bankStatements.get(0).getId(), "Bank statement ID should match");
        
        // When setting null documents
        dto.setDocuments(null);
        
        // Then
        assertNotNull(dto.getDocuments(), "Documents should not be null when set to null");
        assertTrue(dto.getDocuments().isEmpty(), "Documents should be empty when set to null");
    }
    
    @Test
    @DisplayName("Should correctly format dates in JSON serialization")
    void shouldCorrectlyFormatDatesInJsonSerialization() throws Exception {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        LocalDateTime now = LocalDateTime.now();
        dto.setCreatedAt(now);
        dto.setUpdatedAt(now);
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        String expectedDateFormat = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"));
        assertTrue(json.contains("\"created_at\":\"" + expectedDateFormat + "\""), "JSON should contain formatted created_at");
        assertTrue(json.contains("\"updated_at\":\"" + expectedDateFormat + "\""), "JSON should contain formatted updated_at");
    }
    
    @Test
    @DisplayName("Should correctly serialize to JSON")
    void shouldCorrectlySerializeToJson() throws Exception {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        UUID id = UUID.randomUUID();
        dto.setId(id);
        dto.setStatus(ApplicationStatus.PROCESSING.name());
        dto.setReviewStatus(ReviewStatus.IN_REVIEW.name());
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence", 95.5);
        dto.setMetadata(metadata);
        
        LocalDateTime now = LocalDateTime.now();
        dto.setCreatedAt(now);
        dto.setUpdatedAt(now);
        
        dto.setProcessingTimeMinutes(3L);
        dto.setProcessedWithinTargetTime(true);
        dto.setHasAllRequiredDocuments(true);
        dto.setIsCompleted(false);
        dto.setIsActive(true);
        dto.setIsDecided(false);
        dto.setRequiresReview(true);
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertTrue(json.contains("\"id\":\"" + id + "\""), "JSON should contain id");
        assertTrue(json.contains("\"status\":\"PROCESSING\""), "JSON should contain status");
        assertTrue(json.contains("\"review_status\":\"IN_REVIEW\""), "JSON should contain review_status");
        assertTrue(json.contains("\"metadata\":"), "JSON should contain metadata");
        assertTrue(json.contains("\"source\":\"email\""), "JSON should contain metadata source");
        assertTrue(json.contains("\"confidence\":95.5"), "JSON should contain metadata confidence");
        assertTrue(json.contains("\"processing_time_minutes\":3"), "JSON should contain processing_time_minutes");
        assertTrue(json.contains("\"processed_within_target_time\":true"), "JSON should contain processed_within_target_time");
        assertTrue(json.contains("\"has_all_required_documents\":true"), "JSON should contain has_all_required_documents");
        assertTrue(json.contains("\"is_completed\":false"), "JSON should contain is_completed");
        assertTrue(json.contains("\"is_active\":true"), "JSON should contain is_active");
        assertTrue(json.contains("\"is_decided\":false"), "JSON should contain is_decided");
        assertTrue(json.contains("\"requires_review\":true"), "JSON should contain requires_review");
    }
    
    @Test
    @DisplayName("Should correctly deserialize from JSON")
    void shouldCorrectlyDeserializeFromJson() throws Exception {
        // Given
        UUID id = UUID.randomUUID();
        String createdAt = "2023-01-01T12:00:00.000Z";
        String updatedAt = "2023-01-02T12:00:00.000Z";
        
        String json = "{"
                + "\"id\":\"" + id + "\","
                + "\"status\":\"PROCESSING\","
                + "\"review_status\":\"IN_REVIEW\","
                + "\"metadata\":{\"source\":\"email\",\"confidence\":95.5},"
                + "\"created_at\":\"" + createdAt + "\","
                + "\"updated_at\":\"" + updatedAt + "\","
                + "\"processing_time_minutes\":3,"
                + "\"processed_within_target_time\":true,"
                + "\"has_all_required_documents\":true,"
                + "\"is_completed\":false,"
                + "\"is_active\":true,"
                + "\"is_decided\":false,"
                + "\"requires_review\":true"
                + "}";
        
        // When
        ApplicationResponseDTO dto = objectMapper.readValue(json, ApplicationResponseDTO.class);
        
        // Then
        assertEquals(id, dto.getId(), "ID should match");
        assertEquals("PROCESSING", dto.getStatus(), "Status should match");
        assertEquals("IN_REVIEW", dto.getReviewStatus(), "Review status should match");
        assertNotNull(dto.getMetadata(), "Metadata should not be null");
        assertEquals("email", dto.getMetadataValue("source"), "Metadata source should match");
        assertEquals(95.5, dto.getMetadataValue("confidence"), "Metadata confidence should match");
        assertEquals(3L, dto.getProcessingTimeMinutes(), "Processing time should match");
        assertTrue(dto.getProcessedWithinTargetTime(), "Processed within target time should match");
        assertTrue(dto.getHasAllRequiredDocuments(), "Has all required documents should match");
        assertFalse(dto.getIsCompleted(), "Is completed should match");
        assertTrue(dto.getIsActive(), "Is active should match");
        assertFalse(dto.getIsDecided(), "Is decided should match");
        assertTrue(dto.getRequiresReview(), "Requires review should match");
        
        // Check date parsing
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
        LocalDateTime expectedCreatedAt = LocalDateTime.parse(createdAt, formatter);
        LocalDateTime expectedUpdatedAt = LocalDateTime.parse(updatedAt, formatter);
        assertEquals(expectedCreatedAt, dto.getCreatedAt(), "Created at should match");
        assertEquals(expectedUpdatedAt, dto.getUpdatedAt(), "Updated at should match");
    }
    
    @Test
    @DisplayName("Should correctly handle merchant details and documents in JSON")
    void shouldCorrectlyHandleMerchantDetailsAndDocumentsInJson() throws Exception {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        dto.setId(UUID.randomUUID());
        dto.setStatus(ApplicationStatus.PROCESSING.name());
        
        // Add merchant details
        MerchantDetailsResponseDTO merchantDetails = new MerchantDetailsResponseDTO();
        merchantDetails.setId(1L);
        merchantDetails.setLegalName("Test Business");
        dto.setMerchantDetails(merchantDetails);
        
        // Add documents
        List<DocumentResponseDTO> documents = new ArrayList<>();
        DocumentResponseDTO doc1 = new DocumentResponseDTO();
        doc1.setId(UUID.randomUUID());
        doc1.setType("BANK_STATEMENT");
        documents.add(doc1);
        dto.setDocuments(documents);
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        ApplicationResponseDTO deserializedDto = objectMapper.readValue(json, ApplicationResponseDTO.class);
        
        // Then
        assertNotNull(deserializedDto.getMerchantDetails(), "Merchant details should not be null");
        assertEquals("Test Business", deserializedDto.getMerchantDetails().getLegalName(), "Legal name should match");
        
        assertNotNull(deserializedDto.getDocuments(), "Documents should not be null");
        assertEquals(1, deserializedDto.getDocuments().size(), "Should have 1 document");
        assertEquals("BANK_STATEMENT", deserializedDto.getDocuments().get(0).getType(), "Document type should match");
    }
    
    @Test
    @DisplayName("Should correctly check if application has merchant details and documents")
    void shouldCorrectlyCheckIfApplicationHasMerchantDetailsAndDocuments() {
        // Given
        ApplicationResponseDTO dto = new ApplicationResponseDTO();
        
        // When/Then - No merchant details or documents
        assertFalse(dto.hasMerchantDetails(), "Should not have merchant details");
        assertFalse(dto.hasDocuments(), "Should not have documents");
        
        // When - Add merchant details
        MerchantDetailsResponseDTO merchantDetails = new MerchantDetailsResponseDTO();
        dto.setMerchantDetails(merchantDetails);
        
        // Then
        assertTrue(dto.hasMerchantDetails(), "Should have merchant details");
        assertFalse(dto.hasDocuments(), "Should not have documents");
        
        // When - Add documents
        List<DocumentResponseDTO> documents = new ArrayList<>();
        DocumentResponseDTO doc = new DocumentResponseDTO();
        documents.add(doc);
        dto.setDocuments(documents);
        
        // Then
        assertTrue(dto.hasMerchantDetails(), "Should have merchant details");
        assertTrue(dto.hasDocuments(), "Should have documents");
    }
    
    @Test
    @DisplayName("Should correctly build DTO using builder pattern")
    void shouldCorrectlyBuildDTOUsingBuilderPattern() {
        // Given
        UUID id = UUID.randomUUID();
        LocalDateTime now = LocalDateTime.now();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        
        // When
        ApplicationResponseDTO dto = new ApplicationResponseDTO.Builder()
                .withId(id)
                .withStatus(ApplicationStatus.APPROVED)
                .withReviewStatus(ReviewStatus.APPROVED)
                .withMetadata(metadata)
                .withCreatedAt(now)
                .withUpdatedAt(now)
                .withProcessingTimeMinutes(3L)
                .withProcessedWithinTargetTime(true)
                .withHasAllRequiredDocuments(true)
                .withIsCompleted(true)
                .withIsActive(false)
                .withIsDecided(true)
                .withRequiresReview(false)
                .build();
        
        // Then
        assertEquals(id, dto.getId(), "ID should match");
        assertEquals("APPROVED", dto.getStatus(), "Status should match");
        assertEquals("APPROVED", dto.getReviewStatus(), "Review status should match");
        assertEquals(metadata, dto.getMetadata(), "Metadata should match");
        assertEquals(now, dto.getCreatedAt(), "Created at should match");
        assertEquals(now, dto.getUpdatedAt(), "Updated at should match");
        assertEquals(3L, dto.getProcessingTimeMinutes(), "Processing time should match");
        assertTrue(dto.getProcessedWithinTargetTime(), "Processed within target time should match");
        assertTrue(dto.getHasAllRequiredDocuments(), "Has all required documents should match");
        assertTrue(dto.getIsCompleted(), "Is completed should match");
        assertFalse(dto.getIsActive(), "Is active should match");
        assertTrue(dto.getIsDecided(), "Is decided should match");
        assertFalse(dto.getRequiresReview(), "Requires review should match");
    }
    
    @Test
    @DisplayName("Should correctly build DTO from Application entity using builder pattern")
    void shouldCorrectlyBuildDTOFromApplicationEntityUsingBuilderPattern() {
        // Given
        Application application = TestUtils.createRandomApplication();
        
        // When
        ApplicationResponseDTO dto = new ApplicationResponseDTO.Builder(application).build();
        
        // Then
        assertEquals(application.getId(), dto.getId(), "ID should match");
        assertEquals(application.getStatus().name(), dto.getStatus(), "Status should match");
        assertEquals(application.getReviewStatus().name(), dto.getReviewStatus(), "Review status should match");
        assertEquals(application.getMetadata(), dto.getMetadata(), "Metadata should match");
        assertEquals(application.getCreatedAt(), dto.getCreatedAt(), "Created at should match");
        assertEquals(application.getUpdatedAt(), dto.getUpdatedAt(), "Updated at should match");
    }
    
    @Test
    @DisplayName("Should correctly add document to builder")
    void shouldCorrectlyAddDocumentToBuilder() {
        // Given
        DocumentResponseDTO doc = new DocumentResponseDTO();
        doc.setId(UUID.randomUUID());
        doc.setType("BANK_STATEMENT");
        
        // When
        ApplicationResponseDTO dto = new ApplicationResponseDTO.Builder()
                .addDocument(doc)
                .build();
        
        // Then
        assertNotNull(dto.getDocuments(), "Documents should not be null");
        assertEquals(1, dto.getDocuments().size(), "Should have 1 document");
        assertEquals(doc.getId(), dto.getDocuments().get(0).getId(), "Document ID should match");
    }
    
    @Test
    @DisplayName("Should correctly handle null values in builder")
    void shouldCorrectlyHandleNullValuesInBuilder() {
        // When
        ApplicationResponseDTO dto = new ApplicationResponseDTO.Builder()
                .withId(null)
                .withStatus((String) null)
                .withReviewStatus((String) null)
                .withMetadata(null)
                .withCreatedAt(null)
                .withUpdatedAt(null)
                .withMerchantDetails(null)
                .withDocuments(null)
                .withProcessingTimeMinutes(null)
                .withProcessedWithinTargetTime(null)
                .withHasAllRequiredDocuments(null)
                .withIsCompleted(null)
                .withIsActive(null)
                .withIsDecided(null)
                .withRequiresReview(null)
                .build();
        
        // Then
        assertNull(dto.getId(), "ID should be null");
        assertNull(dto.getStatus(), "Status should be null");
        assertNull(dto.getReviewStatus(), "Review status should be null");
        assertNotNull(dto.getMetadata(), "Metadata should not be null");
        assertTrue(dto.getMetadata().isEmpty(), "Metadata should be empty");
        assertNull(dto.getCreatedAt(), "Created at should be null");
        assertNull(dto.getUpdatedAt(), "Updated at should be null");
        assertNull(dto.getMerchantDetails(), "Merchant details should be null");
        assertNotNull(dto.getDocuments(), "Documents should not be null");
        assertTrue(dto.getDocuments().isEmpty(), "Documents should be empty");
        assertNull(dto.getProcessingTimeMinutes(), "Processing time should be null");
        assertNull(dto.getProcessedWithinTargetTime(), "Processed within target time should be null");
        assertNull(dto.getHasAllRequiredDocuments(), "Has all required documents should be null");
        assertNull(dto.getIsCompleted(), "Is completed should be null");
        assertNull(dto.getIsActive(), "Is active should be null");
        assertNull(dto.getIsDecided(), "Is decided should be null");
        assertNull(dto.getRequiresReview(), "Requires review should be null");
    }
    
    @Test
    @DisplayName("Should correctly convert list of entities to list of DTOs")
    void shouldCorrectlyConvertListOfEntitiesToListOfDTOs() {
        // Given
        List<Application> applications = new ArrayList<>();
        Application app1 = TestUtils.createRandomApplication();
        Application app2 = TestUtils.createRandomApplication();
        applications.add(app1);
        applications.add(app2);
        
        // When
        List<ApplicationResponseDTO> dtos = ApplicationResponseDTO.fromEntities(applications, false, false, true);
        
        // Then
        assertNotNull(dtos, "DTOs should not be null");
        assertEquals(2, dtos.size(), "Should have 2 DTOs");
        assertEquals(app1.getId(), dtos.get(0).getId(), "First DTO ID should match");
        assertEquals(app2.getId(), dtos.get(1).getId(), "Second DTO ID should match");
    }
    
    @Test
    @DisplayName("Should return empty list when converting null list of entities")
    void shouldReturnEmptyListWhenConvertingNullListOfEntities() {
        // When
        List<ApplicationResponseDTO> dtos = ApplicationResponseDTO.fromEntities(null, false, false, true);
        
        // Then
        assertNotNull(dtos, "DTOs should not be null");
        assertTrue(dtos.isEmpty(), "DTOs should be empty");
    }
}