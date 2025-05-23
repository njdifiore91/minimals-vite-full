package com.dollarfunding.mca;

import com.dollarfunding.mca.entity.*;
import com.dollarfunding.mca.dto.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;

import java.security.KeyPair;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Utility class providing helper methods for testing across the MCA application.
 * Contains methods for JWT token generation, test data creation, object comparison,
 * and JSON serialization/deserialization.
 */
public class TestUtils {

    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);

    private static final KeyPair keyPair = Keys.keyPairFor(SignatureAlgorithm.RS256);
    
    // Role constants matching the roles defined in the system
    public static final String ROLE_OPERATIONS_STAFF = "ROLE_OPERATIONS_STAFF";
    public static final String ROLE_SYSTEM_ADMIN = "ROLE_SYSTEM_ADMIN";

    /**
     * Creates a test JWT token for the Operations Staff role.
     * 
     * @param userId User ID to include in the token
     * @return JWT token string
     */
    public static String createOperationsStaffToken(String userId) {
        return createToken(userId, Collections.singletonList(ROLE_OPERATIONS_STAFF));
    }

    /**
     * Creates a test JWT token for the System Admin role.
     * 
     * @param userId User ID to include in the token
     * @return JWT token string
     */
    public static String createSystemAdminToken(String userId) {
        return createToken(userId, Collections.singletonList(ROLE_SYSTEM_ADMIN));
    }

    /**
     * Creates a test JWT token with multiple roles.
     * 
     * @param userId User ID to include in the token
     * @param roles List of roles to include in the token
     * @return JWT token string
     */
    public static String createToken(String userId, List<String> roles) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("roles", roles);
        claims.put("userId", userId);
        
        Date now = new Date();
        Date expiration = new Date(now.getTime() + 3600000); // 1 hour expiration
        
        return Jwts.builder()
                .setClaims(claims)
                .setSubject(userId)
                .setIssuedAt(now)
                .setExpiration(expiration)
                .setIssuer("dollarfunding-test")
                .signWith(keyPair.getPrivate(), SignatureAlgorithm.RS256)
                .compact();
    }

    /**
     * Creates a random Application entity for testing.
     * 
     * @return Application entity with random data
     */
    public static Application createRandomApplication() {
        Application application = new Application();
        application.setId(UUID.randomUUID());
        application.setStatus(getRandomEnum(ApplicationStatus.class));
        application.setReviewStatus(getRandomEnum(ReviewStatus.class));
        application.setMetadata(createRandomMetadata());
        application.setCreatedAt(LocalDateTime.now().minusDays(new Random().nextInt(30)));
        application.setUpdatedAt(LocalDateTime.now());
        return application;
    }

    /**
     * Creates a random Document entity for testing.
     * 
     * @param application The application to associate with the document
     * @return Document entity with random data
     */
    public static Document createRandomDocument(Application application) {
        Document document = new Document();
        document.setId(UUID.randomUUID());
        document.setApplication(application);
        document.setType(getRandomEnum(DocumentType.class));
        document.setStoragePath("s3://mca-documents-test/" + UUID.randomUUID() + ".pdf");
        document.setClassification(document.getType().name());
        document.setUploadedAt(LocalDateTime.now().minusDays(new Random().nextInt(10)));
        
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", new Random().nextInt(10000000));
        metadata.put("mimeType", "application/pdf");
        metadata.put("confidenceScore", new Random().nextDouble() * 100);
        document.setMetadata(metadata);
        
        return document;
    }

    /**
     * Creates a random MerchantDetails entity for testing.
     * 
     * @param application The application to associate with the merchant details
     * @return MerchantDetails entity with random data
     */
    public static MerchantDetails createRandomMerchantDetails(Application application) {
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setId(UUID.randomUUID());
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Test Business " + UUID.randomUUID().toString().substring(0, 8));
        merchantDetails.setDbaName("DBA " + UUID.randomUUID().toString().substring(0, 8));
        merchantDetails.setEin("12-" + (1000000 + new Random().nextInt(9000000)));
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Test Street");
        address.put("city", "Test City");
        address.put("state", "TS");
        address.put("zipCode", "12345");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Retail");
        merchantDetails.setRevenue(100000 + new Random().nextInt(900000));
        
        return merchantDetails;
    }

    /**
     * Creates a random Webhook entity for testing.
     * 
     * @return Webhook entity with random data
     */
    public static Webhook createRandomWebhook() {
        Webhook webhook = new Webhook();
        webhook.setId(UUID.randomUUID());
        webhook.setEndpointUrl("https://test-endpoint.com/webhook/" + UUID.randomUUID());
        webhook.setSecretKey(UUID.randomUUID().toString());
        webhook.setActive(new Random().nextBoolean());
        webhook.setEventType(getRandomEnum(EventType.class));
        webhook.setCreatedAt(LocalDateTime.now().minusDays(new Random().nextInt(30)));
        webhook.setUpdatedAt(LocalDateTime.now());
        return webhook;
    }

    /**
     * Creates a random metadata map for testing.
     * 
     * @return Map containing random metadata
     */
    public static Map<String, Object> createRandomMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("emailSubject", "Funding Application " + UUID.randomUUID());
        metadata.put("receivedAt", LocalDateTime.now().minusDays(new Random().nextInt(10)));
        metadata.put("automationConfidence", new Random().nextDouble() * 100);
        return metadata;
    }

    /**
     * Gets a random enum value from the specified enum class.
     * 
     * @param enumClass The enum class
     * @param <T> The enum type
     * @return Random enum value
     */
    public static <T extends Enum<T>> T getRandomEnum(Class<T> enumClass) {
        T[] values = enumClass.getEnumConstants();
        return values[new Random().nextInt(values.length)];
    }

    /**
     * Converts an object to its JSON string representation.
     * 
     * @param object The object to convert
     * @return JSON string representation
     * @throws RuntimeException if serialization fails
     */
    public static String toJson(Object object) {
        try {
            return objectMapper.writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to convert object to JSON", e);
        }
    }

    /**
     * Converts a JSON string to an object of the specified class.
     * 
     * @param json The JSON string
     * @param clazz The target class
     * @param <T> The target type
     * @return Object of the specified class
     * @throws RuntimeException if deserialization fails
     */
    public static <T> T fromJson(String json, Class<T> clazz) {
        try {
            return objectMapper.readValue(json, clazz);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to convert JSON to object", e);
        }
    }

    /**
     * Compares two objects for equality by converting them to JSON and comparing the JSON structures.
     * This is useful for comparing objects with nested structures or collections.
     * 
     * @param first First object
     * @param second Second object
     * @return true if the objects are equal, false otherwise
     */
    public static boolean areEqualByJson(Object first, Object second) {
        try {
            JsonNode firstNode = objectMapper.valueToTree(first);
            JsonNode secondNode = objectMapper.valueToTree(second);
            return firstNode.equals(secondNode);
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Compares two collections for equality by converting them to sets of JSON strings.
     * This is useful for comparing collections of objects regardless of order.
     * 
     * @param first First collection
     * @param second Second collection
     * @return true if the collections contain the same elements, false otherwise
     */
    public static boolean areCollectionsEqualByJson(Collection<?> first, Collection<?> second) {
        if (first == null && second == null) {
            return true;
        }
        if (first == null || second == null || first.size() != second.size()) {
            return false;
        }
        
        Set<String> firstJsonSet = first.stream()
                .map(TestUtils::toJson)
                .collect(Collectors.toSet());
        
        Set<String> secondJsonSet = second.stream()
                .map(TestUtils::toJson)
                .collect(Collectors.toSet());
        
        return firstJsonSet.equals(secondJsonSet);
    }

    /**
     * Converts a LocalDateTime to a Date object.
     * 
     * @param localDateTime The LocalDateTime to convert
     * @return Date object
     */
    public static Date toDate(LocalDateTime localDateTime) {
        return Date.from(localDateTime.atZone(ZoneId.systemDefault()).toInstant());
    }
}