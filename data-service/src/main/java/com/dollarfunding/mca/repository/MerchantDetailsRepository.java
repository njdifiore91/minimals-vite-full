package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.MerchantDetails;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository interface for {@link MerchantDetails} entities.
 * <p>
 * This repository provides database access methods for merchant information associated with MCA applications,
 * including standard CRUD operations inherited from JpaRepository and custom query methods for finding
 * merchants by application ID, legal name, DBA name, industry, and other attributes.
 * </p>
 * <p>
 * It is used by the MerchantService to persist and retrieve merchant data with field-level encryption
 * for sensitive information.
 * </p>
 */
@Repository
public interface MerchantDetailsRepository extends JpaRepository<MerchantDetails, Long> {

    /**
     * Finds merchant details by application.
     *
     * @param application the application to find merchant details for
     * @return an Optional containing the merchant details if found, or empty if not found
     */
    Optional<MerchantDetails> findByApplication(Application application);

    /**
     * Finds merchant details by application ID.
     *
     * @param applicationId the ID of the application to find merchant details for
     * @return an Optional containing the merchant details if found, or empty if not found
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.application.id = :applicationId")
    Optional<MerchantDetails> findByApplicationId(@Param("applicationId") UUID applicationId);

    /**
     * Finds merchants by industry.
     *
     * @param industry the industry to filter by
     * @return a list of merchants in the specified industry
     */
    List<MerchantDetails> findByIndustry(String industry);

    /**
     * Finds merchants by partial industry match (case-insensitive).
     *
     * @param industry the partial industry name to filter by
     * @return a list of merchants with industry names containing the specified string
     */
    List<MerchantDetails> findByIndustryContainingIgnoreCase(String industry);

    /**
     * Finds merchants by partial industry match (case-insensitive) with pagination.
     *
     * @param industry the partial industry name to filter by
     * @param pageable the pagination information
     * @return a page of merchants with industry names containing the specified string
     */
    Page<MerchantDetails> findByIndustryContainingIgnoreCase(String industry, Pageable pageable);

    /**
     * Finds merchants within a revenue range.
     *
     * @param min the minimum revenue
     * @param max the maximum revenue
     * @return a list of merchants with revenue between the specified values
     */
    List<MerchantDetails> findByRevenueBetween(BigDecimal min, BigDecimal max);

    /**
     * Finds merchants within a revenue range with pagination.
     *
     * @param min the minimum revenue
     * @param max the maximum revenue
     * @param pageable the pagination information
     * @return a page of merchants with revenue between the specified values
     */
    Page<MerchantDetails> findByRevenueBetween(BigDecimal min, BigDecimal max, Pageable pageable);

    /**
     * Finds merchants with revenue greater than or equal to a value.
     *
     * @param min the minimum revenue
     * @return a list of merchants with revenue greater than or equal to the specified value
     */
    List<MerchantDetails> findByRevenueGreaterThanEqual(BigDecimal min);

    /**
     * Finds merchants with revenue less than or equal to a value.
     *
     * @param max the maximum revenue
     * @return a list of merchants with revenue less than or equal to the specified value
     */
    List<MerchantDetails> findByRevenueLessThanEqual(BigDecimal max);

    /**
     * Finds merchants by state.
     * <p>
     * Note: This query uses a JSON path expression to filter on the address.state field,
     * which is stored as part of the JSON address object.
     * </p>
     *
     * @param state the state to filter by (2-letter code)
     * @return a list of merchants in the specified state
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.state = :state")
    List<MerchantDetails> findByAddressState(@Param("state") String state);

    /**
     * Finds merchants by city.
     * <p>
     * Note: This query uses a JSON path expression to filter on the address.city field,
     * which is stored as part of the JSON address object.
     * </p>
     *
     * @param city the city to filter by
     * @return a list of merchants in the specified city
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.city = :city")
    List<MerchantDetails> findByAddressCity(@Param("city") String city);

    /**
     * Finds merchants by zip code.
     * <p>
     * Note: This query uses a JSON path expression to filter on the address.zip field,
     * which is stored as part of the JSON address object.
     * </p>
     *
     * @param zip the zip code to filter by
     * @return a list of merchants with the specified zip code
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.zip = :zip")
    List<MerchantDetails> findByAddressZip(@Param("zip") String zip);

    /**
     * Finds merchants by state with pagination.
     *
     * @param state the state to filter by (2-letter code)
     * @param pageable the pagination information
     * @return a page of merchants in the specified state
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.state = :state")
    Page<MerchantDetails> findByAddressState(@Param("state") String state, Pageable pageable);

    /**
     * Finds merchants by city with pagination.
     *
     * @param city the city to filter by
     * @param pageable the pagination information
     * @return a page of merchants in the specified city
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.city = :city")
    Page<MerchantDetails> findByAddressCity(@Param("city") String city, Pageable pageable);

    /**
     * Finds merchants by zip code with pagination.
     *
     * @param zip the zip code to filter by
     * @param pageable the pagination information
     * @return a page of merchants with the specified zip code
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.zip = :zip")
    Page<MerchantDetails> findByAddressZip(@Param("zip") String zip, Pageable pageable);

    /**
     * Finds merchants by legal name (case-insensitive).
     * <p>
     * Note: This query may not be efficient for encrypted fields. The filtering will likely
     * be performed in memory after decryption, rather than at the database level.
     * </p>
     *
     * @param legalName the legal name to filter by
     * @return a list of merchants with the specified legal name
     */
    List<MerchantDetails> findByLegalNameIgnoreCase(String legalName);

