package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO.AddressDTO;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import javax.validation.ConstraintViolation;
import javax.validation.Validation;
import javax.validation.Validator;
import javax.validation.ValidatorFactory;
import java.math.BigDecimal;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test class for {@link MerchantDetailsRequestDTO} that verifies validation constraints,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly validates merchant data,
 * handles address structures correctly, and converts between DTO and entity
 * objects appropriately.
 */
@DisplayName("MerchantDetailsRequestDTO Tests")
class MerchantDetailsRequestDTOTest {

    private Validator validator;
    private ObjectMapper objectMapper;
    private MerchantDetailsRequestDTO validDto;
    private AddressDTO validAddress;

    @BeforeEach
    void setUp() {
        // Initialize validator
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
        
        // Initialize ObjectMapper
        objectMapper = JsonUtil.getObjectMapper();
        
        // Create a valid address for testing
        validAddress = AddressDTO.builder()
                .streetAddress("123 Main St")
                .streetAddress2("Suite 100")
                .city("New York")
                .state("NY")
                .zipCode("10001")
                .build();
        
        // Create a valid DTO for testing
        validDto = MerchantDetailsRequestDTO.builder()
                .legalName("Acme Corporation")
                .dbaName("Acme Corp")
                .ein("12-3456789")
                .address(validAddress)
                .industry("Technology")
                .revenue(new BigDecimal("1000000.00"))
                .build();
    }

    @Nested
    @DisplayName("Validation Tests")
    class ValidationTests {

        @Test
        @DisplayName("Valid DTO should pass validation")
        void validDtoShouldPassValidation() {
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertTrue(violations.isEmpty(), "Valid DTO should not have validation violations");
        }

        @Test
        @DisplayName("DTO with null legal name should fail validation")
        void dtoWithNullLegalNameShouldFailValidation() {
            // Given
            validDto.setLegalName(null);
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null legal name should have validation violations");
            assertEquals(1, violations.size(), "Should have exactly one violation");
            
            ConstraintViolation<MerchantDetailsRequestDTO> violation = violations.iterator().next();
            assertEquals("legalName", violation.getPropertyPath().toString(), "Violation should be on legalName field");
            assertEquals("Legal name is required", violation.getMessage(), "Violation message should match annotation");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" "})  // blank string
        @DisplayName("DTO with blank legal name should fail validation")
        void dtoWithBlankLegalNameShouldFailValidation(String legalName) {
            // Given
            validDto.setLegalName(legalName);
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with blank legal name should have validation violations");
            
            boolean hasLegalNameViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("legalName") && 
                              v.getMessage().equals("Legal name is required"));
            
