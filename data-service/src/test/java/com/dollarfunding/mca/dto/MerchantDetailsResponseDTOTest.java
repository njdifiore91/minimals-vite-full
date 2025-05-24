package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.util.EncryptionUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

/**
 * Test class for {@link MerchantDetailsResponseDTO}.
 * 
 * This class tests the functionality of the MerchantDetailsResponseDTO, including:
 * - Basic DTO functionality (getters, setters, constructors)
 * - JSON serialization/deserialization
 * - Conversion from entity objects
 * - PII data masking
 * - Address and financial information formatting
 */
public class MerchantDetailsResponseDTOTest {

    private ObjectMapper objectMapper;
    private MerchantDetails merchantDetails;
    private Application application;
    private LocalDateTime testDateTime;
    
    @Mock
    private EncryptionUtil encryptionUtil;

    @BeforeEach
    void setUp() {
        // Initialize Mockito annotations
        MockitoAnnotations.openMocks(this);
        
        // Initialize ObjectMapper for JSON serialization/deserialization tests
        objectMapper = new ObjectMapper();
        objectMapper.findAndRegisterModules(); // For LocalDateTime serialization

        // Initialize test date time
        testDateTime = LocalDateTime.of(2023, 1, 15, 10, 30, 0);

        // Create a test Application entity
        application = new Application();
        application.setId(UUID.randomUUID());

        // Create a test MerchantDetails entity with all fields populated
        merchantDetails = new MerchantDetails();
        merchantDetails.setId(UUID.randomUUID());
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Acme Corporation");
        merchantDetails.setDbaName("Acme Corp");
        merchantDetails.setEin("12-3456789");
        merchantDetails.setEncryptionUtil(encryptionUtil); // Set the mock encryption util
        
        // Set up address
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main Street");
        address.put("city", "New York");
        address.put("state", "NY");
        address.put("zip", "10001");
        address.put("country", "USA");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(new BigDecimal("1000000.00"));
        
        // Set up created_at and updated_at timestamps
        merchantDetails.setCreatedAt(testDateTime);
        merchantDetails.setUpdatedAt(testDateTime);
        
        // Set up mock behavior for encryption util
        // When decrypting, return the original value (simulating decryption)
        when(encryptionUtil.decrypt("Acme Corporation")).thenReturn("Acme Corporation");
        when(encryptionUtil.decrypt("Acme Corp")).thenReturn("Acme Corp");
        when(encryptionUtil.decrypt("12-3456789")).thenReturn("12-3456789");
    }

    @Test
    @DisplayName("Test basic DTO functionality")
    void testBasicDtoFunctionality() {
        // Create a DTO using builder pattern
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.builder()
                .id(1L)
                .applicationId(2L)
                .legalName("Test Company")
                .dbaName("Test Co")
                .ein("98-7654321")
                .address(MerchantDetailsResponseDTO.AddressDTO.builder()
                        .street("456 Elm Street")
                        .city("Chicago")
                        .state("IL")
                        .zipCode("60601")
                        .country("USA")
                        .build())
                .industry("Finance")
                .revenue(new BigDecimal("500000.00"))
                .createdAt(testDateTime)
                .updatedAt(testDateTime)
                .build();

        // Verify all fields are set correctly
        assertEquals(1L, dto.getId());
        assertEquals(2L, dto.getApplicationId());
        assertEquals("Test Company", dto.getLegalName());
        assertEquals("Test Co", dto.getDbaName());
        assertEquals("98-7654321", dto.getEin());
        assertNotNull(dto.getAddress());
        assertEquals("456 Elm Street", dto.getAddress().getStreet());
        assertEquals("Chicago", dto.getAddress().getCity());
        assertEquals("IL", dto.getAddress().getState());
        assertEquals("60601", dto.getAddress().getZipCode());
        assertEquals("USA", dto.getAddress().getCountry());
        assertEquals("Finance", dto.getIndustry());
        assertEquals(new BigDecimal("500000.00"), dto.getRevenue());
        assertEquals(testDateTime, dto.getCreatedAt());
        assertEquals(testDateTime, dto.getUpdatedAt());

        // Test no-args constructor and setters
        MerchantDetailsResponseDTO emptyDto = new MerchantDetailsResponseDTO();
        emptyDto.setId(3L);
        emptyDto.setApplicationId(4L);
        emptyDto.setLegalName("Another Company");
        
        assertEquals(3L, emptyDto.getId());
        assertEquals(4L, emptyDto.getApplicationId());
        assertEquals("Another Company", emptyDto.getLegalName());
    }

