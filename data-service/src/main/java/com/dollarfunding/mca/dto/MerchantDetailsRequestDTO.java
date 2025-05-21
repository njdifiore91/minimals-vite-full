package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.MerchantDetails;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.Valid;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;
import java.math.BigDecimal;

/**
 * Data Transfer Object for creating or updating merchant details.
 * This class defines the structure for incoming merchant data with validation annotations
 * for required fields. It includes fields for merchant information with appropriate
 * JSON serialization annotations.
 * <p>
 * Sensitive PII data fields are marked for field-level encryption in the service layer.
 * </p>
 *
 * @author MCA Application Team
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class MerchantDetailsRequestDTO {

    /**
     * Legal name of the merchant (PII data).
     * This field is subject to field-level encryption.
     */
    @NotBlank(message = "Legal name is required")
    @Size(max = 100, message = "Legal name cannot exceed 100 characters")
    @JsonProperty("legal_name")
    private String legalName;

    /**
     * Doing Business As name of the merchant (PII data).
     * This field is subject to field-level encryption.
     */
    @Size(max = 100, message = "DBA name cannot exceed 100 characters")
    @JsonProperty("dba_name")
    private String dbaName;

    /**
     * Employer Identification Number (EIN) of the merchant (PII data).
     * Format: XX-XXXXXXX (9 digits with hyphen)
     * This field is subject to field-level encryption.
     */
    @NotBlank(message = "EIN is required")
    @Pattern(regexp = "^\\d{2}-\\d{7}$", message = "EIN must be in format XX-XXXXXXX")
    @JsonProperty("ein")
    private String ein;

    /**
     * Address of the merchant (PII data).
     * This is a complex structure containing address details.
     */
    @NotNull(message = "Address is required")
    @Valid
    @JsonProperty("address")
    private AddressDTO address;

    /**
     * Industry of the merchant.
     */
    @NotBlank(message = "Industry is required")
    @Size(max = 50, message = "Industry cannot exceed 50 characters")
    @JsonProperty("industry")
    private String industry;

    /**
     * Annual revenue of the merchant.
     */
    @NotNull(message = "Revenue is required")
    @JsonProperty("revenue")
    private BigDecimal revenue;

    /**
     * Converts this DTO to a MerchantDetails entity.
     * Note: This method does not set the id or application_id fields,
     * which should be handled by the service layer.
     *
     * @return A new MerchantDetails entity with data from this DTO
     */
    public MerchantDetails toEntity() {
        MerchantDetails entity = new MerchantDetails();
        entity.setLegalName(this.legalName);
        entity.setDbaName(this.dbaName);
        entity.setEin(this.ein);
        entity.setAddress(this.address != null ? this.address.toAddressObject() : null);
        entity.setIndustry(this.industry);
        entity.setRevenue(this.revenue);
        return entity;
    }

    /**
     * Creates a new DTO from a MerchantDetails entity.
     *
     * @param entity The MerchantDetails entity
     * @return A new MerchantDetailsRequestDTO with data from the entity
     */
    public static MerchantDetailsRequestDTO fromEntity(MerchantDetails entity) {
        if (entity == null) {
            return null;
        }

        return MerchantDetailsRequestDTO.builder()
                .legalName(entity.getLegalName())
                .dbaName(entity.getDbaName())
                .ein(entity.getEin())
                .address(AddressDTO.fromAddressObject(entity.getAddress()))
                .industry(entity.getIndustry())
                .revenue(entity.getRevenue())
                .build();
    }

    /**
     * Inner class representing the address structure.
     * Contains validation annotations for address fields.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class AddressDTO {

        /**
         * Street address line 1 (PII data).
         * This field is subject to field-level encryption.
         */
        @NotBlank(message = "Street address is required")
        @Size(max = 100, message = "Street address cannot exceed 100 characters")
        @JsonProperty("street_address")
        private String streetAddress;

        /**
         * Street address line 2 (PII data).
         * This field is subject to field-level encryption.
         */
        @Size(max = 100, message = "Street address line 2 cannot exceed 100 characters")
        @JsonProperty("street_address_2")
        private String streetAddress2;

        /**
         * City (PII data).
         * This field is subject to field-level encryption.
         */
        @NotBlank(message = "City is required")
        @Size(max = 50, message = "City cannot exceed 50 characters")
        @JsonProperty("city")
        private String city;

        /**
         * State (PII data).
         * This field is subject to field-level encryption.
         */
        @NotBlank(message = "State is required")
        @Size(min = 2, max = 2, message = "State must be a 2-letter code")
        @JsonProperty("state")
        private String state;

        /**
         * ZIP code (PII data).
         * This field is subject to field-level encryption.
         */
        @NotBlank(message = "ZIP code is required")
        @Pattern(regexp = "^\\d{5}(-\\d{4})?$", message = "ZIP code must be in format XXXXX or XXXXX-XXXX")
        @JsonProperty("zip_code")
        private String zipCode;

        /**
         * Converts this DTO to an Address object.
         * The actual implementation depends on the Address class structure.
         *
         * @return An Address object with data from this DTO
         */
        public Object toAddressObject() {
            // Implementation depends on the actual Address class structure
            // This is a placeholder for the actual conversion logic
            return this;
        }

        /**
         * Creates a new AddressDTO from an Address object.
         *
         * @param address The Address object
         * @return A new AddressDTO with data from the Address object
         */
        public static AddressDTO fromAddressObject(Object address) {
            // Implementation depends on the actual Address class structure
            // This is a placeholder for the actual conversion logic
            if (address == null) {
                return null;
            }
            if (address instanceof AddressDTO) {
                return (AddressDTO) address;
            }
            // Default implementation would extract fields from the Address object
            return new AddressDTO();
        }
    }
}