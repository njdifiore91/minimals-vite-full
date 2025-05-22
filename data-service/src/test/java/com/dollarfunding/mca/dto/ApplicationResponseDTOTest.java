package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link ApplicationResponseDTO} that validates the application data structure,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * Tests ensure that the DTO properly represents application data, includes associated
 * merchant details and document references, and formats audit fields consistently.
 */
public class ApplicationResponseDTOTest {

    private ObjectMapper objectMapper;
    private Application application;
    private ApplicationResponseDTO applicationResponseDTO;
    private static final UUID APPLICATION_ID = UUID.fromString("00000000-0000-0000-0000-000000000001");
    private static final LocalDateTime CREATED_AT = LocalDateTime.of(2023, 1, 1, 10, 0, 0);
    private static final LocalDateTime UPDATED_AT = LocalDateTime.of(2023, 1, 2, 15, 30, 0);

    @BeforeEach
    void setUp() {
        // Configure ObjectMapper with JavaTimeModule for LocalDateTime serialization
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        
        // Create test application entity with all required fields
        application = new Application();
        application.setId(APPLICATION_ID);
        application.setStatus(ApplicationStatus.PROCESSING);
        application.setReviewStatus(ReviewStatus.IN_REVIEW);
        application.setCreatedAt(CREATED_AT);
        application.setUpdatedAt(UPDATED_AT);
        
        // Create metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("confidence_score", 0.95);
        metadata.put("processing_time_ms", 2500);
        application.setMetadata(metadata);
        
        // Create merchant details
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setLegalName("Acme Corporation");
        merchantDetails.setDbaName("Acme Inc.");
        merchantDetails.setEin("12-3456789");
        Map<String, String> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "Anytown");
        address.put("state", "CA");
        address.put("zip", "90210");
        merchantDetails.setAddress(address);
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(new BigDecimal("500000.00"));
        merchantDetails.setApplication(application);
        application.setMerchantDetails(merchantDetails);
        
        // Create documents
        List<Document> documents = new ArrayList<>();
        Document doc1 = new Document();
        doc1.setId(UUID.randomUUID());
        doc1.setType(DocumentType.BANK_STATEMENT);
        doc1.setClassification("Bank Statement");
        doc1.setStoragePath("mca-documents-production/00001/bank_statement.pdf");
        doc1.setUploadedAt(LocalDateTime.now());
        doc1.setApplication(application);
        
        Document doc2 = new Document();
        doc2.setId(UUID.randomUUID());
        doc2.setType(DocumentType.ID_VERIFICATION);
        doc2.setClassification("Driver's License");
        doc2.setStoragePath("mca-documents-production/00001/id_verification.pdf");
        doc2.setUploadedAt(LocalDateTime.now());
        doc2.setApplication(application);
        
        documents.add(doc1);
        documents.add(doc2);
        application.setDocuments(documents);
        