    @Test
    @DisplayName("Test JSON serialization/deserialization")
    void testJsonSerializationDeserialization() throws Exception {
        // Create a DTO with test data
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.builder()
                .id(1L)
                .applicationId(2L)
                .legalName("Test Company")
                .dbaName("Test Co")
                .ein("98-7654321")
                .address(MerchantDetailsResponseDTO.AddressDTO.builder()
                        .street("456 Elm Street")
                        .city("Chicago")
                        .state("IL")
                        .zipCode("60601")
                        .country("USA")
                        .build())
                .industry("Finance")
                .revenue(new BigDecimal("500000.00"))
                .createdAt(testDateTime)
                .updatedAt(testDateTime)
                .build();

        // Serialize to JSON
        String json = objectMapper.writeValueAsString(dto);

        // Verify JSON structure
        assertTrue(json.contains("\"id\":1"));
        assertTrue(json.contains("\"application_id\":2"));
        assertTrue(json.contains("\"legal_name\":\"Test Company\""));
        assertTrue(json.contains("\"dba_name\":\"Test Co\""));
        assertTrue(json.contains("\"ein\":\"98-7654321\""));
        assertTrue(json.contains("\"street\":\"456 Elm Street\""));
        assertTrue(json.contains("\"city\":\"Chicago\""));
        assertTrue(json.contains("\"state\":\"IL\""));
        assertTrue(json.contains("\"zip_code\":\"60601\""));
        assertTrue(json.contains("\"country\":\"USA\""));
        assertTrue(json.contains("\"industry\":\"Finance\""));
        assertTrue(json.contains("\"revenue\":\"500000.00\""));

        // Deserialize from JSON
        MerchantDetailsResponseDTO deserializedDto = objectMapper.readValue(json, MerchantDetailsResponseDTO.class);

        // Verify deserialized object
        assertEquals(dto.getId(), deserializedDto.getId());
        assertEquals(dto.getApplicationId(), deserializedDto.getApplicationId());
        assertEquals(dto.getLegalName(), deserializedDto.getLegalName());
        assertEquals(dto.getDbaName(), deserializedDto.getDbaName());
        assertEquals(dto.getEin(), deserializedDto.getEin());
        assertEquals(dto.getAddress().getStreet(), deserializedDto.getAddress().getStreet());
        assertEquals(dto.getAddress().getCity(), deserializedDto.getAddress().getCity());
        assertEquals(dto.getAddress().getState(), deserializedDto.getAddress().getState());
        assertEquals(dto.getAddress().getZipCode(), deserializedDto.getAddress().getZipCode());
        assertEquals(dto.getAddress().getCountry(), deserializedDto.getAddress().getCountry());
        assertEquals(dto.getIndustry(), deserializedDto.getIndustry());
        assertEquals(dto.getRevenue(), deserializedDto.getRevenue());
    }

    @Test
    @DisplayName("Test conversion from entity with full PII data")
    void testFromEntityWithFullPii() {
        // Convert entity to DTO with full PII data
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntityWithFullPii(merchantDetails);

        // Verify all fields are set correctly
        assertEquals(merchantDetails.getId().toString(), dto.getId().toString());
        assertEquals(application.getId().toString(), dto.getApplicationId().toString());
        assertEquals(merchantDetails.getLegalName(), dto.getLegalName());
        assertEquals(merchantDetails.getDbaName(), dto.getDbaName());
        assertEquals(merchantDetails.getEin(), dto.getEin());
        
        // Verify address fields
        assertNotNull(dto.getAddress());
        assertEquals(merchantDetails.getAddressField("street"), dto.getAddress().getStreet());
        assertEquals(merchantDetails.getAddressField("city"), dto.getAddress().getCity());
        assertEquals(merchantDetails.getAddressField("state"), dto.getAddress().getState());
        assertEquals(merchantDetails.getAddressField("zip"), dto.getAddress().getZipCode());
        assertEquals(merchantDetails.getAddressField("country"), dto.getAddress().getCountry());
        
        // Verify other fields
        assertEquals(merchantDetails.getIndustry(), dto.getIndustry());
        assertEquals(merchantDetails.getRevenue(), dto.getRevenue());
    }

