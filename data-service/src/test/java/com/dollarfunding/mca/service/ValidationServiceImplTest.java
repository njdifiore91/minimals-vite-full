package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ErrorResponseDTO.ValidationError;
import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.MerchantDetails;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.service.ValidationServiceImpl.BusinessRule;
import com.dollarfunding.mca.util.JsonUtil;
import com.dollarfunding.mca.util.JsonUtil.JsonValidationResult;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.test.util.ReflectionTestUtils;

import javax.validation.ConstraintViolation;
import javax.validation.Validator;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the ValidationServiceImpl class that handles data validation and business rule application.
 * Tests verify schema validation, business rule application, validation result reporting, and caching of validation results.
 * Uses Mockito to mock dependencies including validation schemas and rule engines.
 */
@ExtendWith(MockitoExtension.class)
public class ValidationServiceImplTest {

    @Mock
    private ApplicationRepository applicationRepository;

    @Mock
    private DocumentRepository documentRepository;

    @Mock
    private Validator validator;

    @Mock
    private ObjectMapper objectMapper;

    @Mock
    private Resource mockResource;

    @InjectMocks
    private ValidationServiceImpl validationService;

    private Map<String, String> schemaCache;
    private Map<String, List<BusinessRule>> businessRules;

    @BeforeEach
    void setUp() throws Exception {
        // Create schema cache and business rules maps
        schemaCache = new ConcurrentHashMap<>();
        businessRules = new ConcurrentHashMap<>();

        // Set up mock schemas
        schemaCache.put("application", "{\"type\": \"object\", \"properties\": {\"id\": {\"type\": \"string\"}}}";
        schemaCache.put("merchant", "{\"type\": \"object\", \"properties\": {\"name\": {\"type\": \"string\"}}}";
        schemaCache.put("document-bank_statement", "{\"type\": \"object\", \"properties\": {\"type\": {\"type\": \"string\"}}}";

        // Set up mock business rules
        List<BusinessRule> applicationRules = new ArrayList<>();
        applicationRules.add(new BusinessRule("status_transition", "Invalid status transition", data -> true));
        businessRules.put("application", applicationRules);

        List<BusinessRule> merchantRules = new ArrayList<>();
        merchantRules.add(new BusinessRule("revenue_threshold", "Revenue must be at least $50,000 for funding", 
                data -> {
                    if (data instanceof MerchantDetailsRequestDTO) {
                        MerchantDetailsRequestDTO merchant = (MerchantDetailsRequestDTO) data;
                        return merchant.getRevenue() == null || merchant.getRevenue().doubleValue() >= 50000.0;
                    }
                    return true;
                }));
        businessRules.put("merchant", merchantRules);

        List<BusinessRule> documentRules = new ArrayList<>();
        documentRules.add(new BusinessRule("confidence_threshold", "Document confidence score below threshold", data -> true));
        businessRules.put("document", documentRules);

        // Inject the mock schema cache and business rules into the validation service
        ReflectionTestUtils.setField(validationService, "schemaCache", schemaCache);
        ReflectionTestUtils.setField(validationService, "businessRules", businessRules);

        // Mock ClassPathResource behavior
        when(mockResource.exists()).thenReturn(true);
        when(mockResource.getInputStream()).thenReturn(new ByteArrayInputStream("{}".getBytes(StandardCharsets.UTF_8)));
    }

    @Test
    @DisplayName("Should initialize schemas and business rules on startup")
    void testInit() throws IOException {
        // Create a new instance with mocked dependencies to test initialization
        ValidationServiceImpl service = new ValidationServiceImpl(applicationRepository, documentRepository, validator, objectMapper);
        
        // Mock the ClassPathResource behavior
        try (MockedStatic<ClassPathResource> mockedStatic = Mockito.mockStatic(ClassPathResource.class)) {
            mockedStatic.when(() -> new ClassPathResource(anyString())).thenReturn(mockResource);
            
            // Call init method
            service.init();
            
            // Verify that schemas were loaded
            Map<String, String> schemaCacheResult = (Map<String, String>) ReflectionTestUtils.getField(service, "schemaCache");
            assertNotNull(schemaCacheResult);
            assertFalse(schemaCacheResult.isEmpty());
            
            // Verify that business rules were initialized
            Map<String, List<BusinessRule>> businessRulesResult = 
                    (Map<String, List<BusinessRule>>) ReflectionTestUtils.getField(service, "businessRules");
            assertNotNull(businessRulesResult);
            assertFalse(businessRulesResult.isEmpty());
        }
    }

    @Test
    @DisplayName("Should validate merchant data successfully")
    void testValidateMerchantDataSuccess() throws Exception {
        // Create a merchant details request DTO with valid data
        MerchantDetailsRequestDTO merchantDTO = new MerchantDetailsRequestDTO();
        merchantDTO.setLegalName("Test Merchant");
        merchantDTO.setRevenue(new BigDecimal("100000.00"));

        // Mock validator to return no violations
        when(validator.validate(merchantDTO)).thenReturn(Collections.emptySet());

        // Mock ObjectMapper to serialize the DTO
        when(objectMapper.writeValueAsString(merchantDTO)).thenReturn("{\"legalName\":\"Test Merchant\",\"revenue\":100000.00}");

        // Mock JsonUtil to validate the JSON
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(true, null));

            // Call the method under test
            validationService.validateMerchantData(merchantDTO);

            // Verify that the validator was called
            verify(validator).validate(merchantDTO);

            // Verify that the ObjectMapper was called to serialize the DTO
            verify(objectMapper).writeValueAsString(merchantDTO);

            // Verify that JsonUtil was called to validate the JSON
            mockedStatic.verify(() -> JsonUtil.validateJson(anyString(), anyString()));
        }
    }

    @Test
    @DisplayName("Should throw ValidationException when merchant data fails bean validation")
    void testValidateMerchantDataFailsBeanValidation() {
        // Create a merchant details request DTO with invalid data
        MerchantDetailsRequestDTO merchantDTO = new MerchantDetailsRequestDTO();

        // Create a mock constraint violation
        @SuppressWarnings("unchecked")
        ConstraintViolation<MerchantDetailsRequestDTO> violation = mock(ConstraintViolation.class);
        when(violation.getPropertyPath()).thenReturn(new MockPath("legalName"));
        when(violation.getMessage()).thenReturn("Legal name is required");

        // Mock validator to return violations
        Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = new HashSet<>();
        violations.add(violation);
        when(validator.validate(merchantDTO)).thenReturn(violations);

        // Call the method under test and verify exception
        ValidationException exception = assertThrows(ValidationException.class, () -> {
            validationService.validateMerchantData(merchantDTO);
        });

        // Verify the exception contains the expected error
        List<ValidationError> errors = exception.getValidationErrors();
        assertNotNull(errors);
        assertEquals(1, errors.size());
        assertEquals("legalName", errors.get(0).getField());
        assertEquals("Legal name is required", errors.get(0).getMessage());

        // Verify that the validator was called
        verify(validator).validate(merchantDTO);
    }

    @Test
    @DisplayName("Should throw ValidationException when merchant data fails schema validation")
    void testValidateMerchantDataFailsSchemaValidation() throws Exception {
        // Create a merchant details request DTO
        MerchantDetailsRequestDTO merchantDTO = new MerchantDetailsRequestDTO();
        merchantDTO.setLegalName("Test Merchant");

        // Mock validator to return no violations
        when(validator.validate(merchantDTO)).thenReturn(Collections.emptySet());

        // Mock ObjectMapper to serialize the DTO
        when(objectMapper.writeValueAsString(merchantDTO)).thenReturn("{\"legalName\":\"Test Merchant\"}");

        // Mock JsonUtil to fail validation
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(false, "Schema validation failed"));

            // Call the method under test and verify exception
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                validationService.validateMerchantData(merchantDTO);
            });

            // Verify the exception contains the expected error
            assertEquals("Merchant data schema validation failed", exception.getMessage());

            // Verify that JsonUtil was called to validate the JSON
            mockedStatic.verify(() -> JsonUtil.validateJson(anyString(), anyString()));
        }
    }

    @Test
    @DisplayName("Should throw ValidationException when merchant data fails business rule validation")
    void testValidateMerchantDataFailsBusinessRuleValidation() throws Exception {
        // Create a merchant details request DTO with revenue below threshold
        MerchantDetailsRequestDTO merchantDTO = new MerchantDetailsRequestDTO();
        merchantDTO.setLegalName("Test Merchant");
        merchantDTO.setRevenue(new BigDecimal("40000.00")); // Below $50,000 threshold

        // Mock validator to return no violations
        when(validator.validate(merchantDTO)).thenReturn(Collections.emptySet());

        // Mock ObjectMapper to serialize the DTO
        when(objectMapper.writeValueAsString(merchantDTO)).thenReturn("{\"legalName\":\"Test Merchant\",\"revenue\":40000.00}");

        // Mock JsonUtil to pass validation
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(true, null));

            // Call the method under test and verify exception
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                validationService.validateMerchantData(merchantDTO);
            });

            // Verify the exception contains the expected error
            assertEquals("Business rule validation failed", exception.getMessage());
            assertEquals("revenue_threshold", exception.getValidationErrors().get(0).getField());
            assertEquals("Revenue must be at least $50,000 for funding", exception.getValidationErrors().get(0).getMessage());
        }
    }

    @Test
    @DisplayName("Should validate application data successfully")
    void testValidateApplicationDataSuccess() throws Exception {
        // Create application data
        Map<String, Object> applicationData = new HashMap<>();
        applicationData.put("id", "12345");
        applicationData.put("status", "PENDING");

        // Mock ObjectMapper to serialize the data
        when(objectMapper.writeValueAsString(applicationData)).thenReturn("{\"id\":\"12345\",\"status\":\"PENDING\"}");

        // Mock JsonUtil to validate the JSON
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(true, null));

            // Call the method under test
            validationService.validateApplicationData(applicationData);

            // Verify that the ObjectMapper was called to serialize the data
            verify(objectMapper).writeValueAsString(applicationData);

            // Verify that JsonUtil was called to validate the JSON
            mockedStatic.verify(() -> JsonUtil.validateJson(anyString(), anyString()));
        }
    }

    @Test
    @DisplayName("Should throw ValidationException when application data fails schema validation")
    void testValidateApplicationDataFailsSchemaValidation() throws Exception {
        // Create application data
        Map<String, Object> applicationData = new HashMap<>();
        applicationData.put("status", "PENDING"); // Missing required id field

        // Mock ObjectMapper to serialize the data
        when(objectMapper.writeValueAsString(applicationData)).thenReturn("{\"status\":\"PENDING\"}");

        // Mock JsonUtil to fail validation
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(false, "Required field 'id' is missing"));

            // Call the method under test and verify exception
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                validationService.validateApplicationData(applicationData);
            });

            // Verify the exception contains the expected error
            assertEquals("Application data schema validation failed", exception.getMessage());

            // Verify that JsonUtil was called to validate the JSON
            mockedStatic.verify(() -> JsonUtil.validateJson(anyString(), anyString()));
        }
    }

    @Test
    @DisplayName("Should throw ValidationException when application data fails business rule validation")
    void testValidateApplicationDataFailsBusinessRuleValidation() throws Exception {
        // Create application data with invalid status transition
        Map<String, Object> applicationData = new HashMap<>();
        applicationData.put("id", "12345");
        applicationData.put("status", "APPROVED");
        applicationData.put("current_status", "NEW"); // Invalid transition from NEW to APPROVED

        // Mock ObjectMapper to serialize the data
        when(objectMapper.writeValueAsString(applicationData)).thenReturn("{\"id\":\"12345\",\"status\":\"APPROVED\",\"current_status\":\"NEW\"}");

        // Mock JsonUtil to pass validation
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(true, null));

            // Mock the business rule to fail
            List<BusinessRule> mockRules = new ArrayList<>();
            BusinessRule mockRule = new BusinessRule("status_transition", "Invalid status transition", data -> false);
            mockRules.add(mockRule);
            Map<String, List<BusinessRule>> mockBusinessRules = new HashMap<>();
            mockBusinessRules.put("application", mockRules);
            ReflectionTestUtils.setField(validationService, "businessRules", mockBusinessRules);

            // Call the method under test and verify exception
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                validationService.validateApplicationData(applicationData);
            });

            // Verify the exception contains the expected error
            assertEquals("Business rule validation failed", exception.getMessage());
            assertEquals("status_transition", exception.getValidationErrors().get(0).getField());
            assertEquals("Invalid status transition", exception.getValidationErrors().get(0).getMessage());
        }
    }

    @Test
    @DisplayName("Should validate document data successfully")
    void testValidateDocumentDataSuccess() throws Exception {
        // Create document data
        Map<String, Object> documentData = new HashMap<>();
        documentData.put("id", "12345");
        documentData.put("type", "BANK_STATEMENT");

        // Mock ObjectMapper to serialize and convert to JsonNode
        when(objectMapper.writeValueAsString(documentData)).thenReturn("{\"id\":\"12345\",\"type\":\"BANK_STATEMENT\"}");
        JsonNode mockNode = mock(JsonNode.class);
        JsonNode typeNode = mock(JsonNode.class);
        when(objectMapper.valueToTree(documentData)).thenReturn(mockNode);
        when(mockNode.has("type")).thenReturn(true);
        when(mockNode.get("type")).thenReturn(typeNode);
        when(typeNode.asText()).thenReturn("BANK_STATEMENT");

        // Mock JsonUtil to validate the JSON
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(true, null));

            // Call the method under test
            validationService.validateDocumentData(documentData);

            // Verify that the ObjectMapper was called to serialize the data
            verify(objectMapper).writeValueAsString(documentData);
            verify(objectMapper).valueToTree(documentData);

            // Verify that JsonUtil was called to validate the JSON
            mockedStatic.verify(() -> JsonUtil.validateJson(anyString(), anyString()));
        }
    }

    @Test
    @DisplayName("Should throw ValidationException when document data has invalid document type")
    void testValidateDocumentDataInvalidType() throws Exception {
        // Create document data with invalid type
        Map<String, Object> documentData = new HashMap<>();
        documentData.put("id", "12345");
        documentData.put("type", "INVALID_TYPE");

        // Mock ObjectMapper to serialize and convert to JsonNode
        JsonNode mockNode = mock(JsonNode.class);
        JsonNode typeNode = mock(JsonNode.class);
        when(objectMapper.valueToTree(documentData)).thenReturn(mockNode);
        when(mockNode.has("type")).thenReturn(true);
        when(mockNode.get("type")).thenReturn(typeNode);
        when(typeNode.asText()).thenReturn("INVALID_TYPE");

        // Call the method under test and verify exception
        ValidationException exception = assertThrows(ValidationException.class, () -> {
            validationService.validateDocumentData(documentData);
        });

        // Verify the exception contains the expected error
        assertEquals("Invalid document type", exception.getMessage());
        assertEquals("type", exception.getValidationErrors().get(0).getField());
        assertEquals("Document type is not recognized", exception.getValidationErrors().get(0).getMessage());

        // Verify that the ObjectMapper was called
        verify(objectMapper).valueToTree(documentData);
    }

    @Test
    @DisplayName("Should throw ValidationException when document data fails schema validation")
    void testValidateDocumentDataFailsSchemaValidation() throws Exception {
        // Create document data
        Map<String, Object> documentData = new HashMap<>();
        documentData.put("id", "12345");
        documentData.put("type", "BANK_STATEMENT");

        // Mock ObjectMapper to serialize and convert to JsonNode
        when(objectMapper.writeValueAsString(documentData)).thenReturn("{\"id\":\"12345\",\"type\":\"BANK_STATEMENT\"}");
        JsonNode mockNode = mock(JsonNode.class);
        JsonNode typeNode = mock(JsonNode.class);
        when(objectMapper.valueToTree(documentData)).thenReturn(mockNode);
        when(mockNode.has("type")).thenReturn(true);
        when(mockNode.get("type")).thenReturn(typeNode);
        when(typeNode.asText()).thenReturn("BANK_STATEMENT");

        // Mock JsonUtil to fail validation
        try (MockedStatic<JsonUtil> mockedStatic = Mockito.mockStatic(JsonUtil.class)) {
            mockedStatic.when(() -> JsonUtil.validateJson(anyString(), anyString()))
                    .thenReturn(new JsonValidationResult(false, "Schema validation failed"));

            // Call the method under test and verify exception
            ValidationException exception = assertThrows(ValidationException.class, () -> {
                validationService.validateDocumentData(documentData);
            });

            // Verify the exception contains the expected error
            assertEquals("Document data schema validation failed", exception.getMessage());

            // Verify that JsonUtil was called to validate the JSON
            mockedStatic.verify(() -> JsonUtil.validateJson(anyString(), anyString()));
        }
    }

    @Test
    @DisplayName("Should check if application is complete successfully")
    void testIsApplicationCompleteSuccess() {
        // Create UUID for application
        UUID applicationId = UUID.randomUUID();

        // Mock application repository
        Application mockApplication = mock(Application.class);
        MerchantDetails mockMerchantDetails = mock(MerchantDetails.class);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(mockApplication));
        when(mockApplication.getMerchantDetails()).thenReturn(mockMerchantDetails);

        // Mock document repository
        List<Document> documents = new ArrayList<>();
        Document idDoc = createMockDocument(DocumentType.ID_VERIFICATION);
        Document bankDoc = createMockDocument(DocumentType.BANK_STATEMENT);
        Document businessDoc = createMockDocument(DocumentType.BUSINESS_LICENSE);
        documents.add(idDoc);
        documents.add(bankDoc);
        documents.add(businessDoc);
        when(documentRepository.findByApplicationId(applicationId)).thenReturn(documents);

        // Call the method under test
        boolean result = validationService.isApplicationComplete(applicationId);

        // Verify the result
        assertTrue(result);

        // Verify that the repositories were called
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should return false when application is missing merchant details")
    void testIsApplicationCompleteMissingMerchantDetails() {
        // Create UUID for application
        UUID applicationId = UUID.randomUUID();

        // Mock application repository
        Application mockApplication = mock(Application.class);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(mockApplication));
        when(mockApplication.getMerchantDetails()).thenReturn(null); // Missing merchant details

        // Call the method under test
        boolean result = validationService.isApplicationComplete(applicationId);

        // Verify the result
        assertFalse(result);

        // Verify that the repository was called
        verify(applicationRepository).findById(applicationId);
    }

    @Test
    @DisplayName("Should return false when application is missing required documents")
    void testIsApplicationCompleteMissingRequiredDocuments() {
        // Create UUID for application
        UUID applicationId = UUID.randomUUID();

        // Mock application repository
        Application mockApplication = mock(Application.class);
        MerchantDetails mockMerchantDetails = mock(MerchantDetails.class);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(mockApplication));
        when(mockApplication.getMerchantDetails()).thenReturn(mockMerchantDetails);

        // Mock document repository to return incomplete set of documents
        List<Document> documents = new ArrayList<>();
        Document idDoc = createMockDocument(DocumentType.ID_VERIFICATION);
        documents.add(idDoc); // Missing financial and business documents
        when(documentRepository.findByApplicationId(applicationId)).thenReturn(documents);

        // Call the method under test
        boolean result = validationService.isApplicationComplete(applicationId);

        // Verify the result
        assertFalse(result);

        // Verify that the repositories were called
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should return false when documents have insufficient confidence scores")
    void testIsApplicationCompleteInsufficientConfidence() {
        // Create UUID for application
        UUID applicationId = UUID.randomUUID();

        // Mock application repository
        Application mockApplication = mock(Application.class);
        MerchantDetails mockMerchantDetails = mock(MerchantDetails.class);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(mockApplication));
        when(mockApplication.getMerchantDetails()).thenReturn(mockMerchantDetails);

        // Mock document repository
        List<Document> documents = new ArrayList<>();
        Document idDoc = createMockDocument(DocumentType.ID_VERIFICATION);
        Document bankDoc = createMockDocument(DocumentType.BANK_STATEMENT);
        Document businessDoc = createMockDocument(DocumentType.BUSINESS_LICENSE);
        
        // Set low confidence score for bank document
        Map<String, Double> lowConfidenceScores = new HashMap<>();
        lowConfidenceScores.put("accountNumber", 0.6); // Below threshold
        when(bankDoc.getConfidenceScores()).thenReturn(lowConfidenceScores);
        when(bankDoc.getOcrConfidenceThreshold()).thenReturn(0.85);
        
        documents.add(idDoc);
        documents.add(bankDoc);
        documents.add(businessDoc);
        when(documentRepository.findByApplicationId(applicationId)).thenReturn(documents);

        // Call the method under test
        boolean result = validationService.isApplicationComplete(applicationId);

        // Verify the result
        assertFalse(result);

        // Verify that the repositories were called
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should check if application has required documents successfully")
    void testHasRequiredDocumentsSuccess() {
        // Create UUID for application
        UUID applicationId = UUID.randomUUID();

        // Mock application repository
        Application mockApplication = mock(Application.class);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(mockApplication));

        // Mock document repository
        List<Document> documents = new ArrayList<>();
        Document idDoc = mock(Document.class);
        Document bankDoc = mock(Document.class);
        Document businessDoc = mock(Document.class);
        when(idDoc.getType()).thenReturn(DocumentType.ID_VERIFICATION);
        when(bankDoc.getType()).thenReturn(DocumentType.BANK_STATEMENT);
        when(businessDoc.getType()).thenReturn(DocumentType.BUSINESS_LICENSE);
        documents.add(idDoc);
        documents.add(bankDoc);
        documents.add(businessDoc);
        when(documentRepository.findByApplicationId(applicationId)).thenReturn(documents);

        // Call the method under test
        boolean result = validationService.hasRequiredDocuments(applicationId);

        // Verify the result
        assertTrue(result);

        // Verify that the repositories were called
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should return false when application has no documents")
    void testHasRequiredDocumentsNoDocuments() {
        // Create UUID for application
        UUID applicationId = UUID.randomUUID();

        // Mock application repository
        Application mockApplication = mock(Application.class);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(mockApplication));

        // Mock document repository to return empty list
        when(documentRepository.findByApplicationId(applicationId)).thenReturn(Collections.emptyList());

        // Call the method under test
        boolean result = validationService.hasRequiredDocuments(applicationId);

        // Verify the result
        assertFalse(result);

        // Verify that the repositories were called
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should return false when application is missing some required document types")
    void testHasRequiredDocumentsMissingTypes() {
        // Create UUID for application
        UUID applicationId = UUID.randomUUID();

        // Mock application repository
        Application mockApplication = mock(Application.class);
        when(applicationRepository.findById(applicationId)).thenReturn(Optional.of(mockApplication));

        // Mock document repository to return incomplete set of documents
        List<Document> documents = new ArrayList<>();
        Document idDoc = mock(Document.class);
        when(idDoc.getType()).thenReturn(DocumentType.ID_VERIFICATION);
        documents.add(idDoc); // Missing financial and business documents
        when(documentRepository.findByApplicationId(applicationId)).thenReturn(documents);

        // Call the method under test
        boolean result = validationService.hasRequiredDocuments(applicationId);

        // Verify the result
        assertFalse(result);

        // Verify that the repositories were called
        verify(applicationRepository).findById(applicationId);
        verify(documentRepository).findByApplicationId(applicationId);
    }

    @Test
    @DisplayName("Should add and retrieve custom business rules")
    void testAddAndGetBusinessRules() {
        // Create a custom business rule
        BusinessRule customRule = new BusinessRule("custom_rule", "Custom rule message", data -> true);

        // Add the rule
        validationService.addBusinessRule("application", customRule);

        // Get the rules
        List<BusinessRule> rules = validationService.getBusinessRules("application");

        // Verify the rule was added
        assertNotNull(rules);
        assertTrue(rules.size() > 0);
        boolean found = false;
        for (BusinessRule rule : rules) {
            if (rule.getName().equals("custom_rule")) {
                found = true;
                assertEquals("Custom rule message", rule.getMessage());
                break;
            }
        }
        assertTrue(found, "Custom rule should be found in the list");
    }

    @Test
    @DisplayName("Should remove business rules")
    void testRemoveBusinessRule() {
        // Create a custom business rule
        BusinessRule customRule = new BusinessRule("custom_rule", "Custom rule message", data -> true);

        // Add the rule
        validationService.addBusinessRule("application", customRule);

        // Verify the rule was added
        List<BusinessRule> rulesBeforeRemoval = validationService.getBusinessRules("application");
        boolean foundBeforeRemoval = false;
        for (BusinessRule rule : rulesBeforeRemoval) {
            if (rule.getName().equals("custom_rule")) {
                foundBeforeRemoval = true;
                break;
            }
        }
        assertTrue(foundBeforeRemoval, "Custom rule should be found before removal");

        // Remove the rule
        boolean removed = validationService.removeBusinessRule("application", "custom_rule");
        assertTrue(removed, "Rule should be successfully removed");

        // Verify the rule was removed
        List<BusinessRule> rulesAfterRemoval = validationService.getBusinessRules("application");
        boolean foundAfterRemoval = false;
        for (BusinessRule rule : rulesAfterRemoval) {
            if (rule.getName().equals("custom_rule")) {
                foundAfterRemoval = true;
                break;
            }
        }
        assertFalse(foundAfterRemoval, "Custom rule should not be found after removal");
    }

    @Test
    @DisplayName("Should apply business rules correctly")
    void testBusinessRuleApplication() {
        // Create a business rule that always passes
        BusinessRule passingRule = new BusinessRule("passing_rule", "This rule always passes", data -> true);

        // Create a business rule that always fails
        BusinessRule failingRule = new BusinessRule("failing_rule", "This rule always fails", data -> false);

        // Test passing rule
        assertTrue(passingRule.apply("test data"), "Passing rule should return true");

        // Test failing rule
        assertFalse(failingRule.apply("test data"), "Failing rule should return false");

        // Verify rule properties
        assertEquals("passing_rule", passingRule.getName());
        assertEquals("This rule always passes", passingRule.getMessage());
        assertEquals("failing_rule", failingRule.getName());
        assertEquals("This rule always fails", failingRule.getMessage());
    }

    // Helper method to create a mock document with confidence scores
    private Document createMockDocument(DocumentType type) {
        Document mockDocument = mock(Document.class);
        when(mockDocument.getType()).thenReturn(type);
        
        // Create confidence scores above threshold
        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("field1", 0.95);
        confidenceScores.put("field2", 0.90);
        when(mockDocument.getConfidenceScores()).thenReturn(confidenceScores);
        
        // Set threshold based on document type
        when(mockDocument.getOcrConfidenceThreshold()).thenReturn(type.getOcrConfidenceThreshold());
        
        return mockDocument;
    }

    // Helper class to mock Path for constraint violations
    private static class MockPath implements javax.validation.Path {
        private final String propertyName;

        public MockPath(String propertyName) {
            this.propertyName = propertyName;
        }

        @Override
        public Iterator<Node> iterator() {
            List<Node> nodes = new ArrayList<>();
            nodes.add(new MockNode(propertyName));
            return nodes.iterator();
        }

        @Override
        public String toString() {
            return propertyName;
        }
    }

    // Helper class to mock Path.Node for constraint violations
    private static class MockNode implements javax.validation.Path.Node {
        private final String name;

        public MockNode(String name) {
            this.name = name;
        }

        @Override
        public String getName() {
            return name;
        }

        @Override
        public boolean isInIterable() {
            return false;
        }

        @Override
        public Integer getIndex() {
            return null;
        }

        @Override
        public Object getKey() {
            return null;
        }

        @Override
        public ElementKind getKind() {
            return ElementKind.PROPERTY;
        }

        @Override
        public <T extends Node> T as(Class<T> nodeType) {
            return null;
        }
    }
}