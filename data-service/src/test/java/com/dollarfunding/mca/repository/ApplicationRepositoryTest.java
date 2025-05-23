package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
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
import org.springframework.data.domain.Sort;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * JUnit test class for ApplicationRepository that verifies the repository correctly
 * interacts with the database for Application entities.
 * 
 * This test class uses @DataJpaTest to configure an in-memory database for testing
 * and includes setup methods to create test data. It tests CRUD operations (save, findById,
 * findAll, delete), custom query methods for filtering by status and review status,
 * date range queries, and pagination support.
 */
@DataJpaTest
public class ApplicationRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private ApplicationRepository applicationRepository;

    private Application newApplication;
    private Application pendingApplication;
    private Application processingApplication;
    private Application completedApplication;
    private Application rejectedApplication;
    private Application fastProcessedApplication;

    /**
     * Set up test data before each test.
     * Creates applications with different statuses, review statuses, and metadata.
     */
    @BeforeEach
    public void setUp() {
        // Create applications with different statuses and review statuses
        newApplication = createApplication(ApplicationStatus.NEW, ReviewStatus.NOT_REVIEWED);
        pendingApplication = createApplication(ApplicationStatus.PENDING, ReviewStatus.IN_REVIEW);
        processingApplication = createApplication(ApplicationStatus.PROCESSING, ReviewStatus.IN_REVIEW);
        completedApplication = createApplication(ApplicationStatus.COMPLETED, ReviewStatus.APPROVED);
        rejectedApplication = createApplication(ApplicationStatus.REJECTED, ReviewStatus.REJECTED);
        
        // Create an application that was processed in under 5 minutes
        fastProcessedApplication = new Application.Builder()
                .withStatus(ApplicationStatus.COMPLETED)
                .withReviewStatus(ReviewStatus.APPROVED)
                .withCreatedAt(LocalDateTime.now().minusMinutes(4))
                .withUpdatedAt(LocalDateTime.now())
                .build();
        
        // Add metadata to applications
        addMetadata(newApplication, "source", "email");
        addMetadata(pendingApplication, "source", "web");
        addMetadata(processingApplication, "confidenceScore", "0.95");
        addMetadata(completedApplication, "processingTimeMs", "240000");
        addMetadata(rejectedApplication, "rejectionReason", "Incomplete documentation");
        addMetadata(fastProcessedApplication, "processingTimeMs", "180000");
        
        // Add documents to some applications
        addDocument(pendingApplication, DocumentType.BANK_STATEMENT);
        addDocument(pendingApplication, DocumentType.TAX_RETURN);
        addDocument(completedApplication, DocumentType.BANK_STATEMENT);
        addDocument(completedApplication, DocumentType.TAX_RETURN);
        addDocument(completedApplication, DocumentType.BUSINESS_LICENSE);
        
        // Add merchant details to some applications
        addMerchantDetails(completedApplication, "ABC Corp", "ABC Coffee Shop", "12-3456789");
        addMerchantDetails(processingApplication, "XYZ Inc", "XYZ Bakery", "98-7654321");
        
        // Persist applications
        entityManager.persist(newApplication);
        entityManager.persist(pendingApplication);
        entityManager.persist(processingApplication);
        entityManager.persist(completedApplication);
        entityManager.persist(rejectedApplication);
        entityManager.persist(fastProcessedApplication);
        entityManager.flush();
    }

    /**
     * Helper method to create an application with the specified status and review status.
     */
    private Application createApplication(ApplicationStatus status, ReviewStatus reviewStatus) {
        return new Application.Builder()
                .withStatus(status)
                .withReviewStatus(reviewStatus)
                .withCreatedAt(LocalDateTime.now().minusDays(1))
                .withUpdatedAt(LocalDateTime.now())
                .build();
    }

    /**
     * Helper method to add metadata to an application.
     */
    private void addMetadata(Application application, String key, String value) {
        application.addMetadata(key, value);
    }

    /**
     * Helper method to add a document to an application.
     */
    private void addDocument(Application application, DocumentType documentType) {
        Document document = new Document();
        document.setType(documentType);
        document.setStoragePath("s3://mca-documents-test/" + UUID.randomUUID() + ".pdf");
        document.setClassification(documentType.name());
        document.setUploadedAt(LocalDateTime.now());
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("fileSize", 1024);
        metadata.put("mimeType", "application/pdf");
        document.setMetadata(metadata);
        application.addDocument(document);
    }

    /**
     * Helper method to add merchant details to an application.
     */
    private void addMerchantDetails(Application application, String legalName, String dbaName, String ein) {
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setLegalName(legalName);
        merchantDetails.setDbaName(dbaName);
        merchantDetails.setEin(ein);
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "New York");
        address.put("state", "NY");
        address.put("zip", "10001");
        merchantDetails.setAddress(address);
        merchantDetails.setIndustry("Retail");
        merchantDetails.setRevenue(1000000.0);
        application.setMerchantDetails(merchantDetails);
    }

    @Test
    @DisplayName("Should save application")
    public void testSaveApplication() {
        // Create a new application
        Application application = new Application.Builder()
                .withStatus(ApplicationStatus.NEW)
                .withReviewStatus(ReviewStatus.NOT_REVIEWED)
                .build();
        
        // Save the application
        Application savedApplication = applicationRepository.save(application);
        
        // Verify the application was saved
        assertThat(savedApplication).isNotNull();
        assertThat(savedApplication.getId()).isNotNull();
        assertThat(savedApplication.getStatus()).isEqualTo(ApplicationStatus.NEW);
        assertThat(savedApplication.getReviewStatus()).isEqualTo(ReviewStatus.NOT_REVIEWED);
    }

    @Test
    @DisplayName("Should find application by ID")
    public void testFindApplicationById() {
        // Find an application by ID
        Optional<Application> foundApplication = applicationRepository.findById(newApplication.getId());
        
        // Verify the application was found
        assertThat(foundApplication).isPresent();
        assertThat(foundApplication.get().getStatus()).isEqualTo(ApplicationStatus.NEW);
        assertThat(foundApplication.get().getReviewStatus()).isEqualTo(ReviewStatus.NOT_REVIEWED);
    }

    @Test
    @DisplayName("Should find all applications")
    public void testFindAllApplications() {
        // Find all applications
        List<Application> applications = applicationRepository.findAll();
        
        // Verify all applications were found
        assertThat(applications).hasSize(6);
    }

    @Test
    @DisplayName("Should delete application")
    public void testDeleteApplication() {
        // Delete an application
        applicationRepository.delete(newApplication);
        
        // Verify the application was deleted
        Optional<Application> deletedApplication = applicationRepository.findById(newApplication.getId());
        assertThat(deletedApplication).isEmpty();
    }

    @Test
    @DisplayName("Should find applications by status")
    public void testFindByStatus() {
        // Find applications by status
        List<Application> newApplications = applicationRepository.findByStatus(ApplicationStatus.NEW);
        List<Application> completedApplications = applicationRepository.findByStatus(ApplicationStatus.COMPLETED);
        
        // Verify the correct applications were found
        assertThat(newApplications).hasSize(1);
        assertThat(newApplications.get(0).getStatus()).isEqualTo(ApplicationStatus.NEW);
        
        assertThat(completedApplications).hasSize(2);
        assertThat(completedApplications).allMatch(app -> app.getStatus() == ApplicationStatus.COMPLETED);
    }

    @Test
    @DisplayName("Should find applications by status with pagination")
    public void testFindByStatusWithPagination() {
        // Create page request
        PageRequest pageRequest = PageRequest.of(0, 1, Sort.by("createdAt").descending());
        
        // Find applications by status with pagination
        Page<Application> completedApplicationsPage = applicationRepository.findByStatus(ApplicationStatus.COMPLETED, pageRequest);
        
        // Verify the correct page was returned
        assertThat(completedApplicationsPage.getTotalElements()).isEqualTo(2);
        assertThat(completedApplicationsPage.getContent()).hasSize(1);
        assertThat(completedApplicationsPage.getTotalPages()).isEqualTo(2);
    }

    @Test
    @DisplayName("Should find applications by review status")
    public void testFindByReviewStatus() {
        // Find applications by review status
        List<Application> inReviewApplications = applicationRepository.findByReviewStatus(ReviewStatus.IN_REVIEW);
        List<Application> approvedApplications = applicationRepository.findByReviewStatus(ReviewStatus.APPROVED);
        
        // Verify the correct applications were found
        assertThat(inReviewApplications).hasSize(2);
        assertThat(inReviewApplications).allMatch(app -> app.getReviewStatus() == ReviewStatus.IN_REVIEW);
        
        assertThat(approvedApplications).hasSize(2);
        assertThat(approvedApplications).allMatch(app -> app.getReviewStatus() == ReviewStatus.APPROVED);
    }

    @Test
    @DisplayName("Should find applications by status and review status")
    public void testFindByStatusAndReviewStatus() {
        // Find applications by status and review status
        List<Application> completedApprovedApplications = applicationRepository.findByStatusAndReviewStatus(
                ApplicationStatus.COMPLETED, ReviewStatus.APPROVED);
        
        // Verify the correct applications were found
        assertThat(completedApprovedApplications).hasSize(2);
        assertThat(completedApprovedApplications).allMatch(app -> 
                app.getStatus() == ApplicationStatus.COMPLETED && 
                app.getReviewStatus() == ReviewStatus.APPROVED);
    }

    @Test
    @DisplayName("Should find applications created within date range")
    public void testFindByCreatedAtBetween() {
        // Define date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(2);
        LocalDateTime endDate = LocalDateTime.now();
        
        // Find applications created within date range
        List<Application> applications = applicationRepository.findByCreatedAtBetween(startDate, endDate);
        
        // Verify the correct applications were found
        assertThat(applications).hasSize(6);
    }

    @Test
    @DisplayName("Should find applications updated within date range")
    public void testFindByUpdatedAtBetween() {
        // Define date range
        LocalDateTime startDate = LocalDateTime.now().minusHours(1);
        LocalDateTime endDate = LocalDateTime.now().plusHours(1);
        
        // Find applications updated within date range
        List<Application> applications = applicationRepository.findByUpdatedAtBetween(startDate, endDate);
        
        // Verify the correct applications were found
        assertThat(applications).hasSize(6);
    }

    @Test
    @DisplayName("Should find applications by status created within date range")
    public void testFindByStatusAndCreatedAtBetween() {
        // Define date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(2);
        LocalDateTime endDate = LocalDateTime.now();
        
        // Find applications by status created within date range
        List<Application> completedApplications = applicationRepository.findByStatusAndCreatedAtBetween(
                ApplicationStatus.COMPLETED, startDate, endDate);
        
        // Verify the correct applications were found
        assertThat(completedApplications).hasSize(2);
        assertThat(completedApplications).allMatch(app -> app.getStatus() == ApplicationStatus.COMPLETED);
    }

    @Test
    @DisplayName("Should find applications by review status created within date range")
    public void testFindByReviewStatusAndCreatedAtBetween() {
        // Define date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(2);
        LocalDateTime endDate = LocalDateTime.now();
        
        // Find applications by review status created within date range
        List<Application> approvedApplications = applicationRepository.findByReviewStatusAndCreatedAtBetween(
                ReviewStatus.APPROVED, startDate, endDate);
        
        // Verify the correct applications were found
        assertThat(approvedApplications).hasSize(2);
        assertThat(approvedApplications).allMatch(app -> app.getReviewStatus() == ReviewStatus.APPROVED);
    }

    @Test
    @DisplayName("Should find applications by metadata key")
    public void testFindByMetadataKey() {
        // Find applications by metadata key
        List<Application> applicationsWithSource = applicationRepository.findByMetadataKey("source");
        
        // Verify the correct applications were found
        assertThat(applicationsWithSource).hasSize(2);
    }

    @Test
    @DisplayName("Should find applications by metadata key-value pair")
    public void testFindByMetadataKeyValue() {
        // Find applications by metadata key-value pair
        List<Application> emailApplications = applicationRepository.findByMetadataKeyValue("source", "email");
        
        // Verify the correct applications were found
        assertThat(emailApplications).hasSize(1);
        assertThat(emailApplications.get(0).getMetadataValue("source")).isEqualTo("email");
    }

    @Test
    @DisplayName("Should find applications by status and metadata key-value pair")
    public void testFindByStatusAndMetadataKeyValue() {
        // Find applications by status and metadata key-value pair
        List<Application> pendingWebApplications = applicationRepository.findByStatusAndMetadataKeyValue(
                ApplicationStatus.PENDING, "source", "web");
        
        // Verify the correct applications were found
        assertThat(pendingWebApplications).hasSize(1);
        assertThat(pendingWebApplications.get(0).getStatus()).isEqualTo(ApplicationStatus.PENDING);
        assertThat(pendingWebApplications.get(0).getMetadataValue("source")).isEqualTo("web");
    }

    @Test
    @DisplayName("Should count applications by status")
    public void testCountByStatus() {
        // Count applications by status
        long newCount = applicationRepository.countByStatus(ApplicationStatus.NEW);
        long completedCount = applicationRepository.countByStatus(ApplicationStatus.COMPLETED);
        
        // Verify the correct counts were returned
        assertThat(newCount).isEqualTo(1);
        assertThat(completedCount).isEqualTo(2);
    }

    @Test
    @DisplayName("Should count applications by review status")
    public void testCountByReviewStatus() {
        // Count applications by review status
        long notReviewedCount = applicationRepository.countByReviewStatus(ReviewStatus.NOT_REVIEWED);
        long approvedCount = applicationRepository.countByReviewStatus(ReviewStatus.APPROVED);
        
        // Verify the correct counts were returned
        assertThat(notReviewedCount).isEqualTo(1);
        assertThat(approvedCount).isEqualTo(2);
    }

    @Test
    @DisplayName("Should count applications by status and review status")
    public void testCountByStatusAndReviewStatus() {
        // Count applications by status and review status
        long completedApprovedCount = applicationRepository.countByStatusAndReviewStatus(
                ApplicationStatus.COMPLETED, ReviewStatus.APPROVED);
        
        // Verify the correct count was returned
        assertThat(completedApprovedCount).isEqualTo(2);
    }

    @Test
    @DisplayName("Should count applications created within date range")
    public void testCountByCreatedAtBetween() {
        // Define date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(2);
        LocalDateTime endDate = LocalDateTime.now();
        
        // Count applications created within date range
        long count = applicationRepository.countByCreatedAtBetween(startDate, endDate);
        
        // Verify the correct count was returned
        assertThat(count).isEqualTo(6);
    }

    @Test
    @DisplayName("Should find applications processed under five minutes")
    public void testFindApplicationsProcessedUnderFiveMinutes() {
        // Find applications processed under five minutes
        List<Application> fastApplications = applicationRepository.findApplicationsProcessedUnderFiveMinutes();
        
        // Verify the correct applications were found
        assertThat(fastApplications).hasSize(1);
        assertThat(fastApplications.get(0).getId()).isEqualTo(fastProcessedApplication.getId());
        
        // Verify the application meets the processing time requirement
        long processingTime = ChronoUnit.MILLIS.between(
                fastApplications.get(0).getCreatedAt(), 
                fastApplications.get(0).getUpdatedAt());
        assertThat(processingTime).isLessThan(300000); // 5 minutes in milliseconds
    }

    @Test
    @DisplayName("Should calculate average processing time")
    public void testCalculateAverageProcessingTimeMillis() {
        // Calculate average processing time
        Double averageTime = applicationRepository.calculateAverageProcessingTimeMillis();
        
        // Verify the average time is calculated
        assertThat(averageTime).isNotNull();
        assertThat(averageTime).isGreaterThan(0.0);
    }

    @Test
    @DisplayName("Should find applications requiring human intervention")
    public void testFindApplicationsRequiringHumanIntervention() {
        // Find applications requiring human intervention
        List<Application> applications = applicationRepository.findApplicationsRequiringHumanIntervention();
        
        // Verify the correct applications were found
        assertThat(applications).hasSize(1); // Only PENDING application requires intervention
        assertThat(applications.get(0).getStatus()).isEqualTo(ApplicationStatus.PENDING);
    }

    @Test
    @DisplayName("Should find automatically processed applications")
    public void testFindAutomaticallyProcessedApplications() {
        // Find automatically processed applications
        List<Application> applications = applicationRepository.findAutomaticallyProcessedApplications();
        
        // Verify the correct applications were found
        assertThat(applications).hasSize(2);
        assertThat(applications).allMatch(app -> app.getStatus() == ApplicationStatus.COMPLETED);
    }

    @Test
    @DisplayName("Should calculate automation rate")
    public void testCalculateAutomationRate() {
        // Calculate automation rate
        Double automationRate = applicationRepository.calculateAutomationRate();
        
        // Verify the automation rate is calculated
        assertThat(automationRate).isNotNull();
        // 2 out of 6 applications were automatically processed
        assertThat(automationRate).isEqualTo(2.0 / 6.0);
    }

    @Test
    @DisplayName("Should find applications by document count")
    public void testFindByDocumentCount() {
        // Find applications by document count
        List<Application> applicationsWithTwoDocuments = applicationRepository.findByDocumentCount(2);
        List<Application> applicationsWithThreeDocuments = applicationRepository.findByDocumentCount(3);
        
        // Verify the correct applications were found
        assertThat(applicationsWithTwoDocuments).hasSize(1);
        assertThat(applicationsWithTwoDocuments.get(0).getDocumentCount()).isEqualTo(2);
        
        assertThat(applicationsWithThreeDocuments).hasSize(1);
        assertThat(applicationsWithThreeDocuments.get(0).getDocumentCount()).isEqualTo(3);
    }

    @Test
    @DisplayName("Should find applications with merchant details")
    public void testFindApplicationsWithMerchantDetails() {
        // Find applications with merchant details
        List<Application> applications = applicationRepository.findApplicationsWithMerchantDetails();
        
        // Verify the correct applications were found
        assertThat(applications).hasSize(2);
        assertThat(applications).allMatch(app -> app.getMerchantDetails() != null);
    }

    @Test
    @DisplayName("Should find applications without merchant details")
    public void testFindApplicationsWithoutMerchantDetails() {
        // Find applications without merchant details
        List<Application> applications = applicationRepository.findApplicationsWithoutMerchantDetails();
        
        // Verify the correct applications were found
        assertThat(applications).hasSize(4);
        assertThat(applications).allMatch(app -> app.getMerchantDetails() == null);
    }
}