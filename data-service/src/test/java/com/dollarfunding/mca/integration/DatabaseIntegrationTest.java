package com.dollarfunding.mca.integration;

import com.dollarfunding.mca.cache.CacheConstants;
import com.dollarfunding.mca.cache.RedisCacheService;
import com.dollarfunding.mca.entity.*;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.repository.MerchantDetailsRepository;
import com.dollarfunding.mca.repository.WebhookRepository;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cache.CacheManager;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.DefaultTransactionDefinition;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.RedisContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test for database operations with PostgreSQL and Redis caching.
 * 
 * This test verifies:
 * 1. Database CRUD operations and transaction management
 * 2. Redis caching with appropriate TTL settings
 * 3. Field-level encryption for PII data
 * 4. Flyway migrations
 * 5. Validation rules
 */
@SpringBootTest
@Testcontainers
@ActiveProfiles("test")
public class DatabaseIntegrationTest {

    @Container
    private static final PostgreSQLContainer<?> postgresContainer = new PostgreSQLContainer<>("postgres:14")
            .withDatabaseName("mca_test")
            .withUsername("test")
            .withPassword("test");

    @Container
    private static final RedisContainer redisContainer = new RedisContainer("redis:7.0")
            .withExposedPorts(6379);

    @DynamicPropertySource
    static void registerDynamicProperties(DynamicPropertyRegistry registry) {
        // PostgreSQL properties
        registry.add("spring.datasource.url", postgresContainer::getJdbcUrl);
        registry.add("spring.datasource.username", postgresContainer::getUsername);
        registry.add("spring.datasource.password", postgresContainer::getPassword);
        
        // Redis properties
        registry.add("spring.redis.host", redisContainer::getHost);
        registry.add("spring.redis.port", redisContainer::getFirstMappedPort);
    }

    @Autowired
    private ApplicationRepository applicationRepository;

    @Autowired
    private DocumentRepository documentRepository;

    @Autowired
    private MerchantDetailsRepository merchantDetailsRepository;

    @Autowired
    private WebhookRepository webhookRepository;

    @Autowired
    private PlatformTransactionManager transactionManager;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private Flyway flyway;

    @Autowired
    private CacheManager cacheManager;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private RedisCacheService cacheService;

    @BeforeEach
    void setUp() {
        // Clear all data before each test
        documentRepository.deleteAll();
        merchantDetailsRepository.deleteAll();
        applicationRepository.deleteAll();
        webhookRepository.deleteAll();
        
        // Clear Redis cache
        Objects.requireNonNull(cacheManager.getCache(CacheConstants.CACHE_APPLICATIONS)).clear();
        Objects.requireNonNull(cacheManager.getCache(CacheConstants.CACHE_DOCUMENTS)).clear();
        Objects.requireNonNull(cacheManager.getCache(CacheConstants.CACHE_MERCHANTS)).clear();
    }

    @AfterEach
    void tearDown() {
        // Additional cleanup if needed
    }

    /**
     * Test basic CRUD operations for Application entity.
     */
    @Test
    void testApplicationCrudOperations() {
        // Create application
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("source", "email");
        metadata.put("priority", "high");
        application.setMetadata(metadata);
        
        Application savedApplication = applicationRepository.save(application);
        
        // Read application
        Optional<Application> retrievedApp = applicationRepository.findById(savedApplication.getId());
        assertTrue(retrievedApp.isPresent());
        assertEquals(ApplicationStatus.NEW, retrievedApp.get().getStatus());
        assertEquals(ReviewStatus.NOT_REVIEWED, retrievedApp.get().getReviewStatus());
        assertEquals("email", retrievedApp.get().getMetadata().get("source"));
        assertEquals("high", retrievedApp.get().getMetadata().get("priority"));
        
        // Update application
        Application appToUpdate = retrievedApp.get();
        appToUpdate.setStatus(ApplicationStatus.PROCESSING);
        appToUpdate.setReviewStatus(ReviewStatus.IN_REVIEW);
        applicationRepository.save(appToUpdate);
        
        Optional<Application> updatedApp = applicationRepository.findById(savedApplication.getId());
        assertTrue(updatedApp.isPresent());
        assertEquals(ApplicationStatus.PROCESSING, updatedApp.get().getStatus());
        assertEquals(ReviewStatus.IN_REVIEW, updatedApp.get().getReviewStatus());
        
        // Delete application
        applicationRepository.delete(updatedApp.get());
        assertFalse(applicationRepository.findById(savedApplication.getId()).isPresent());
    }

