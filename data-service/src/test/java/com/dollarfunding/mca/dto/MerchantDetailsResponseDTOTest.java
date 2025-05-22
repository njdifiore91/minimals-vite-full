package com.dollarfunding.mca.dto;

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

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Test class for {@link MerchantDetailsResponseDTO} that validates the merchant details structure,
 * JSON serialization/deserialization, and entity conversion.
 * 
 * This test suite ensures that the DTO properly represents merchant information,
 * handles sensitive PII data appropriately, and formats address and financial
 * information consistently.
 */
@DisplayName("MerchantDetailsResponseDTO Tests")
class MerchantDetailsResponseDTOTest {

    private ObjectMapper objectMapper;
    private MerchantDetails mockMerchantDetails;
    private Map<String, String> testAddress;

    @BeforeEach
    void setUp() {
        // Initialize ObjectMapper
        objectMapper = JsonUtil.getObjectMapper();
        
        // Create test address
        testAddress = new HashMap<>();
        testAddress.put("street", "123 Main St");
        testAddress.put("city", "New York");
        testAddress.put("state", "NY");
        testAddress.put("zip", "10001");
        testAddress.put("country", "USA");
        
        // Create mock MerchantDetails entity
        mockMerchantDetails = mock(MerchantDetails.class);
        when(mockMerchantDetails.getId()).thenReturn(1L);
        when(mockMerchantDetails.getApplicationId()).thenReturn(100L);
        when(mockMerchantDetails.getLegalName()).thenReturn("Acme Corporation");
        when(mockMerchantDetails.getDbaName()).thenReturn("Acme Corp");
        when(mockMerchantDetails.getEin()).thenReturn("12-3456789");
        when(mockMerchantDetails.getAddress()).thenReturn(testAddress);
        when(mockMerchantDetails.getIndustry()).thenReturn("Technology");
        when(mockMerchantDetails.getRevenue()).thenReturn(new BigDecimal("1000000.00"));
    }

    @Nested
    @DisplayName("PII Data Masking Tests")
    class PiiDataMaskingTests {

        @Test
        @DisplayName("Legal name should be properly masked")
        void legalNameShouldBeProperlyMasked() {
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            String maskedName = dto.getLegalName();
            assertNotNull(maskedName, "Masked legal name should not be null");
            assertEquals("A****************n", maskedName, "Legal name should be masked with first and last characters visible");
        }

        @Test
        @DisplayName("DBA name should be properly masked")
        void dbaNameShouldBeProperlyMasked() {
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            String maskedName = dto.getDbaName();
            assertNotNull(maskedName, "Masked DBA name should not be null");
            assertEquals("A*******p", maskedName, "DBA name should be masked with first and last characters visible");
        }

        @Test
        @DisplayName("EIN should be properly masked")
        void einShouldBeProperlyMasked() {
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            String maskedEin = dto.getEin();
            assertNotNull(maskedEin, "Masked EIN should not be null");
            assertEquals("**-***6789", maskedEin, "EIN should be masked with only last 4 digits visible");
        }

