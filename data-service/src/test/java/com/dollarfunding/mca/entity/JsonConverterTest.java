package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.JsonUtil;
import com.dollarfunding.mca.util.JsonUtil.JsonConversionException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import javax.persistence.AttributeConverter;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

/**
 * Unit tests for custom JPA converters that handle JSON serialization and deserialization for entity fields.
 * Tests include validation of conversion between Java objects and JSON strings, handling of null values,
 * error cases, and integration with entity classes.
 */
@ExtendWith(MockitoExtension.class)
public class JsonConverterTest {

    private ObjectMapper objectMapper;
    
    @Mock
    private Application application;
    
    @Mock
    private Document document;
    
    @Mock
    private MerchantDetails merchantDetails;
    
    // Test data
    private Map<String, Object> testMetadata;
    private Map<String, Object> testAddress;
    
    @BeforeEach
    void setUp() {
        objectMapper = JsonUtil.getObjectMapper();
        
        // Initialize test metadata for Application and Document entities
        testMetadata = new HashMap<>();
        testMetadata.put("source", "email");
        testMetadata.put("processingTime", 120);
        testMetadata.put("automationScore", 0.95);
        testMetadata.put("confidenceScore", 0.98);
        
        // Initialize test address for MerchantDetails entity
        testAddress = new HashMap<>();
        testAddress.put("street", "123 Main St");
        testAddress.put("city", "New York");
        testAddress.put("state", "NY");
        testAddress.put("zipCode", "10001");
        testAddress.put("country", "USA");
    }
    
    /**
     * Test class for the JSON converter used in the Application entity for the metadata field.
     */
    public static class ApplicationMetadataConverter implements AttributeConverter<Map<String, Object>, String> {
        
        @Override
        public String convertToDatabaseColumn(Map<String, Object> attribute) {
            if (attribute == null) {
                return null;
            }
            try {
                return JsonUtil.toJson(attribute);
            } catch (JsonConversionException e) {
                throw new RuntimeException("Error converting application metadata to JSON", e);
            }
        }
        
        @Override
        public Map<String, Object> convertToEntityAttribute(String dbData) {
            if (dbData == null || dbData.isEmpty()) {
                return new HashMap<>();
            }
            try {
                return JsonUtil.fromJson(dbData, new TypeReference<Map<String, Object>>() {});
            } catch (JsonConversionException e) {
                throw new RuntimeException("Error converting JSON to application metadata", e);
            }
        }
    }
    
    /**
     * Test class for the JSON converter used in the Document entity for the metadata field.
     */
    public static class DocumentMetadataConverter implements AttributeConverter<Map<String, Object>, String> {
        
        @Override
        public String convertToDatabaseColumn(Map<String, Object> attribute) {
            if (attribute == null) {
                return null;
            }
            try {
                return JsonUtil.toJson(attribute);
            } catch (JsonConversionException e) {
                throw new RuntimeException("Error converting document metadata to JSON", e);
            }
        }
        
        @Override
        public Map<String, Object> convertToEntityAttribute(String dbData) {
            if (dbData == null || dbData.isEmpty()) {
                return new HashMap<>();
            }
            try {
                return JsonUtil.fromJson(dbData, new TypeReference<Map<String, Object>>() {});
            } catch (JsonConversionException e) {
                throw new RuntimeException("Error converting JSON to document metadata", e);
            }
        }
    }
    
    /**
     * Test class for the JSON converter used in the MerchantDetails entity for the address field.
     */
    public static class AddressConverter implements AttributeConverter<Map<String, Object>, String> {
        
        @Override
        public String convertToDatabaseColumn(Map<String, Object> attribute) {
            if (attribute == null) {
                return null;
            }
            try {
                return JsonUtil.toJson(attribute);
            } catch (JsonConversionException e) {
                throw new RuntimeException("Error converting address to JSON", e);
            }
        }
        
        @Override
        public Map<String, Object> convertToEntityAttribute(String dbData) {
            if (dbData == null || dbData.isEmpty()) {
                return new HashMap<>();
            }
            try {
                return JsonUtil.fromJson(dbData, new TypeReference<Map<String, Object>>() {});
            } catch (JsonConversionException e) {
                throw new RuntimeException("Error converting JSON to address", e);
            }
        }
    }
    
