package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.MerchantDetails;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository interface for MerchantDetails entities.
 * 
 * This repository provides database access methods for merchant information associated with MCA applications.
 * It extends JpaRepository to inherit standard CRUD operations and adds custom query methods for finding
 * merchants by application ID, legal name, DBA name, industry, and other attributes.
 * 
 * The repository supports field-level encryption for sensitive PII data through the MerchantDetails entity,
 * which handles encryption and decryption of sensitive fields like legal name, DBA name, and EIN.
 */
@Repository
public interface MerchantDetailsRepository extends JpaRepository<MerchantDetails, UUID> {
    
    /**
     * Find a merchant details record by its ID.
     * 
     * @param id The merchant details ID
     * @return Optional containing the merchant details if found, empty otherwise
     */
    Optional<MerchantDetails> findById(UUID id);
    
    /**
     * Find a merchant details record by application ID.
     * 
     * @param applicationId The application ID to search for
     * @return Optional containing the merchant details if found, empty otherwise
     */
    Optional<MerchantDetails> findByApplicationId(UUID applicationId);
    
    /**
     * Check if a merchant details record exists for the given application ID.
     * 
     * @param applicationId The application ID to check
     * @return true if a merchant details record exists for the application, false otherwise
     */
    boolean existsByApplicationId(UUID applicationId);
    
    /**
     * Find merchant details records by legal name (case-insensitive partial match).
     * Note: Due to field-level encryption, this query may not be efficient and should be used with caution.
     * 
     * @param legalName The legal name to search for (partial match)
     * @return List of merchant details records with matching legal name
     */
    @Query("SELECT m FROM MerchantDetails m WHERE LOWER(m.legalName) LIKE LOWER(CONCAT('%', :legalName, '%'))")
    List<MerchantDetails> findByLegalNameContainingIgnoreCase(@Param("legalName") String legalName);
    
    /**
     * Find merchant details records by legal name (case-insensitive partial match), with pagination.
     * Note: Due to field-level encryption, this query may not be efficient and should be used with caution.
     * 
     * @param legalName The legal name to search for (partial match)
     * @param pageable The pagination information
     * @return Page of merchant details records with matching legal name
     */
    @Query("SELECT m FROM MerchantDetails m WHERE LOWER(m.legalName) LIKE LOWER(CONCAT('%', :legalName, '%'))")
    Page<MerchantDetails> findByLegalNameContainingIgnoreCase(@Param("legalName") String legalName, Pageable pageable);
    
    /**
     * Find merchant details records by DBA name (case-insensitive partial match).
     * Note: Due to field-level encryption, this query may not be efficient and should be used with caution.
     * 
     * @param dbaName The DBA name to search for (partial match)
     * @return List of merchant details records with matching DBA name
     */
    @Query("SELECT m FROM MerchantDetails m WHERE LOWER(m.dbaName) LIKE LOWER(CONCAT('%', :dbaName, '%'))")
    List<MerchantDetails> findByDbaNameContainingIgnoreCase(@Param("dbaName") String dbaName);
    
    /**
     * Find merchant details records by DBA name (case-insensitive partial match), with pagination.
     * Note: Due to field-level encryption, this query may not be efficient and should be used with caution.
     * 
     * @param dbaName The DBA name to search for (partial match)
     * @param pageable The pagination information
     * @return Page of merchant details records with matching DBA name
     */
    @Query("SELECT m FROM MerchantDetails m WHERE LOWER(m.dbaName) LIKE LOWER(CONCAT('%', :dbaName, '%'))")
    Page<MerchantDetails> findByDbaNameContainingIgnoreCase(@Param("dbaName") String dbaName, Pageable pageable);
    
    /**
     * Find merchant details records by EIN.
     * Note: Due to field-level encryption, this query may not be efficient and should be used with caution.
     * 
     * @param ein The EIN to search for
     * @return List of merchant details records with matching EIN
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.ein = :ein")
    List<MerchantDetails> findByEin(@Param("ein") String ein);
    
    /**
     * Find merchant details records by industry (case-insensitive partial match).
     * 
     * @param industry The industry to search for (partial match)
     * @return List of merchant details records with matching industry
     */
    List<MerchantDetails> findByIndustryContainingIgnoreCase(String industry);
    
    /**
     * Find merchant details records by industry (case-insensitive partial match), with pagination.
     * 
     * @param industry The industry to search for (partial match)
     * @param pageable The pagination information
     * @return Page of merchant details records with matching industry
     */
    Page<MerchantDetails> findByIndustryContainingIgnoreCase(String industry, Pageable pageable);
    
    /**
     * Find merchant details records by exact industry match.
     * 
     * @param industry The industry to search for (exact match)
     * @return List of merchant details records with the specified industry
     */
    List<MerchantDetails> findByIndustry(String industry);
    
