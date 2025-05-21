package com.dollarfunding.mca.dto;

import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.util.EncryptionUtil;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Data Transfer Object for returning merchant details to clients.
 * Provides a complete view of merchant information while handling sensitive PII data appropriately.
 * Used for API responses in the MCA application processing system.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class MerchantDetailsResponseDTO {

    @JsonProperty("id")
    private Long id;

    @JsonProperty("application_id")
    private Long applicationId;

    @JsonProperty("legal_name")
    private String legalName;

    @JsonProperty("dba_name")
    private String dbaName;

    @JsonProperty("ein")
    private String ein;

    @JsonProperty("address")
    private Map<String, String> address;

    @JsonProperty("industry")
    private String industry;

    @JsonProperty("revenue")
    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private BigDecimal revenue;

    /**
     * Default constructor for Jackson deserialization
     */
    public MerchantDetailsResponseDTO() {
    }

    /**
     * Constructor to create DTO from entity
     * @param merchantDetails The merchant details entity
     */
    public MerchantDetailsResponseDTO(MerchantDetails merchantDetails) {
        this.id = merchantDetails.getId();
        this.applicationId = merchantDetails.getApplicationId();
        
        // Handle sensitive PII data appropriately
        this.legalName = maskSensitiveData(merchantDetails.getLegalName());
        this.dbaName = maskSensitiveData(merchantDetails.getDbaName());
        this.ein = maskEIN(merchantDetails.getEin());
        
        this.address = merchantDetails.getAddress();
        this.industry = merchantDetails.getIndustry();
        this.revenue = merchantDetails.getRevenue();
    }

    /**
     * Static factory method to create DTO from entity
     * @param merchantDetails The merchant details entity
     * @return A new MerchantDetailsResponseDTO instance
     */
    public static MerchantDetailsResponseDTO fromEntity(MerchantDetails merchantDetails) {
        if (merchantDetails == null) {
            return null;
        }
        return new MerchantDetailsResponseDTO(merchantDetails);
    }

    /**
     * Masks sensitive data for API responses
     * @param data The sensitive data to mask
     * @return Masked data string
     */
    private String maskSensitiveData(String data) {
        if (data == null || data.isEmpty()) {
            return data;
        }
        
        // Show only first and last character, mask the rest
        if (data.length() <= 2) {
            return data;
        }
        
        return data.substring(0, 1) + 
               "*".repeat(data.length() - 2) + 
               data.substring(data.length() - 1);
    }

    /**
     * Masks EIN (Employer Identification Number) for API responses
     * Format: XX-XXXXXXX (show only last 4 digits)
     * @param ein The EIN to mask
     * @return Masked EIN string
     */
    private String maskEIN(String ein) {
        if (ein == null || ein.isEmpty()) {
            return ein;
        }
        
        // Format: XX-XXXXXXX (show only last 4 digits)
        if (ein.contains("-") && ein.length() >= 10) {
            return "**-***" + ein.substring(ein.length() - 4);
        } else if (ein.length() >= 9) {
            // Handle EIN without hyphen
            return "*****" + ein.substring(ein.length() - 4);
        }
        
        return ein;
    }

    // Getters and setters

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getApplicationId() {
        return applicationId;
    }

    public void setApplicationId(Long applicationId) {
        this.applicationId = applicationId;
    }

    public String getLegalName() {
        return legalName;
    }

    public void setLegalName(String legalName) {
        this.legalName = legalName;
    }

    public String getDbaName() {
        return dbaName;
    }

    public void setDbaName(String dbaName) {
        this.dbaName = dbaName;
    }

    public String getEin() {
        return ein;
    }

    public void setEin(String ein) {
        this.ein = ein;
    }

    public Map<String, String> getAddress() {
        return address;
    }

    public void setAddress(Map<String, String> address) {
        this.address = address;
    }

    public String getIndustry() {
        return industry;
    }

    public void setIndustry(String industry) {
        this.industry = industry;
    }

    public BigDecimal getRevenue() {
        return revenue;
    }

    public void setRevenue(BigDecimal revenue) {
        this.revenue = revenue;
    }
}