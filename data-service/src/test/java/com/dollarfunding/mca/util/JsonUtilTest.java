package com.dollarfunding.mca.util;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the JsonUtil class.
 * 
 * Tests verify the functionality of JSON serialization and deserialization utilities
 * for the MCA application, including:
 * - Conversion between Java objects and JSON strings
 * - Handling of complex types and nested objects
 * - Custom serializers/deserializers
 * - Dynamic JSON manipulation
 * - Error handling for malformed JSON
 * - JSON schema validation
 * - JSON transformation and filtering
 */
public class JsonUtilTest {

    // Test data classes
    static class SimpleTestObject {
        private String stringValue;
        private int intValue;
        private boolean boolValue;
        
        public SimpleTestObject() {
        }
        
        public SimpleTestObject(String stringValue, int intValue, boolean boolValue) {
            this.stringValue = stringValue;
            this.intValue = intValue;
            this.boolValue = boolValue;
        }

        public String getStringValue() {
            return stringValue;
        }

        public void setStringValue(String stringValue) {
            this.stringValue = stringValue;
        }

        public int getIntValue() {
            return intValue;
        }

        public void setIntValue(int intValue) {
            this.intValue = intValue;
        }

        public boolean isBoolValue() {
            return boolValue;
        }

        public void setBoolValue(boolean boolValue) {
            this.boolValue = boolValue;
        }
        
        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            SimpleTestObject that = (SimpleTestObject) o;
            return intValue == that.intValue &&
                   boolValue == that.boolValue &&
                   (stringValue == null ? that.stringValue == null : stringValue.equals(that.stringValue));
        }
    }
    
    static class ComplexTestObject {
        private String name;
        private List<SimpleTestObject> items;
        private Map<String, Object> metadata;
        private LocalDate date;
        private LocalDateTime timestamp;
        
        public ComplexTestObject() {
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public List<SimpleTestObject> getItems() {
            return items;
        }

        public void setItems(List<SimpleTestObject> items) {
            this.items = items;
        }

        public Map<String, Object> getMetadata() {
            return metadata;
        }

        public void setMetadata(Map<String, Object> metadata) {
            this.metadata = metadata;
        }

        public LocalDate getDate() {
            return date;
        }

        public void setDate(LocalDate date) {
            this.date = date;
        }

        public LocalDateTime getTimestamp() {
            return timestamp;
        }

        public void setTimestamp(LocalDateTime timestamp) {
            this.timestamp = timestamp;
        }
    }
    
    // Document metadata class to simulate real application data
    static class DocumentMetadata {
        private String documentType;
        private Map<String, Double> confidenceScores;
        private List<String> detectedFields;
        
        public DocumentMetadata() {
        }

        public DocumentMetadata(String documentType, Map<String, Double> confidenceScores, List<String> detectedFields) {
            this.documentType = documentType;
            this.confidenceScores = confidenceScores;
            this.detectedFields = detectedFields;
        }

        public String getDocumentType() {
            return documentType;
        }

        public void setDocumentType(String documentType) {
            this.documentType = documentType;
        }

        public Map<String, Double> getConfidenceScores() {
            return confidenceScores;
        }

        public void setConfidenceScores(Map<String, Double> confidenceScores) {
            this.confidenceScores = confidenceScores;
        }

        public List<String> getDetectedFields() {
            return detectedFields;
        }

        public void setDetectedFields(List<String> detectedFields) {
            this.detectedFields = detectedFields;
        }
    }

    /**
     * Test for converting a simple Java object to JSON string.
     */
    @Test
    public void testToJson_SimpleObject() throws JsonUtil.JsonConversionException {
        // Arrange
        SimpleTestObject testObject = new SimpleTestObject("test value", 42, true);
        
        // Act
        String json = JsonUtil.toJson(testObject);
        
        // Assert
        assertTrue(json.contains("\"stringValue\":\"test value\""));
        assertTrue(json.contains("\"intValue\":42"));
        assertTrue(json.contains("\"boolValue\":true"));
    }

    /**
     * Test for converting a JSON string to a simple Java object.
     */
    @Test
    public void testFromJson_SimpleObject() throws JsonUtil.JsonConversionException {
        // Arrange
        String json = "{\"stringValue\":\"test value\",\"intValue\":42,\"boolValue\":true}";
        
        // Act
        SimpleTestObject result = JsonUtil.fromJson(json, SimpleTestObject.class);
        
        // Assert
        assertEquals("test value", result.getStringValue());
        assertEquals(42, result.getIntValue());
        assertTrue(result.isBoolValue());
    }

    /**
     * Test for converting a complex Java object with nested objects, collections, and dates to JSON.
     */
    @Test
    public void testToJson_ComplexObject() throws JsonUtil.JsonConversionException {
        // Arrange
        ComplexTestObject testObject = new ComplexTestObject();
        testObject.setName("Complex Test");
        testObject.setItems(Arrays.asList(
            new SimpleTestObject("item1", 1, true),
            new SimpleTestObject("item2", 2, false)
        ));
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("key1", "value1");
        metadata.put("key2", 123);
        metadata.put("key3", Arrays.asList("a", "b", "c"));
        testObject.setMetadata(metadata);
        
        testObject.setDate(LocalDate.of(2023, 5, 15));
        testObject.setTimestamp(LocalDateTime.of(2023, 5, 15, 10, 30, 45));
        
        // Act
        String json = JsonUtil.toJson(testObject);
        
        // Assert
        assertTrue(json.contains("\"name\":\"Complex Test\""));
        assertTrue(json.contains("\"items\":"));
        assertTrue(json.contains("\"metadata\":"));
        assertTrue(json.contains("\"date\":\"2023-05-15\""));
        assertTrue(json.contains("\"timestamp\":\"2023-05-15T10:30:45\""));
    }

    /**
     * Test for converting a JSON string to a complex Java object with nested objects, collections, and dates.
     */
    @Test
    public void testFromJson_ComplexObject() throws JsonUtil.JsonConversionException {
        // Arrange
        String json = "{\"name\":\"Complex Test\",\"items\":[{\"stringValue\":\"item1\",\"intValue\":1,\"boolValue\":true},{\"stringValue\":\"item2\",\"intValue\":2,\"boolValue\":false}],\"metadata\":{\"key1\":\"value1\",\"key2\":123,\"key3\":[\"a\",\"b\",\"c\"]},\"date\":\"2023-05-15\",\"timestamp\":\"2023-05-15T10:30:45\"}";
        
        // Act
        ComplexTestObject result = JsonUtil.fromJson(json, ComplexTestObject.class);
        
        // Assert
        assertEquals("Complex Test", result.getName());
        assertEquals(2, result.getItems().size());
        assertEquals("item1", result.getItems().get(0).getStringValue());
        assertEquals(1, result.getItems().get(0).getIntValue());
        assertTrue(result.getItems().get(0).isBoolValue());
        assertEquals("item2", result.getItems().get(1).getStringValue());
        assertEquals(2, result.getItems().get(1).getIntValue());
        assertFalse(result.getItems().get(1).isBoolValue());
        assertEquals(3, result.getMetadata().size());
        assertEquals("value1", result.getMetadata().get("key1"));
        assertEquals(123, result.getMetadata().get("key2"));
        assertEquals(LocalDate.of(2023, 5, 15), result.getDate());
        assertEquals(LocalDateTime.of(2023, 5, 15, 10, 30, 45), result.getTimestamp());
    }

    /**
     * Test for converting a JSON string to a generic type using TypeReference.
     */
    @Test
    public void testFromJson_WithTypeReference() throws JsonUtil.JsonConversionException {
        // Arrange
        String json = "[{\"stringValue\":\"item1\",\"intValue\":1,\"boolValue\":true},{\"stringValue\":\"item2\",\"intValue\":2,\"boolValue\":false}]";
        
        // Act
        List<SimpleTestObject> result = JsonUtil.fromJson(json, new TypeReference<List<SimpleTestObject>>() {});
        
        // Assert
        assertEquals(2, result.size());
        assertEquals("item1", result.get(0).getStringValue());
        assertEquals(1, result.get(0).getIntValue());
        assertTrue(result.get(0).isBoolValue());
        assertEquals("item2", result.get(1).getStringValue());
        assertEquals(2, result.get(1).getIntValue());
        assertFalse(result.get(1).isBoolValue());
    }

    /**
     * Test for converting a JSON input stream to a Java object.
     */
    @Test
    public void testFromJson_InputStream() throws JsonUtil.JsonConversionException {
        // Arrange
        String jsonStr = "{\"stringValue\":\"test value\",\"intValue\":42,\"boolValue\":true}";
        InputStream inputStream = new ByteArrayInputStream(jsonStr.getBytes());
        
        // Act
        SimpleTestObject result = JsonUtil.fromJson(inputStream, SimpleTestObject.class);
        
        // Assert
        assertEquals("test value", result.getStringValue());
        assertEquals(42, result.getIntValue());
        assertTrue(result.isBoolValue());
    }

    /**
     * Test for converting a JSON string to a JsonNode for dynamic manipulation.
     */
    @Test
    public void testToJsonNode_FromString() throws JsonUtil.JsonConversionException {
        // Arrange
        String json = "{\"name\":\"Test\",\"value\":42,\"nested\":{\"key\":\"nestedValue\"}}";
        
        // Act
        JsonNode node = JsonUtil.toJsonNode(json);
        
        // Assert
        assertEquals("Test", node.get("name").asText());
        assertEquals(42, node.get("value").asInt());
        assertTrue(node.has("nested"));
        assertEquals("nestedValue", node.get("nested").get("key").asText());
    }

    /**
     * Test for converting a Java object to a JsonNode.
     */
    @Test
    public void testToJsonNode_FromObject() throws JsonUtil.JsonConversionException {
        // Arrange
        SimpleTestObject testObject = new SimpleTestObject("test value", 42, true);
        
        // Act
        JsonNode node = JsonUtil.toJsonNode(testObject);
        
        // Assert
        assertEquals("test value", node.get("stringValue").asText());
        assertEquals(42, node.get("intValue").asInt());
        assertTrue(node.get("boolValue").asBoolean());
    }

    /**
     * Test for creating an empty ObjectNode.
     */
    @Test
    public void testCreateObjectNode() {
        // Act
        ObjectNode node = JsonUtil.createObjectNode();
        
        // Assert
        assertNotNull(node);
        assertTrue(node.isEmpty());
        
        // Verify we can add properties
        node.put("test", "value");
        assertEquals("value", node.get("test").asText());
    }

    /**
     * Test for creating an empty ArrayNode.
     */
    @Test
    public void testCreateArrayNode() {
        // Act
        ArrayNode node = JsonUtil.createArrayNode();
        
        // Assert
        assertNotNull(node);
        assertEquals(0, node.size());
        
        // Verify we can add elements
        node.add("test");
        assertEquals(1, node.size());
        assertEquals("test", node.get(0).asText());
    }

    /**
     * Test for converting a JsonNode to a Java object.
     */
    @Test
    public void testFromJsonNode() throws JsonUtil.JsonConversionException {
        // Arrange
        ObjectNode node = JsonUtil.createObjectNode();
        node.put("stringValue", "test value");
        node.put("intValue", 42);
        node.put("boolValue", true);
        
        // Act
        SimpleTestObject result = JsonUtil.fromJsonNode(node, SimpleTestObject.class);
        
        // Assert
        assertEquals("test value", result.getStringValue());
        assertEquals(42, result.getIntValue());
        assertTrue(result.isBoolValue());
    }

    /**
     * Test for merging two JSON objects.
     */
    @Test
    public void testMergeJson() throws JsonUtil.JsonConversionException {
        // Arrange
        String json1 = "{\"name\":\"Test\",\"value\":42,\"nested\":{\"key1\":\"value1\"}}";
        String json2 = "{\"value\":99,\"nested\":{\"key2\":\"value2\"},\"newField\":\"newValue\"}";
        
        // Act
        String merged = JsonUtil.mergeJson(json1, json2);
        JsonNode mergedNode = JsonUtil.toJsonNode(merged);
        
        // Assert
        assertEquals("Test", mergedNode.get("name").asText());
        assertEquals(99, mergedNode.get("value").asInt()); // Overwritten by json2
        assertEquals("newValue", mergedNode.get("newField").asText()); // Added from json2
        assertTrue(mergedNode.has("nested"));
        assertEquals("value1", mergedNode.get("nested").get("key1").asText()); // Preserved from json1
        assertEquals("value2", mergedNode.get("nested").get("key2").asText()); // Added from json2
    }

    /**
     * Test for validating JSON against a schema.
     */
    @Test
    public void testValidateJson() throws JsonUtil.JsonConversionException {
        // Arrange
        String json = "{\"name\":\"Test Document\",\"documentType\":\"invoice\",\"pageCount\":5}";
        String schema = "{\"type\":\"object\",\"required\":[\"name\",\"documentType\"],\"properties\":{\"name\":{\"type\":\"string\"},\"documentType\":{\"type\":\"string\",\"enum\":[\"invoice\",\"receipt\",\"statement\"]},\"pageCount\":{\"type\":\"integer\",\"minimum\":1}}}";
        
        // Act
        JsonUtil.JsonValidationResult result = JsonUtil.validateJson(json, schema);
        
        // Assert
        assertTrue(result.isValid());
    }

    /**
     * Test for validating invalid JSON against a schema.
     */
    @Test
    public void testValidateJson_Invalid() throws JsonUtil.JsonConversionException {
        // Arrange
        String json = "{\"name\":\"Test Document\",\"documentType\":\"unknown\",\"pageCount\":0}";
        String schema = "{\"type\":\"object\",\"required\":[\"name\",\"documentType\"],\"properties\":{\"name\":{\"type\":\"string\"},\"documentType\":{\"type\":\"string\",\"enum\":[\"invoice\",\"receipt\",\"statement\"]},\"pageCount\":{\"type\":\"integer\",\"minimum\":1}}}";
        
        // Act
        JsonUtil.JsonValidationResult result = JsonUtil.validateJson(json, schema);
        
        // Assert
        assertFalse(result.isValid());
        assertTrue(result.getMessage().contains("unknown")); // Error message should mention the invalid enum value
        assertTrue(result.getMessage().contains("minimum")); // Error message should mention the minimum value constraint
    }

    /**
     * Test for checking if a string is valid JSON.
     */
    @Test
    public void testIsValidJson() {
        // Valid JSON
        assertTrue(JsonUtil.isValidJson("{\"name\":\"Test\"}"));
        assertTrue(JsonUtil.isValidJson("[1,2,3]"));
        assertTrue(JsonUtil.isValidJson("true"));
        assertTrue(JsonUtil.isValidJson("42"));
        assertTrue(JsonUtil.isValidJson("\"string\""));
        
        // Invalid JSON
        assertFalse(JsonUtil.isValidJson("{name:\"Test\"}"));
        assertFalse(JsonUtil.isValidJson("{\"name\":\"Test\"")); // Missing closing brace
        assertFalse(JsonUtil.isValidJson("[1,2,"));
        assertFalse(JsonUtil.isValidJson("Not JSON"));
    }

    /**
     * Test for filtering a JSON object by keeping only specified fields.
     */
    @Test
    public void testFilterJson() throws JsonUtil.JsonConversionException {
        // Arrange
        String json = "{\"id\":123,\"name\":\"Test\",\"sensitive\":\"secret\",\"metadata\":{\"key\":\"value\"}}";
        List<String> fields = Arrays.asList("id", "name");
        
        // Act
        String filtered = JsonUtil.filterJson(json, fields);
        JsonNode filteredNode = JsonUtil.toJsonNode(filtered);
        
        // Assert
        assertEquals(2, filteredNode.size());
        assertTrue(filteredNode.has("id"));
        assertTrue(filteredNode.has("name"));
        assertFalse(filteredNode.has("sensitive"));
        assertFalse(filteredNode.has("metadata"));
        assertEquals(123, filteredNode.get("id").asInt());
        assertEquals("Test", filteredNode.get("name").asText());
    }

    /**
     * Test for converting a Map to JSON and back.
     */
    @Test
    public void testMapToJsonAndBack() throws JsonUtil.JsonConversionException {
        // Arrange
        Map<String, Object> map = new HashMap<>();
        map.put("string", "value");
        map.put("number", 42);
        map.put("boolean", true);
        map.put("decimal", new BigDecimal("123.45"));
        map.put("array", Arrays.asList(1, 2, 3));
        Map<String, String> nestedMap = new HashMap<>();
        nestedMap.put("nestedKey", "nestedValue");
        map.put("object", nestedMap);
        
        // Act
        String json = JsonUtil.mapToJson(map);
        Map<String, Object> resultMap = JsonUtil.jsonToMap(json);
        
        // Assert
        assertEquals(6, resultMap.size());
        assertEquals("value", resultMap.get("string"));
        assertEquals(42, resultMap.get("number"));
        assertEquals(true, resultMap.get("boolean"));
        assertTrue(resultMap.get("decimal").toString().contains("123.45"));
        assertTrue(resultMap.get("array") instanceof List);
        assertTrue(resultMap.get("object") instanceof Map);
        
        @SuppressWarnings("unchecked")
        Map<String, Object> resultNestedMap = (Map<String, Object>) resultMap.get("object");
        assertEquals("nestedValue", resultNestedMap.get("nestedKey"));
    }

    /**
     * Test for pretty-printing JSON.
     */
    @Test
    public void testToPrettyJson() throws JsonUtil.JsonConversionException {
        // Arrange
        SimpleTestObject testObject = new SimpleTestObject("test value", 42, true);
        
        // Act
        String json = JsonUtil.toPrettyJson(testObject);
        
        // Assert
        assertTrue(json.contains("\n"));
        assertTrue(json.contains("  "));
        assertTrue(json.contains("\"stringValue\" : \"test value\""));
    }

    /**
     * Test for error handling when converting invalid JSON to an object.
     */
    @Test
    public void testFromJson_InvalidJson() {
        // Arrange
        String invalidJson = "{\"name\":\"Test\"";
        
        // Act & Assert
        Exception exception = assertThrows(JsonUtil.JsonConversionException.class, () -> {
            JsonUtil.fromJson(invalidJson, SimpleTestObject.class);
        });
        
        assertTrue(exception.getMessage().contains("Failed to convert JSON"));
    }

    /**
     * Test for error handling when merging invalid JSON objects.
     */
    @Test
    public void testMergeJson_InvalidJson() {
        // Arrange
        String validJson = "{\"name\":\"Test\"}";
        String invalidJson = "{\"value\":42";
        
        // Act & Assert
        Exception exception = assertThrows(JsonUtil.JsonConversionException.class, () -> {
            JsonUtil.mergeJson(validJson, invalidJson);
        });
        
        assertTrue(exception.getMessage().contains("Failed to merge JSON"));
    }

    /**
     * Test for error handling when merging non-object JSON values.
     */
    @Test
    public void testMergeJson_NonObjectJson() {
        // Arrange
        String json1 = "{\"name\":\"Test\"}";
        String json2 = "[1,2,3]";
        
        // Act & Assert
        Exception exception = assertThrows(JsonUtil.JsonConversionException.class, () -> {
            JsonUtil.mergeJson(json1, json2);
        });
        
        assertTrue(exception.getMessage().contains("must represent objects"));
    }

    /**
     * Test for error handling when filtering non-object JSON.
     */
    @Test
    public void testFilterJson_NonObjectJson() {
        // Arrange
        String json = "[1,2,3]";
        List<String> fields = Arrays.asList("id", "name");
        
        // Act & Assert
        Exception exception = assertThrows(JsonUtil.JsonConversionException.class, () -> {
            JsonUtil.filterJson(json, fields);
        });
        
        assertTrue(exception.getMessage().contains("must represent an object"));
    }

    /**
     * Test for handling document metadata with confidence scores (simulating real application data).
     */
    @Test
    public void testDocumentMetadataWithConfidenceScores() throws JsonUtil.JsonConversionException {
        // Arrange
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("companyName", 0.95);
        confidenceScores.put("invoiceNumber", 0.87);
        confidenceScores.put("date", 0.92);
        confidenceScores.put("amount", 0.89);
        
        DocumentMetadata metadata = new DocumentMetadata(
            "invoice",
            confidenceScores,
            Arrays.asList("companyName", "invoiceNumber", "date", "amount")
        );
        
        // Act
        String json = JsonUtil.toJson(metadata);
        DocumentMetadata result = JsonUtil.fromJson(json, DocumentMetadata.class);
        
        // Assert
        assertEquals("invoice", result.getDocumentType());
        assertEquals(4, result.getConfidenceScores().size());
        assertEquals(0.95, result.getConfidenceScores().get("companyName"), 0.001);
        assertEquals(0.87, result.getConfidenceScores().get("invoiceNumber"), 0.001);
        assertEquals(0.92, result.getConfidenceScores().get("date"), 0.001);
        assertEquals(0.89, result.getConfidenceScores().get("amount"), 0.001);
        assertEquals(4, result.getDetectedFields().size());
        assertTrue(result.getDetectedFields().contains("companyName"));
        assertTrue(result.getDetectedFields().contains("invoiceNumber"));
        assertTrue(result.getDetectedFields().contains("date"));
        assertTrue(result.getDetectedFields().contains("amount"));
    }

    /**
     * Test for getting the configured ObjectMapper instance.
     */
    @Test
    public void testGetObjectMapper() {
        // Act
        ObjectMapper mapper = JsonUtil.getObjectMapper();
        
        // Assert
        assertNotNull(mapper);
        
        // Verify it's properly configured
        assertFalse(mapper.getSerializationConfig().isEnabled(com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS));
        assertFalse(mapper.getDeserializationConfig().isEnabled(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES));
    }
}