            assertTrue(hasLegalNameViolation, "Should have a violation on legalName field");
        }

        @Test
        @DisplayName("DTO with oversized legal name should fail validation")
        void dtoWithOversizedLegalNameShouldFailValidation() {
            // Given
            StringBuilder longName = new StringBuilder();
            for (int i = 0; i < 101; i++) {
                longName.append("a");
            }
            validDto.setLegalName(longName.toString());
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized legal name should have validation violations");
            
            boolean hasLegalNameSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("legalName") && 
                              v.getMessage().contains("cannot exceed 100 characters"));
            
            assertTrue(hasLegalNameSizeViolation, "Should have a size violation on legalName field");
        }

        @Test
        @DisplayName("DTO with oversized DBA name should fail validation")
        void dtoWithOversizedDbaNameShouldFailValidation() {
            // Given
            StringBuilder longName = new StringBuilder();
            for (int i = 0; i < 101; i++) {
                longName.append("a");
            }
            validDto.setDbaName(longName.toString());
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized DBA name should have validation violations");
            
            boolean hasDbaNameSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("dbaName") && 
                              v.getMessage().contains("cannot exceed 100 characters"));
            
            assertTrue(hasDbaNameSizeViolation, "Should have a size violation on dbaName field");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" "})  // blank string
        @DisplayName("DTO with blank EIN should fail validation")
        void dtoWithBlankEinShouldFailValidation(String ein) {
            // Given
            validDto.setEin(ein);
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with blank EIN should have validation violations");
            
            boolean hasEinViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("ein") && 
                              v.getMessage().equals("EIN is required"));
            
            assertTrue(hasEinViolation, "Should have a violation on ein field");
        }

        @ParameterizedTest
        @ValueSource(strings = {"123456789", "12345678", "12-345678", "123-45678", "12-34567890", "AB-1234567"})
        @DisplayName("DTO with invalid EIN format should fail validation")
        void dtoWithInvalidEinFormatShouldFailValidation(String ein) {
            // Given
            validDto.setEin(ein);
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with invalid EIN format should have validation violations");
            
            boolean hasEinFormatViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("ein") && 
                              v.getMessage().equals("EIN must be in format XX-XXXXXXX"));
            
            assertTrue(hasEinFormatViolation, "Should have a format violation on ein field");
        }

        @Test
        @DisplayName("DTO with null address should fail validation")
        void dtoWithNullAddressShouldFailValidation() {
            // Given
            validDto.setAddress(null);
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null address should have validation violations");
            
            boolean hasAddressViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("address") && 
                              v.getMessage().equals("Address is required"));
            
            assertTrue(hasAddressViolation, "Should have a violation on address field");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" "})  // blank string
        @DisplayName("DTO with blank industry should fail validation")
        void dtoWithBlankIndustryShouldFailValidation(String industry) {
            // Given
            validDto.setIndustry(industry);
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with blank industry should have validation violations");
            
            boolean hasIndustryViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("industry") && 
                              v.getMessage().equals("Industry is required"));
            
            assertTrue(hasIndustryViolation, "Should have a violation on industry field");
        }

        @Test
        @DisplayName("DTO with oversized industry should fail validation")
        void dtoWithOversizedIndustryShouldFailValidation() {
            // Given
            StringBuilder longIndustry = new StringBuilder();
            for (int i = 0; i < 51; i++) {
                longIndustry.append("a");
            }
            validDto.setIndustry(longIndustry.toString());
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with oversized industry should have validation violations");
            
            boolean hasIndustrySizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("industry") && 
                              v.getMessage().contains("cannot exceed 50 characters"));
            
            assertTrue(hasIndustrySizeViolation, "Should have a size violation on industry field");
        }

        @Test
        @DisplayName("DTO with null revenue should fail validation")
        void dtoWithNullRevenueShouldFailValidation() {
            // Given
            validDto.setRevenue(null);
            
            // When
            Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(validDto);
            
            // Then
            assertFalse(violations.isEmpty(), "DTO with null revenue should have validation violations");
            
            boolean hasRevenueViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("revenue") && 
                              v.getMessage().equals("Revenue is required"));
            
            assertTrue(hasRevenueViolation, "Should have a violation on revenue field");
        }
    }

    @Nested
    @DisplayName("Address Validation Tests")
    class AddressValidationTests {

        @Test
        @DisplayName("Valid address should pass validation")
        void validAddressShouldPassValidation() {
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertTrue(violations.isEmpty(), "Valid address should not have validation violations");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" "})  // blank string
        @DisplayName("Address with blank street address should fail validation")
        void addressWithBlankStreetAddressShouldFailValidation(String streetAddress) {
            // Given
            validAddress.setStreetAddress(streetAddress);
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertFalse(violations.isEmpty(), "Address with blank street address should have validation violations");
            
            boolean hasStreetAddressViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("streetAddress") && 
                              v.getMessage().equals("Street address is required"));
            
            assertTrue(hasStreetAddressViolation, "Should have a violation on streetAddress field");
        }

        @Test
        @DisplayName("Address with oversized street address should fail validation")
        void addressWithOversizedStreetAddressShouldFailValidation() {
            // Given
            StringBuilder longStreet = new StringBuilder();
            for (int i = 0; i < 101; i++) {
                longStreet.append("a");
            }
            validAddress.setStreetAddress(longStreet.toString());
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertFalse(violations.isEmpty(), "Address with oversized street address should have validation violations");
            
            boolean hasStreetAddressSizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("streetAddress") && 
                              v.getMessage().contains("cannot exceed 100 characters"));
            
            assertTrue(hasStreetAddressSizeViolation, "Should have a size violation on streetAddress field");
        }

        @Test
        @DisplayName("Address with oversized street address line 2 should fail validation")
        void addressWithOversizedStreetAddress2ShouldFailValidation() {
            // Given
            StringBuilder longStreet = new StringBuilder();
            for (int i = 0; i < 101; i++) {
                longStreet.append("a");
            }
            validAddress.setStreetAddress2(longStreet.toString());
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertFalse(violations.isEmpty(), "Address with oversized street address line 2 should have validation violations");
            
            boolean hasStreetAddress2SizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("streetAddress2") && 
                              v.getMessage().contains("cannot exceed 100 characters"));
            
            assertTrue(hasStreetAddress2SizeViolation, "Should have a size violation on streetAddress2 field");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" "})  // blank string
        @DisplayName("Address with blank city should fail validation")
        void addressWithBlankCityShouldFailValidation(String city) {
            // Given
            validAddress.setCity(city);
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertFalse(violations.isEmpty(), "Address with blank city should have validation violations");
            
            boolean hasCityViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("city") && 
                              v.getMessage().equals("City is required"));
            
            assertTrue(hasCityViolation, "Should have a violation on city field");
        }

        @Test
        @DisplayName("Address with oversized city should fail validation")
        void addressWithOversizedCityShouldFailValidation() {
            // Given
            StringBuilder longCity = new StringBuilder();
            for (int i = 0; i < 51; i++) {
                longCity.append("a");
            }
            validAddress.setCity(longCity.toString());
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertFalse(violations.isEmpty(), "Address with oversized city should have validation violations");
            
            boolean hasCitySizeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("city") && 
                              v.getMessage().contains("cannot exceed 50 characters"));
            
            assertTrue(hasCitySizeViolation, "Should have a size violation on city field");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "A", "ABC"})  // invalid state codes
        @DisplayName("Address with invalid state should fail validation")
        void addressWithInvalidStateShouldFailValidation(String state) {
            // Given
            validAddress.setState(state);
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertFalse(violations.isEmpty(), "Address with invalid state should have validation violations");
            
            boolean hasStateViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("state") && 
                              (v.getMessage().equals("State is required") || 
                               v.getMessage().equals("State must be a 2-letter code")));
            
            assertTrue(hasStateViolation, "Should have a violation on state field");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {" ", "123", "12345-", "1234", "123456", "12345-123", "12345-12345"})  // invalid ZIP codes
        @DisplayName("Address with invalid ZIP code should fail validation")
        void addressWithInvalidZipCodeShouldFailValidation(String zipCode) {
            // Given
            validAddress.setZipCode(zipCode);
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertFalse(violations.isEmpty(), "Address with invalid ZIP code should have validation violations");
            
            boolean hasZipCodeViolation = violations.stream()
                    .anyMatch(v -> v.getPropertyPath().toString().equals("zipCode") && 
                              (v.getMessage().equals("ZIP code is required") || 
                               v.getMessage().contains("ZIP code must be in format")));
            
            assertTrue(hasZipCodeViolation, "Should have a violation on zipCode field");
        }

        @ParameterizedTest
        @ValueSource(strings = {"12345", "12345-6789"})  // valid ZIP codes
        @DisplayName("Address with valid ZIP code should pass validation")
        void addressWithValidZipCodeShouldPassValidation(String zipCode) {
            // Given
            validAddress.setZipCode(zipCode);
            
            // When
            Set<ConstraintViolation<AddressDTO>> violations = validator.validate(validAddress);
            
            // Then
            assertTrue(violations.isEmpty(), "Address with valid ZIP code should not have validation violations");
        }
    }

    @Nested
    @DisplayName("JSON Serialization/Deserialization Tests")
    class JsonTests {

        @Test
        @DisplayName("DTO should serialize to JSON correctly")
        void dtoShouldSerializeToJsonCorrectly() throws Exception {
            // When
            String json = objectMapper.writeValueAsString(validDto);
            
            // Then
            assertNotNull(json, "JSON should not be null");
            assertTrue(json.contains("\"legal_name\":\"Acme Corporation\""), "JSON should contain legal_name field");
            assertTrue(json.contains("\"dba_name\":\"Acme Corp\""), "JSON should contain dba_name field");
            assertTrue(json.contains("\"ein\":\"12-3456789\""), "JSON should contain ein field");
            assertTrue(json.contains("\"industry\":\"Technology\""), "JSON should contain industry field");
            assertTrue(json.contains("\"revenue\":1000000.00"), "JSON should contain revenue field");
            assertTrue(json.contains("\"address\":"), "JSON should contain address field");
            assertTrue(json.contains("\"street_address\":\"123 Main St\""), "JSON should contain street_address field");
            assertTrue(json.contains("\"street_address_2\":\"Suite 100\""), "JSON should contain street_address_2 field");
            assertTrue(json.contains("\"city\":\"New York\""), "JSON should contain city field");
            assertTrue(json.contains("\"state\":\"NY\""), "JSON should contain state field");
            assertTrue(json.contains("\"zip_code\":\"10001\""), "JSON should contain zip_code field");
        }

        @Test
        @DisplayName("JSON should deserialize to DTO correctly")
        void jsonShouldDeserializeToDtoCorrectly() throws Exception {
            // Given
            String json = "{\"legal_name\":\"XYZ Inc\",\"dba_name\":\"XYZ\",\"ein\":\"98-7654321\",\"address\":{\"street_address\":\"456 Park Ave\",\"street_address_2\":\"Floor 2\",\"city\":\"Chicago\",\"state\":\"IL\",\"zip_code\":\"60601\"},\"industry\":\"Finance\",\"revenue\":500000.00}";
            
            // When
            MerchantDetailsRequestDTO dto = objectMapper.readValue(json, MerchantDetailsRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("XYZ Inc", dto.getLegalName(), "Legal name should match");
            assertEquals("XYZ", dto.getDbaName(), "DBA name should match");
            assertEquals("98-7654321", dto.getEin(), "EIN should match");
            assertEquals("Finance", dto.getIndustry(), "Industry should match");
            assertEquals(new BigDecimal("500000.00"), dto.getRevenue(), "Revenue should match");
            
            assertNotNull(dto.getAddress(), "Address should not be null");
            assertEquals("456 Park Ave", dto.getAddress().getStreetAddress(), "Street address should match");
            assertEquals("Floor 2", dto.getAddress().getStreetAddress2(), "Street address 2 should match");
            assertEquals("Chicago", dto.getAddress().getCity(), "City should match");
            assertEquals("IL", dto.getAddress().getState(), "State should match");
            assertEquals("60601", dto.getAddress().getZipCode(), "ZIP code should match");
        }

        @Test
        @DisplayName("DTO should ignore unknown JSON properties")
        void dtoShouldIgnoreUnknownJsonProperties() throws Exception {
            // Given
            String json = "{\"legal_name\":\"ABC LLC\",\"dba_name\":\"ABC\",\"ein\":\"45-6789012\",\"address\":{\"street_address\":\"789 Broadway\",\"city\":\"San Francisco\",\"state\":\"CA\",\"zip_code\":\"94105\",\"unknown_field\":\"value\"},\"industry\":\"Retail\",\"revenue\":750000.00,\"unknown_field\":\"value\"}";
            
            // When
            MerchantDetailsRequestDTO dto = objectMapper.readValue(json, MerchantDetailsRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("ABC LLC", dto.getLegalName(), "Legal name should match");
            assertEquals("ABC", dto.getDbaName(), "DBA name should match");
            assertEquals("45-6789012", dto.getEin(), "EIN should match");
            assertEquals("Retail", dto.getIndustry(), "Industry should match");
            assertEquals(new BigDecimal("750000.00"), dto.getRevenue(), "Revenue should match");
            
            assertNotNull(dto.getAddress(), "Address should not be null");
            assertEquals("789 Broadway", dto.getAddress().getStreetAddress(), "Street address should match");
            assertNull(dto.getAddress().getStreetAddress2(), "Street address 2 should be null");
            assertEquals("San Francisco", dto.getAddress().getCity(), "City should match");
            assertEquals("CA", dto.getAddress().getState(), "State should match");
            assertEquals("94105", dto.getAddress().getZipCode(), "ZIP code should match");
            // Unknown fields should be ignored without exception
        }

        @Test
        @DisplayName("JSON with missing optional fields should deserialize correctly")
        void jsonWithMissingOptionalFieldsShouldDeserializeCorrectly() throws Exception {
            // Given
            String json = "{\"legal_name\":\"DEF Corp\",\"ein\":\"56-7890123\",\"address\":{\"street_address\":\"321 Oak St\",\"city\":\"Boston\",\"state\":\"MA\",\"zip_code\":\"02108\"},\"industry\":\"Healthcare\",\"revenue\":1250000.00}";
            
            // When
            MerchantDetailsRequestDTO dto = objectMapper.readValue(json, MerchantDetailsRequestDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals("DEF Corp", dto.getLegalName(), "Legal name should match");
            assertNull(dto.getDbaName(), "DBA name should be null");
            assertEquals("56-7890123", dto.getEin(), "EIN should match");
            assertEquals("Healthcare", dto.getIndustry(), "Industry should match");
            assertEquals(new BigDecimal("1250000.00"), dto.getRevenue(), "Revenue should match");
            
            assertNotNull(dto.getAddress(), "Address should not be null");
            assertEquals("321 Oak St", dto.getAddress().getStreetAddress(), "Street address should match");
            assertNull(dto.getAddress().getStreetAddress2(), "Street address 2 should be null");
            assertEquals("Boston", dto.getAddress().getCity(), "City should match");
            assertEquals("MA", dto.getAddress().getState(), "State should match");
            assertEquals("02108", dto.getAddress().getZipCode(), "ZIP code should match");
        }
    }

    @Nested
    @DisplayName("Entity Conversion Tests")
    class EntityConversionTests {

        @Test
        @DisplayName("DTO should convert to entity correctly")
        void dtoShouldConvertToEntityCorrectly() {
            // When
            MerchantDetails entity = validDto.toEntity();
            
            // Then
            assertNotNull(entity, "Entity should not be null");
            assertEquals(validDto.getLegalName(), entity.getLegalName(), "Legal name should match");
            assertEquals(validDto.getDbaName(), entity.getDbaName(), "DBA name should match");
            assertEquals(validDto.getEin(), entity.getEin(), "EIN should match");
            assertEquals(validDto.getIndustry(), entity.getIndustry(), "Industry should match");
            assertEquals(validDto.getRevenue(), entity.getRevenue(), "Revenue should match");
            
            // Address is converted using toAddressObject method which returns the AddressDTO itself in this test
            // In a real implementation, this would convert to the actual Address object
            assertNotNull(entity.getAddress(), "Address should not be null");
        }

        @Test
        @DisplayName("Entity should convert to DTO correctly")
        void entityShouldConvertToDtoCorrectly() {
            // Given
            MerchantDetails entity = new MerchantDetails();
            entity.setLegalName("GHI Enterprises");
            entity.setDbaName("GHI");
            entity.setEin("78-9012345");
            entity.setIndustry("Manufacturing");
            entity.setRevenue(new BigDecimal("2000000.00"));
            entity.setAddress(validAddress); // Using AddressDTO as a placeholder for the real Address object
            
            // When
            MerchantDetailsRequestDTO dto = MerchantDetailsRequestDTO.fromEntity(entity);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(entity.getLegalName(), dto.getLegalName(), "Legal name should match");
            assertEquals(entity.getDbaName(), dto.getDbaName(), "DBA name should match");
            assertEquals(entity.getEin(), dto.getEin(), "EIN should match");
            assertEquals(entity.getIndustry(), dto.getIndustry(), "Industry should match");
            assertEquals(entity.getRevenue(), dto.getRevenue(), "Revenue should match");
            
            // Address is converted using fromAddressObject method
            assertNotNull(dto.getAddress(), "Address should not be null");
        }

        @Test
        @DisplayName("Null entity should convert to null DTO")
        void nullEntityShouldConvertToNullDto() {
            // When
            MerchantDetailsRequestDTO dto = MerchantDetailsRequestDTO.fromEntity(null);
            
            // Then
            assertNull(dto, "DTO should be null when entity is null");
        }

        @Test
        @DisplayName("Entity with null address should convert to DTO with null address")
        void entityWithNullAddressShouldConvertToDtoWithNullAddress() {
            // Given
            MerchantDetails entity = new MerchantDetails();
            entity.setLegalName("JKL Inc");
            entity.setDbaName("JKL");
            entity.setEin("89-0123456");
            entity.setIndustry("Consulting");
            entity.setRevenue(new BigDecimal("1500000.00"));
            entity.setAddress(null);
            
            // When
            MerchantDetailsRequestDTO dto = MerchantDetailsRequestDTO.fromEntity(entity);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(entity.getLegalName(), dto.getLegalName(), "Legal name should match");
            assertEquals(entity.getDbaName(), dto.getDbaName(), "DBA name should match");
            assertEquals(entity.getEin(), dto.getEin(), "EIN should match");
            assertEquals(entity.getIndustry(), dto.getIndustry(), "Industry should match");
            assertEquals(entity.getRevenue(), dto.getRevenue(), "Revenue should match");
            assertNull(dto.getAddress(), "Address should be null");
        }
    }

    @Nested
    @DisplayName("Address Conversion Tests")
    class AddressConversionTests {

        @Test
        @DisplayName("AddressDTO should convert to Address object correctly")
        void addressDtoShouldConvertToAddressObjectCorrectly() {
            // When
            Object addressObject = validAddress.toAddressObject();
            
            // Then
            assertNotNull(addressObject, "Address object should not be null");
            // In a real implementation, this would verify the conversion to the actual Address object
            // For this test, we're just checking that the method returns something (which is the DTO itself)
            assertTrue(addressObject instanceof AddressDTO, "Address object should be an instance of AddressDTO");
        }

        @Test
        @DisplayName("Address object should convert to AddressDTO correctly")
        void addressObjectShouldConvertToAddressDtoCorrectly() {
            // Given
            // Using the AddressDTO as a placeholder for the real Address object
            Object addressObject = validAddress;
            
            // When
            AddressDTO dto = AddressDTO.fromAddressObject(addressObject);
            
            // Then
            assertNotNull(dto, "AddressDTO should not be null");
            // In a real implementation, this would verify the conversion from the actual Address object
            // For this test, we're just checking that the method returns something
            assertSame(validAddress, dto, "Should return the same AddressDTO instance");
        }

        @Test
        @DisplayName("Null address object should convert to null AddressDTO")
        void nullAddressObjectShouldConvertToNullAddressDto() {
            // When
            AddressDTO dto = AddressDTO.fromAddressObject(null);
            
            // Then
            assertNull(dto, "AddressDTO should be null when address object is null");
        }

        @Test
        @DisplayName("Non-AddressDTO object should convert to empty AddressDTO")
        void nonAddressDtoObjectShouldConvertToEmptyAddressDto() {
            // Given
            Object nonAddressObject = "Not an address";
            
            // When
            AddressDTO dto = AddressDTO.fromAddressObject(nonAddressObject);
            
            // Then
            assertNotNull(dto, "AddressDTO should not be null");
            // In a real implementation, this would verify the conversion from a non-AddressDTO object
            // For this test, we're just checking that the method returns a new empty AddressDTO
            assertNotSame(validAddress, dto, "Should not return the same AddressDTO instance");
            assertNull(dto.getStreetAddress(), "Street address should be null");
            assertNull(dto.getStreetAddress2(), "Street address 2 should be null");
            assertNull(dto.getCity(), "City should be null");
            assertNull(dto.getState(), "State should be null");
            assertNull(dto.getZipCode(), "ZIP code should be null");
        }
    }
}