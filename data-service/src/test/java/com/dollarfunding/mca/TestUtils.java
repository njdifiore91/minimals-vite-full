package com.dollarfunding.mca;

import com.dollarfunding.mca.security.RoleConstants;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.core.io.ClassPathResource;
import org.springframework.util.ResourceUtils;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * Utility class providing helper methods for testing across the MCA application.
 * <p>
 * This class includes methods for:
 * - Creating test JWT tokens with different roles
 * - Generating random test data
 * - Comparing objects for equality
 * - Working with JSON for API testing
 */
public final class TestUtils {

    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    private static KeyPair keyPair;
    
    // Prevent instantiation
    private TestUtils() {
        throw new UnsupportedOperationException("Utility class cannot be instantiated");
    }

    /**
     * Generates a JWT token for testing with the specified role.
     *
     * @param username the username to include in the token
     * @param role     the role to include in the token (use constants from RoleConstants)
     * @return a JWT token string
     */
    public static String generateJwtToken(String username, String role) {
        return generateJwtToken(username, Collections.singletonList(role), 3600000L); // 1 hour expiry
    }

    /**
     * Generates a JWT token for testing with the specified roles and expiration time.
     *
     * @param username   the username to include in the token
     * @param roles      the roles to include in the token (use constants from RoleConstants)
     * @param expiryTime the token expiry time in milliseconds
     * @return a JWT token string
     */
    public static String generateJwtToken(String username, List<String> roles, Long expiryTime) {
        try {
            Date now = new Date();
            Date expiry = new Date(now.getTime() + expiryTime);
            
            Map<String, Object> claims = new HashMap<>();
            claims.put("roles", roles);
            claims.put("username", username);
            
            return Jwts.builder()
                    .setClaims(claims)
                    .setSubject(username)
                    .setIssuedAt(now)
                    .setExpiration(expiry)
                    .setIssuer("mca-test")
                    .setAudience("mca-test-client")
                    .signWith(getSigningKey(), SignatureAlgorithm.RS256)
                    .compact();
        } catch (Exception e) {
            throw new RuntimeException("Error generating JWT token for testing", e);
        }
    }

    /**
     * Generates a JWT token for an Operations Staff user.
     *
     * @param username the username to include in the token
     * @return a JWT token string
     */
    public static String generateOperationsStaffToken(String username) {
        return generateJwtToken(username, RoleConstants.ROLE_OPERATIONS_STAFF);
    }

    /**
     * Generates a JWT token for a System Admin user.
     *
     * @param username the username to include in the token
     * @return a JWT token string
     */
    public static String generateSystemAdminToken(String username) {
        return generateJwtToken(username, RoleConstants.ROLE_SYSTEM_ADMIN);
    }

    /**
     * Gets the private key for signing JWT tokens.
     * In a test environment, we generate a key pair if none exists.
     *
     * @return the private key for signing
     */
    private static PrivateKey getSigningKey() {
        if (keyPair == null) {
            try {
                // Try to load keys from test resources if available
                File privateKeyFile = ResourceUtils.getFile("classpath:jwt/private_key.pem");
                if (privateKeyFile.exists()) {
                    byte[] privateKeyBytes = Files.readAllBytes(privateKeyFile.toPath());
                    String privateKeyPEM = new String(privateKeyBytes)
                            .replace("-----BEGIN PRIVATE KEY-----", "")
                            .replace("-----END PRIVATE KEY-----", "")
                            .replaceAll("\\s", "");
                    
                    byte[] decodedKey = Base64.getDecoder().decode(privateKeyPEM);
                    KeyFactory keyFactory = KeyFactory.getInstance("RSA");
                    PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(decodedKey);
                    return keyFactory.generatePrivate(keySpec);
                }
            } catch (Exception e) {
                // If loading fails, generate a new key pair
                keyPair = Keys.keyPairFor(SignatureAlgorithm.RS256);
            }
            
            if (keyPair == null) {
                keyPair = Keys.keyPairFor(SignatureAlgorithm.RS256);
            }
        }
        
        return keyPair.getPrivate();
    }

