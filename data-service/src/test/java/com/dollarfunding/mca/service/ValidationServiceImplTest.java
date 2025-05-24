package com.dollarfunding.mca.service;

import com.dollarfunding.mca.cache.CacheConstants;
import com.dollarfunding.mca.cache.CacheKeyGenerator;
import com.dollarfunding.mca.cache.RedisCacheService;
import com.dollarfunding.mca.dto.ApplicationRequestDTO;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.ApplicationStatus;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.entity.ReviewStatus;
import com.dollarfunding.mca.util.ErrorUtil;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the ValidationServiceImpl class that handles data validation and business rule application.
 * Tests verify schema validation, business rule application, validation result reporting, and caching of validation results.
 */
@ExtendWith(MockitoExtension.class)
public class ValidationServiceImplTest {

    @Mock
    private RedisCacheService cacheService;

    @Mock
    private CacheKeyGenerator cacheKeyGenerator;

    @Mock
    private ErrorUtil errorUtil;

    @InjectMocks
    private ValidationServiceImpl validationService;

    // Test data
    private ApplicationRequestDTO applicationRequestDTO;
    private DocumentRequestDTO documentRequestDTO;
    private MerchantDetailsRequestDTO merchantDetailsRequestDTO;
    private Application application;
    private Document document;
    private MerchantDetails merchantDetails;
    private List<Document> documents;

    @BeforeEach
    void setUp() {
        // Initialize ValidationServiceImpl manually to call @PostConstruct method
        validationService = new ValidationServiceImpl();
        validationService = spy(validationService);
        
        // Inject mocks
        ReflectionTestUtils.setField(validationService, "cacheService", cacheService);
        ReflectionTestUtils.setField(validationService, "cacheKeyGenerator", cacheKeyGenerator);
        ReflectionTestUtils.setField(validationService, "errorUtil", errorUtil);
        
        // Call init method manually since @PostConstruct won't be called in tests
        validationService.init();
        
        // Setup test data
        setupTestData();
    }

    private void setupTestData() {
        // Setup ApplicationRequestDTO
        applicationRequestDTO = new ApplicationRequestDTO();
        applicationRequestDTO.setStatus(ApplicationStatus.NEW);
        applicationRequestDTO.setMetadata("{\"requestedAmount\": 50000, \"businessName\": \"Test Business\"}");

        // Setup DocumentRequestDTO
        documentRequestDTO = new DocumentRequestDTO();
        documentRequestDTO.setType(DocumentType.BANK_STATEMENT);
        documentRequestDTO.setApplicationId(1L);
        documentRequestDTO.setMetadata("{\"accountNumber\": \"123456789\", \"bankName\": \"Test Bank\"}");

        // Setup MerchantDetailsRequestDTO
        merchantDetailsRequestDTO = new MerchantDetailsRequestDTO();
        merchantDetailsRequestDTO.setApplicationId(1L);
        merchantDetailsRequestDTO.setLegalName("Test Merchant Inc.");
        merchantDetailsRequestDTO.setDbaName("Test Merchant");
        merchantDetailsRequestDTO.setEin("12-3456789");
        Map<String, Object> address = new HashMap<>();
        address.put("street1", "123 Test St");
        address.put("city", "Test City");
        address.put("state", "TS");
        address.put("zipCode", "12345");
        merchantDetailsRequestDTO.setAddress(address);
        merchantDetailsRequestDTO.setIndustry("Technology");
        merchantDetailsRequestDTO.setRevenue(500000.0);

        // Setup Application entity
        application = new Application();
        application.setId(1L);
        application.setStatus(ApplicationStatus.NEW);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        application.setCreatedAt(LocalDateTime.now());
        application.setUpdatedAt(LocalDateTime.now());
        application.setMetadata("{\"requestedAmount\": 50000, \"businessName\": \"Test Business\"}");

        // Setup Document entity
        document = new Document();
        document.setId(1L);
        document.setApplication(application);
        document.setType(DocumentType.BANK_STATEMENT);
        document.setStoragePath("s3://mca-documents/1/bank-statement.pdf");
        document.setUploadedAt(LocalDateTime.now());
        document.setMetadata("{\"accountNumber\": \"123456789\", \"bankName\": \"Test Bank\", \"statementDate\": \"2023-01-01\", \"averageDailyBalance\": 10000, \"totalDeposits\": 25000}");

        // Setup MerchantDetails entity
        merchantDetails = new MerchantDetails();
        merchantDetails.setId(1L);
        merchantDetails.setApplication(application);
        merchantDetails.setLegalName("Test Merchant Inc.");
        merchantDetails.setDbaName("Test Merchant");
        merchantDetails.setEin("12-3456789");
        merchantDetails.setAddress("{\"street1\": \"123 Test St\", \"city\": \"Test City\", \"state\": \"TS\", \"zipCode\": \"12345\"}");
        merchantDetails.setIndustry("Technology");
        merchantDetails.setRevenue(500000.0);
        merchantDetails.setMetadata("{\"businessStartDate\": \"2020-01-01\"}");

        // Setup documents list
        documents = new ArrayList<>();
        documents.add(document);

        // Add documents to application
        application.setDocuments(documents);
        application.setMerchantDetails(merchantDetails);
    }

    @Test
    @DisplayName("Test validateApplicationData with valid data")
    void testValidateApplicationDataWithValidData() {
        // Setup
        String cacheKey = "app-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateApplicationData(applicationRequestDTO);

        // Verify
        assertTrue(result.isEmpty(), "Validation should pass with no errors");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApplicationData with invalid data")
    void testValidateApplicationDataWithInvalidData() {
        // Setup
        applicationRequestDTO.setStatus(null); // Invalid: status is required
        applicationRequestDTO.setMetadata("invalid-json"); // Invalid: not a valid JSON

        String cacheKey = "app-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateApplicationData(applicationRequestDTO);

        // Verify
        assertFalse(result.isEmpty(), "Validation should fail with errors");
        assertEquals(2, result.size(), "Should have 2 validation errors");
        assertTrue(result.containsKey("status"), "Should have error for status");
        assertTrue(result.containsKey("metadata"), "Should have error for metadata");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApplicationData with cached result")
    void testValidateApplicationDataWithCachedResult() {
        // Setup
        String cacheKey = "app-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application"), anyInt()))
                .thenReturn(cacheKey);

        // Create a cached validation result
        Map<String, String> cachedErrors = new HashMap<>();
        cachedErrors.put("test", "Cached error");
        ValidationResult cachedResult = new ValidationResult(false, cachedErrors);

        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(cachedResult); // Return cached result

        // Execute
        Map<String, String> result = validationService.validateApplicationData(applicationRequestDTO);

