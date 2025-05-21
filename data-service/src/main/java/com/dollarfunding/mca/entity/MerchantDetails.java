package com.dollarfunding.mca.entity;

import com.dollarfunding.mca.config.EncryptionConfig;
import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Objects;

/**
 * Entity class representing merchant information in the database.
 * Maps to the MerchantDetails schema with fields for merchant information.
 * Implements field-level encryption for sensitive PII data.
 */
@Entity
@Table(name = "merchant_details")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MerchantDetails {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * One-to-One relationship with Application entity.
     * Each merchant details record is associated with exactly one application.
     */
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "application_id", nullable = false)
    @JsonIgnore
    private Application application;

    /**
     * Legal name of the merchant (encrypted).
     * This field contains PII and is encrypted at rest.
     */
    @NotBlank(message = "Legal name is required")
    @Size(max = 255, message = "Legal name must be less than 255 characters")
    @Column(name = "legal_name", nullable = false)
    @Convert(converter = EncryptionConfig.StringEncryptionConverter.class)
    private String legalName;

    /**
     * Doing Business As name of the merchant (encrypted).
     * This field contains PII and is encrypted at rest.
     */
    @Size(max = 255, message = "DBA name must be less than 255 characters")
    @Column(name = "dba_name")
    @Convert(converter = EncryptionConfig.StringEncryptionConverter.class)
    private String dbaName;

    /**
     * Employer Identification Number of the merchant (encrypted).
     * This field contains PII and is encrypted at rest.
     */
    @NotBlank(message = "EIN is required")
    @Pattern(regexp = "^\\d{2}-\\d{7}$", message = "EIN must be in format XX-XXXXXXX")
    @Column(name = "ein", nullable = false)
    @Convert(converter = EncryptionConfig.StringEncryptionConverter.class)
    private String ein;

    /**
     * Address of the merchant stored as JSON.
     * Contains street, city, state, zip, and country.
     */
    @NotNull(message = "Address is required")
    @Column(name = "address", columnDefinition = "jsonb", nullable = false)
    @Convert(converter = EncryptionConfig.JsonAddressConverter.class)
    private Address address;

    /**
     * Industry of the merchant.
     */
    @NotBlank(message = "Industry is required")
    @Size(max = 100, message = "Industry must be less than 100 characters")
    @Column(name = "industry", nullable = false)
    private String industry;

    /**
     * Annual revenue of the merchant.
     */
    @NotNull(message = "Revenue is required")
    @Column(name = "revenue", nullable = false)
    private BigDecimal revenue;

    /**
     * Timestamp when the record was created.
     */
    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    /**
     * Timestamp when the record was last updated.
     */
    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    /**
     * Address class for storing merchant address information as JSON.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Address {
        @NotBlank(message = "Street is required")
        private String street;

        @NotBlank(message = "City is required")
        private String city;

        @NotBlank(message = "State is required")
        @Size(min = 2, max = 2, message = "State must be a 2-letter code")
        private String state;

        @NotBlank(message = "Zip code is required")
        @Pattern(regexp = "^\\d{5}(-\\d{4})?$", message = "Zip code must be in format XXXXX or XXXXX-XXXX")
        private String zip;

        @NotBlank(message = "Country is required")
        private String country;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        MerchantDetails that = (MerchantDetails) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "MerchantDetails{" +
                "id=" + id +
                ", applicationId=" + (application != null ? application.getId() : null) +
                ", legalName='[REDACTED]'" +
                ", dbaName='[REDACTED]'" +
                ", ein='[REDACTED]'" +
                ", industry='" + industry + '\'' +
                ", revenue=" + revenue +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}