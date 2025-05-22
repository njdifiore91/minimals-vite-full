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

import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.util.JsonUtil;

/**
 * JUnit test class for {@link DocumentRepository} that verifies the repository correctly
 * interacts with the database for {@link Document} entities.
 * <p>
 * This test class uses {@link DataJpaTest} to configure an in-memory database for testing
 * and includes setup methods to create test data. It tests CRUD operations, custom query
 * methods for finding documents by application ID, type, classification, and upload date,
 * as well as the relationship between Document and Application entities.
 * </p>
 */
@DataJpaTest
public class DocumentRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private DocumentRepository documentRepository;

    @Autowired
    private ApplicationRepository applicationRepository;

    private Application application1;
    private Application application2;
    private Document document1;
    private Document document2;
    private Document document3;
    private Document document4;
    private Document document5;

    /**
     * Sets up test data before each test method.
     * <p>
     * Creates two applications and five document entities with different configurations:
     * <ul>
     *   <li>document1: BANK_STATEMENT for application1, high confidence</li>
     *   <li>document2: TAX_RETURN for application1, high confidence</li>
     *   <li>document3: ID_VERIFICATION for application1, low confidence</li>
     *   <li>document4: BUSINESS_LICENSE for application2, high confidence</li>
     *   <li>document5: INVOICE for application2, missing metadata</li>
     * </ul>
     * </p>
     */
    @BeforeEach
    public void setup() {
        // Create test applications
        application1 = new Application(ApplicationStatus.PROCESSING, ReviewStatus.IN_REVIEW);
        application2 = new Application(ApplicationStatus.PENDING, ReviewStatus.NEEDS_INFORMATION);

        // Persist applications
        application1 = entityManager.persist(application1);
        application2 = entityManager.persist(application2);

        // Create test documents with different configurations
        document1 = createBankStatement(application1);
        document2 = createTaxReturn(application1);
        document3 = createIdVerification(application1);
        document4 = createBusinessLicense(application2);
        document5 = createInvoice(application2);

        // Persist test documents
        entityManager.persist(document1);
        entityManager.persist(document2);
        entityManager.persist(document3);
        entityManager.persist(document4);
        entityManager.persist(document5);
        entityManager.flush();
    }

    /**
     * Creates a bank statement document for testing.
     *
     * @param application The application to associate with the document
     * @return A bank statement document with high confidence scores
     */
    private Document createBankStatement(Application application) {
        Document document = new Document(application.getId(), DocumentType.BANK_STATEMENT,
                "s3://mca-documents-production/bank-statements/statement-123.pdf");
        document.setClassification("Monthly Bank Statement");
        document.setUploadedAt(LocalDateTime.now().minusDays(5));

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("bankName", "First National Bank");
        metadata.put("accountNumber", "XXXX-XXXX-1234");
        metadata.put("statementDate", "2023-01-15");
        metadata.put("accountType", "Business Checking");
        metadata.put("accountBalance", 24750.55);

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.95);
        confidenceScores.put("bankName", 0.98);
        confidenceScores.put("accountNumber", 0.92);
        confidenceScores.put("statementDate", 0.97);
        confidenceScores.put("accountBalance", 0.94);

        metadata.put("confidenceScores", confidenceScores);
        document.setMetadata(metadata);

        return document;
    }

    /**
     * Creates a tax return document for testing.
     *
     * @param application The application to associate with the document
     * @return A tax return document with high confidence scores
     */
    private Document createTaxReturn(Application application) {
        Document document = new Document(application.getId(), DocumentType.TAX_RETURN,
                "s3://mca-documents-production/tax-returns/tax-return-456.pdf");
        document.setClassification("Business Tax Return");
        document.setUploadedAt(LocalDateTime.now().minusDays(4));

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("taxYear", "2022");
        metadata.put("businessName", "ABC Enterprises LLC");
        metadata.put("ein", "XX-XXXXXXX");
        metadata.put("filingStatus", "S-Corporation");
        metadata.put("grossIncome", 875000.00);
        metadata.put("netIncome", 245000.00);

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.93);
        confidenceScores.put("taxYear", 0.99);
        confidenceScores.put("businessName", 0.97);
        confidenceScores.put("ein", 0.95);
        confidenceScores.put("grossIncome", 0.91);
        confidenceScores.put("netIncome", 0.90);

        metadata.put("confidenceScores", confidenceScores);
        document.setMetadata(metadata);

        return document;
    }

    /**
     * Creates an ID verification document for testing.
     *
     * @param application The application to associate with the document
     * @return An ID verification document with low confidence scores
     */
    private Document createIdVerification(Application application) {
        Document document = new Document(application.getId(), DocumentType.ID_VERIFICATION,
                "s3://mca-documents-production/id-verification/drivers-license-789.jpg");
        document.setClassification("Driver's License");
        document.setUploadedAt(LocalDateTime.now().minusDays(3));

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("idType", "Driver's License");
        metadata.put("state", "CA");
        metadata.put("fullName", "John A. Smith");
        metadata.put("idNumber", "DL12345678");
        metadata.put("expirationDate", "2025-08-15");
        metadata.put("dateOfBirth", "1980-06-22");

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.85); // Below threshold for ID_VERIFICATION (0.90)
        confidenceScores.put("idType", 0.92);
        confidenceScores.put("state", 0.95);
        confidenceScores.put("fullName", 0.88); // Below threshold
        confidenceScores.put("idNumber", 0.87); // Below threshold
        confidenceScores.put("expirationDate", 0.91);
        confidenceScores.put("dateOfBirth", 0.89); // Below threshold

        metadata.put("confidenceScores", confidenceScores);
        document.setMetadata(metadata);

        return document;
    }

    /**
     * Creates a business license document for testing.
     *
     * @param application The application to associate with the document
     * @return A business license document with high confidence scores
     */
    private Document createBusinessLicense(Application application) {
        Document document = new Document(application.getId(), DocumentType.BUSINESS_LICENSE,
                "s3://mca-documents-production/business-licenses/license-101.pdf");
        document.setClassification("State Business License");
        document.setUploadedAt(LocalDateTime.now().minusDays(2));

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("licenseType", "Business Operation License");
        metadata.put("licenseNumber", "BL-987654");
        metadata.put("issuingAuthority", "State of California");
        metadata.put("businessName", "XYZ Corporation");
        metadata.put("issueDate", "2022-03-15");
        metadata.put("expirationDate", "2024-03-14");

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.94);
        confidenceScores.put("licenseType", 0.92);
        confidenceScores.put("licenseNumber", 0.95);
        confidenceScores.put("issuingAuthority", 0.93);
        confidenceScores.put("businessName", 0.91);
        confidenceScores.put("issueDate", 0.90);
        confidenceScores.put("expirationDate", 0.89);

        metadata.put("confidenceScores", confidenceScores);
        document.setMetadata(metadata);

        return document;
    }

    /**
     * Creates an invoice document for testing.
     *
     * @param application The application to associate with the document
     * @return An invoice document with missing metadata
     */
    private Document createInvoice(Application application) {
        Document document = new Document(application.getId(), DocumentType.INVOICE,
                "s3://mca-documents-production/invoices/invoice-202.pdf");
        document.setClassification("Sales Invoice");
        document.setUploadedAt(LocalDateTime.now().minusDays(1));
        // No metadata set for this document to test handling of missing metadata

        return document;
    }

    /**
     * Tests that the repository can save a document entity and retrieve it by ID.
     */
    @Test
    @DisplayName("Should save and find document by ID")
    public void testSaveAndFindById() {
        // Create a new document
        Document newDocument = new Document(application1.getId(), DocumentType.MISCELLANEOUS,
                "s3://mca-documents-production/misc/document-999.pdf");
        newDocument.setClassification("Miscellaneous Document");
        newDocument.setUploadedAt(LocalDateTime.now());

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("description", "Additional supporting document");
        metadata.put("pages", 5);
        newDocument.setMetadata(metadata);

        // Save the document
        Document savedDocument = documentRepository.save(newDocument);

        // Verify the document was saved with an ID
        assertThat(savedDocument.getId()).isNotNull();

        // Find the document by ID
        Optional<Document> foundDocument = documentRepository.findById(savedDocument.getId());

        // Verify the document was found and has the correct properties
        assertThat(foundDocument).isPresent();
        assertThat(foundDocument.get().getApplicationId()).isEqualTo(application1.getId());
        assertThat(foundDocument.get().getType()).isEqualTo(DocumentType.MISCELLANEOUS);
        assertThat(foundDocument.get().getClassification()).isEqualTo("Miscellaneous Document");
        assertThat(foundDocument.get().getStoragePath()).isEqualTo("s3://mca-documents-production/misc/document-999.pdf");
        assertThat(foundDocument.get().getMetadataValue("description")).isEqualTo("Additional supporting document");
        assertThat(foundDocument.get().getMetadataValue("pages")).isEqualTo(5);
    }

    /**
     * Tests that the repository can find all document entities.
     */
    @Test
    @DisplayName("Should find all documents")
    public void testFindAll() {
        // Find all documents
        List<Document> documents = documentRepository.findAll();

        // Verify all documents were found
        assertThat(documents).hasSize(5);
        assertThat(documents).extracting(Document::getType)
                .contains(
                        DocumentType.BANK_STATEMENT,
                        DocumentType.TAX_RETURN,
                        DocumentType.ID_VERIFICATION,
                        DocumentType.BUSINESS_LICENSE,
                        DocumentType.INVOICE
                );
    }

    /**
     * Tests that the repository can delete a document entity.
     */
    @Test
    @DisplayName("Should delete document")
    public void testDelete() {
        // Delete document1
        documentRepository.delete(document1);
        entityManager.flush();

        // Verify document1 was deleted
        Optional<Document> deletedDocument = documentRepository.findById(document1.getId());
        assertThat(deletedDocument).isEmpty();

        // Verify other documents still exist
        List<Document> remainingDocuments = documentRepository.findAll();
        assertThat(remainingDocuments).hasSize(4);
        assertThat(remainingDocuments).extracting(Document::getId)
                .contains(document2.getId(), document3.getId(), document4.getId(), document5.getId());
    }

    /**
     * Tests that the repository can find documents by application ID.
     */
    @Test
    @DisplayName("Should find documents by application ID")
    public void testFindByApplicationId() {
        // Find documents for application1
        List<Document> application1Documents = documentRepository.findByApplicationId(application1.getId());

        // Verify documents for application1 were found
        assertThat(application1Documents).hasSize(3);
        assertThat(application1Documents).extracting(Document::getId)
                .contains(document1.getId(), document2.getId(), document3.getId());

        // Find documents for application2
        List<Document> application2Documents = documentRepository.findByApplicationId(application2.getId());

        // Verify documents for application2 were found
        assertThat(application2Documents).hasSize(2);
        assertThat(application2Documents).extracting(Document::getId)
                .contains(document4.getId(), document5.getId());

        // Test with non-existent application ID
        List<Document> nonExistentApplicationDocuments = documentRepository.findByApplicationId(UUID.randomUUID());
        assertThat(nonExistentApplicationDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents by application ID ordered by upload date.
     */
    @Test
    @DisplayName("Should find documents by application ID ordered by upload date")
    public void testFindByApplicationIdOrderByUploadedAtDesc() {
        // Find documents for application1 ordered by upload date (descending)
        List<Document> orderedDocuments = documentRepository.findByApplicationIdOrderByUploadedAtDesc(application1.getId());

        // Verify documents are ordered by upload date (descending)
        assertThat(orderedDocuments).hasSize(3);
        assertThat(orderedDocuments.get(0).getId()).isEqualTo(document3.getId()); // Most recent
        assertThat(orderedDocuments.get(1).getId()).isEqualTo(document2.getId());
        assertThat(orderedDocuments.get(2).getId()).isEqualTo(document1.getId()); // Oldest
    }

    /**
     * Tests that the repository can find a document by ID and application ID.
     */
    @Test
    @DisplayName("Should find document by ID and application ID")
    public void testFindByIdAndApplicationId() {
        // Find document by ID and application ID
        Optional<Document> foundDocument = documentRepository.findByIdAndApplicationId(
                document1.getId(), application1.getId());

        // Verify the document was found
        assertThat(foundDocument).isPresent();
        assertThat(foundDocument.get().getId()).isEqualTo(document1.getId());

        // Test with correct ID but wrong application ID
        Optional<Document> notFoundDocument = documentRepository.findByIdAndApplicationId(
                document1.getId(), application2.getId());
        assertThat(notFoundDocument).isEmpty();
    }

    /**
     * Tests that the repository can find documents by type.
     */
    @Test
    @DisplayName("Should find documents by type")
    public void testFindByType() {
        // Find documents by type
        List<Document> bankStatements = documentRepository.findByType(DocumentType.BANK_STATEMENT);
        assertThat(bankStatements).hasSize(1);
        assertThat(bankStatements.get(0).getId()).isEqualTo(document1.getId());

        List<Document> taxReturns = documentRepository.findByType(DocumentType.TAX_RETURN);
        assertThat(taxReturns).hasSize(1);
        assertThat(taxReturns.get(0).getId()).isEqualTo(document2.getId());

        // Test with non-existent type
        List<Document> nonExistentTypeDocuments = documentRepository.findByType(DocumentType.MISCELLANEOUS);
        assertThat(nonExistentTypeDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents by application ID and type.
     */
    @Test
    @DisplayName("Should find documents by application ID and type")
    public void testFindByApplicationIdAndType() {
        // Find documents by application ID and type
        List<Document> application1BankStatements = documentRepository.findByApplicationIdAndType(
                application1.getId(), DocumentType.BANK_STATEMENT);
        assertThat(application1BankStatements).hasSize(1);
        assertThat(application1BankStatements.get(0).getId()).isEqualTo(document1.getId());

        // Test with correct application ID but non-existent type
        List<Document> application1Miscellaneous = documentRepository.findByApplicationIdAndType(
                application1.getId(), DocumentType.MISCELLANEOUS);
        assertThat(application1Miscellaneous).isEmpty();

        // Test with non-existent application ID
        List<Document> nonExistentApplicationBankStatements = documentRepository.findByApplicationIdAndType(
                UUID.randomUUID(), DocumentType.BANK_STATEMENT);
        assertThat(nonExistentApplicationBankStatements).isEmpty();
    }

    /**
     * Tests that the repository can find documents by classification.
     */
    @Test
    @DisplayName("Should find documents by classification")
    public void testFindByClassification() {
        // Find documents by classification
        List<Document> monthlyBankStatements = documentRepository.findByClassification("Monthly Bank Statement");
        assertThat(monthlyBankStatements).hasSize(1);
        assertThat(monthlyBankStatements.get(0).getId()).isEqualTo(document1.getId());

        List<Document> businessTaxReturns = documentRepository.findByClassification("Business Tax Return");
        assertThat(businessTaxReturns).hasSize(1);
        assertThat(businessTaxReturns.get(0).getId()).isEqualTo(document2.getId());

        // Test with non-existent classification
        List<Document> nonExistentClassificationDocuments = documentRepository.findByClassification("Non-existent Classification");
        assertThat(nonExistentClassificationDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents by application ID and classification.
     */
    @Test
    @DisplayName("Should find documents by application ID and classification")
    public void testFindByApplicationIdAndClassification() {
        // Find documents by application ID and classification
        List<Document> application1MonthlyBankStatements = documentRepository.findByApplicationIdAndClassification(
                application1.getId(), "Monthly Bank Statement");
        assertThat(application1MonthlyBankStatements).hasSize(1);
        assertThat(application1MonthlyBankStatements.get(0).getId()).isEqualTo(document1.getId());

        // Test with correct application ID but non-existent classification
        List<Document> application1NonExistentClassification = documentRepository.findByApplicationIdAndClassification(
                application1.getId(), "Non-existent Classification");
        assertThat(application1NonExistentClassification).isEmpty();

        // Test with non-existent application ID
        List<Document> nonExistentApplicationMonthlyBankStatements = documentRepository.findByApplicationIdAndClassification(
                UUID.randomUUID(), "Monthly Bank Statement");
        assertThat(nonExistentApplicationMonthlyBankStatements).isEmpty();
    }

    /**
     * Tests that the repository can find documents uploaded within a specific date range.
     */
    @Test
    @DisplayName("Should find documents by upload date range")
    public void testFindByUploadedAtBetween() {
        // Find documents uploaded within a date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(4).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now().minusDays(2).withHour(23).withMinute(59).withSecond(59);

        List<Document> documentsInRange = documentRepository.findByUploadedAtBetween(startDate, endDate);

        // Verify documents uploaded within the date range were found
        assertThat(documentsInRange).hasSize(3);
        assertThat(documentsInRange).extracting(Document::getId)
                .contains(document2.getId(), document3.getId(), document4.getId());

        // Test with date range that doesn't include any documents
        LocalDateTime pastStartDate = LocalDateTime.now().minusDays(10);
        LocalDateTime pastEndDate = LocalDateTime.now().minusDays(6);

        List<Document> documentsInPastRange = documentRepository.findByUploadedAtBetween(pastStartDate, pastEndDate);
        assertThat(documentsInPastRange).isEmpty();
    }

    /**
     * Tests that the repository can find documents by application ID and upload date range.
     */
    @Test
    @DisplayName("Should find documents by application ID and upload date range")
    public void testFindByApplicationIdAndUploadedAtBetween() {
        // Find documents for application1 uploaded within a date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(5).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now().minusDays(3).withHour(23).withMinute(59).withSecond(59);

        List<Document> application1DocumentsInRange = documentRepository.findByApplicationIdAndUploadedAtBetween(
                application1.getId(), startDate, endDate);

        // Verify documents for application1 uploaded within the date range were found
        assertThat(application1DocumentsInRange).hasSize(3);
        assertThat(application1DocumentsInRange).extracting(Document::getId)
                .contains(document1.getId(), document2.getId(), document3.getId());

        // Test with application2
        List<Document> application2DocumentsInRange = documentRepository.findByApplicationIdAndUploadedAtBetween(
                application2.getId(), startDate, endDate);
        assertThat(application2DocumentsInRange).isEmpty();
    }

    /**
     * Tests that the repository can find documents uploaded after a specific date.
     */
    @Test
    @DisplayName("Should find documents uploaded after a specific date")
    public void testFindByUploadedAtAfter() {
        // Find documents uploaded after a specific date
        LocalDateTime date = LocalDateTime.now().minusDays(3).withHour(0).withMinute(0).withSecond(0);

        List<Document> documentsAfterDate = documentRepository.findByUploadedAtAfter(date);

        // Verify documents uploaded after the date were found
        assertThat(documentsAfterDate).hasSize(3);
        assertThat(documentsAfterDate).extracting(Document::getId)
                .contains(document3.getId(), document4.getId(), document5.getId());
    }

    /**
     * Tests that the repository can find documents uploaded before a specific date.
     */
    @Test
    @DisplayName("Should find documents uploaded before a specific date")
    public void testFindByUploadedAtBefore() {
        // Find documents uploaded before a specific date
        LocalDateTime date = LocalDateTime.now().minusDays(3).withHour(0).withMinute(0).withSecond(0);

        List<Document> documentsBeforeDate = documentRepository.findByUploadedAtBefore(date);

        // Verify documents uploaded before the date were found
        assertThat(documentsBeforeDate).hasSize(2);
        assertThat(documentsBeforeDate).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());
    }

    /**
     * Tests that the repository can count documents by application ID.
     */
    @Test
    @DisplayName("Should count documents by application ID")
    public void testCountByApplicationId() {
        // Count documents for application1
        long application1DocumentCount = documentRepository.countByApplicationId(application1.getId());
        assertThat(application1DocumentCount).isEqualTo(3);

        // Count documents for application2
        long application2DocumentCount = documentRepository.countByApplicationId(application2.getId());
        assertThat(application2DocumentCount).isEqualTo(2);

        // Count documents for non-existent application
        long nonExistentApplicationDocumentCount = documentRepository.countByApplicationId(UUID.randomUUID());
        assertThat(nonExistentApplicationDocumentCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can count documents by application ID and type.
     */
    @Test
    @DisplayName("Should count documents by application ID and type")
    public void testCountByApplicationIdAndType() {
        // Count documents for application1 by type
        long application1BankStatementCount = documentRepository.countByApplicationIdAndType(
                application1.getId(), DocumentType.BANK_STATEMENT);
        assertThat(application1BankStatementCount).isEqualTo(1);

        long application1TaxReturnCount = documentRepository.countByApplicationIdAndType(
                application1.getId(), DocumentType.TAX_RETURN);
        assertThat(application1TaxReturnCount).isEqualTo(1);

        // Count documents for non-existent type
        long application1MiscellaneousCount = documentRepository.countByApplicationIdAndType(
                application1.getId(), DocumentType.MISCELLANEOUS);
        assertThat(application1MiscellaneousCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can check if a document exists by ID and application ID.
     */
    @Test
    @DisplayName("Should check if document exists by ID and application ID")
    public void testExistsByIdAndApplicationId() {
        // Check if document exists by ID and application ID
        boolean exists = documentRepository.existsByIdAndApplicationId(document1.getId(), application1.getId());
        assertThat(exists).isTrue();

        // Check with correct ID but wrong application ID
        boolean notExistsWrongApplication = documentRepository.existsByIdAndApplicationId(
                document1.getId(), application2.getId());
        assertThat(notExistsWrongApplication).isFalse();

        // Check with non-existent ID
        boolean notExistsWrongId = documentRepository.existsByIdAndApplicationId(
                UUID.randomUUID(), application1.getId());
        assertThat(notExistsWrongId).isFalse();
    }

    /**
     * Tests that the repository can delete documents by application ID.
     */
    @Test
    @DisplayName("Should delete documents by application ID")
    public void testDeleteByApplicationId() {
        // Delete documents for application1
        documentRepository.deleteByApplicationId(application1.getId());
        entityManager.flush();

        // Verify documents for application1 were deleted
        List<Document> application1Documents = documentRepository.findByApplicationId(application1.getId());
        assertThat(application1Documents).isEmpty();

        // Verify documents for application2 still exist
        List<Document> application2Documents = documentRepository.findByApplicationId(application2.getId());
        assertThat(application2Documents).hasSize(2);
    }

    /**
     * Tests that the repository can find documents with metadata containing a specific key.
     */
    @Test
    @DisplayName("Should find documents with metadata containing a specific key")
    public void testFindByMetadataContainsKey() {
        // Find documents with metadata containing a specific key
        String jsonPath = "{\"bankName\": {}}";
        List<Document> documentsWithBankName = documentRepository.findByMetadataContainsKey(jsonPath);

        // Verify documents with the specified metadata key were found
        assertThat(documentsWithBankName).hasSize(1);
        assertThat(documentsWithBankName.get(0).getId()).isEqualTo(document1.getId());

        // Test with another key
        String taxYearJsonPath = "{\"taxYear\": {}}";
        List<Document> documentsWithTaxYear = documentRepository.findByMetadataContainsKey(taxYearJsonPath);
        assertThat(documentsWithTaxYear).hasSize(1);
        assertThat(documentsWithTaxYear.get(0).getId()).isEqualTo(document2.getId());
    }

    /**
     * Tests that the repository can find documents with metadata containing a specific key-value pair.
     */
    @Test
    @DisplayName("Should find documents with metadata containing a specific key-value pair")
    public void testFindByMetadataContains() {
        // Find documents with metadata containing a specific key-value pair
        String keyValueJson = "{\"bankName\": \"First National Bank\"}";
        List<Document> documentsWithBankName = documentRepository.findByMetadataContains(keyValueJson);

        // Verify documents with the specified metadata key-value pair were found
        assertThat(documentsWithBankName).hasSize(1);
        assertThat(documentsWithBankName.get(0).getId()).isEqualTo(document1.getId());

        // Test with another key-value pair
        String taxYearJson = "{\"taxYear\": \"2022\"}";
        List<Document> documentsWith2022TaxYear = documentRepository.findByMetadataContains(taxYearJson);
        assertThat(documentsWith2022TaxYear).hasSize(1);
        assertThat(documentsWith2022TaxYear.get(0).getId()).isEqualTo(document2.getId());

        // Test with non-existent key-value pair
        String nonExistentJson = "{\"nonExistentKey\": \"nonExistentValue\"}";
        List<Document> documentsWithNonExistentKeyValue = documentRepository.findByMetadataContains(nonExistentJson);
        assertThat(documentsWithNonExistentKeyValue).isEmpty();
    }

    /**
     * Tests that the repository can find documents with a confidence score above a threshold for a specific field.
     */
    @Test
    @DisplayName("Should find documents with confidence score above threshold")
    public void testFindByConfidenceScoreGreaterThan() {
        // Find documents with classification confidence score above 0.90
        List<Document> highConfidenceDocuments = documentRepository.findByConfidenceScoreGreaterThan(
                "classification", 0.90);

        // Verify documents with high confidence scores were found
        assertThat(highConfidenceDocuments).hasSize(3);
        assertThat(highConfidenceDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId(), document4.getId());

        // Test with higher threshold
        List<Document> veryHighConfidenceDocuments = documentRepository.findByConfidenceScoreGreaterThan(
                "classification", 0.94);
        assertThat(veryHighConfidenceDocuments).hasSize(1);
        assertThat(veryHighConfidenceDocuments.get(0).getId()).isEqualTo(document1.getId());
    }

    /**
     * Tests that the repository can find documents with a confidence score below a threshold for a specific field.
     */
    @Test
    @DisplayName("Should find documents with confidence score below threshold")
    public void testFindByConfidenceScoreLessThan() {
        // Find documents with classification confidence score below 0.90
        List<Document> lowConfidenceDocuments = documentRepository.findByConfidenceScoreLessThan(
                "classification", 0.90);

        // Verify documents with low confidence scores were found
        assertThat(lowConfidenceDocuments).hasSize(1);
        assertThat(lowConfidenceDocuments.get(0).getId()).isEqualTo(document3.getId());

        // Test with lower threshold
        List<Document> veryLowConfidenceDocuments = documentRepository.findByConfidenceScoreLessThan(
                "classification", 0.80);
        assertThat(veryLowConfidenceDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents with a specific storage path pattern.
     */
    @Test
    @DisplayName("Should find documents by storage path pattern")
    public void testFindByStoragePathPattern() {
        // Find documents with storage path matching a pattern
        List<Document> bankStatementDocuments = documentRepository.findByStoragePathPattern(
                "s3://mca-documents-production/bank-statements/%");

        // Verify documents with matching storage path pattern were found
        assertThat(bankStatementDocuments).hasSize(1);
        assertThat(bankStatementDocuments.get(0).getId()).isEqualTo(document1.getId());

        // Test with another pattern
        List<Document> taxReturnDocuments = documentRepository.findByStoragePathPattern(
                "s3://mca-documents-production/tax-returns/%");
        assertThat(taxReturnDocuments).hasSize(1);
        assertThat(taxReturnDocuments.get(0).getId()).isEqualTo(document2.getId());

        // Test with broader pattern
        List<Document> allProductionDocuments = documentRepository.findByStoragePathPattern(
                "s3://mca-documents-production/%");
        assertThat(allProductionDocuments).hasSize(5);
    }

    /**
     * Tests that the repository can find documents that need review based on confidence scores.
     */
    @Test
    @DisplayName("Should find documents needing review")
    public void testFindDocumentsNeedingReview() {
        // Find documents needing review
        List<Document> documentsNeedingReview = documentRepository.findDocumentsNeedingReview();

        // Verify documents needing review were found
        assertThat(documentsNeedingReview).hasSize(1);
        assertThat(documentsNeedingReview.get(0).getId()).isEqualTo(document3.getId());
    }

    /**
     * Tests that the repository can find documents that need review for a specific application.
     */
    @Test
    @DisplayName("Should find documents needing review by application ID")
    public void testFindDocumentsNeedingReviewByApplicationId() {
        // Find documents needing review for application1
        List<Document> application1DocumentsNeedingReview = documentRepository.findDocumentsNeedingReviewByApplicationId(
                application1.getId());

        // Verify documents needing review for application1 were found
        assertThat(application1DocumentsNeedingReview).hasSize(1);
        assertThat(application1DocumentsNeedingReview.get(0).getId()).isEqualTo(document3.getId());

        // Test with application2
        List<Document> application2DocumentsNeedingReview = documentRepository.findDocumentsNeedingReviewByApplicationId(
                application2.getId());
        assertThat(application2DocumentsNeedingReview).isEmpty();
    }

    /**
     * Tests that the repository can find documents with high-confidence classification.
     */
    @Test
    @DisplayName("Should find documents with high-confidence classification")
    public void testFindDocumentsWithHighConfidenceClassification() {
        // Find documents with high-confidence classification
        List<Document> highConfidenceDocuments = documentRepository.findDocumentsWithHighConfidenceClassification();

        // Verify documents with high-confidence classification were found
        assertThat(highConfidenceDocuments).hasSize(3);
        assertThat(highConfidenceDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId(), document4.getId());
    }

    /**
     * Tests that the repository can find documents with low-confidence classification.
     */
    @Test
    @DisplayName("Should find documents with low-confidence classification")
    public void testFindDocumentsWithLowConfidenceClassification() {
        // Find documents with low-confidence classification
        List<Document> lowConfidenceDocuments = documentRepository.findDocumentsWithLowConfidenceClassification();

        // Verify documents with low-confidence classification were found
        assertThat(lowConfidenceDocuments).hasSize(1);
        assertThat(lowConfidenceDocuments.get(0).getId()).isEqualTo(document3.getId());
    }

    /**
     * Tests that the repository can find documents containing personally identifiable information (PII).
     */
    @Test
    @DisplayName("Should find documents containing PII")
    public void testFindDocumentsContainingPII() {
        // Find documents containing PII
        List<Document> documentsWithPII = documentRepository.findDocumentsContainingPII();

        // Verify documents containing PII were found
        assertThat(documentsWithPII).hasSize(2);
        assertThat(documentsWithPII).extracting(Document::getType)
                .contains(DocumentType.ID_VERIFICATION, DocumentType.TAX_RETURN);
    }

    /**
     * Tests that the repository can find financial documents.
     */
    @Test
    @DisplayName("Should find financial documents")
    public void testFindFinancialDocuments() {
        // Find financial documents
        List<Document> financialDocuments = documentRepository.findFinancialDocuments();

        // Verify financial documents were found
        assertThat(financialDocuments).hasSize(3);
        assertThat(financialDocuments).extracting(Document::getType)
                .contains(DocumentType.BANK_STATEMENT, DocumentType.TAX_RETURN, DocumentType.INVOICE);
    }

    /**
     * Tests that the repository can find documents with valid storage information.
     */
    @Test
    @DisplayName("Should find documents with valid storage")
    public void testFindDocumentsWithValidStorage() {
        // Find documents with valid storage
        List<Document> documentsWithValidStorage = documentRepository.findDocumentsWithValidStorage();

        // Verify all documents have valid storage
        assertThat(documentsWithValidStorage).hasSize(5);

        // Create a document with invalid storage
        Document invalidStorageDocument = new Document(application1.getId(), DocumentType.MISCELLANEOUS,
                "invalid-storage-path");
        invalidStorageDocument.setClassification("Invalid Storage Document");
        invalidStorageDocument.setUploadedAt(LocalDateTime.now());
        entityManager.persist(invalidStorageDocument);
        entityManager.flush();

        // Find documents with valid storage again
        List<Document> documentsWithValidStorageAfterInvalid = documentRepository.findDocumentsWithValidStorage();

        // Verify only documents with valid storage were found
        assertThat(documentsWithValidStorageAfterInvalid).hasSize(5);
    }

    /**
     * Tests that the repository can find documents with invalid or missing storage information.
     */
    @Test
    @DisplayName("Should find documents with invalid storage")
    public void testFindDocumentsWithInvalidStorage() {
        // Initially, all documents have valid storage
        List<Document> documentsWithInvalidStorage = documentRepository.findDocumentsWithInvalidStorage();
        assertThat(documentsWithInvalidStorage).isEmpty();

        // Create documents with invalid storage
        Document nullStorageDocument = new Document(application1.getId(), DocumentType.MISCELLANEOUS, null);
        nullStorageDocument.setClassification("Null Storage Document");
        nullStorageDocument.setUploadedAt(LocalDateTime.now());

        Document emptyStorageDocument = new Document(application1.getId(), DocumentType.MISCELLANEOUS, "");
        emptyStorageDocument.setClassification("Empty Storage Document");
        emptyStorageDocument.setUploadedAt(LocalDateTime.now());

        Document invalidStorageDocument = new Document(application1.getId(), DocumentType.MISCELLANEOUS,
                "invalid-storage-path");
        invalidStorageDocument.setClassification("Invalid Storage Document");
        invalidStorageDocument.setUploadedAt(LocalDateTime.now());

        entityManager.persist(nullStorageDocument);
        entityManager.persist(emptyStorageDocument);
        entityManager.persist(invalidStorageDocument);
        entityManager.flush();

        // Find documents with invalid storage
        List<Document> documentsWithInvalidStorageAfter = documentRepository.findDocumentsWithInvalidStorage();

        // Verify documents with invalid storage were found
        assertThat(documentsWithInvalidStorageAfter).hasSize(3);
    }

    /**
     * Tests the relationship between Document and Application entities.
     */
    @Test
    @DisplayName("Should handle Document-Application relationship")
    public void testDocumentApplicationRelationship() {
        // Retrieve document with application relationship
        Document documentWithApplication = entityManager.find(Document.class, document1.getId());

        // Verify the application relationship is correctly established
        assertThat(documentWithApplication.getApplication()).isNotNull();
        assertThat(documentWithApplication.getApplication().getId()).isEqualTo(application1.getId());

        // Retrieve application with documents relationship
        Application applicationWithDocuments = entityManager.find(Application.class, application1.getId());

        // Verify the documents relationship is correctly established
        assertThat(applicationWithDocuments.getDocuments()).isNotNull();
        assertThat(applicationWithDocuments.getDocuments()).hasSize(3);
        assertThat(applicationWithDocuments.getDocuments()).extracting(Document::getId)
                .contains(document1.getId(), document2.getId(), document3.getId());

        // Test adding a document to an application
        Document newDocument = new Document(application1.getId(), DocumentType.MISCELLANEOUS,
                "s3://mca-documents-production/misc/new-document.pdf");
        newDocument.setClassification("New Miscellaneous Document");
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
     * Tests the Document entity's business methods.
     */
    @Test
    @DisplayName("Should handle Document entity business methods")
    public void testDocumentEntityBusinessMethods() {
        // Test containsPII method
        assertThat(document1.containsPII()).isFalse(); // BANK_STATEMENT
        assertThat(document2.containsPII()).isTrue();  // TAX_RETURN
        assertThat(document3.containsPII()).isTrue();  // ID_VERIFICATION

        // Test isFinancialDocument method
        assertThat(document1.isFinancialDocument()).isTrue();  // BANK_STATEMENT
        assertThat(document2.isFinancialDocument()).isTrue();  // TAX_RETURN
        assertThat(document3.isFinancialDocument()).isFalse(); // ID_VERIFICATION
        assertThat(document4.isFinancialDocument()).isFalse(); // BUSINESS_LICENSE
        assertThat(document5.isFinancialDocument()).isTrue();  // INVOICE

        // Test getOcrConfidenceThreshold method
        assertThat(document1.getOcrConfidenceThreshold()).isEqualTo(0.85); // BANK_STATEMENT
        assertThat(document2.getOcrConfidenceThreshold()).isEqualTo(0.80); // TAX_RETURN
        assertThat(document3.getOcrConfidenceThreshold()).isEqualTo(0.90); // ID_VERIFICATION

        // Test isClassifiedWithHighConfidence method
        assertThat(document1.isClassifiedWithHighConfidence()).isTrue();  // 0.95 > 0.85
        assertThat(document2.isClassifiedWithHighConfidence()).isTrue();  // 0.93 > 0.80
        assertThat(document3.isClassifiedWithHighConfidence()).isFalse(); // 0.85 < 0.90

        // Test getBucketName and getObjectKey methods
        assertThat(document1.getBucketName()).isEqualTo("mca-documents-production");
        assertThat(document1.getObjectKey()).isEqualTo("bank-statements/statement-123.pdf");

        // Test hasValidStorage method
        assertThat(document1.hasValidStorage()).isTrue();

        // Test hasMetadata method
        assertThat(document1.hasMetadata()).isTrue();
        assertThat(document5.hasMetadata()).isFalse();

        // Test isValidForProcessing method
        assertThat(document1.isValidForProcessing()).isTrue();

        // Test adding and retrieving metadata
        document5.addMetadata("testKey", "testValue");
        assertThat(document5.getMetadataValue("testKey")).isEqualTo("testValue");

        // Test adding confidence scores
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.88);
        confidenceScores.put("invoiceNumber", 0.92);
        document5.addConfidenceScores(confidenceScores);

        // Verify confidence scores were added
        assertThat(document5.getConfidenceScore("classification")).isEqualTo(0.88);
        assertThat(document5.getConfidenceScore("invoiceNumber")).isEqualTo(0.92);
    }

    /**
     * Tests the Document entity's builder pattern.
     */
    @Test
    @DisplayName("Should create Document using builder pattern")
    public void testDocumentBuilder() {
        // Create a document using the builder pattern
        Document.Builder builder = new Document.Builder(
                application1.getId(),
                DocumentType.MISCELLANEOUS,
                "s3://mca-documents-production/misc/builder-document.pdf");

        builder.withClassification("Builder Test Document")
               .withUploadedAt(LocalDateTime.now())
               .addMetadata("source", "builder-test")
               .addMetadata("pages", 10);

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.95);
        confidenceScores.put("pages", 0.99);
        builder.withConfidenceScores(confidenceScores);

        Document builtDocument = builder.build();

        // Save the document
        Document savedDocument = documentRepository.save(builtDocument);

        // Verify the document was saved with the correct properties
        assertThat(savedDocument.getId()).isNotNull();
        assertThat(savedDocument.getApplicationId()).isEqualTo(application1.getId());
        assertThat(savedDocument.getType()).isEqualTo(DocumentType.MISCELLANEOUS);
        assertThat(savedDocument.getClassification()).isEqualTo("Builder Test Document");
        assertThat(savedDocument.getStoragePath()).isEqualTo("s3://mca-documents-production/misc/builder-document.pdf");
        assertThat(savedDocument.getMetadataValue("source")).isEqualTo("builder-test");
        assertThat(savedDocument.getMetadataValue("pages")).isEqualTo(10);
        assertThat(savedDocument.getConfidenceScore("classification")).isEqualTo(0.95);
        assertThat(savedDocument.getConfidenceScore("pages")).isEqualTo(0.99);
    }
}