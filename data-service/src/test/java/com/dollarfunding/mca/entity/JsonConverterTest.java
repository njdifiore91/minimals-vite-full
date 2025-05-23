package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Nested;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for JSON conversion functionality in entity classes.
 * 
 * Tests the conversion between Java objects and JSON strings for entity fields,
 * handling of null values, error cases, and integration with entity classes.
 */
@DisplayName("JSON Converter Tests")
public class JsonConverterTest {

    private Map<String, Object> testMetadata;
    private Map<String, Object> testAddress;
    private Application application;
    private Document document;
    private MerchantDetails merchantDetails;
    private UUID testId;
    
    @BeforeEach
    void setUp() {
        testId = UUID.randomUUID();
        
        // Set up test metadata for Application and Document
        testMetadata = new HashMap<>();
        testMetadata.put("source", "email");
        testMetadata.put("priority", 1);
        testMetadata.put("tags", Arrays.asList("urgent", "new-customer"));
        Map<String, Object> processingDetails = new HashMap<>();
        processingDetails.put("processingTime", 2500);
        processingDetails.put("automationScore", 0.95);
        testMetadata.put("processingDetails", processingDetails);
        
        // Set up test address for MerchantDetails
        testAddress = new HashMap<>();
        testAddress.put("street", "123 Main St");
        testAddress.put("city", "New York");
        testAddress.put("state", "NY");
        testAddress.put("zip", "10001");
        testAddress.put("country", "USA");
        
        // Create test entities
        application = new Application(ApplicationStatus.NEW, testMetadata, 
                LocalDateTime.now(), LocalDateTime.now(), ReviewStatus.NOT_REVIEWED);
        
        document = new Document(testId, DocumentType.BANK_STATEMENT, "mca-documents-production/test.pdf",
                DocumentClassification.VERIFIED, LocalDateTime.now(), testMetadata);
        
        merchantDetails = new MerchantDetails(testId, "Test Company LLC", "Test Co", "12-3456789",
                testAddress, "Retail", new BigDecimal("1000000.00"));
    }
    
    @Nested
    @DisplayName("Object to JSON String Conversion Tests")
    class ObjectToJsonStringConversionTests {
        
        @Test
        @DisplayName("Should convert Map to JSON string")
        void shouldConvertMapToJsonString() throws JsonUtil.JsonConversionException {
            // Convert Map to JSON string
            String json = JsonUtil.toJson(testMetadata);
            
            // Verify JSON string contains expected values
            assertTrue(json.contains("\"source\":\"email\""));
            assertTrue(json.contains("\"priority\":1"));
            assertTrue(json.contains("\"tags\":[\"urgent\",\"new-customer\"]"));
            assertTrue(json.contains("\"processingDetails\":"));
            assertTrue(json.contains("\"processingTime\":2500"));
            assertTrue(json.contains("\"automationScore\":0.95"));
        }
        
        @Test
        @DisplayName("Should convert empty Map to empty JSON object")
        void shouldConvertEmptyMapToEmptyJsonObject() throws JsonUtil.JsonConversionException {
            // Convert empty Map to JSON string
            String json = JsonUtil.toJson(new HashMap<>());
            
            // Verify JSON string is an empty object
            assertEquals("{}", json);
        }
        
        @Test
        @DisplayName("Should convert null to null JSON")
        void shouldConvertNullToNullJson() throws JsonUtil.JsonConversionException {
            // Convert null to JSON string
            String json = JsonUtil.toJson(null);
            
            // Verify JSON string is null
            assertEquals("null", json);
        }
    }
    
    @Nested
    @DisplayName("JSON String to Object Conversion Tests")
    class JsonStringToObjectConversionTests {
        
        @Test
        @DisplayName("Should convert JSON string to Map")
        void shouldConvertJsonStringToMap() throws JsonUtil.JsonConversionException {
            // Create JSON string
            String json = "{\"name\":\"Test\",\"value\":123,\"active\":true}";
            
            // Convert JSON string to Map
            Map<String, Object> result = JsonUtil.fromJson(json, new TypeReference<Map<String, Object>>() {});
            
            // Verify Map contains expected values
            assertEquals("Test", result.get("name"));
            assertEquals(123, result.get("value"));
            assertEquals(true, result.get("active"));
        }
        
