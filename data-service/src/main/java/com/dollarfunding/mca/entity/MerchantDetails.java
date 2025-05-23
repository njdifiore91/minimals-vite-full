package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.util.EncryptionUtil;
import com.dollarfunding.mca.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;

import javax.persistence.*;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import org.hibernate.annotations.Type;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * JPA entity class representing merchant information in the database.
 * 
 * This entity maps to the MerchantDetails schema and stores detailed information about
 * the merchant applying for cash advance. It includes field-level encryption for sensitive
 * PII data and maintains a One-to-One relationship with the Application entity.
 * 
 * The OCR Service extracts this data from documents using machine learning models with
 * 99% data extraction accuracy.
 */
@Entity
@Table(name = "merchant_details")
public class MerchantDetails {

    /**
     * Encryption utility for field-level encryption of PII data
     */
    @Autowired
    @Transient
    private EncryptionUtil encryptionUtil;

    /**
     * Unique identifier for the merchant details
     */
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    /**
     * ID of the application this merchant details belongs to
     */
    @Column(name = "application_id", nullable = false)
    private UUID applicationId;
    
    /**
     * One-to-One relationship with the Application entity
     */
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "application_id", insertable = false, updatable = false)
    private Application application;

    /**
     * Legal name of the merchant (encrypted)
     * This field contains PII and is encrypted at the field level
     */
    @NotNull
    @Size(min = 1, max = 255)
    @Column(name = "legal_name", nullable = false)
    private String legalName;

    /**
     * Doing Business As name of the merchant (encrypted)
     * This field contains PII and is encrypted at the field level
     */
    @Size(max = 255)
    @Column(name = "dba_name")
    private String dbaName;

    /**
     * Employer Identification Number of the merchant (encrypted)
     * This field contains PII and is encrypted at the field level
     */
    @Size(max = 20)
    @Column(name = "ein")
    private String ein;

    /**
     * JSON string representation of the merchant's address
     * Includes street, city, state, zip, country
     */
    @Column(name = "address", columnDefinition = "jsonb")
    @Type(type = "jsonb")
    private String addressJson;

    /**
     * In-memory representation of the merchant's address
     * Not persisted directly to the database, but converted to/from addressJson
     */
    @Transient
    private Map<String, Object> address;

    /**
     * Industry of the merchant
     */
    @Size(max = 100)
    @Column(name = "industry")
    private String industry;

    /**
     * Annual revenue of the merchant
     */
    @Column(name = "revenue")
    private BigDecimal revenue;

    /**
     * Default constructor required by JPA
     */
    public MerchantDetails() {
        this.address = new HashMap<>();
    }

    /**
     * Constructor with required fields
     * 
     * @param applicationId The ID of the application this merchant details belongs to
     * @param legalName The legal name of the merchant
     */
    public MerchantDetails(UUID applicationId, String legalName) {
        this();
        this.applicationId = applicationId;
        this.legalName = legalName;
    }

    /**
     * Constructor with all fields except ID
     * 
     * @param applicationId The ID of the application this merchant details belongs to
     * @param legalName The legal name of the merchant
     * @param dbaName The doing business as name of the merchant
     * @param ein The employer identification number of the merchant
     * @param address The address of the merchant as a Map
     * @param industry The industry of the merchant
     * @param revenue The annual revenue of the merchant
     */
    public MerchantDetails(UUID applicationId, String legalName, String dbaName, String ein,
                          Map<String, Object> address, String industry, BigDecimal revenue) {
        this.applicationId = applicationId;
        // Note: Encryption will be handled by the setters when encryptionUtil is available
        this.legalName = legalName;
        this.dbaName = dbaName;
        this.ein = ein;
        this.address = address != null ? address : new HashMap<>();
        this.industry = industry;
        this.revenue = revenue;
        
        // Convert address map to JSON string
        if (address != null) {
            try {
                this.addressJson = JsonUtil.toJson(address);
            } catch (JsonUtil.JsonConversionException e) {
                this.addressJson = "{}";
            }
        } else {
            this.addressJson = "{}";
        }
    }

    /**
     * @return the merchant details ID
     */
    public UUID getId() {
        return id;
    }

    /**
     * @param id the merchant details ID to set
     */
    public void setId(UUID id) {
        this.id = id;
    }

    /**
     * @return the application ID this merchant details belongs to
     */
    public UUID getApplicationId() {
        return applicationId;
    }

    /**
     * @param applicationId the application ID to set
     */
    public void setApplicationId(UUID applicationId) {
        this.applicationId = applicationId;
    }
    
    /**
     * @return the application this merchant details belongs to
     */
    public Application getApplication() {
        return application;
    }

    /**
     * @param application the application to set
     */
    public void setApplication(Application application) {
        this.application = application;
        if (application != null && application.getId() != null) {
            this.applicationId = application.getId();
        }
    }

    /**
     * @return the legal name of the merchant (decrypted)
     */
    public String getLegalName() {
        if (legalName != null && encryptionUtil != null) {
            return encryptionUtil.decrypt(legalName);
        }
        return legalName;
    }

    /**
     * @param legalName the legal name to set (will be encrypted)
     */
    public void setLegalName(String legalName) {
        if (legalName != null && encryptionUtil != null) {
            this.legalName = encryptionUtil.encrypt(legalName);
        } else {
            this.legalName = legalName;
        }
    }

    /**
     * @return the doing business as name of the merchant (decrypted)
     */
    public String getDbaName() {
        if (dbaName != null && encryptionUtil != null) {
            return encryptionUtil.decrypt(dbaName);
        }
        return dbaName;
    }

    /**
     * @param dbaName the doing business as name to set (will be encrypted)
     */
    public void setDbaName(String dbaName) {
        if (dbaName != null && encryptionUtil != null) {
            this.dbaName = encryptionUtil.encrypt(dbaName);
        } else {
            this.dbaName = dbaName;
        }
    }

    /**
     * @return the employer identification number of the merchant (decrypted)
     */
    public String getEin() {
        if (ein != null && encryptionUtil != null) {
            return encryptionUtil.decrypt(ein);
        }
        return ein;
    }

    /**
     * @param ein the employer identification number to set (will be encrypted)
     */
    public void setEin(String ein) {
        if (ein != null && encryptionUtil != null) {
            this.ein = encryptionUtil.encrypt(ein);
        } else {
            this.ein = ein;
        }
    }

    /**
     * @return the address of the merchant
     */
    public Map<String, Object> getAddress() {
        if (address == null && addressJson != null && !addressJson.isEmpty()) {
            try {
                address = JsonUtil.fromJson(addressJson, new TypeReference<Map<String, Object>>() {});
            } catch (JsonUtil.JsonConversionException e) {
                address = new HashMap<>();
            }
        }
        return address != null ? address : new HashMap<>();
    }

    /**
     * @param address the address to set
     */
    public void setAddress(Map<String, Object> address) {
        this.address = address;
        if (address != null) {
            try {
                this.addressJson = JsonUtil.toJson(address);
            } catch (JsonUtil.JsonConversionException e) {
                this.addressJson = "{}";
            }
        } else {
            this.addressJson = "{}";
        }
    }

    /**
     * Gets the JSON string representation of the address
     * 
     * @return the address JSON string
     */
    public String getAddressJson() {
        return addressJson;
    }

    /**
     * Sets the address from a JSON string
     * 
     * @param addressJson the address JSON string to set
     */
    public void setAddressJson(String addressJson) {
        this.addressJson = addressJson;
        if (addressJson != null && !addressJson.isEmpty()) {
            try {
                this.address = JsonUtil.fromJson(addressJson, new TypeReference<Map<String, Object>>() {});
            } catch (JsonUtil.JsonConversionException e) {
                this.address = new HashMap<>();
            }
        } else {
            this.address = new HashMap<>();
        }
    }

    /**
     * Gets a specific address field
     * 
     * @param field the address field to get
     * @return the value of the address field, or null if not available
     */
    public String getAddressField(String field) {
        Map<String, Object> addressMap = getAddress();
        if (addressMap == null || !addressMap.containsKey(field)) {
            return null;
        }
        Object value = addressMap.get(field);
        return value != null ? value.toString() : null;
    }

    /**
     * Sets a specific address field
     * 
     * @param field the address field to set
     * @param value the value to set
     */
    public void setAddressField(String field, String value) {
        Map<String, Object> addressMap = getAddress();
        if (addressMap == null) {
            addressMap = new HashMap<>();
        }
        addressMap.put(field, value);
        setAddress(addressMap);
    }

    /**
     * @return the industry of the merchant
     */
    public String getIndustry() {
        return industry;
    }

    /**
     * @param industry the industry to set
     */
    public void setIndustry(String industry) {
        this.industry = industry;
    }

    /**
     * @return the annual revenue of the merchant
     */
    public BigDecimal getRevenue() {
        return revenue;
    }

    /**
     * @param revenue the annual revenue to set
     */
    public void setRevenue(BigDecimal revenue) {
        this.revenue = revenue;
    }

    /**
     * Gets the full address as a formatted string
     * 
     * @return the full address as a string
     */
    public String getFullAddress() {
        Map<String, Object> addressMap = getAddress();
        if (addressMap == null || addressMap.isEmpty()) {
            return "";
        }
        
        StringBuilder sb = new StringBuilder();
        appendIfNotNull(sb, addressMap.get("street"), "");
        appendIfNotNull(sb, addressMap.get("city"), ", ");
        appendIfNotNull(sb, addressMap.get("state"), ", ");
        appendIfNotNull(sb, addressMap.get("zip"), " ");
        appendIfNotNull(sb, addressMap.get("country"), ", ");
        
        return sb.toString();
    }
    
    /**
     * Helper method to append address components to a StringBuilder
     * 
     * @param sb the StringBuilder to append to
     * @param value the value to append
     * @param prefix the prefix to add before the value
     */
    private void appendIfNotNull(StringBuilder sb, Object value, String prefix) {
        if (value != null && !value.toString().isEmpty()) {
            if (sb.length() > 0 && !prefix.isEmpty()) {
                sb.append(prefix);
            }
            sb.append(value);
        }
    }

    /**
     * Checks if this merchant details has a valid address
     * 
     * @return true if the merchant details has a valid address
     */
    public boolean hasValidAddress() {
        Map<String, Object> addressMap = getAddress();
        if (addressMap == null || addressMap.isEmpty()) {
            return false;
        }
        
        // Check for required address fields
        return addressMap.containsKey("street") && 
               addressMap.containsKey("city") && 
               addressMap.containsKey("state") && 
               addressMap.containsKey("zip");
    }

    /**
     * Returns a string representation of this entity for debugging and logging
     * 
     * @return a string representation of this entity
     */
    @Override
    public String toString() {
        return "MerchantDetails{" +
                "id=" + id +
                ", applicationId=" + applicationId +
                ", legalName='[REDACTED]'" +
                ", dbaName='[REDACTED]'" +
                ", ein='[REDACTED]'" +
                ", hasAddress=" + hasValidAddress() +
                ", industry='" + industry + '\'' +
                ", hasRevenue=" + (revenue != null) +
                "}";
    }

    /**
     * Compares this entity with another object for equality
     * 
     * @param o the object to compare with
     * @return true if the objects are equal
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        MerchantDetails that = (MerchantDetails) o;

        return id != null ? id.equals(that.id) : that.id == null;
    }

    /**
     * Returns a hash code for this entity
     * 
     * @return a hash code value for this object
     */
    @Override
    public int hashCode() {
        return id != null ? id.hashCode() : 0;
    }

    /**
     * Sets the encryption utility for this entity
     * 
     * @param encryptionUtil the encryption utility to set
     */
    public void setEncryptionUtil(EncryptionUtil encryptionUtil) {
        this.encryptionUtil = encryptionUtil;
    }
    
    /**
     * Encrypts all sensitive fields in this entity
     * This method should be called after loading the entity from the database
     * to ensure that all sensitive fields are properly encrypted
     */
    @PostLoad
    public void encryptSensitiveFields() {
        if (encryptionUtil != null) {
            if (legalName != null && !legalName.isEmpty() && !isEncrypted(legalName)) {
                legalName = encryptionUtil.encrypt(legalName);
            }
            if (dbaName != null && !dbaName.isEmpty() && !isEncrypted(dbaName)) {
                dbaName = encryptionUtil.encrypt(dbaName);
            }
            if (ein != null && !ein.isEmpty() && !isEncrypted(ein)) {
                ein = encryptionUtil.encrypt(ein);
            }
        }
    }
    
    /**
     * Checks if a string is already encrypted
     * This is a simple heuristic and may need to be improved
     * 
     * @param value the string to check
     * @return true if the string appears to be encrypted
     */
    private boolean isEncrypted(String value) {
        // A simple heuristic: encrypted values are Base64 encoded and typically longer
        return value != null && value.length() > 20 && value.matches("^[A-Za-z0-9+/=]+$");
    }

    /**
     * Builder class for creating MerchantDetails instances
     */
    public static class Builder {
        private UUID applicationId;
        private String legalName;
        private String dbaName;
        private String ein;
        private Map<String, Object> address = new HashMap<>();
        private String industry;
        private BigDecimal revenue;
        private EncryptionUtil encryptionUtil;

        public Builder(UUID applicationId, String legalName) {
            this.applicationId = applicationId;
            this.legalName = legalName;
        }

        public Builder withDbaName(String dbaName) {
            this.dbaName = dbaName;
            return this;
        }

        public Builder withEin(String ein) {
            this.ein = ein;
            return this;
        }

        public Builder withAddress(Map<String, Object> address) {
            this.address = address;
            return this;
        }

        public Builder addAddressField(String field, String value) {
            this.address.put(field, value);
            return this;
        }

        public Builder withIndustry(String industry) {
            this.industry = industry;
            return this;
        }

        public Builder withRevenue(BigDecimal revenue) {
            this.revenue = revenue;
            return this;
        }
        
        public Builder withEncryptionUtil(EncryptionUtil encryptionUtil) {
            this.encryptionUtil = encryptionUtil;
            return this;
        }

        public MerchantDetails build() {
            MerchantDetails merchantDetails = new MerchantDetails(applicationId, legalName, dbaName, ein, address, industry, revenue);
            if (encryptionUtil != null) {
                merchantDetails.setEncryptionUtil(encryptionUtil);
                // Encrypt sensitive fields
                merchantDetails.setLegalName(legalName);
                merchantDetails.setDbaName(dbaName);
                merchantDetails.setEin(ein);
            }
            return merchantDetails;
        }
    }
}