    /**
     * Gets the public key for verifying JWT tokens.
     *
     * @return the public key for verification
     */
    public static PublicKey getVerificationKey() {
        if (keyPair == null) {
            getSigningKey(); // Initialize key pair if needed
        }
        
        try {
            // Try to load keys from test resources if available
            File publicKeyFile = ResourceUtils.getFile("classpath:jwt/public_key.pem");
            if (publicKeyFile.exists()) {
                byte[] publicKeyBytes = Files.readAllBytes(publicKeyFile.toPath());
                String publicKeyPEM = new String(publicKeyBytes)
                        .replace("-----BEGIN PUBLIC KEY-----", "")
                        .replace("-----END PUBLIC KEY-----", "")
                        .replaceAll("\\s", "");
                
                byte[] decodedKey = Base64.getDecoder().decode(publicKeyPEM);
                KeyFactory keyFactory = KeyFactory.getInstance("RSA");
                X509EncodedKeySpec keySpec = new X509EncodedKeySpec(decodedKey);
                return keyFactory.generatePublic(keySpec);
            }
        } catch (Exception e) {
            // If loading fails, use the generated key pair
        }
        
        return keyPair.getPublic();
    }

    /**
     * Generates a random string of the specified length.
     *
     * @param length the length of the string to generate
     * @return a random alphanumeric string
     */
    public static String randomString(int length) {
        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        StringBuilder sb = new StringBuilder(length);
        Random random = new Random();
        
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        
        return sb.toString();
    }

    /**
     * Generates a random email address for testing.
     *
     * @return a random email address
     */
    public static String randomEmail() {
        return randomString(8) + "@" + randomString(5) + ".com";
    }

    /**
     * Generates a random integer within the specified range.
     *
     * @param min the minimum value (inclusive)
     * @param max the maximum value (exclusive)
     * @return a random integer
     */
    public static int randomInt(int min, int max) {
        return ThreadLocalRandom.current().nextInt(min, max);
    }

    /**
     * Generates a random long within the specified range.
     *
     * @param min the minimum value (inclusive)
     * @param max the maximum value (exclusive)
     * @return a random long
     */
    public static long randomLong(long min, long max) {
        return ThreadLocalRandom.current().nextLong(min, max);
    }

    /**
     * Generates a random double within the specified range.
     *
     * @param min the minimum value (inclusive)
     * @param max the maximum value (exclusive)
     * @return a random double
     */
    public static double randomDouble(double min, double max) {
        return ThreadLocalRandom.current().nextDouble(min, max);
    }

    /**
     * Generates a random boolean value.
     *
     * @return a random boolean
     */
    public static boolean randomBoolean() {
        return ThreadLocalRandom.current().nextBoolean();
    }

    /**
     * Generates a random date within the specified range.
     *
     * @param startInclusive the start date (inclusive)
     * @param endExclusive   the end date (exclusive)
     * @return a random date
     */
    public static LocalDate randomDate(LocalDate startInclusive, LocalDate endExclusive) {
        long startEpochDay = startInclusive.toEpochDay();
        long endEpochDay = endExclusive.toEpochDay();
        long randomDay = ThreadLocalRandom.current().nextLong(startEpochDay, endEpochDay);
        return LocalDate.ofEpochDay(randomDay);
    }

    /**
     * Generates a random date-time within the specified range.
     *
     * @param startInclusive the start date-time (inclusive)
     * @param endExclusive   the end date-time (exclusive)
     * @return a random date-time
     */
    public static LocalDateTime randomDateTime(LocalDateTime startInclusive, LocalDateTime endExclusive) {
        long startEpochSecond = startInclusive.atZone(ZoneId.systemDefault()).toEpochSecond();
        long endEpochSecond = endExclusive.atZone(ZoneId.systemDefault()).toEpochSecond();
        long randomSecond = ThreadLocalRandom.current().nextLong(startEpochSecond, endEpochSecond);
        return LocalDateTime.ofInstant(java.time.Instant.ofEpochSecond(randomSecond), ZoneId.systemDefault());
    }

    /**
     * Generates a random UUID string.
     *
     * @return a random UUID string
     */
    public static String randomUuid() {
        return UUID.randomUUID().toString();
    }

    /**
     * Selects a random element from the provided list.
     *
     * @param <T>  the type of elements in the list
     * @param list the list to select from
     * @return a randomly selected element, or null if the list is empty
     */
    public static <T> T randomElement(List<T> list) {
        if (list == null || list.isEmpty()) {
            return null;
        }
        return list.get(ThreadLocalRandom.current().nextInt(list.size()));
    }

    /**
     * Selects a random element from the provided array.
     *
     * @param <T>   the type of elements in the array
     * @param array the array to select from
     * @return a randomly selected element, or null if the array is empty
     */
    public static <T> T randomElement(T[] array) {
        if (array == null || array.length == 0) {
            return null;
        }
        return array[ThreadLocalRandom.current().nextInt(array.length)];
    }