        @Test
        @DisplayName("EIN without hyphen should be properly masked")
        void einWithoutHyphenShouldBeProperlyMasked() {
            // Given
            when(mockMerchantDetails.getEin()).thenReturn("123456789");
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            String maskedEin = dto.getEin();
            assertNotNull(maskedEin, "Masked EIN should not be null");
            assertEquals("*****6789", maskedEin, "EIN without hyphen should be masked with only last 4 digits visible");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @DisplayName("Null or empty legal name should remain unchanged")
        void nullOrEmptyLegalNameShouldRemainUnchanged(String legalName) {
            // Given
            when(mockMerchantDetails.getLegalName()).thenReturn(legalName);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertEquals(legalName, dto.getLegalName(), "Null or empty legal name should remain unchanged");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @DisplayName("Null or empty DBA name should remain unchanged")
        void nullOrEmptyDbaNameShouldRemainUnchanged(String dbaName) {
            // Given
            when(mockMerchantDetails.getDbaName()).thenReturn(dbaName);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertEquals(dbaName, dto.getDbaName(), "Null or empty DBA name should remain unchanged");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @DisplayName("Null or empty EIN should remain unchanged")
        void nullOrEmptyEinShouldRemainUnchanged(String ein) {
            // Given
            when(mockMerchantDetails.getEin()).thenReturn(ein);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertEquals(ein, dto.getEin(), "Null or empty EIN should remain unchanged");
        }

        @ParameterizedTest
        @ValueSource(strings = {"A", "AB"})
        @DisplayName("Short legal name (2 chars or less) should remain unchanged")
        void shortLegalNameShouldRemainUnchanged(String legalName) {
            // Given
            when(mockMerchantDetails.getLegalName()).thenReturn(legalName);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertEquals(legalName, dto.getLegalName(), "Short legal name should remain unchanged");
        }

        @ParameterizedTest
        @ValueSource(strings = {"A", "AB"})
        @DisplayName("Short DBA name (2 chars or less) should remain unchanged")
        void shortDbaNameShouldRemainUnchanged(String dbaName) {
            // Given
            when(mockMerchantDetails.getDbaName()).thenReturn(dbaName);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertEquals(dbaName, dto.getDbaName(), "Short DBA name should remain unchanged");
        }

        @ParameterizedTest
        @ValueSource(strings = {"123", "12-3", "1-23"})
        @DisplayName("Short or invalid format EIN should remain unchanged")
        void shortOrInvalidFormatEinShouldRemainUnchanged(String ein) {
            // Given
            when(mockMerchantDetails.getEin()).thenReturn(ein);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertEquals(ein, dto.getEin(), "Short or invalid format EIN should remain unchanged");
        }
    }

    @Nested
    @DisplayName("JSON Serialization/Deserialization Tests")
    class JsonTests {

        @Test
        @DisplayName("DTO should serialize to JSON correctly")
        void dtoShouldSerializeToJsonCorrectly() throws Exception {
            // Given
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertNotNull(json, "JSON should not be null");
            assertTrue(json.contains("\"id\":1"), "JSON should contain id field");
            assertTrue(json.contains("\"application_id\":100"), "JSON should contain application_id field");
            assertTrue(json.contains("\"legal_name\":\"A****************n\""), "JSON should contain masked legal_name field");
            assertTrue(json.contains("\"dba_name\":\"A*******p\""), "JSON should contain masked dba_name field");
            assertTrue(json.contains("\"ein\":\"**-***6789\""), "JSON should contain masked ein field");
            assertTrue(json.contains("\"industry\":\"Technology\""), "JSON should contain industry field");
            assertTrue(json.contains("\"revenue\":\"1000000.00\""), "JSON should contain revenue field as string");
            assertTrue(json.contains("\"address\":"), "JSON should contain address field");
            assertTrue(json.contains("\"street\":\"123 Main St\""), "JSON should contain street in address");
            assertTrue(json.contains("\"city\":\"New York\""), "JSON should contain city in address");
            assertTrue(json.contains("\"state\":\"NY\""), "JSON should contain state in address");
            assertTrue(json.contains("\"zip\":\"10001\""), "JSON should contain zip in address");
            assertTrue(json.contains("\"country\":\"USA\""), "JSON should contain country in address");
        }

        @Test
        @DisplayName("JSON should deserialize to DTO correctly")
        void jsonShouldDeserializeToDtoCorrectly() throws Exception {
            // Given
            String json = "{\"id\":2,\"application_id\":200,\"legal_name\":\"X**Y\",\"dba_name\":\"X*Z\",\"ein\":\"**-***4321\",\"address\":{\"street\":\"456 Park Ave\",\"city\":\"Chicago\",\"state\":\"IL\",\"zip\":\"60601\",\"country\":\"USA\"},\"industry\":\"Finance\",\"revenue\":\"500000.00\"}";
            
            // When
            MerchantDetailsResponseDTO dto = objectMapper.readValue(json, MerchantDetailsResponseDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(2L, dto.getId(), "ID should match");
            assertEquals(200L, dto.getApplicationId(), "Application ID should match");
            assertEquals("X**Y", dto.getLegalName(), "Legal name should match");
            assertEquals("X*Z", dto.getDbaName(), "DBA name should match");
            assertEquals("**-***4321", dto.getEin(), "EIN should match");
            assertEquals("Finance", dto.getIndustry(), "Industry should match");
            assertEquals(new BigDecimal("500000.00"), dto.getRevenue(), "Revenue should match");
            
            assertNotNull(dto.getAddress(), "Address should not be null");
            assertEquals("456 Park Ave", dto.getAddress().get("street"), "Street should match");
            assertEquals("Chicago", dto.getAddress().get("city"), "City should match");
            assertEquals("IL", dto.getAddress().get("state"), "State should match");
            assertEquals("60601", dto.getAddress().get("zip"), "ZIP should match");
            assertEquals("USA", dto.getAddress().get("country"), "Country should match");
        }

        @Test
        @DisplayName("JSON with missing optional fields should deserialize correctly")
        void jsonWithMissingOptionalFieldsShouldDeserializeCorrectly() throws Exception {
            // Given
            String json = "{\"id\":3,\"application_id\":300,\"legal_name\":\"Z****A\",\"ein\":\"**-***5678\",\"address\":{\"street\":\"789 Broadway\",\"city\":\"San Francisco\",\"state\":\"CA\",\"zip\":\"94105\"},\"industry\":\"Retail\",\"revenue\":\"750000.00\"}";
            
            // When
            MerchantDetailsResponseDTO dto = objectMapper.readValue(json, MerchantDetailsResponseDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(3L, dto.getId(), "ID should match");
            assertEquals(300L, dto.getApplicationId(), "Application ID should match");
            assertEquals("Z****A", dto.getLegalName(), "Legal name should match");
            assertNull(dto.getDbaName(), "DBA name should be null");
            assertEquals("**-***5678", dto.getEin(), "EIN should match");
            assertEquals("Retail", dto.getIndustry(), "Industry should match");
            assertEquals(new BigDecimal("750000.00"), dto.getRevenue(), "Revenue should match");
            
            assertNotNull(dto.getAddress(), "Address should not be null");
            assertEquals("789 Broadway", dto.getAddress().get("street"), "Street should match");
            assertEquals("San Francisco", dto.getAddress().get("city"), "City should match");
            assertEquals("CA", dto.getAddress().get("state"), "State should match");
            assertEquals("94105", dto.getAddress().get("zip"), "ZIP should match");
            assertNull(dto.getAddress().get("country"), "Country should be null");
        }

        @Test
        @DisplayName("DTO should ignore unknown JSON properties")
        void dtoShouldIgnoreUnknownJsonProperties() throws Exception {
            // Given
            String json = "{\"id\":4,\"application_id\":400,\"legal_name\":\"W****E\",\"dba_name\":\"W*E\",\"ein\":\"**-***9012\",\"address\":{\"street\":\"321 Oak St\",\"city\":\"Boston\",\"state\":\"MA\",\"zip\":\"02108\",\"country\":\"USA\",\"unknown_field\":\"value\"},\"industry\":\"Healthcare\",\"revenue\":\"1250000.00\",\"unknown_field\":\"value\"}";
            
            // When
            MerchantDetailsResponseDTO dto = objectMapper.readValue(json, MerchantDetailsResponseDTO.class);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(4L, dto.getId(), "ID should match");
            assertEquals(400L, dto.getApplicationId(), "Application ID should match");
            assertEquals("W****E", dto.getLegalName(), "Legal name should match");
            assertEquals("W*E", dto.getDbaName(), "DBA name should match");
            assertEquals("**-***9012", dto.getEin(), "EIN should match");
            assertEquals("Healthcare", dto.getIndustry(), "Industry should match");
            assertEquals(new BigDecimal("1250000.00"), dto.getRevenue(), "Revenue should match");
            
            assertNotNull(dto.getAddress(), "Address should not be null");
            assertEquals("321 Oak St", dto.getAddress().get("street"), "Street should match");
            assertEquals("Boston", dto.getAddress().get("city"), "City should match");
            assertEquals("MA", dto.getAddress().get("state"), "State should match");
            assertEquals("02108", dto.getAddress().get("zip"), "ZIP should match");
            assertEquals("USA", dto.getAddress().get("country"), "Country should match");
            // Unknown fields should be ignored without exception
        }
    }

    @Nested
    @DisplayName("Entity Conversion Tests")
    class EntityConversionTests {

        @Test
        @DisplayName("Entity should convert to DTO correctly")
        void entityShouldConvertToDtoCorrectly() {
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(mockMerchantDetails.getId(), dto.getId(), "ID should match");
            assertEquals(mockMerchantDetails.getApplicationId(), dto.getApplicationId(), "Application ID should match");
            assertEquals("A****************n", dto.getLegalName(), "Legal name should be masked");
            assertEquals("A*******p", dto.getDbaName(), "DBA name should be masked");
            assertEquals("**-***6789", dto.getEin(), "EIN should be masked");
            assertEquals(mockMerchantDetails.getIndustry(), dto.getIndustry(), "Industry should match");
            assertEquals(mockMerchantDetails.getRevenue(), dto.getRevenue(), "Revenue should match");
            assertEquals(mockMerchantDetails.getAddress(), dto.getAddress(), "Address should match");
        }

        @Test
        @DisplayName("Static factory method should convert entity to DTO correctly")
        void staticFactoryMethodShouldConvertEntityToDtoCorrectly() {
            // When
            MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntity(mockMerchantDetails);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(mockMerchantDetails.getId(), dto.getId(), "ID should match");
            assertEquals(mockMerchantDetails.getApplicationId(), dto.getApplicationId(), "Application ID should match");
            assertEquals("A****************n", dto.getLegalName(), "Legal name should be masked");
            assertEquals("A*******p", dto.getDbaName(), "DBA name should be masked");
            assertEquals("**-***6789", dto.getEin(), "EIN should be masked");
            assertEquals(mockMerchantDetails.getIndustry(), dto.getIndustry(), "Industry should match");
            assertEquals(mockMerchantDetails.getRevenue(), dto.getRevenue(), "Revenue should match");
            assertEquals(mockMerchantDetails.getAddress(), dto.getAddress(), "Address should match");
        }

        @Test
        @DisplayName("Null entity should convert to null DTO")
        void nullEntityShouldConvertToNullDto() {
            // When
            MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntity(null);
            
            // Then
            assertNull(dto, "DTO should be null when entity is null");
        }

        @Test
        @DisplayName("Entity with null fields should convert to DTO with null fields")
        void entityWithNullFieldsShouldConvertToDtoWithNullFields() {
            // Given
            when(mockMerchantDetails.getDbaName()).thenReturn(null);
            when(mockMerchantDetails.getAddress()).thenReturn(null);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertNotNull(dto, "DTO should not be null");
            assertEquals(mockMerchantDetails.getId(), dto.getId(), "ID should match");
            assertEquals(mockMerchantDetails.getApplicationId(), dto.getApplicationId(), "Application ID should match");
            assertEquals("A****************n", dto.getLegalName(), "Legal name should be masked");
            assertNull(dto.getDbaName(), "DBA name should be null");
            assertEquals("**-***6789", dto.getEin(), "EIN should be masked");
            assertEquals(mockMerchantDetails.getIndustry(), dto.getIndustry(), "Industry should match");
            assertEquals(mockMerchantDetails.getRevenue(), dto.getRevenue(), "Revenue should match");
            assertNull(dto.getAddress(), "Address should be null");
        }
    }

    @Nested
    @DisplayName("Address and Financial Information Tests")
    class AddressAndFinancialInformationTests {

        @Test
        @DisplayName("Address map structure should be preserved")
        void addressMapStructureShouldBePreserved() {
            // Given
            Map<String, String> complexAddress = new HashMap<>();
            complexAddress.put("street", "123 Main St");
            complexAddress.put("street2", "Suite 100");
            complexAddress.put("city", "New York");
            complexAddress.put("state", "NY");
            complexAddress.put("zip", "10001");
            complexAddress.put("country", "USA");
            complexAddress.put("type", "business");
            when(mockMerchantDetails.getAddress()).thenReturn(complexAddress);
            
            // When
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // Then
            assertNotNull(dto.getAddress(), "Address should not be null");
            assertEquals(7, dto.getAddress().size(), "Address should have all keys");
            assertEquals("123 Main St", dto.getAddress().get("street"), "Street should match");
            assertEquals("Suite 100", dto.getAddress().get("street2"), "Street2 should match");
            assertEquals("New York", dto.getAddress().get("city"), "City should match");
            assertEquals("NY", dto.getAddress().get("state"), "State should match");
            assertEquals("10001", dto.getAddress().get("zip"), "ZIP should match");
            assertEquals("USA", dto.getAddress().get("country"), "Country should match");
            assertEquals("business", dto.getAddress().get("type"), "Type should match");
        }

        @Test
        @DisplayName("Revenue should be formatted as string in JSON")
        void revenueShouldBeFormattedAsStringInJson() throws Exception {
            // Given
            when(mockMerchantDetails.getRevenue()).thenReturn(new BigDecimal("1234567.89"));
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertTrue(json.contains("\"revenue\":\"1234567.89\""), "Revenue should be formatted as string in JSON");
        }

        @Test
        @DisplayName("Revenue with zero decimal places should be formatted correctly")
        void revenueWithZeroDecimalPlacesShouldBeFormattedCorrectly() throws Exception {
            // Given
            when(mockMerchantDetails.getRevenue()).thenReturn(new BigDecimal("1000000"));
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertTrue(json.contains("\"revenue\":\"1000000\""), "Revenue with zero decimal places should be formatted correctly");
        }

        @Test
        @DisplayName("Revenue with many decimal places should be preserved")
        void revenueWithManyDecimalPlacesShouldBePreserved() throws Exception {
            // Given
            when(mockMerchantDetails.getRevenue()).thenReturn(new BigDecimal("1234.56789"));
            MerchantDetailsResponseDTO dto = new MerchantDetailsResponseDTO(mockMerchantDetails);
            
            // When
            String json = objectMapper.writeValueAsString(dto);
            
            // Then
            assertTrue(json.contains("\"revenue\":\"1234.56789\""), "Revenue with many decimal places should be preserved");
        }
    }
}