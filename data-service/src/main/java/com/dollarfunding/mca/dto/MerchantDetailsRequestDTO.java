package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * Data Transfer Object for creating or updating merchant details.
 * This class defines the structure for incoming merchant data with
 * validation annotations for required fields. It serves as the contract
 * for merchant operations in the REST API.
 * <p>
 * Fields include merchant information (legal_name, dba_name, ein, address,
 * industry, revenue) with appropriate JSON serialization annotations.
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
     * This field is required and will be encrypted at rest.
     */
    @NotBlank(message = "Legal name is required")
    @Size(max = 255, message = "Legal name must be less than 255 characters")
    @JsonProperty("legal_name")
    private String legalName;

    /**
     * Doing Business As name of the merchant (PII data).
     * This field is optional and will be encrypted at rest if provided.
     */
    @Size(max = 255, message = "DBA name must be less than 255 characters")
    @JsonProperty("dba_name")
    private String dbaName;

    /**
     * Employer Identification Number (EIN) of the merchant (PII data).
     * This field is required, must follow the format XX-XXXXXXX,
     * and will be encrypted at rest.
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
    @Size(max = 100, message = "Industry must be less than 100 characters")
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
     * This method handles the conversion of all fields, including proper
     * formatting of address and financial information.
     *
     * @param application The associated Application entity
     * @return A new MerchantDetails entity with data from this DTO
     */
    public MerchantDetails toEntity(Application application) {
        if (application == null) {
            throw new IllegalArgumentException("Application cannot be null");
        }

        // Convert address DTO to entity address
        MerchantDetails.Address addressEntity = null;
        if (this.address != null) {
            addressEntity = MerchantDetails.Address.builder()
                    .street(this.address.getStreet())
                    .city(this.address.getCity())
                    .state(this.address.getState())
                    .zip(this.address.getZipCode())
                    .country(this.address.getCountry())
                    .build();
        }

        // Build and return the entity
        return MerchantDetails.builder()
                .application(application)
                .legalName(this.legalName)
                .dbaName(this.dbaName)
                .ein(this.ein)
                .address(addressEntity)
                .industry(this.industry)
                .revenue(this.revenue)
                .build();
    }

    /**
     * Updates an existing MerchantDetails entity with data from this DTO.
     * This method updates all fields in the entity with values from this DTO,
     * preserving the entity's ID, creation timestamp, and application reference.
     *
     * @param entity The existing MerchantDetails entity to update
     * @return The updated MerchantDetails entity
     */
    public MerchantDetails updateEntity(MerchantDetails entity) {
        if (entity == null) {
            throw new IllegalArgumentException("Entity cannot be null");
        }

        // Update simple fields
        entity.setLegalName(this.legalName);
        entity.setDbaName(this.dbaName);
        entity.setEin(this.ein);
        entity.setIndustry(this.industry);
        entity.setRevenue(this.revenue);

        // Update address if provided
        if (this.address != null) {
            MerchantDetails.Address addressEntity = entity.getAddress();
            if (addressEntity == null) {
                addressEntity = new MerchantDetails.Address();
            }
            
            addressEntity.setStreet(this.address.getStreet());
            addressEntity.setCity(this.address.getCity());
            addressEntity.setState(this.address.getState());
            addressEntity.setZip(this.address.getZipCode());
            addressEntity.setCountry(this.address.getCountry());
            
            entity.setAddress(addressEntity);
        }

        return entity;
    }

    /**
     * Inner class representing the address structure for API requests.
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
        @NotBlank(message = "Street is required")
        @JsonProperty("street")
        private String street;

        /**
         * City (PII data).
         */
        @NotBlank(message = "City is required")
        @JsonProperty("city")
        private String city;

        /**
         * State (2-letter code).
         */
        @NotBlank(message = "State is required")
        @Size(min = 2, max = 2, message = "State must be a 2-letter code")
        @JsonProperty("state")
        private String state;

        /**
         * ZIP code.
         */
        @NotBlank(message = "ZIP code is required")
        @Pattern(regexp = "^\\d{5}(-\\d{4})?$", message = "ZIP code must be in format XXXXX or XXXXX-XXXX")
        @JsonProperty("zip_code")
        private String zipCode;

        /**
         * Country.
         */
        @NotBlank(message = "Country is required")
        @JsonProperty("country")
        private String country;

        /**
         * Creates a new AddressDTO from a MerchantDetails.Address object.
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