    /**
     * Creates a random subset of the provided list.
     *
     * @param <T>  the type of elements in the list
     * @param list the list to select from
     * @param size the size of the subset to create
     * @return a randomly selected subset of the list
     */
    public static <T> List<T> randomSubset(List<T> list, int size) {
        if (list == null || list.isEmpty() || size <= 0) {
            return Collections.emptyList();
        }
        
        if (size >= list.size()) {
            return new ArrayList<>(list);
        }
        
        List<T> copy = new ArrayList<>(list);
        Collections.shuffle(copy);
        return copy.subList(0, size);
    }

    /**
     * Converts an object to its JSON string representation.
     *
     * @param object the object to convert
     * @return the JSON string representation of the object
     * @throws RuntimeException if the conversion fails
     */
    public static String toJson(Object object) {
        try {
            return objectMapper.writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Error converting object to JSON", e);
        }
    }

    /**
     * Converts a JSON string to an object of the specified type.
     *
     * @param <T>        the type of the object
     * @param json       the JSON string to convert
     * @param targetType the class of the target type
     * @return the object representation of the JSON string
     * @throws RuntimeException if the conversion fails
     */
    public static <T> T fromJson(String json, Class<T> targetType) {
        try {
            return objectMapper.readValue(json, targetType);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Error converting JSON to object", e);
        }
    }

    /**
     * Converts a JSON string to a JsonNode for flexible access.
     *
     * @param json the JSON string to convert
     * @return the JsonNode representation of the JSON string
     * @throws RuntimeException if the conversion fails
     */
    public static JsonNode jsonToNode(String json) {
        try {
            return objectMapper.readTree(json);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Error converting JSON to JsonNode", e);
        }
    }

    /**
     * Reads a JSON file from the classpath and converts it to an object of the specified type.
     *
     * @param <T>        the type of the object
     * @param path       the classpath path to the JSON file
     * @param targetType the class of the target type
     * @return the object representation of the JSON file
     * @throws RuntimeException if the file cannot be read or the conversion fails
     */
    public static <T> T readJsonFromClasspath(String path, Class<T> targetType) {
        try {
            ClassPathResource resource = new ClassPathResource(path);
            return objectMapper.readValue(resource.getInputStream(), targetType);
        } catch (IOException e) {
            throw new RuntimeException("Error reading JSON from classpath: " + path, e);
        }
    }

    /**
     * Compares two objects for deep equality, handling collections and nested objects.
     * This is useful for comparing complex objects in test assertions.
     *
     * @param expected the expected object
     * @param actual   the actual object
     * @return true if the objects are deeply equal, false otherwise
     */
    public static boolean deepEquals(Object expected, Object actual) {
        if (expected == actual) {
            return true;
        }
        
        if (expected == null || actual == null) {
            return false;
        }
        
        // Convert both objects to JSON and compare the JSON structures
        try {
            JsonNode expectedNode = objectMapper.valueToTree(expected);
            JsonNode actualNode = objectMapper.valueToTree(actual);
            return expectedNode.equals(actualNode);
        } catch (Exception e) {
            // Fall back to regular equals if JSON conversion fails
            return Objects.equals(expected, actual);
        }
    }

    /**
     * Filters a collection based on a predicate and returns a new list.
     *
     * @param <T>        the type of elements in the collection
     * @param collection the collection to filter
     * @param predicate  the predicate to apply
     * @return a new list containing only the elements that match the predicate
     */
    public static <T> List<T> filterCollection(Collection<T> collection, Predicate<T> predicate) {
        if (collection == null) {
            return Collections.emptyList();
        }
        
        return collection.stream()
                .filter(predicate)
                .collect(Collectors.toList());
    }

    /**
     * Reads a file from the classpath as a string.
     *
     * @param path the classpath path to the file
     * @return the contents of the file as a string
     * @throws RuntimeException if the file cannot be read
     */
    public static String readFileFromClasspath(String path) {
        try {
            ClassPathResource resource = new ClassPathResource(path);
            return new String(Files.readAllBytes(resource.getFile().toPath()));
        } catch (IOException e) {
            throw new RuntimeException("Error reading file from classpath: " + path, e);
        }
    }

    /**
     * Formats a date-time for use in test data.
     * 
     * @param dateTime the date-time to format
     * @return the formatted date-time string
     */
    public static String formatDateTime(LocalDateTime dateTime) {
        return dateTime.toString();
    }

    /**
     * Formats a date for use in test data.
     * 
     * @param date the date to format
     * @return the formatted date string
     */
    public static String formatDate(LocalDate date) {
        return date.toString();
    }
}