    @Test
    @DisplayName("Test Application metadata conversion to JSON string")
    void testApplicationMetadataToJson() throws JsonConversionException {
        // Arrange
        ApplicationMetadataConverter converter = new ApplicationMetadataConverter();
        
        // Act
        String json = converter.convertToDatabaseColumn(testMetadata);
        
        // Assert
        assertNotNull(json);
        assertTrue(json.contains("\"source\":\"email\""));
        assertTrue(json.contains("\"processingTime\":120"));
        assertTrue(json.contains("\"automationScore\":0.95"));
        assertTrue(json.contains("\"confidenceScore\":0.98"));
        
        // Verify the JSON is valid and can be parsed back to a JsonNode
        JsonNode jsonNode = objectMapper.readTree(json);
        assertEquals("email", jsonNode.get("source").asText());
        assertEquals(120, jsonNode.get("processingTime").asInt());
        assertEquals(0.95, jsonNode.get("automationScore").asDouble());
        assertEquals(0.98, jsonNode.get("confidenceScore").asDouble());
    }
    
    @Test
    @DisplayName("Test JSON string conversion to Application metadata")
    void testJsonToApplicationMetadata() throws IOException, JsonConversionException {
        // Arrange
        ApplicationMetadataConverter converter = new ApplicationMetadataConverter();
        String json = JsonUtil.toJson(testMetadata);
        
        // Act
        Map<String, Object> result = converter.convertToEntityAttribute(json);
        
        // Assert
        assertNotNull(result);
        assertEquals(4, result.size());
        assertEquals("email", result.get("source"));
        assertEquals(120, result.get("processingTime"));
        assertEquals(0.95, result.get("automationScore"));
        assertEquals(0.98, result.get("confidenceScore"));
    }
    
    @Test
    @DisplayName("Test Document metadata conversion to JSON string")
    void testDocumentMetadataToJson() throws JsonConversionException {
        // Arrange
        DocumentMetadataConverter converter = new DocumentMetadataConverter();
        Map<String, Object> documentMetadata = new HashMap<>(testMetadata);
        documentMetadata.put("documentType", "BANK_STATEMENT");
        documentMetadata.put("pageCount", 5);
        documentMetadata.put("extractedFields", 12);
        
        // Act
        String json = converter.convertToDatabaseColumn(documentMetadata);
        
        // Assert
        assertNotNull(json);
        assertTrue(json.contains("\"documentType\":\"BANK_STATEMENT\""));
        assertTrue(json.contains("\"pageCount\":5"));
        assertTrue(json.contains("\"extractedFields\":12"));
        
        // Verify the JSON is valid and can be parsed back to a JsonNode
        JsonNode jsonNode = objectMapper.readTree(json);
        assertEquals("BANK_STATEMENT", jsonNode.get("documentType").asText());
        assertEquals(5, jsonNode.get("pageCount").asInt());
        assertEquals(12, jsonNode.get("extractedFields").asInt());
    }
    
    @Test
    @DisplayName("Test JSON string conversion to Document metadata")
    void testJsonToDocumentMetadata() throws IOException, JsonConversionException {
        // Arrange
        DocumentMetadataConverter converter = new DocumentMetadataConverter();
        Map<String, Object> documentMetadata = new HashMap<>(testMetadata);
        documentMetadata.put("documentType", "BANK_STATEMENT");
        documentMetadata.put("pageCount", 5);
        documentMetadata.put("extractedFields", 12);
        String json = JsonUtil.toJson(documentMetadata);
        
        // Act
        Map<String, Object> result = converter.convertToEntityAttribute(json);
        
        // Assert
        assertNotNull(result);
        assertEquals(7, result.size());
        assertEquals("BANK_STATEMENT", result.get("documentType"));
        assertEquals(5, result.get("pageCount"));
        assertEquals(12, result.get("extractedFields"));
    }
    
    @Test
    @DisplayName("Test MerchantDetails address conversion to JSON string")
    void testAddressToJson() throws JsonConversionException {
        // Arrange
        AddressConverter converter = new AddressConverter();
        
        // Act
        String json = converter.convertToDatabaseColumn(testAddress);
        
        // Assert
        assertNotNull(json);
        assertTrue(json.contains("\"street\":\"123 Main St\""));
        assertTrue(json.contains("\"city\":\"New York\""));
        assertTrue(json.contains("\"state\":\"NY\""));
        assertTrue(json.contains("\"zipCode\":\"10001\""));
        assertTrue(json.contains("\"country\":\"USA\""));
        
        // Verify the JSON is valid and can be parsed back to a JsonNode
        JsonNode jsonNode = objectMapper.readTree(json);
        assertEquals("123 Main St", jsonNode.get("street").asText());
        assertEquals("New York", jsonNode.get("city").asText());
        assertEquals("NY", jsonNode.get("state").asText());
        assertEquals("10001", jsonNode.get("zipCode").asText());
        assertEquals("USA", jsonNode.get("country").asText());
    }
    
