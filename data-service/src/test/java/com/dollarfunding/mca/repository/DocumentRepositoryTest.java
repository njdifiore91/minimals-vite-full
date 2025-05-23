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
import com.dollarfunding.mca.entity.DocumentClassification;
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
     * Creates two application entities and five document entities with different configurations:
     * <ul>
     *   <li>document1: BANK_STATEMENT type, VERIFIED classification, uploaded 5 days ago</li>
     *   <li>document2: TAX_RETURN type, NEEDS_REVIEW classification, uploaded 4 days ago</li>
     *   <li>document3: BUSINESS_LICENSE type, FLAGGED classification, uploaded 3 days ago</li>
     *   <li>document4: ID_VERIFICATION type, REJECTED classification, uploaded 2 days ago</li>
     *   <li>document5: MISCELLANEOUS type, UNCLASSIFIED classification, uploaded 1 day ago</li>
     * </ul>
     * </p>
     */
    @BeforeEach
    public void setup() {
        // Create test applications
        application1 = new Application.Builder()
                .withStatus(ApplicationStatus.NEW)
                .withReviewStatus(ReviewStatus.NOT_REVIEWED)
                .addMetadata("source", "email")
                .build();

        application2 = new Application.Builder()
                .withStatus(ApplicationStatus.PENDING)
                .withReviewStatus(ReviewStatus.IN_REVIEW)
                .addMetadata("source", "web")
                .build();

        // Persist applications
        application1 = entityManager.persist(application1);
        application2 = entityManager.persist(application2);
        
        // Create test documents with different configurations
        document1 = createDocument(
                application1.getId(),
                DocumentType.BANK_STATEMENT,
                "mca-documents-production/bank-statements/statement-" + application1.getId() + ".pdf",
                DocumentClassification.VERIFIED,
                LocalDateTime.now().minusDays(5),
                createMetadata("confidenceScore", 0.98, "pageCount", 5)
        );

        document2 = createDocument(
                application1.getId(),
                DocumentType.TAX_RETURN,
                "mca-documents-production/tax-returns/tax-return-" + application1.getId() + ".pdf",
                DocumentClassification.NEEDS_REVIEW,
                LocalDateTime.now().minusDays(4),
                createMetadata("confidenceScore", 0.75, "pageCount", 10, "taxYear", "2022")
        );

        document3 = createDocument(
                application2.getId(),
                DocumentType.BUSINESS_LICENSE,
                "mca-documents-production/business-licenses/license-" + application2.getId() + ".jpg",
                DocumentClassification.FLAGGED,
                LocalDateTime.now().minusDays(3),
                createMetadata("confidenceScore", 0.65, "expirationDate", "2025-12-31")
        );

        document4 = createDocument(
                application2.getId(),
                DocumentType.ID_VERIFICATION,
                "mca-documents-production/id-verification/id-" + application2.getId() + ".jpg",
                DocumentClassification.REJECTED,
                LocalDateTime.now().minusDays(2),
                createMetadata("confidenceScore", 0.35, "idType", "driver_license")
        );

        document5 = createDocument(
                application2.getId(),
                DocumentType.MISCELLANEOUS,
                "mca-documents-production/miscellaneous/misc-" + application2.getId() + ".png",
                DocumentClassification.UNCLASSIFIED,
                LocalDateTime.now().minusDays(1),
                createMetadata("confidenceScore", 0.0, "documentDescription", "Additional supporting document")
        );

        // Persist documents
        document1 = entityManager.persist(document1);
        document2 = entityManager.persist(document2);
        document3 = entityManager.persist(document3);
        document4 = entityManager.persist(document4);
        document5 = entityManager.persist(document5);
        
        // Set up relationships
        application1.addDocument(document1);
        application1.addDocument(document2);
        application2.addDocument(document3);
        application2.addDocument(document4);
        application2.addDocument(document5);
        
        entityManager.flush();
    }

    /**
     * Creates a document with the specified properties.
     *
     * @param applicationId The application ID
     * @param type The document type
     * @param storagePath The storage path
     * @param classification The document classification
     * @param uploadedAt The upload date
     * @param metadata The document metadata
     * @return A new document entity
     */
    private Document createDocument(UUID applicationId, DocumentType type, String storagePath,
                                   DocumentClassification classification, LocalDateTime uploadedAt,
                                   Map<String, Object> metadata) {
        return new Document.Builder(applicationId, type, storagePath)
                .withClassification(classification)
                .withUploadedAt(uploadedAt)
                .withMetadata(metadata)
                .build();
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
     * Tests that the repository can save a document entity and retrieve it by ID.
     */
    @Test
    @DisplayName("Should save and find document by ID")
    public void testSaveAndFindById() {
        // Create a new document
        Document newDocument = new Document.Builder(
                application1.getId(),
                DocumentType.INVOICE,
                "mca-documents-production/invoices/invoice-new.pdf")
                .withClassification(DocumentClassification.VERIFIED)
                .addMetadata("confidenceScore", 0.97)
                .addMetadata("invoiceAmount", 5000.00)
                .build();

        // Save the document
        Document savedDocument = documentRepository.save(newDocument);

        // Verify the document was saved with an ID
        assertThat(savedDocument.getId()).isNotNull();

        // Find the document by ID
        Optional<Document> foundDocument = documentRepository.findById(savedDocument.getId());

        // Verify the document was found and has the correct properties
        assertThat(foundDocument).isPresent();
        assertThat(foundDocument.get().getType()).isEqualTo(DocumentType.INVOICE);
        assertThat(foundDocument.get().getClassification()).isEqualTo(DocumentClassification.VERIFIED);
        assertThat(foundDocument.get().getStoragePath()).isEqualTo("mca-documents-production/invoices/invoice-new.pdf");
        assertThat(foundDocument.get().getMetadataValue("confidenceScore")).isEqualTo(0.97);
        assertThat(foundDocument.get().getMetadataValue("invoiceAmount")).isEqualTo(5000.00);
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
                        DocumentType.BUSINESS_LICENSE,
                        DocumentType.ID_VERIFICATION,
                        DocumentType.MISCELLANEOUS
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
        // Find documents by application ID
        List<Document> application1Documents = documentRepository.findByApplicationId(application1.getId());
        assertThat(application1Documents).hasSize(2);
        assertThat(application1Documents).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());

        List<Document> application2Documents = documentRepository.findByApplicationId(application2.getId());
        assertThat(application2Documents).hasSize(3);
        assertThat(application2Documents).extracting(Document::getId)
                .contains(document3.getId(), document4.getId(), document5.getId());

        // Test with non-existent application ID
        List<Document> nonExistentApplicationDocuments = documentRepository.findByApplicationId(UUID.randomUUID());
        assertThat(nonExistentApplicationDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents by application ID with pagination.
     */
    @Test
    @DisplayName("Should find documents by application ID with pagination")
    public void testFindByApplicationIdWithPagination() {
        // Create additional documents for application2
        for (int i = 0; i < 10; i++) {
            Document doc = createDocument(
                    application2.getId(),
                    DocumentType.MISCELLANEOUS,
                    "mca-documents-production/miscellaneous/misc-" + i + ".pdf",
                    DocumentClassification.UNCLASSIFIED,
                    LocalDateTime.now().minusHours(i),
                    createMetadata("index", i, "confidenceScore", 0.5)
            );
            entityManager.persist(doc);
            application2.addDocument(doc);
        }
        entityManager.flush();

        // Find documents by application ID with pagination
        Pageable pageable = PageRequest.of(0, 5, Sort.by("uploadedAt").descending());
        Page<Document> application2DocumentsPage = documentRepository.findByApplicationId(application2.getId(), pageable);

        // Verify pagination works correctly
        assertThat(application2DocumentsPage.getContent()).hasSize(5);
        assertThat(application2DocumentsPage.getTotalElements()).isEqualTo(13); // 3 original + 10 new
        assertThat(application2DocumentsPage.getTotalPages()).isEqualTo(3);
        assertThat(application2DocumentsPage.getNumber()).isEqualTo(0);

        // Get next page
        pageable = PageRequest.of(1, 5, Sort.by("uploadedAt").descending());
        application2DocumentsPage = documentRepository.findByApplicationId(application2.getId(), pageable);

        // Verify second page
        assertThat(application2DocumentsPage.getContent()).hasSize(5);
        assertThat(application2DocumentsPage.getNumber()).isEqualTo(1);
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

        List<Document> miscellaneous = documentRepository.findByType(DocumentType.MISCELLANEOUS);
        assertThat(miscellaneous).hasSize(1);
        assertThat(miscellaneous.get(0).getId()).isEqualTo(document5.getId());

        // Test with non-existent type
        List<Document> nonExistentTypeDocuments = documentRepository.findByType(DocumentType.INVOICE);
        assertThat(nonExistentTypeDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents by classification.
     */
    @Test
    @DisplayName("Should find documents by classification")
    public void testFindByClassification() {
        // Find documents by classification
        List<Document> verifiedDocuments = documentRepository.findByClassification(DocumentClassification.VERIFIED);
        assertThat(verifiedDocuments).hasSize(1);
        assertThat(verifiedDocuments.get(0).getId()).isEqualTo(document1.getId());

        List<Document> needsReviewDocuments = documentRepository.findByClassification(DocumentClassification.NEEDS_REVIEW);
        assertThat(needsReviewDocuments).hasSize(1);
        assertThat(needsReviewDocuments.get(0).getId()).isEqualTo(document2.getId());

        List<Document> flaggedDocuments = documentRepository.findByClassification(DocumentClassification.FLAGGED);
        assertThat(flaggedDocuments).hasSize(1);
        assertThat(flaggedDocuments.get(0).getId()).isEqualTo(document3.getId());

        List<Document> rejectedDocuments = documentRepository.findByClassification(DocumentClassification.REJECTED);
        assertThat(rejectedDocuments).hasSize(1);
        assertThat(rejectedDocuments.get(0).getId()).isEqualTo(document4.getId());

        List<Document> unclassifiedDocuments = documentRepository.findByClassification(DocumentClassification.UNCLASSIFIED);
        assertThat(unclassifiedDocuments).hasSize(1);
        assertThat(unclassifiedDocuments.get(0).getId()).isEqualTo(document5.getId());
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

        List<Document> application2Miscellaneous = documentRepository.findByApplicationIdAndType(
                application2.getId(), DocumentType.MISCELLANEOUS);
        assertThat(application2Miscellaneous).hasSize(1);
        assertThat(application2Miscellaneous.get(0).getId()).isEqualTo(document5.getId());

        // Test with non-existent combination
        List<Document> application1Invoices = documentRepository.findByApplicationIdAndType(
                application1.getId(), DocumentType.INVOICE);
        assertThat(application1Invoices).isEmpty();
    }

    /**
     * Tests that the repository can find documents by application ID and classification.
     */
    @Test
    @DisplayName("Should find documents by application ID and classification")
    public void testFindByApplicationIdAndClassification() {
        // Find documents by application ID and classification
        List<Document> application1VerifiedDocuments = documentRepository.findByApplicationIdAndClassification(
                application1.getId(), DocumentClassification.VERIFIED);
        assertThat(application1VerifiedDocuments).hasSize(1);
        assertThat(application1VerifiedDocuments.get(0).getId()).isEqualTo(document1.getId());

        List<Document> application2RejectedDocuments = documentRepository.findByApplicationIdAndClassification(
                application2.getId(), DocumentClassification.REJECTED);
        assertThat(application2RejectedDocuments).hasSize(1);
        assertThat(application2RejectedDocuments.get(0).getId()).isEqualTo(document4.getId());

        // Test with non-existent combination
        List<Document> application1RejectedDocuments = documentRepository.findByApplicationIdAndClassification(
                application1.getId(), DocumentClassification.REJECTED);
        assertThat(application1RejectedDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents by type and classification.
     */
    @Test
    @DisplayName("Should find documents by type and classification")
    public void testFindByTypeAndClassification() {
        // Find documents by type and classification
        List<Document> verifiedBankStatements = documentRepository.findByTypeAndClassification(
                DocumentType.BANK_STATEMENT, DocumentClassification.VERIFIED);
        assertThat(verifiedBankStatements).hasSize(1);
        assertThat(verifiedBankStatements.get(0).getId()).isEqualTo(document1.getId());

        List<Document> needsReviewTaxReturns = documentRepository.findByTypeAndClassification(
                DocumentType.TAX_RETURN, DocumentClassification.NEEDS_REVIEW);
        assertThat(needsReviewTaxReturns).hasSize(1);
        assertThat(needsReviewTaxReturns.get(0).getId()).isEqualTo(document2.getId());

        // Test with non-existent combination
        List<Document> verifiedTaxReturns = documentRepository.findByTypeAndClassification(
                DocumentType.TAX_RETURN, DocumentClassification.VERIFIED);
        assertThat(verifiedTaxReturns).isEmpty();
    }

    /**
     * Tests that the repository can find documents by application ID, type, and classification.
     */
    @Test
    @DisplayName("Should find documents by application ID, type, and classification")
    public void testFindByApplicationIdAndTypeAndClassification() {
        // Find documents by application ID, type, and classification
        List<Document> application1VerifiedBankStatements = documentRepository.findByApplicationIdAndTypeAndClassification(
                application1.getId(), DocumentType.BANK_STATEMENT, DocumentClassification.VERIFIED);
        assertThat(application1VerifiedBankStatements).hasSize(1);
        assertThat(application1VerifiedBankStatements.get(0).getId()).isEqualTo(document1.getId());

        List<Document> application2RejectedIdVerifications = documentRepository.findByApplicationIdAndTypeAndClassification(
                application2.getId(), DocumentType.ID_VERIFICATION, DocumentClassification.REJECTED);
        assertThat(application2RejectedIdVerifications).hasSize(1);
        assertThat(application2RejectedIdVerifications.get(0).getId()).isEqualTo(document4.getId());

        // Test with non-existent combination
        List<Document> application1RejectedBankStatements = documentRepository.findByApplicationIdAndTypeAndClassification(
                application1.getId(), DocumentType.BANK_STATEMENT, DocumentClassification.REJECTED);
        assertThat(application1RejectedBankStatements).isEmpty();
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
     * Tests that the repository can find documents uploaded after a specific date.
     */
    @Test
    @DisplayName("Should find documents uploaded after a specific date")
    public void testFindByUploadedAtAfter() {
        // Find documents uploaded after a specific date
        LocalDateTime date = LocalDateTime.now().minusDays(3).withHour(0).withMinute(0).withSecond(0);

        List<Document> documentsAfterDate = documentRepository.findByUploadedAtAfter(date);

        // Verify documents uploaded after the date were found
        assertThat(documentsAfterDate).hasSize(2);
        assertThat(documentsAfterDate).extracting(Document::getId)
                .contains(document4.getId(), document5.getId());
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
     * Tests that the repository can find documents by application ID and upload date range.
     */
    @Test
    @DisplayName("Should find documents by application ID and upload date range")
    public void testFindByApplicationIdAndUploadedAtBetween() {
        // Find documents by application ID and upload date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(5).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now().minusDays(3).withHour(23).withMinute(59).withSecond(59);

        List<Document> application1DocumentsInRange = documentRepository.findByApplicationIdAndUploadedAtBetween(
                application1.getId(), startDate, endDate);

        // Verify documents for application1 uploaded within the date range were found
        assertThat(application1DocumentsInRange).hasSize(2);
        assertThat(application1DocumentsInRange).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());

        // Test with application2
        List<Document> application2DocumentsInRange = documentRepository.findByApplicationIdAndUploadedAtBetween(
                application2.getId(), startDate, endDate);
        assertThat(application2DocumentsInRange).hasSize(1);
        assertThat(application2DocumentsInRange.get(0).getId()).isEqualTo(document3.getId());
    }

    /**
     * Tests that the repository can find documents by type and upload date range.
     */
    @Test
    @DisplayName("Should find documents by type and upload date range")
    public void testFindByTypeAndUploadedAtBetween() {
        // Find documents by type and upload date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(5).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now().minusDays(1).withHour(23).withMinute(59).withSecond(59);

        List<Document> bankStatementsInRange = documentRepository.findByTypeAndUploadedAtBetween(
                DocumentType.BANK_STATEMENT, startDate, endDate);

        // Verify bank statements uploaded within the date range were found
        assertThat(bankStatementsInRange).hasSize(1);
        assertThat(bankStatementsInRange.get(0).getId()).isEqualTo(document1.getId());

        // Test with another type
        List<Document> idVerificationsInRange = documentRepository.findByTypeAndUploadedAtBetween(
                DocumentType.ID_VERIFICATION, startDate, endDate);
        assertThat(idVerificationsInRange).hasSize(1);
        assertThat(idVerificationsInRange.get(0).getId()).isEqualTo(document4.getId());
    }

    /**
     * Tests that the repository can find documents by classification and upload date range.
     */
    @Test
    @DisplayName("Should find documents by classification and upload date range")
    public void testFindByClassificationAndUploadedAtBetween() {
        // Find documents by classification and upload date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(5).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now().minusDays(1).withHour(23).withMinute(59).withSecond(59);

        List<Document> verifiedDocumentsInRange = documentRepository.findByClassificationAndUploadedAtBetween(
                DocumentClassification.VERIFIED, startDate, endDate);

        // Verify verified documents uploaded within the date range were found
        assertThat(verifiedDocumentsInRange).hasSize(1);
        assertThat(verifiedDocumentsInRange.get(0).getId()).isEqualTo(document1.getId());

        // Test with another classification
        List<Document> rejectedDocumentsInRange = documentRepository.findByClassificationAndUploadedAtBetween(
                DocumentClassification.REJECTED, startDate, endDate);
        assertThat(rejectedDocumentsInRange).hasSize(1);
        assertThat(rejectedDocumentsInRange.get(0).getId()).isEqualTo(document4.getId());
    }

    /**
     * Tests that the repository can find documents by storage path.
     */
    @Test
    @DisplayName("Should find documents by storage path")
    public void testFindByStoragePath() {
        // Find documents by storage path
        String storagePath = document1.getStoragePath();
        List<Document> documentsByPath = documentRepository.findByStoragePath(storagePath);

        // Verify documents with the specified storage path were found
        assertThat(documentsByPath).hasSize(1);
        assertThat(documentsByPath.get(0).getId()).isEqualTo(document1.getId());

        // Test with non-existent storage path
        List<Document> nonExistentPathDocuments = documentRepository.findByStoragePath("non-existent-path");
        assertThat(nonExistentPathDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents with a storage path containing a specific string.
     */
    @Test
    @DisplayName("Should find documents with storage path containing a specific string")
    public void testFindByStoragePathContaining() {
        // Find documents with storage path containing a specific string
        List<Document> bankStatementDocuments = documentRepository.findByStoragePathContaining("bank-statements");

        // Verify documents with storage path containing the specified string were found
        assertThat(bankStatementDocuments).hasSize(1);
        assertThat(bankStatementDocuments.get(0).getId()).isEqualTo(document1.getId());

        // Test with another string
        List<Document> pdfDocuments = documentRepository.findByStoragePathContaining(".pdf");
        assertThat(pdfDocuments).hasSize(2);
        assertThat(pdfDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());

        // Test with non-existent string
        List<Document> nonExistentStringDocuments = documentRepository.findByStoragePathContaining("non-existent-string");
        assertThat(nonExistentStringDocuments).isEmpty();
    }

    /**
     * Tests that the repository can count documents by application ID.
     */
    @Test
    @DisplayName("Should count documents by application ID")
    public void testCountByApplicationId() {
        // Count documents by application ID
        long application1DocumentCount = documentRepository.countByApplicationId(application1.getId());
        assertThat(application1DocumentCount).isEqualTo(2);

        long application2DocumentCount = documentRepository.countByApplicationId(application2.getId());
        assertThat(application2DocumentCount).isEqualTo(3);

        // Test with non-existent application ID
        long nonExistentApplicationDocumentCount = documentRepository.countByApplicationId(UUID.randomUUID());
        assertThat(nonExistentApplicationDocumentCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can count documents by type.
     */
    @Test
    @DisplayName("Should count documents by type")
    public void testCountByType() {
        // Count documents by type
        long bankStatementCount = documentRepository.countByType(DocumentType.BANK_STATEMENT);
        assertThat(bankStatementCount).isEqualTo(1);

        long taxReturnCount = documentRepository.countByType(DocumentType.TAX_RETURN);
        assertThat(taxReturnCount).isEqualTo(1);

        long businessLicenseCount = documentRepository.countByType(DocumentType.BUSINESS_LICENSE);
        assertThat(businessLicenseCount).isEqualTo(1);

        long idVerificationCount = documentRepository.countByType(DocumentType.ID_VERIFICATION);
        assertThat(idVerificationCount).isEqualTo(1);

        long miscellaneousCount = documentRepository.countByType(DocumentType.MISCELLANEOUS);
        assertThat(miscellaneousCount).isEqualTo(1);

        // Test with non-existent type
        long invoiceCount = documentRepository.countByType(DocumentType.INVOICE);
        assertThat(invoiceCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can count documents by classification.
     */
    @Test
    @DisplayName("Should count documents by classification")
    public void testCountByClassification() {
        // Count documents by classification
        long verifiedCount = documentRepository.countByClassification(DocumentClassification.VERIFIED);
        assertThat(verifiedCount).isEqualTo(1);

        long needsReviewCount = documentRepository.countByClassification(DocumentClassification.NEEDS_REVIEW);
        assertThat(needsReviewCount).isEqualTo(1);

        long flaggedCount = documentRepository.countByClassification(DocumentClassification.FLAGGED);
        assertThat(flaggedCount).isEqualTo(1);

        long rejectedCount = documentRepository.countByClassification(DocumentClassification.REJECTED);
        assertThat(rejectedCount).isEqualTo(1);

        long unclassifiedCount = documentRepository.countByClassification(DocumentClassification.UNCLASSIFIED);
        assertThat(unclassifiedCount).isEqualTo(1);
    }

    /**
     * Tests that the repository can count documents by application ID and type.
     */
    @Test
    @DisplayName("Should count documents by application ID and type")
    public void testCountByApplicationIdAndType() {
        // Count documents by application ID and type
        long application1BankStatementCount = documentRepository.countByApplicationIdAndType(
                application1.getId(), DocumentType.BANK_STATEMENT);
        assertThat(application1BankStatementCount).isEqualTo(1);

        long application2MiscellaneousCount = documentRepository.countByApplicationIdAndType(
                application2.getId(), DocumentType.MISCELLANEOUS);
        assertThat(application2MiscellaneousCount).isEqualTo(1);

        // Test with non-existent combination
        long application1InvoiceCount = documentRepository.countByApplicationIdAndType(
                application1.getId(), DocumentType.INVOICE);
        assertThat(application1InvoiceCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can count documents uploaded within a specific date range.
     */
    @Test
    @DisplayName("Should count documents by upload date range")
    public void testCountByUploadedAtBetween() {
        // Count documents uploaded within a date range
        LocalDateTime startDate = LocalDateTime.now().minusDays(4).withHour(0).withMinute(0).withSecond(0);
        LocalDateTime endDate = LocalDateTime.now().minusDays(2).withHour(23).withMinute(59).withSecond(59);

        long documentsInRangeCount = documentRepository.countByUploadedAtBetween(startDate, endDate);

        // Verify count of documents uploaded within the date range
        assertThat(documentsInRangeCount).isEqualTo(3);

        // Test with date range that doesn't include any documents
        LocalDateTime pastStartDate = LocalDateTime.now().minusDays(10);
        LocalDateTime pastEndDate = LocalDateTime.now().minusDays(6);

        long documentsInPastRangeCount = documentRepository.countByUploadedAtBetween(pastStartDate, pastEndDate);
        assertThat(documentsInPastRangeCount).isEqualTo(0);
    }

    /**
     * Tests that the repository can find documents with metadata containing a specific key.
     */
    @Test
    @DisplayName("Should find documents with metadata containing a specific key")
    public void testFindByMetadataContainsKey() {
        // Find documents with metadata containing a specific key
        String jsonPath = "{\"pageCount\": {}}";
        List<Document> documentsWithPageCount = documentRepository.findByMetadataContainsKey(jsonPath);

        // Verify documents with the specified metadata key were found
        assertThat(documentsWithPageCount).hasSize(2);
        assertThat(documentsWithPageCount).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());

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
        String keyValueJson = "{\"confidenceScore\": 0.98}";
        List<Document> documentsWithHighConfidence = documentRepository.findByMetadataContains(keyValueJson);

        // Verify documents with the specified metadata key-value pair were found
        assertThat(documentsWithHighConfidence).hasSize(1);
        assertThat(documentsWithHighConfidence.get(0).getId()).isEqualTo(document1.getId());

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
     * Tests that the repository can find documents with a confidence score above a specific threshold.
     */
    @Test
    @DisplayName("Should find documents with confidence score above threshold")
    public void testFindByConfidenceScoreGreaterThanEqual() {
        // Find documents with confidence score above threshold
        List<Document> highConfidenceDocuments = documentRepository.findByConfidenceScoreGreaterThanEqual(0.7);

        // Verify documents with confidence score above threshold were found
        assertThat(highConfidenceDocuments).hasSize(2);
        assertThat(highConfidenceDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());

        // Test with higher threshold
        List<Document> veryHighConfidenceDocuments = documentRepository.findByConfidenceScoreGreaterThanEqual(0.9);
        assertThat(veryHighConfidenceDocuments).hasSize(1);
        assertThat(veryHighConfidenceDocuments.get(0).getId()).isEqualTo(document1.getId());
    }

    /**
     * Tests that the repository can find documents with a confidence score below a specific threshold.
     */
    @Test
    @DisplayName("Should find documents with confidence score below threshold")
    public void testFindByConfidenceScoreLessThan() {
        // Find documents with confidence score below threshold
        List<Document> lowConfidenceDocuments = documentRepository.findByConfidenceScoreLessThan(0.7);

        // Verify documents with confidence score below threshold were found
        assertThat(lowConfidenceDocuments).hasSize(3);
        assertThat(lowConfidenceDocuments).extracting(Document::getId)
                .contains(document3.getId(), document4.getId(), document5.getId());

        // Test with lower threshold
        List<Document> veryLowConfidenceDocuments = documentRepository.findByConfidenceScoreLessThan(0.4);
        assertThat(veryLowConfidenceDocuments).hasSize(2);
        assertThat(veryLowConfidenceDocuments).extracting(Document::getId)
                .contains(document4.getId(), document5.getId());
    }

    /**
     * Tests that the repository can find documents that require manual review.
     */
    @Test
    @DisplayName("Should find documents requiring manual review")
    public void testFindDocumentsRequiringManualReview() {
        // Find documents requiring manual review
        List<Document> documentsRequiringManualReview = documentRepository.findDocumentsRequiringManualReview();

        // Verify documents requiring manual review were found
        assertThat(documentsRequiringManualReview).hasSize(2);
        assertThat(documentsRequiringManualReview).extracting(Document::getId)
                .contains(document2.getId(), document3.getId());
    }

    /**
     * Tests that the repository can find documents that are acceptable for processing.
     */
    @Test
    @DisplayName("Should find acceptable documents")
    public void testFindAcceptableDocuments() {
        // Find acceptable documents
        List<Document> acceptableDocuments = documentRepository.findAcceptableDocuments();

        // Verify acceptable documents were found
        assertThat(acceptableDocuments).hasSize(2);
        assertThat(acceptableDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());
    }

    /**
     * Tests that the repository can find documents that have been rejected.
     */
    @Test
    @DisplayName("Should find rejected documents")
    public void testFindRejectedDocuments() {
        // Find rejected documents
        List<Document> rejectedDocuments = documentRepository.findRejectedDocuments();

        // Verify rejected documents were found
        assertThat(rejectedDocuments).hasSize(1);
        assertThat(rejectedDocuments.get(0).getId()).isEqualTo(document4.getId());
    }

    /**
     * Tests that the repository can find documents that have been verified.
     */
    @Test
    @DisplayName("Should find verified documents")
    public void testFindVerifiedDocuments() {
        // Find verified documents
        List<Document> verifiedDocuments = documentRepository.findVerifiedDocuments();

        // Verify verified documents were found
        assertThat(verifiedDocuments).hasSize(1);
        assertThat(verifiedDocuments.get(0).getId()).isEqualTo(document1.getId());
    }

    /**
     * Tests that the repository can find documents that have not yet been classified.
     */
    @Test
    @DisplayName("Should find unclassified documents")
    public void testFindUnclassifiedDocuments() {
        // Find unclassified documents
        List<Document> unclassifiedDocuments = documentRepository.findUnclassifiedDocuments();

        // Verify unclassified documents were found
        assertThat(unclassifiedDocuments).hasSize(1);
        assertThat(unclassifiedDocuments.get(0).getId()).isEqualTo(document5.getId());
    }

    /**
     * Tests that the repository can find documents associated with a specific application that require manual review.
     */
    @Test
    @DisplayName("Should find documents requiring manual review by application ID")
    public void testFindDocumentsRequiringManualReviewByApplicationId() {
        // Find documents requiring manual review by application ID
        List<Document> application1DocumentsRequiringManualReview = documentRepository
                .findDocumentsRequiringManualReviewByApplicationId(application1.getId());

        // Verify documents requiring manual review for application1 were found
        assertThat(application1DocumentsRequiringManualReview).hasSize(1);
        assertThat(application1DocumentsRequiringManualReview.get(0).getId()).isEqualTo(document2.getId());

        // Test with application2
        List<Document> application2DocumentsRequiringManualReview = documentRepository
                .findDocumentsRequiringManualReviewByApplicationId(application2.getId());
        assertThat(application2DocumentsRequiringManualReview).hasSize(1);
        assertThat(application2DocumentsRequiringManualReview.get(0).getId()).isEqualTo(document3.getId());
    }

    /**
     * Tests that the repository can find documents of a specific type that require manual review.
     */
    @Test
    @DisplayName("Should find documents requiring manual review by type")
    public void testFindDocumentsRequiringManualReviewByType() {
        // Find documents requiring manual review by type
        List<Document> taxReturnDocumentsRequiringManualReview = documentRepository
                .findDocumentsRequiringManualReviewByType(DocumentType.TAX_RETURN);

        // Verify tax return documents requiring manual review were found
        assertThat(taxReturnDocumentsRequiringManualReview).hasSize(1);
        assertThat(taxReturnDocumentsRequiringManualReview.get(0).getId()).isEqualTo(document2.getId());

        // Test with another type
        List<Document> businessLicenseDocumentsRequiringManualReview = documentRepository
                .findDocumentsRequiringManualReviewByType(DocumentType.BUSINESS_LICENSE);
        assertThat(businessLicenseDocumentsRequiringManualReview).hasSize(1);
        assertThat(businessLicenseDocumentsRequiringManualReview.get(0).getId()).isEqualTo(document3.getId());

        // Test with type that doesn't have documents requiring manual review
        List<Document> bankStatementDocumentsRequiringManualReview = documentRepository
                .findDocumentsRequiringManualReviewByType(DocumentType.BANK_STATEMENT);
        assertThat(bankStatementDocumentsRequiringManualReview).isEmpty();
    }

    /**
     * Tests that the repository can find documents with a specific file extension.
     */
    @Test
    @DisplayName("Should find documents by file extension")
    public void testFindByFileExtension() {
        // Find documents by file extension
        List<Document> pdfDocuments = documentRepository.findByFileExtension("pdf");

        // Verify documents with PDF extension were found
        assertThat(pdfDocuments).hasSize(2);
        assertThat(pdfDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());

        // Test with another extension
        List<Document> jpgDocuments = documentRepository.findByFileExtension("jpg");
        assertThat(jpgDocuments).hasSize(2);
        assertThat(jpgDocuments).extracting(Document::getId)
                .contains(document3.getId(), document4.getId());

        // Test with another extension (case insensitive)
        List<Document> pngDocuments = documentRepository.findByFileExtension("PNG");
        assertThat(pngDocuments).hasSize(1);
        assertThat(pngDocuments.get(0).getId()).isEqualTo(document5.getId());

        // Test with non-existent extension
        List<Document> docxDocuments = documentRepository.findByFileExtension("docx");
        assertThat(docxDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents with a specific MIME type.
     */
    @Test
    @DisplayName("Should find documents by MIME type")
    public void testFindByMimeType() {
        // Find documents by MIME type
        List<Document> pdfDocuments = documentRepository.findByMimeType("application/pdf");

        // Verify documents with PDF MIME type were found
        assertThat(pdfDocuments).hasSize(2);
        assertThat(pdfDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId());

        // Test with another MIME type
        List<Document> jpegDocuments = documentRepository.findByMimeType("image/jpeg");
        assertThat(jpegDocuments).hasSize(2);
        assertThat(jpegDocuments).extracting(Document::getId)
                .contains(document3.getId(), document4.getId());

        // Test with another MIME type
        List<Document> pngDocuments = documentRepository.findByMimeType("image/png");
        assertThat(pngDocuments).hasSize(1);
        assertThat(pngDocuments.get(0).getId()).isEqualTo(document5.getId());

        // Test with non-existent MIME type
        List<Document> wordDocuments = documentRepository.findByMimeType("application/msword");
        assertThat(wordDocuments).isEmpty();
    }

    /**
     * Tests that the repository can find documents in a specific S3 bucket.
     */
    @Test
    @DisplayName("Should find documents by bucket name")
    public void testFindByBucketName() {
        // Find documents by bucket name
        List<Document> productionBucketDocuments = documentRepository.findByBucketName("mca-documents-production");

        // Verify documents in the production bucket were found
        assertThat(productionBucketDocuments).hasSize(5);

        // Test with non-existent bucket name
        List<Document> stagingBucketDocuments = documentRepository.findByBucketName("mca-documents-staging");
        assertThat(stagingBucketDocuments).isEmpty();
    }

    /**
     * Tests that the repository can delete all documents associated with a specific application.
     */
    @Test
    @DisplayName("Should delete documents by application ID")
    public void testDeleteByApplicationId() {
        // Delete documents by application ID
        long deletedCount = documentRepository.deleteByApplicationId(application1.getId());
        entityManager.flush();

        // Verify documents for application1 were deleted
        assertThat(deletedCount).isEqualTo(2);
        List<Document> remainingDocuments = documentRepository.findAll();
        assertThat(remainingDocuments).hasSize(3);
        assertThat(remainingDocuments).extracting(Document::getId)
                .contains(document3.getId(), document4.getId(), document5.getId());

        // Verify no documents remain for application1
        List<Document> application1Documents = documentRepository.findByApplicationId(application1.getId());
        assertThat(application1Documents).isEmpty();
    }

    /**
     * Tests that the repository can delete all documents of a specific type.
     */
    @Test
    @DisplayName("Should delete documents by type")
    public void testDeleteByType() {
        // Delete documents by type
        long deletedCount = documentRepository.deleteByType(DocumentType.BANK_STATEMENT);
        entityManager.flush();

        // Verify bank statement documents were deleted
        assertThat(deletedCount).isEqualTo(1);
        List<Document> remainingDocuments = documentRepository.findAll();
        assertThat(remainingDocuments).hasSize(4);
        assertThat(remainingDocuments).extracting(Document::getId)
                .contains(document2.getId(), document3.getId(), document4.getId(), document5.getId());

        // Verify no bank statement documents remain
        List<Document> bankStatementDocuments = documentRepository.findByType(DocumentType.BANK_STATEMENT);
        assertThat(bankStatementDocuments).isEmpty();
    }

    /**
     * Tests that the repository can delete all documents with a specific classification.
     */
    @Test
    @DisplayName("Should delete documents by classification")
    public void testDeleteByClassification() {
        // Delete documents by classification
        long deletedCount = documentRepository.deleteByClassification(DocumentClassification.REJECTED);
        entityManager.flush();

        // Verify rejected documents were deleted
        assertThat(deletedCount).isEqualTo(1);
        List<Document> remainingDocuments = documentRepository.findAll();
        assertThat(remainingDocuments).hasSize(4);
        assertThat(remainingDocuments).extracting(Document::getId)
                .contains(document1.getId(), document2.getId(), document3.getId(), document5.getId());

        // Verify no rejected documents remain
        List<Document> rejectedDocuments = documentRepository.findByClassification(DocumentClassification.REJECTED);
        assertThat(rejectedDocuments).isEmpty();
    }

    /**
     * Tests that the repository can delete all documents uploaded before a specific date.
     */
    @Test
    @DisplayName("Should delete documents uploaded before a specific date")
    public void testDeleteByUploadedAtBefore() {
        // Delete documents uploaded before a specific date
        LocalDateTime date = LocalDateTime.now().minusDays(3).withHour(0).withMinute(0).withSecond(0);
        long deletedCount = documentRepository.deleteByUploadedAtBefore(date);
        entityManager.flush();

        // Verify documents uploaded before the date were deleted
        assertThat(deletedCount).isEqualTo(2);
        List<Document> remainingDocuments = documentRepository.findAll();
        assertThat(remainingDocuments).hasSize(3);
        assertThat(remainingDocuments).extracting(Document::getId)
                .contains(document3.getId(), document4.getId(), document5.getId());

        // Verify no documents uploaded before the date remain
        List<Document> documentsBeforeDate = documentRepository.findByUploadedAtBefore(date);
        assertThat(documentsBeforeDate).isEmpty();
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

        // Test setting a different application
        documentWithApplication.setApplication(application2);
        entityManager.flush();

        // Verify the application relationship was updated
        Document updatedDocument = entityManager.find(Document.class, document1.getId());
        assertThat(updatedDocument.getApplication().getId()).isEqualTo(application2.getId());
        assertThat(updatedDocument.getApplicationId()).isEqualTo(application2.getId());

        // Test setting application ID directly
        updatedDocument.setApplicationId(application1.getId());
        entityManager.flush();

        // Verify the application ID was updated
        Document documentAfterIdUpdate = entityManager.find(Document.class, document1.getId());
        assertThat(documentAfterIdUpdate.getApplicationId()).isEqualTo(application1.getId());
    }

    /**
     * Tests the Document entity's metadata handling methods.
     */
    @Test
    @DisplayName("Should handle Document entity metadata methods")
    public void testDocumentEntityMetadataMethods() {
        // Test getMetadata method
        Map<String, Object> metadata = document1.getMetadata();
        assertThat(metadata).isNotNull();
        assertThat(metadata).containsEntry("confidenceScore", 0.98);
        assertThat(metadata).containsEntry("pageCount", 5);

        // Test getMetadataValue method
        assertThat(document1.getMetadataValue("confidenceScore")).isEqualTo(0.98);
        assertThat(document1.getMetadataValue("pageCount")).isEqualTo(5);

        // Test addMetadata method
        document1.addMetadata("new_key", "new_value");
        assertThat(document1.getMetadataValue("new_key")).isEqualTo("new_value");

        // Test setMetadata method
        Map<String, Object> newMetadata = new HashMap<>();
        newMetadata.put("completely_new", "completely_new_value");
        newMetadata.put("another_key", 123);
        document1.setMetadata(newMetadata);

        assertThat(document1.getMetadata()).isEqualTo(newMetadata);
        assertThat(document1.getMetadataValue("confidenceScore")).isNull(); // Old key is gone
        assertThat(document1.getMetadataValue("completely_new")).isEqualTo("completely_new_value");
        assertThat(document1.getMetadataValue("another_key")).isEqualTo(123);

        // Test JSON conversion
        String metadataJson = document1.getMetadataJson();
        assertThat(metadataJson).isNotNull();
        assertThat(metadataJson).contains("completely_new");
        assertThat(metadataJson).contains("completely_new_value");
        assertThat(metadataJson).contains("another_key");
        assertThat(metadataJson).contains("123");

        // Test setMetadataJson method
        String newMetadataJson = "{\"json_key\": \"json_value\", \"json_number\": 456}";
        document1.setMetadataJson(newMetadataJson);

        assertThat(document1.getMetadataValue("json_key")).isEqualTo("json_value");
        assertThat(document1.getMetadataValue("json_number")).isEqualTo(456);
    }

    /**
     * Tests the Document entity's utility methods.
     */
    @Test
    @DisplayName("Should handle Document entity utility methods")
    public void testDocumentEntityUtilityMethods() {
        // Test getFileName method
        assertThat(document1.getFileName()).isEqualTo("statement-" + application1.getId() + ".pdf");

        // Test getFileExtension method
        assertThat(document1.getFileExtension()).isEqualTo("pdf");
        assertThat(document3.getFileExtension()).isEqualTo("jpg");
        assertThat(document5.getFileExtension()).isEqualTo("png");

        // Test getMimeType method
        assertThat(document1.getMimeType()).isEqualTo("application/pdf");
        assertThat(document3.getMimeType()).isEqualTo("image/jpeg");
        assertThat(document5.getMimeType()).isEqualTo("image/png");

        // Test requiresManualReview method
        assertThat(document1.requiresManualReview()).isFalse(); // VERIFIED
        assertThat(document2.requiresManualReview()).isTrue();  // NEEDS_REVIEW
        assertThat(document3.requiresManualReview()).isTrue();  // FLAGGED
        assertThat(document4.requiresManualReview()).isFalse(); // REJECTED
        assertThat(document5.requiresManualReview()).isFalse(); // UNCLASSIFIED

        // Test isAcceptable method
        assertThat(document1.isAcceptable()).isTrue();  // VERIFIED
        assertThat(document2.isAcceptable()).isTrue();  // NEEDS_REVIEW
        assertThat(document3.isAcceptable()).isFalse(); // FLAGGED
        assertThat(document4.isAcceptable()).isFalse(); // REJECTED
        assertThat(document5.isAcceptable()).isFalse(); // UNCLASSIFIED

        // Test getBucketName method
        assertThat(document1.getBucketName()).isEqualTo("mca-documents-production");

        // Test getObjectKey method
        assertThat(document1.getObjectKey()).isEqualTo("bank-statements/statement-" + application1.getId() + ".pdf");

        // Test getConfidenceScore method
        assertThat(document1.getConfidenceScore()).isEqualTo(0.98);
        assertThat(document2.getConfidenceScore()).isEqualTo(0.75);
        assertThat(document3.getConfidenceScore()).isEqualTo(0.65);
        assertThat(document4.getConfidenceScore()).isEqualTo(0.35);
        assertThat(document5.getConfidenceScore()).isEqualTo(0.0);

        // Test setConfidenceScore method
        document5.setConfidenceScore(0.85);
        assertThat(document5.getConfidenceScore()).isEqualTo(0.85);
        assertThat(document5.getClassification()).isEqualTo(DocumentClassification.NEEDS_REVIEW); // Classification updated based on score
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
                DocumentType.INVOICE,
                "mca-documents-production/invoices/invoice-builder-test.pdf")
                .withClassification(DocumentClassification.VERIFIED)
                .withUploadedAt(LocalDateTime.now())
                .addMetadata("confidenceScore", 0.99)
                .addMetadata("invoiceAmount", 10000.00)
                .addMetadata("invoiceNumber", "INV-12345");

        Document builtDocument = builder.build();

        // Save the document
        Document savedDocument = documentRepository.save(builtDocument);

        // Verify the document was saved with the correct properties
        assertThat(savedDocument.getId()).isNotNull();
        assertThat(savedDocument.getType()).isEqualTo(DocumentType.INVOICE);
        assertThat(savedDocument.getClassification()).isEqualTo(DocumentClassification.VERIFIED);
        assertThat(savedDocument.getStoragePath()).isEqualTo("mca-documents-production/invoices/invoice-builder-test.pdf");
        assertThat(savedDocument.getMetadataValue("confidenceScore")).isEqualTo(0.99);
        assertThat(savedDocument.getMetadataValue("invoiceAmount")).isEqualTo(10000.00);
        assertThat(savedDocument.getMetadataValue("invoiceNumber")).isEqualTo("INV-12345");
    }
}