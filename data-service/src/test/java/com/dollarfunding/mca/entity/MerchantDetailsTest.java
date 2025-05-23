package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.EncryptionUtil;
import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the MerchantDetails entity.
 * 
 * These tests verify JPA mapping, field validation, relationships, and field-level encryption
 * for the MerchantDetails entity. The test suite ensures that the MerchantDetails entity can be
 * properly persisted and retrieved with all its attributes and relationships intact, and that
 * sensitive data is properly encrypted.
 */
@ExtendWith({SpringExtension.class, MockitoExtension.class})
@DataJpaTest
public class MerchantDetailsTest {

    @Autowired
    private TestEntityManager entityManager;
    
    @Mock
    private EncryptionUtil encryptionUtil;
    
    private Validator validator;
    
    @BeforeEach
    void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Configure mock encryption util
        when(encryptionUtil.encrypt(anyString())).thenAnswer(invocation -> {
            String input = invocation.getArgument(0);
            return "ENCRYPTED:" + input;
        });
        
        when(encryptionUtil.decrypt(anyString())).thenAnswer(invocation -> {
            String input = invocation.getArgument(0);
            if (input != null && input.startsWith("ENCRYPTED:")) {
                return input.substring(10);
            }
            return input;
        });
    }
    
    /**
     * Tests for basic entity properties and validation.
     */
    @Nested
    @DisplayName("Basic Entity Tests")
    class BasicEntityTests {
        
        @Test
        @DisplayName("Should create merchant details with default constructor")
        void shouldCreateMerchantDetailsWithDefaultConstructor() {
            // When
            MerchantDetails merchantDetails = new MerchantDetails();
            
            // Then
            assertNotNull(merchantDetails);
            assertNull(merchantDetails.getId());
            assertNull(merchantDetails.getApplicationId());
            assertNull(merchantDetails.getLegalName());
            assertNull(merchantDetails.getDbaName());
            assertNull(merchantDetails.getEin());
            assertNotNull(merchantDetails.getAddress());
            assertTrue(merchantDetails.getAddress().isEmpty());
            assertNull(merchantDetails.getIndustry());
            assertNull(merchantDetails.getRevenue());
        }
        
        @Test
        @DisplayName("Should create merchant details with required fields constructor")
        void shouldCreateMerchantDetailsWithRequiredFieldsConstructor() {
            // Given
            UUID applicationId = UUID.randomUUID();
            String legalName = "Acme Corporation";
            
            // When
            MerchantDetails merchantDetails = new MerchantDetails(applicationId, legalName);
            
            // Then
            assertNotNull(merchantDetails);
            assertEquals(applicationId, merchantDetails.getApplicationId());
            assertEquals(legalName, merchantDetails.getLegalName());
            assertNull(merchantDetails.getDbaName());
            assertNull(merchantDetails.getEin());
            assertNotNull(merchantDetails.getAddress());
            assertTrue(merchantDetails.getAddress().isEmpty());
            assertNull(merchantDetails.getIndustry());
            assertNull(merchantDetails.getRevenue());
        }
        
        @Test
        @DisplayName("Should create merchant details with all fields constructor")
        void shouldCreateMerchantDetailsWithAllFieldsConstructor() {
            // Given
            UUID applicationId = UUID.randomUUID();
            String legalName = "Acme Corporation";
            String dbaName = "Acme";
            String ein = "12-3456789";
            Map<String, Object> address = new HashMap<>();
            address.put("street", "123 Main St");
            address.put("city", "Anytown");
            address.put("state", "CA");
            address.put("zip", "12345");
            address.put("country", "USA");
            String industry = "Technology";
            BigDecimal revenue = new BigDecimal("1000000.00");
            
            // When
            MerchantDetails merchantDetails = new MerchantDetails(applicationId, legalName, dbaName, ein,
                    address, industry, revenue);
            
            // Then
            assertNotNull(merchantDetails);
            assertEquals(applicationId, merchantDetails.getApplicationId());
            assertEquals(legalName, merchantDetails.getLegalName());
            assertEquals(dbaName, merchantDetails.getDbaName());
            assertEquals(ein, merchantDetails.getEin());
            assertEquals(address, merchantDetails.getAddress());
            assertEquals(industry, merchantDetails.getIndustry());
            assertEquals(revenue, merchantDetails.getRevenue());
            
            // Verify address JSON was created
            assertNotNull(merchantDetails.getAddressJson());
            assertTrue(JsonUtil.isValidJson(merchantDetails.getAddressJson()));
        }
        
        @Test
        @DisplayName("Should validate required fields")
        void shouldValidateRequiredFields() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setApplicationId(null);
            merchantDetails.setLegalName(null);
            
            // When
            Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(merchantDetails);
            
            // Then
            assertEquals(1, violations.size());
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("legalName")));
        }
        
        @Test
        @DisplayName("Should validate field size constraints")
        void shouldValidateFieldSizeConstraints() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setApplicationId(UUID.randomUUID());
            
            // Test legal name too long (> 255 chars)
            StringBuilder longName = new StringBuilder();
            for (int i = 0; i < 30; i++) {
                longName.append("0123456789");
            }
            merchantDetails.setLegalName(longName.toString());
            
            // Test dba name too long (> 255 chars)
            merchantDetails.setDbaName(longName.toString());
            
            // Test ein too long (> 20 chars)
            merchantDetails.setEin("12345678901234567890123");
            
            // Test industry too long (> 100 chars)
            StringBuilder longIndustry = new StringBuilder();
            for (int i = 0; i < 11; i++) {
                longIndustry.append("0123456789");
            }
            merchantDetails.setIndustry(longIndustry.toString());
            
            // When
            Set<ConstraintViolation<MerchantDetails>> violations = validator.validate(merchantDetails);
            
            // Then
            assertTrue(violations.size() >= 3);
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("legalName")));
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("dbaName")));
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("ein")));
            assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("industry")));
        }
        
        @Test
        @DisplayName("Should create merchant details with builder")
        void shouldCreateMerchantDetailsWithBuilder() {
            // Given
            UUID applicationId = UUID.randomUUID();
            String legalName = "Acme Corporation";
            String dbaName = "Acme";
            String ein = "12-3456789";
            String industry = "Technology";
            BigDecimal revenue = new BigDecimal("1000000.00");
            
            // When
            MerchantDetails merchantDetails = new MerchantDetails.Builder(applicationId, legalName)
                    .withDbaName(dbaName)
                    .withEin(ein)
                    .addAddressField("street", "123 Main St")
                    .addAddressField("city", "Anytown")
                    .addAddressField("state", "CA")
                    .addAddressField("zip", "12345")
                    .addAddressField("country", "USA")
                    .withIndustry(industry)
                    .withRevenue(revenue)
                    .withEncryptionUtil(encryptionUtil)
                    .build();
            
            // Then
            assertNotNull(merchantDetails);
            assertEquals(applicationId, merchantDetails.getApplicationId());
            assertEquals(legalName, merchantDetails.getLegalName());
            assertEquals(dbaName, merchantDetails.getDbaName());
            assertEquals(ein, merchantDetails.getEin());
            assertEquals(industry, merchantDetails.getIndustry());
            assertEquals(revenue, merchantDetails.getRevenue());
            
            // Verify address fields
            Map<String, Object> address = merchantDetails.getAddress();
            assertEquals(5, address.size());
            assertEquals("123 Main St", address.get("street"));
            assertEquals("Anytown", address.get("city"));
            assertEquals("CA", address.get("state"));
            assertEquals("12345", address.get("zip"));
            assertEquals("USA", address.get("country"));
        }
    }
    
    /**
     * Tests for field-level encryption of sensitive PII data.
     */
    @Nested
    @DisplayName("Field-Level Encryption Tests")
    class FieldLevelEncryptionTests {
        
        @Test
        @DisplayName("Should encrypt and decrypt legal name")
        void shouldEncryptAndDecryptLegalName() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setEncryptionUtil(encryptionUtil);
            String legalName = "Acme Corporation";
            
            // When
            merchantDetails.setLegalName(legalName);
            
            // Then - Field should be encrypted internally
            assertEquals("ENCRYPTED:" + legalName, Mockito.mockingDetails(encryptionUtil).getInvocations().stream()
                    .filter(i -> i.getMethod().getName().equals("encrypt"))
                    .findFirst()
                    .map(i -> i.getArgument(0))
                    .orElse(null));
            
            // And decrypted when accessed
            assertEquals(legalName, merchantDetails.getLegalName());
        }
        
        @Test
        @DisplayName("Should encrypt and decrypt dba name")
        void shouldEncryptAndDecryptDbaName() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setEncryptionUtil(encryptionUtil);
            String dbaName = "Acme";
            
            // When
            merchantDetails.setDbaName(dbaName);
            
            // Then - Field should be encrypted internally
            assertEquals("ENCRYPTED:" + dbaName, Mockito.mockingDetails(encryptionUtil).getInvocations().stream()
                    .filter(i -> i.getMethod().getName().equals("encrypt"))
                    .findFirst()
                    .map(i -> i.getArgument(0))
                    .orElse(null));
            
            // And decrypted when accessed
            assertEquals(dbaName, merchantDetails.getDbaName());
        }
        
        @Test
        @DisplayName("Should encrypt and decrypt ein")
        void shouldEncryptAndDecryptEin() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setEncryptionUtil(encryptionUtil);
            String ein = "12-3456789";
            
            // When
            merchantDetails.setEin(ein);
            
            // Then - Field should be encrypted internally
            assertEquals("ENCRYPTED:" + ein, Mockito.mockingDetails(encryptionUtil).getInvocations().stream()
                    .filter(i -> i.getMethod().getName().equals("encrypt"))
                    .findFirst()
                    .map(i -> i.getArgument(0))
                    .orElse(null));
            
            // And decrypted when accessed
            assertEquals(ein, merchantDetails.getEin());
        }
        
        @Test
        @DisplayName("Should handle null values in encrypted fields")
        void shouldHandleNullValuesInEncryptedFields() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setEncryptionUtil(encryptionUtil);
            
            // When
            merchantDetails.setLegalName(null);
            merchantDetails.setDbaName(null);
            merchantDetails.setEin(null);
            
            // Then
            assertNull(merchantDetails.getLegalName());
            assertNull(merchantDetails.getDbaName());
            assertNull(merchantDetails.getEin());
        }
        
        @Test
        @DisplayName("Should handle empty values in encrypted fields")
        void shouldHandleEmptyValuesInEncryptedFields() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setEncryptionUtil(encryptionUtil);
            
            // When
            merchantDetails.setLegalName("");
            merchantDetails.setDbaName("");
            merchantDetails.setEin("");
            
            // Then
            assertEquals("", merchantDetails.getLegalName());
            assertEquals("", merchantDetails.getDbaName());
            assertEquals("", merchantDetails.getEin());
        }
        
        @Test
        @DisplayName("Should encrypt sensitive fields on post load")
        void shouldEncryptSensitiveFieldsOnPostLoad() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setEncryptionUtil(encryptionUtil);
            merchantDetails.setLegalName("Acme Corporation");
            merchantDetails.setDbaName("Acme");
            merchantDetails.setEin("12-3456789");
            
            // When - Simulate @PostLoad event
            merchantDetails.encryptSensitiveFields();
            
            // Then - Fields should be encrypted
            assertEquals("Acme Corporation", merchantDetails.getLegalName());
            assertEquals("Acme", merchantDetails.getDbaName());
            assertEquals("12-3456789", merchantDetails.getEin());
        }
    }
    
    /**
     * Tests for JSON address field conversion.
     */
    @Nested
    @DisplayName("JSON Address Tests")
    class JsonAddressTests {
        
        @Test
        @DisplayName("Should convert address map to JSON string")
        void shouldConvertAddressMapToJsonString() throws Exception {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            Map<String, Object> address = new HashMap<>();
            address.put("street", "123 Main St");
            address.put("city", "Anytown");
            address.put("state", "CA");
            address.put("zip", "12345");
            address.put("country", "USA");
            
            // When
            merchantDetails.setAddress(address);
            
            // Then
            assertNotNull(merchantDetails.getAddressJson());
            assertTrue(JsonUtil.isValidJson(merchantDetails.getAddressJson()));
            
            // Verify the JSON contains the expected data
            Map<String, Object> parsedAddress = JsonUtil.fromJson(
                merchantDetails.getAddressJson(), 
                new TypeReference<Map<String, Object>>() {}
            );
            assertEquals(5, parsedAddress.size());
            assertEquals("123 Main St", parsedAddress.get("street"));
            assertEquals("Anytown", parsedAddress.get("city"));
            assertEquals("CA", parsedAddress.get("state"));
            assertEquals("12345", parsedAddress.get("zip"));
            assertEquals("USA", parsedAddress.get("country"));
        }
        
        @Test
        @DisplayName("Should convert JSON string to address map")
        void shouldConvertJsonStringToAddressMap() throws Exception {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            String addressJson = "{\"street\":\"123 Main St\",\"city\":\"Anytown\",\"state\":\"CA\",\"zip\":\"12345\",\"country\":\"USA\"}";
            
            // When
            merchantDetails.setAddressJson(addressJson);
            
            // Then
            assertNotNull(merchantDetails.getAddress());
            assertEquals(5, merchantDetails.getAddress().size());
            assertEquals("123 Main St", merchantDetails.getAddress().get("street"));
            assertEquals("Anytown", merchantDetails.getAddress().get("city"));
            assertEquals("CA", merchantDetails.getAddress().get("state"));
            assertEquals("12345", merchantDetails.getAddress().get("zip"));
            assertEquals("USA", merchantDetails.getAddress().get("country"));
        }
        
        @Test
        @DisplayName("Should set and get individual address fields")
        void shouldSetAndGetIndividualAddressFields() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            
            // When
            merchantDetails.setAddressField("street", "123 Main St");
            merchantDetails.setAddressField("city", "Anytown");
            merchantDetails.setAddressField("state", "CA");
            merchantDetails.setAddressField("zip", "12345");
            merchantDetails.setAddressField("country", "USA");
            
            // Then
            assertEquals("123 Main St", merchantDetails.getAddressField("street"));
            assertEquals("Anytown", merchantDetails.getAddressField("city"));
            assertEquals("CA", merchantDetails.getAddressField("state"));
            assertEquals("12345", merchantDetails.getAddressField("zip"));
            assertEquals("USA", merchantDetails.getAddressField("country"));
            
            // Verify JSON was updated
            assertNotNull(merchantDetails.getAddressJson());
            assertTrue(JsonUtil.isValidJson(merchantDetails.getAddressJson()));
        }
        
        @Test
        @DisplayName("Should handle null or empty address")
        void shouldHandleNullOrEmptyAddress() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            
            // When
            merchantDetails.setAddress(null);
            
            // Then
            assertNotNull(merchantDetails.getAddress());
            assertTrue(merchantDetails.getAddress().isEmpty());
            assertEquals("{}", merchantDetails.getAddressJson());
            
            // When
            merchantDetails.setAddressJson(null);
            
            // Then
            assertNotNull(merchantDetails.getAddress());
            assertTrue(merchantDetails.getAddress().isEmpty());
            
            // When
            merchantDetails.setAddressJson("");
            
            // Then
            assertNotNull(merchantDetails.getAddress());
            assertTrue(merchantDetails.getAddress().isEmpty());
        }
        
        @Test
        @DisplayName("Should format full address correctly")
        void shouldFormatFullAddressCorrectly() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            Map<String, Object> address = new HashMap<>();
            address.put("street", "123 Main St");
            address.put("city", "Anytown");
            address.put("state", "CA");
            address.put("zip", "12345");
            address.put("country", "USA");
            merchantDetails.setAddress(address);
            
            // When
            String fullAddress = merchantDetails.getFullAddress();
            
            // Then
            assertEquals("123 Main St, Anytown, CA 12345, USA", fullAddress);
        }
        
        @Test
        @DisplayName("Should determine if address is valid")
        void shouldDetermineIfAddressIsValid() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            
            // When/Then - Empty address
            assertFalse(merchantDetails.hasValidAddress());
            
            // When - Partial address
            Map<String, Object> partialAddress = new HashMap<>();
            partialAddress.put("street", "123 Main St");
            partialAddress.put("city", "Anytown");
            merchantDetails.setAddress(partialAddress);
            
            // Then
            assertFalse(merchantDetails.hasValidAddress());
            
            // When - Complete address
            Map<String, Object> completeAddress = new HashMap<>();
            completeAddress.put("street", "123 Main St");
            completeAddress.put("city", "Anytown");
            completeAddress.put("state", "CA");
            completeAddress.put("zip", "12345");
            merchantDetails.setAddress(completeAddress);
            
            // Then
            assertTrue(merchantDetails.hasValidAddress());
        }
    }
    
    /**
     * Tests for One-to-One relationship with Application entity.
     */
    @Nested
    @DisplayName("Relationship Tests")
    class RelationshipTests {
        
        @Test
        @DisplayName("Should maintain bidirectional relationship with Application entity")
        void shouldMaintainBidirectionalRelationshipWithApplicationEntity() {
            // Given
            Application application = new Application();
            application.setId(UUID.randomUUID());
            MerchantDetails merchantDetails = new MerchantDetails();
            
            // When
            merchantDetails.setApplication(application);
            
            // Then
            assertSame(application, merchantDetails.getApplication());
            assertEquals(application.getId(), merchantDetails.getApplicationId());
        }
        
        @Test
        @DisplayName("Should update applicationId when application is set")
        void shouldUpdateApplicationIdWhenApplicationIsSet() {
            // Given
            UUID applicationId = UUID.randomUUID();
            Application application = new Application(ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
            application.setId(applicationId);
            MerchantDetails merchantDetails = new MerchantDetails();
            
            // When
            merchantDetails.setApplication(application);
            
            // Then
            assertEquals(applicationId, merchantDetails.getApplicationId());
        }
        
        @Test
        @DisplayName("Should handle null application")
        void shouldHandleNullApplication() {
            // Given
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setApplicationId(UUID.randomUUID());
            
            // When
            merchantDetails.setApplication(null);
            
            // Then
            assertNull(merchantDetails.getApplication());
            // ApplicationId should remain unchanged
            assertNotNull(merchantDetails.getApplicationId());
        }
    }
    
    /**
     * Tests for persistence and retrieval of MerchantDetails entity.
     */
    @Nested
    @DisplayName("Persistence Tests")
    class PersistenceTests {
        
        @Test
        @DisplayName("Should persist and retrieve merchant details with all fields")
        void shouldPersistAndRetrieveMerchantDetailsWithAllFields() {
            // Given
            UUID applicationId = UUID.randomUUID();
            String legalName = "Acme Corporation";
            String dbaName = "Acme";
            String ein = "12-3456789";
            Map<String, Object> address = new HashMap<>();
            address.put("street", "123 Main St");
            address.put("city", "Anytown");
            address.put("state", "CA");
            address.put("zip", "12345");
            address.put("country", "USA");
            String industry = "Technology";
            BigDecimal revenue = new BigDecimal("1000000.00");
            
            MerchantDetails merchantDetails = new MerchantDetails(applicationId, legalName, dbaName, ein,
                    address, industry, revenue);
            
            // When
            MerchantDetails savedMerchantDetails = entityManager.persistAndFlush(merchantDetails);
            entityManager.clear();
            MerchantDetails retrievedMerchantDetails = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
            
            // Then
            assertNotNull(retrievedMerchantDetails);
            assertEquals(savedMerchantDetails.getId(), retrievedMerchantDetails.getId());
            assertEquals(applicationId, retrievedMerchantDetails.getApplicationId());
            assertEquals(legalName, retrievedMerchantDetails.getLegalName());
            assertEquals(dbaName, retrievedMerchantDetails.getDbaName());
            assertEquals(ein, retrievedMerchantDetails.getEin());
            assertEquals(industry, retrievedMerchantDetails.getIndustry());
            assertEquals(0, revenue.compareTo(retrievedMerchantDetails.getRevenue()));
            
            // Verify address was persisted correctly
            Map<String, Object> retrievedAddress = retrievedMerchantDetails.getAddress();
            assertEquals(5, retrievedAddress.size());
            assertEquals("123 Main St", retrievedAddress.get("street"));
            assertEquals("Anytown", retrievedAddress.get("city"));
            assertEquals("CA", retrievedAddress.get("state"));
            assertEquals("12345", retrievedAddress.get("zip"));
            assertEquals("USA", retrievedAddress.get("country"));
        }
        
        @Test
        @DisplayName("Should persist and retrieve merchant details with application relationship")
        void shouldPersistAndRetrieveMerchantDetailsWithApplicationRelationship() {
            // Given
            Application application = new Application();
            entityManager.persistAndFlush(application);
            entityManager.clear();
            
            Application savedApplication = entityManager.find(Application.class, application.getId());
            
            MerchantDetails merchantDetails = new MerchantDetails(savedApplication.getId(), "Acme Corporation");
            merchantDetails.setApplication(savedApplication);
            
            // When
            MerchantDetails savedMerchantDetails = entityManager.persistAndFlush(merchantDetails);
            entityManager.clear();
            MerchantDetails retrievedMerchantDetails = entityManager.find(MerchantDetails.class, savedMerchantDetails.getId());
            
            // Then
            assertNotNull(retrievedMerchantDetails);
            assertEquals(savedApplication.getId(), retrievedMerchantDetails.getApplicationId());
            
            // Load the application relationship
            Application retrievedApplication = retrievedMerchantDetails.getApplication();
            assertNotNull(retrievedApplication);
            assertEquals(savedApplication.getId(), retrievedApplication.getId());
        }
    }
    
    /**
     * Tests for utility methods in the MerchantDetails entity.
     */
    @Nested
    @DisplayName("Utility Method Tests")
    class UtilityMethodTests {
        
        @Test
        @DisplayName("Should generate proper toString representation")
        void shouldGenerateProperToStringRepresentation() {
            // Given
            UUID id = UUID.randomUUID();
            UUID applicationId = UUID.randomUUID();
            MerchantDetails merchantDetails = new MerchantDetails(applicationId, "Acme Corporation");
            merchantDetails.setId(id);
            merchantDetails.setDbaName("Acme");
            merchantDetails.setEin("12-3456789");
            merchantDetails.setIndustry("Technology");
            merchantDetails.setRevenue(new BigDecimal("1000000.00"));
            
            Map<String, Object> address = new HashMap<>();
            address.put("street", "123 Main St");
            address.put("city", "Anytown");
            address.put("state", "CA");
            address.put("zip", "12345");
            merchantDetails.setAddress(address);
            
            // When
            String toString = merchantDetails.toString();
            
            // Then
            assertNotNull(toString);
            assertTrue(toString.contains(id.toString()));
            assertTrue(toString.contains(applicationId.toString()));
            assertTrue(toString.contains("[REDACTED]"));
            assertTrue(toString.contains("hasAddress=true"));
            assertTrue(toString.contains("industry='Technology'"));
            assertTrue(toString.contains("hasRevenue=true"));
        }
        
        @Test
        @DisplayName("Should implement equals and hashCode correctly")
        void shouldImplementEqualsAndHashCodeCorrectly() {
            // Given
            UUID id = UUID.randomUUID();
            
            MerchantDetails merchantDetails1 = new MerchantDetails();
            merchantDetails1.setId(id);
            
            MerchantDetails merchantDetails2 = new MerchantDetails();
            merchantDetails2.setId(id);
            
            MerchantDetails merchantDetails3 = new MerchantDetails();
            merchantDetails3.setId(UUID.randomUUID());
            
            // When/Then - equals
            assertEquals(merchantDetails1, merchantDetails1); // Same instance
            assertEquals(merchantDetails1, merchantDetails2); // Same ID
            assertNotEquals(merchantDetails1, merchantDetails3); // Different ID
            assertNotEquals(merchantDetails1, null); // Null comparison
            assertNotEquals(merchantDetails1, new Object()); // Different type
            
            // When/Then - hashCode
            assertEquals(merchantDetails1.hashCode(), merchantDetails2.hashCode()); // Same ID
            assertNotEquals(merchantDetails1.hashCode(), merchantDetails3.hashCode()); // Different ID
        }
    }
}