        // Verify
        assertFalse(result.isEmpty(), "Should return cached validation errors");
        assertEquals(1, result.size(), "Should have 1 validation error from cache");
        assertEquals("Cached error", result.get("test"), "Should return the cached error message");
        verify(cacheService, never()).put(anyString(), any(), anyLong()); // Should not cache again
    }

    @Test
    @DisplayName("Test validateDocumentData with valid data")
    void testValidateDocumentDataWithValidData() {
        // Setup
        String cacheKey = "doc-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("document"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateDocumentData(documentRequestDTO);

        // Verify
        assertTrue(result.isEmpty(), "Validation should pass with no errors");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDocumentData with invalid data")
    void testValidateDocumentDataWithInvalidData() {
        // Setup
        documentRequestDTO.setType(null); // Invalid: type is required
        documentRequestDTO.setApplicationId(null); // Invalid: applicationId is required
        documentRequestDTO.setMetadata("invalid-json"); // Invalid: not a valid JSON

        String cacheKey = "doc-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("document"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateDocumentData(documentRequestDTO);

        // Verify
        assertFalse(result.isEmpty(), "Validation should fail with errors");
        assertEquals(3, result.size(), "Should have 3 validation errors");
        assertTrue(result.containsKey("type"), "Should have error for type");
        assertTrue(result.containsKey("applicationId"), "Should have error for applicationId");
        assertTrue(result.containsKey("metadata"), "Should have error for metadata");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateMerchantDetails with valid data")
    void testValidateMerchantDetailsWithValidData() {
        // Setup
        String cacheKey = "merchant-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateMerchantDetails(merchantDetailsRequestDTO);

        // Verify
        assertTrue(result.isEmpty(), "Validation should pass with no errors");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateMerchantDetails with invalid data")
    void testValidateMerchantDetailsWithInvalidData() {
        // Setup
        merchantDetailsRequestDTO.setApplicationId(null); // Invalid: applicationId is required
        merchantDetailsRequestDTO.setLegalName(""); // Invalid: legalName is required
        merchantDetailsRequestDTO.setEin("invalid-ein"); // Invalid: ein format
        merchantDetailsRequestDTO.setAddress(null); // Invalid: address is required
        merchantDetailsRequestDTO.setIndustry(""); // Invalid: industry is required
        merchantDetailsRequestDTO.setRevenue(-1.0); // Invalid: revenue must be positive

        String cacheKey = "merchant-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateMerchantDetails(merchantDetailsRequestDTO);

        // Verify
        assertFalse(result.isEmpty(), "Validation should fail with errors");
        assertEquals(6, result.size(), "Should have 6 validation errors");
        assertTrue(result.containsKey("applicationId"), "Should have error for applicationId");
        assertTrue(result.containsKey("legalName"), "Should have error for legalName");
        assertTrue(result.containsKey("ein"), "Should have error for ein");
        assertTrue(result.containsKey("address"), "Should have error for address");
        assertTrue(result.containsKey("industry"), "Should have error for industry");
        assertTrue(result.containsKey("revenue"), "Should have error for revenue");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateMerchantDetails with invalid address")
    void testValidateMerchantDetailsWithInvalidAddress() {
        // Setup
        Map<String, Object> invalidAddress = new HashMap<>();
        invalidAddress.put("street1", "123 Test St");
        // Missing city, state, zipCode
        merchantDetailsRequestDTO.setAddress(invalidAddress);

        String cacheKey = "merchant-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateMerchantDetails(merchantDetailsRequestDTO);

        // Verify
        assertFalse(result.isEmpty(), "Validation should fail with errors");
        assertTrue(result.containsKey("address"), "Should have error for address");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateMerchantDetails with invalid zip code")
    void testValidateMerchantDetailsWithInvalidZipCode() {
        // Setup
        Map<String, Object> addressWithInvalidZip = new HashMap<>();
        addressWithInvalidZip.put("street1", "123 Test St");
        addressWithInvalidZip.put("city", "Test City");
        addressWithInvalidZip.put("state", "TS");
        addressWithInvalidZip.put("zipCode", "invalid-zip"); // Invalid zip code format
        merchantDetailsRequestDTO.setAddress(addressWithInvalidZip);

        String cacheKey = "merchant-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant"), anyInt()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        Map<String, String> result = validationService.validateMerchantDetails(merchantDetailsRequestDTO);

        // Verify
        assertFalse(result.isEmpty(), "Validation should fail with errors");
        assertTrue(result.containsKey("address.zipCode"), "Should have error for address.zipCode");
        verify(cacheService).put(eq(cacheKey), any(ValidationResult.class), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApplication with valid entity")
    void testValidateApplicationWithValidEntity() {
        // Setup
        String cacheKey = "app-entity-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application_entity"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateApplication(application);

        // Verify
        assertTrue(result.isValid(), "Validation should pass for valid application entity");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApplication with invalid entity")
    void testValidateApplicationWithInvalidEntity() {
        // Setup
        application.setStatus(null); // Invalid: status is required
        application.setReviewStatus(null); // Invalid: reviewStatus is required
        application.setCreatedAt(null); // Invalid: createdAt is required
        application.setUpdatedAt(null); // Invalid: updatedAt is required
        application.setMetadata("invalid-json"); // Invalid: not a valid JSON

        String cacheKey = "app-entity-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application_entity"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateApplication(application);

        // Verify
        assertFalse(result.isValid(), "Validation should fail for invalid application entity");
        assertEquals(5, result.getErrors().size(), "Should have 5 validation errors");
        assertTrue(result.getErrors().containsKey("status"), "Should have error for status");
        assertTrue(result.getErrors().containsKey("reviewStatus"), "Should have error for reviewStatus");
        assertTrue(result.getErrors().containsKey("createdAt"), "Should have error for createdAt");
        assertTrue(result.getErrors().containsKey("updatedAt"), "Should have error for updatedAt");
        assertTrue(result.getErrors().containsKey("metadata"), "Should have error for metadata");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDocument with valid entity")
    void testValidateDocumentWithValidEntity() {
        // Setup
        String cacheKey = "doc-entity-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("document_entity"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateDocument(document);

        // Verify
        assertTrue(result.isValid(), "Validation should pass for valid document entity");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDocument with invalid entity")
    void testValidateDocumentWithInvalidEntity() {
        // Setup
        document.setType(null); // Invalid: type is required
        document.setApplication(null); // Invalid: application is required
        document.setStoragePath(""); // Invalid: storagePath is required
        document.setUploadedAt(null); // Invalid: uploadedAt is required
        document.setMetadata("invalid-json"); // Invalid: not a valid JSON

        String cacheKey = "doc-entity-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("document_entity"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateDocument(document);

        // Verify
        assertFalse(result.isValid(), "Validation should fail for invalid document entity");
        assertEquals(5, result.getErrors().size(), "Should have 5 validation errors");
        assertTrue(result.getErrors().containsKey("type"), "Should have error for type");
        assertTrue(result.getErrors().containsKey("application"), "Should have error for application");
        assertTrue(result.getErrors().containsKey("storagePath"), "Should have error for storagePath");
        assertTrue(result.getErrors().containsKey("uploadedAt"), "Should have error for uploadedAt");
        assertTrue(result.getErrors().containsKey("metadata"), "Should have error for metadata");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateMerchant with valid entity")
    void testValidateMerchantWithValidEntity() {
        // Setup
        String cacheKey = "merchant-entity-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant_entity"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateMerchant(merchantDetails);

        // Verify
        assertTrue(result.isValid(), "Validation should pass for valid merchant entity");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateMerchant with invalid entity")
    void testValidateMerchantWithInvalidEntity() {
        // Setup
        merchantDetails.setApplication(null); // Invalid: application is required
        merchantDetails.setLegalName(""); // Invalid: legalName is required
        merchantDetails.setEin("invalid-ein"); // Invalid: ein format
        merchantDetails.setAddress(""); // Invalid: address is required
        merchantDetails.setIndustry(""); // Invalid: industry is required
        merchantDetails.setRevenue(-1.0); // Invalid: revenue must be positive

        String cacheKey = "merchant-entity-validation-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant_entity"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateMerchant(merchantDetails);

        // Verify
        assertFalse(result.isValid(), "Validation should fail for invalid merchant entity");
        assertEquals(6, result.getErrors().size(), "Should have 6 validation errors");
        assertTrue(result.getErrors().containsKey("application"), "Should have error for application");
        assertTrue(result.getErrors().containsKey("legalName"), "Should have error for legalName");
        assertTrue(result.getErrors().containsKey("ein"), "Should have error for ein");
        assertTrue(result.getErrors().containsKey("address"), "Should have error for address");
        assertTrue(result.getErrors().containsKey("industry"), "Should have error for industry");
        assertTrue(result.getErrors().containsKey("revenue"), "Should have error for revenue");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test evaluateApplicationCompleteness with complete application")
    void testEvaluateApplicationCompletenessWithCompleteApplication() {
        // Setup
        // Add required documents
        Document bankStatement1 = createDocument(DocumentType.BANK_STATEMENT, "2023-01-01");
        Document bankStatement2 = createDocument(DocumentType.BANK_STATEMENT, "2023-02-01");
        Document bankStatement3 = createDocument(DocumentType.BANK_STATEMENT, "2023-03-01");
        Document taxReturn = createDocument(DocumentType.TAX_RETURN, "2023-01-01");
        Document businessLicense = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> completeDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );
        
        application.setDocuments(completeDocuments);
        application.setStatus(ApplicationStatus.PROCESSING); // Not NEW or PENDING

        // Mock validation results
        when(validationService.validateMerchant(any(MerchantDetails.class)))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        String cacheKey = "app-completeness-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application_completeness"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.evaluateApplicationCompleteness(application);

        // Verify
        assertTrue(result.isValid(), "Application should be complete");
        assertTrue(result.getErrors().isEmpty(), "Should have no errors for complete application");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for complete application");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test evaluateApplicationCompleteness with incomplete application")
    void testEvaluateApplicationCompletenessWithIncompleteApplication() {
        // Setup
        // Missing required documents
        application.setDocuments(Collections.singletonList(document)); // Only one bank statement
        application.setStatus(ApplicationStatus.NEW); // Still in NEW status

        // Mock validation results
        when(validationService.validateMerchant(any(MerchantDetails.class)))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));
        
        Map<String, String> documentErrors = new HashMap<>();
        documentErrors.put("BANK_STATEMENT", "Required 3 document(s) of type BANK_STATEMENT, but found only 1");
        documentErrors.put("TAX_RETURN", "Required 1 document(s) of type TAX_RETURN, but found only 0");
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(false, documentErrors, ValidationSeverity.WARNING));

        String cacheKey = "app-completeness-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application_completeness"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.evaluateApplicationCompleteness(application);

        // Verify
        assertFalse(result.isValid(), "Application should be incomplete");
        assertEquals(2, result.getErrors().size(), "Should have 2 errors for incomplete application");
        assertTrue(result.getErrors().containsKey("documentsValidation"), "Should have error for documents validation");
        assertTrue(result.getErrors().containsKey("applicationStatus"), "Should have error for application status");
        assertEquals(ValidationSeverity.WARNING, result.getSeverity(), "Severity should be WARNING for incomplete application");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test evaluateApplicationCompleteness with missing merchant details")
    void testEvaluateApplicationCompletenessWithMissingMerchantDetails() {
        // Setup
        application.setMerchantDetails(null); // Missing merchant details

        String cacheKey = "app-completeness-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application_completeness"), anyLong()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.evaluateApplicationCompleteness(application);

        // Verify
        assertFalse(result.isValid(), "Application should be incomplete");
        assertTrue(result.getErrors().containsKey("merchantDetails"), "Should have error for missing merchant details");
        assertEquals(ValidationSeverity.WARNING, result.getSeverity(), "Severity should be WARNING for incomplete application");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test determineApplicationStatus with complete application")
    void testDetermineApplicationStatusWithCompleteApplication() {
        // Setup
        // Add required documents
        Document bankStatement1 = createDocument(DocumentType.BANK_STATEMENT, "2023-01-01");
        Document bankStatement2 = createDocument(DocumentType.BANK_STATEMENT, "2023-02-01");
        Document bankStatement3 = createDocument(DocumentType.BANK_STATEMENT, "2023-03-01");
        Document taxReturn = createDocument(DocumentType.TAX_RETURN, "2023-01-01");
        Document businessLicense = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> completeDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );
        
        application.setDocuments(completeDocuments);
        application.setReviewStatus(ReviewStatus.APPROVED);

        // Mock validation results
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ApplicationStatus result = validationService.determineApplicationStatus(application);

        // Verify
        assertEquals(ApplicationStatus.APPROVED, result, "Application status should be APPROVED");
    }

    @Test
    @DisplayName("Test determineApplicationStatus with incomplete application")
    void testDetermineApplicationStatusWithIncompleteApplication() {
        // Setup
        // Missing required documents
        application.setDocuments(Collections.singletonList(document)); // Only one bank statement

        // Mock validation results
        Map<String, String> documentErrors = new HashMap<>();
        documentErrors.put("BANK_STATEMENT", "Required 3 document(s) of type BANK_STATEMENT, but found only 1");
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(false, documentErrors));

        // Execute
        ApplicationStatus result = validationService.determineApplicationStatus(application);

        // Verify
        assertEquals(ApplicationStatus.PENDING, result, "Application status should be PENDING");
    }

    @Test
    @DisplayName("Test determineApplicationStatus with missing merchant details")
    void testDetermineApplicationStatusWithMissingMerchantDetails() {
        // Setup
        application.setMerchantDetails(null); // Missing merchant details

        // Mock validation results
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ApplicationStatus result = validationService.determineApplicationStatus(application);

        // Verify
        assertEquals(ApplicationStatus.PENDING, result, "Application status should be PENDING");
    }

    @Test
    @DisplayName("Test determineApplicationStatus with different review statuses")
    void testDetermineApplicationStatusWithDifferentReviewStatuses() {
        // Setup
        // Add required documents
        Document bankStatement1 = createDocument(DocumentType.BANK_STATEMENT, "2023-01-01");
        Document bankStatement2 = createDocument(DocumentType.BANK_STATEMENT, "2023-02-01");
        Document bankStatement3 = createDocument(DocumentType.BANK_STATEMENT, "2023-03-01");
        Document taxReturn = createDocument(DocumentType.TAX_RETURN, "2023-01-01");
        Document businessLicense = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> completeDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );
        
        application.setDocuments(completeDocuments);

        // Mock validation results
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Test different review statuses
        application.setReviewStatus(ReviewStatus.APPROVED);
        assertEquals(ApplicationStatus.APPROVED, validationService.determineApplicationStatus(application), 
                "Application status should be APPROVED when review status is APPROVED");

        application.setReviewStatus(ReviewStatus.REJECTED);
        assertEquals(ApplicationStatus.REJECTED, validationService.determineApplicationStatus(application), 
                "Application status should be REJECTED when review status is REJECTED");

        application.setReviewStatus(ReviewStatus.NEEDS_INFORMATION);
        assertEquals(ApplicationStatus.PENDING, validationService.determineApplicationStatus(application), 
                "Application status should be PENDING when review status is NEEDS_INFORMATION");

        application.setReviewStatus(ReviewStatus.IN_REVIEW);
        assertEquals(ApplicationStatus.PROCESSING, validationService.determineApplicationStatus(application), 
                "Application status should be PROCESSING when review status is IN_REVIEW");

        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);
        assertEquals(ApplicationStatus.PROCESSING, validationService.determineApplicationStatus(application), 
                "Application status should be PROCESSING when review status is NOT_REVIEWED");
    }

    @Test
    @DisplayName("Test determineReviewStatus with complete application")
    void testDetermineReviewStatusWithCompleteApplication() {
        // Setup
        // Add required documents
        Document bankStatement1 = createDocument(DocumentType.BANK_STATEMENT, "2023-01-01");
        Document bankStatement2 = createDocument(DocumentType.BANK_STATEMENT, "2023-02-01");
        Document bankStatement3 = createDocument(DocumentType.BANK_STATEMENT, "2023-03-01");
        Document taxReturn = createDocument(DocumentType.TAX_RETURN, "2023-01-01");
        Document businessLicense = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> completeDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );
        
        application.setDocuments(completeDocuments);
        application.setReviewStatus(ReviewStatus.NOT_REVIEWED);

        // Mock validation results
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ReviewStatus result = validationService.determineReviewStatus(application);

        // Verify
        assertEquals(ReviewStatus.IN_REVIEW, result, "Review status should be IN_REVIEW for complete application");
    }

    @Test
    @DisplayName("Test determineReviewStatus with incomplete application")
    void testDetermineReviewStatusWithIncompleteApplication() {
        // Setup
        // Missing required documents
        application.setDocuments(Collections.singletonList(document)); // Only one bank statement

        // Mock validation results
        Map<String, String> documentErrors = new HashMap<>();
        documentErrors.put("BANK_STATEMENT", "Required 3 document(s) of type BANK_STATEMENT, but found only 1");
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(false, documentErrors));

        // Execute
        ReviewStatus result = validationService.determineReviewStatus(application);

        // Verify
        assertEquals(ReviewStatus.NEEDS_INFORMATION, result, "Review status should be NEEDS_INFORMATION for incomplete application");
    }

    @Test
    @DisplayName("Test determineReviewStatus with missing merchant details")
    void testDetermineReviewStatusWithMissingMerchantDetails() {
        // Setup
        application.setMerchantDetails(null); // Missing merchant details

        // Execute
        ReviewStatus result = validationService.determineReviewStatus(application);

        // Verify
        assertEquals(ReviewStatus.NEEDS_INFORMATION, result, "Review status should be NEEDS_INFORMATION for missing merchant details");
    }

    @Test
    @DisplayName("Test determineReviewStatus with existing review status")
    void testDetermineReviewStatusWithExistingReviewStatus() {
        // Setup
        // Add required documents
        Document bankStatement1 = createDocument(DocumentType.BANK_STATEMENT, "2023-01-01");
        Document bankStatement2 = createDocument(DocumentType.BANK_STATEMENT, "2023-02-01");
        Document bankStatement3 = createDocument(DocumentType.BANK_STATEMENT, "2023-03-01");
        Document taxReturn = createDocument(DocumentType.TAX_RETURN, "2023-01-01");
        Document businessLicense = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> completeDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );
        
        application.setDocuments(completeDocuments);
        application.setReviewStatus(ReviewStatus.APPROVED); // Already approved

        // Mock validation results
        when(validationService.validateRequiredDocuments(anyList()))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ReviewStatus result = validationService.determineReviewStatus(application);

        // Verify
        assertEquals(ReviewStatus.APPROVED, result, "Review status should remain APPROVED");
    }

    @Test
    @DisplayName("Test validateExtractedData with valid data")
    void testValidateExtractedDataWithValidData() {
        // Setup
        DocumentType documentType = DocumentType.BANK_STATEMENT;
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("accountNumber", "12345678901");
        extractedData.put("routingNumber", "123456789");
        extractedData.put("bankName", "Test Bank");
        extractedData.put("accountName", "Test Account");
        extractedData.put("statementDate", "2023-01-01");
        extractedData.put("beginningBalance", 10000.0);
        extractedData.put("endingBalance", 12000.0);
        extractedData.put("averageDailyBalance", 11000.0);
        extractedData.put("totalDeposits", 5000.0);
        extractedData.put("totalWithdrawals", 3000.0);

        String cacheKey = "extracted-data-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("extracted_data"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateExtractedData(documentType, extractedData);

        // Verify
        assertTrue(result.isValid(), "Validation should pass for valid extracted data");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for valid data");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateExtractedData with invalid data")
    void testValidateExtractedDataWithInvalidData() {
        // Setup
        DocumentType documentType = DocumentType.BANK_STATEMENT;
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("accountNumber", "123"); // Invalid: doesn't match pattern
        extractedData.put("routingNumber", "12345"); // Invalid: doesn't match pattern
        // Missing required fields: bankName, accountName, statementDate, etc.

        String cacheKey = "extracted-data-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("extracted_data"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateExtractedData(documentType, extractedData);

        // Verify
        assertFalse(result.isValid(), "Validation should fail for invalid extracted data");
        assertTrue(result.getErrors().size() > 0, "Should have validation errors");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for invalid data");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateExtractedData with unknown document type")
    void testValidateExtractedDataWithUnknownDocumentType() {
        // Setup
        DocumentType documentType = null; // Unknown document type
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("field1", "value1");

        String cacheKey = "extracted-data-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("extracted_data"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateExtractedData(documentType, extractedData);

        // Verify
        assertFalse(result.isValid(), "Validation should fail for unknown document type");
        assertTrue(result.getErrors().containsKey("schema"), "Should have error for schema");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for unknown document type");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateExtractedDataWithConfidence with high confidence")
    void testValidateExtractedDataWithConfidenceWithHighConfidence() {
        // Setup
        DocumentType documentType = DocumentType.BANK_STATEMENT;
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("accountNumber", "12345678901");
        extractedData.put("routingNumber", "123456789");
        extractedData.put("bankName", "Test Bank");
        extractedData.put("accountName", "Test Account");
        extractedData.put("statementDate", "2023-01-01");
        extractedData.put("beginningBalance", 10000.0);
        extractedData.put("endingBalance", 12000.0);
        extractedData.put("averageDailyBalance", 11000.0);
        extractedData.put("totalDeposits", 5000.0);
        extractedData.put("totalWithdrawals", 3000.0);

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("accountNumber", 0.95);
        confidenceScores.put("routingNumber", 0.98);
        confidenceScores.put("bankName", 0.99);
        confidenceScores.put("accountName", 0.97);
        confidenceScores.put("statementDate", 0.96);
        confidenceScores.put("beginningBalance", 0.90);
        confidenceScores.put("endingBalance", 0.92);
        confidenceScores.put("averageDailyBalance", 0.85);
        confidenceScores.put("totalDeposits", 0.88);
        confidenceScores.put("totalWithdrawals", 0.87);

        String cacheKey = "extracted-data-confidence-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("extracted_data_confidence"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock schema validation result
        when(validationService.validateExtractedData(eq(documentType), eq(extractedData)))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ValidationResult result = validationService.validateExtractedDataWithConfidence(documentType, extractedData, confidenceScores);

        // Verify
        assertTrue(result.isValid(), "Validation should pass for high confidence scores");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for high confidence");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateExtractedDataWithConfidence with low confidence")
    void testValidateExtractedDataWithConfidenceWithLowConfidence() {
        // Setup
        DocumentType documentType = DocumentType.BANK_STATEMENT;
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("accountNumber", "12345678901");
        extractedData.put("routingNumber", "123456789");
        extractedData.put("bankName", "Test Bank");
        extractedData.put("accountName", "Test Account");
        extractedData.put("statementDate", "2023-01-01");

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("accountNumber", 0.95); // High confidence
        confidenceScores.put("routingNumber", 0.70); // Low confidence
        confidenceScores.put("bankName", 0.60); // Low confidence
        confidenceScores.put("accountName", 0.97); // High confidence
        confidenceScores.put("statementDate", 0.30); // Very low confidence

        String cacheKey = "extracted-data-confidence-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("extracted_data_confidence"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock schema validation result
        when(validationService.validateExtractedData(eq(documentType), eq(extractedData)))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ValidationResult result = validationService.validateExtractedDataWithConfidence(documentType, extractedData, confidenceScores);

        // Verify
        assertFalse(result.isValid(), "Validation should fail for low confidence scores");
        assertEquals(3, result.getErrors().size(), "Should have 3 validation errors");
        assertTrue(result.getErrors().containsKey("routingNumber"), "Should have error for routingNumber");
        assertTrue(result.getErrors().containsKey("bankName"), "Should have error for bankName");
        assertTrue(result.getErrors().containsKey("statementDate"), "Should have error for statementDate");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for very low confidence");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateRequiredDocuments with all required documents")
    void testValidateRequiredDocumentsWithAllRequiredDocuments() {
        // Setup
        // Create required documents
        Document bankStatement1 = createDocument(DocumentType.BANK_STATEMENT, "2023-01-01");
        Document bankStatement2 = createDocument(DocumentType.BANK_STATEMENT, "2023-02-01");
        Document bankStatement3 = createDocument(DocumentType.BANK_STATEMENT, "2023-03-01");
        Document taxReturn = createDocument(DocumentType.TAX_RETURN, "2023-01-01");
        Document businessLicense = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> completeDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );

        String cacheKey = "required-documents-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("required_documents"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateRequiredDocuments(completeDocuments);

        // Verify
        assertTrue(result.isValid(), "Validation should pass with all required documents");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE with all required documents");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateRequiredDocuments with missing documents")
    void testValidateRequiredDocumentsWithMissingDocuments() {
        // Setup
        // Missing some required documents
        Document bankStatement1 = createDocument(DocumentType.BANK_STATEMENT, "2023-01-01");
        Document bankStatement2 = createDocument(DocumentType.BANK_STATEMENT, "2023-02-01");
        // Missing third bank statement
        // Missing tax return
        Document businessLicense = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        // Missing ID verification
        
        List<Document> incompleteDocuments = Arrays.asList(
            bankStatement1, bankStatement2, businessLicense
        );

        String cacheKey = "required-documents-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("required_documents"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateRequiredDocuments(incompleteDocuments);

        // Verify
        assertFalse(result.isValid(), "Validation should fail with missing documents");
        assertEquals(3, result.getErrors().size(), "Should have 3 validation errors");
        assertTrue(result.getErrors().containsKey("BANK_STATEMENT"), "Should have error for BANK_STATEMENT");
        assertTrue(result.getErrors().containsKey("TAX_RETURN"), "Should have error for TAX_RETURN");
        assertTrue(result.getErrors().containsKey("ID_VERIFICATION"), "Should have error for ID_VERIFICATION");
        assertEquals(ValidationSeverity.WARNING, result.getSeverity(), "Severity should be WARNING with some missing documents");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateRequiredDocuments with empty document list")
    void testValidateRequiredDocumentsWithEmptyDocumentList() {
        // Setup
        List<Document> emptyDocuments = Collections.emptyList();

        String cacheKey = "required-documents-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("required_documents"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateRequiredDocuments(emptyDocuments);

        // Verify
        assertFalse(result.isValid(), "Validation should fail with empty document list");
        assertEquals(1, result.getErrors().size(), "Should have 1 validation error");
        assertTrue(result.getErrors().containsKey("documents"), "Should have error for documents");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR with empty document list");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateRequiredDocuments with null document list")
    void testValidateRequiredDocumentsWithNullDocumentList() {
        // Setup
        List<Document> nullDocuments = null;

        String cacheKey = "required-documents-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("required_documents"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateRequiredDocuments(nullDocuments);

        // Verify
        assertFalse(result.isValid(), "Validation should fail with null document list");
        assertEquals(1, result.getErrors().size(), "Should have 1 validation error");
        assertTrue(result.getErrors().containsKey("documents"), "Should have error for documents");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR with null document list");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateBusinessRules with valid application")
    void testValidateBusinessRulesWithValidApplication() {
        // Setup
        // Create required documents with valid data
        Document bankStatement1 = createBankStatement("2023-01-01", 10000.0, 25000.0);
        Document bankStatement2 = createBankStatement("2023-02-01", 12000.0, 27000.0);
        Document bankStatement3 = createBankStatement("2023-03-01", 15000.0, 30000.0);
        Document taxReturn = createTaxReturn("2023");
        Document businessLicense = createBusinessLicense(LocalDate.now().plusYears(1));
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> validDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );
        
        // Valid merchant details
        merchantDetails.setRevenue(500000.0); // $500,000 revenue (above minimum)
        merchantDetails.setMetadata("{\"businessStartDate\": \"2020-01-01\"}"); // Business older than 1 year

        String cacheKey = "business-rules-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("business_rules"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock application completeness validation
        when(validationService.evaluateApplicationCompleteness(eq(application)))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ValidationResult result = validationService.validateBusinessRules(application, merchantDetails, validDocuments);

        // Verify
        assertTrue(result.isValid(), "Business rules validation should pass for valid application");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for valid application");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateBusinessRules with invalid application")
    void testValidateBusinessRulesWithInvalidApplication() {
        // Setup
        // Create documents with invalid data
        Document bankStatement1 = createBankStatement("2023-01-01", 2000.0, 5000.0); // Low average balance
        Document bankStatement2 = createBankStatement("2023-02-01", 1500.0, 4000.0); // Low average balance
        // Missing third bank statement
        Document taxReturn = createTaxReturn("2020"); // Not recent tax year
        Document businessLicense = createBusinessLicense(LocalDate.now().minusMonths(1)); // Expired license
        
        List<Document> invalidDocuments = Arrays.asList(
            bankStatement1, bankStatement2, taxReturn, businessLicense
        );
        
        // Invalid merchant details
        merchantDetails.setRevenue(50000.0); // $50,000 revenue (below minimum)
        merchantDetails.setMetadata("{\"businessStartDate\": \"2022-06-01\"}"); // Business less than 1 year old

        String cacheKey = "business-rules-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("business_rules"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock application completeness validation
        Map<String, String> completenessErrors = new HashMap<>();
        completenessErrors.put("documents", "Missing required documents");
        when(validationService.evaluateApplicationCompleteness(eq(application)))
                .thenReturn(new ValidationResult(false, completenessErrors));

        // Execute
        ValidationResult result = validationService.validateBusinessRules(application, merchantDetails, invalidDocuments);

        // Verify
        assertFalse(result.isValid(), "Business rules validation should fail for invalid application");
        assertTrue(result.getErrors().size() > 0, "Should have validation errors");
        assertTrue(result.getErrors().containsKey("completeness"), "Should have error for completeness");
        assertTrue(result.getErrors().containsKey("revenue"), "Should have error for revenue");
        assertTrue(result.getErrors().containsKey("businessAge"), "Should have error for businessAge");
        assertTrue(result.getErrors().containsKey("bankStatements"), "Should have error for bankStatements");
        assertTrue(result.getErrors().containsKey("avgDailyBalance"), "Should have error for avgDailyBalance");
        assertTrue(result.getErrors().containsKey("taxReturnYear"), "Should have error for taxReturnYear");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for invalid application");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateBusinessRules with missing merchant details")
    void testValidateBusinessRulesWithMissingMerchantDetails() {
        // Setup
        MerchantDetails nullMerchantDetails = null;

        String cacheKey = "business-rules-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("business_rules"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateBusinessRules(application, nullMerchantDetails, documents);

        // Verify
        assertFalse(result.isValid(), "Business rules validation should fail with missing merchant details");
        assertTrue(result.getErrors().containsKey("merchantDetails"), "Should have error for merchantDetails");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for missing merchant details");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApprovalRequirements with valid application")
    void testValidateApprovalRequirementsWithValidApplication() {
        // Setup
        // Create required documents with valid data
        Document bankStatement1 = createBankStatement("2023-01-01", 10000.0, 25000.0);
        Document bankStatement2 = createBankStatement("2023-02-01", 12000.0, 27000.0);
        Document bankStatement3 = createBankStatement("2023-03-01", 15000.0, 30000.0);
        Document taxReturn = createTaxReturn("2023");
        Document businessLicense = createBusinessLicense(LocalDate.now().plusYears(1));
        Document idVerification = createDocument(DocumentType.ID_VERIFICATION, "2023-01-01");
        
        List<Document> validDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, taxReturn, businessLicense, idVerification
        );
        
        // Valid merchant details
        merchantDetails.setRevenue(500000.0); // $500,000 revenue
        
        // Valid requested amount (less than 20% of revenue)
        application.setMetadata("{\"requestedAmount\": 50000, \"businessName\": \"Test Business\"}");

        String cacheKey = "approval-requirements-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("approval_requirements"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock business rules validation
        when(validationService.validateBusinessRules(eq(application), eq(merchantDetails), eq(validDocuments)))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Mock other validations
        doReturn(true).when(validationService).hasConsistentDepositPattern(anyList());
        doReturn(true).when(validationService).hasSufficientDepositVolume(anyList());
        doReturn(true).when(validationService).isBusinessLicenseValid(any(Document.class));

        // Execute
        ValidationResult result = validationService.validateApprovalRequirements(application, merchantDetails, validDocuments);

        // Verify
        assertTrue(result.isValid(), "Approval requirements validation should pass for valid application");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for valid application");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApprovalRequirements with invalid application")
    void testValidateApprovalRequirementsWithInvalidApplication() {
        // Setup
        // Create documents with invalid data
        Document bankStatement1 = createBankStatement("2023-01-01", 10000.0, 25000.0);
        Document bankStatement2 = createBankStatement("2023-02-01", 12000.0, 27000.0);
        Document bankStatement3 = createBankStatement("2023-03-01", 15000.0, 30000.0);
        Document businessLicense = createBusinessLicense(LocalDate.now().minusMonths(1)); // Expired license
        
        List<Document> invalidDocuments = Arrays.asList(
            bankStatement1, bankStatement2, bankStatement3, businessLicense
        );
        
        // Valid merchant details
        merchantDetails.setRevenue(500000.0); // $500,000 revenue
        
        // Invalid requested amount (more than 20% of revenue)
        application.setMetadata("{\"requestedAmount\": 150000, \"businessName\": \"Test Business\"}");

        String cacheKey = "approval-requirements-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("approval_requirements"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock business rules validation
        when(validationService.validateBusinessRules(eq(application), eq(merchantDetails), eq(invalidDocuments)))
                .thenReturn(new ValidationResult(true, Collections.emptyMap())); // Business rules pass

        // Mock other validations
        doReturn(false).when(validationService).hasConsistentDepositPattern(anyList());
        doReturn(false).when(validationService).hasSufficientDepositVolume(anyList());
        doReturn(false).when(validationService).isBusinessLicenseValid(any(Document.class));

        // Execute
        ValidationResult result = validationService.validateApprovalRequirements(application, merchantDetails, invalidDocuments);

        // Verify
        assertFalse(result.isValid(), "Approval requirements validation should fail for invalid application");
        assertEquals(4, result.getErrors().size(), "Should have 4 validation errors");
        assertTrue(result.getErrors().containsKey("requestedAmount"), "Should have error for requestedAmount");
        assertTrue(result.getErrors().containsKey("depositPattern"), "Should have error for depositPattern");
        assertTrue(result.getErrors().containsKey("depositVolume"), "Should have error for depositVolume");
        assertTrue(result.getErrors().containsKey("businessLicense"), "Should have error for businessLicense");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for invalid application");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApprovalRequirements with failed business rules")
    void testValidateApprovalRequirementsWithFailedBusinessRules() {
        // Setup
        // Mock business rules validation
        Map<String, String> businessRuleErrors = new HashMap<>();
        businessRuleErrors.put("revenue", "Merchant revenue must be at least $100,000");
        businessRuleErrors.put("businessAge", "Business must be at least one year old");
        ValidationResult businessRulesResult = new ValidationResult(false, businessRuleErrors, ValidationSeverity.ERROR);
        
        when(validationService.validateBusinessRules(eq(application), eq(merchantDetails), eq(documents)))
                .thenReturn(businessRulesResult);

        String cacheKey = "approval-requirements-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("approval_requirements"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateApprovalRequirements(application, merchantDetails, documents);

        // Verify
        assertFalse(result.isValid(), "Approval requirements validation should fail with failed business rules");
        assertEquals(2, result.getErrors().size(), "Should have 2 validation errors from business rules");
        assertTrue(result.getErrors().containsKey("revenue"), "Should have error for revenue");
        assertTrue(result.getErrors().containsKey("businessAge"), "Should have error for businessAge");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for failed business rules");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApplicationDataConsistency with consistent data")
    void testValidateApplicationDataConsistencyWithConsistentData() {
        // Setup
        // Application metadata
        application.setMetadata("{\"requestedAmount\": 50000, \"businessName\": \"Test Business Inc\"}");
        
        // Extracted data from documents
        Map<DocumentType, Map<String, Object>> extractedDataMap = new HashMap<>();
        
        // Business license data
        Map<String, Object> licenseData = new HashMap<>();
        licenseData.put("businessName", "Test Business Inc."); // Matches application business name
        extractedDataMap.put(DocumentType.BUSINESS_LICENSE, licenseData);
        
        // Tax return data
        Map<String, Object> taxData = new HashMap<>();
        taxData.put("businessName", "Test Business Incorporated"); // Similar to application business name
        extractedDataMap.put(DocumentType.TAX_RETURN, taxData);
        
        // Bank statement data
        Map<String, Object> bankData = new HashMap<>();
        bankData.put("averageDailyBalance", 15000.0); // Reasonable compared to requested amount
        extractedDataMap.put(DocumentType.BANK_STATEMENT, bankData);

        String cacheKey = "app-data-consistency-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application_data_consistency"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock name matching
        doReturn(true).when(validationService).isNameMatch(anyString(), anyString());

        // Execute
        ValidationResult result = validationService.validateApplicationDataConsistency(application, extractedDataMap);

        // Verify
        assertTrue(result.isValid(), "Data consistency validation should pass for consistent data");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for consistent data");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateApplicationDataConsistency with inconsistent data")
    void testValidateApplicationDataConsistencyWithInconsistentData() {
        // Setup
        // Application metadata
        application.setMetadata("{\"requestedAmount\": 150000, \"businessName\": \"Test Business Inc\"}");
        
        // Extracted data from documents
        Map<DocumentType, Map<String, Object>> extractedDataMap = new HashMap<>();
        
        // Business license data
        Map<String, Object> licenseData = new HashMap<>();
        licenseData.put("businessName", "Completely Different Business"); // Doesn't match application business name
        extractedDataMap.put(DocumentType.BUSINESS_LICENSE, licenseData);
        
        // Tax return data
        Map<String, Object> taxData = new HashMap<>();
        taxData.put("businessName", "Another Different Name"); // Doesn't match application business name
        extractedDataMap.put(DocumentType.TAX_RETURN, taxData);
        
        // Bank statement data
        Map<String, Object> bankData = new HashMap<>();
        bankData.put("averageDailyBalance", 5000.0); // Too low compared to requested amount
        extractedDataMap.put(DocumentType.BANK_STATEMENT, bankData);

        String cacheKey = "app-data-consistency-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("application_data_consistency"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock name matching
        doReturn(false).when(validationService).isNameMatch(anyString(), anyString());

        // Execute
        ValidationResult result = validationService.validateApplicationDataConsistency(application, extractedDataMap);

        // Verify
        assertFalse(result.isValid(), "Data consistency validation should fail for inconsistent data");
        assertEquals(3, result.getErrors().size(), "Should have 3 validation errors");
        assertTrue(result.getErrors().containsKey("businessName"), "Should have error for businessName");
        assertTrue(result.getErrors().containsKey("businessNameTax"), "Should have error for businessNameTax");
        assertTrue(result.getErrors().containsKey("requestedAmountBalance"), "Should have error for requestedAmountBalance");
        assertEquals(ValidationSeverity.WARNING, result.getSeverity(), "Severity should be WARNING for inconsistent data");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDataConsistency with consistent merchant data")
    void testValidateDataConsistencyWithConsistentMerchantData() {
        // Setup
        // Merchant details
        merchantDetails.setLegalName("Test Merchant Inc.");
        merchantDetails.setDbaName("Test Merchant");
        merchantDetails.setEin("12-3456789");
        merchantDetails.setRevenue(500000.0);
        
        // Extracted data from documents
        Map<DocumentType, Map<String, Object>> extractedDataMap = new HashMap<>();
        
        // Business license data
        Map<String, Object> licenseData = new HashMap<>();
        licenseData.put("businessName", "Test Merchant Inc"); // Matches merchant legal name
        extractedDataMap.put(DocumentType.BUSINESS_LICENSE, licenseData);
        
        // Tax return data
        Map<String, Object> taxData = new HashMap<>();
        taxData.put("ein", "12-3456789"); // Matches merchant EIN
        taxData.put("grossRevenue", 520000.0); // Close to merchant revenue (within 10%)
        extractedDataMap.put(DocumentType.TAX_RETURN, taxData);

        String cacheKey = "merchant-data-consistency-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant_data_consistency"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock name matching
        doReturn(true).when(validationService).isNameMatch(anyString(), anyString());

        // Execute
        ValidationResult result = validationService.validateDataConsistency(merchantDetails, extractedDataMap);

        // Verify
        assertTrue(result.isValid(), "Data consistency validation should pass for consistent merchant data");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for consistent data");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDataConsistency with inconsistent merchant data")
    void testValidateDataConsistencyWithInconsistentMerchantData() {
        // Setup
        // Merchant details
        merchantDetails.setLegalName("Test Merchant Inc.");
        merchantDetails.setDbaName("Test Merchant");
        merchantDetails.setEin("12-3456789");
        merchantDetails.setRevenue(500000.0);
        
        // Extracted data from documents
        Map<DocumentType, Map<String, Object>> extractedDataMap = new HashMap<>();
        
        // Business license data
        Map<String, Object> licenseData = new HashMap<>();
        licenseData.put("businessName", "Completely Different Business"); // Doesn't match merchant names
        extractedDataMap.put(DocumentType.BUSINESS_LICENSE, licenseData);
        
        // Tax return data
        Map<String, Object> taxData = new HashMap<>();
        taxData.put("ein", "98-7654321"); // Doesn't match merchant EIN
        taxData.put("grossRevenue", 900000.0); // Significantly different from merchant revenue (>10%)
        extractedDataMap.put(DocumentType.TAX_RETURN, taxData);

        String cacheKey = "merchant-data-consistency-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("merchant_data_consistency"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock name matching
        doReturn(false).when(validationService).isNameMatch(anyString(), anyString());

        // Execute
        ValidationResult result = validationService.validateDataConsistency(merchantDetails, extractedDataMap);

        // Verify
        assertFalse(result.isValid(), "Data consistency validation should fail for inconsistent merchant data");
        assertEquals(3, result.getErrors().size(), "Should have 3 validation errors");
        assertTrue(result.getErrors().containsKey("businessName"), "Should have error for businessName");
        assertTrue(result.getErrors().containsKey("ein"), "Should have error for ein");
        assertTrue(result.getErrors().containsKey("revenue"), "Should have error for revenue");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for inconsistent EIN");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDataQuality with high quality data")
    void testValidateDataQualityWithHighQualityData() {
        // Setup
        // Extracted data from documents
        Map<DocumentType, Map<String, Object>> extractedDataMap = new HashMap<>();
        
        // Bank statement data
        Map<String, Object> bankData = new HashMap<>();
        bankData.put("accountNumber", "12345678901");
        bankData.put("routingNumber", "123456789");
        bankData.put("bankName", "Test Bank");
        extractedDataMap.put(DocumentType.BANK_STATEMENT, bankData);
        
        // Confidence scores
        Map<DocumentType, Map<String, Double>> confidenceScoresMap = new HashMap<>();
        
        // Bank statement confidence scores
        Map<String, Double> bankConfidence = new HashMap<>();
        bankConfidence.put("accountNumber", 0.95);
        bankConfidence.put("routingNumber", 0.98);
        bankConfidence.put("bankName", 0.97);
        confidenceScoresMap.put(DocumentType.BANK_STATEMENT, bankConfidence);

        String cacheKey = "data-quality-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("data_quality"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock extracted data validation
        when(validationService.validateExtractedDataWithConfidence(any(DocumentType.class), anyMap(), anyMap()))
                .thenReturn(new ValidationResult(true, Collections.emptyMap()));

        // Execute
        ValidationResult result = validationService.validateDataQuality(extractedDataMap, confidenceScoresMap);

        // Verify
        assertTrue(result.isValid(), "Data quality validation should pass for high quality data");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for high quality data");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDataQuality with low quality data")
    void testValidateDataQualityWithLowQualityData() {
        // Setup
        // Extracted data from documents
        Map<DocumentType, Map<String, Object>> extractedDataMap = new HashMap<>();
        
        // Bank statement data
        Map<String, Object> bankData = new HashMap<>();
        bankData.put("accountNumber", "12345678901");
        bankData.put("routingNumber", "123456789");
        bankData.put("bankName", "Test Bank");
        extractedDataMap.put(DocumentType.BANK_STATEMENT, bankData);
        
        // Tax return data
        Map<String, Object> taxData = new HashMap<>();
        taxData.put("ein", "12-3456789");
        taxData.put("grossRevenue", 500000.0);
        extractedDataMap.put(DocumentType.TAX_RETURN, taxData);
        
        // Confidence scores
        Map<DocumentType, Map<String, Double>> confidenceScoresMap = new HashMap<>();
        
        // Bank statement confidence scores (low confidence)
        Map<String, Double> bankConfidence = new HashMap<>();
        bankConfidence.put("accountNumber", 0.65); // Below threshold
        bankConfidence.put("routingNumber", 0.70); // Below threshold
        bankConfidence.put("bankName", 0.80); // Above threshold
        confidenceScoresMap.put(DocumentType.BANK_STATEMENT, bankConfidence);
        
        // Tax return confidence scores (very low confidence for critical field)
        Map<String, Double> taxConfidence = new HashMap<>();
        taxConfidence.put("ein", 0.30); // Very low confidence for critical field
        taxConfidence.put("grossRevenue", 0.85); // Above threshold
        confidenceScoresMap.put(DocumentType.TAX_RETURN, taxConfidence);

        String cacheKey = "data-quality-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("data_quality"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock extracted data validation for bank statement (low confidence)
        Map<String, String> bankErrors = new HashMap<>();
        bankErrors.put("accountNumber", "Low confidence score: 0.65 (below threshold of 0.75)");
        bankErrors.put("routingNumber", "Low confidence score: 0.70 (below threshold of 0.75)");
        when(validationService.validateExtractedDataWithConfidence(eq(DocumentType.BANK_STATEMENT), eq(bankData), eq(bankConfidence)))
                .thenReturn(new ValidationResult(false, bankErrors, ValidationSeverity.WARNING));
        
        // Mock extracted data validation for tax return (very low confidence)
        Map<String, String> taxErrors = new HashMap<>();
        taxErrors.put("ein", "Low confidence score: 0.30 (below threshold of 0.75)");
        when(validationService.validateExtractedDataWithConfidence(eq(DocumentType.TAX_RETURN), eq(taxData), eq(taxConfidence)))
                .thenReturn(new ValidationResult(false, taxErrors, ValidationSeverity.ERROR));

        // Execute
        ValidationResult result = validationService.validateDataQuality(extractedDataMap, confidenceScoresMap);

        // Verify
        assertFalse(result.isValid(), "Data quality validation should fail for low quality data");
        assertTrue(result.getErrors().size() > 0, "Should have validation errors");
        assertTrue(result.getErrors().containsKey("TAX_RETURN.ein"), "Should have error for TAX_RETURN.ein");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for low quality critical data");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDocumentClassification with correct classification")
    void testValidateDocumentClassificationWithCorrectClassification() {
        // Setup
        document.setType(DocumentType.BANK_STATEMENT);
        
        // Extracted data matching bank statement schema
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("accountNumber", "12345678901");
        extractedData.put("routingNumber", "123456789");
        extractedData.put("bankName", "Test Bank");
        extractedData.put("accountName", "Test Account");
        extractedData.put("statementDate", "2023-01-01");
        extractedData.put("beginningBalance", 10000.0);
        extractedData.put("endingBalance", 12000.0);
        extractedData.put("averageDailyBalance", 11000.0);
        extractedData.put("totalDeposits", 5000.0);
        extractedData.put("totalWithdrawals", 3000.0);

        String cacheKey = "document-classification-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("document_classification"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Execute
        ValidationResult result = validationService.validateDocumentClassification(document, extractedData);

        // Verify
        assertTrue(result.isValid(), "Document classification validation should pass for correct classification");
        assertTrue(result.getErrors().isEmpty(), "Should have no validation errors");
        assertEquals(ValidationSeverity.NONE, result.getSeverity(), "Severity should be NONE for correct classification");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test validateDocumentClassification with incorrect classification")
    void testValidateDocumentClassificationWithIncorrectClassification() {
        // Setup
        document.setType(DocumentType.BANK_STATEMENT);
        
        // Extracted data matching tax return schema, not bank statement
        Map<String, Object> extractedData = new HashMap<>();
        extractedData.put("taxYear", 2023);
        extractedData.put("ein", "12-3456789");
        extractedData.put("businessName", "Test Business");
        extractedData.put("grossRevenue", 500000.0);
        extractedData.put("netIncome", 100000.0);
        extractedData.put("taxLiability", 25000.0);
        // Missing all required bank statement fields

        String cacheKey = "document-classification-key";
        when(cacheKeyGenerator.generateKey(eq(CacheConstants.VALIDATION_CACHE), eq("document_classification"), anyString()))
                .thenReturn(cacheKey);
        when(cacheService.get(eq(cacheKey), eq(ValidationResult.class)))
                .thenReturn(null); // No cached result

        // Mock document type suggestion
        doReturn(DocumentType.TAX_RETURN).when(validationService).suggestDocumentType(anyMap());

        // Execute
        ValidationResult result = validationService.validateDocumentClassification(document, extractedData);

        // Verify
        assertFalse(result.isValid(), "Document classification validation should fail for incorrect classification");
        assertEquals(2, result.getErrors().size(), "Should have 2 validation errors");
        assertTrue(result.getErrors().containsKey("classification"), "Should have error for classification");
        assertTrue(result.getErrors().containsKey("suggestedType"), "Should have suggested document type");
        assertEquals(ValidationSeverity.ERROR, result.getSeverity(), "Severity should be ERROR for incorrect classification");
        verify(cacheService).put(eq(cacheKey), eq(result), eq(CacheConstants.VALIDATION_RESULT_TTL));
    }

    @Test
    @DisplayName("Test getDocumentValidationSchema with valid document type")
    void testGetDocumentValidationSchemaWithValidDocumentType() {
        // Execute
        Map<String, Object> schema = validationService.getDocumentValidationSchema(DocumentType.BANK_STATEMENT);

        // Verify
        assertNotNull(schema, "Should return a schema for valid document type");
        assertTrue(schema.containsKey("accountNumber"), "Schema should contain accountNumber field");
        assertTrue(schema.containsKey("routingNumber"), "Schema should contain routingNumber field");
        assertTrue(schema.containsKey("bankName"), "Schema should contain bankName field");
    }

    @Test
    @DisplayName("Test getDocumentValidationSchema with null document type")
    void testGetDocumentValidationSchemaWithNullDocumentType() {
        // Execute
        Map<String, Object> schema = validationService.getDocumentValidationSchema(null);

        // Verify
        assertNull(schema, "Should return null for null document type");
    }

    // Helper methods
    private Document createDocument(DocumentType type, String dateStr) {
        Document doc = new Document();
        doc.setId(System.nanoTime()); // Generate unique ID
        doc.setApplication(application);
        doc.setType(type);
        doc.setStoragePath("s3://mca-documents/1/" + type.toString().toLowerCase() + ".pdf");
        doc.setUploadedAt(LocalDateTime.now());
        doc.setMetadata("{\"documentDate\": \"" + dateStr + "\"}");
        return doc;
    }

    private Document createBankStatement(String dateStr, double avgDailyBalance, double totalDeposits) {
        Document doc = createDocument(DocumentType.BANK_STATEMENT, dateStr);
        doc.setMetadata("{\"statementDate\": \"" + dateStr + "\", \"averageDailyBalance\": " + avgDailyBalance + ", \"totalDeposits\": " + totalDeposits + "}");
        return doc;
    }

    private Document createTaxReturn(String taxYear) {
        Document doc = createDocument(DocumentType.TAX_RETURN, "2023-01-01");
        doc.setMetadata("{\"taxYear\": \"" + taxYear + "\", \"ein\": \"12-3456789\", \"grossRevenue\": 500000, \"netIncome\": 100000}");
        return doc;
    }

    private Document createBusinessLicense(LocalDate expirationDate) {
        Document doc = createDocument(DocumentType.BUSINESS_LICENSE, "2023-01-01");
        doc.setMetadata("{\"licenseNumber\": \"LIC123456\", \"issueDate\": \"2023-01-01\", \"expirationDate\": \"" + expirationDate + "\"}");
        return doc;
    }

    // Inner classes for ValidationResult and ValidationSeverity if they are defined within ValidationServiceImpl
    public static class ValidationResult {
        private final boolean valid;
        private final Map<String, String> errors;
        private final ValidationSeverity severity;

        public ValidationResult(boolean valid, Map<String, String> errors) {
            this(valid, errors, valid ? ValidationSeverity.NONE : ValidationSeverity.ERROR);
        }

        public ValidationResult(boolean valid, Map<String, String> errors, ValidationSeverity severity) {
            this.valid = valid;
            this.errors = errors;
            this.severity = severity;
        }

        public boolean isValid() {
            return valid;
        }

        public Map<String, String> getErrors() {
            return errors;
        }

        public ValidationSeverity getSeverity() {
            return severity;
        }
    }

    public enum ValidationSeverity {
        NONE,
        INFO,
        WARNING,
        ERROR
    }

    // Utility class for reflection-based field injection
    private static class ReflectionTestUtils {
        public static void setField(Object target, String fieldName, Object value) {
            try {
                java.lang.reflect.Field field = findField(target.getClass(), fieldName);
                if (field == null) {
                    throw new IllegalArgumentException("Field '" + fieldName + "' not found on target class " + target.getClass().getName());
                }
                field.setAccessible(true);
                field.set(target, value);
            } catch (IllegalAccessException e) {
                throw new RuntimeException("Failed to set field '" + fieldName + "' on target class " + target.getClass().getName(), e);
            }
        }

        private static java.lang.reflect.Field findField(Class<?> clazz, String fieldName) {
            Class<?> searchType = clazz;
            while (searchType != null) {
                try {
                    return searchType.getDeclaredField(fieldName);
                } catch (NoSuchFieldException e) {
                    searchType = searchType.getSuperclass();
                }
            }
            return null;
        }
    }
}