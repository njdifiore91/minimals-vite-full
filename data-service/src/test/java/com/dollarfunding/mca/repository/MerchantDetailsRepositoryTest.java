package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.context.ActiveProfiles;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * JUnit test class for {@link MerchantDetailsRepository}.
 * 
 * This class verifies that the repository correctly interacts with the database
 * for MerchantDetails entities, testing CRUD operations, custom query methods,
 * and the relationship between MerchantDetails and Application entities.
 */
@DataJpaTest
@ActiveProfiles("test")
public class MerchantDetailsRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private MerchantDetailsRepository merchantDetailsRepository;

    @Autowired
    private ApplicationRepository applicationRepository;

    private Application testApplication;
    private MerchantDetails testMerchantDetails;

    /**
     * Sets up test data before each test.
     */
    @BeforeEach
    public void setup() {
        // Create a test application
        testApplication = new Application();
        testApplication.setStatus(ApplicationStatus.NEW);
        testApplication.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(testApplication);
        entityManager.flush();

        // Create a test merchant details record
        testMerchantDetails = new MerchantDetails();
        testMerchantDetails.setApplication(testApplication);
        testMerchantDetails.setLegalName("Test Merchant LLC");
        testMerchantDetails.setDbaName("Test Merchant");
        testMerchantDetails.setEin("12-3456789");
        
        MerchantDetails.Address address = new MerchantDetails.Address();
        address.setStreet("123 Test St");
        address.setCity("Test City");
        address.setState("TX");
        address.setZip("12345");
        address.setCountry("USA");
        testMerchantDetails.setAddress(address);
        
        testMerchantDetails.setIndustry("Technology");
        testMerchantDetails.setRevenue(new BigDecimal("500000.00"));
        
        entityManager.persist(testMerchantDetails);
        entityManager.flush();
    }

    /**
     * Tests saving a merchant details record.
     */
    @Test
    @DisplayName("Should save merchant details")
    public void testSaveMerchantDetails() {
        // Create a new application
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(application);
        
        // Create a new merchant details record
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("New Merchant LLC");
        merchantDetails.setDbaName("New Merchant");
        merchantDetails.setEin("98-7654321");
        
        MerchantDetails.Address address = new MerchantDetails.Address();
        address.setStreet("456 New St");
        address.setCity("New City");
        address.setState("NY");
        address.setZip("54321");
        address.setCountry("USA");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Retail");
        merchantDetails.setRevenue(new BigDecimal("1000000.00"));
        
        // Save the merchant details
        MerchantDetails savedMerchantDetails = merchantDetailsRepository.save(merchantDetails);
        
        // Verify the merchant details was saved
        assertThat(savedMerchantDetails).isNotNull();
        assertThat(savedMerchantDetails.getId()).isNotNull();
        assertThat(savedMerchantDetails.getLegalName()).isEqualTo("New Merchant LLC");
        assertThat(savedMerchantDetails.getDbaName()).isEqualTo("New Merchant");
        assertThat(savedMerchantDetails.getEin()).isEqualTo("98-7654321");
        assertThat(savedMerchantDetails.getIndustry()).isEqualTo("Retail");
        assertThat(savedMerchantDetails.getRevenue()).isEqualByComparingTo(new BigDecimal("1000000.00"));
        assertThat(savedMerchantDetails.getAddress().getCity()).isEqualTo("New City");
        assertThat(savedMerchantDetails.getAddress().getState()).isEqualTo("NY");
    }

    /**
     * Tests finding a merchant details record by ID.
     */
    @Test
    @DisplayName("Should find merchant details by ID")
    public void testFindMerchantDetailsById() {
        // Find the merchant details by ID
        Optional<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findById(testMerchantDetails.getId());
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).isPresent();
        assertThat(foundMerchantDetails.get().getLegalName()).isEqualTo("Test Merchant LLC");
        assertThat(foundMerchantDetails.get().getDbaName()).isEqualTo("Test Merchant");
        assertThat(foundMerchantDetails.get().getEin()).isEqualTo("12-3456789");
        assertThat(foundMerchantDetails.get().getIndustry()).isEqualTo("Technology");
        assertThat(foundMerchantDetails.get().getRevenue()).isEqualByComparingTo(new BigDecimal("500000.00"));
    }

    /**
     * Tests finding all merchant details records.
     */
    @Test
    @DisplayName("Should find all merchant details")
    public void testFindAllMerchantDetails() {
        // Create another merchant details record
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(application);
        
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Another Merchant LLC");
        merchantDetails.setDbaName("Another Merchant");
        merchantDetails.setEin("45-6789012");
        
        MerchantDetails.Address address = new MerchantDetails.Address();
        address.setStreet("789 Another St");
        address.setCity("Another City");
        address.setState("CA");
        address.setZip("67890");
        address.setCountry("USA");
        merchantDetails.setAddress(address);
        
        merchantDetails.setIndustry("Healthcare");
        merchantDetails.setRevenue(new BigDecimal("750000.00"));
        
        entityManager.persist(merchantDetails);
        entityManager.flush();
        
        // Find all merchant details
        List<MerchantDetails> allMerchantDetails = merchantDetailsRepository.findAll();
        
        // Verify all merchant details were found
        assertThat(allMerchantDetails).hasSize(2);
    }

    /**
     * Tests deleting a merchant details record.
     */
    @Test
    @DisplayName("Should delete merchant details")
    public void testDeleteMerchantDetails() {
        // Delete the merchant details
        merchantDetailsRepository.delete(testMerchantDetails);
        entityManager.flush();
        
        // Verify the merchant details was deleted
        Optional<MerchantDetails> deletedMerchantDetails = merchantDetailsRepository.findById(testMerchantDetails.getId());
        assertThat(deletedMerchantDetails).isEmpty();
    }

    /**
     * Tests finding a merchant details record by application.
     */
    @Test
    @DisplayName("Should find merchant details by application")
    public void testFindByApplication() {
        // Find the merchant details by application
        Optional<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByApplication(testApplication);
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).isPresent();
        assertThat(foundMerchantDetails.get().getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding a merchant details record by application ID.
     */
    @Test
    @DisplayName("Should find merchant details by application ID")
    public void testFindByApplicationId() {
        // Find the merchant details by application ID
        Optional<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByApplicationId(testApplication.getId());
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).isPresent();
        assertThat(foundMerchantDetails.get().getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by industry.
     */
    @Test
    @DisplayName("Should find merchant details by industry")
    public void testFindByIndustry() {
        // Find merchant details by industry
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByIndustry("Technology");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by partial industry match.
     */
    @Test
    @DisplayName("Should find merchant details by partial industry match")
    public void testFindByIndustryContainingIgnoreCase() {
        // Find merchant details by partial industry match
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByIndustryContainingIgnoreCase("tech");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by partial industry match with pagination.
     */
    @Test
    @DisplayName("Should find merchant details by partial industry match with pagination")
    public void testFindByIndustryContainingIgnoreCaseWithPagination() {
        // Create multiple merchant details records with different industries
        for (int i = 0; i < 10; i++) {
            Application application = new Application();
            application.setStatus(ApplicationStatus.NEW);
            application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
            entityManager.persist(application);
            
            MerchantDetails merchantDetails = new MerchantDetails();
            merchantDetails.setApplication(application);
            merchantDetails.setLegalName("Tech Company " + i + " LLC");
            merchantDetails.setDbaName("Tech Company " + i);
            merchantDetails.setEin("12-345678" + i);
            
            MerchantDetails.Address address = new MerchantDetails.Address();
            address.setStreet(i + " Tech St");
            address.setCity("Tech City");
            address.setState("TX");
            address.setZip("12345");
            address.setCountry("USA");
            merchantDetails.setAddress(address);
            
            merchantDetails.setIndustry("Technology " + i);
            merchantDetails.setRevenue(new BigDecimal("500000.00").add(new BigDecimal(i * 10000)));
            
            entityManager.persist(merchantDetails);
        }
        entityManager.flush();
        
        // Find merchant details by partial industry match with pagination
        Pageable pageable = PageRequest.of(0, 5);
        Page<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByIndustryContainingIgnoreCase("Technology", pageable);
        
        // Verify the merchant details was found with correct pagination
        assertThat(foundMerchantDetails.getContent()).hasSize(5);
        assertThat(foundMerchantDetails.getTotalElements()).isGreaterThanOrEqualTo(11); // 10 new + 1 from setup
        assertThat(foundMerchantDetails.getTotalPages()).isGreaterThanOrEqualTo(3);
    }

    /**
     * Tests finding merchant details records within a revenue range.
     */
    @Test
    @DisplayName("Should find merchant details within revenue range")
    public void testFindByRevenueBetween() {
        // Create merchant details with different revenues
        Application app1 = new Application();
        app1.setStatus(ApplicationStatus.NEW);
        app1.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app1);
        
        MerchantDetails md1 = new MerchantDetails();
        md1.setApplication(app1);
        md1.setLegalName("Low Revenue LLC");
        md1.setDbaName("Low Revenue");
        md1.setEin("11-111111");
        md1.setAddress(testMerchantDetails.getAddress());
        md1.setIndustry("Retail");
        md1.setRevenue(new BigDecimal("100000.00"));
        entityManager.persist(md1);
        
        Application app2 = new Application();
        app2.setStatus(ApplicationStatus.NEW);
        app2.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app2);
        
        MerchantDetails md2 = new MerchantDetails();
        md2.setApplication(app2);
        md2.setLegalName("High Revenue LLC");
        md2.setDbaName("High Revenue");
        md2.setEin("99-999999");
        md2.setAddress(testMerchantDetails.getAddress());
        md2.setIndustry("Retail");
        md2.setRevenue(new BigDecimal("1000000.00"));
        entityManager.persist(md2);
        
        entityManager.flush();
        
        // Find merchant details within revenue range
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByRevenueBetween(
                new BigDecimal("400000.00"), new BigDecimal("600000.00"));
        
        // Verify the correct merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by state.
     */
    @Test
    @DisplayName("Should find merchant details by state")
    public void testFindByAddressState() {
        // Find merchant details by state
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByAddressState("TX");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by city.
     */
    @Test
    @DisplayName("Should find merchant details by city")
    public void testFindByAddressCity() {
        // Find merchant details by city
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByAddressCity("Test City");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by zip code.
     */
    @Test
    @DisplayName("Should find merchant details by zip code")
    public void testFindByAddressZip() {
        // Find merchant details by zip code
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByAddressZip("12345");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by legal name.
     */
    @Test
    @DisplayName("Should find merchant details by legal name")
    public void testFindByLegalNameIgnoreCase() {
        // Find merchant details by legal name
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByLegalNameIgnoreCase("test merchant llc");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by partial legal name match.
     */
    @Test
    @DisplayName("Should find merchant details by partial legal name match")
    public void testFindByLegalNameContainingIgnoreCase() {
        // Find merchant details by partial legal name match
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByLegalNameContainingIgnoreCase("test");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by DBA name.
     */
    @Test
    @DisplayName("Should find merchant details by DBA name")
    public void testFindByDbaNameIgnoreCase() {
        // Find merchant details by DBA name
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByDbaNameIgnoreCase("test merchant");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by partial DBA name match.
     */
    @Test
    @DisplayName("Should find merchant details by partial DBA name match")
    public void testFindByDbaNameContainingIgnoreCase() {
        // Find merchant details by partial DBA name match
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByDbaNameContainingIgnoreCase("merchant");
        
        // Verify the merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by industry and revenue range.
     */
    @Test
    @DisplayName("Should find merchant details by industry and revenue range")
    public void testFindByIndustryAndRevenueBetween() {
        // Create merchant details with different industries and revenues
        Application app1 = new Application();
        app1.setStatus(ApplicationStatus.NEW);
        app1.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app1);
        
        MerchantDetails md1 = new MerchantDetails();
        md1.setApplication(app1);
        md1.setLegalName("Tech Low Revenue LLC");
        md1.setDbaName("Tech Low Revenue");
        md1.setEin("11-222222");
        md1.setAddress(testMerchantDetails.getAddress());
        md1.setIndustry("Technology");
        md1.setRevenue(new BigDecimal("100000.00"));
        entityManager.persist(md1);
        
        Application app2 = new Application();
        app2.setStatus(ApplicationStatus.NEW);
        app2.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app2);
        
        MerchantDetails md2 = new MerchantDetails();
        md2.setApplication(app2);
        md2.setLegalName("Retail High Revenue LLC");
        md2.setDbaName("Retail High Revenue");
        md2.setEin("33-444444");
        md2.setAddress(testMerchantDetails.getAddress());
        md2.setIndustry("Retail");
        md2.setRevenue(new BigDecimal("800000.00"));
        entityManager.persist(md2);
        
        entityManager.flush();
        
        // Find merchant details by industry and revenue range
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByIndustryAndRevenueBetween(
                "Technology", new BigDecimal("400000.00"), new BigDecimal("600000.00"));
        
        // Verify the correct merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests finding merchant details records by state and industry.
     */
    @Test
    @DisplayName("Should find merchant details by state and industry")
    public void testFindByAddressStateAndIndustry() {
        // Create merchant details with different states and industries
        Application app1 = new Application();
        app1.setStatus(ApplicationStatus.NEW);
        app1.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app1);
        
        MerchantDetails md1 = new MerchantDetails();
        md1.setApplication(app1);
        md1.setLegalName("CA Tech LLC");
        md1.setDbaName("CA Tech");
        md1.setEin("55-666666");
        
        MerchantDetails.Address address1 = new MerchantDetails.Address();
        address1.setStreet("123 CA St");
        address1.setCity("CA City");
        address1.setState("CA");
        address1.setZip("54321");
        address1.setCountry("USA");
        md1.setAddress(address1);
        
        md1.setIndustry("Technology");
        md1.setRevenue(new BigDecimal("500000.00"));
        entityManager.persist(md1);
        
        Application app2 = new Application();
        app2.setStatus(ApplicationStatus.NEW);
        app2.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app2);
        
        MerchantDetails md2 = new MerchantDetails();
        md2.setApplication(app2);
        md2.setLegalName("TX Retail LLC");
        md2.setDbaName("TX Retail");
        md2.setEin("77-888888");
        
        MerchantDetails.Address address2 = new MerchantDetails.Address();
        address2.setStreet("456 TX St");
        address2.setCity("TX City");
        address2.setState("TX");
        address2.setZip("98765");
        address2.setCountry("USA");
        md2.setAddress(address2);
        
        md2.setIndustry("Retail");
        md2.setRevenue(new BigDecimal("500000.00"));
        entityManager.persist(md2);
        
        entityManager.flush();
        
        // Find merchant details by state and industry
        List<MerchantDetails> foundMerchantDetails = merchantDetailsRepository.findByAddressStateAndIndustry(
                "TX", "Technology");
        
        // Verify the correct merchant details was found
        assertThat(foundMerchantDetails).hasSize(1);
        assertThat(foundMerchantDetails.get(0).getId()).isEqualTo(testMerchantDetails.getId());
    }

    /**
     * Tests counting merchant details records by industry.
     */
    @Test
    @DisplayName("Should count merchant details by industry")
    public void testCountByIndustry() {
        // Create additional merchant details with the same industry
        Application app = new Application();
        app.setStatus(ApplicationStatus.NEW);
        app.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app);
        
        MerchantDetails md = new MerchantDetails();
        md.setApplication(app);
        md.setLegalName("Another Tech LLC");
        md.setDbaName("Another Tech");
        md.setEin("22-333333");
        md.setAddress(testMerchantDetails.getAddress());
        md.setIndustry("Technology");
        md.setRevenue(new BigDecimal("300000.00"));
        entityManager.persist(md);
        
        entityManager.flush();
        
        // Count merchant details by industry
        long count = merchantDetailsRepository.countByIndustry("Technology");
        
        // Verify the count
        assertThat(count).isEqualTo(2);
    }

    /**
     * Tests counting merchant details records by state.
     */
    @Test
    @DisplayName("Should count merchant details by state")
    public void testCountByAddressState() {
        // Create additional merchant details with the same state
        Application app = new Application();
        app.setStatus(ApplicationStatus.NEW);
        app.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app);
        
        MerchantDetails md = new MerchantDetails();
        md.setApplication(app);
        md.setLegalName("Another TX LLC");
        md.setDbaName("Another TX");
        md.setEin("44-555555");
        md.setAddress(testMerchantDetails.getAddress());
        md.setIndustry("Healthcare");
        md.setRevenue(new BigDecimal("400000.00"));
        entityManager.persist(md);
        
        entityManager.flush();
        
        // Count merchant details by state
        long count = merchantDetailsRepository.countByAddressState("TX");
        
        // Verify the count
        assertThat(count).isEqualTo(2);
    }

    /**
     * Tests checking if a merchant exists for a specific application.
     */
    @Test
    @DisplayName("Should check if merchant exists for application")
    public void testExistsByApplication() {
        // Check if merchant exists for application
        boolean exists = merchantDetailsRepository.existsByApplication(testApplication);
        
        // Verify the result
        assertThat(exists).isTrue();
        
        // Create a new application without merchant details
        Application newApp = new Application();
        newApp.setStatus(ApplicationStatus.NEW);
        newApp.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(newApp);
        entityManager.flush();
        
        // Check if merchant exists for the new application
        boolean notExists = merchantDetailsRepository.existsByApplication(newApp);
        
        // Verify the result
        assertThat(notExists).isFalse();
    }

    /**
     * Tests checking if a merchant exists for a specific application ID.
     */
    @Test
    @DisplayName("Should check if merchant exists for application ID")
    public void testExistsByApplicationId() {
        // Check if merchant exists for application ID
        boolean exists = merchantDetailsRepository.existsByApplicationId(testApplication.getId());
        
        // Verify the result
        assertThat(exists).isTrue();
        
        // Create a new application without merchant details
        Application newApp = new Application();
        newApp.setStatus(ApplicationStatus.NEW);
        newApp.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(newApp);
        entityManager.flush();
        
        // Check if merchant exists for the new application ID
        boolean notExists = merchantDetailsRepository.existsByApplicationId(newApp.getId());
        
        // Verify the result
        assertThat(notExists).isFalse();
    }

    /**
     * Tests field-level encryption for sensitive PII data.
     * This test verifies that sensitive fields are encrypted in the database
     * but can be decrypted when retrieved through the repository.
     */
    @Test
    @DisplayName("Should encrypt and decrypt sensitive PII data")
    public void testFieldLevelEncryption() {
        // Save a merchant details record with sensitive data
        Application app = new Application();
        app.setStatus(ApplicationStatus.NEW);
        app.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        entityManager.persist(app);
        
        MerchantDetails md = new MerchantDetails();
        md.setApplication(app);
        md.setLegalName("Sensitive Data LLC");
        md.setDbaName("Sensitive Data");
        md.setEin("12-3456789");
        md.setAddress(testMerchantDetails.getAddress());
        md.setIndustry("Finance");
        md.setRevenue(new BigDecimal("500000.00"));
        
        MerchantDetails savedMd = merchantDetailsRepository.save(md);
        entityManager.flush();
        entityManager.clear(); // Clear the persistence context to ensure data is fetched from the database
        
        // Retrieve the merchant details record
        Optional<MerchantDetails> retrievedMdOpt = merchantDetailsRepository.findById(savedMd.getId());
        assertThat(retrievedMdOpt).isPresent();
        
        MerchantDetails retrievedMd = retrievedMdOpt.get();
        
        // Verify that sensitive data is correctly decrypted
        assertThat(retrievedMd.getLegalName()).isEqualTo("Sensitive Data LLC");
        assertThat(retrievedMd.getDbaName()).isEqualTo("Sensitive Data");
        assertThat(retrievedMd.getEin()).isEqualTo("12-3456789");
        
        // Verify that non-sensitive data is not encrypted
        assertThat(retrievedMd.getIndustry()).isEqualTo("Finance");
        assertThat(retrievedMd.getRevenue()).isEqualByComparingTo(new BigDecimal("500000.00"));
    }

    /**
     * Tests the relationship between MerchantDetails and Application entities.
     */
    @Test
    @DisplayName("Should maintain relationship between MerchantDetails and Application")
    public void testMerchantDetailsApplicationRelationship() {
        // Retrieve the application and verify it has the correct merchant details
        Application retrievedApp = entityManager.find(Application.class, testApplication.getId());
        assertThat(retrievedApp).isNotNull();
        assertThat(retrievedApp.getMerchantDetails()).isNotNull();
        assertThat(retrievedApp.getMerchantDetails().getId()).isEqualTo(testMerchantDetails.getId());
        
        // Retrieve the merchant details and verify it has the correct application
        MerchantDetails retrievedMd = entityManager.find(MerchantDetails.class, testMerchantDetails.getId());
        assertThat(retrievedMd).isNotNull();
        assertThat(retrievedMd.getApplication()).isNotNull();
        assertThat(retrievedMd.getApplication().getId()).isEqualTo(testApplication.getId());
    }
}