    /**
     * Test transaction management with commit and rollback scenarios.
     */
    @Test
    void testTransactionManagement() {
        // Test successful transaction (commit)
        DefaultTransactionDefinition txDef = new DefaultTransactionDefinition();
        txDef.setIsolationLevel(TransactionDefinition.ISOLATION_READ_COMMITTED);
        TransactionStatus txStatus = transactionManager.getTransaction(txDef);
        
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Application savedApplication = applicationRepository.save(application);
        
        transactionManager.commit(txStatus);
        
        // Verify application was saved
        assertTrue(applicationRepository.findById(savedApplication.getId()).isPresent());
        
        // Test transaction rollback
        txStatus = transactionManager.getTransaction(txDef);
        
        Application application2 = new Application();
        application2.setStatus(ApplicationStatus.PENDING);
        application2.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Application savedApplication2 = applicationRepository.save(application2);
        
        // Get the ID before rollback
        Long app2Id = savedApplication2.getId();
        
        // Rollback the transaction
        transactionManager.rollback(txStatus);
        
        // Verify application was not saved due to rollback
        assertFalse(applicationRepository.findById(app2Id).isPresent());
    }

    /**
     * Test Redis caching with appropriate TTL settings.
     * - Application data: 15 minutes TTL
     * - User sessions: 24 hours TTL
     */
    @Test
    void testRedisCaching() throws Exception {
        // Create test data
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Application savedApplication = applicationRepository.save(application);
        
        // Cache application data (15 minutes TTL)
        String appCacheKey = "application:" + savedApplication.getId();
        cacheService.put(CacheConstants.CACHE_APPLICATIONS, appCacheKey, savedApplication);
        
        // Verify data is cached
        assertTrue(cacheService.exists(CacheConstants.CACHE_APPLICATIONS, appCacheKey));
        
        // Verify TTL is set correctly (15 minutes = 900 seconds)
        Long ttl = redisTemplate.getExpire(CacheConstants.CACHE_APPLICATIONS + ":" + appCacheKey);
        assertNotNull(ttl);
        assertTrue(ttl <= 900 && ttl > 0, "TTL should be less than or equal to 900 seconds but greater than 0");
        
        // Test user session caching (24 hours TTL)
        String sessionKey = "user:session:123";
        Map<String, Object> sessionData = new HashMap<>();
        sessionData.put("userId", 123);
        sessionData.put("role", "Operations Staff");
        
        cacheService.put(CacheConstants.CACHE_SESSIONS, sessionKey, sessionData);
        
        // Verify session data is cached
        assertTrue(cacheService.exists(CacheConstants.CACHE_SESSIONS, sessionKey));
        
        // Verify TTL is set correctly (24 hours = 86400 seconds)
        Long sessionTtl = redisTemplate.getExpire(CacheConstants.CACHE_SESSIONS + ":" + sessionKey);
        assertNotNull(sessionTtl);
        assertTrue(sessionTtl <= 86400 && sessionTtl > 0, "Session TTL should be less than or equal to 86400 seconds but greater than 0");
        
        // Test cache eviction
        cacheService.evict(CacheConstants.CACHE_APPLICATIONS, appCacheKey);
        assertFalse(cacheService.exists(CacheConstants.CACHE_APPLICATIONS, appCacheKey));
    }

    /**
     * Test field-level encryption for PII data in MerchantDetails entity.
     */
    @Test
    void testFieldLevelEncryption() {
        // Create application
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Application savedApplication = applicationRepository.save(application);
        
        // Create merchant details with PII data
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setApplication(savedApplication);
        merchantDetails.setLegalName("Acme Corporation"); // PII - should be encrypted
        merchantDetails.setDbaName("Acme"); // PII - should be encrypted
        merchantDetails.setEin("12-3456789"); // PII - should be encrypted
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(new BigDecimal("1000000.00"));
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "New York");
        address.put("state", "NY");
        address.put("zip", "10001");
        merchantDetails.setAddress(address);
        
        MerchantDetails savedMerchant = merchantDetailsRepository.save(merchantDetails);
        
        // Verify merchant details were saved
        Optional<MerchantDetails> retrievedMerchant = merchantDetailsRepository.findById(savedMerchant.getId());
        assertTrue(retrievedMerchant.isPresent());
        
        // Verify PII data is correctly decrypted when retrieved through the repository
        assertEquals("Acme Corporation", retrievedMerchant.get().getLegalName());
        assertEquals("Acme", retrievedMerchant.get().getDbaName());
        assertEquals("12-3456789", retrievedMerchant.get().getEin());
        
