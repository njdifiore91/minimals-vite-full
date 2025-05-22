package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.test.context.ActiveProfiles;

import com.dollarfunding.mca.config.EncryptionConfig;

import java.util.Set;

/**
 * Unit test class for the MerchantDetails entity that verifies JPA mapping, field validation,
 * relationships, and field-level encryption.
 * 
 * Tests include validation of required fields, proper encryption and decryption of sensitive PII fields
 * (legal_name, dba_name, ein), JSON conversion for the address field, and the One-to-One relationship
 * with the Application entity.
 */
@DataJpaTest
@ActiveProfiles("test")
public class MerchantDetailsTest {

    @Autowired
    private TestEntityManager entityManager;
    
    private Validator validator;
    
    private MerchantDetails merchantDetails;
    private Application application;
    
    @BeforeEach
    public void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Create a test Application
        application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        application = entityManager.persistAndFlush(application);
        
        // Create a test MerchantDetails with valid data
        merchantDetails = new MerchantDetails();
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("ABC Corporation");
        merchantDetails.setDbaName("ABC Business");
        merchantDetails.setEin("12-3456789");
        
        // Create a valid address
        MerchantDetails.Address address = new MerchantDetails.Address();
        address.setStreet("123 Main St");
        address.setCity("New York");
        address.setState("NY");
        address.setZip("10001");
        address.setCountry("USA");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(new BigDecimal("1000000.00"));
    }
    
    @Test
    @DisplayName("Should validate required fields")
    public void testRequiredFields() {
        // Given
        MerchantDetails invalidMerchant = new MerchantDetails();
        
        // When
        Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(invalidMerchant);
        
        // Then
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("application")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("legalName")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("ein")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("address")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("industry")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("revenue")));
    }
    
    @Test
    @DisplayName("Should validate field size constraints")
    public void testFieldSizeConstraints() {
        // Given
        merchantDetails.setLegalName("A".repeat(256)); // Exceeds max size of 255
        merchantDetails.setDbaName("B".repeat(256)); // Exceeds max size of 255
        merchantDetails.setIndustry("C".repeat(101)); // Exceeds max size of 100
        
        // When
        Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(merchantDetails);
        
        // Then
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("legalName")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("dbaName")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("industry")));
    }
    
    @Test
    @DisplayName("Should validate EIN format")
    public void testEinFormat() {
        // Given
        merchantDetails.setEin("123456789"); // Invalid format, should be XX-XXXXXXX
        
        // When
        Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(merchantDetails);
        
        // Then
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("ein")));
        
        // Given valid format
        merchantDetails.setEin("12-3456789");
        
        // When
        violations = validator.validate(merchantDetails);
        
        // Then
        assertTrue(violations.isEmpty());
    }
    
    @Test
    @DisplayName("Should validate address fields")
    public void testAddressValidation() {
        // Given
        MerchantDetails.Address invalidAddress = new MerchantDetails.Address();
        // Missing required fields
        merchantDetails.setAddress(invalidAddress);
        
        // When
        Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(merchantDetails);
        
        // Then
        assertFalse(violations.isEmpty());
        
        // Given valid address
        MerchantDetails.Address validAddress = new MerchantDetails.Address();
        validAddress.setStreet("123 Main St");
        validAddress.setCity("New York");
        validAddress.setState("NY");
        validAddress.setZip("10001");
        validAddress.setCountry("USA");
        merchantDetails.setAddress(validAddress);
        
        // When
        violations = validator.validate(merchantDetails);
        
        // Then
        assertTrue(violations.isEmpty());
        
        // Test state length validation
        validAddress.setState("NYC"); // Should be 2 characters
        
        // When
        violations = validator.validate(merchantDetails);
        
        // Then
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("State must be a 2-letter code")));
        
        // Test zip code format validation
        validAddress.setState("NY");
        validAddress.setZip("1000"); // Invalid format
        
        // When
        violations = validator.validate(merchantDetails);
        
        // Then
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("Zip code must be in format")));
        
        // Test valid zip code formats
        validAddress.setZip("10001");
        violations = validator.validate(merchantDetails);
        assertTrue(violations.isEmpty());
        
        validAddress.setZip("10001-1234");
        violations = validator.validate(merchantDetails);
        assertTrue(violations.isEmpty());
    }
    
    @Test
    @DisplayName("Should persist and retrieve MerchantDetails entity")
    public void testPersistAndRetrieve() {
        // Given
        MerchantDetails savedMerchantDetails = entityManager.persistAndFlush(merchantDetails);
        entityManager.clear();
        
        // When
        MerchantDetails retrievedMerchantDetails = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
        
        // Then
        assertNotNull(retrievedMerchantDetails);
        assertEquals(merchantDetails.getLegalName(), retrievedMerchantDetails.getLegalName());
        assertEquals(merchantDetails.getDbaName(), retrievedMerchantDetails.getDbaName());
        assertEquals(merchantDetails.getEin(), retrievedMerchantDetails.getEin());
        assertEquals(merchantDetails.getIndustry(), retrievedMerchantDetails.getIndustry());
        assertEquals(merchantDetails.getRevenue(), retrievedMerchantDetails.getRevenue());
        
        // Verify address
        assertNotNull(retrievedMerchantDetails.getAddress());
        assertEquals(merchantDetails.getAddress().getStreet(), retrievedMerchantDetails.getAddress().getStreet());
        assertEquals(merchantDetails.getAddress().getCity(), retrievedMerchantDetails.getAddress().getCity());
        assertEquals(merchantDetails.getAddress().getState(), retrievedMerchantDetails.getAddress().getState());
        assertEquals(merchantDetails.getAddress().getZip(), retrievedMerchantDetails.getAddress().getZip());
        assertEquals(merchantDetails.getAddress().getCountry(), retrievedMerchantDetails.getAddress().getCountry());
        
        // Verify timestamps
        assertNotNull(retrievedMerchantDetails.getCreatedAt());
        assertNotNull(retrievedMerchantDetails.getUpdatedAt());
    }
    
    @Test
    @DisplayName("Should verify One-to-One relationship with Application entity")
    public void testApplicationRelationship() {
        // Given
        MerchantDetails savedMerchantDetails = entityManager.persistAndFlush(merchantDetails);
        entityManager.clear();
        
        // When
        MerchantDetails retrievedMerchantDetails = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
        Application retrievedApplication = entityManager.find(Application.class, application.getId());
        
        // Then
        assertNotNull(retrievedMerchantDetails.getApplication());
        assertEquals(application.getId(), retrievedMerchantDetails.getApplication().getId());
        
        // Verify bidirectional relationship
        assertNotNull(retrievedApplication.getMerchantDetails());
        assertEquals(retrievedMerchantDetails.getId(), retrievedApplication.getMerchantDetails().getId());
    }
    
    @Test
    @DisplayName("Should encrypt sensitive PII fields")
    public void testFieldEncryption() {
        // Given
        MerchantDetails savedMerchantDetails = entityManager.persistAndFlush(merchantDetails);
        
        // When - get the raw database values using native query
        Object[] rawValues = (Object[]) entityManager.getEntityManager()
                .createNativeQuery("SELECT legal_name, dba_name, ein FROM merchant_details WHERE id = :id")
                .setParameter("id", savedMerchantDetails.getId())
                .getSingleResult();
        
        String encryptedLegalName = (String) rawValues[0];
        String encryptedDbaName = (String) rawValues[1];
        String encryptedEin = (String) rawValues[2];
        
        // Then - verify the values are encrypted
        assertNotEquals(merchantDetails.getLegalName(), encryptedLegalName);
        assertNotEquals(merchantDetails.getDbaName(), encryptedDbaName);
        assertNotEquals(merchantDetails.getEin(), encryptedEin);
        
        // Verify the encrypted values are in Base64 format (a characteristic of encrypted data)
        assertTrue(encryptedLegalName.matches("^[A-Za-z0-9+/]+={0,2}$"));
        assertTrue(encryptedDbaName.matches("^[A-Za-z0-9+/]+={0,2}$"));
        assertTrue(encryptedEin.matches("^[A-Za-z0-9+/]+={0,2}$"));
        
        // Verify that when we retrieve the entity, the values are properly decrypted
        entityManager.clear();
        MerchantDetails retrievedMerchant = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
        assertEquals(merchantDetails.getLegalName(), retrievedMerchant.getLegalName());
        assertEquals(merchantDetails.getDbaName(), retrievedMerchant.getDbaName());
        assertEquals(merchantDetails.getEin(), retrievedMerchant.getEin());
    }
    
    @Test
    @DisplayName("Should store address as JSON")
    public void testAddressJsonStorage() {
        // Given
        MerchantDetails savedMerchantDetails = entityManager.persist(merchantDetails);
        
        // When - get the raw database value using native query
        String jsonAddress = (String) entityManager.getEntityManager()
                .createNativeQuery("SELECT address FROM merchant_details WHERE id = :id")
                .setParameter("id", savedMerchantDetails.getId())
                .getSingleResult();
        
        // Then - verify it's a valid JSON string
        assertNotNull(jsonAddress);
        assertTrue(jsonAddress.contains("street"));
        assertTrue(jsonAddress.contains("city"));
        assertTrue(jsonAddress.contains("state"));
        assertTrue(jsonAddress.contains("zip"));
        assertTrue(jsonAddress.contains("country"));
        assertTrue(jsonAddress.contains("123 Main St"));
        assertTrue(jsonAddress.contains("New York"));
        assertTrue(jsonAddress.contains("NY"));
        assertTrue(jsonAddress.contains("10001"));
        assertTrue(jsonAddress.contains("USA"));
    }
    
    @Test
    @DisplayName("Should update MerchantDetails entity")
    public void testUpdateMerchantDetails() {
        // Given
        MerchantDetails savedMerchantDetails = entityManager.persistAndFlush(merchantDetails);
        entityManager.clear();
        
        // When - retrieve, update and save
        MerchantDetails retrievedMerchantDetails = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
        retrievedMerchantDetails.setLegalName("XYZ Corporation");
        retrievedMerchantDetails.setDbaName("XYZ Business");
        retrievedMerchantDetails.setIndustry("Finance");
        retrievedMerchantDetails.setRevenue(new BigDecimal("2000000.00"));
        
        MerchantDetails.Address updatedAddress = retrievedMerchantDetails.getAddress();
        updatedAddress.setStreet("456 Park Ave");
        updatedAddress.setCity("Chicago");
        updatedAddress.setState("IL");
        updatedAddress.setZip("60601");
        retrievedMerchantDetails.setAddress(updatedAddress);
        
        entityManager.persistAndFlush(retrievedMerchantDetails);
        entityManager.clear();
        
        // Then - verify updates were saved
        MerchantDetails updatedMerchantDetails = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
        assertEquals("XYZ Corporation", updatedMerchantDetails.getLegalName());
        assertEquals("XYZ Business", updatedMerchantDetails.getDbaName());
        assertEquals("Finance", updatedMerchantDetails.getIndustry());
        assertEquals(new BigDecimal("2000000.00"), updatedMerchantDetails.getRevenue());
        
        assertEquals("456 Park Ave", updatedMerchantDetails.getAddress().getStreet());
        assertEquals("Chicago", updatedMerchantDetails.getAddress().getCity());
        assertEquals("IL", updatedMerchantDetails.getAddress().getState());
        assertEquals("60601", updatedMerchantDetails.getAddress().getZip());
        
        // Verify updatedAt timestamp was updated
        assertTrue(updatedMerchantDetails.getUpdatedAt().isAfter(updatedMerchantDetails.getCreatedAt()));
    }
    
    @Test
    @DisplayName("Should handle null optional fields")
    public void testNullOptionalFields() {
        // Given
        merchantDetails.setDbaName(null); // DBA name is optional
        
        // When
        Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(merchantDetails);
        
        // Then - should be valid
        assertTrue(violations.isEmpty());
        
        // When - persist and retrieve
        MerchantDetails savedMerchantDetails = entityManager.persistAndFlush(merchantDetails);
        entityManager.clear();
        MerchantDetails retrievedMerchantDetails = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
        
        // Then - null value should be preserved
        assertNull(retrievedMerchantDetails.getDbaName());
    }
    
    @Test
    @DisplayName("Should properly implement equals and hashCode")
    public void testEqualsAndHashCode() {
        // Given
        MerchantDetails merchant1 = new MerchantDetails();
        merchant1.setId(1L);
        
        MerchantDetails merchant2 = new MerchantDetails();
        merchant2.setId(1L);
        
        MerchantDetails merchant3 = new MerchantDetails();
        merchant3.setId(2L);
        
        // Then
        assertEquals(merchant1, merchant2);
        assertNotEquals(merchant1, merchant3);
        assertEquals(merchant1.hashCode(), merchant2.hashCode());
        assertNotEquals(merchant1.hashCode(), merchant3.hashCode());
    }
    
    @Test
    @DisplayName("Should implement proper toString method")
    public void testToString() {
        // Given
        merchantDetails.setId(1L);
        
        // When
        String toString = merchantDetails.toString();
        
        // Then
        assertNotNull(toString);
        assertTrue(toString.contains("id=1"));
        assertTrue(toString.contains("legalName='[REDACTED]'"));
        assertTrue(toString.contains("dbaName='[REDACTED]'"));
        assertTrue(toString.contains("ein='[REDACTED]'"));
        assertTrue(toString.contains("industry='Technology'"));
        
        // Verify PII is not exposed in toString
        assertFalse(toString.contains("ABC Corporation"));
        assertFalse(toString.contains("ABC Business"));
        assertFalse(toString.contains("12-3456789"));
    }
    
    @Test
    @DisplayName("Should use builder pattern correctly")
    public void testBuilderPattern() {
        // Given
        MerchantDetails.Address address = MerchantDetails.Address.builder()
                .street("123 Main St")
                .city("New York")
                .state("NY")
                .zip("10001")
                .country("USA")
                .build();
        
        MerchantDetails builtMerchant = MerchantDetails.builder()
                .application(application)
                .legalName("ABC Corporation")
                .dbaName("ABC Business")
                .ein("12-3456789")
                .address(address)
                .industry("Technology")
                .revenue(new BigDecimal("1000000.00"))
                .build();
        
        // When
        Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(builtMerchant);
        
        // Then
        assertTrue(violations.isEmpty());
        assertEquals("ABC Corporation", builtMerchant.getLegalName());
        assertEquals("ABC Business", builtMerchant.getDbaName());
        assertEquals("12-3456789", builtMerchant.getEin());
        assertEquals("Technology", builtMerchant.getIndustry());
        assertEquals(new BigDecimal("1000000.00"), builtMerchant.getRevenue());
        assertEquals("123 Main St", builtMerchant.getAddress().getStreet());
        assertEquals("New York", builtMerchant.getAddress().getCity());
        assertEquals("NY", builtMerchant.getAddress().getState());
        assertEquals("10001", builtMerchant.getAddress().getZip());
        assertEquals("USA", builtMerchant.getAddress().getCountry());
    }
}