    @Test
    @DisplayName("Test conversion from entity with masked PII data")
    void testFromEntityWithMaskedPii() {
        // Convert entity to DTO with masked PII data
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntityWithMaskedPii(merchantDetails);

        // Verify non-PII fields are set correctly
        assertEquals(merchantDetails.getId().toString(), dto.getId().toString());
        assertEquals(application.getId().toString(), dto.getApplicationId().toString());
        assertEquals(merchantDetails.getIndustry(), dto.getIndustry());
        assertEquals(merchantDetails.getRevenue(), dto.getRevenue());

        // Verify PII fields are masked
        assertNotEquals(merchantDetails.getLegalName(), dto.getLegalName());
        assertTrue(dto.getLegalName().startsWith("A"));
        assertTrue(dto.getLegalName().contains("*"));
        
        assertNotEquals(merchantDetails.getDbaName(), dto.getDbaName());
        assertTrue(dto.getDbaName().startsWith("A"));
        assertTrue(dto.getDbaName().contains("*"));
        
        assertNotEquals(merchantDetails.getEin(), dto.getEin());
        assertTrue(dto.getEin().startsWith("**-***"));
        assertTrue(dto.getEin().endsWith("6789"));
        
        // Verify address is masked
        assertNotNull(dto.getAddress());
        assertNotEquals(merchantDetails.getAddressField("street"), dto.getAddress().getStreet());
        assertTrue(dto.getAddress().getStreet().startsWith("123"));
        assertTrue(dto.getAddress().getStreet().contains("*"));
        
        // City, state, and ZIP should not be masked
        assertEquals(merchantDetails.getAddressField("city"), dto.getAddress().getCity());
        assertEquals(merchantDetails.getAddressField("state"), dto.getAddress().getState());
        assertEquals(merchantDetails.getAddressField("zip"), dto.getAddress().getZipCode());
        assertEquals(merchantDetails.getAddressField("country"), dto.getAddress().getCountry());
    }

    @Test
    @DisplayName("Test name masking functionality")
    void testNameMasking() {
        // Create a DTO with masked PII data
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntityWithMaskedPii(merchantDetails);

        // Verify legal name masking ("Acme Corporation" -> "A*** C***********")
        String maskedLegalName = dto.getLegalName();
        assertEquals('A', maskedLegalName.charAt(0));
        for (int i = 1; i < maskedLegalName.indexOf(' '); i++) {
            assertEquals('*', maskedLegalName.charAt(i));
        }
        assertEquals('C', maskedLegalName.charAt(maskedLegalName.indexOf(' ') + 1));
        for (int i = maskedLegalName.indexOf(' ') + 2; i < maskedLegalName.length(); i++) {
            assertEquals('*', maskedLegalName.charAt(i));
        }

        // Verify DBA name masking ("Acme Corp" -> "A*** C***")
        String maskedDbaName = dto.getDbaName();
        assertEquals('A', maskedDbaName.charAt(0));
        for (int i = 1; i < maskedDbaName.indexOf(' '); i++) {
            assertEquals('*', maskedDbaName.charAt(i));
        }
        assertEquals('C', maskedDbaName.charAt(maskedDbaName.indexOf(' ') + 1));
        for (int i = maskedDbaName.indexOf(' ') + 2; i < maskedDbaName.length(); i++) {
            assertEquals('*', maskedDbaName.charAt(i));
        }
    }

    @Test
    @DisplayName("Test EIN masking functionality")
    void testEinMasking() {
        // Create a DTO with masked PII data
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntityWithMaskedPii(merchantDetails);

        // Verify EIN masking ("12-3456789" -> "**-***6789")
        String maskedEin = dto.getEin();
        assertEquals("**-***6789", maskedEin);
    }

    @Test
    @DisplayName("Test address masking functionality")
    void testAddressMasking() {
        // Create a DTO with masked PII data
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntityWithMaskedPii(merchantDetails);

        // Verify street address masking ("123 Main Street" -> "123 **** ******")
        String maskedStreet = dto.getAddress().getStreet();
        assertTrue(maskedStreet.startsWith("123 "));
        for (int i = 4; i < maskedStreet.length(); i++) {
            if (maskedStreet.charAt(i) != ' ') {
                assertEquals('*', maskedStreet.charAt(i));
            }
        }

        // Verify that city, state, ZIP, and country are not masked
        assertEquals("New York", dto.getAddress().getCity());
        assertEquals("NY", dto.getAddress().getState());
        assertEquals("10001", dto.getAddress().getZipCode());
        assertEquals("USA", dto.getAddress().getCountry());
    }