        // Convert entity to DTO
        applicationResponseDTO = ApplicationResponseDTO.fromEntity(application);
    }

    @Test
    @DisplayName("Should convert Application entity to ApplicationResponseDTO correctly")
    void shouldConvertEntityToDTO() {
        // Assert basic fields
        assertEquals(APPLICATION_ID, applicationResponseDTO.getId());
        assertEquals(ApplicationStatus.PROCESSING, applicationResponseDTO.getStatus());
        assertEquals(ReviewStatus.IN_REVIEW, applicationResponseDTO.getReviewStatus());
        assertEquals(CREATED_AT, applicationResponseDTO.getCreatedAt());
        assertEquals(UPDATED_AT, applicationResponseDTO.getUpdatedAt());
        
        // Assert metadata
        assertNotNull(applicationResponseDTO.getMetadata());
        assertEquals("email", applicationResponseDTO.getMetadata().get("source"));
        assertEquals(0.95, applicationResponseDTO.getMetadata().get("confidence_score"));
        assertEquals(2500, applicationResponseDTO.getMetadata().get("processing_time_ms"));
        
        // Assert merchant details
        assertNotNull(applicationResponseDTO.getMerchantDetails());
        assertEquals("A*************n", applicationResponseDTO.getMerchantDetails().getLegalName());
        assertEquals("A*******.", applicationResponseDTO.getMerchantDetails().getDbaName());
        assertEquals("**-***6789", applicationResponseDTO.getMerchantDetails().getEin());
        assertEquals("Technology", applicationResponseDTO.getMerchantDetails().getIndustry());
        assertEquals(new BigDecimal("500000.00"), applicationResponseDTO.getMerchantDetails().getRevenue());
        
        // Assert documents
        assertNotNull(applicationResponseDTO.getDocuments());
        assertEquals(2, applicationResponseDTO.getDocuments().size());
        assertEquals(DocumentType.BANK_STATEMENT, applicationResponseDTO.getDocuments().get(0).getType());
        assertEquals(DocumentType.ID_VERIFICATION, applicationResponseDTO.getDocuments().get(1).getType());
    }

    @Test
    @DisplayName("Should serialize ApplicationResponseDTO to JSON correctly")
    void shouldSerializeToJson() throws IOException {
        // Serialize DTO to JSON
        String json = objectMapper.writeValueAsString(applicationResponseDTO);
        
        // Assert JSON contains expected fields
        assertTrue(json.contains("\"id\":\"" + APPLICATION_ID + "\""));
        assertTrue(json.contains("\"status\":\"PROCESSING\""));
        assertTrue(json.contains("\"review_status\":\"IN_REVIEW\""));
        assertTrue(json.contains("\"created_at\":"));
        assertTrue(json.contains("\"updated_at\":"));
        assertTrue(json.contains("\"metadata\":"));
        assertTrue(json.contains("\"merchant_details\":"));
        assertTrue(json.contains("\"documents\":"));
        
        // Deserialize JSON back to DTO
        ApplicationResponseDTO deserializedDTO = objectMapper.readValue(json, ApplicationResponseDTO.class);
        
        // Assert deserialized DTO matches original
        assertEquals(applicationResponseDTO.getId(), deserializedDTO.getId());
        assertEquals(applicationResponseDTO.getStatus(), deserializedDTO.getStatus());
        assertEquals(applicationResponseDTO.getReviewStatus(), deserializedDTO.getReviewStatus());
    }

    @Test
    @DisplayName("Should format audit fields correctly")
    void shouldFormatAuditFieldsCorrectly() throws IOException {
        // Serialize DTO to JSON
        String json = objectMapper.writeValueAsString(applicationResponseDTO);
        
        // Assert created_at and updated_at are formatted correctly
        assertTrue(json.contains("\"created_at\":\"2023-01-01T10:00:00.000Z\""));
        assertTrue(json.contains("\"updated_at\":\"2023-01-02T15:30:00.000Z\""));
    }

    @Test
    @DisplayName("Should handle null associated entities gracefully")
    void shouldHandleNullAssociatedEntities() {
        // Create application without merchant details and documents
        Application appWithoutAssociations = new Application();
        appWithoutAssociations.setId(UUID.randomUUID());
        appWithoutAssociations.setStatus(ApplicationStatus.NEW);
        appWithoutAssociations.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        appWithoutAssociations.setCreatedAt(LocalDateTime.now());
        appWithoutAssociations.setUpdatedAt(LocalDateTime.now());
        
        // Convert to DTO
        ApplicationResponseDTO dtoWithoutAssociations = ApplicationResponseDTO.fromEntity(appWithoutAssociations);
        
        // Assert null associations are handled correctly
        assertNotNull(dtoWithoutAssociations);
        assertNull(dtoWithoutAssociations.getMerchantDetails());
        assertNull(dtoWithoutAssociations.getDocuments());
    }

    @Test
    @DisplayName("Should convert list of Application entities to list of DTOs correctly")
    void shouldConvertEntityListToDTOList() {
        // Create list of applications
        List<Application> applications = new ArrayList<>();
        applications.add(application);
        
        Application secondApp = new Application();
        secondApp.setId(UUID.randomUUID());
        secondApp.setStatus(ApplicationStatus.APPROVED);
        secondApp.setReviewStatus(ReviewStatus.APPROVED);
        secondApp.setCreatedAt(LocalDateTime.now());
        secondApp.setUpdatedAt(LocalDateTime.now());
        applications.add(secondApp);
        
        // Convert to DTO list
        List<ApplicationResponseDTO> dtoList = ApplicationResponseDTO.fromEntities(applications);
        
        // Assert conversion
        assertNotNull(dtoList);
        assertEquals(2, dtoList.size());
        assertEquals(application.getId(), dtoList.get(0).getId());
        assertEquals(secondApp.getId(), dtoList.get(1).getId());
    }

    @Test
    @DisplayName("Should handle null input gracefully in fromEntity method")
    void shouldHandleNullInputInFromEntity() {
        // Call fromEntity with null
        ApplicationResponseDTO dto = ApplicationResponseDTO.fromEntity(null);
        
        // Assert null is returned
        assertNull(dto);
    }

    @Test
    @DisplayName("Should handle null input gracefully in fromEntities method")
    void shouldHandleNullInputInFromEntities() {
        // Call fromEntities with null
        List<ApplicationResponseDTO> dtoList = ApplicationResponseDTO.fromEntities(null);
        
        // Assert null is returned
        assertNull(dtoList);
    }

    @Test
    @DisplayName("Should generate correct status summary")
    void shouldGenerateCorrectStatusSummary() {
        // Get status summary
        String summary = applicationResponseDTO.getStatusSummary();
        
        // Assert summary contains expected information
        assertTrue(summary.contains(APPLICATION_ID.toString()));
        assertTrue(summary.contains("PROCESSING"));
        assertTrue(summary.contains("IN_REVIEW"));
        assertTrue(summary.contains("A*************n"));
        assertTrue(summary.contains("2 document(s)"));
    }

    @Test
    @DisplayName("Should generate correct toString output")
    void shouldGenerateCorrectToString() {
        // Get toString output
        String toString = applicationResponseDTO.toString();
        
        // Assert toString contains expected information
        assertTrue(toString.contains(APPLICATION_ID.toString()));
        assertTrue(toString.contains("PROCESSING"));
        assertTrue(toString.contains("IN_REVIEW"));
        assertTrue(toString.contains("merchantDetails=present"));
        assertTrue(toString.contains("documents=2 documents"));
    }
}