    /**
     * Find merchant details records by exact industry match, with pagination.
     * 
     * @param industry The industry to search for (exact match)
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified industry
     */
    Page<MerchantDetails> findByIndustry(String industry, Pageable pageable);
    
    /**
     * Find merchant details records with revenue greater than or equal to the specified amount.
     * 
     * @param revenue The minimum revenue amount
     * @return List of merchant details records with revenue >= the specified amount
     */
    List<MerchantDetails> findByRevenueGreaterThanEqual(BigDecimal revenue);
    
    /**
     * Find merchant details records with revenue greater than or equal to the specified amount, with pagination.
     * 
     * @param revenue The minimum revenue amount
     * @param pageable The pagination information
     * @return Page of merchant details records with revenue >= the specified amount
     */
    Page<MerchantDetails> findByRevenueGreaterThanEqual(BigDecimal revenue, Pageable pageable);
    
    /**
     * Find merchant details records with revenue less than or equal to the specified amount.
     * 
     * @param revenue The maximum revenue amount
     * @return List of merchant details records with revenue <= the specified amount
     */
    List<MerchantDetails> findByRevenueLessThanEqual(BigDecimal revenue);
    
    /**
     * Find merchant details records with revenue less than or equal to the specified amount, with pagination.
     * 
     * @param revenue The maximum revenue amount
     * @param pageable The pagination information
     * @return Page of merchant details records with revenue <= the specified amount
     */
    Page<MerchantDetails> findByRevenueLessThanEqual(BigDecimal revenue, Pageable pageable);
    
    /**
     * Find merchant details records with revenue between the specified minimum and maximum amounts.
     * 
     * @param minRevenue The minimum revenue amount (inclusive)
     * @param maxRevenue The maximum revenue amount (inclusive)
     * @return List of merchant details records with revenue between the specified amounts
     */
    List<MerchantDetails> findByRevenueBetween(BigDecimal minRevenue, BigDecimal maxRevenue);
    
    /**
     * Find merchant details records with revenue between the specified minimum and maximum amounts, with pagination.
     * 
     * @param minRevenue The minimum revenue amount (inclusive)
     * @param maxRevenue The maximum revenue amount (inclusive)
     * @param pageable The pagination information
     * @return Page of merchant details records with revenue between the specified amounts
     */
    Page<MerchantDetails> findByRevenueBetween(BigDecimal minRevenue, BigDecimal maxRevenue, Pageable pageable);
    
    /**
     * Find merchant details records with a specific address field value.
     * 
     * @param field The address field name (e.g., "state", "city", "zip")
     * @param value The value to search for
     * @return List of merchant details records with the specified address field value
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> :field = :value")
    List<MerchantDetails> findByAddressField(@Param("field") String field, @Param("value") String value);
    
    /**
     * Find merchant details records with a specific address field value, with pagination.
     * 
     * @param field The address field name (e.g., "state", "city", "zip")
     * @param value The value to search for
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified address field value
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> :field = :value")
    Page<MerchantDetails> findByAddressField(@Param("field") String field, @Param("value") String value, Pageable pageable);
    
    /**
     * Find merchant details records with a specific state in their address.
     * 
     * @param state The state code to search for (e.g., "CA", "NY")
     * @return List of merchant details records with the specified state
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'state' = :state")
    List<MerchantDetails> findByState(@Param("state") String state);
    
    /**
     * Find merchant details records with a specific state in their address, with pagination.
     * 
     * @param state The state code to search for (e.g., "CA", "NY")
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified state
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'state' = :state")
    Page<MerchantDetails> findByState(@Param("state") String state, Pageable pageable);
    
    /**
     * Find merchant details records with a specific city in their address.
     * 
     * @param city The city to search for
     * @return List of merchant details records with the specified city
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'city' = :city")
    List<MerchantDetails> findByCity(@Param("city") String city);
    
    /**
     * Find merchant details records with a specific city in their address, with pagination.
     * 
     * @param city The city to search for
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified city
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'city' = :city")
    Page<MerchantDetails> findByCity(@Param("city") String city, Pageable pageable);
    
    /**
     * Find merchant details records with a specific ZIP code in their address.
     * 
     * @param zip The ZIP code to search for
     * @return List of merchant details records with the specified ZIP code
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'zip' = :zip")
    List<MerchantDetails> findByZip(@Param("zip") String zip);
    
    /**
     * Find merchant details records with a specific ZIP code in their address, with pagination.
     * 
     * @param zip The ZIP code to search for
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified ZIP code
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'zip' = :zip")
    Page<MerchantDetails> findByZip(@Param("zip") String zip, Pageable pageable);
    
    /**
     * Find merchant details records with a specific state and city in their address.
     * 
     * @param state The state code to search for (e.g., "CA", "NY")
     * @param city The city to search for
     * @return List of merchant details records with the specified state and city
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'state' = :state AND m.addressJson ->> 'city' = :city")
    List<MerchantDetails> findByStateAndCity(@Param("state") String state, @Param("city") String city);
    
    /**
     * Find merchant details records with a specific state and city in their address, with pagination.
     * 
     * @param state The state code to search for (e.g., "CA", "NY")
     * @param city The city to search for
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified state and city
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'state' = :state AND m.addressJson ->> 'city' = :city")
    Page<MerchantDetails> findByStateAndCity(@Param("state") String state, @Param("city") String city, Pageable pageable);
    
    /**
     * Find merchant details records with a specific industry and minimum revenue.
     * 
     * @param industry The industry to search for
     * @param minRevenue The minimum revenue amount
     * @return List of merchant details records with the specified industry and minimum revenue
     */
    List<MerchantDetails> findByIndustryAndRevenueGreaterThanEqual(String industry, BigDecimal minRevenue);
    
