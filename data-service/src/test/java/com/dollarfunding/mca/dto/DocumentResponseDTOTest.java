package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

/**
 * Test class for {@link DocumentResponseDTO}.
 * Validates document metadata structure, JSON serialization/deserialization,
 * pre-signed URL generation, document classification confidence scores, and entity conversion.
 */
@ExtendWith(MockitoExtension.class)
public class DocumentResponseDTOTest {

    private static final ObjectMapper objectMapper = new ObjectMapper();
    
    @Mock
    private Document document;
    
    @Mock
    private Application application;
    
    private UUID documentId;
    private UUID applicationId;
    private LocalDateTime uploadedAt;
    private Map<String, Object> metadata;
    
    @BeforeEach
    void setUp() {
        // Initialize test data
        documentId = UUID.randomUUID();
        applicationId = UUID.randomUUID();
        uploadedAt = LocalDateTime.now();
        
        // Create metadata with classification confidence scores
        metadata = new HashMap<>();
        metadata.put("confidence", 0.95);
        metadata.put("pageCount", 3);
        metadata.put("fileSize", 1024);
        
        Map<String, Double> classificationScores = new HashMap<>();
        classificationScores.put("BANK_STATEMENT", 0.95);
        classificationScores.put("TAX_RETURN", 0.03);
        classificationScores.put("BUSINESS_LICENSE", 0.02);
        metadata.put("classificationScores", classificationScores);
        
        // Configure mock document
        when(document.getId()).thenReturn(documentId);
        when(document.getApplication()).thenReturn(application);
        when(application.getId()).thenReturn(applicationId);
        when(document.getType()).thenReturn(DocumentType.BANK_STATEMENT);
        when(document.getStoragePath()).thenReturn("documents/" + applicationId + "/" + documentId + ".pdf");
        when(document.getClassification()).thenReturn("BANK_STATEMENT");
        when(document.getUploadedAt()).thenReturn(uploadedAt);
        when(document.getMetadata()).thenReturn(metadata);
    }
    
    @Test
    @DisplayName("Should convert Document entity to DocumentResponseDTO correctly")
    void shouldConvertEntityToDTO() {
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        
        // Then
        assertThat(dto).isNotNull();
        assertThat(dto.getId()).isEqualTo(documentId);
        assertThat(dto.getApplicationId()).isEqualTo(applicationId);
        assertThat(dto.getType()).isEqualTo(DocumentType.BANK_STATEMENT.name());
        assertThat(dto.getStoragePath()).isEqualTo("documents/" + applicationId + "/" + documentId + ".pdf");
        assertThat(dto.getClassification()).isEqualTo("BANK_STATEMENT");
        assertThat(dto.getUploadedAt()).isEqualTo(uploadedAt);
        assertThat(dto.getMetadata()).isEqualTo(metadata);
    }
    
    @Test
    @DisplayName("Should include pre-signed URL for secure document access")
    void shouldIncludePreSignedUrl() {
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        
        // Then
        assertThat(dto.getPreSignedUrl()).isNotNull();
        assertThat(dto.getPreSignedUrl()).startsWith("https://");
        assertThat(dto.getPreSignedUrl()).contains(documentId.toString());
        assertThat(dto.getPreSignedUrl()).contains("Expires=");
        assertThat(dto.getPreSignedUrl()).contains("Signature=");
    }
    
    @Test
    @DisplayName("Should include document classification confidence scores")
    void shouldIncludeClassificationConfidenceScores() {
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        
        // Then
        assertThat(dto.getMetadata()).containsKey("classificationScores");
        
        @SuppressWarnings("unchecked")
        Map<String, Double> scores = (Map<String, Double>) dto.getMetadata().get("classificationScores");
        
        assertThat(scores).isNotNull();
        assertThat(scores).containsKey("BANK_STATEMENT");
        assertThat(scores.get("BANK_STATEMENT")).isEqualTo(0.95);
        assertThat(scores).containsKey("TAX_RETURN");
        assertThat(scores.get("TAX_RETURN")).isEqualTo(0.03);
        assertThat(scores).containsKey("BUSINESS_LICENSE");
        assertThat(scores.get("BUSINESS_LICENSE")).isEqualTo(0.02);
    }
    