    @Test
    @DisplayName("Test JSON string conversion to MerchantDetails address")
    void testJsonToAddress() throws IOException, JsonConversionException {
        // Arrange
        AddressConverter converter = new AddressConverter();
        String json = JsonUtil.toJson(testAddress);
        
        // Act
        Map<String, Object> result = converter.convertToEntityAttribute(json);
        
        // Assert
        assertNotNull(result);
        assertEquals(5, result.size());
        assertEquals("123 Main St", result.get("street"));
        assertEquals("New York", result.get("city"));
        assertEquals("NY", result.get("state"));
        assertEquals("10001", result.get("zipCode"));
        assertEquals("USA", result.get("country"));
    }
    
    @Test
    @DisplayName("Test handling null values in converters")
    void testNullHandling() {
        // Arrange
        ApplicationMetadataConverter appConverter = new ApplicationMetadataConverter();
        DocumentMetadataConverter docConverter = new DocumentMetadataConverter();
        AddressConverter addressConverter = new AddressConverter();
        
        // Act & Assert - null to JSON
        assertNull(appConverter.convertToDatabaseColumn(null));
        assertNull(docConverter.convertToDatabaseColumn(null));
        assertNull(addressConverter.convertToDatabaseColumn(null));
        
        // Act & Assert - null/empty JSON to object
        assertTrue(appConverter.convertToEntityAttribute(null).isEmpty());
        assertTrue(docConverter.convertToEntityAttribute(null).isEmpty());
        assertTrue(addressConverter.convertToEntityAttribute(null).isEmpty());
        
        assertTrue(appConverter.convertToEntityAttribute("").isEmpty());
        assertTrue(docConverter.convertToEntityAttribute("").isEmpty());
        assertTrue(addressConverter.convertToEntityAttribute("").isEmpty());
    }
    
    @Test
    @DisplayName("Test error handling for invalid JSON")
    void testInvalidJsonHandling() {
        // Arrange
        ApplicationMetadataConverter converter = new ApplicationMetadataConverter();
        String invalidJson = "{\"source\":\"email\", invalid json}";
        
        // Act & Assert
        Exception exception = assertThrows(RuntimeException.class, () -> {
            converter.convertToEntityAttribute(invalidJson);
        });
        
        assertTrue(exception.getMessage().contains("Error converting JSON to application metadata"));
    }
    
    @Test
    @DisplayName("Test complex nested object conversion")
    void testComplexNestedObjectConversion() throws JsonConversionException {
        // Arrange
        ApplicationMetadataConverter converter = new ApplicationMetadataConverter();
        Map<String, Object> complexMetadata = new HashMap<>();
        
        // Create nested objects
        Map<String, Object> extractionDetails = new HashMap<>();
        extractionDetails.put("engine", "OCR-v2");
        extractionDetails.put("accuracy", 0.97);
        
        Map<String, Object> processingStats = new HashMap<>();
        processingStats.put("startTime", "2023-05-15T10:30:00Z");
        processingStats.put("endTime", "2023-05-15T10:30:05Z");
        processingStats.put("duration", 5000);
        
        // Add nested objects to main metadata
        complexMetadata.put("source", "email");
        complexMetadata.put("extractionDetails", extractionDetails);
        complexMetadata.put("processingStats", processingStats);
        
        // Act
        String json = converter.convertToDatabaseColumn(complexMetadata);
        Map<String, Object> result = converter.convertToEntityAttribute(json);
        
        // Assert
        assertNotNull(result);
        assertEquals(3, result.size());
        assertEquals("email", result.get("source"));
        
        // Verify nested objects
        @SuppressWarnings("unchecked")
        Map<String, Object> resultExtractionDetails = (Map<String, Object>) result.get("extractionDetails");
        assertNotNull(resultExtractionDetails);
        assertEquals("OCR-v2", resultExtractionDetails.get("engine"));
        assertEquals(0.97, resultExtractionDetails.get("accuracy"));
        
        @SuppressWarnings("unchecked")
        Map<String, Object> resultProcessingStats = (Map<String, Object>) result.get("processingStats");
        assertNotNull(resultProcessingStats);
        assertEquals("2023-05-15T10:30:00Z", resultProcessingStats.get("startTime"));
        assertEquals("2023-05-15T10:30:05Z", resultProcessingStats.get("endTime"));
        assertEquals(5000, resultProcessingStats.get("duration"));
    }
    