    /**
     * Finds merchants by partial legal name match (case-insensitive).
     * <p>
     * Note: This query may not be efficient for encrypted fields. The filtering will likely
     * be performed in memory after decryption, rather than at the database level.
     * </p>
     *
     * @param legalName the partial legal name to filter by
     * @return a list of merchants with legal names containing the specified string
     */
    List<MerchantDetails> findByLegalNameContainingIgnoreCase(String legalName);

    /**
     * Finds merchants by DBA name (case-insensitive).
     * <p>
     * Note: This query may not be efficient for encrypted fields. The filtering will likely
     * be performed in memory after decryption, rather than at the database level.
     * </p>
     *
     * @param dbaName the DBA name to filter by
     * @return a list of merchants with the specified DBA name
     */
    List<MerchantDetails> findByDbaNameIgnoreCase(String dbaName);

    /**
     * Finds merchants by partial DBA name match (case-insensitive).
     * <p>
     * Note: This query may not be efficient for encrypted fields. The filtering will likely
     * be performed in memory after decryption, rather than at the database level.
     * </p>
     *
     * @param dbaName the partial DBA name to filter by
     * @return a list of merchants with DBA names containing the specified string
     */
    List<MerchantDetails> findByDbaNameContainingIgnoreCase(String dbaName);

    /**
     * Finds merchants by industry and revenue range.
     *
     * @param industry the industry to filter by
     * @param minRevenue the minimum revenue
     * @param maxRevenue the maximum revenue
     * @return a list of merchants in the specified industry with revenue between the specified values
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.industry = :industry AND m.revenue BETWEEN :minRevenue AND :maxRevenue")
    List<MerchantDetails> findByIndustryAndRevenueBetween(
            @Param("industry") String industry,
            @Param("minRevenue") BigDecimal minRevenue,
            @Param("maxRevenue") BigDecimal maxRevenue);

    /**
     * Finds merchants by industry and revenue range with pagination.
     *
     * @param industry the industry to filter by
     * @param minRevenue the minimum revenue
     * @param maxRevenue the maximum revenue
     * @param pageable the pagination information
     * @return a page of merchants in the specified industry with revenue between the specified values
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.industry = :industry AND m.revenue BETWEEN :minRevenue AND :maxRevenue")
    Page<MerchantDetails> findByIndustryAndRevenueBetween(
            @Param("industry") String industry,
            @Param("minRevenue") BigDecimal minRevenue,
            @Param("maxRevenue") BigDecimal maxRevenue,
            Pageable pageable);

    /**
     * Finds merchants by state and industry.
     *
     * @param state the state to filter by (2-letter code)
     * @param industry the industry to filter by
     * @return a list of merchants in the specified state and industry
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.state = :state AND m.industry = :industry")
    List<MerchantDetails> findByAddressStateAndIndustry(
            @Param("state") String state,
            @Param("industry") String industry);

    /**
     * Finds merchants by state and industry with pagination.
     *
     * @param state the state to filter by (2-letter code)
     * @param industry the industry to filter by
     * @param pageable the pagination information
     * @return a page of merchants in the specified state and industry
     */
    @Query("SELECT m FROM MerchantDetails m WHERE m.address.state = :state AND m.industry = :industry")
    Page<MerchantDetails> findByAddressStateAndIndustry(
            @Param("state") String state,
            @Param("industry") String industry,
            Pageable pageable);

    /**
     * Counts merchants by industry.
     *
     * @param industry the industry to count merchants for
     * @return the number of merchants in the specified industry
     */
    long countByIndustry(String industry);

    /**
     * Counts merchants by state.
     *
     * @param state the state to count merchants for (2-letter code)
     * @return the number of merchants in the specified state
     */
    @Query("SELECT COUNT(m) FROM MerchantDetails m WHERE m.address.state = :state")
    long countByAddressState(@Param("state") String state);

    /**
     * Checks if a merchant exists for the specified application.
     *
     * @param application the application to check for
     * @return true if a merchant exists for the specified application, false otherwise
     */
    boolean existsByApplication(Application application);

    /**
     * Checks if a merchant exists for the specified application ID.
     *
     * @param applicationId the application ID to check for
     * @return true if a merchant exists for the specified application ID, false otherwise
     */
    @Query("SELECT CASE WHEN COUNT(m) > 0 THEN true ELSE false END FROM MerchantDetails m WHERE m.application.id = :applicationId")
    boolean existsByApplicationId(@Param("applicationId") UUID applicationId);
}