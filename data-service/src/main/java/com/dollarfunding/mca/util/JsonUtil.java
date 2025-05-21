package com.dollarfunding.mca.util;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.github.fge.jsonschema.core.exceptions.ProcessingException;
import com.github.fge.jsonschema.core.report.ProcessingReport;
import com.github.fge.jsonschema.main.JsonSchema;
import com.github.fge.jsonschema.main.JsonSchemaFactory;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Map;

/**
 * Utility class for JSON serialization and deserialization operations in the MCA application.
 * Provides methods for converting between Java objects and JSON strings, with support for
 * custom type handling and error management.
 *
 * This utility supports:
 * - JSON-based API contracts with standardized error responses
 * - Internal service communication using JSON messages via RabbitMQ
 * - API responses using standardized JSON structures
 * - Document metadata stored as structured JSON with confidence scores
 * - OCR extraction results as JSON with field-value pairs and confidence metrics
 */
public class JsonUtil {

    private static final ObjectMapper objectMapper = createObjectMapper();
    
    /**
     * Creates and configures the ObjectMapper with custom settings.
     * 
     * @return A configured ObjectMapper instance
     */
    private static ObjectMapper createObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        
        // Configure serialization features
        mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        mapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);
        mapper.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);
        
        // Configure deserialization features
        mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        mapper.configure(DeserializationFeature.ACCEPT_SINGLE_VALUE_AS_ARRAY, true);
        mapper.configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true);
        
        // Register modules for handling Java 8 date/time types
        mapper.registerModule(new JavaTimeModule());
        
        return mapper;
    }
    
    /**
     * Get the configured ObjectMapper instance.
     * 
     * @return The singleton ObjectMapper instance
     */
    public static ObjectMapper getObjectMapper() {
        return objectMapper;
    }
    
    /**
     * Converts a Java object to a JSON string.
     * 
     * @param object The object to convert to JSON
     * @return JSON string representation of the object
     * @throws JsonConversionException If conversion fails
     */
    public static String toJson(Object object) throws JsonConversionException {
        try {
            return objectMapper.writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new JsonConversionException("Failed to convert object to JSON", e);
        }
    }
    
    /**
     * Converts a Java object to a pretty-printed JSON string.
     * 
     * @param object The object to convert to JSON
     * @return Pretty-printed JSON string representation of the object
     * @throws JsonConversionException If conversion fails
     */
    public static String toPrettyJson(Object object) throws JsonConversionException {
        try {
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new JsonConversionException("Failed to convert object to pretty JSON", e);
        }
    }
    
    /**
     * Converts a JSON string to a Java object of the specified class.
     * 
     * @param json The JSON string to convert
     * @param clazz The class of the target object
     * @param <T> The type of the target object
     * @return An instance of the target class
     * @throws JsonConversionException If conversion fails
     */
    public static <T> T fromJson(String json, Class<T> clazz) throws JsonConversionException {
        try {
            return objectMapper.readValue(json, clazz);
        } catch (IOException e) {
            throw new JsonConversionException("Failed to convert JSON to object of type " + clazz.getName(), e);
        }
    }
    
    /**
     * Converts a JSON string to a Java object using a TypeReference.
     * Useful for generic types like List<T> or Map<K,V>.
     * 
     * @param json The JSON string to convert
     * @param typeReference The TypeReference describing the target type
     * @param <T> The type of the target object
     * @return An instance of the target type
     * @throws JsonConversionException If conversion fails
     */
    public static <T> T fromJson(String json, TypeReference<T> typeReference) throws JsonConversionException {
        try {
            return objectMapper.readValue(json, typeReference);
        } catch (IOException e) {
            throw new JsonConversionException("Failed to convert JSON to object using TypeReference", e);
        }
    }
    
    /**
     * Converts a JSON input stream to a Java object of the specified class.
     * 
     * @param inputStream The input stream containing JSON data
     * @param clazz The class of the target object
     * @param <T> The type of the target object
     * @return An instance of the target class
     * @throws JsonConversionException If conversion fails
     */
    public static <T> T fromJson(InputStream inputStream, Class<T> clazz) throws JsonConversionException {
        try {
            return objectMapper.readValue(inputStream, clazz);
        } catch (IOException e) {
            throw new JsonConversionException("Failed to convert JSON input stream to object of type " + clazz.getName(), e);
        }
    }
    
    /**
     * Converts a JSON string to a JsonNode for dynamic JSON manipulation.
     * 
     * @param json The JSON string to convert
     * @return A JsonNode representing the JSON structure
     * @throws JsonConversionException If conversion fails
     */
    public static JsonNode toJsonNode(String json) throws JsonConversionException {
        try {
            return objectMapper.readTree(json);
        } catch (IOException e) {
            throw new JsonConversionException("Failed to convert JSON to JsonNode", e);
        }
    }
    
    /**
     * Converts a Java object to a JsonNode.
     * 
     * @param object The object to convert
     * @return A JsonNode representing the object
     * @throws JsonConversionException If conversion fails
     */
    public static JsonNode toJsonNode(Object object) throws JsonConversionException {
        return objectMapper.valueToTree(object);
    }
    
    /**
     * Creates a new empty ObjectNode for building JSON objects dynamically.
     * 
     * @return An empty ObjectNode
     */
    public static ObjectNode createObjectNode() {
        return objectMapper.createObjectNode();
    }
    
    /**
     * Creates a new empty ArrayNode for building JSON arrays dynamically.
     * 
     * @return An empty ArrayNode
     */
    public static ArrayNode createArrayNode() {
        return objectMapper.createArrayNode();
    }
    
    /**
     * Converts a JsonNode to a Java object of the specified class.
     * 
     * @param node The JsonNode to convert
     * @param clazz The class of the target object
     * @param <T> The type of the target object
     * @return An instance of the target class
     * @throws JsonConversionException If conversion fails
     */
    public static <T> T fromJsonNode(JsonNode node, Class<T> clazz) throws JsonConversionException {
        try {
            return objectMapper.treeToValue(node, clazz);
        } catch (JsonProcessingException e) {
            throw new JsonConversionException("Failed to convert JsonNode to object of type " + clazz.getName(), e);
        }
    }
    
    /**
     * Merges two JSON objects represented as strings.
     * Properties from the second JSON will overwrite properties from the first if they have the same name.
     * 
     * @param json1 The first JSON string
     * @param json2 The second JSON string
     * @return A merged JSON string
     * @throws JsonConversionException If merging fails
     */
    public static String mergeJson(String json1, String json2) throws JsonConversionException {
        try {
            JsonNode node1 = objectMapper.readTree(json1);
            JsonNode node2 = objectMapper.readTree(json2);
            
            if (!(node1 instanceof ObjectNode) || !(node2 instanceof ObjectNode)) {
                throw new JsonConversionException("Both JSON strings must represent objects for merging");
            }
            
            JsonNode merged = mergeNodes((ObjectNode) node1, (ObjectNode) node2);
            return objectMapper.writeValueAsString(merged);
        } catch (IOException e) {
            throw new JsonConversionException("Failed to merge JSON strings", e);
        }
    }
    
    /**
     * Merges two ObjectNodes recursively.
     * 
     * @param mainNode The main node that will be updated
     * @param updateNode The node containing updates to apply
     * @return The merged ObjectNode
     */
    private static JsonNode mergeNodes(ObjectNode mainNode, ObjectNode updateNode) {
        updateNode.fields().forEachRemaining(entry -> {
            String fieldName = entry.getKey();
            JsonNode value = entry.getValue();
            
            if (mainNode.has(fieldName)) {
                JsonNode mainValue = mainNode.get(fieldName);
                
                if (mainValue instanceof ObjectNode && value instanceof ObjectNode) {
                    // Recursively merge nested objects
                    mainNode.set(fieldName, mergeNodes((ObjectNode) mainValue, (ObjectNode) value));
                } else {
                    // Overwrite with the update value
                    mainNode.set(fieldName, value);
                }
            } else {
                // Add new field
                mainNode.set(fieldName, value);
            }
        });
        
        return mainNode;
    }
    
    /**
     * Validates a JSON string against a JSON schema.
     * 
     * @param json The JSON string to validate
     * @param schemaJson The JSON schema as a string
     * @return A validation result containing success status and any error messages
     * @throws JsonConversionException If validation processing fails
     */
    public static JsonValidationResult validateJson(String json, String schemaJson) throws JsonConversionException {
        try {
            JsonNode jsonNode = objectMapper.readTree(json);
            JsonNode schemaNode = objectMapper.readTree(schemaJson);
            
            JsonSchemaFactory factory = JsonSchemaFactory.byDefault();
            JsonSchema schema = factory.getJsonSchema(schemaNode);
            
            ProcessingReport report = schema.validate(jsonNode);
            return new JsonValidationResult(report.isSuccess(), report.toString());
        } catch (IOException | ProcessingException e) {
            throw new JsonConversionException("Failed to validate JSON against schema", e);
        }
    }
    
    /**
     * Checks if a string is valid JSON.
     * 
     * @param json The string to check
     * @return true if the string is valid JSON, false otherwise
     */
    public static boolean isValidJson(String json) {
        try {
            objectMapper.readTree(json);
            return true;
        } catch (IOException e) {
            return false;
        }
    }
    
    /**
     * Filters a JSON object by keeping only the specified fields.
     * 
     * @param json The JSON string to filter
     * @param fields The list of field names to keep
     * @return A filtered JSON string
     * @throws JsonConversionException If filtering fails
     */
    public static String filterJson(String json, List<String> fields) throws JsonConversionException {
        try {
            JsonNode node = objectMapper.readTree(json);
            if (!(node instanceof ObjectNode)) {
                throw new JsonConversionException("JSON string must represent an object for filtering");
            }
            
            ObjectNode filteredNode = objectMapper.createObjectNode();
            for (String field : fields) {
                if (node.has(field)) {
                    filteredNode.set(field, node.get(field));
                }
            }
            
            return objectMapper.writeValueAsString(filteredNode);
        } catch (IOException e) {
            throw new JsonConversionException("Failed to filter JSON", e);
        }
    }
    
    /**
     * Converts a Map to a JSON string.
     * 
     * @param map The map to convert
     * @return A JSON string representation of the map
     * @throws JsonConversionException If conversion fails
     */
    public static String mapToJson(Map<String, Object> map) throws JsonConversionException {
        return toJson(map);
    }
    
    /**
     * Converts a JSON string to a Map.
     * 
     * @param json The JSON string to convert
     * @return A Map representation of the JSON
     * @throws JsonConversionException If conversion fails
     */
    public static Map<String, Object> jsonToMap(String json) throws JsonConversionException {
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (IOException e) {
            throw new JsonConversionException("Failed to convert JSON to Map", e);
        }
    }
    
    /**
     * Result class for JSON schema validation operations.
     */
    public static class JsonValidationResult {
        private final boolean valid;
        private final String message;
        
        public JsonValidationResult(boolean valid, String message) {
            this.valid = valid;
            this.message = message;
        }
        
        public boolean isValid() {
            return valid;
        }
        
        public String getMessage() {
            return message;
        }
    }
    
    /**
     * Exception thrown when JSON conversion operations fail.
     */
    public static class JsonConversionException extends Exception {
        public JsonConversionException(String message) {
            super(message);
        }
        
        public JsonConversionException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}