    @Test
    @DisplayName("Test integration with Application entity")
    void testIntegrationWithApplicationEntity() throws JsonConversionException {
        // Arrange
        ApplicationMetadataConverter converter = new ApplicationMetadataConverter();
        String jsonMetadata = JsonUtil.toJson(testMetadata);
        
        // Mock the entity behavior
        when(application.getMetadata()).thenReturn(testMetadata);
        
        // Act
        String dbColumn = converter.convertToDatabaseColumn(application.getMetadata());
        Map<String, Object> entityAttribute = converter.convertToEntityAttribute(dbColumn);
        
        // Assert
        assertEquals(jsonMetadata, dbColumn);
        assertEquals(testMetadata, entityAttribute);
    }
    
    @Test
    @DisplayName("Test integration with Document entity")
    void testIntegrationWithDocumentEntity() throws JsonConversionException {
        // Arrange
        DocumentMetadataConverter converter = new DocumentMetadataConverter();
        Map<String, Object> documentMetadata = new HashMap<>(testMetadata);
        documentMetadata.put("documentType", "BANK_STATEMENT");
        String jsonMetadata = JsonUtil.toJson(documentMetadata);
        
        // Mock the entity behavior
        when(document.getMetadata()).thenReturn(documentMetadata);
        
        // Act
        String dbColumn = converter.convertToDatabaseColumn(document.getMetadata());
        Map<String, Object> entityAttribute = converter.convertToEntityAttribute(dbColumn);
        
        // Assert
        assertEquals(jsonMetadata, dbColumn);
        assertEquals(documentMetadata, entityAttribute);
    }
    
    @Test
    @DisplayName("Test integration with MerchantDetails entity")
    void testIntegrationWithMerchantDetailsEntity() throws JsonConversionException {
        // Arrange
        AddressConverter converter = new AddressConverter();
        String jsonAddress = JsonUtil.toJson(testAddress);
        
        // Mock the entity behavior
        when(merchantDetails.getAddress()).thenReturn(testAddress);
        
        // Act
        String dbColumn = converter.convertToDatabaseColumn(merchantDetails.getAddress());
        Map<String, Object> entityAttribute = converter.convertToEntityAttribute(dbColumn);
        
        // Assert
        assertEquals(jsonAddress, dbColumn);
        assertEquals(testAddress, entityAttribute);
    }
    
    @Test
    @DisplayName("Test JSON with confidence scores for document metadata")
    void testJsonWithConfidenceScores() throws JsonConversionException {
        // Arrange
        DocumentMetadataConverter converter = new DocumentMetadataConverter();
        Map<String, Object> documentMetadata = new HashMap<>();
        
        // Create metadata with confidence scores for extracted fields
        Map<String, Object> extractedFields = new HashMap<>();
        
        Map<String, Object> accountNumberField = new HashMap<>();
        accountNumberField.put("value", "123456789");
        accountNumberField.put("confidence", 0.98);
        extractedFields.put("accountNumber", accountNumberField);
        
        Map<String, Object> balanceField = new HashMap<>();
        balanceField.put("value", "5000.00");
        balanceField.put("confidence", 0.95);
        extractedFields.put("balance", balanceField);
        
        Map<String, Object> dateField = new HashMap<>();
        dateField.put("value", "2023-05-15");
        dateField.put("confidence", 0.99);
        extractedFields.put("statementDate", dateField);
        
        documentMetadata.put("documentType", "BANK_STATEMENT");
        documentMetadata.put("extractedFields", extractedFields);
        documentMetadata.put("overallConfidence", 0.97);
        
        // Act
        String json = converter.convertToDatabaseColumn(documentMetadata);
        Map<String, Object> result = converter.convertToEntityAttribute(json);
        
        // Assert
        assertNotNull(result);
        assertEquals(3, result.size());
        assertEquals("BANK_STATEMENT", result.get("documentType"));
        assertEquals(0.97, result.get("overallConfidence"));
        
        // Verify extracted fields with confidence scores
        @SuppressWarnings("unchecked")
        Map<String, Object> resultExtractedFields = (Map<String, Object>) result.get("extractedFields");
        assertNotNull(resultExtractedFields);
        
        @SuppressWarnings("unchecked")
        Map<String, Object> resultAccountNumber = (Map<String, Object>) resultExtractedFields.get("accountNumber");
        assertEquals("123456789", resultAccountNumber.get("value"));
        assertEquals(0.98, resultAccountNumber.get("confidence"));
        
        @SuppressWarnings("unchecked")
        Map<String, Object> resultBalance = (Map<String, Object>) resultExtractedFields.get("balance");
        assertEquals("5000.00", resultBalance.get("value"));
        assertEquals(0.95, resultBalance.get("confidence"));
    }
}