    /**
     * Find merchant details records with a specific industry and minimum revenue, with pagination.
     * 
     * @param industry The industry to search for
     * @param minRevenue The minimum revenue amount
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified industry and minimum revenue
     */
    Page<MerchantDetails> findByIndustryAndRevenueGreaterThanEqual(String industry, BigDecimal minRevenue, Pageable pageable);
    
    /**
     * Find merchant details records with a specific state and minimum revenue.
     * 
     * @param state The state code to search for (e.g., "CA", "NY")
     * @param minRevenue The minimum revenue amount
     * @return List of merchant details records with the specified state and minimum revenue
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'state' = :state AND m.revenue >= :minRevenue")
    List<MerchantDetails> findByStateAndRevenueGreaterThanEqual(@Param("state") String state, @Param("minRevenue") BigDecimal minRevenue);
    
    /**
     * Find merchant details records with a specific state and minimum revenue, with pagination.
     * 
     * @param state The state code to search for (e.g., "CA", "NY")
     * @param minRevenue The minimum revenue amount
     * @param pageable The pagination information
     * @return Page of merchant details records with the specified state and minimum revenue
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ->> 'state' = :state AND m.revenue >= :minRevenue")
    Page<MerchantDetails> findByStateAndRevenueGreaterThanEqual(@Param("state") String state, @Param("minRevenue") BigDecimal minRevenue, Pageable pageable);
    
    /**
     * Count the number of merchant details records with a specific industry.
     * 
     * @param industry The industry to count
     * @return The number of merchant details records with the specified industry
     */
    long countByIndustry(String industry);
    
    /**
     * Count the number of merchant details records with a specific state in their address.
     * 
     * @param state The state code to count (e.g., "CA", "NY")
     * @return The number of merchant details records with the specified state
     */
    @Query("SELECT COUNT(m) FROM MerchantDetails m WHERE m.addressJson ->> 'state' = :state")
    long countByState(@Param("state") String state);
    
    /**
     * Count the number of merchant details records with revenue greater than or equal to the specified amount.
     * 
     * @param revenue The minimum revenue amount
     * @return The number of merchant details records with revenue >= the specified amount
     */
    long countByRevenueGreaterThanEqual(BigDecimal revenue);
    
    /**
     * Find merchant details records with valid addresses.
     * A valid address has street, city, state, and zip fields.
     * 
     * @return List of merchant details records with valid addresses
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ? 'street' AND m.addressJson ? 'city' AND m.addressJson ? 'state' AND m.addressJson ? 'zip'")
    List<MerchantDetails> findWithValidAddresses();
    
    /**
     * Find merchant details records with valid addresses, with pagination.
     * A valid address has street, city, state, and zip fields.
     * 
     * @param pageable The pagination information
     * @return Page of merchant details records with valid addresses
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.addressJson ? 'street' AND m.addressJson ? 'city' AND m.addressJson ? 'state' AND m.addressJson ? 'zip'")
    Page<MerchantDetails> findWithValidAddresses(Pageable pageable);
    
    /**
     * Find merchant details records with incomplete addresses.
     * An incomplete address is missing one or more of street, city, state, or zip fields.
     * 
     * @return List of merchant details records with incomplete addresses
     */
    @Query("SELECT m FROM MerchantDetails m WHERE NOT (m.addressJson ? 'street' AND m.addressJson ? 'city' AND m.addressJson ? 'state' AND m.addressJson ? 'zip')")
    List<MerchantDetails> findWithIncompleteAddresses();
    
    /**
     * Find merchant details records with incomplete addresses, with pagination.
     * An incomplete address is missing one or more of street, city, state, or zip fields.
     * 
     * @param pageable The pagination information
     * @return Page of merchant details records with incomplete addresses
     */
    @Query("SELECT m FROM MerchantDetails m WHERE NOT (m.addressJson ? 'street' AND m.addressJson ? 'city' AND m.addressJson ? 'state' AND m.addressJson ? 'zip')")
    Page<MerchantDetails> findWithIncompleteAddresses(Pageable pageable);
}