    @Test
    @DisplayName("Test AddressDTO functionality")
    void testAddressDtoFunctionality() {
        // Create an AddressDTO using builder pattern
        MerchantDetailsResponseDTO.AddressDTO addressDto = MerchantDetailsResponseDTO.AddressDTO.builder()
                .street("789 Oak Avenue")
                .city("Los Angeles")
                .state("CA")
                .zipCode("90001")
                .country("USA")
                .build();

        // Verify all fields are set correctly
        assertEquals("789 Oak Avenue", addressDto.getStreet());
        assertEquals("Los Angeles", addressDto.getCity());
        assertEquals("CA", addressDto.getState());
        assertEquals("90001", addressDto.getZipCode());
        assertEquals("USA", addressDto.getCountry());

        // Test fromAddressObject method with a Map
        Map<String, Object> addressMap = new HashMap<>();
        addressMap.put("street", "321 Pine Road");
        addressMap.put("city", "Miami");
        addressMap.put("state", "FL");
        addressMap.put("zip", "33101");
        addressMap.put("country", "USA");
        merchantDetails.setAddress(addressMap);

        // Create a mock Address object using the Map
        // Note: In the actual implementation, the Address object is created from the Map
        // in the MerchantDetailsResponseDTO.AddressDTO.fromAddressObject method
        MerchantDetailsResponseDTO.AddressDTO convertedAddressDto = 
                MerchantDetailsResponseDTO.AddressDTO.fromAddressObject(merchantDetails.getAddress());

        // Verify converted address
        assertEquals("321 Pine Road", convertedAddressDto.getStreet());
        assertEquals("Miami", convertedAddressDto.getCity());
        assertEquals("FL", convertedAddressDto.getState());
        assertEquals("33101", convertedAddressDto.getZipCode());
        assertEquals("USA", convertedAddressDto.getCountry());
    }

    @Test
    @DisplayName("Test handling of null entity")
    void testHandlingOfNullEntity() {
        // Test fromEntity with null
        assertNull(MerchantDetailsResponseDTO.fromEntity(null, false));
        assertNull(MerchantDetailsResponseDTO.fromEntityWithFullPii(null));
        assertNull(MerchantDetailsResponseDTO.fromEntityWithMaskedPii(null));
    }

    @Test
    @DisplayName("Test handling of null fields in entity")
    void testHandlingOfNullFieldsInEntity() {
        // Create entity with null fields
        MerchantDetails entityWithNulls = new MerchantDetails();
        entityWithNulls.setId(UUID.randomUUID());
        entityWithNulls.setLegalName("Test Company");
        // Leave other fields null

        // Convert to DTO
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.fromEntityWithFullPii(entityWithNulls);

        // Verify non-null fields
        assertEquals(entityWithNulls.getId().toString(), dto.getId().toString());
        assertEquals("Test Company", dto.getLegalName());

        // Verify null fields
        assertNull(dto.getApplicationId());
        assertNull(dto.getDbaName());
        assertNull(dto.getEin());
        assertNull(dto.getAddress());
        assertNull(dto.getIndustry());
        assertNull(dto.getRevenue());
    }

    @Test
    @DisplayName("Test handling of empty address in entity")
    void testHandlingOfEmptyAddressInEntity() {
        // Create entity with empty address
        MerchantDetails entityWithEmptyAddress = new MerchantDetails();
        entityWithEmptyAddress.setId(UUID.randomUUID());
        entityWithEmptyAddress.setLegalName("Test Company");
        entityWithEmptyAddress.setAddress(new HashMap<>()); // Empty address

        // Convert to DTO with full PII
        MerchantDetailsResponseDTO dtoWithFullPii = MerchantDetailsResponseDTO.fromEntityWithFullPii(entityWithEmptyAddress);

        // Verify address is null (since the map is empty)
        assertNull(dtoWithFullPii.getAddress());

        // Convert to DTO with masked PII
        MerchantDetailsResponseDTO dtoWithMaskedPii = MerchantDetailsResponseDTO.fromEntityWithMaskedPii(entityWithEmptyAddress);

        // Verify address is null (since the map is empty)
        assertNull(dtoWithMaskedPii.getAddress());
    }

    @Test
    @DisplayName("Test revenue formatting")
    void testRevenueFormatting() throws Exception {
        // Create a DTO with revenue
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.builder()
                .id(1L)
                .legalName("Test Company")
                .revenue(new BigDecimal("1234567.89"))
                .build();

        // Serialize to JSON
        String json = objectMapper.writeValueAsString(dto);

        // Verify revenue is formatted as a string with two decimal places
        assertTrue(json.contains("\"revenue\":\"1234567.89\""));
    }
}