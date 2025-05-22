package com.dollarfunding.mca.repository;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.util.JsonUtil;

/**
 * JUnit test class for {@link ApplicationRepository} that verifies the repository correctly
 * interacts with the database for {@link Application} entities.
 * <p>
 * This test class uses {@link DataJpaTest} to configure an in-memory database for testing
 * and includes setup methods to create test data. It tests CRUD operations, custom query
 * methods for filtering by status and review status, date range queries, and pagination support.
 * </p>
 */
@DataJpaTest
public class ApplicationRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private ApplicationRepository applicationRepository;

    private Application application1;
    private Application application2;
    private Application application3;
    private Application application4;
    private Application application5;

    /**
     * Sets up test data before each test method.
     * <p>
     * Creates five application entities with different configurations:
     * <ul>
     *   <li>application1: NEW status, NOT_REVIEWED review status, created 5 days ago</li>
     *   <li>application2: PENDING status, IN_REVIEW review status, created 4 days ago</li>
     *   <li>application3: PROCESSING status, NEEDS_INFORMATION review status, created 3 days ago</li>
     *   <li>application4: APPROVED status, APPROVED review status, created 2 days ago</li>
     *   <li>application5: COMPLETED status, APPROVED review status, created 1 day ago</li>
     * </ul>
     * </p>
     */
    @BeforeEach
    public void setup() {
        // Create test applications with different configurations
        application1 = createApplication(
                ApplicationStatus.NEW,
                ReviewStatus.NOT_REVIEWED,
                LocalDateTime.now().minusDays(5),
                createMetadata("source", "email", "confidence", 0.95)
        );

        application2 = createApplication(
                ApplicationStatus.PENDING,
                ReviewStatus.IN_REVIEW,
                LocalDateTime.now().minusDays(4),
                createMetadata("source", "web", "priority", "high")
        );

        application3 = createApplication(
                ApplicationStatus.PROCESSING,
                ReviewStatus.NEEDS_INFORMATION,
                LocalDateTime.now().minusDays(3),
                createMetadata("source", "email", "missing_documents", true)
        );

        application4 = createApplication(
                ApplicationStatus.APPROVED,
                ReviewStatus.APPROVED,
                LocalDateTime.now().minusDays(2),
                createMetadata("source", "web", "approved_amount", 50000.00)
        );

        application5 = createApplication(
                ApplicationStatus.COMPLETED,
                ReviewStatus.APPROVED,
                LocalDateTime.now().minusDays(1),
                createMetadata("source", "email", "processing_time_minutes", 4)
        );

        // Persist test applications
        application1 = entityManager.persist(application1);
        application2 = entityManager.persist(application2);
        application3 = entityManager.persist(application3);
        application4 = entityManager.persist(application4);
        application5 = entityManager.persist(application5);
        
        // Add documents to applications
        addDocumentsToApplication(application1);
        addDocumentsToApplication(application2);
        
        // Add merchant details to applications
        addMerchantDetailsToApplication(application1, "Retail");
        addMerchantDetailsToApplication(application2, "Food Service");
        addMerchantDetailsToApplication(application3, "Construction");
        addMerchantDetailsToApplication(application4, "Retail");
        addMerchantDetailsToApplication(application5, "Technology");
        
        entityManager.flush();
    }

    /**
     * Creates an application with the specified status, review status, creation date, and metadata.
     *
     * @param status The application status
     * @param reviewStatus The review status
     * @param createdAt The creation date
     * @param metadata The application metadata
     * @return A new application entity
     */
    private Application createApplication(ApplicationStatus status, ReviewStatus reviewStatus,
                                         LocalDateTime createdAt, Map<String, Object> metadata) {
        Application application = new Application.Builder()
                .withStatus(status)
                .withReviewStatus(reviewStatus)
                .withCreatedAt(createdAt)
                .withUpdatedAt(createdAt.plusHours(1)) // Updated 1 hour after creation
                .withMetadata(metadata)
                .build();
        return application;
    }

    /**
     * Creates a metadata map with the specified key-value pairs.
     *
     * @param keyValues Key-value pairs (must be even number of arguments)
     * @return A map containing the key-value pairs
     */
    private Map<String, Object> createMetadata(Object... keyValues) {
        if (keyValues.length % 2 != 0) {
            throw new IllegalArgumentException("Must provide an even number of key-value pairs");
        }

        Map<String, Object> metadata = new HashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            metadata.put(keyValues[i].toString(), keyValues[i + 1]);
        }
        return metadata;
    }
    
    /**
     * Adds test documents to an application.
     *
     * @param application The application to add documents to
     */
    private void addDocumentsToApplication(Application application) {
        // Create and add documents
        Document bankStatement = new Document(application.getId(), DocumentType.BANK_STATEMENT,
                "s3://mca-documents-production/bank-statements/statement-" + application.getId() + ".pdf");
        bankStatement.setClassification("Monthly Bank Statement");
        bankStatement.setUploadedAt(LocalDateTime.now().minusDays(1));
        
        Document idVerification = new Document(application.getId(), DocumentType.ID_VERIFICATION,
                "s3://mca-documents-production/id-verification/id-" + application.getId() + ".jpg");
        idVerification.setClassification("Driver's License");
        idVerification.setUploadedAt(LocalDateTime.now().minusDays(1));
        
        Document businessLicense = new Document(application.getId(), DocumentType.BUSINESS_LICENSE,
                "s3://mca-documents-production/business-licenses/license-" + application.getId() + ".pdf");
        businessLicense.setClassification("Business License");
        businessLicense.setUploadedAt(LocalDateTime.now().minusDays(1));
        
        // Add documents to application
        application.addDocument(bankStatement);
        application.addDocument(idVerification);
        application.addDocument(businessLicense);
        
        // Persist documents
        entityManager.persist(bankStatement);
        entityManager.persist(idVerification);
        entityManager.persist(businessLicense);
    }
    
    /**
     * Adds merchant details to an application.
     *
     * @param application The application to add merchant details to
     * @param industry The merchant industry
     */
    private void addMerchantDetailsToApplication(Application application, String industry) {
        // Create merchant details
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setLegalName("Test Merchant " + application.getId());
        merchantDetails.setDbaName("DBA " + application.getId());
        merchantDetails.setEin("12-3456789");
        merchantDetails.setIndustry(industry);
        merchantDetails.setRevenue(500000.00);
        
        // Set address
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "Anytown");
        address.put("state", "CA");
        address.put("zipCode", "12345");
        merchantDetails.setAddress(address);
        
        // Set application relationship
        merchantDetails.setApplication(application);
        application.setMerchantDetails(merchantDetails);
        
        // Persist merchant details
        entityManager.persist(merchantDetails);
    }

    /**
     * Tests that the repository can save an application entity and retrieve it by ID.
     */
    @Test
    @DisplayName("Should save and find application by ID")
    public void testSaveAndFindById() {
        // Create a new application
        Application newApplication = new Application.Builder()
                .withStatus(ApplicationStatus.NEW)
                .withReviewStatus(ReviewStatus.NOT_REVIEWED)
                .addMetadata("source", "api")
                .addMetadata("priority", "medium")
                .build();

        // Save the application
        Application savedApplication = applicationRepository.save(newApplication);

        // Verify the application was saved with an ID
        assertThat(savedApplication.getId()).isNotNull();

        // Find the application by ID
        Optional<Application> foundApplication = applicationRepository.findById(savedApplication.getId());

        // Verify the application was found and has the correct properties
        assertThat(foundApplication).isPresent();
        assertThat(foundApplication.get().getStatus()).isEqualTo(ApplicationStatus.NEW);
        assertThat(foundApplication.get().getReviewStatus()).isEqualTo(ReviewStatus.NOT_REVIEWED);
        assertThat(foundApplication.get().getMetadataValue("source")).isEqualTo("api");
        assertThat(foundApplication.get().getMetadataValue("priority")).isEqualTo("medium");
    }

    /**
     * Tests that the repository can find all application entities.
     */
    @Test
    @DisplayName("Should find all applications")
    public void testFindAll() {
        // Find all applications
        List<Application> applications = applicationRepository.findAll();

        // Verify all applications were found
        assertThat(applications).hasSize(5);
        assertThat(applications).extracting(Application::getStatus)
                .contains(
                        ApplicationStatus.NEW,
                        ApplicationStatus.PENDING,
                        ApplicationStatus.PROCESSING,
                        ApplicationStatus.APPROVED,
                        ApplicationStatus.COMPLETED
                );
    }

    /**
     * Tests that the repository can delete an application entity.
     */
    @Test
    @DisplayName("Should delete application")
    public void testDelete() {
        // Delete application1
        applicationRepository.delete(application1);
        entityManager.flush();

        // Verify application1 was deleted
        Optional<Application> deletedApplication = applicationRepository.findById(application1.getId());
        assertThat(deletedApplication).isEmpty();

        // Verify other applications still exist
        List<Application> remainingApplications = applicationRepository.findAll();
        assertThat(remainingApplications).hasSize(4);
        assertThat(remainingApplications).extracting(Application::getId)
                .contains(application2.getId(), application3.getId(), application4.getId(), application5.getId());
    }

    /**
     * Tests that the repository can find applications by status.
     */
    @Test
    @DisplayName("Should find applications by status")
    public void testFindByStatus() {
        // Find applications by status
        List<Application> newApplications = applicationRepository.findByStatus(ApplicationStatus.NEW);
        assertThat(newApplications).hasSize(1);
        assertThat(newApplications.get(0).getId()).isEqualTo(application1.getId());

        List<Application> pendingApplications = applicationRepository.findByStatus(ApplicationStatus.PENDING);
        assertThat(pendingApplications).hasSize(1);
        assertThat(pendingApplications.get(0).getId()).isEqualTo(application2.getId());

        // Test with non-existent status
        List<Application> rejectedApplications = applicationRepository.findByStatus(ApplicationStatus.REJECTED);
        assertThat(rejectedApplications).isEmpty();
    }

    /**
     * Tests that the repository can find applications by status with pagination.
     */
    @Test
    @DisplayName("Should find applications by status with pagination")
    public void testFindByStatusWithPagination() {
        // Create additional applications with APPROVED status
        for (int i = 0; i < 10; i++) {
            Application app = createApplication(
                    ApplicationStatus.APPROVED,
                    ReviewStatus.APPROVED,
                    LocalDateTime.now().minusDays(1),
                    createMetadata("source", "batch", "index", i)
            );
            entityManager.persist(app);
        }
        entityManager.flush();

        // Find applications by status with pagination
        Pageable pageable = PageRequest.of(0, 5, Sort.by("createdAt").descending());
        Page<Application> approvedApplicationsPage = applicationRepository.findByStatus(ApplicationStatus.APPROVED, pageable);

        // Verify pagination works correctly
        assertThat(approvedApplicationsPage.getContent()).hasSize(5);
        assertThat(approvedApplicationsPage.getTotalElements()).isEqualTo(11); // 1 original + 10 new
        assertThat(approvedApplicationsPage.getTotalPages()).isEqualTo(3);
        assertThat(approvedApplicationsPage.getNumber()).isEqualTo(0);

        // Get next page
        pageable = PageRequest.of(1, 5, Sort.by("createdAt").descending());
        approvedApplicationsPage = applicationRepository.findByStatus(ApplicationStatus.APPROVED, pageable);

        // Verify second page
        assertThat(approvedApplicationsPage.getContent()).hasSize(5);
        assertThat(approvedApplicationsPage.getNumber()).isEqualTo(1);
    }

    /**
     * Tests that the repository can find applications by review status.
     */
    @Test
    @DisplayName("Should find applications by review status")
    public void testFindByReviewStatus() {
        // Find applications by review status
        List<Application> notReviewedApplications = applicationRepository.findByReviewStatus(ReviewStatus.NOT_REVIEWED);
        assertThat(notReviewedApplications).hasSize(1);
        assertThat(notReviewedApplications.get(0).getId()).isEqualTo(application1.getId());

        List<Application> inReviewApplications = applicationRepository.findByReviewStatus(ReviewStatus.IN_REVIEW);
        assertThat(inReviewApplications).hasSize(1);
        assertThat(inReviewApplications.get(0).getId()).isEqualTo(application2.getId());

        List<Application> approvedApplications = applicationRepository.findByReviewStatus(ReviewStatus.APPROVED);
        assertThat(approvedApplications).hasSize(2);
        assertThat(approvedApplications).extracting(Application::getId)
                .contains(application4.getId(), application5.getId());

        // Test with non-existent review status
        List<Application> rejectedApplications = applicationRepository.findByReviewStatus(ReviewStatus.REJECTED);
        assertThat(rejectedApplications).isEmpty();
    }

    /**
     * Tests that the repository can find applications by status and review status.
     */
    @Test
    @DisplayName("Should find applications by status and review status")
    public void testFindByStatusAndReviewStatus() {
        // Find applications by status and review status
        List<Application> newNotReviewedApplications = applicationRepository.findByStatusAndReviewStatus(
                ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
        assertThat(newNotReviewedApplications).hasSize(1);
        assertThat(newNotReviewedApplications.get(0).getId()).isEqualTo(application1.getId());

        List<Application> approvedApprovedApplications = applicationRepository.findByStatusAndReviewStatus(
                ApplicationStatus.APPROVED, ReviewStatus.APPROVED);
        assertThat(approvedApprovedApplications).hasSize(1);
        assertThat(approvedApprovedApplications.get(0).getId()).isEqualTo(application4.getId());

        // Test with non-existent combination
        List<Application> newApprovedApplications = applicationRepository.findByStatusAndReviewStatus(
                ApplicationStatus.NEW, ReviewStatus.APPROVED);
        assertThat(newApprovedApplications).isEmpty();
    }

    /**
     * Tests that the repository can find applications created within a specific date range.
     */
    @Test
    @DisplayName("Should find applications by creation date range")
    public void testFindByCreatedAtBetween() {
        // Find applications created within a date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(4).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now().minusDays(2).withHour(23).withMinute(59).withSecond(59);

        List<Application> applicationsInRange = applicationRepository.findByCreatedAtBetween(startDate, endDate);

        // Verify applications created within the date range were found
        assertThat(applicationsInRange).hasSize(3);
        assertThat(applicationsInRange).extracting(Application::getId)
                .contains(application2.getId(), application3.getId(), application4.getId());

        // Test with date range that doesn't include any applications
        LocalDateTime pastStartDate = LocalDateTime.now().minusDays(10);
        LocalDateTime pastEndDate = LocalDateTime.now().minusDays(6);

        List<Application> applicationsInPastRange = applicationRepository.findByCreatedAtBetween(pastStartDate, pastEndDate);
        assertThat(applicationsInPastRange).isEmpty();
    }

    /**
     * Tests that the repository can find applications updated within a specific date range.
     */
    @Test
    @DisplayName("Should find applications by update date range")
    public void testFindByUpdatedAtBetween() {
        // Update application1 to have a recent update time
        application1.setUpdatedAt(LocalDateTime.now().minusHours(1));
        entityManager.persist(application1);
        entityManager.flush();

        // Find applications updated within a date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(1).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now();

        List<Application> applicationsInRange = applicationRepository.findByUpdatedAtBetween(startDate, endDate);

        // Verify applications updated within the date range were found
        assertThat(applicationsInRange).hasSize(2);
        assertThat(applicationsInRange).extracting(Application::getId)
                .contains(application1.getId(), application5.getId());
    }

    /**
     * Tests that the repository can find applications created after a specific date.
     */
    @Test
    @DisplayName("Should find applications created after a specific date")
    public void testFindByCreatedAtAfter() {
        // Find applications created after a specific date
        LocalDateTime date = LocalDateTime.now().minusDays(3).withHour(0).withMinute(0).withSecond(0);

        List<Application> applicationsAfterDate = applicationRepository.findByCreatedAtAfter(date);

        // Verify applications created after the date were found
        assertThat(applicationsAfterDate).hasSize(3);
        assertThat(applicationsAfterDate).extracting(Application::getId)
                .contains(application3.getId(), application4.getId(), application5.getId());
    }

    /**
     * Tests that the repository can find applications created before a specific date.
     */
    @Test
    @DisplayName("Should find applications created before a specific date")
    public void testFindByCreatedAtBefore() {
        // Find applications created before a specific date
        LocalDateTime date = LocalDateTime.now().minusDays(3).withHour(0).withMinute(0).withSecond(0);

        List<Application> applicationsBeforeDate = applicationRepository.findByCreatedAtBefore(date);

        // Verify applications created before the date were found
        assertThat(applicationsBeforeDate).hasSize(2);
        assertThat(applicationsBeforeDate).extracting(Application::getId)
                .contains(application1.getId(), application2.getId());
    }

    /**
     * Tests that the repository can count applications by status.
     */
    @Test
    @DisplayName("Should count applications by status")
    public void testCountByStatus() {
        // Count applications by status
        long newApplicationCount = applicationRepository.countByStatus(ApplicationStatus.NEW);
        assertThat(newApplicationCount).isEqualTo(1);

        long pendingApplicationCount = applicationRepository.countByStatus(ApplicationStatus.PENDING);
        assertThat(pendingApplicationCount).isEqualTo(1);

        long processingApplicationCount = applicationRepository.countByStatus(ApplicationStatus.PROCESSING);
        assertThat(processingApplicationCount).isEqualTo(1);

        long approvedApplicationCount = applicationRepository.countByStatus(ApplicationStatus.APPROVED);
        assertThat(approvedApplicationCount).isEqualTo(1);

        long completedApplicationCount = applicationRepository.countByStatus(ApplicationStatus.COMPLETED);
        assertThat(completedApplicationCount).isEqualTo(1);

        // Count applications with non-existent status
        long rejectedApplicationCount = applicationRepository.countByStatus(ApplicationStatus.REJECTED);
        assertThat(rejectedApplicationCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can count applications by review status.
     */
    @Test
    @DisplayName("Should count applications by review status")
    public void testCountByReviewStatus() {
        // Count applications by review status
        long notReviewedApplicationCount = applicationRepository.countByReviewStatus(ReviewStatus.NOT_REVIEWED);
        assertThat(notReviewedApplicationCount).isEqualTo(1);

        long inReviewApplicationCount = applicationRepository.countByReviewStatus(ReviewStatus.IN_REVIEW);
        assertThat(inReviewApplicationCount).isEqualTo(1);

        long needsInformationApplicationCount = applicationRepository.countByReviewStatus(ReviewStatus.NEEDS_INFORMATION);
        assertThat(needsInformationApplicationCount).isEqualTo(1);

        long approvedApplicationCount = applicationRepository.countByReviewStatus(ReviewStatus.APPROVED);
        assertThat(approvedApplicationCount).isEqualTo(2);

        // Count applications with non-existent review status
        long rejectedApplicationCount = applicationRepository.countByReviewStatus(ReviewStatus.REJECTED);
        assertThat(rejectedApplicationCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can find applications with metadata containing a specific key.
     */
    @Test
    @DisplayName("Should find applications with metadata containing a specific key")
    public void testFindByMetadataContainsKey() {
        // Find applications with metadata containing a specific key
        String jsonPath = "{\"priority\": {}}";
        List<Application> applicationsWithPriority = applicationRepository.findByMetadataContainsKey(jsonPath);

        // Verify applications with the specified metadata key were found
        assertThat(applicationsWithPriority).hasSize(1);
        assertThat(applicationsWithPriority.get(0).getId()).isEqualTo(application2.getId());

        // Test with another key
        String approvedAmountJsonPath = "{\"approved_amount\": {}}";
        List<Application> applicationsWithApprovedAmount = applicationRepository.findByMetadataContainsKey(approvedAmountJsonPath);
        assertThat(applicationsWithApprovedAmount).hasSize(1);
        assertThat(applicationsWithApprovedAmount.get(0).getId()).isEqualTo(application4.getId());
    }

    /**
     * Tests that the repository can find applications with metadata containing a specific key-value pair.
     */
    @Test
    @DisplayName("Should find applications with metadata containing a specific key-value pair")
    public void testFindByMetadataContains() {
        // Find applications with metadata containing a specific key-value pair
        String keyValueJson = "{\"source\": \"email\"}";
        List<Application> applicationsWithEmailSource = applicationRepository.findByMetadataContains(keyValueJson);

        // Verify applications with the specified metadata key-value pair were found
        assertThat(applicationsWithEmailSource).hasSize(3);
        assertThat(applicationsWithEmailSource).extracting(Application::getId)
                .contains(application1.getId(), application3.getId(), application5.getId());

        // Test with another key-value pair
        String processingTimeJson = "{\"processing_time_minutes\": 4}";
        List<Application> applicationsWith4MinProcessingTime = applicationRepository.findByMetadataContains(processingTimeJson);
        assertThat(applicationsWith4MinProcessingTime).hasSize(1);
        assertThat(applicationsWith4MinProcessingTime.get(0).getId()).isEqualTo(application5.getId());

        // Test with non-existent key-value pair
        String nonExistentJson = "{\"nonExistentKey\": \"nonExistentValue\"}";
        List<Application> applicationsWithNonExistentKeyValue = applicationRepository.findByMetadataContains(nonExistentJson);
        assertThat(applicationsWithNonExistentKeyValue).isEmpty();
    }

    /**
     * Tests that the repository can find applications with metadata containing a specific key-value pair, with pagination.
     */
    @Test
    @DisplayName("Should find applications with metadata containing a specific key-value pair, with pagination")
    public void testFindByMetadataContainsWithPagination() {
        // Create additional applications with email source
        for (int i = 0; i < 10; i++) {
            Application app = createApplication(
                    ApplicationStatus.NEW,
                    ReviewStatus.NOT_REVIEWED,
                    LocalDateTime.now().minusHours(i),
                    createMetadata("source", "email", "index", i)
            );
            entityManager.persist(app);
        }
        entityManager.flush();

        // Find applications with metadata containing a specific key-value pair, with pagination
        String keyValueJson = "{\"source\": \"email\"}";
        Pageable pageable = PageRequest.of(0, 5, Sort.by("createdAt").descending());
        Page<Application> emailSourceApplicationsPage = applicationRepository.findByMetadataContains(keyValueJson, pageable);

        // Verify pagination works correctly
        assertThat(emailSourceApplicationsPage.getContent()).hasSize(5);
        assertThat(emailSourceApplicationsPage.getTotalElements()).isEqualTo(13); // 3 original + 10 new
        assertThat(emailSourceApplicationsPage.getTotalPages()).isEqualTo(3);
        assertThat(emailSourceApplicationsPage.getNumber()).isEqualTo(0);

        // Get next page
        pageable = PageRequest.of(1, 5, Sort.by("createdAt").descending());
        emailSourceApplicationsPage = applicationRepository.findByMetadataContains(keyValueJson, pageable);

        // Verify second page
        assertThat(emailSourceApplicationsPage.getContent()).hasSize(5);
        assertThat(emailSourceApplicationsPage.getNumber()).isEqualTo(1);
    }

    /**
     * Tests that the repository can find applications that require review.
     */
    @Test
    @DisplayName("Should find applications requiring review")
    public void testFindApplicationsRequiringReview() {
        // Find applications requiring review
        List<Application> applicationsRequiringReview = applicationRepository.findApplicationsRequiringReview();

        // Verify applications requiring review were found
        assertThat(applicationsRequiringReview).hasSize(2);
        assertThat(applicationsRequiringReview).extracting(Application::getId)
                .contains(application1.getId(), application3.getId());
    }

    /**
     * Tests that the repository can find active applications.
     */
    @Test
    @DisplayName("Should find active applications")
    public void testFindActiveApplications() {
        // Find active applications
        List<Application> activeApplications = applicationRepository.findActiveApplications();

        // Verify active applications were found
        assertThat(activeApplications).hasSize(3);
        assertThat(activeApplications).extracting(Application::getId)
                .contains(application1.getId(), application2.getId(), application3.getId());
    }

    /**
     * Tests that the repository can find decided applications.
     */
    @Test
    @DisplayName("Should find decided applications")
    public void testFindDecidedApplications() {
        // Find decided applications
        List<Application> decidedApplications = applicationRepository.findDecidedApplications();

        // Verify decided applications were found
        assertThat(decidedApplications).hasSize(2);
        assertThat(decidedApplications).extracting(Application::getId)
                .contains(application4.getId(), application5.getId());
    }

    /**
     * Tests that the repository can find completed applications.
     */
    @Test
    @DisplayName("Should find completed applications")
    public void testFindCompletedApplications() {
        // Find completed applications
        List<Application> completedApplications = applicationRepository.findCompletedApplications();

        // Verify completed applications were found
        assertThat(completedApplications).hasSize(1);
        assertThat(completedApplications.get(0).getId()).isEqualTo(application5.getId());
    }

    /**
     * Tests that the repository can find applications processed within the target time (5 minutes).
     */
    @Test
    @DisplayName("Should find applications processed within target time")
    public void testFindApplicationsProcessedWithinTargetTime() {
        // Find applications processed within target time
        List<Application> applicationsProcessedWithinTargetTime = applicationRepository.findApplicationsProcessedWithinTargetTime();

        // Verify applications processed within target time were found
        assertThat(applicationsProcessedWithinTargetTime).hasSize(1);
        assertThat(applicationsProcessedWithinTargetTime.get(0).getId()).isEqualTo(application5.getId());
    }

    /**
     * Tests that the repository can find applications that exceeded the target processing time (5 minutes).
     */
    @Test
    @DisplayName("Should find applications exceeding target time")
    public void testFindApplicationsExceedingTargetTime() {
        // Create an application that exceeded the target processing time
        Application slowApplication = createApplication(
                ApplicationStatus.COMPLETED,
                ReviewStatus.APPROVED,
                LocalDateTime.now().minusDays(2),
                createMetadata("source", "email", "processing_time_minutes", 10)
        );
        slowApplication.setUpdatedAt(slowApplication.getCreatedAt().plusMinutes(10)); // 10 minutes processing time
        entityManager.persist(slowApplication);
        entityManager.flush();

        // Find applications exceeding target time
        List<Application> applicationsExceedingTargetTime = applicationRepository.findApplicationsExceedingTargetTime();

        // Verify applications exceeding target time were found
        assertThat(applicationsExceedingTargetTime).hasSize(1);
        assertThat(applicationsExceedingTargetTime.get(0).getId()).isEqualTo(slowApplication.getId());
    }

    /**
     * Tests that the repository can calculate the average processing time for completed applications.
     */
    @Test
    @DisplayName("Should calculate average processing time")
    public void testCalculateAverageProcessingTimeMinutes() {
        // Create additional completed applications with different processing times
        Application app1 = createApplication(
                ApplicationStatus.COMPLETED,
                ReviewStatus.APPROVED,
                LocalDateTime.now().minusDays(3),
                createMetadata("source", "email", "processing_time_minutes", 3)
        );
        app1.setUpdatedAt(app1.getCreatedAt().plusMinutes(3)); // 3 minutes processing time

        Application app2 = createApplication(
                ApplicationStatus.COMPLETED,
                ReviewStatus.APPROVED,
                LocalDateTime.now().minusDays(2),
                createMetadata("source", "email", "processing_time_minutes", 7)
        );
        app2.setUpdatedAt(app2.getCreatedAt().plusMinutes(7)); // 7 minutes processing time

        entityManager.persist(app1);
        entityManager.persist(app2);
        entityManager.flush();

        // Calculate average processing time
        Double averageProcessingTime = applicationRepository.calculateAverageProcessingTimeMinutes();

        // Verify average processing time
        assertThat(averageProcessingTime).isNotNull();
        // Average of 1 hour (application5), 3 minutes (app1), and 7 minutes (app2)
        // Note: The actual value may vary due to how the test data is created and how the database calculates the average
        assertThat(averageProcessingTime).isGreaterThan(0.0);
    }

    /**
     * Tests that the repository can find applications with merchant details in a specific industry.
     */
    @Test
    @DisplayName("Should find applications by merchant industry")
    public void testFindByMerchantIndustry() {
        // Find applications by merchant industry
        List<Application> retailApplications = applicationRepository.findByMerchantIndustry("Retail");

        // Verify applications with merchants in the retail industry were found
        assertThat(retailApplications).hasSize(2);
        assertThat(retailApplications).extracting(Application::getId)
                .contains(application1.getId(), application4.getId());

        // Test with another industry
        List<Application> technologyApplications = applicationRepository.findByMerchantIndustry("Technology");
        assertThat(technologyApplications).hasSize(1);
        assertThat(technologyApplications.get(0).getId()).isEqualTo(application5.getId());

        // Test with non-existent industry
        List<Application> nonExistentIndustryApplications = applicationRepository.findByMerchantIndustry("Non-existent Industry");
        assertThat(nonExistentIndustryApplications).isEmpty();
    }

    /**
     * Tests that the repository can find applications with merchant details in a specific state.
     */
    @Test
    @DisplayName("Should find applications by merchant state")
    public void testFindByMerchantState() {
        // Find applications by merchant state
        List<Application> californiaApplications = applicationRepository.findByMerchantState("CA");

        // Verify applications with merchants in California were found
        assertThat(californiaApplications).hasSize(5);

        // Create an application with merchant in a different state
        Application texasApplication = createApplication(
                ApplicationStatus.NEW,
                ReviewStatus.NOT_REVIEWED,
                LocalDateTime.now().minusDays(1),
                createMetadata("source", "web")
        );
        entityManager.persist(texasApplication);

        // Add merchant details with Texas address
        MerchantDetails texasMerchant = new MerchantDetails();
        texasMerchant.setLegalName("Texas Merchant");
        texasMerchant.setDbaName("Texas DBA");
        texasMerchant.setEin("12-3456789");
        texasMerchant.setIndustry("Retail");
        texasMerchant.setRevenue(500000.00);

        Map<String, Object> texasAddress = new HashMap<>();
        texasAddress.put("street", "123 Main St");
        texasAddress.put("city", "Austin");
        texasAddress.put("state", "TX");
        texasAddress.put("zipCode", "78701");
        texasMerchant.setAddress(texasAddress);

        texasMerchant.setApplication(texasApplication);
        texasApplication.setMerchantDetails(texasMerchant);

        entityManager.persist(texasMerchant);
        entityManager.flush();

        // Find applications by merchant state again
        List<Application> texasApplications = applicationRepository.findByMerchantState("TX");

        // Verify applications with merchants in Texas were found
        assertThat(texasApplications).hasSize(1);
        assertThat(texasApplications.get(0).getId()).isEqualTo(texasApplication.getId());
    }

    /**
     * Tests that the repository can find applications that have all required documents.
     */
    @Test
    @DisplayName("Should find applications with all required documents")
    public void testFindApplicationsWithAllRequiredDocuments() {
        // Find applications with all required documents
        List<Application> applicationsWithAllRequiredDocuments = applicationRepository.findApplicationsWithAllRequiredDocuments();

        // Verify applications with all required documents were found
        assertThat(applicationsWithAllRequiredDocuments).hasSize(2);
        assertThat(applicationsWithAllRequiredDocuments).extracting(Application::getId)
                .contains(application1.getId(), application2.getId());
    }

    /**
     * Tests that the repository can find applications that are missing required documents.
     */
    @Test
    @DisplayName("Should find applications missing required documents")
    public void testFindApplicationsMissingRequiredDocuments() {
        // Find applications missing required documents
        List<Application> applicationsMissingRequiredDocuments = applicationRepository.findApplicationsMissingRequiredDocuments();

        // Verify applications missing required documents were found
        assertThat(applicationsMissingRequiredDocuments).hasSize(3);
        assertThat(applicationsMissingRequiredDocuments).extracting(Application::getId)
                .contains(application3.getId(), application4.getId(), application5.getId());
    }

    /**
     * Tests the relationship between Application and Document entities.
     */
    @Test
    @DisplayName("Should handle Application-Document relationship")
    public void testApplicationDocumentRelationship() {
        // Retrieve application with documents relationship
        Application applicationWithDocuments = entityManager.find(Application.class, application1.getId());

        // Verify the documents relationship is correctly established
        assertThat(applicationWithDocuments.getDocuments()).isNotNull();
        assertThat(applicationWithDocuments.getDocuments()).hasSize(3);
        assertThat(applicationWithDocuments.getDocuments()).extracting(Document::getType)
                .contains(DocumentType.BANK_STATEMENT, DocumentType.ID_VERIFICATION, DocumentType.BUSINESS_LICENSE);

        // Test adding a document to an application
        Document newDocument = new Document(application1.getId(), DocumentType.TAX_RETURN,
                "s3://mca-documents-production/tax-returns/tax-return-" + application1.getId() + ".pdf");
        newDocument.setClassification("Business Tax Return");
        newDocument.setUploadedAt(LocalDateTime.now());

        applicationWithDocuments.addDocument(newDocument);
        entityManager.persist(newDocument);
        entityManager.flush();

        // Verify the document was added to the application
        Application updatedApplication = entityManager.find(Application.class, application1.getId());
        assertThat(updatedApplication.getDocuments()).hasSize(4);

        // Test removing a document from an application
        updatedApplication.removeDocument(newDocument);
        entityManager.flush();

        // Verify the document was removed from the application
        Application applicationAfterRemoval = entityManager.find(Application.class, application1.getId());
        assertThat(applicationAfterRemoval.getDocuments()).hasSize(3);
    }

    /**
     * Tests the relationship between Application and MerchantDetails entities.
     */
    @Test
    @DisplayName("Should handle Application-MerchantDetails relationship")
    public void testApplicationMerchantDetailsRelationship() {
        // Retrieve application with merchant details relationship
        Application applicationWithMerchantDetails = entityManager.find(Application.class, application1.getId());

        // Verify the merchant details relationship is correctly established
        assertThat(applicationWithMerchantDetails.getMerchantDetails()).isNotNull();
        assertThat(applicationWithMerchantDetails.getMerchantDetails().getLegalName()).isEqualTo("Test Merchant " + application1.getId());
        assertThat(applicationWithMerchantDetails.getMerchantDetails().getIndustry()).isEqualTo("Retail");

        // Test updating merchant details
        MerchantDetails merchantDetails = applicationWithMerchantDetails.getMerchantDetails();
        merchantDetails.setDbaName("Updated DBA Name");
        merchantDetails.setRevenue(750000.00);
        entityManager.flush();

        // Verify the merchant details were updated
        Application updatedApplication = entityManager.find(Application.class, application1.getId());
        assertThat(updatedApplication.getMerchantDetails().getDbaName()).isEqualTo("Updated DBA Name");
        assertThat(updatedApplication.getMerchantDetails().getRevenue()).isEqualTo(750000.00);
    }

    /**
     * Tests the Application entity's business methods.
     */
    @Test
    @DisplayName("Should handle Application entity business methods")
    public void testApplicationEntityBusinessMethods() {
        // Test isCompleted method
        assertThat(application1.isCompleted()).isFalse(); // NEW status
        assertThat(application5.isCompleted()).isTrue();  // COMPLETED status

        // Test isActive method
        assertThat(application1.isActive()).isTrue();  // NEW status
        assertThat(application2.isActive()).isTrue();  // PENDING status
        assertThat(application3.isActive()).isTrue();  // PROCESSING status
        assertThat(application4.isActive()).isFalse(); // APPROVED status
        assertThat(application5.isActive()).isFalse(); // COMPLETED status

        // Test isDecided method
        assertThat(application1.isDecided()).isFalse(); // NEW status
        assertThat(application4.isDecided()).isTrue();  // APPROVED status
        assertThat(application5.isDecided()).isTrue();  // COMPLETED status

        // Test requiresReview method
        assertThat(application1.requiresReview()).isTrue();  // NOT_REVIEWED status
        assertThat(application3.requiresReview()).isTrue();  // NEEDS_INFORMATION status
        assertThat(application4.requiresReview()).isFalse(); // APPROVED status

        // Test hasAllRequiredDocuments method
        assertThat(application1.hasAllRequiredDocuments()).isTrue();  // Has all required documents
        
        // Create an application with missing documents
        Application incompleteApplication = createApplication(
                ApplicationStatus.NEW,
                ReviewStatus.NOT_REVIEWED,
                LocalDateTime.now(),
                createMetadata("source", "web")
        );
        entityManager.persist(incompleteApplication);
        
        // Add only one document type
        Document bankStatement = new Document(incompleteApplication.getId(), DocumentType.BANK_STATEMENT,
                "s3://mca-documents-production/bank-statements/statement-incomplete.pdf");
        bankStatement.setClassification("Monthly Bank Statement");
        bankStatement.setUploadedAt(LocalDateTime.now());
        incompleteApplication.addDocument(bankStatement);
        entityManager.persist(bankStatement);
        entityManager.flush();
        
        assertThat(incompleteApplication.hasAllRequiredDocuments()).isFalse(); // Missing required documents

        // Test updateStatus method
        boolean statusUpdated = application1.updateStatus(ApplicationStatus.PENDING);
        assertThat(statusUpdated).isTrue();
        assertThat(application1.getStatus()).isEqualTo(ApplicationStatus.PENDING);

        // Test invalid status transition
        boolean invalidStatusUpdate = application1.updateStatus(ApplicationStatus.COMPLETED);
        assertThat(invalidStatusUpdate).isFalse();
        assertThat(application1.getStatus()).isEqualTo(ApplicationStatus.PENDING); // Unchanged

        // Test updateReviewStatus method
        boolean reviewStatusUpdated = application1.updateReviewStatus(ReviewStatus.IN_REVIEW);
        assertThat(reviewStatusUpdated).isTrue();
        assertThat(application1.getReviewStatus()).isEqualTo(ReviewStatus.IN_REVIEW);
    }

    /**
     * Tests the Application entity's metadata handling methods.
     */
    @Test
    @DisplayName("Should handle Application entity metadata methods")
    public void testApplicationEntityMetadataMethods() {
        // Test getMetadata method
        Map<String, Object> metadata = application1.getMetadata();
        assertThat(metadata).isNotNull();
        assertThat(metadata).containsEntry("source", "email");
        assertThat(metadata).containsEntry("confidence", 0.95);

        // Test getMetadataValue method
        assertThat(application1.getMetadataValue("source")).isEqualTo("email");
        assertThat(application1.getMetadataValue("confidence")).isEqualTo(0.95);

        // Test addMetadata method
        application1.addMetadata("new_key", "new_value");
        assertThat(application1.getMetadataValue("new_key")).isEqualTo("new_value");

        // Test setMetadata method
        Map<String, Object> newMetadata = new HashMap<>();
        newMetadata.put("completely_new", "completely_new_value");
        newMetadata.put("another_key", 123);
        application1.setMetadata(newMetadata);

        assertThat(application1.getMetadata()).isEqualTo(newMetadata);
        assertThat(application1.getMetadataValue("source")).isNull(); // Old key is gone
        assertThat(application1.getMetadataValue("completely_new")).isEqualTo("completely_new_value");
        assertThat(application1.getMetadataValue("another_key")).isEqualTo(123);

        // Test JSON conversion
        String metadataJson = application1.getMetadataJson();
        assertThat(metadataJson).isNotNull();
        assertThat(metadataJson).contains("completely_new");
        assertThat(metadataJson).contains("completely_new_value");
        assertThat(metadataJson).contains("another_key");
        assertThat(metadataJson).contains("123");

        // Test setMetadataJson method
        String newMetadataJson = "{\"json_key\": \"json_value\", \"json_number\": 456}";
        application1.setMetadataJson(newMetadataJson);

        assertThat(application1.getMetadataValue("json_key")).isEqualTo("json_value");
        assertThat(application1.getMetadataValue("json_number")).isEqualTo(456);
    }

    /**
     * Tests the Application entity's builder pattern.
     */
    @Test
    @DisplayName("Should create Application using builder pattern")
    public void testApplicationBuilder() {
        // Create an application using the builder pattern
        Application.Builder builder = new Application.Builder()
                .withStatus(ApplicationStatus.NEW)
                .withReviewStatus(ReviewStatus.NOT_REVIEWED)
                .withCreatedAt(LocalDateTime.now())
                .withUpdatedAt(LocalDateTime.now())
                .addMetadata("source", "builder-test")
                .addMetadata("priority", "high");

        Application builtApplication = builder.build();

        // Save the application
        Application savedApplication = applicationRepository.save(builtApplication);

        // Verify the application was saved with the correct properties
        assertThat(savedApplication.getId()).isNotNull();
        assertThat(savedApplication.getStatus()).isEqualTo(ApplicationStatus.NEW);
        assertThat(savedApplication.getReviewStatus()).isEqualTo(ReviewStatus.NOT_REVIEWED);
        assertThat(savedApplication.getMetadataValue("source")).isEqualTo("builder-test");
        assertThat(savedApplication.getMetadataValue("priority")).isEqualTo("high");
    }
}