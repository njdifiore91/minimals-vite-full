package com.dollarfunding.mca.util;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link JsonUtil} class.
 * 
 * Tests verify the JSON serialization and deserialization functionality, including:
 * - Conversion between Java objects and JSON strings
 * - Handling of complex types and nested objects
 * - Custom serializers/deserializers for specific data types
 * - Dynamic JSON manipulation using JsonNode
 * - Error handling for malformed JSON
 * - JSON schema validation
 * - JSON transformation and filtering
 */
@DisplayName("JsonUtil Tests")
class JsonUtilTest {

    // Test data classes
    static class SimpleTestObject {
        private String stringValue;
        private int intValue;
        private boolean boolValue;
        
        public SimpleTestObject() {
            // Default constructor for Jackson
        }
        
        public SimpleTestObject(String stringValue, int intValue, boolean boolValue) {
            this.stringValue = stringValue;
            this.intValue = intValue;
            this.boolValue = boolValue;
        }
        
        public String getStringValue() { return stringValue; }
        public void setStringValue(String stringValue) { this.stringValue = stringValue; }
        
        public int getIntValue() { return intValue; }
        public void setIntValue(int intValue) { this.intValue = intValue; }
        
        public boolean isBoolValue() { return boolValue; }
        public void setBoolValue(boolean boolValue) { this.boolValue = boolValue; }
        
        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            SimpleTestObject that = (SimpleTestObject) o;
            return intValue == that.intValue && 
                   boolValue == that.boolValue && 
                   (stringValue != null ? stringValue.equals(that.stringValue) : that.stringValue == null);
        }
    }
    
    static class ComplexTestObject {
        private String name;
        private List<SimpleTestObject> items;
        private Map<String, Object> metadata;
        private LocalDateTime timestamp;
        
        public ComplexTestObject() {
            // Default constructor for Jackson
        }
        
        public ComplexTestObject(String name, List<SimpleTestObject> items, Map<String, Object> metadata, LocalDateTime timestamp) {
            this.name = name;
            this.items = items;
            this.metadata = metadata;
            this.timestamp = timestamp;
        }
        
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        
        public List<SimpleTestObject> getItems() { return items; }
        public void setItems(List<SimpleTestObject> items) { this.items = items; }
        
        public Map<String, Object> getMetadata() { return metadata; }
        public void setMetadata(Map<String, Object> metadata) { this.metadata = metadata; }
        
        public LocalDateTime getTimestamp() { return timestamp; }
        public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    }
    
    // Test data
    private SimpleTestObject simpleObject;
    private ComplexTestObject complexObject;
    private String simpleObjectJson;
    private String complexObjectJson;
    private String malformedJson;
    private String validJsonSchema;
    private String invalidJsonSchema;
    
    @BeforeEach
    void setUp() {
        // Initialize simple test object
        simpleObject = new SimpleTestObject("test value", 42, true);
        simpleObjectJson = "{\"stringValue\":\"test value\",\"intValue\":42,\"boolValue\":true}";
        
        // Initialize complex test object
        List<SimpleTestObject> items = new ArrayList<>();
        items.add(new SimpleTestObject("item1", 1, true));
        items.add(new SimpleTestObject("item2", 2, false));
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("key1", "value1");
        metadata.put("key2", 123);
        metadata.put("key3", Arrays.asList("a", "b", "c"));
        
        LocalDateTime timestamp = LocalDateTime.of(2023, 5, 15, 10, 30, 0);
        complexObject = new ComplexTestObject("Test Complex Object", items, metadata, timestamp);
        
        // Malformed JSON for error testing
        malformedJson = "{\"name\":\"Incomplete JSON";
        
        // JSON Schema for validation testing
        validJsonSchema = "{\"type\":\"object\",\"properties\":{\"stringValue\":{\"type\":\"string\"},\"intValue\":{\"type\":\"integer\"},\"boolValue\":{\"type\":\"boolean\"}},\"required\":[\"stringValue\",\"intValue\",\"boolValue\"]}";
        invalidJsonSchema = "{\"type\":\"object\",\"properties\":{\"stringValue\":{\"type\":\"number\"},\"intValue\":{\"type\":\"string\"},\"boolValue\":{\"type\":\"integer\"}},\"required\":[\"stringValue\",\"intValue\",\"boolValue\"]}";
    }
    
    @Nested
    @DisplayName("Object to JSON Conversion Tests")
    class ObjectToJsonTests {
        
        @Test
        @DisplayName("Should convert simple object to JSON string")
        void shouldConvertSimpleObjectToJson() throws JsonUtil.JsonConversionException {
            String json = JsonUtil.toJson(simpleObject);
            assertNotNull(json);
            assertTrue(json.contains("\"stringValue\":\"test value\""));
            assertTrue(json.contains("\"intValue\":42"));
            assertTrue(json.contains("\"boolValue\":true"));
        }
        
        @Test
        @DisplayName("Should convert complex object to JSON string")
        void shouldConvertComplexObjectToJson() throws JsonUtil.JsonConversionException {
            String json = JsonUtil.toJson(complexObject);
            assertNotNull(json);
            assertTrue(json.contains("\"name\":\"Test Complex Object\""));
            assertTrue(json.contains("\"items\":"));
            assertTrue(json.contains("\"metadata\":"));
            assertTrue(json.contains("\"timestamp\":"));
        }
        
        @Test
        @DisplayName("Should convert object to pretty-printed JSON string")
        void shouldConvertToPrettyJson() throws JsonUtil.JsonConversionException {
            String json = JsonUtil.toPrettyJson(simpleObject);
            assertNotNull(json);
            assertTrue(json.contains("\n"));
            assertTrue(json.contains("  "));
            assertTrue(json.contains("\"stringValue\" : \"test value\""));
        }
        
        @Test
        @DisplayName("Should convert null to JSON string")
        void shouldConvertNullToJson() throws JsonUtil.JsonConversionException {
            String json = JsonUtil.toJson(null);
            assertEquals("null", json);
        }
        
        @Test
        @DisplayName("Should convert Map to JSON string")
        void shouldConvertMapToJson() throws JsonUtil.JsonConversionException {
            Map<String, Object> map = new HashMap<>();
            map.put("key1", "value1");
            map.put("key2", 123);
            map.put("key3", true);
            
            String json = JsonUtil.mapToJson(map);
            assertNotNull(json);
            assertTrue(json.contains("\"key1\":\"value1\""));
            assertTrue(json.contains("\"key2\":123"));
            assertTrue(json.contains("\"key3\":true"));
        }
    }
    
    @Nested
    @DisplayName("JSON to Object Conversion Tests")
    class JsonToObjectTests {
        
        @Test
        @DisplayName("Should convert JSON string to simple object")
        void shouldConvertJsonToSimpleObject() throws JsonUtil.JsonConversionException {
            SimpleTestObject result = JsonUtil.fromJson(simpleObjectJson, SimpleTestObject.class);
            assertNotNull(result);
            assertEquals("test value", result.getStringValue());
            assertEquals(42, result.getIntValue());
            assertTrue(result.isBoolValue());
            assertEquals(simpleObject, result);
        }
        
        @Test
        @DisplayName("Should convert JSON string to complex object")
        void shouldConvertJsonToComplexObject() throws JsonUtil.JsonConversionException {
            // First convert complex object to JSON
            String json = JsonUtil.toJson(complexObject);
            
            // Then convert back to object
            ComplexTestObject result = JsonUtil.fromJson(json, ComplexTestObject.class);
            assertNotNull(result);
            assertEquals("Test Complex Object", result.getName());
            assertNotNull(result.getItems());
            assertEquals(2, result.getItems().size());
            assertNotNull(result.getMetadata());
            assertEquals(3, result.getMetadata().size());
            assertNotNull(result.getTimestamp());
        }
        
        @Test
        @DisplayName("Should convert JSON string to generic type using TypeReference")
        void shouldConvertJsonToGenericType() throws JsonUtil.JsonConversionException {
            String json = "[{\"stringValue\":\"item1\",\"intValue\":1,\"boolValue\":true},{\"stringValue\":\"item2\",\"intValue\":2,\"boolValue\":false}]";
            
            List<SimpleTestObject> result = JsonUtil.fromJson(json, new TypeReference<List<SimpleTestObject>>() {});
            assertNotNull(result);
            assertEquals(2, result.size());
            assertEquals("item1", result.get(0).getStringValue());
            assertEquals(1, result.get(0).getIntValue());
            assertTrue(result.get(0).isBoolValue());
            assertEquals("item2", result.get(1).getStringValue());
            assertEquals(2, result.get(1).getIntValue());
            assertFalse(result.get(1).isBoolValue());
        }
        
        @Test
        @DisplayName("Should convert JSON string to Map")
        void shouldConvertJsonToMap() throws JsonUtil.JsonConversionException {
            String json = "{\"key1\":\"value1\",\"key2\":123,\"key3\":true}";
            
            Map<String, Object> result = JsonUtil.jsonToMap(json);
            assertNotNull(result);
            assertEquals(3, result.size());
            assertEquals("value1", result.get("key1"));
            assertEquals(123, ((Number) result.get("key2")).intValue());
            assertEquals(true, result.get("key3"));
        }
        
        @Test
        @DisplayName("Should convert JSON input stream to object")
        void shouldConvertJsonInputStreamToObject() throws JsonUtil.JsonConversionException {
            InputStream inputStream = new ByteArrayInputStream(simpleObjectJson.getBytes(StandardCharsets.UTF_8));
            
            SimpleTestObject result = JsonUtil.fromJson(inputStream, SimpleTestObject.class);
            assertNotNull(result);
            assertEquals("test value", result.getStringValue());
            assertEquals(42, result.getIntValue());
            assertTrue(result.isBoolValue());
        }
        
        @Test
        @DisplayName("Should throw exception when converting invalid JSON to object")
        void shouldThrowExceptionForInvalidJson() {
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.fromJson(malformedJson, SimpleTestObject.class);
            });
        }
    }
    
    @Nested
    @DisplayName("JsonNode Manipulation Tests")
    class JsonNodeTests {
        
        @Test
        @DisplayName("Should convert JSON string to JsonNode")
        void shouldConvertJsonToJsonNode() throws JsonUtil.JsonConversionException {
            JsonNode node = JsonUtil.toJsonNode(simpleObjectJson);
            assertNotNull(node);
            assertTrue(node.isObject());
            assertEquals("test value", node.get("stringValue").asText());
            assertEquals(42, node.get("intValue").asInt());
            assertTrue(node.get("boolValue").asBoolean());
        }
        
        @Test
        @DisplayName("Should convert object to JsonNode")
        void shouldConvertObjectToJsonNode() throws JsonUtil.JsonConversionException {
            JsonNode node = JsonUtil.toJsonNode(simpleObject);
            assertNotNull(node);
            assertTrue(node.isObject());
            assertEquals("test value", node.get("stringValue").asText());
            assertEquals(42, node.get("intValue").asInt());
            assertTrue(node.get("boolValue").asBoolean());
        }
        
        @Test
        @DisplayName("Should convert JsonNode to object")
        void shouldConvertJsonNodeToObject() throws JsonUtil.JsonConversionException {
            JsonNode node = JsonUtil.toJsonNode(simpleObject);
            
            SimpleTestObject result = JsonUtil.fromJsonNode(node, SimpleTestObject.class);
            assertNotNull(result);
            assertEquals("test value", result.getStringValue());
            assertEquals(42, result.getIntValue());
            assertTrue(result.isBoolValue());
        }
        
        @Test
        @DisplayName("Should create empty ObjectNode")
        void shouldCreateEmptyObjectNode() {
            ObjectNode node = JsonUtil.createObjectNode();
            assertNotNull(node);
            assertTrue(node.isObject());
            assertEquals(0, node.size());
        }
        
        @Test
        @DisplayName("Should create empty ArrayNode")
        void shouldCreateEmptyArrayNode() {
            ArrayNode node = JsonUtil.createArrayNode();
            assertNotNull(node);
            assertTrue(node.isArray());
            assertEquals(0, node.size());
        }
        
        @Test
        @DisplayName("Should build JSON object dynamically")
        void shouldBuildJsonObjectDynamically() throws JsonUtil.JsonConversionException {
            ObjectNode node = JsonUtil.createObjectNode();
            node.put("stringValue", "dynamic value");
            node.put("intValue", 99);
            node.put("boolValue", true);
            
            String json = JsonUtil.toJson(node);
            assertNotNull(json);
            assertTrue(json.contains("\"stringValue\":\"dynamic value\""));
            assertTrue(json.contains("\"intValue\":99"));
            assertTrue(json.contains("\"boolValue\":true"));
            
            SimpleTestObject result = JsonUtil.fromJsonNode(node, SimpleTestObject.class);
            assertEquals("dynamic value", result.getStringValue());
            assertEquals(99, result.getIntValue());
            assertTrue(result.isBoolValue());
        }
    }
    
    @Nested
    @DisplayName("JSON Transformation Tests")
    class JsonTransformationTests {
        
        @Test
        @DisplayName("Should merge two JSON objects")
        void shouldMergeJsonObjects() throws JsonUtil.JsonConversionException {
            String json1 = "{\"key1\":\"value1\",\"key2\":\"value2\"}";
            String json2 = "{\"key2\":\"updated\",\"key3\":\"value3\"}";
            
            String merged = JsonUtil.mergeJson(json1, json2);
            assertNotNull(merged);
            
            Map<String, Object> result = JsonUtil.jsonToMap(merged);
            assertEquals(3, result.size());
            assertEquals("value1", result.get("key1"));
            assertEquals("updated", result.get("key2"));
            assertEquals("value3", result.get("key3"));
        }
        
        @Test
        @DisplayName("Should merge nested JSON objects")
        void shouldMergeNestedJsonObjects() throws JsonUtil.JsonConversionException {
            String json1 = "{\"key1\":\"value1\",\"nested\":{\"nestedKey1\":\"nestedValue1\",\"nestedKey2\":\"nestedValue2\"}}";
            String json2 = "{\"key2\":\"value2\",\"nested\":{\"nestedKey2\":\"updated\",\"nestedKey3\":\"nestedValue3\"}}";
            
            String merged = JsonUtil.mergeJson(json1, json2);
            assertNotNull(merged);
            
            JsonNode result = JsonUtil.toJsonNode(merged);
            assertEquals("value1", result.get("key1").asText());
            assertEquals("value2", result.get("key2").asText());
            
            JsonNode nested = result.get("nested");
            assertNotNull(nested);
            assertEquals("nestedValue1", nested.get("nestedKey1").asText());
            assertEquals("updated", nested.get("nestedKey2").asText());
            assertEquals("nestedValue3", nested.get("nestedKey3").asText());
        }
        
        @Test
        @DisplayName("Should throw exception when merging non-object JSON")
        void shouldThrowExceptionWhenMergingNonObjectJson() {
            String json1 = "{\"key1\":\"value1\"}";
            String json2 = "[\"item1\", \"item2\"]";
            
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.mergeJson(json1, json2);
            });
        }
        
        @Test
        @DisplayName("Should filter JSON by field names")
        void shouldFilterJsonByFieldNames() throws JsonUtil.JsonConversionException {
            String json = "{\"field1\":\"value1\",\"field2\":\"value2\",\"field3\":\"value3\",\"field4\":\"value4\"}";
            List<String> fields = Arrays.asList("field1", "field3");
            
            String filtered = JsonUtil.filterJson(json, fields);
            assertNotNull(filtered);
            
            Map<String, Object> result = JsonUtil.jsonToMap(filtered);
            assertEquals(2, result.size());
            assertTrue(result.containsKey("field1"));
            assertFalse(result.containsKey("field2"));
            assertTrue(result.containsKey("field3"));
            assertFalse(result.containsKey("field4"));
        }
        
        @Test
        @DisplayName("Should throw exception when filtering non-object JSON")
        void shouldThrowExceptionWhenFilteringNonObjectJson() {
            String json = "[\"item1\", \"item2\"]";
            List<String> fields = Arrays.asList("field1", "field3");
            
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.filterJson(json, fields);
            });
        }
    }
    
    @Nested
    @DisplayName("JSON Validation Tests")
    class JsonValidationTests {
        
        @Test
        @DisplayName("Should validate JSON against schema successfully")
        void shouldValidateJsonAgainstSchemaSuccessfully() throws JsonUtil.JsonConversionException {
            JsonUtil.JsonValidationResult result = JsonUtil.validateJson(simpleObjectJson, validJsonSchema);
            assertTrue(result.isValid());
        }
        
        @Test
        @DisplayName("Should fail validation for JSON against invalid schema")
        void shouldFailValidationForJsonAgainstInvalidSchema() throws JsonUtil.JsonConversionException {
            JsonUtil.JsonValidationResult result = JsonUtil.validateJson(simpleObjectJson, invalidJsonSchema);
            assertFalse(result.isValid());
            assertNotNull(result.getMessage());
        }
        
        @Test
        @DisplayName("Should check if string is valid JSON")
        void shouldCheckIfStringIsValidJson() {
            assertTrue(JsonUtil.isValidJson(simpleObjectJson));
            assertFalse(JsonUtil.isValidJson(malformedJson));
        }
        
        @Test
        @DisplayName("Should throw exception when validating with invalid schema")
        void shouldThrowExceptionWhenValidatingWithInvalidSchema() {
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.validateJson(simpleObjectJson, malformedJson);
            });
        }
    }
    
    @Nested
    @DisplayName("Integration Tests with Real Data")
    class IntegrationTests {
        
        @Test
        @DisplayName("Should handle complex nested structures")
        void shouldHandleComplexNestedStructures() throws JsonUtil.JsonConversionException {
            // Create a complex nested structure
            Map<String, Object> rootMap = new HashMap<>();
            
            Map<String, Object> level1Map = new HashMap<>();
            List<Map<String, Object>> level1List = new ArrayList<>();
            
            for (int i = 0; i < 3; i++) {
                Map<String, Object> item = new HashMap<>();
                item.put("id", i);
                item.put("name", "Item " + i);
                
                Map<String, Object> nestedMap = new HashMap<>();
                nestedMap.put("nestedKey1", "nestedValue" + i);
                nestedMap.put("nestedKey2", i * 10);
                item.put("nested", nestedMap);
                
                level1List.add(item);
            }
            
            level1Map.put("items", level1List);
            level1Map.put("count", level1List.size());
            
            rootMap.put("data", level1Map);
            rootMap.put("status", "success");
            rootMap.put("timestamp", LocalDate.of(2023, 5, 15).toString());
            
            // Convert to JSON and back
            String json = JsonUtil.toJson(rootMap);
            assertNotNull(json);
            
            Map<String, Object> result = JsonUtil.jsonToMap(json);
            assertNotNull(result);
            assertEquals("success", result.get("status"));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> resultData = (Map<String, Object>) result.get("data");
            assertNotNull(resultData);
            assertEquals(3, ((Number) resultData.get("count")).intValue());
            
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> resultItems = (List<Map<String, Object>>) resultData.get("items");
            assertNotNull(resultItems);
            assertEquals(3, resultItems.size());
            
            for (int i = 0; i < 3; i++) {
                Map<String, Object> item = resultItems.get(i);
                assertEquals(i, ((Number) item.get("id")).intValue());
                assertEquals("Item " + i, item.get("name"));
                
                @SuppressWarnings("unchecked")
                Map<String, Object> nestedMap = (Map<String, Object>) item.get("nested");
                assertNotNull(nestedMap);
                assertEquals("nestedValue" + i, nestedMap.get("nestedKey1"));
                assertEquals(i * 10, ((Number) nestedMap.get("nestedKey2")).intValue());
            }
        }
        
        @Test
        @DisplayName("Should handle real-world application data")
        void shouldHandleRealWorldApplicationData() throws JsonUtil.JsonConversionException {
            // Create a mock MCA application object
            Map<String, Object> application = new HashMap<>();
            application.put("id", "APP-12345");
            application.put("status", "in_review");
            
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("funding_amount", 50000);
            metadata.put("term_length", 12);
            metadata.put("purpose", "Inventory purchase");
            metadata.put("confidence_score", 0.95);
            
            application.put("metadata", metadata);
            application.put("created_at", "2023-05-15T10:30:00Z");
            application.put("updated_at", "2023-05-15T14:45:00Z");
            application.put("review_status", "pending_verification");
            
            // Convert to JSON
            String json = JsonUtil.toJson(application);
            assertNotNull(json);
            
            // Verify JSON structure
            JsonNode node = JsonUtil.toJsonNode(json);
            assertEquals("APP-12345", node.get("id").asText());
            assertEquals("in_review", node.get("status").asText());
            assertEquals("pending_verification", node.get("review_status").asText());
            
            JsonNode metadataNode = node.get("metadata");
            assertNotNull(metadataNode);
            assertEquals(50000, metadataNode.get("funding_amount").asInt());
            assertEquals(12, metadataNode.get("term_length").asInt());
            assertEquals("Inventory purchase", metadataNode.get("purpose").asText());
            assertEquals(0.95, metadataNode.get("confidence_score").asDouble(), 0.001);
            
            // Convert back to Map
            Map<String, Object> result = JsonUtil.jsonToMap(json);
            assertEquals("APP-12345", result.get("id"));
            assertEquals("in_review", result.get("status"));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> resultMetadata = (Map<String, Object>) result.get("metadata");
            assertEquals(50000, ((Number) resultMetadata.get("funding_amount")).intValue());
            assertEquals("Inventory purchase", resultMetadata.get("purpose"));
        }
        
        @Test
        @DisplayName("Should handle document metadata with confidence scores")
        void shouldHandleDocumentMetadataWithConfidenceScores() throws JsonUtil.JsonConversionException {
            // Create a mock document metadata object with confidence scores
            Map<String, Object> document = new HashMap<>();
            document.put("id", "DOC-67890");
            document.put("application_id", "APP-12345");
            document.put("type", "bank_statement");
            document.put("storage_path", "mca-documents-staging/APP-12345/bank_statement.pdf");
            document.put("uploaded_at", "2023-05-15T09:15:00Z");
            
            Map<String, Object> classification = new HashMap<>();
            classification.put("document_type", "bank_statement");
            classification.put("confidence", 0.98);
            classification.put("alternative_types", Arrays.asList(
                Map.of("type", "financial_document", "confidence", 0.75),
                Map.of("type", "account_statement", "confidence", 0.65)
            ));
            document.put("classification", classification);
            
            Map<String, Object> extractedData = new HashMap<>();
            extractedData.put("account_number", Map.of("value", "*****6789", "confidence", 0.99));
            extractedData.put("bank_name", Map.of("value", "First National Bank", "confidence", 0.97));
            extractedData.put("account_holder", Map.of("value", "ABC Business LLC", "confidence", 0.95));
            extractedData.put("statement_date", Map.of("value", "2023-04-30", "confidence", 0.98));
            extractedData.put("opening_balance", Map.of("value", 25000.00, "confidence", 0.96));
            extractedData.put("closing_balance", Map.of("value", 32150.75, "confidence", 0.97));
            
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("page_count", 5);
            metadata.put("extracted_data", extractedData);
            document.put("metadata", metadata);
            
            // Convert to JSON
            String json = JsonUtil.toJson(document);
            assertNotNull(json);
            
            // Verify JSON structure
            JsonNode node = JsonUtil.toJsonNode(json);
            assertEquals("DOC-67890", node.get("id").asText());
            assertEquals("APP-12345", node.get("application_id").asText());
            assertEquals("bank_statement", node.get("type").asText());
            
            JsonNode classificationNode = node.get("classification");
            assertNotNull(classificationNode);
            assertEquals("bank_statement", classificationNode.get("document_type").asText());
            assertEquals(0.98, classificationNode.get("confidence").asDouble(), 0.001);
            
            JsonNode metadataNode = node.get("metadata");
            assertNotNull(metadataNode);
            assertEquals(5, metadataNode.get("page_count").asInt());
            
            JsonNode extractedDataNode = metadataNode.get("extracted_data");
            assertNotNull(extractedDataNode);
            
            JsonNode accountNumberNode = extractedDataNode.get("account_number");
            assertEquals("*****6789", accountNumberNode.get("value").asText());
            assertEquals(0.99, accountNumberNode.get("confidence").asDouble(), 0.001);
            
            // Convert back to Map and verify
            Map<String, Object> result = JsonUtil.jsonToMap(json);
            assertEquals("DOC-67890", result.get("id"));
            assertEquals("bank_statement", result.get("type"));
            
            @SuppressWarnings("unchecked")
            Map<String, Object> resultClassification = (Map<String, Object>) result.get("classification");
            assertEquals("bank_statement", resultClassification.get("document_type"));
            assertEquals(0.98, ((Number) resultClassification.get("confidence")).doubleValue(), 0.001);
        }
    }
    
    @Nested
    @DisplayName("Error Handling Tests")
    class ErrorHandlingTests {
        
        @Test
        @DisplayName("Should handle null input gracefully")
        void shouldHandleNullInputGracefully() throws JsonUtil.JsonConversionException {
            assertDoesNotThrow(() -> JsonUtil.toJson(null));
            
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.fromJson((String) null, SimpleTestObject.class);
            });
            
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.toJsonNode((String) null);
            });
        }
        
        @Test
        @DisplayName("Should handle empty JSON string")
        void shouldHandleEmptyJsonString() {
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.fromJson("", SimpleTestObject.class);
            });
            
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.toJsonNode("");
            });
            
            assertFalse(JsonUtil.isValidJson(""));
        }
        
        @Test
        @DisplayName("Should handle malformed JSON string")
        void shouldHandleMalformedJsonString() {
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.fromJson(malformedJson, SimpleTestObject.class);
            });
            
            assertThrows(JsonUtil.JsonConversionException.class, () -> {
                JsonUtil.toJsonNode(malformedJson);
            });
            
            assertFalse(JsonUtil.isValidJson(malformedJson));
        }
        
        @Test
        @DisplayName("Should handle type mismatch during deserialization")
        void shouldHandleTypeMismatchDuringDeserialization() {
            String invalidTypeJson = "{\"stringValue\":42,\"intValue\":\"not an int\",\"boolValue\":\"not a boolean\"}";
            
            // Jackson's default behavior is to try to convert types
            SimpleTestObject result = assertDoesNotThrow(() -> {
                return JsonUtil.fromJson(invalidTypeJson, SimpleTestObject.class);
            });
            
            // It should have converted "42" to a string
            assertEquals("42", result.getStringValue());
            
            // It should have failed to convert "not an int" to an int, using default value 0
            assertEquals(0, result.getIntValue());
            
            // It should have interpreted "not a boolean" as true (non-empty string)
            assertFalse(result.isBoolValue());
        }
    }
    
    @Nested
    @DisplayName("ObjectMapper Configuration Tests")
    class ObjectMapperConfigurationTests {
        
        @Test
        @DisplayName("Should get configured ObjectMapper instance")
        void shouldGetConfiguredObjectMapperInstance() {
            ObjectMapper mapper = JsonUtil.getObjectMapper();
            assertNotNull(mapper);
        }
        
        @Test
        @DisplayName("Should handle Java 8 date/time types")
        void shouldHandleJava8DateTimeTypes() throws JsonUtil.JsonConversionException {
            // Create an object with LocalDateTime
            Map<String, Object> map = new HashMap<>();
            LocalDateTime now = LocalDateTime.now();
            map.put("timestamp", now);
            
            // Convert to JSON
            String json = JsonUtil.toJson(map);
            assertNotNull(json);
            
            // The timestamp should be formatted as ISO string, not as array or timestamp
            assertFalse(json.contains("[")); // Not an array
            assertTrue(json.contains("\"timestamp\":"));
            
            // Convert back and verify
            JsonNode node = JsonUtil.toJsonNode(json);
            assertNotNull(node.get("timestamp"));
            assertFalse(node.get("timestamp").isArray());
        }
        
        @Test
        @DisplayName("Should ignore unknown properties during deserialization")
        void shouldIgnoreUnknownPropertiesDuringDeserialization() throws JsonUtil.JsonConversionException {
            String jsonWithExtraProps = "{\"stringValue\":\"test value\",\"intValue\":42,\"boolValue\":true,\"extraProp\":\"extra value\"}";
            
            SimpleTestObject result = JsonUtil.fromJson(jsonWithExtraProps, SimpleTestObject.class);
            assertNotNull(result);
            assertEquals("test value", result.getStringValue());
            assertEquals(42, result.getIntValue());
            assertTrue(result.isBoolValue());
            // Extra property should be ignored without error
        }
        
        @Test
        @DisplayName("Should exclude null values during serialization")
        void shouldExcludeNullValuesDuringSerialization() throws JsonUtil.JsonConversionException {
            SimpleTestObject object = new SimpleTestObject(null, 42, true);
            
            String json = JsonUtil.toJson(object);
            assertNotNull(json);
            assertFalse(json.contains("\"stringValue\":null"));
            assertTrue(json.contains("\"intValue\":42"));
            assertTrue(json.contains("\"boolValue\":true"));
        }
    }
}