        // Verify non-PII data is stored correctly
        assertEquals("Technology", retrievedMerchant.get().getIndustry());
        assertEquals(0, new BigDecimal("1000000.00").compareTo(retrievedMerchant.get().getRevenue()));
        assertEquals("123 Main St", retrievedMerchant.get().getAddress().get("street"));
        
        // Verify data is actually encrypted in the database
        // We'll use JdbcTemplate to query the raw data
        Map<String, Object> rawData = jdbcTemplate.queryForMap(
                "SELECT legal_name, dba_name, ein FROM merchant_details WHERE id = ?", 
                savedMerchant.getId());
        
        String encryptedLegalName = (String) rawData.get("legal_name");
        String encryptedDbaName = (String) rawData.get("dba_name");
        String encryptedEin = (String) rawData.get("ein");
        
        // Encrypted data should not match the original values
        assertNotEquals("Acme Corporation", encryptedLegalName);
        assertNotEquals("Acme", encryptedDbaName);
        assertNotEquals("12-3456789", encryptedEin);
    }

    /**
     * Test Flyway migrations to ensure database schema is correctly created.
     */
    @Test
    void testFlywayMigrations() {
        // Verify Flyway migrations have been applied
        List<Map<String, Object>> migrations = jdbcTemplate.queryForList(
                "SELECT version, description FROM flyway_schema_history ORDER BY installed_rank");
        
        assertFalse(migrations.isEmpty(), "No Flyway migrations found");
        
        // Verify specific migrations exist
        boolean foundV1 = false;
        boolean foundV2 = false;
        boolean foundV3 = false;
        
        for (Map<String, Object> migration : migrations) {
            String version = (String) migration.get("version");
            if ("1".equals(version)) {
                foundV1 = true;
            } else if ("2".equals(version)) {
                foundV2 = true;
            } else if ("3".equals(version)) {
                foundV3 = true;
            }
        }
        
        assertTrue(foundV1, "V1 migration not found");
        assertTrue(foundV2, "V2 migration not found");
        assertTrue(foundV3, "V3 migration not found");
        
        // Verify tables exist
        List<String> tables = jdbcTemplate.queryForList(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                String.class);
        
        assertTrue(tables.contains("application"), "Application table not found");
        assertTrue(tables.contains("document"), "Document table not found");
        assertTrue(tables.contains("merchant_details"), "Merchant details table not found");
        assertTrue(tables.contains("webhook"), "Webhook table not found");
        
        // Verify indexes exist
        List<String> indexes = jdbcTemplate.queryForList(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'",
                String.class);
        
        assertTrue(indexes.contains("idx_application_status"), "Application status index not found");
        assertTrue(indexes.contains("idx_application_review_status"), "Application review status index not found");
        assertTrue(indexes.contains("idx_document_application_id"), "Document application_id index not found");
    }

    /**
     * Test validation rules for entity fields.
     */
    @Test
    void testValidationRules() {
        // Test validation for Application entity
        Application invalidApp = new Application();
        // Status is required but not set
        
        try {
            applicationRepository.save(invalidApp);
            fail("Should have thrown an exception for invalid application");
        } catch (Exception e) {
            // Expected exception
        }
        
        // Test validation for Document entity
        Application validApp = new Application();
        validApp.setStatus(ApplicationStatus.NEW);
        validApp.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Application savedApp = applicationRepository.save(validApp);
        
        Document invalidDoc = new Document();
        // Application is required but not set
        // Type is required but not set
        
        try {
            documentRepository.save(invalidDoc);
            fail("Should have thrown an exception for invalid document");
        } catch (Exception e) {
            // Expected exception
        }
        
        // Test validation for MerchantDetails entity
        MerchantDetails invalidMerchant = new MerchantDetails();
        // Application is required but not set
        // Legal name is required but not set
        
        try {
            merchantDetailsRepository.save(invalidMerchant);
            fail("Should have thrown an exception for invalid merchant details");
        } catch (Exception e) {
            // Expected exception
        }
    }

    /**
     * Test relationships between entities (Application, Document, MerchantDetails).
     */
    @Test
    void testEntityRelationships() {
        // Create application
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Application savedApplication = applicationRepository.save(application);
        
        // Create documents associated with the application
        Document doc1 = new Document();
        doc1.setApplication(savedApplication);
        doc1.setType(DocumentType.BANK_STATEMENT);
        doc1.setClassification("high_confidence");
        doc1.setStoragePath("s3://mca-documents-test/app-" + savedApplication.getId() + "/bank-statement.pdf");
        doc1.setUploadedAt(LocalDateTime.now());
        
        Document doc2 = new Document();
        doc2.setApplication(savedApplication);
        doc2.setType(DocumentType.TAX_RETURN);
        doc2.setClassification("high_confidence");
        doc2.setStoragePath("s3://mca-documents-test/app-" + savedApplication.getId() + "/tax-return.pdf");
        doc2.setUploadedAt(LocalDateTime.now());
        
        documentRepository.save(doc1);
        documentRepository.save(doc2);
        
        // Create merchant details associated with the application
        MerchantDetails merchantDetails = new MerchantDetails();
        merchantDetails.setApplication(savedApplication);
        merchantDetails.setLegalName("Acme Corporation");
        merchantDetails.setDbaName("Acme");
        merchantDetails.setEin("12-3456789");
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(new BigDecimal("1000000.00"));
        
        Map<String, Object> address = new HashMap<>();
        address.put("street", "123 Main St");
        address.put("city", "New York");
        address.put("state", "NY");
        address.put("zip", "10001");
        merchantDetails.setAddress(address);
        
        merchantDetailsRepository.save(merchantDetails);
        
        // Test bidirectional relationship: Application -> Documents
        Optional<Application> retrievedApp = applicationRepository.findById(savedApplication.getId());
        assertTrue(retrievedApp.isPresent());
        
        List<Document> appDocuments = retrievedApp.get().getDocuments();
        assertEquals(2, appDocuments.size());
        
        // Test bidirectional relationship: Application -> MerchantDetails
        MerchantDetails appMerchant = retrievedApp.get().getMerchantDetails();
        assertNotNull(appMerchant);
        assertEquals("Acme Corporation", appMerchant.getLegalName());
        
        // Test bidirectional relationship: Document -> Application
        Optional<Document> retrievedDoc = documentRepository.findById(doc1.getId());
        assertTrue(retrievedDoc.isPresent());
        assertEquals(savedApplication.getId(), retrievedDoc.get().getApplication().getId());
        
        // Test bidirectional relationship: MerchantDetails -> Application
        Optional<MerchantDetails> retrievedMerchant = merchantDetailsRepository.findById(merchantDetails.getId());
        assertTrue(retrievedMerchant.isPresent());
        assertEquals(savedApplication.getId(), retrievedMerchant.get().getApplication().getId());
        
        // Test cascade delete: deleting an application should delete associated documents and merchant details
        applicationRepository.delete(savedApplication);
        
        // Verify documents were deleted
        assertFalse(documentRepository.findById(doc1.getId()).isPresent());
        assertFalse(documentRepository.findById(doc2.getId()).isPresent());
        
        // Verify merchant details were deleted
        assertFalse(merchantDetailsRepository.findById(merchantDetails.getId()).isPresent());
    }

    /**
     * Test cache invalidation when entities are updated.
     */
    @Test
    void testCacheInvalidation() throws Exception {
        // Create application
        Application application = new Application();
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        Application savedApplication = applicationRepository.save(application);
        
        // Cache application
        String cacheKey = "application:" + savedApplication.getId();
        cacheService.put(CacheConstants.CACHE_APPLICATIONS, cacheKey, savedApplication);
        
        // Verify application is in cache
        assertTrue(cacheService.exists(CacheConstants.CACHE_APPLICATIONS, cacheKey));
        
        // Update application
        savedApplication.setStatus(ApplicationStatus.PROCESSING);
        applicationRepository.save(savedApplication);
        
        // Evict from cache
        cacheService.evict(CacheConstants.CACHE_APPLICATIONS, cacheKey);
        
        // Verify application is no longer in cache
        assertFalse(cacheService.exists(CacheConstants.CACHE_APPLICATIONS, cacheKey));
        
        // Cache application again
        cacheService.put(CacheConstants.CACHE_APPLICATIONS, cacheKey, savedApplication);
        
        // Verify application is in cache again
        assertTrue(cacheService.exists(CacheConstants.CACHE_APPLICATIONS, cacheKey));
        
        // Wait for TTL expiration (using a very short TTL for testing)
        // Note: In a real test, we would mock the time or use a test-specific TTL
        await().atMost(2, TimeUnit.SECONDS).until(() -> {
            return !cacheService.exists(CacheConstants.CACHE_APPLICATIONS, cacheKey);
        });
    }
}