        @Test
        @DisplayName("Should convert empty JSON object to empty Map")
        void shouldConvertEmptyJsonObjectToEmptyMap() throws JsonUtil.JsonConversionException {
            // Convert empty JSON object to Map
            Map<String, Object> result = JsonUtil.fromJson("{}", new TypeReference<Map<String, Object>>() {});
            
            // Verify Map is empty
            assertTrue(result.isEmpty());
        }
        
        @Test
        @DisplayName("Should throw exception for invalid JSON")
        void shouldThrowExceptionForInvalidJson() {
            // Create invalid JSON string
            String invalidJson = "{\"name\":\"Test\"value\":123}";
            
            // Verify exception is thrown for invalid JSON
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.fromJson(invalidJson, new TypeReference<Map<String, Object>>() {});
            });
        }
    }
    
    @Nested
    @DisplayName("Null Handling Tests")
    class NullHandlingTests {
        
        @Test
        @DisplayName("Application should handle null metadata")
        void applicationShouldHandleNullMetadata() {
            // Create Application with null metadata
            Application app = new Application(ApplicationStatus.NEW, null, 
                    LocalDateTime.now(), LocalDateTime.now(), ReviewStatus.NOT_REVIEWED);
            
            // Verify metadata JSON is empty object
            assertEquals("{}", app.getMetadataJson());
            
            // Verify metadata Map is empty but not null
            assertNotNull(app.getMetadata());
            assertTrue(app.getMetadata().isEmpty());
        }
        
        @Test
        @DisplayName("Document should handle null metadata")
        void documentShouldHandleNullMetadata() {
            // Create Document with null metadata
            Document doc = new Document(testId, DocumentType.BANK_STATEMENT, "test.pdf",
                    DocumentClassification.VERIFIED, LocalDateTime.now(), null);
            
            // Verify metadata JSON is empty object
            assertEquals("{}", doc.getMetadataJson());
            
            // Verify metadata Map is empty but not null
            assertNotNull(doc.getMetadata());
            assertTrue(doc.getMetadata().isEmpty());
        }
        
        @Test
        @DisplayName("MerchantDetails should handle null address")
        void merchantDetailsShouldHandleNullAddress() {
            // Create MerchantDetails with null address
            MerchantDetails merchant = new MerchantDetails(testId, "Test Company LLC", "Test Co", "12-3456789",
                    null, "Retail", new BigDecimal("1000000.00"));
            
            // Verify address JSON is empty object
            assertEquals("{}", merchant.getAddressJson());
            
            // Verify address Map is empty but not null
            assertNotNull(merchant.getAddress());
            assertTrue(merchant.getAddress().isEmpty());
        }
    }
    
    @Nested
    @DisplayName("Error Handling Tests")
    class ErrorHandlingTests {
        
        @Test
        @DisplayName("Application should handle invalid metadata JSON")
        void applicationShouldHandleInvalidMetadataJson() {
            // Create Application
            Application app = new Application();
            
            // Set invalid JSON string
            app.setMetadataJson("{\"name\":\"Test\"value\":123}");
            
            // Verify metadata Map is empty but not null
            assertNotNull(app.getMetadata());
            assertTrue(app.getMetadata().isEmpty());
        }
        
        @Test
        @DisplayName("Document should handle invalid metadata JSON")
        void documentShouldHandleInvalidMetadataJson() {
            // Create Document
            Document doc = new Document();
            
            // Set invalid JSON string
            doc.setMetadataJson("{\"name\":\"Test\"value\":123}");
            
            // Verify metadata Map is empty but not null
            assertNotNull(doc.getMetadata());
            assertTrue(doc.getMetadata().isEmpty());
        }
        
        @Test
        @DisplayName("MerchantDetails should handle invalid address JSON")
        void merchantDetailsShouldHandleInvalidAddressJson() {
            // Create MerchantDetails
            MerchantDetails merchant = new MerchantDetails();
            
            // Set invalid JSON string
            merchant.setAddressJson("{\"street\":\"123 Main St\"city\":\"New York\"}");
            
            // Verify address Map is empty but not null
            assertNotNull(merchant.getAddress());
            assertTrue(merchant.getAddress().isEmpty());
        }
    }
    
    @Nested
    @DisplayName("Entity Integration Tests")
    class EntityIntegrationTests {
        
        @Test
        @DisplayName("Application should maintain metadata integrity")
        void applicationShouldMaintainMetadataIntegrity() {
            // Verify initial metadata is set correctly
            assertEquals(testMetadata, application.getMetadata());
            
            // Add new metadata
            application.addMetadata("status", "pending");
            
            // Verify metadata was updated
            assertEquals("pending", application.getMetadataValue("status"));
            
            // Verify JSON was updated
            assertTrue(application.getMetadataJson().contains("\"status\":\"pending\""));
        }
        
        @Test
        @DisplayName("Document should maintain metadata integrity")
        void documentShouldMaintainMetadataIntegrity() {
            // Verify initial metadata is set correctly
            assertEquals(testMetadata, document.getMetadata());
            
            // Add new metadata
            document.addMetadata("confidenceScore", 0.98);
            
            // Verify metadata was updated
            assertEquals(0.98, document.getConfidenceScore());
            
            // Verify JSON was updated
            assertTrue(document.getMetadataJson().contains("\"confidenceScore\":0.98"));
        }
        
        @Test
        @DisplayName("MerchantDetails should maintain address integrity")
        void merchantDetailsShouldMaintainAddressIntegrity() {
            // Verify initial address is set correctly
            assertEquals(testAddress, merchantDetails.getAddress());
            
            // Update address field
            merchantDetails.setAddressField("street", "456 Broadway");
            
            // Verify address was updated
            assertEquals("456 Broadway", merchantDetails.getAddressField("street"));
            
            // Verify JSON was updated
            assertTrue(merchantDetails.getAddressJson().contains("\"street\":\"456 Broadway\""));
        }
    }
    
    @Nested
    @DisplayName("Complex Object Conversion Tests")
    class ComplexObjectConversionTests {
        
        @Test
        @DisplayName("Should handle nested objects in metadata")
        void shouldHandleNestedObjectsInMetadata() {
            // Create complex nested metadata
            Map<String, Object> complexMetadata = new HashMap<>();
            complexMetadata.put("id", testId.toString());
            
            Map<String, Object> customer = new HashMap<>();
            customer.put("name", "John Doe");
            customer.put("email", "john@example.com");
            
            Map<String, Object> address = new HashMap<>();
            address.put("street", "123 Main St");
            address.put("city", "New York");
            address.put("state", "NY");
            address.put("zip", "10001");
            
            customer.put("address", address);
            complexMetadata.put("customer", customer);
            
            List<Map<String, Object>> documents = Arrays.asList(
                Map.of("type", "BANK_STATEMENT", "filename", "bank.pdf"),
                Map.of("type", "TAX_RETURN", "filename", "tax.pdf")
            );
            complexMetadata.put("documents", documents);
            
            // Set complex metadata on Application
            application.setMetadata(complexMetadata);
            
            // Convert to JSON and back to verify integrity
            String json = application.getMetadataJson();
            application.setMetadataJson(json);
            Map<String, Object> retrievedMetadata = application.getMetadata();
            
            // Verify complex structure is maintained
            assertEquals(testId.toString(), retrievedMetadata.get("id"));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> retrievedCustomer = (Map<String, Object>) retrievedMetadata.get("customer");
            assertNotNull(retrievedCustomer);
            assertEquals("John Doe", retrievedCustomer.get("name"));
            assertEquals("john@example.com", retrievedCustomer.get("email"));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> retrievedAddress = (Map<String, Object>) retrievedCustomer.get("address");
            assertNotNull(retrievedAddress);
            assertEquals("123 Main St", retrievedAddress.get("street"));
            assertEquals("New York", retrievedAddress.get("city"));
            
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> retrievedDocuments = (List<Map<String, Object>>) retrievedMetadata.get("documents");
            assertNotNull(retrievedDocuments);
            assertEquals(2, retrievedDocuments.size());
            assertEquals("BANK_STATEMENT", retrievedDocuments.get(0).get("type"));
            assertEquals("tax.pdf", retrievedDocuments.get(1).get("filename"));
        }
        
        @Test
        @DisplayName("Should handle arrays in metadata")
        void shouldHandleArraysInMetadata() {
            // Create metadata with arrays
            Map<String, Object> arrayMetadata = new HashMap<>();
            arrayMetadata.put("strings", Arrays.asList("one", "two", "three"));
            arrayMetadata.put("numbers", Arrays.asList(1, 2, 3, 4, 5));
            arrayMetadata.put("mixed", Arrays.asList("string", 123, true, null));
            
            // Set array metadata on Document
            document.setMetadata(arrayMetadata);
            
            // Convert to JSON and back to verify integrity
            String json = document.getMetadataJson();
            document.setMetadataJson(json);
            Map<String, Object> retrievedMetadata = document.getMetadata();
            
            // Verify arrays are maintained
            @SuppressWarnings("unchecked")
            List<String> strings = (List<String>) retrievedMetadata.get("strings");
            assertNotNull(strings);
            assertEquals(3, strings.size());
            assertEquals("one", strings.get(0));
            assertEquals("three", strings.get(2));
            
            @SuppressWarnings("unchecked")
            List<Integer> numbers = (List<Integer>) retrievedMetadata.get("numbers");
            assertNotNull(numbers);
            assertEquals(5, numbers.size());
            assertEquals(1, numbers.get(0));
            assertEquals(5, numbers.get(4));
            
            @SuppressWarnings("unchecked")
            List<Object> mixed = (List<Object>) retrievedMetadata.get("mixed");
            assertNotNull(mixed);
            assertEquals(4, mixed.size());
            assertEquals("string", mixed.get(0));
            assertEquals(123, mixed.get(1));
            assertEquals(true, mixed.get(2));
            assertNull(mixed.get(3));
        }
    }
    
    @Nested
    @DisplayName("Persistence Simulation Tests")
    class PersistenceSimulationTests {
        
        @Test
        @DisplayName("Should simulate persistence and retrieval of Application metadata")
        void shouldSimulatePersistenceAndRetrievalOfApplicationMetadata() {
            // Get JSON representation (simulates database storage)
            String storedJson = application.getMetadataJson();
            
            // Create new Application (simulates retrieval from database)
            Application retrievedApp = new Application();
            retrievedApp.setMetadataJson(storedJson);
            
            // Verify metadata was correctly retrieved
            Map<String, Object> retrievedMetadata = retrievedApp.getMetadata();
            assertEquals("email", retrievedMetadata.get("source"));
            assertEquals(1, retrievedMetadata.get("priority"));
            
            @SuppressWarnings("unchecked")
            List<String> tags = (List<String>) retrievedMetadata.get("tags");
            assertNotNull(tags);
            assertEquals(2, tags.size());
            assertEquals("urgent", tags.get(0));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> processingDetails = (Map<String, Object>) retrievedMetadata.get("processingDetails");
            assertNotNull(processingDetails);
            assertEquals(2500, processingDetails.get("processingTime"));
            assertEquals(0.95, processingDetails.get("automationScore"));
        }
        
        @Test
        @DisplayName("Should simulate persistence and retrieval of Document metadata")
        void shouldSimulatePersistenceAndRetrievalOfDocumentMetadata() {
            // Get JSON representation (simulates database storage)
            String storedJson = document.getMetadataJson();
            
            // Create new Document (simulates retrieval from database)
            Document retrievedDoc = new Document();
            retrievedDoc.setMetadataJson(storedJson);
            
            // Verify metadata was correctly retrieved
            Map<String, Object> retrievedMetadata = retrievedDoc.getMetadata();
            assertEquals(testMetadata, retrievedMetadata);
        }
        
        @Test
        @DisplayName("Should simulate persistence and retrieval of MerchantDetails address")
        void shouldSimulatePersistenceAndRetrievalOfMerchantDetailsAddress() {
            // Get JSON representation (simulates database storage)
            String storedJson = merchantDetails.getAddressJson();
            
            // Create new MerchantDetails (simulates retrieval from database)
            MerchantDetails retrievedMerchant = new MerchantDetails();
            retrievedMerchant.setAddressJson(storedJson);
            
            // Verify address was correctly retrieved
            Map<String, Object> retrievedAddress = retrievedMerchant.getAddress();
            assertEquals(testAddress, retrievedAddress);
            assertEquals("123 Main St", retrievedMerchant.getAddressField("street"));
            assertEquals("New York", retrievedMerchant.getAddressField("city"));
            assertEquals("NY", retrievedMerchant.getAddressField("state"));
            assertEquals("10001", retrievedMerchant.getAddressField("zip"));
            assertEquals("USA", retrievedMerchant.getAddressField("country"));
        }
    }
}