package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.MerchantDetails;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * Data Transfer Object for returning merchant details to clients.
 * This class provides a complete view of merchant information while handling
 * sensitive PII data appropriately. It includes all merchant fields with
 * proper serialization for API responses.
 * <p>
 * Sensitive PII data fields are masked in the response to protect privacy.
 * </p>
 *
 * @author MCA Application Team
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class MerchantDetailsResponseDTO {

    /**
     * Unique identifier for the merchant details record.
     */
    @JsonProperty("id")
    private Long id;

    /**
     * Associated application ID.
     */
    @JsonProperty("application_id")
    private Long applicationId;

    /**
     * Legal name of the merchant (PII data).
     * This field contains the full legal name for authorized users,
     * or a masked version for users without full access permissions.
     */
    @JsonProperty("legal_name")
    private String legalName;

    /**
     * Doing Business As name of the merchant (PII data).
     * This field contains the full DBA name for authorized users,
     * or a masked version for users without full access permissions.
     */
    @JsonProperty("dba_name")
    private String dbaName;

    /**
     * Employer Identification Number (EIN) of the merchant (PII data).
     * This field contains the full EIN for authorized users,
     * or a masked version for users without full access permissions.
     */
    @JsonProperty("ein")
    private String ein;

    /**
     * Address of the merchant (PII data).
     * This is a complex structure containing address details.
     */
    @JsonProperty("address")
    private AddressDTO address;

    /**
     * Industry of the merchant.
     */
    @JsonProperty("industry")
    private String industry;

    /**
     * Annual revenue of the merchant.
     * Formatted as a currency value with two decimal places.
     */
    @JsonProperty("revenue")
    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private BigDecimal revenue;

    /**
     * Timestamp when the merchant details record was created.
     */
    @JsonProperty("created_at")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime createdAt;

    /**
     * Timestamp when the merchant details record was last updated.
     */
    @JsonProperty("updated_at")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime updatedAt;

    /**
     * Creates a new DTO from a MerchantDetails entity.
     * This method handles the conversion of all fields, including proper
     * formatting of address and financial information.
     *
     * @param entity The MerchantDetails entity
     * @param maskPii Flag indicating whether to mask PII data
     * @return A new MerchantDetailsResponseDTO with data from the entity
     */
    public static MerchantDetailsResponseDTO fromEntity(MerchantDetails entity, boolean maskPii) {
        if (entity == null) {
            return null;
        }

        // Build the response DTO with all fields from the entity
        MerchantDetailsResponseDTO dto = MerchantDetailsResponseDTO.builder()
                .id(entity.getId())
                .applicationId(entity.getApplication() != null ? entity.getApplication().getId() : null)
                .industry(entity.getIndustry())
                .revenue(entity.getRevenue())
                .createdAt(entity.getCreatedAt())
                .updatedAt(entity.getUpdatedAt())
                .build();

        // Handle PII data based on masking flag
        if (maskPii) {
            // Mask sensitive PII data for users without full access permissions
            dto.setLegalName(maskName(entity.getLegalName()));
            dto.setDbaName(entity.getDbaName() != null ? maskName(entity.getDbaName()) : null);
            dto.setEin(maskEin(entity.getEin()));
            dto.setAddress(maskAddress(entity.getAddress()));
        } else {
            // Include full PII data for authorized users
            dto.setLegalName(entity.getLegalName());
            dto.setDbaName(entity.getDbaName());
            dto.setEin(entity.getEin());
            dto.setAddress(AddressDTO.fromAddressObject(entity.getAddress()));
        }

        return dto;
    }

    /**
     * Creates a new DTO from a MerchantDetails entity with PII data masked.
     * This is a convenience method that calls fromEntity(entity, true).
     *
     * @param entity The MerchantDetails entity
     * @return A new MerchantDetailsResponseDTO with masked PII data
     */
    public static MerchantDetailsResponseDTO fromEntityWithMaskedPii(MerchantDetails entity) {
        return fromEntity(entity, true);
    }

    /**
     * Creates a new DTO from a MerchantDetails entity with full PII data.
     * This is a convenience method that calls fromEntity(entity, false).
     *
     * @param entity The MerchantDetails entity
     * @return A new MerchantDetailsResponseDTO with full PII data
     */
    public static MerchantDetailsResponseDTO fromEntityWithFullPii(MerchantDetails entity) {
        return fromEntity(entity, false);
    }

    /**
     * Masks a name by showing only the first character followed by asterisks.
     * For example, "Acme Corporation" becomes "A*** C***********".
     *
     * @param name The name to mask
     * @return The masked name
     */
    private static String maskName(String name) {
        if (name == null || name.isEmpty()) {
            return name;
        }

        String[] parts = name.split("\\s+");
        StringBuilder masked = new StringBuilder();

        for (int i = 0; i < parts.length; i++) {
            String part = parts[i];
            if (part.length() > 0) {
                masked.append(part.charAt(0));
                for (int j = 1; j < part.length(); j++) {
                    masked.append("*");
                }
            }
            if (i < parts.length - 1) {
                masked.append(" ");
            }
        }

        return masked.toString();
    }

    /**
     * Masks an EIN by showing only the last 4 digits.
     * For example, "12-3456789" becomes "**-****6789".
     *
     * @param ein The EIN to mask
     * @return The masked EIN
     */
    private static String maskEin(String ein) {
        if (ein == null || ein.isEmpty()) {
            return ein;
        }

        // EIN format is XX-XXXXXXX (9 digits with hyphen)
        if (ein.length() < 5) {
            return "**-*******";
        }

        return "**-***" + ein.substring(ein.length() - 4);
    }

    /**
     * Masks an address by partially obscuring street information while
     * preserving city, state, and ZIP code.
     *
     * @param address The address to mask
     * @return The masked address as an AddressDTO
     */
    private static AddressDTO maskAddress(MerchantDetails.Address address) {
        if (address == null) {
            return null;
        }

        // Create a masked version of the address
        return AddressDTO.builder()
                .street(maskStreetAddress(address.getStreet()))
                .city(address.getCity())
                .state(address.getState())
                .zipCode(address.getZip())
                .country(address.getCountry())
                .build();
    }

    /**
     * Masks a street address by showing only the house/building number
     * and replacing the street name with asterisks.
     * For example, "123 Main Street" becomes "123 **** ******".
     *
     * @param street The street address to mask
     * @return The masked street address
     */
    private static String maskStreetAddress(String street) {
        if (street == null || street.isEmpty()) {
            return street;
        }

        // Extract the house/building number (assuming it's at the beginning)
        String[] parts = street.split("\\s+", 2);
        if (parts.length < 2) {
            return street;
        }

        // Keep the house/building number and mask the rest
        StringBuilder masked = new StringBuilder(parts[0]);
        masked.append(" ");

        // Mask each word in the street name
        String[] streetParts = parts[1].split("\\s+");
        for (int i = 0; i < streetParts.length; i++) {
            for (int j = 0; j < streetParts[i].length(); j++) {
                masked.append("*");
            }
            if (i < streetParts.length - 1) {
                masked.append(" ");
            }
        }

        return masked.toString();
    }

    /**
     * Inner class representing the address structure for API responses.
     * Contains fields for street, city, state, ZIP code, and country.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class AddressDTO {

        /**
         * Street address (PII data).
         */
        @JsonProperty("street")
        private String street;

        /**
         * City (PII data).
         */
        @JsonProperty("city")
        private String city;

        /**
         * State (2-letter code).
         */
        @JsonProperty("state")
        private String state;

        /**
         * ZIP code.
         */
        @JsonProperty("zip_code")
        private String zipCode;

        /**
         * Country.
         */
        @JsonProperty("country")
        private String country;

        /**
         * Creates a new AddressDTO from an Address object.
         *
         * @param address The Address object
         * @return A new AddressDTO with data from the Address object
         */
        public static AddressDTO fromAddressObject(MerchantDetails.Address address) {
            if (address == null) {
                return null;
            }

            return AddressDTO.builder()
                    .street(address.getStreet())
                    .city(address.getCity())
                    .state(address.getState())
                    .zipCode(address.getZip())
                    .country(address.getCountry())
                    .build();
        }
    }
}