    @Test
    @DisplayName("Should serialize to JSON correctly")
    void shouldSerializeToJson() throws Exception {
        // Given
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        
        // When
        String json = objectMapper.writeValueAsString(dto);
        
        // Then
        assertThat(json).isNotNull();
        assertThat(json).contains(documentId.toString());
        assertThat(json).contains(applicationId.toString());
        assertThat(json).contains("BANK_STATEMENT");
        assertThat(json).contains("preSignedUrl");
        assertThat(json).contains("classificationScores");
    }
    
    @Test
    @DisplayName("Should deserialize from JSON correctly")
    void shouldDeserializeFromJson() throws Exception {
        // Given
        DocumentResponseDTO originalDto = DocumentResponseDTO.fromEntity(document);
        String json = objectMapper.writeValueAsString(originalDto);
        
        // When
        DocumentResponseDTO deserializedDto = objectMapper.readValue(json, DocumentResponseDTO.class);
        
        // Then
        assertThat(deserializedDto).isNotNull();
        assertThat(deserializedDto.getId()).isEqualTo(documentId);
        assertThat(deserializedDto.getApplicationId()).isEqualTo(applicationId);
        assertThat(deserializedDto.getType()).isEqualTo(DocumentType.BANK_STATEMENT.name());
        assertThat(deserializedDto.getClassification()).isEqualTo("BANK_STATEMENT");
        assertThat(deserializedDto.getPreSignedUrl()).isEqualTo(originalDto.getPreSignedUrl());
    }
    
    @Test
    @DisplayName("Should handle null metadata gracefully")
    void shouldHandleNullMetadata() {
        // Given
        when(document.getMetadata()).thenReturn(null);
        
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        
        // Then
        assertThat(dto.getMetadata()).isNotNull();
        assertThat(dto.getMetadata()).isEmpty();
    }
    
    @Test
    @DisplayName("Should handle document with no classification")
    void shouldHandleNoClassification() {
        // Given
        when(document.getClassification()).thenReturn(null);
        
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        
        // Then
        assertThat(dto.getClassification()).isNull();
    }
    
    @Test
    @DisplayName("Should validate pre-signed URL expiration time")
    void shouldValidatePreSignedUrlExpiration() {
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        String preSignedUrl = dto.getPreSignedUrl();
        
        // Then
        assertThat(preSignedUrl).contains("Expires=");
        
        // Extract expiration timestamp from URL
        int expiresIndex = preSignedUrl.indexOf("Expires=");
        int andIndex = preSignedUrl.indexOf("&", expiresIndex);
        String expiresValue = preSignedUrl.substring(expiresIndex + 8, andIndex != -1 ? andIndex : preSignedUrl.length());
        long expirationTimestamp = Long.parseLong(expiresValue);
        
        // Verify expiration is in the future (at least 5 minutes)
        long currentTimestamp = System.currentTimeMillis() / 1000;
        assertThat(expirationTimestamp).isGreaterThan(currentTimestamp + 300);
    }
    
    @Test
    @DisplayName("Should include document metadata fields")
    void shouldIncludeDocumentMetadataFields() {
        // When
        DocumentResponseDTO dto = DocumentResponseDTO.fromEntity(document);
        
        // Then
        assertThat(dto.getMetadata()).containsKey("confidence");
        assertThat(dto.getMetadata().get("confidence")).isEqualTo(0.95);
        
        assertThat(dto.getMetadata()).containsKey("pageCount");
        assertThat(dto.getMetadata().get("pageCount")).isEqualTo(3);
        
        assertThat(dto.getMetadata()).containsKey("fileSize");
        assertThat(dto.getMetadata().get("fileSize")).isEqualTo(1024);
    }
}